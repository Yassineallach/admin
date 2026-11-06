package com.airpointer.remote.tv

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

/**
 * LG webOS TVs: SSAP over WebSocket (wss://TV:3001, older firmware ws://TV:3000).
 *  1. {"type":"register", payload:{pairingType:"PROMPT", manifest:{permissions…}, client-key}} → the TV
 *     asks the user, then answers {"type":"registered", payload:{"client-key":…}} (kept for next time).
 *  2. Commands: {"type":"request","uri":"ssap://audio/volumeUp"} etc.
 *  3. Navigation keys (arrows, OK, back, home, numbers) go through the "pointer input socket"
 *     obtained from ssap://com.webos.service.networkinput/getPointerInputSocket, as text frames
 *     "type:button\nname:UP\n\n".
 */
class LgWebOsTv(private val host: String, private var clientKey: String?, private var mac: String?, pin: String? = null) : TvConnection {

    private val trust = PinnedTrust(pin)
    private val http = SamsungTv.pinnedClient(trust)
    override val certificatePin: String? get() = trust.seen

    override val protocol = TvProtocol.LG_WEBOS
    private val _state = MutableStateFlow<TvConnState>(TvConnState.Disconnected)
    override val state: StateFlow<TvConnState> = _state
    override val supportsText = true
    override val supportedKeys = (SSAP.keys + BUTTONS.keys + TvKey.VOICE).toSet()
    override val limitations = listOf(
        "Accept the request on the TV the first time (Settings → General → Mobile TV On helps with power-on).",
        "Power on uses Wake-on-LAN and needs \"Mobile TV On\" / \"Turn on via Wi-Fi\" enabled on the TV.",
        "Voice is recognised on the phone and inserted into the TV's focused text field.",
        "Some webOS versions reject unsigned remote apps for a few permissions; if registration fails, use IR or Bluetooth.",
    )
    override val credential: String? get() = clientKey

    private var ws: WebSocket? = null
    private var pointer: WebSocket? = null
    private val ids = AtomicInteger(1)
    private var muted = false

    override suspend fun connect() = withContext(Dispatchers.IO) {
        _state.value = TvConnState.Connecting
        if (!open("wss://$host:3001") && !open("ws://$host:3000")) {
            _state.value = TvConnState.Failed("Cannot reach the LG TV at $host. Is it on and on the same network?")
            return@withContext
        }
        val reply = request(null, registerPayload(clientKey), type = "register", timeoutMs = 60_000, waitFor = "registered")
        val key = reply?.optJSONObject("payload")?.optString("client-key")
        if (key.isNullOrBlank()) {
            _state.value = TvConnState.Failed("The TV did not accept Air Pointer (prompt declined or timed out).")
            return@withContext
        }
        clientKey = key
        openPointerSocket()
        _state.value = TvConnState.Connected
    }

