package com.airpointer.remote.ui.screens

import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Computer
import androidx.compose.material.icons.rounded.Devices
import androidx.compose.material.icons.rounded.Headphones
import androidx.compose.material.icons.rounded.Smartphone
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.hid.BluetoothHidController.Phase
import com.airpointer.remote.hid.BluetoothPairingManager
import com.airpointer.remote.ui.AppActions
import com.airpointer.remote.ui.components.Divider
import com.airpointer.remote.ui.components.IconBadge
import com.airpointer.remote.ui.components.Panel
import com.airpointer.remote.ui.components.PrimaryButton
import com.airpointer.remote.ui.components.ScreenScaffold
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.SectionLabel
import com.airpointer.remote.ui.theme.Palette

@Composable
fun PairingScreen(graph: AppGraph, actions: AppActions, onBack: () -> Unit) {
    val pairing = graph.pairing
    val p by pairing.state.collectAsStateWithLifecycle()
    val hid by graph.hid.state.collectAsStateWithLifecycle()
    val context = LocalContext.current

    DisposableEffect(Unit) {
        pairing.attach()
        onDispose { pairing.detach() }
    }

    ScreenScaffold("Devices & pairing", onBack) {
        if (!hid.registered) Panel {
            Text("Bluetooth HID is not ready", style = MaterialTheme.typography.titleMedium, color = Palette.Warning)
            Text(hid.unsupportedReason ?: hid.lastError ?: "Wait for the status on the home screen to read \"Ready\" before pairing. " +
                "Windows reads the mouse service only while Air Pointer is registered.",
                style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
        }

        SectionLabel("Option A — pair from the computer (recommended)")
        Panel {
            Text("1. Make “${pairing.localName}” visible", style = MaterialTheme.typography.titleMedium)
            Text(if (p.discoverable) "Visible to nearby computers now." else "Phones are hidden by default. Make it visible for 3 minutes.",
                style = MaterialTheme.typography.bodyMedium, color = if (p.discoverable) Palette.Positive else Palette.TextSecondary)
            PrimaryButton(if (p.discoverable) "Visible — extend" else "Make visible", Modifier.fillMaxWidth(), onClick = actions.makeDiscoverable)
            Divider()
            Text("2. On Windows", style = MaterialTheme.typography.titleMedium)
            Text(
                "Settings → Bluetooth & devices → Add device → Bluetooth, then choose “${pairing.localName}”. " +
                    "Confirm the same code on both screens. Windows installs it as a mouse and keyboard and connects automatically.",
                style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary,
            )
            Text(
                "Already paired before installing Air Pointer? Remove the phone on the PC and the PC on the phone, then pair again — " +
                    "Windows caches the old service list and will not see the mouse otherwise.",
                style = MaterialTheme.typography.bodySmall, color = Palette.Warning,
            )
        }

        SectionLabel("Paired devices")
        Panel {
            if (p.bonded.isEmpty()) Text("No paired devices yet.", style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
            p.bonded.forEachIndexed { i, d ->
                if (i > 0) Divider()
                val isHost = hid.host?.address == d.address
                val connected = isHost && hid.connected
                val connecting = isHost && hid.phase == Phase.CONNECTING
                DeviceRow(d, status = when {
                    connected -> "Connected"
                    connecting -> "Connecting…"
                    else -> d.kind.label
                }) {
                    when {
                        connected -> SecondaryButton("Disconnect") { graph.hid.disconnect() }
                        connecting -> CircularProgressIndicator(Modifier.size(22.dp), color = Palette.Accent, strokeWidth = 2.dp)
                        else -> SecondaryButton("Connect", enabled = hid.registered) { graph.hid.connect(d.address) }
                    }
                }
            }
            TextButton(onClick = {
                context.startActivity(Intent(Settings.ACTION_BLUETOOTH_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }) { Text("Manage / forget in Android settings", color = Palette.TextSecondary) }
        }

        SectionLabel("Option B — find the computer from the phone")
        Panel {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Nearby devices", style = MaterialTheme.typography.titleMedium)
                    Text("The computer must be visible (Windows: keep the Bluetooth settings page open).",
                        style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                }
                if (p.scanning) CircularProgressIndicator(Modifier.size(22.dp), color = Palette.Accent, strokeWidth = 2.dp)
            }
            if (p.message != null) Text(p.message!!, style = MaterialTheme.typography.bodySmall, color = Palette.Warning)
            SecondaryButton(if (p.scanning) "Stop scanning" else "Scan", Modifier.fillMaxWidth()) {
                if (p.scanning) pairing.stopScan() else pairing.startScan()
            }
            p.discovered.forEach { d ->
                Divider()
                DeviceRow(d, status = buildString {
                    append(d.kind.label)
                    d.rssi?.let { append(" · $it dBm") }
                }) {
                    if (p.bondingAddress == d.address) CircularProgressIndicator(Modifier.size(22.dp), color = Palette.Accent, strokeWidth = 2.dp)
                    else SecondaryButton("Pair", enabled = hid.registered) {
                        pairing.pair(d.address) { addr -> graph.hid.connect(addr) }
                    }
                }
            }
        }
    }
}

@Composable
private fun DeviceRow(d: BluetoothPairingManager.Device, status: String, trailing: @Composable () -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        IconBadge(
            when (d.kind) {
                BluetoothPairingManager.Kind.COMPUTER -> Icons.Rounded.Computer
                BluetoothPairingManager.Kind.PHONE -> Icons.Rounded.Smartphone
                BluetoothPairingManager.Kind.AUDIO -> Icons.Rounded.Headphones
                else -> Icons.Rounded.Devices
            },
            tint = if (d.kind == BluetoothPairingManager.Kind.COMPUTER) Palette.Accent else Palette.TextSecondary,
        )
        Column(Modifier.weight(1f)) {
            Text(d.name, style = MaterialTheme.typography.titleMedium, maxLines = 1)
            Text(status, style = MaterialTheme.typography.bodySmall, color = if (status == "Connected") Palette.Positive else Palette.TextSecondary)
        }
        trailing()
    }
}
