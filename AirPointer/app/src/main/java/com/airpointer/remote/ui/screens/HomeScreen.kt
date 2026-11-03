package com.airpointer.remote.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.BluetoothSearching
import androidx.compose.material.icons.rounded.Insights
import androidx.compose.material.icons.rounded.PowerSettingsNew
import androidx.compose.material.icons.rounded.Slideshow
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.hid.BluetoothHidController.Support
import com.airpointer.remote.motion.SensorMotionSource
import com.airpointer.remote.ui.AppActions
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.components.Panel
import com.airpointer.remote.ui.components.PrimaryButton
import com.airpointer.remote.ui.components.ScreenScaffold
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.SectionLabel
import com.airpointer.remote.ui.components.StatusDot
import com.airpointer.remote.ui.statusOf
import com.airpointer.remote.ui.theme.Palette

@Composable
fun HomeScreen(graph: AppGraph, actions: AppActions, navigate: (Route) -> Unit, onStart: () -> Unit, onStop: () -> Unit) {
    val s by graph.hid.state.collectAsStateWithLifecycle()
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val status = statusOf(s, actions.permissionsGranted)

    ScreenScaffold(title = "", onBack = null, actions = {
        if (s.serviceRunning) IconButton(onClick = onStop) {
            Icon(Icons.Rounded.PowerSettingsNew, "Stop service", tint = Palette.TextTertiary)
        }
    }) {
        Text("AIR POINTER", style = MaterialTheme.typography.labelSmall, color = Palette.Accent)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(status.title, style = MaterialTheme.typography.displayLarge, color = Palette.TextPrimary, modifier = Modifier.weight(1f))
            StatusDot(status.color, status.pulsing, 9.dp)
        }
        Text(status.detail, style = MaterialTheme.typography.bodyLarge, color = Palette.TextSecondary)
        Spacer(Modifier.height(6.dp))

        when {
            !actions.permissionsGranted -> Panel {
                Text("Bluetooth permission", style = MaterialTheme.typography.titleMedium)
                Text("Air Pointer registers itself as a Bluetooth mouse and keyboard. Android requires the Nearby devices permission for that.",
                    style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
                PrimaryButton("Grant permission", Modifier.fillMaxWidth(), onClick = actions.requestPermissions)
            }
            !s.bluetoothOn && s.adapterPresent -> Panel {
                Text("Bluetooth is off", style = MaterialTheme.typography.titleMedium)
                PrimaryButton("Turn on Bluetooth", Modifier.fillMaxWidth(), onClick = actions.enableBluetooth)
            }
            s.support == Support.UNSUPPORTED -> Panel {
                Text("This phone cannot act as a Bluetooth mouse", style = MaterialTheme.typography.titleMedium, color = Palette.Negative)
                Text(
                    "Android's Bluetooth HID Device profile (Android 9+) is optional, and some manufacturers ship firmware with it disabled. " +
                        "Nothing in an app can enable it. The sensors and the motion preview in Diagnostics still work so you can test the pointer pipeline.",
                    style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    SecondaryButton("Retry") { graph.hid.restart() }
                    SecondaryButton("Diagnostics") { navigate(Route.DIAGNOSTICS) }
                }
            }
            !s.serviceRunning -> Panel {
                Text("Service stopped", style = MaterialTheme.typography.titleMedium)
                Text("Start the Bluetooth service to become visible as a mouse.", style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
                PrimaryButton("Start", Modifier.fillMaxWidth(), onClick = onStart)
            }
        }

        if (s.lastError != null && s.support != Support.UNSUPPORTED) Panel {
            Text("Last error", style = MaterialTheme.typography.labelSmall, color = Palette.Warning)
            Text(s.lastError!!, style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
            if (!s.registered) SecondaryButton("Retry registration") { graph.hid.restart() }
        }

        if (s.connected) {
            PrimaryButton("Open presentation remote", Modifier.fillMaxWidth()) { navigate(Route.REMOTE) }
            SecondaryButton("Disconnect", Modifier.fillMaxWidth()) { graph.hid.disconnect() }
        } else if (s.registered) {
            val last = settings.lastHostAddress
            if (last != null && s.reconnectAttempt == 0 && s.phase != com.airpointer.remote.hid.BluetoothHidController.Phase.CONNECTING) {
                PrimaryButton("Connect to ${settings.lastHostName ?: last}", Modifier.fillMaxWidth()) { graph.hid.connect(last) }
            } else if (last == null) {
                PrimaryButton("Pair a computer", Modifier.fillMaxWidth()) { navigate(Route.PAIRING) }
            }
        }

        SectionLabel("Navigate")
        Tile(Icons.Rounded.Slideshow, "Presentation remote", "Slides, clicks, pointer and gestures") { navigate(Route.REMOTE) }
        Tile(Icons.Rounded.BluetoothSearching, "Devices & pairing", "Make discoverable, pair, connect") { navigate(Route.PAIRING) }
        Tile(Icons.Rounded.Tune, "Sensitivity & calibration", "Speed, smoothing, drift, gestures") { navigate(Route.SETTINGS) }
        Tile(Icons.Rounded.Insights, "Diagnostics", "Bluetooth, sensors, live motion, log") { navigate(Route.DIAGNOSTICS) }

        if (graph.motion.capabilities.mode != SensorMotionSource.Mode.GYRO) Panel {
            Text("Limited motion sensors", style = MaterialTheme.typography.titleMedium, color = Palette.Warning)
            Text(
                if (graph.motion.capabilities.mode == SensorMotionSource.Mode.TILT_FALLBACK)
                    "No gyroscope found. Air Pointer falls back to tilt control (joystick-like), which is less precise."
                else "No motion sensors found. Buttons, gestures and keys still work.",
                style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary,
            )
        }
    }
}

@Composable
private fun Tile(icon: ImageVector, title: String, subtitle: String, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(Palette.Surface)
            .border(1.dp, Palette.Outline.copy(alpha = 0.6f), RoundedCornerShape(20.dp))
            .clickable(onClick = onClick).padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        com.airpointer.remote.ui.components.IconBadge(icon, tint = Palette.TextPrimary)
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        }
        Text("›", style = MaterialTheme.typography.titleLarge, color = Palette.TextTertiary)
    }
}
