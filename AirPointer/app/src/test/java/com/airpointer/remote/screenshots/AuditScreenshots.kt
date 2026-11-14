package com.airpointer.remote.screenshots

import androidx.activity.compose.setContent
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import com.airpointer.remote.MainActivity
import com.airpointer.remote.graph
import com.airpointer.remote.transport.TransportKind
import com.airpointer.remote.ui.AppActions
import com.airpointer.remote.ui.screens.DiagnosticsScreen
import com.airpointer.remote.ui.screens.HomeScreen
import com.airpointer.remote.ui.screens.MediaRemoteScreen
import com.airpointer.remote.ui.screens.PairingScreen
import com.airpointer.remote.ui.screens.PcMouseScreen
import com.airpointer.remote.ui.screens.SettingsScreen
import com.airpointer.remote.ui.screens.TvDevicesScreen
import com.airpointer.remote.ui.theme.AirPointerTheme
import com.github.takahirom.roborazzi.ExperimentalRoborazziApi
import com.github.takahirom.roborazzi.captureRoboImage
import com.github.takahirom.roborazzi.captureScreenRoboImage
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Shadows.shadowOf
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/** Every screen not covered elsewhere, on a tall display so whole pages can be reviewed. */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w411dp-h2200dp-night-xxhdpi")
@OptIn(ExperimentalRoborazziApi::class)
class AuditScreenshots {
    @get:Rule val compose = createAndroidComposeRule<MainActivity>()
    private val actions = AppActions({}, {}, {}, permissionsGranted = true)
    private val g get() = compose.activity.graph

    private fun show(content: @androidx.compose.runtime.Composable () -> Unit) {
        compose.runOnUiThread { compose.activity.setContent { AirPointerTheme { content() } } }
        shadowOf(android.os.Looper.getMainLooper()).idle(); compose.waitForIdle()
    }
    private fun save(name: String) = compose.onRoot().captureRoboImage("build/screenshots/audit/$name.png")
    private fun saveScreen(name: String) { shadowOf(android.os.Looper.getMainLooper()).idle(); captureScreenRoboImage("build/screenshots/audit/$name.png") }

    @Test fun connectionBluetooth() { g.settings.update { it.copy(transport = TransportKind.BLUETOOTH) }; show { PairingScreen(g, actions) {} }; save("connection-bluetooth") }
    @Test fun connectionWifi() { g.settings.update { it.copy(transport = TransportKind.WIFI) }; show { PairingScreen(g, actions) {} }; Thread.sleep(1800); shadowOf(android.os.Looper.getMainLooper()).idle(); save("connection-wifi") }
    @Test fun settings() { show { SettingsScreen(g) {} }; save("settings") }
    @Test fun diagnostics() { show { DiagnosticsScreen(g) {} }; save("diagnostics") }
    @Test fun tvDevices() { show { TvDevicesScreen(g) {} }; save("tv-devices") }
    @Test fun mediaVlcSetup() { g.settings.update { it.copy(mediaPlayer = "VLC", vlcHost = null) }; show { MediaRemoteScreen(g, {}, {}) }; save("media-vlc-setup") }
    @Test fun airMouseTab() { show { PcMouseScreen(g, compose.activity, {}, {}) }; compose.onNodeWithText("Air mouse").performClick(); compose.waitForIdle(); save("pc-mouse-air") }
    @Test fun tableTab() { show { PcMouseScreen(g, compose.activity, {}, {}) }; compose.onNodeWithText("Table").performClick(); compose.waitForIdle(); save("pc-mouse-table") }
    @Test fun keyboardDialog() {
        show { PcMouseScreen(g, compose.activity, {}, {}) }
        compose.mainClock.autoAdvance = false // the text field's blinking cursor never lets Compose go idle
        compose.onNodeWithContentDescription("Keyboard").performClick()
        compose.mainClock.advanceTimeBy(500)
        saveScreen("keyboard-dialog")
    }
    @Test fun homeGateDialog() {
        g.settings.update { it.copy(transport = TransportKind.WIFI, wifiHost = "192.168.1.20", wifiPin = "123456") }
        show { HomeScreen(g, actions, {}, {}, {}) }
        compose.onNodeWithText("Presentation").performClick(); compose.waitForIdle(); saveScreen("home-gate-dialog")
    }
    @Test fun homeFull() {
        g.settings.update { it.copy(transport = TransportKind.WIFI, wifiHost = "192.168.1.20", wifiPin = "123456", wifiName = "Office PC") }
        show { HomeScreen(g, actions, {}, {}, {}) }; save("home-full")
    }
}