    private suspend fun open(url: String): Boolean {
        val opened = CompletableDeferred<Boolean>()
        ws = http.newWebSocket(Request.Builder().url(url).build(), object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) { opened.complete(true) }
            override fun onMessage(webSocket: WebSocket, text: String) {
                val j = runCatching { JSONObject(text) }.getOrNull() ?: return
                if (j.optString("type") == "response" && j.optJSONObject("payload")?.optString("pairingType") == "PROMPT") {
                    _state.value = TvConnState.NeedsUser("Accept the request on the TV screen.")
                    return
                }
                val id = j.optString("id")
                val p = waiting[id] ?: return
                val waitFor = p.waitFor
                if (waitFor == null || j.optString("type") == waitFor || j.optString("type") == "error") {
                    waiting.remove(id); p.deferred.complete(j)
                }
            }
            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                opened.complete(false)
                if (_state.value is TvConnState.Connected) _state.value = TvConnState.Failed("Connection to the TV was lost")
            }
        })
        return withTimeoutOrNull(5000) { opened.await() } ?: false
    }

    private class Pending(val deferred: CompletableDeferred<JSONObject>, val waitFor: String?)
    private val waiting = ConcurrentHashMap<String, Pending>()

    private suspend fun request(uri: String?, payload: JSONObject?, type: String = "request", timeoutMs: Long = 4000, waitFor: String? = null): JSONObject? {
        val id = "${type}_${ids.getAndIncrement()}"
        val d = CompletableDeferred<JSONObject>()
        waiting[id] = Pending(d, waitFor)
        val msg = JSONObject().put("type", type).put("id", id)
        if (uri != null) msg.put("uri", uri)
        if (payload != null) msg.put("payload", payload)
        ws?.send(msg.toString()) ?: return null
        return withTimeoutOrNull(timeoutMs) { d.await() }.also { waiting.remove(id) }
    }

    private suspend fun openPointerSocket() {
        val r = request("ssap://com.webos.service.networkinput/getPointerInputSocket", null)
        val path = r?.optJSONObject("payload")?.optString("socketPath")?.takeIf { it.isNotBlank() } ?: return
        pointer = http.newWebSocket(Request.Builder().url(path).build(), object : WebSocketListener() {})
    }

    override suspend fun send(key: TvKey) = withContext(Dispatchers.IO) {
        if (key == TvKey.POWER && _state.value !is TvConnState.Connected) { mac?.let { WakeOnLan.send(it) }; return@withContext }
        BUTTONS[key]?.let { pointer?.send(buttonFrame(it)); return@withContext }
        when (key) {
            TvKey.MUTE -> { muted = !muted; request("ssap://audio/setMute", JSONObject().put("mute", muted)) }
            TvKey.SOURCE -> request("ssap://system.launcher/launch", JSONObject().put("id", "com.webos.app.inputpicker"))
            TvKey.SETTINGS -> request("ssap://system.launcher/launch", JSONObject().put("id", "com.palm.app.settings"))
            else -> SSAP[key]?.let { request(it, null) }
        }
        Unit
    }

    override suspend fun sendText(text: String) = withContext(Dispatchers.IO) {
        request("ssap://com.webos.service.ime/insertText", JSONObject().put("text", text).put("replace", 0))
        Unit
    }

    override fun close() {
        pointer?.close(1000, null); ws?.close(1000, null)
        pointer = null; ws = null
        _state.value = TvConnState.Disconnected
    }

    companion object {
        val SSAP: Map<TvKey, String> = mapOf(
            TvKey.POWER to "ssap://system/turnOff",
            TvKey.VOLUME_UP to "ssap://audio/volumeUp", TvKey.VOLUME_DOWN to "ssap://audio/volumeDown",
            TvKey.MUTE to "ssap://audio/setMute",
            TvKey.CHANNEL_UP to "ssap://tv/channelUp", TvKey.CHANNEL_DOWN to "ssap://tv/channelDown",
            TvKey.PLAY to "ssap://media.controls/play", TvKey.PAUSE to "ssap://media.controls/pause",
            TvKey.STOP to "ssap://media.controls/stop", TvKey.REWIND to "ssap://media.controls/rewind",
            TvKey.FAST_FORWARD to "ssap://media.controls/fastForward",
            TvKey.SOURCE to "ssap://system.launcher/launch", TvKey.SETTINGS to "ssap://system.launcher/launch",
        )

        /** Pointer-socket button names. */
        val BUTTONS: Map<TvKey, String> = mapOf(
            TvKey.HOME to "HOME", TvKey.BACK to "BACK", TvKey.MENU to "MENU", TvKey.INFO to "INFO", TvKey.EXIT to "EXIT",
            TvKey.UP to "UP", TvKey.DOWN to "DOWN", TvKey.LEFT to "LEFT", TvKey.RIGHT to "RIGHT", TvKey.OK to "ENTER",
            TvKey.PLAY_PAUSE to "PLAY",
        ) + TvKey.digits.mapIndexed { i, k -> k to "$i" }

        fun buttonFrame(name: String) = "type:button\nname:$name\n\n"

        fun registerPayload(clientKey: String?): JSONObject {
            val permissions = listOf(
                "LAUNCH", "LAUNCH_WEBAPP", "APP_TO_APP", "CONTROL_AUDIO", "CONTROL_DISPLAY",
                "CONTROL_INPUT_JOYSTICK", "CONTROL_INPUT_MEDIA_PLAYBACK", "CONTROL_INPUT_TV", "CONTROL_POWER",
                "CONTROL_INPUT_TEXT", "CONTROL_MOUSE_AND_KEYBOARD", "READ_INSTALLED_APPS", "READ_INPUT_DEVICE_LIST",
                "READ_CURRENT_CHANNEL", "READ_RUNNING_APPS", "WRITE_NOTIFICATION_TOAST", "READ_POWER_STATE",
            )
            return JSONObject()
                .put("forcePairing", false)
                .put("pairingType", "PROMPT")
                .apply { if (clientKey != null) put("client-key", clientKey) }
                .put("manifest", JSONObject()
                    .put("manifestVersion", 1)
                    .put("appVersion", "1.0")
                    .put("permissions", JSONArray(permissions)))
        }
    }
}
