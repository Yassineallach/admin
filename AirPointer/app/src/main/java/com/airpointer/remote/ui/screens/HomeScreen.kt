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
import androidx.compose.material.icons.rounded.Mouse
import androidx.compose.material.icons.rounded.PlayCircle
import androidx.compose.material.icons.rounded.PowerSettingsNew
import androidx.compose.material.icons.rounded.Slideshow
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material.icons.rounded.Tv
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
import com.airpointer.remote.transport.TransportKind
import com.airpointer.remote.ui.AppActions
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.components.IconBadge
import com.airpointer.remote.ui.components.Panel
import com.airpointer.remote.ui.components.PrimaryButton
import com.airpointer.remote.ui.components.ScreenScaffold
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.SectionLabel
import com.airpointer.remote.ui.components.StatusDot
import com.airpointer.remote.ui.rememberLinkStatus
import com.airpointer.remote.ui.theme.Palette

@Composable
fun HomeScreen(graph: AppGraph, actions: AppActions, navigate: (Route) -> Unit, onStart: () -> Unit, onStop: () -> Unit) {
    val s by graph.hid.state.collectAsStateWithLifecycle()
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val tvState by graph.tv.state.collectAsStateWithLifecycle()
    val link = rememberLinkStatus(graph, actions.permissionsGranted)
    val bt = settings.transport == TransportKind.BLUETOOTH

    ScreenScaffold(title = "", onBack = null, actions = {
        if (s.serviceRunning) IconButton(onClick = onStop) {
            Icon(Icons.Rounded.PowerSettingsNew, "Stop service", tint = Palette.TextTertiary)
        }
    }) {
        Text("AIR POINTER · REMOTE CONTROL CENTER", style = MaterialTheme.typography.labelSmall, color = Palette.Accent)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(link.info.title, style = MaterialTheme.typography.displayLarge, color = Palette.TextPrimary, modifier = Modifier.weight(1f))
            StatusDot(link.info.color, link.info.pulsing, 9.dp)
        }
        Text(link.info.detail, style = MaterialTheme.typography.bodyLarge, color = Palette.TextSecondary)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("PC link: ${if (bt) "Bluetooth" else "Wi-Fi"}", style = MaterialTheme.typography.labelMedium, color = Palette.TextTertiary,
                modifier = Modifier.weight(1f))
            SecondaryButton("Connection") { navigate(Route.PAIRING) }
        }
        Spacer(Modifier.height(4.dp))

        when {
            !actions.permissionsGranted && bt -> Panel {
                Text("Bluetooth permission", style = MaterialTheme.typography.titleMedium)
                Text("Bluetooth mode registers the phone as a mouse and keyboard, which needs the Nearby devices permission. Wi-Fi mode does not.",
                    style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
                PrimaryButton("Grant permission", Modifier.fillMaxWidth(), onClick = actions.requestPermissions)
            }
            bt && !s.bluetoothOn && s.adapterPresent -> Panel {
                Text("Bluetooth is off", style = MaterialTheme.typography.titleMedium)
                PrimaryButton("Turn on Bluetooth", Modifier.fillMaxWidth(), onClick = actions.enableBluetooth)
            }
            bt && s.support == Support.UNSUPPORTED -> Panel {
                Text("This phone cannot act as a Bluetooth mouse", style = MaterialTheme.typography.titleMedium, color = Palette.Negative)
                Text("The manufacturer disabled Android's Bluetooth HID Device profile. Switch the PC link to Wi-Fi and run the desktop companion instead.",
                    style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    SecondaryButton("Use Wi-Fi") { navigate(Route.PAIRING) }
                    SecondaryButton("Retry") { graph.hid.restart() }
                }
            }
            bt && !s.serviceRunning -> Panel {
                Text("Service stopped", style = MaterialTheme.typography.titleMedium)
                PrimaryButton("Start", Modifier.fillMaxWidth(), onClick = onStart)
            }
        }

        SectionLabel("Remote presets")
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            PresetTile(Icons.Rounded.Slideshow, "Presentation", "Slides, laser, air pointer", Modifier.weight(1f)) { navigate(Route.REMOTE) }
            PresetTile(Icons.Rounded.Mouse, "PC Mouse", "Air mouse · touchpad · table", Modifier.weight(1f)) { navigate(Route.PC_MOUSE) }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            PresetTile(Icons.Rounded.Tv, "TV Remote",
                graph.tvRepository.selected?.let { "${it.name} · ${tvStateLabel(tvState)}" } ?: "Android TV, Samsung, LG, IR",
                Modifier.weight(1f)) { navigate(Route.TV) }
            PresetTile(Icons.Rounded.PlayCircle, "Media Player", "VLC and MPV on your PC", Modifier.weight(1f)) { navigate(Route.MEDIA) }
        }

        SectionLabel("Setup")
        Tile(Icons.Rounded.BluetoothSearching, "Connection", "Bluetooth pairing or Wi-Fi companion") { navigate(Route.PAIRING) }
        Tile(Icons.Rounded.Tune, "Sensitivity & calibration", "Pointer speed, smoothing, drift, gestures") { navigate(Route.SETTINGS) }
        Tile(Icons.Rounded.Insights, "Diagnostics", "Links, sensors, live motion, log") { navigate(Route.DIAGNOSTICS) }
    }
}

private fun tvStateLabel(s: com.airpointer.remote.tv.TvConnState) = when (s) {
    com.airpointer.remote.tv.TvConnState.Connected -> "connected"
    com.airpointer.remote.tv.TvConnState.Connecting -> "connecting"
    is com.airpointer.remote.tv.TvConnState.NeedsUser -> "action needed"
    is com.airpointer.remote.tv.TvConnState.Failed -> "offline"
    com.airpointer.remote.tv.TvConnState.Disconnected -> "saved"
}

@Composable
private fun PresetTile(icon: ImageVector, title: String, subtitle: String, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier.height(132.dp).clip(RoundedCornerShape(24.dp)).background(Palette.Surface)
            .border(1.dp, Palette.Outline.copy(alpha = 0.6f), RoundedCornerShape(24.dp))
            .clickable(onClick = onClick).padding(16.dp),
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        IconBadge(icon, tint = Palette.Accent, bg = Palette.AccentDim)
        Column {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary, maxLines = 2)
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
        IconBadge(icon, tint = Palette.TextPrimary)
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        }
        Text("›", style = MaterialTheme.typography.titleLarge, color = Palette.TextTertiary)
    }
}
