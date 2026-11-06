package com.airpointer.remote.media

import com.airpointer.remote.transport.WifiCompanionClient
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicLong

/**
 * MPV through its JSON IPC (`--input-ipc-server`). mpv only exposes IPC on a local Unix socket or
 * Windows named pipe, so commands travel phone → desktop companion (Wi-Fi) → mpv socket.
 * Every command is {"command":[…],"request_id":N}; replies carry {"error":"success","data":…}.
 */
class MpvBackend(private val send: suspend (String) -> String?) : MediaBackend {

    constructor(companion: WifiCompanionClient) : this({ json -> companion.mpv(json) })

    override val displayName = "MPV"
    override val capabilities = MediaCap.entries.toSet()

    private val ids = AtomicLong(1)

    private suspend fun command(vararg args: Any): Any? {
        val id = ids.getAndIncrement()
        val json = JSONObject().put("command", JSONArray(args.toList())).put("request_id", id).toString()
        val reply = send(json) ?: throw MediaException(
            "No answer from mpv. Start mpv with --input-ipc-server (see the setup guide) and keep the companion running.")
        val j = JSONObject(reply)
        val err = j.optString("error", "success")
        if (err != "success") {
            if (err == "property unavailable") return null
            throw MediaException("mpv: $err")
        }
        return j.opt("data").takeIf { it != JSONObject.NULL }
    }

    private suspend fun prop(name: String): Any? = try { command("get_property", name) } catch (e: MediaException) {
        if (e.message?.contains("mpv:") == true) null else throw e
    }

    override suspend fun status(): MediaStatus {
        val pause = prop("pause") as? Boolean
        val idle = prop("idle-active") as? Boolean ?: false
        val pos = (prop("time-pos") as? Number)?.toDouble() ?: 0.0
        val dur = (prop("duration") as? Number)?.toDouble() ?: 0.0
        return MediaStatus(
            state = when {
                idle || pause == null -> PlayState.STOPPED
                pause -> PlayState.PAUSED
                else -> PlayState.PLAYING
            },
            positionSec = pos,
            durationSec = dur,
            volumePercent = (prop("volume") as? Number)?.toInt() ?: 0,
            muted = prop("mute") as? Boolean ?: false,
            speed = (prop("speed") as? Number)?.toDouble() ?: 1.0,
            title = prop("media-title") as? String,
            subtitleDelaySec = (prop("sub-delay") as? Number)?.toDouble() ?: 0.0,
            subtitlesVisible = prop("sub-visibility") as? Boolean,
            fullscreen = prop("fullscreen") as? Boolean ?: false,
            audioTrack = prop("aid")?.toString(),
            subtitleTrack = prop("sid")?.toString(),
        )
    }

    override suspend fun playPause() { command("cycle", "pause") }
    override suspend fun stop() { command("stop") }
    override suspend fun previous() { command("playlist-prev") }
    override suspend fun next() { command("playlist-next") }
    override suspend fun seekRelative(seconds: Double) { command("seek", seconds, "relative+exact") }
    override suspend fun seekTo(seconds: Double) { command("seek", seconds, "absolute") }
    override suspend fun changeVolume(deltaPercent: Int) { command("add", "volume", deltaPercent) }
    override suspend fun toggleMute() { command("cycle", "mute") }
    override suspend fun setSpeed(speed: Double) { command("set_property", "speed", speed) }
    override suspend fun toggleFullscreen() { command("cycle", "fullscreen") }
    override suspend fun toggleSubtitles() { command("cycle", "sub-visibility") }
    override suspend fun shiftSubtitleDelay(deltaSec: Double) { command("add", "sub-delay", deltaSec) }
    override suspend fun cycleAudioTrack() { command("cycle", "audio") }
    override suspend fun cycleSubtitleTrack() { command("cycle", "sub") }
}
