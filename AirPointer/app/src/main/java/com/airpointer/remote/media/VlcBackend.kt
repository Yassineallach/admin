package com.airpointer.remote.media

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.Credentials
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * VLC Media Player through its built-in HTTP interface ("Web" Lua interface, default port 8080,
 * Basic auth with an empty user name and the password set in VLC preferences).
 * Endpoint: GET /requests/status.json?command=…&val=…   (always returns the full status JSON).
 */
class VlcBackend(
    private val host: String,
    private val port: Int = 8080,
    private val password: String,
    private val client: OkHttpClient = defaultClient,
) : MediaBackend {

    override val displayName = "VLC"
    override val capabilities = setOf(
        MediaCap.STOP, MediaCap.PREV_NEXT, MediaCap.SEEK, MediaCap.SPEED, MediaCap.FULLSCREEN,
        MediaCap.SUBTITLE_TOGGLE, MediaCap.SUBTITLE_DELAY, MediaCap.AUDIO_TRACK, MediaCap.SUBTITLE_TRACK,
        MediaCap.VOLUME, MediaCap.MUTE,
    )

    private var last: JSONObject? = null
    private var volumeBeforeMute = 256

    private suspend fun call(command: String? = null, value: String? = null): JSONObject = withContext(Dispatchers.IO) {
        val url = HttpUrl.Builder().scheme("http").host(host).port(port)
            .addPathSegments("requests/status.json")
            .apply {
                if (command != null) addQueryParameter("command", command)
                if (value != null) addQueryParameter("val", value)
            }.build()
        val req = Request.Builder().url(url).header("Authorization", Credentials.basic("", password)).build()
        try {
            client.newCall(req).execute().use { r ->
                when (r.code) {
                    200 -> JSONObject(r.body!!.string()).also { last = it }
                    401 -> throw MediaException("VLC rejected the password (Tools → Preferences → All → Interface → Main interfaces → Lua → Lua HTTP password).")
                    else -> throw MediaException("VLC answered HTTP ${r.code}")
                }
            }
        } catch (e: MediaException) {
            throw e
        } catch (e: Exception) {
            throw MediaException("Cannot reach VLC at $host:$port — is the Web interface enabled and the firewall open?", e)
        }
    }

    override suspend fun status(): MediaStatus = parseStatus(call())

    override suspend fun playPause() { call("pl_pause") }
    override suspend fun stop() { call("pl_stop") }
    override suspend fun previous() { call("pl_previous") }
    override suspend fun next() { call("pl_next") }
    override suspend fun seekRelative(seconds: Double) {
        val s = seconds.toInt()
        call("seek", if (s >= 0) "+$s" else "$s")
    }
    override suspend fun seekTo(seconds: Double) { call("seek", seconds.toInt().coerceAtLeast(0).toString()) }

    /** VLC volume is 0…512 where 256 = 100 %. */
    override suspend fun changeVolume(deltaPercent: Int) {
        val delta = deltaPercent * 256 / 100
        call("volume", if (delta >= 0) "+$delta" else "$delta")
    }

    /** VLC's HTTP interface has no mute command: remember the volume, set 0, restore it. */
    override suspend fun toggleMute() {
        val vol = (last ?: call()).optInt("volume", 256)
        if (vol > 0) {
            volumeBeforeMute = vol
            call("volume", "0")
        } else {
            call("volume", volumeBeforeMute.coerceAtLeast(64).toString())
        }
    }

    override suspend fun setSpeed(speed: Double) { call("rate", speed.toString()) }
    override suspend fun toggleFullscreen() { call("fullscreen") }

    override suspend fun toggleSubtitles() {
        val s = last ?: call()
        val subs = streams(s, "Subtitle")
        if (subs.isEmpty()) throw MediaException("This file has no subtitle track.")
        // subtitle_track with an invalid id (-1) disables subtitles in VLC 3.
        val current = currentSubtitle
        currentSubtitle = if (current == null || current < 0) subs.first() else -1
        call("subtitle_track", currentSubtitle.toString())
    }

    override suspend fun shiftSubtitleDelay(deltaSec: Double) {
        val now = (last ?: call()).optDouble("subtitledelay", 0.0)
        call("subdelay", "%.2f".format(java.util.Locale.US, now + deltaSec))
    }

    private var currentAudio: Int? = null
    private var currentSubtitle: Int? = null

    override suspend fun cycleAudioTrack() {
        val tracks = streams(last ?: call(), "Audio")
        if (tracks.size < 2) throw MediaException("Only one audio track is available.")
        val i = tracks.indexOf(currentAudio ?: tracks.first())
        currentAudio = tracks[(i + 1) % tracks.size]
        call("audio_track", currentAudio.toString())
    }

    override suspend fun cycleSubtitleTrack() {
        val tracks = streams(last ?: call(), "Subtitle")
        if (tracks.isEmpty()) throw MediaException("This file has no subtitle track.")
        val i = tracks.indexOf(currentSubtitle ?: -1)
        currentSubtitle = if (i + 1 >= tracks.size) -1 else tracks[i + 1]
        call("subtitle_track", currentSubtitle.toString())
    }

    companion object {
        val defaultClient: OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(3, TimeUnit.SECONDS).readTimeout(3, TimeUnit.SECONDS).build()

        /** Stream ids of a given type from information.category ("Stream N" → id N). */
        fun streams(status: JSONObject, type: String): List<Int> {
            val cat = status.optJSONObject("information")?.optJSONObject("category") ?: return emptyList()
            val out = mutableListOf<Int>()
            for (key in cat.keys()) {
                if (!key.startsWith("Stream ")) continue
                val obj = cat.optJSONObject(key) ?: continue
                val t = obj.optString("Type", obj.optString("Type_", ""))
                if (t.equals(type, ignoreCase = true)) key.removePrefix("Stream ").toIntOrNull()?.let { out += it }
            }
            return out.sorted()
        }

        fun parseStatus(j: JSONObject): MediaStatus {
            val meta = j.optJSONObject("information")?.optJSONObject("category")?.optJSONObject("meta")
            val title = meta?.optString("title")?.takeIf { it.isNotBlank() } ?: meta?.optString("filename")?.takeIf { it.isNotBlank() }
            val vol = j.optInt("volume", 0)
            val fs = j.opt("fullscreen")
            return MediaStatus(
                state = when (j.optString("state")) {
                    "playing" -> PlayState.PLAYING
                    "paused" -> PlayState.PAUSED
                    else -> PlayState.STOPPED
                },
                positionSec = j.optDouble("time", 0.0).let { t ->
                    // "time" is whole seconds; position (0…1) × length is finer when available.
                    val len = j.optDouble("length", 0.0); val pos = j.optDouble("position", -1.0)
                    if (len > 0 && pos >= 0) pos * len else t
                },
                durationSec = j.optDouble("length", 0.0).coerceAtLeast(0.0),
                volumePercent = vol * 100 / 256,
                muted = vol == 0,
                speed = j.optDouble("rate", 1.0),
                title = title,
                subtitleDelaySec = j.optDouble("subtitledelay", 0.0),
                fullscreen = fs == true || fs == 1 || fs == "true",
            )
        }
    }
}
