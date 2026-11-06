package com.airpointer.remote.tv

import android.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.security.SecureRandom
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLContext

/**
 * Samsung Tizen Smart TVs (2016+): WebSocket remote API.
 *   wss://TV:8002/api/v2/channels/samsung.remote.control?name=<base64>&token=<token>
 * First connection: the TV shows "Allow"; it then sends ms.channel.connect with a token we keep.
 * Keys: {"method":"ms.remote.control","params":{"Cmd":"Click","DataOfCmd":"KEY_…","Option":"false","TypeOfRemote":"SendRemoteKey"}}
 * Power on: Wake-on-LAN to the MAC reported by http://TV:8001/api/v2/ (needs "Power on with mobile").
 */
class SamsungTv(
    private val host: String,
    private var token: String?,
    private var mac: String?,
    private val appName: String = "Air Pointer",
    pin: String? = null,
) : TvConnection {

    private val trust = PinnedTrust(pin)
    private val http = pinnedClient(trust)
    override val certificatePin: String? get() = trust.seen

    override val protocol = TvProtocol.SAMSUNG_TIZEN
    private val _state = MutableStateFlow<TvConnState>(TvConnState.Disconnected)
    override val state: StateFlow<TvConnState> = _state
    override val supportsText = true
    override val supportedKeys = KEYS.keys + TvKey.VOICE
    override val limitations = listOf(
        "Accept the \"Air Pointer\" request on the TV the first time.",
        "Power on uses Wake-on-LAN: enable Settings → General → Network → Expert → Power On with Mobile.",
        "Voice is recognised on the phone and typed into the TV's focused text field.",
        "Samsung models before 2016 (Orsay, port 55000) are not supported.",
    )
    override val credential: String? get() = token
    val macAddress: String? get() = mac

    private var ws: WebSocket? = null

    override suspend fun connect() = withContext(Dispatchers.IO) {
        _state.value = TvConnState.Connecting
        if (mac == null) mac = runCatching { fetchMac() }.getOrNull()
        val name = Base64.encodeToString(appName.toByteArray(), Base64.NO_WRAP)
        val url = "wss://$host:8002/api/v2/channels/samsung.remote.control?name=$name" + (token?.let { "&token=$it" } ?: "")
        ws = http.newWebSocket(Request.Builder().url(url).build(), object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                if (token == null) _state.value = TvConnState.NeedsUser("Choose \"Allow\" on the TV screen.")
            }
            override fun onMessage(webSocket: WebSocket, text: String) {
                val j = runCatching { JSONObject(text) }.getOrNull() ?: return
                when (j.optString("event")) {
                    "ms.channel.connect" -> {
                        j.optJSONObject("data")?.optString("token")?.takeIf { it.isNotBlank() }?.let { token = it }
                        _state.value = TvConnState.Connected
                    }
                    "ms.channel.unauthorized" -> _state.value = TvConnState.Failed("The TV denied access. Allow \"Air Pointer\" under Settings → General → External Device Manager → Device Connect Manager.")
                    "ms.channel.timeOut" -> _state.value = TvConnState.Failed("No answer on the TV in time. Try again and accept the prompt.")
                }
            }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                _state.value = TvConnState.Failed("Cannot reach the Samsung TV at $host (${t.message}).")
            }
            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                if (_state.value is TvConnState.Connected) _state.value = TvConnState.Disconnected
            }
        })
    }

    private fun fetchMac(): String? {
        val r = http.newCall(Request.Builder().url("http://$host:8001/api/v2/").build()).execute()
        return r.use { JSONObject(it.body!!.string()).optJSONObject("device")?.optString("wifiMac")?.takeIf { m -> m.contains(':') } }
    }

    override suspend fun send(key: TvKey) = withContext(Dispatchers.IO) {
        if (key == TvKey.POWER && _state.value !is TvConnState.Connected) {
            mac?.let { WakeOnLan.send(it) }
            return@withContext
        }
        val code = KEYS[key] ?: return@withContext
        ws?.send(keyMessage(code))
        if (key == TvKey.POWER) mac?.let { WakeOnLan.send(it) } // also wakes a TV in network standby
        Unit
    }

    override suspend fun sendText(text: String) = withContext(Dispatchers.IO) {
        ws?.send(textMessage(text))
        ws?.send(JSONObject().put("method", "ms.remote.control").put("params",
            JSONObject().put("TypeOfRemote", "SendInputEnd")).toString())
        Unit
    }

    override fun close() {
        ws?.close(1000, null); ws = null
        _state.value = TvConnState.Disconnected
    }

    companion object {
        val KEYS: Map<TvKey, String> = mapOf(
            TvKey.POWER to "KEY_POWER", TvKey.VOLUME_UP to "KEY_VOLUP", TvKey.VOLUME_DOWN to "KEY_VOLDOWN",
            TvKey.MUTE to "KEY_MUTE", TvKey.CHANNEL_UP to "KEY_CHUP", TvKey.CHANNEL_DOWN to "KEY_CHDOWN",
            TvKey.HOME to "KEY_HOME", TvKey.BACK to "KEY_RETURN", TvKey.MENU to "KEY_MENU", TvKey.SETTINGS to "KEY_MENU",
            TvKey.SOURCE to "KEY_SOURCE", TvKey.INFO to "KEY_INFO", TvKey.EXIT to "KEY_EXIT",
            TvKey.UP to "KEY_UP", TvKey.DOWN to "KEY_DOWN", TvKey.LEFT to "KEY_LEFT", TvKey.RIGHT to "KEY_RIGHT",
            TvKey.OK to "KEY_ENTER", TvKey.PLAY_PAUSE to "KEY_PLAY", TvKey.PLAY to "KEY_PLAY", TvKey.PAUSE to "KEY_PAUSE",
            TvKey.STOP to "KEY_STOP", TvKey.REWIND to "KEY_REWIND", TvKey.FAST_FORWARD to "KEY_FF",
        ) + TvKey.digits.mapIndexed { i, k -> k to "KEY_$i" }

        fun keyMessage(code: String): String = JSONObject()
            .put("method", "ms.remote.control")
            .put("params", JSONObject().put("Cmd", "Click").put("DataOfCmd", code).put("Option", "false").put("TypeOfRemote", "SendRemoteKey"))
            .toString()

        fun textMessage(text: String): String = JSONObject()
            .put("method", "ms.remote.control")
            .put("params", JSONObject()
                .put("Cmd", Base64.encodeToString(text.toByteArray(), Base64.NO_WRAP))
                .put("DataOfCmd", "base64").put("TypeOfRemote", "SendInputString"))
            .toString()

        /** OkHttp client that accepts exactly the pinned self-signed TV certificate (see [PinnedTrust]). */
        internal fun pinnedClient(trust: PinnedTrust): OkHttpClient {
            val ctx = SSLContext.getInstance("TLS").apply { init(null, arrayOf(trust), SecureRandom()) }
            return OkHttpClient.Builder()
                .sslSocketFactory(ctx.socketFactory, trust)
                .hostnameVerifier { _, _ -> true } // local IP + self-signed cert: the pin replaces name checks
                .connectTimeout(4, TimeUnit.SECONDS)
                .readTimeout(0, TimeUnit.SECONDS)
                .pingInterval(20, TimeUnit.SECONDS)
                .build()
        }
    }
}
