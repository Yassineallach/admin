package com.airpointer.remote.screenshots

import androidx.activity.compose.setContent
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onRoot
import com.airpointer.remote.MainActivity
import com.airpointer.remote.graph
import com.airpointer.remote.transport.TransportKind
import com.airpointer.remote.ui.AppActions
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.screens.HomeScreen
import com.airpointer.remote.ui.screens.MediaRemoteScreen
import com.airpointer.remote.ui.screens.PcMouseScreen
import com.airpointer.remote.ui.screens.RemoteScreen
import com.airpointer.remote.ui.screens.TvRemoteScreen
import com.airpointer.remote.ui.theme.AirPointerTheme
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/**
 * Full screens with the real activity and app graph. With AIRPOINTER_SCREENSHOT_COMPANION=host:port:pin
 * the app connects to a real companion over Wi-Fi first, so "connected" screens show a real link.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-night-xxhdpi")
class ScreenScreenshots {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()

    private val actions = AppActions({}, {}, {}, permissionsGranted = true)

    private fun connect(): Boolean {
        val e = System.getenv("AIRPOINTER_SCREENSHOT_COMPANION")?.split(':') ?: return false
        val g = compose.activity.graph
        g.settings.update { it.copy(transport = TransportKind.WIFI, wifiHost = e[0], wifiPort = e[1].toInt(), wifiPin = e[2], wifiName = "Office PC") }
        g.wifi.connect(e[0], e[1].toInt(), e[2])
        val deadline = System.currentTimeMillis() + 8000
        while (!g.wifi.isConnected && System.currentTimeMillis() < deadline) Thread.sleep(50)
        check(g.wifi.isConnected) { "companion did not accept the connection" }
        Thread.sleep(2500) // first keep-alive round trip → signal quality
        // State flows are collected on the main looper, which Robolectric only runs on request.
        org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle()
        check(g.link.connectedFlow.value) { "link not reported as connected" }
        return true
    }

    private fun shot(name: String, content: @androidx.compose.runtime.Composable () -> Unit) {
        compose.runOnUiThread { compose.activity.setContent { AirPointerTheme { content() } } }
        org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle()
        compose.waitForIdle()
        compose.onRoot().captureRoboImage("build/screenshots/$name.png")
    }

    @Test fun homeNotSetUp() {
        val g = compose.activity.graph
        g.settings.update { it.copy(transport = TransportKind.WIFI, wifiHost = null, wifiPin = null) }
        shot("home-not-set-up") { HomeScreen(g, actions, {}, {}, {}) }
    }

    @Test fun homeConnected() {
        assumeTrue(connect())
        val g = compose.activity.graph
        g.settings.update { it.copy(lastRemote = Route.PC_MOUSE.name) }
        shot("home-connected") { HomeScreen(g, actions, {}, {}, {}) }
    }

    @Test fun pcMouse() {
        assumeTrue(connect())
        shot("remote-pc-mouse") { PcMouseScreen(compose.activity.graph, compose.activity, {}, {}) }
    }

    @Test fun presentation() {
        assumeTrue(connect())
        shot("remote-presentation") { RemoteScreen(compose.activity.graph, compose.activity, {}, {}) }
    }

    @Test fun presentationDisconnected() {
        shot("remote-presentation-disconnected") { RemoteScreen(compose.activity.graph, compose.activity, {}, {}) }
    }

    @Test fun media() {
        assumeTrue(connect())
        val g = compose.activity.graph
        g.settings.update { it.copy(mediaPlayer = "MPV") }
        shot("remote-media") { MediaRemoteScreen(g, {}, {}) }
    }

    @Test fun tv() {
        val g = compose.activity.graph
        val tv = com.airpointer.remote.tv.SavedTv("t1", "Living room", com.airpointer.remote.tv.TvProtocol.BLUETOOTH_HID)
        g.tvRepository.save(tv); g.tvRepository.select(tv.id)
        shot("remote-tv") { TvRemoteScreen(g, {}, {}) }
    }
}
