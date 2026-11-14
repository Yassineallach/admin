package com.airpointer.remote.media

/** What the timeline and buttons show. Times in seconds. */
data class MediaStatus(
    val state: PlayState = PlayState.STOPPED,
    val positionSec: Double = 0.0,
    val durationSec: Double = 0.0,
    val volumePercent: Int = 0,
    val muted: Boolean = false,
    val speed: Double = 1.0,
    val title: String? = null,
    val subtitleDelaySec: Double = 0.0,
    val subtitlesVisible: Boolean? = null,
    val fullscreen: Boolean = false,
    val audioTrack: String? = null,
    val subtitleTrack: String? = null,
) {
    val remainingSec get() = (durationSec - positionSec).coerceAtLeast(0.0)
}

enum class PlayState { PLAYING, PAUSED, STOPPED }

enum class MediaCap { STOP, PREV_NEXT, SEEK, SPEED, FULLSCREEN, SUBTITLE_TOGGLE, SUBTITLE_DELAY, AUDIO_TRACK, SUBTITLE_TRACK, VOLUME, MUTE }

/** One desktop media player. VLC and MPV use completely different protocols, see the implementations. */
interface MediaBackend {
    val displayName: String
    val capabilities: Set<MediaCap>

    /** Fetch the player state; throws [MediaException] when the player cannot be reached. */
    suspend fun status(): MediaStatus

    suspend fun playPause()
    suspend fun stop()
    suspend fun previous()
    suspend fun next()
    suspend fun seekRelative(seconds: Double)
    suspend fun seekTo(seconds: Double)
    suspend fun changeVolume(deltaPercent: Int)
    /** Absolute volume, 0–100 %. */
    suspend fun setVolume(percent: Int)
    suspend fun toggleMute()
    suspend fun setSpeed(speed: Double)
    suspend fun toggleFullscreen()
    suspend fun toggleSubtitles()
    suspend fun shiftSubtitleDelay(deltaSec: Double)
    suspend fun cycleAudioTrack()
    suspend fun cycleSubtitleTrack()
}

class MediaException(message: String, cause: Throwable? = null) : Exception(message, cause)

fun formatTime(sec: Double): String {
    val s = sec.toLong().coerceAtLeast(0)
    val h = s / 3600; val m = (s % 3600) / 60; val r = s % 60
    return if (h > 0) "%d:%02d:%02d".format(h, m, r) else "%d:%02d".format(m, r)
}
