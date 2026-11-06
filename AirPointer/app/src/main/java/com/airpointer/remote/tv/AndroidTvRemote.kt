package com.airpointer.remote.tv

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import java.io.OutputStream
import java.math.BigInteger
import java.net.InetSocketAddress
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.cert.X509Certificate
import java.security.interfaces.RSAPublicKey
import java.util.Calendar
import javax.net.ssl.KeyManagerFactory
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocket
import javax.net.ssl.TrustManager
import javax.security.auth.x500.X500Principal

/**
 * Android TV / Google TV "Remote Service v2" (the protocol of Google's own TV remote app).
 *
 *  Pairing, port 6467 (once): TLS with a client certificate → PairingRequest → Options →
 *  Configuration (6-digit hex code) → the TV shows a code → Secret = SHA-256(client modulus,
 *  client exponent, server modulus, server exponent, code[2..]) whose first byte must equal code[0..1].
 *  Remote, port 6466: same client certificate; answer RemoteConfigure / RemoteSetActive / pings,
 *  send RemoteKeyInject(Android KeyEvent code, SHORT).
 * Messages are protobuf, each prefixed with its varint length.
 */
class AndroidTvRemote(private val host: String, private val deviceName: String, pin: String? = null) : TvConnection {

    private val trust = PinnedTrust(pin)
    override val certificatePin: String? get() = trust.seen

    override val protocol = TvProtocol.ANDROID_TV
    private val _state = MutableStateFlow<TvConnState>(TvConnState.Disconnected)
    override val state: StateFlow<TvConnState> = _state
    override val supportsText = false
    override val supportedKeys = KEYCODES.keys + TvKey.VOICE
    override val limitations = listOf(
        "Pairing needs the 6-digit code shown on the TV once; later connections are automatic.",
        "Voice opens the TV's own Google Assistant (it listens through the TV/remote microphone).",
        "Power on from standby works only if the TV keeps its network on (\"Network standby\").",
    )

    @Volatile private var socket: SSLSocket? = null
    private var pairing: SSLSocket? = null
    @Volatile private var closed = false

    override suspend fun connect() = withContext(Dispatchers.IO) {
        closed = false
        _state.value = TvConnState.Connecting
        try {
            openRemote()
        } catch (e: javax.net.ssl.SSLException) {
            // The TV does not know our certificate yet: pair first.
            startPairing()
        } catch (e: Exception) {
            _state.value = TvConnState.Failed("Cannot reach the TV at $host (${e.message}). Is it on and on the same Wi-Fi?")
        }
    }

