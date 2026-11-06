package com.airpointer.remote.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.transport.TransportKind
import com.airpointer.remote.transport.WifiCompanionClient
import com.airpointer.remote.ui.theme.Palette

data class LinkStatus(
    val transport: TransportKind,
    val connected: Boolean,
    val info: StatusInfo,
    val hostName: String?,
)

/** Status of whichever transport (Bluetooth HID or Wi-Fi companion) is selected. */
@Composable
fun rememberLinkStatus(graph: AppGraph, permissionsGranted: Boolean = true): LinkStatus {
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val hid by graph.hid.state.collectAsStateWithLifecycle()
    val wifi by graph.wifi.state.collectAsStateWithLifecycle()
    return if (settings.transport == TransportKind.WIFI) {
        val info = when (wifi.phase) {
            WifiCompanionClient.Phase.CONNECTED -> StatusInfo("Connected", "${wifi.serverName ?: wifi.host} · Wi-Fi" +
                (wifi.latencyMs?.let { " · $it ms" } ?: ""), Palette.Positive, true)
            WifiCompanionClient.Phase.CONNECTING -> StatusInfo("Connecting", "${wifi.host} · ${wifi.error ?: "Wi-Fi"}", Palette.Warning, true)
            WifiCompanionClient.Phase.FAILED -> StatusInfo("Not connected", wifi.error ?: "Wi-Fi connection failed", Palette.Negative, false)
            WifiCompanionClient.Phase.IDLE -> StatusInfo("Not connected", "Choose a computer running the Air Pointer companion.", Palette.TextSecondary, false)
        }
        LinkStatus(TransportKind.WIFI, wifi.phase == WifiCompanionClient.Phase.CONNECTED, info, wifi.serverName ?: wifi.host)
    } else {
        LinkStatus(TransportKind.BLUETOOTH, hid.connected, statusOf(hid, permissionsGranted), hid.host?.name)
    }
}
