package com.airpointer.remote.transport

import com.airpointer.remote.diagnostics.DiagnosticsLog
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.withTimeoutOrNull
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.net.URLDecoder
import java.net.URLEncoder
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * Client for the Air Pointer desktop companion (see companion/protocol.go).
 * A reader thread handles the handshake and replies, a writer thread drains an outgoing queue so
 * the sensor/io thread never blocks on the network, and a keep-alive ping detects dead links.
 */
class WifiCompanionClient(
    private val log: DiagnosticsLog,
    scope: CoroutineScope,
    private val clientName: String,
) : ReportSink {

    enum class Phase { IDLE, CONNECTING, CONNECTED, FAILED }

    data class State(
        val phase: Phase = Phase.IDLE,
        val host: String? = null,
        val port: Int = DEFAULT_PORT,
        val serverName: String? = null,
        val serverOs: String? = null,
        val features: Set<String> = emptySet(),
        val error: String? = null,
        val latencyMs: Int? = null,
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state
    override val connectedFlow: StateFlow<Boolean> =
        _state.map { it.phase == Phase.CONNECTED }.stateIn(scope, SharingStarted.Eagerly, false)

    override val reportsSent = AtomicLong()
    override val reportFailures = AtomicLong()

    @Volatile private var socket: Socket? = null
    @Volatile private var connected = false
    @Volatile private var wanted: Target? = null
    private val outgoing = LinkedBlockingQueue<String>(512)
    private val pendingMpv = ConcurrentLinkedQueue<CompletableDeferred<String?>>()
    @Volatile private var pingSentAt = 0L
    private var generation = 0

    private data class Target(val host: String, val port: Int, val pin: String)

    override val isConnected: Boolean get() = connected

    @Synchronized
    fun connect(host: String, port: Int, pin: String) {
        wanted = Target(host.trim(), port, pin.trim())
        restart()
    }

    @Synchronized
    fun disconnect() {
        wanted = null
        generation++
        closeSocket()
        _state.update { it.copy(phase = Phase.IDLE, error = null) }
    }

    @Synchronized
    private fun restart() {
        val t = wanted ?: return
        generation++
        val gen = generation
        closeSocket()
        _state.update { State(phase = Phase.CONNECTING, host = t.host, port = t.port) }
        Thread({ runConnection(t, gen) }, "wifi-companion").apply { isDaemon = true; start() }
    }

    private fun closeSocket() {
        connected = false
        try { socket?.close() } catch (_: Exception) {}
        socket = null
        outgoing.clear()
        while (true) pendingMpv.poll()?.complete(null) ?: break
    }

    private fun runConnection(t: Target, gen: Int) {
        var attempt = 0
        while (gen == generation && wanted == t) {
            val result = try {
                session(t, gen)
            } catch (e: Exception) {
                e.message ?: e.javaClass.simpleName
            }
            if (gen != generation) return
            connected = false
            if (result == PIN_REJECTED) {
                log.e(TAG, "Companion rejected the PIN")
                _state.update { it.copy(phase = Phase.FAILED, error = "Wrong PIN. Check the PIN shown in the companion window.") }
                return
            }
            attempt++
            val delay = minOf(1000L * attempt, 10_000L)
            log.w(TAG, "Wi-Fi link lost ($result); retrying in ${delay / 1000}s")
            _state.update { it.copy(phase = Phase.CONNECTING, error = result) }
            Thread.sleep(delay)
        }
    }

    /** Runs one TCP session; returns the reason it ended. */
    private fun session(t: Target, gen: Int): String {
        val s = Socket()
        s.tcpNoDelay = true
        s.connect(InetSocketAddress(t.host, t.port), 4000)
        s.soTimeout = 8000
        synchronized(this) {
            if (gen != generation) { s.close(); return "superseded" }
            socket = s
        }
        val reader = BufferedReader(InputStreamReader(s.getInputStream(), Charsets.UTF_8))
        val out = s.getOutputStream()
        val challenge = reader.readLine() ?: return "closed during handshake"
        if (!challenge.startsWith("CHALLENGE ")) return "not an Air Pointer companion"
        val nonce = hexToBytes(challenge.removePrefix("CHALLENGE ").trim())
        writeLine(out, "HELLO 1 ${URLEncoder.encode(clientName, "UTF-8")} ${proof(t.pin, nonce)}")
        val reply = reader.readLine() ?: return "closed during handshake"
        if (reply.startsWith("DENIED")) return if (reply.contains("pin")) PIN_REJECTED else reply
        if (!reply.startsWith("WELCOME ")) return "unexpected reply"
        val f = reply.split(' ')
        val name = f.getOrNull(1)?.let { URLDecoder.decode(it, "UTF-8") }
        connected = true
        outgoing.clear()
        _state.update {
            it.copy(phase = Phase.CONNECTED, serverName = name, serverOs = f.getOrNull(2),
                features = f.getOrNull(3)?.split(',')?.toSet().orEmpty(), error = null)
        }
        log.i(TAG, "Connected to companion $name at ${t.host}:${t.port}")
        val writer = Thread({ writerLoop(out, gen) }, "wifi-writer").apply { isDaemon = true; start() }
        try {
            while (gen == generation) {
                val line = reader.readLine() ?: return "companion closed the connection"
                when {
                    line == "P" -> {
                        val rtt = (System.nanoTime() - pingSentAt) / 1_000_000
                        _state.update { it.copy(latencyMs = rtt.toInt()) }
                    }
                    line.startsWith("MPV ") -> pendingMpv.poll()?.complete(line.removePrefix("MPV "))
                    line.startsWith("MPVERR") -> pendingMpv.poll()?.complete(null)
                }
            }
            return "superseded"
        } finally {
            connected = false
            writer.interrupt()
            try { s.close() } catch (_: Exception) {}
        }
    }

    private fun writerLoop(out: OutputStream, gen: Int) {
        var lastPing = 0L
        try {
            while (gen == generation && connected) {
                val line = outgoing.poll(500, TimeUnit.MILLISECONDS)
                val now = System.nanoTime()
                if (line != null) writeLine(out, line)
                if (now - lastPing > PING_INTERVAL_NS) {
                    pingSentAt = now; lastPing = now
                    writeLine(out, "P")
                }
            }
        } catch (_: Exception) {
            try { socket?.close() } catch (_: Exception) {}
        }
    }

    private fun writeLine(out: OutputStream, line: String) {
        out.write((line + "\n").toByteArray(Charsets.UTF_8))
        out.flush()
    }

    override fun sendReport(id: Int, data: ByteArray): Boolean {
        if (!connected) return false
        val ok = outgoing.offer("R $id ${bytesToHex(data)}")
        if (ok) reportsSent.incrementAndGet() else reportFailures.incrementAndGet()
        return ok
    }

    /** Send an mpv JSON IPC command through the companion; returns mpv's JSON reply or null. */
    suspend fun mpv(json: String, timeoutMs: Long = 2500): String? {
        if (!connected) return null
        val d = CompletableDeferred<String?>()
        pendingMpv.add(d)
        if (!outgoing.offer("MPV $json")) { pendingMpv.remove(d); return null }
        return withTimeoutOrNull(timeoutMs) { d.await() }.also { if (it == null) pendingMpv.remove(d) }
    }

    companion object {
        private const val TAG = "WiFi"
        const val DEFAULT_PORT = 47778
        const val DISCOVERY_PORT = 47777
        private const val PIN_REJECTED = "__pin__"
        private const val PING_INTERVAL_NS = 2_000_000_000L

        fun proof(pin: String, nonce: ByteArray): String {
            val mac = Mac.getInstance("HmacSHA256")
            mac.init(SecretKeySpec(pin.toByteArray(Charsets.UTF_8), "HmacSHA256"))
            return bytesToHex(mac.doFinal(nonce))
        }

        fun bytesToHex(b: ByteArray): String {
            val hex = "0123456789abcdef"
            val sb = StringBuilder(b.size * 2)
            for (x in b) { sb.append(hex[(x.toInt() shr 4) and 0xF]); sb.append(hex[x.toInt() and 0xF]) }
            return sb.toString()
        }

        fun hexToBytes(s: String): ByteArray = ByteArray(s.length / 2) { i ->
            ((Character.digit(s[2 * i], 16) shl 4) or Character.digit(s[2 * i + 1], 16)).toByte()
        }
    }
}
