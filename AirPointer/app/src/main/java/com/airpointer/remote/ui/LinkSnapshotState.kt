package com.airpointer.remote.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.hid.BluetoothHidController
import com.airpointer.remote.transport.TransportKind
import com.airpointer.remote.transport.WifiCompanionClient

/** Collects the Bluetooth / Wi-Fi controllers into the transport-independent [LinkSnapshot]. */
@Composable
fun rememberLinkSnapshot(graph: AppGraph, permissionsGranted: Boolean): LinkSnapshot {
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val hid by graph.hid.state.collectAsStateWithLifecycle()
    val wifi by graph.wifi.state.collectAsStateWithLifecycle()
    val lost by graph.linkMonitor.lost.collectAsStateWithLifecycle()
    val wifiAvailable by graph.linkMonitor.wifiAvailable.collectAsStateWithLifecycle()
    return if (settings.transport == TransportKind.WIFI) LinkSnapshot(
        method = Method.WIFI,
        connected = wifi.phase == WifiCompanionClient.Phase.CONNECTED,
        connecting = wifi.phase == WifiCompanionClient.Phase.CONNECTING,
        computerName = wifi.serverName ?: settings.wifiName ?: settings.wifiHost,
        configured = settings.wifiHost != null && settings.wifiPin != null,
        latencyMs = wifi.latencyMs,
        error = wifi.error,
        wifiAvailable = wifiAvailable,
        pinRejected = wifi.phase == WifiCompanionClient.Phase.FAILED && wifi.error?.contains("PIN") == true,
        lost = lost,
    ) else LinkSnapshot(
        method = Method.BLUETOOTH,
        connected = hid.connected,
        connecting = hid.phase == BluetoothHidController.Phase.CONNECTING,
        computerName = hid.host?.name ?: settings.lastHostName,
        configured = settings.lastHostAddress != null,
        reconnectAttempt = hid.reconnectAttempt,
        error = hid.lastError,
        permissionGranted = permissionsGranted,
        bluetoothOn = hid.bluetoothOn || !hid.adapterPresent,
        hidSupported = hid.adapterPresent && hid.support != BluetoothHidController.Support.UNSUPPORTED,
        serviceRunning = hid.serviceRunning,
        lost = lost,
    )
}

/** Toolbar status for remote screens. */
fun LinkSnapshot.toolbarStatus(): Pair<Tone, String> = when {
    connected -> Tone.SUCCESS to "CONNECTED · ${(computerName ?: method.label).uppercase()}"
    connecting || reconnectAttempt > 0 -> Tone.PROGRESS to "CONNECTING"
    lost -> Tone.ERROR to "CONNECTION LOST"
    else -> Tone.NEUTRAL to "NOT CONNECTED"
}