    private fun tls(port: Int): SSLSocket {
        val ctx = SSLContext.getInstance("TLS")
        val kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm())
        kmf.init(clientKeyStore(), null)
        ctx.init(kmf.keyManagers, arrayOf<TrustManager>(trust), null)
        val s = ctx.socketFactory.createSocket() as SSLSocket
        s.connect(InetSocketAddress(host, port), 4000)
        s.soTimeout = 0
        s.startHandshake()
        return s
    }

    private fun send(out: OutputStream, msg: ByteArray) {
        synchronized(out) {
            out.write(ProtoWriter.varintBytes(msg.size)); out.write(msg); out.flush()
        }
    }

    // ------------------------------------------------------------------ pairing (6467)

    private fun startPairing() {
        val s = tls(PAIRING_PORT)
        pairing = s
        val out = s.outputStream; val inp = s.inputStream
        fun pairingMsg(build: ProtoWriter.() -> Unit) = ProtoWriter().int(1, 2).int(2, STATUS_OK).apply(build).toByteArray()
        fun expect(field: Int) {
            val m = ProtoMessage.parse(ProtoMessage.readDelimited(inp) ?: error("TV closed the pairing connection"))
            val status = m.int(2) ?: STATUS_OK
            if (status != STATUS_OK) error("TV refused pairing (status $status)")
            if (!m.has(field)) error("unexpected pairing reply ${m.fieldNumbers}")
        }
        send(out, pairingMsg { message(10) { string(1, "atvremote"); string(2, deviceName) } })
        expect(11)
        send(out, pairingMsg {
            message(20) {
                message(1) { int(1, ENCODING_HEX); int(2, 6) }
                int(3, ROLE_INPUT)
            }
        })
        expect(20)
        send(out, pairingMsg { message(30) { message(1) { int(1, ENCODING_HEX); int(2, 6) }; int(2, ROLE_INPUT) } })
        expect(31)
        _state.value = TvConnState.NeedsUser("Enter the code shown on the TV", needsCode = true)
    }

    override suspend fun submitCode(code: String) = withContext(Dispatchers.IO) {
        val s = pairing ?: return@withContext
        try {
            val clientKey = clientCertificate().publicKey as RSAPublicKey
            val serverKey = (s.session.peerCertificates[0] as X509Certificate).publicKey as RSAPublicKey
            val secret = pairingSecret(clientKey.modulus, clientKey.publicExponent, serverKey.modulus, serverKey.publicExponent, code)
                ?: run { _state.value = TvConnState.NeedsUser("That code does not match. Check the TV and try again.", true); return@withContext }
            send(s.outputStream, ProtoWriter().int(1, 2).int(2, STATUS_OK).message(40) { bytes(1, secret) }.toByteArray())
            val reply = ProtoMessage.parse(ProtoMessage.readDelimited(s.inputStream) ?: error("no reply"))
            if ((reply.int(2) ?: STATUS_OK) != STATUS_OK || !reply.has(41)) error("TV rejected the code")
            s.close(); pairing = null
            _state.value = TvConnState.Connecting
            openRemote()
        } catch (e: Exception) {
            _state.value = TvConnState.Failed("Pairing failed: ${e.message}")
        }
    }

    // ------------------------------------------------------------------ remote (6466)

    private fun openRemote() {
        val s = tls(REMOTE_PORT)
        val out = s.outputStream; val inp = s.inputStream
        // A paired TV starts by sending RemoteConfigure. An unknown certificate is either refused
        // during the handshake or the TV closes the connection without a word: pair in both cases.
        s.soTimeout = 5000
        val first = try { ProtoMessage.readDelimited(inp) } catch (_: Exception) { null }
        if (first == null) { runCatching { s.close() }; throw javax.net.ssl.SSLException("not paired") }
        s.soTimeout = 0
        socket = s
        Thread({
            var pending: ByteArray? = first
            try {
                while (!closed) {
                    val raw = pending ?: ProtoMessage.readDelimited(inp) ?: break
                    pending = null
                    val m = ProtoMessage.parse(raw)
                    when {
                        m.has(1) -> send(out, ProtoWriter().message(1) {
                            int(1, 622)
                            message(2) { string(1, "Air Pointer"); string(2, "Air Pointer"); int(3, 1); string(4, "1"); string(5, "atvremote"); string(6, "1.0.0") }
                        }.toByteArray())
                        m.has(2) -> {
                            send(out, ProtoWriter().message(2) { int(1, 622) }.toByteArray())
                            _state.value = TvConnState.Connected
                        }
                        m.has(8) -> send(out, ProtoWriter().message(9) { int(1, m.message(8)?.int(1) ?: 0) }.toByteArray())
                        m.has(3) -> _state.value = TvConnState.Failed("TV reported a remote error")
                    }
                }
            } catch (_: Exception) {
            }
            if (!closed) _state.value = TvConnState.Failed("Connection to the TV was lost")
        }, "atv-remote").apply { isDaemon = true; start() }
    }

    override suspend fun send(key: TvKey) = withContext(Dispatchers.IO) {
        val s = socket ?: return@withContext
        val code = if (key == TvKey.VOICE) KEYCODE_ASSIST else KEYCODES[key] ?: return@withContext
        runCatching { send(s.outputStream, keyInject(code, DIRECTION_SHORT)) }
            .onFailure { _state.value = TvConnState.Failed("Connection to the TV was lost") }
        Unit
    }

    override fun close() {
        closed = true
        runCatching { socket?.close() }; runCatching { pairing?.close() }
        socket = null; pairing = null
        _state.value = TvConnState.Disconnected
    }

    companion object {
        const val PAIRING_PORT = 6467
        const val REMOTE_PORT = 6466
        const val STATUS_OK = 200
        const val ENCODING_HEX = 3
        const val ROLE_INPUT = 1
        const val DIRECTION_SHORT = 3
        const val KEYCODE_ASSIST = 219
        private const val ALIAS = "airpointer-atv-client"

        /** Android KeyEvent codes understood by the TV. */
        val KEYCODES: Map<TvKey, Int> = mapOf(
            TvKey.POWER to 26, TvKey.VOLUME_UP to 24, TvKey.VOLUME_DOWN to 25, TvKey.MUTE to 164,
            TvKey.CHANNEL_UP to 166, TvKey.CHANNEL_DOWN to 167, TvKey.HOME to 3, TvKey.BACK to 4,
            TvKey.MENU to 82, TvKey.SETTINGS to 176, TvKey.SOURCE to 178, TvKey.INFO to 165,
            TvKey.UP to 19, TvKey.DOWN to 20, TvKey.LEFT to 21, TvKey.RIGHT to 22, TvKey.OK to 23,
            TvKey.PLAY_PAUSE to 85, TvKey.PLAY to 126, TvKey.PAUSE to 127, TvKey.STOP to 86,
            TvKey.REWIND to 89, TvKey.FAST_FORWARD to 90, TvKey.EXIT to 111,
        ) + TvKey.digits.mapIndexed { i, k -> k to 7 + i }

        fun keyInject(keyCode: Int, direction: Int): ByteArray =
            ProtoWriter().message(10) { int(1, keyCode); int(2, direction) }.toByteArray()

        /** Unsigned big-endian bytes without leading zeros (Python `bytes.fromhex('%X' % n)` with even padding). */
        fun unsignedBytes(n: BigInteger): ByteArray {
            val b = n.toByteArray()
            var i = 0
            while (i < b.size - 1 && b[i] == 0.toByte()) i++
            return b.copyOfRange(i, b.size)
        }

        /** Returns the 32-byte secret, or null when the code's check byte does not match. */
        fun pairingSecret(clientN: BigInteger, clientE: BigInteger, serverN: BigInteger, serverE: BigInteger, code: String): ByteArray? {
            val c = code.trim().uppercase()
            if (c.length != 6 || c.any { it !in "0123456789ABCDEF" }) return null
            val nonce = BigInteger(c.substring(2), 16).toByteArray().let { if (it.size > 2) it.copyOfRange(it.size - 2, it.size) else ByteArray(2 - it.size) + it }
            val md = MessageDigest.getInstance("SHA-256")
            md.update(unsignedBytes(clientN)); md.update(unsignedBytes(clientE))
            md.update(unsignedBytes(serverN)); md.update(unsignedBytes(serverE))
            md.update(nonce)
            val hash = md.digest()
            return if ((hash[0].toInt() and 0xFF) == c.substring(0, 2).toInt(16)) hash else null
        }

        /** RSA client identity kept in the Android Keystore (generated once, private key never leaves it). */
        fun clientKeyStore(): KeyStore {
            val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
            if (!ks.containsAlias(ALIAS)) {
                val start = Calendar.getInstance(); val end = Calendar.getInstance().apply { add(Calendar.YEAR, 20) }
                val kpg = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, "AndroidKeyStore")
                kpg.initialize(
                    KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_DECRYPT)
                        .setKeySize(2048)
                        .setCertificateSubject(X500Principal("CN=atvremote/Air Pointer"))
                        .setCertificateSerialNumber(BigInteger.ONE)
                        .setCertificateNotBefore(start.time).setCertificateNotAfter(end.time)
                        .setDigests(KeyProperties.DIGEST_NONE, KeyProperties.DIGEST_SHA256, KeyProperties.DIGEST_SHA384, KeyProperties.DIGEST_SHA512)
                        .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1, KeyProperties.SIGNATURE_PADDING_RSA_PSS)
                        .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_RSA_PKCS1, KeyProperties.ENCRYPTION_PADDING_NONE)
                        .build(),
                )
                kpg.generateKeyPair()
            }
            return ks
        }

        fun clientCertificate(): X509Certificate = clientKeyStore().getCertificate(ALIAS) as X509Certificate
    }
}
