package com.airpointer.remote.ui

import androidx.compose.ui.graphics.Color
import com.airpointer.remote.hid.BluetoothHidController
import com.airpointer.remote.hid.BluetoothHidController.Phase
import com.airpointer.remote.hid.BluetoothHidController.Support
import com.airpointer.remote.ui.theme.Palette

data class StatusInfo(val title: String, val detail: String, val color: Color, val pulsing: Boolean)

fun statusOf(s: BluetoothHidController.State, permissionsGranted: Boolean): StatusInfo = when {
    !s.adapterPresent -> StatusInfo("No Bluetooth", "This device has no Bluetooth hardware.", Palette.Negative, false)
    !permissionsGranted -> StatusInfo("Permission needed", "Allow Nearby devices so Air Pointer can act as a Bluetooth mouse.", Palette.Warning, false)
    !s.bluetoothOn -> StatusInfo("Bluetooth is off", "Turn on Bluetooth to start.", Palette.Warning, false)
    s.support == Support.UNSUPPORTED -> StatusInfo("Not supported", s.unsupportedReason ?: "HID peripheral mode unavailable.", Palette.Negative, false)
    s.phase == Phase.CONNECTED -> StatusInfo("Connected", s.host?.name ?: "Computer", Palette.Positive, true)
    s.phase == Phase.CONNECTING -> StatusInfo("Connecting", s.host?.name ?: "Computer", Palette.Warning, true)
    s.reconnectAttempt > 0 -> StatusInfo("Reconnecting", "${s.host?.name ?: "Last computer"} · attempt ${s.reconnectAttempt}", Palette.Warning, true)
    s.phase == Phase.DISCONNECTING -> StatusInfo("Disconnecting", s.host?.name ?: "", Palette.TextSecondary, false)
    s.registered -> StatusInfo("Ready", "Waiting for a computer to connect.", Palette.TextSecondary, true)
    s.support == Support.CHECKING || s.phase == Phase.REGISTERING -> StatusInfo("Starting", "Registering as a Bluetooth mouse…", Palette.TextSecondary, true)
    !s.serviceRunning -> StatusInfo("Stopped", "The Bluetooth service is not running.", Palette.TextTertiary, false)
    else -> StatusInfo("Idle", "Preparing Bluetooth…", Palette.TextTertiary, false)
}
