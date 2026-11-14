package com.airpointer.remote.screenshots

import androidx.activity.ComponentActivity
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Insights
import androidx.compose.material.icons.rounded.Mouse
import androidx.compose.material.icons.rounded.Slideshow
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.unit.dp
import com.airpointer.remote.ui.LinkSnapshot
import com.airpointer.remote.ui.Method
import com.airpointer.remote.ui.components.BannerTone
import com.airpointer.remote.ui.components.ConnectionCard
import com.airpointer.remote.ui.components.NotificationBanner
import com.airpointer.remote.ui.components.RemoteCard
import com.airpointer.remote.ui.components.SetupItem
import com.airpointer.remote.ui.connectionCardState
import com.airpointer.remote.ui.theme.AirPointerTheme
import com.airpointer.remote.ui.theme.Palette
import com.github.takahirom.roborazzi.captureRoboImage
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/** Renders the redesigned components with Android's real graphics stack (no device needed). */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-night-xxhdpi")
class UiScreenshots {
    @get:Rule val compose = createAndroidComposeRule<ComponentActivity>()

    private fun shot(name: String, content: @androidx.compose.runtime.Composable () -> Unit) {
        compose.setContent { AirPointerTheme { Column(Modifier.background(Palette.Background).padding(20.dp)) { content() } } }
        compose.onRoot().captureRoboImage("build/screenshots/$name.png")
    }

    @Test fun connectionCardStates() = shot("connection-cards") {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            val base = LinkSnapshot(Method.WIFI, configured = true, computerName = "Office PC")
            ConnectionCard(connectionCardState(base.copy(connected = true, latencyMs = 9)), {})
            ConnectionCard(connectionCardState(base.copy(connecting = true)), {})
            ConnectionCard(connectionCardState(base), {})
        }
    }

    @Test fun errorStates() = shot("error-states") {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            ConnectionCard(connectionCardState(LinkSnapshot(Method.BLUETOOTH, configured = true, bluetoothOn = false)), {})
            ConnectionCard(connectionCardState(LinkSnapshot(Method.BLUETOOTH, configured = true, computerName = "Office PC", lost = true)), {})
            NotificationBanner("CONNECTION LOST", "Office PC is no longer reachable.", BannerTone.ERROR,
                primary = "Reconnect" to {}, secondary = "Settings" to {}, onDismiss = {})
        }
    }

    @Test fun presetsAndSettings() = shot("presets") {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(14.dp)) {
                RemoteCard(Icons.Rounded.Slideshow, "Presentation", "Slides, laser and air pointer", Modifier.weight(1f), badge = "Needs PC") {}
                RemoteCard(Icons.Rounded.Mouse, "PC Mouse", "Touchpad, air mouse, keyboard", Modifier.weight(1f)) {}
            }
            SetupItem(Icons.Rounded.Insights, "Diagnostics", "Link quality, sensors, event log") {}
        }
    }
}
