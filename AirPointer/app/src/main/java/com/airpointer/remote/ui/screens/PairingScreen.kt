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
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.text.input.KeyboardType
import com.airpointer.remote.transport.CompanionDiscovery
import com.airpointer.remote.transport.TransportKind
import com.airpointer.remote.transport.WifiCompanionClient
import com.airpointer.remote.ui.components.Segmented
import kotlinx.coroutines.launch
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

    val settings by graph.settings.settings.collectAsStateWithLifecycle()

    ScreenScaffold("Connection", onBack) {
        Text("How should the phone reach your computer?", style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
        Segmented(TransportKind.entries.toList(), settings.transport, { if (it == TransportKind.WIFI) "Wi-Fi" else "Bluetooth" }) { t ->
            graph.settings.update { it.copy(transport = t) }
            if (t == TransportKind.WIFI) settings.let { st ->
                if (st.wifiHost != null && st.wifiPin != null) graph.wifi.connect(st.wifiHost, st.wifiPort, st.wifiPin)
            } else graph.wifi.disconnect()
        }
        Text(
            if (settings.transport == TransportKind.WIFI)
                "Wi-Fi: works with every phone and every Windows/Linux PC, lowest latency, adds MPV control. Needs the small Air Pointer Companion running on the PC."
            else "Bluetooth: no software on the PC — the phone appears as a mouse and keyboard. Needs a phone whose firmware supports the HID Device profile.",
            style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary,
        )
        if (settings.transport == TransportKind.WIFI) WifiSection(graph) else {
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
}

@Composable
private fun WifiSection(graph: AppGraph) {
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val wifi by graph.wifi.state.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()
    var scanning by remember { mutableStateOf(false) }
    var found by remember { mutableStateOf<List<CompanionDiscovery.Found>>(emptyList()) }
    var pinFor by remember { mutableStateOf<Pair<String, Int>?>(null) }
    var pinName by remember { mutableStateOf<String?>(null) }
    var manualHost by remember { mutableStateOf(settings.wifiHost ?: "") }

    fun scan() {
        scanning = true
        scope.launch { found = graph.companionDiscovery.scan(); scanning = false }
    }
    LaunchedEffect(Unit) { if (wifi.phase != WifiCompanionClient.Phase.CONNECTED) scan() }

    SectionLabel("Computer")
    Panel {
        when (wifi.phase) {
            WifiCompanionClient.Phase.CONNECTED -> {
                Text("Connected to ${wifi.serverName}", style = MaterialTheme.typography.titleMedium, color = Palette.Positive)
                Text("${wifi.host}:${wifi.port} · ${wifi.serverOs} · ${wifi.latencyMs?.let { "$it ms" } ?: "…"} · " +
                    wifi.features.joinToString(), style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                if ("mouse" !in wifi.features) Text("The companion runs in media-only mode: input injection is not permitted on that computer (see the companion window).",
                    style = MaterialTheme.typography.bodySmall, color = Palette.Warning)
                SecondaryButton("Disconnect") { graph.wifi.disconnect() }
            }
            WifiCompanionClient.Phase.CONNECTING -> Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                CircularProgressIndicator(Modifier.size(20.dp), color = Palette.Accent, strokeWidth = 2.dp)
                Text("Connecting to ${wifi.host}… ${wifi.error ?: ""}", style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
            }
            else -> {
                Text("Not connected", style = MaterialTheme.typography.titleMedium)
                wifi.error?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = Palette.Negative) }
            }
        }
    }

    SectionLabel("Computers on this network")
    if (!scanning && found.isEmpty() && wifi.phase != WifiCompanionClient.Phase.CONNECTED) {
        com.airpointer.remote.ui.components.NotificationBanner(
            title = "NO COMPUTER FOUND",
            message = "Make sure the Air Pointer Companion is running on your PC and both devices are on the same Wi-Fi " +
                "(guest networks often hide devices). You can also type the address shown in the companion window below.",
            tone = com.airpointer.remote.ui.components.BannerTone.WARNING,
            primary = "Scan again" to { scan() },
        )
    }
    Panel {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(if (scanning) "Searching…" else if (found.isEmpty()) "None found yet." else "${found.size} found",
                style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary, modifier = Modifier.weight(1f))
            if (scanning) CircularProgressIndicator(Modifier.size(20.dp), color = Palette.Accent, strokeWidth = 2.dp)
            else SecondaryButton("Scan") { scan() }
        }
        found.forEach { f ->
            Divider()
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                IconBadge(Icons.Rounded.Computer, tint = Palette.Accent)
                Column(Modifier.weight(1f)) {
                    Text(f.name, style = MaterialTheme.typography.titleMedium)
                    Text("${f.host}:${f.port}", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                }
                SecondaryButton("Connect") { pinFor = f.host to f.port; pinName = f.name }
            }
        }
        Divider()
        Text("Or enter the address shown in the companion window", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedTextField(manualHost, { manualHost = it }, Modifier.weight(1f), singleLine = true,
                placeholder = { Text("192.168.1.20") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
            SecondaryButton("Next", enabled = manualHost.isNotBlank()) {
                val parts = manualHost.trim().split(':')
                pinFor = parts[0] to (parts.getOrNull(1)?.toIntOrNull() ?: WifiCompanionClient.DEFAULT_PORT); pinName = null
            }
        }
    }

    SectionLabel("Set up the companion (once)")
    Panel {
        Text("1. Copy the companion to the PC: AirPointerCompanion-windows-amd64.exe (Windows) or airpointer-companion-linux-amd64 (Linux), from the project's dist folder.",
            style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        Text("2. Run it. Allow it through the firewall on private networks. It shows the computer's address and a 6-digit PIN.",
            style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        Text("3. Keep the phone and the PC on the same Wi-Fi network. Guest networks often block devices from seeing each other.",
            style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
    }

    pinFor?.let { (host, port) ->
        var pin by remember { mutableStateOf(if (settings.wifiHost == host) settings.wifiPin.orEmpty() else "") }
        AlertDialog(
            onDismissRequest = { pinFor = null },
            containerColor = Palette.SurfaceHigh,
            title = { Text("PIN for ${pinName ?: host}") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Enter the 6-digit PIN shown in the companion window.", style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
                    OutlinedTextField(pin, { v -> pin = v.filter { it.isDigit() }.take(6) }, singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword))
                }
            },
            confirmButton = {
                TextButton(enabled = pin.length == 6, onClick = {
                    graph.settings.update { it.copy(transport = TransportKind.WIFI, wifiHost = host, wifiPort = port, wifiPin = pin, wifiName = pinName) }
                    graph.wifi.connect(host, port, pin)
                    pinFor = null
                }) { Text("Connect", color = Palette.Accent) }
            },
            dismissButton = { TextButton(onClick = { pinFor = null }) { Text("Cancel", color = Palette.TextSecondary) } },
        )
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
