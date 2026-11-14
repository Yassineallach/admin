package com.airpointer.remote.screenshots

import androidx.activity.compose.setContent
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onRoot
import com.airpointer.remote.MainActivity
import com.airpointer.remote.graph
import com.airpointer.remote.transport.TransportKind
import com.airpointer.remote.ui.AppActions
import com.airpointer.remote.ui.screens.HomeScreen
import com.airpointer.remote.ui.screens.MediaRemoteScreen
import com.airpointer.remote.ui.screens.PairingScreen
import com.airpointer.remote.ui.screens.PcMouseScreen
import com.airpointer.remote.ui.screens.RemoteScreen
import com.airpointer.remote.ui.screens.SettingsScreen
import com.airpointer.remote.ui.screens.TvRemoteScreen
import com.airpointer.remote.ui.theme.AirPointerTheme
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/** Where each ad slot sits: every screen with its slot in the loading state (no ad requests). */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-night-xxhdpi")
open class AdSlotScreenshots {
    protected open val dir = "large"
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()
    private val actions = AppActions({}, {}, {}, permissionsGranted = true)
    private val g get() = compose.activity.graph

    private fun shot(name: String, content: @androidx.compose.runtime.Composable () -> Unit) {
        g.settings.update { it.copy(transport = TransportKind.WIFI, wifiHost = "192.168.1.20", wifiPin = "123456", wifiName = "Office PC") }
        compose.runOnUiThread { g.ads.showLoadingSlotsForPreview() }
        compose.runOnUiThread { compose.activity.setContent { AirPointerTheme { content() } } }
        shadowOf(android.os.Looper.getMainLooper()).idle(); compose.waitForIdle()
        compose.onRoot().captureRoboImage("build/screenshots/ad-slots/$dir/$name.png")
    }

    @Test fun home() = shot("home") { HomeScreen(g, actions, {}, {}, {}) }
    @Test fun connection() = shot("connection") { PairingScreen(g, actions) {} }
    @Test fun settings() = shot("settings") { SettingsScreen(g) {} }
    @Test fun presentation() = shot("presentation") { RemoteScreen(g, compose.activity, {}, {}) }
    @Test fun pcMouse() = shot("pc-mouse") { PcMouseScreen(g, compose.activity, {}, {}) }
    @Test fun media() = shot("media") { g.settings.update { it.copy(mediaPlayer = "MPV") }; MediaRemoteScreen(g, {}, {}) }
    @Test fun tv() = shot("tv") {
        val tv = com.airpointer.remote.tv.SavedTv("t1", "Living room", com.airpointer.remote.tv.TvProtocol.BLUETOOTH_HID)
        g.tvRepository.save(tv); g.tvRepository.select(tv.id)
        TvRemoteScreen(g, {}, {})
    }
}

/** Small phone (360x640dp): the ad must still be visible without scrolling. */
@Config(sdk = [34], qualifiers = "w360dp-h640dp-night-xhdpi")
class AdSlotSmallScreenshots : AdSlotScreenshots() { override val dir = "small" }
