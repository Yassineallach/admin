package com.airpointer.remote.media

import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.airpointer.remote.transport.WifiCompanionClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test

/**
 * Runs the real Kotlin clients against real players. Skipped unless the environment provides:
 *   AIRPOINTER_VLC=host:port:password   (cvlc --intf http --http-password …)
 *   AIRPOINTER_COMPANION=host:port:pin   (companion with mpv --input-ipc-server running)
 */
class MediaIntegrationTest {

    private fun env(name: String) = System.getenv(name)?.split(':')

    @Test
    fun vlcHttpInterface() = runBlocking {
        val e = env("AIRPOINTER_VLC"); assumeTrue("AIRPOINTER_VLC not set", e != null)
        val vlc = VlcBackend(e!![0], e[1].toInt(), e[2])
        var s = vlc.status()
        println("VLC status: $s")
        assertTrue("duration known", s.durationSec > 50)

        vlc.seekTo(30.0); delay(600)
        s = vlc.status(); println("after seekTo(30): ${s.positionSec}")
        assertEquals(30.0, s.positionSec, 2.0)

        vlc.seekRelative(10.0); delay(600)
        s = vlc.status(); println("after +10: ${s.positionSec}")
        assertEquals(40.0, s.positionSec, 2.5)

        vlc.seekRelative(-10.0); delay(600)
        assertEquals(30.0, vlc.status().positionSec, 2.5)

        vlc.changeVolume(50); delay(300)
        val v0 = vlc.status().volumePercent
        if (v0 > 0) { // needs a real audio output; headless CI has none
            vlc.changeVolume(-20); delay(300)
            val v1 = vlc.status().volumePercent
            println("volume $v0 -> $v1")
            assertTrue(v1 < v0)
            vlc.toggleMute(); delay(300)
            assertTrue("muted", vlc.status().muted)
            vlc.toggleMute(); delay(300)
            assertEquals(v1.toDouble(), vlc.status().volumePercent.toDouble(), 2.0)
        } else println("VLC volume checks skipped: no audio output device in this environment")

        vlc.setSpeed(1.5); delay(300)
        assertEquals(1.5, vlc.status().speed, 0.01)
        vlc.setSpeed(1.0)

        vlc.shiftSubtitleDelay(0.5); delay(300)
        assertEquals(0.5, vlc.status().subtitleDelaySec, 0.05)
        vlc.shiftSubtitleDelay(-0.5)

        val audio = VlcBackend.streams(org.json.JSONObject(), "Audio")
        assertTrue(audio.isEmpty())
        vlc.cycleAudioTrack() // two audio tracks in the test file
        vlc.toggleSubtitles()

        assertEquals(PlayState.PLAYING, vlc.status().state)
        vlc.playPause(); delay(400)
        assertEquals(PlayState.PAUSED, vlc.status().state)
        vlc.playPause(); delay(400)
        assertEquals(PlayState.PLAYING, vlc.status().state)
    }

    @Test
    fun mpvThroughCompanion() = runBlocking {
        val e = env("AIRPOINTER_COMPANION"); assumeTrue("AIRPOINTER_COMPANION not set", e != null)
        val client = WifiCompanionClient(DiagnosticsLog(), CoroutineScope(SupervisorJob() + Dispatchers.IO), "JVM test")
        client.connect(e!![0], e[1].toInt(), e[2])
        repeat(50) { if (!client.isConnected) delay(100) }
        assertTrue("connected to companion: ${client.state.value}", client.isConnected)
        assertTrue("mpv feature", "mpv" in client.state.value.features)

        val mpv = MpvBackend(client)
        var s = mpv.status()
        println("MPV status: $s")
        assertTrue(s.durationSec > 50)
        assertEquals("Air Pointer test clip", s.title)

        mpv.seekTo(30.0); delay(500)
        assertEquals(30.0, mpv.status().positionSec, 1.5)
        mpv.seekRelative(10.0); delay(500)
        assertEquals(40.0, mpv.status().positionSec, 1.5)

        val v = mpv.status().volumePercent
        mpv.changeVolume(-10); delay(200)
        assertEquals(v - 10, mpv.status().volumePercent)
        mpv.toggleMute(); delay(200)
        assertTrue(mpv.status().muted)
        mpv.toggleMute()

        mpv.setSpeed(1.25); delay(200)
        assertEquals(1.25, mpv.status().speed, 0.001)
        mpv.setSpeed(1.0)

        mpv.shiftSubtitleDelay(0.2); delay(200)
        assertEquals(0.2, mpv.status().subtitleDelaySec, 0.001)
        mpv.shiftSubtitleDelay(-0.2)

        val sub0 = mpv.status().subtitlesVisible
        mpv.toggleSubtitles(); delay(200)
        assertEquals(sub0?.not(), mpv.status().subtitlesVisible)
        mpv.toggleSubtitles()

        val a0 = mpv.status().audioTrack
        mpv.cycleAudioTrack(); delay(300)
        println("audio track $a0 -> ${mpv.status().audioTrack}")
        assertTrue(a0 != mpv.status().audioTrack)

        mpv.playPause(); delay(300)
        assertEquals(PlayState.PAUSED, mpv.status().state)
        mpv.playPause(); delay(300)
        assertEquals(PlayState.PLAYING, mpv.status().state)
        client.disconnect()
    }
}
