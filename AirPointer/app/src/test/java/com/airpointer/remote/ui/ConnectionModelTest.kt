package com.airpointer.remote.ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ConnectionModelTest {
    private val bt = LinkSnapshot(Method.BLUETOOTH, configured = true, computerName = "Office PC")
    private val wifi = LinkSnapshot(Method.WIFI, configured = true, computerName = "Office PC")

    private fun check(s: LinkSnapshot, kind: CardKind, primary: CardAction?, secondary: CardAction? = null) {
        val c = connectionCardState(s)
        assertEquals(kind, c.kind); assertEquals(primary, c.primary); assertEquals(secondary, c.secondary)
    }

    @Test fun disconnected() = check(bt, CardKind.DISCONNECTED, CardAction.CONNECT, CardAction.CONNECTION_SETTINGS)
    @Test fun notSetUp() = check(bt.copy(configured = false), CardKind.NOT_SET_UP, CardAction.SET_UP)
    @Test fun connecting() = check(wifi.copy(connecting = true), CardKind.CONNECTING, CardAction.CANCEL)
    @Test fun reconnectingCountsAsConnecting() = check(bt.copy(reconnectAttempt = 2), CardKind.CONNECTING, CardAction.CANCEL)
    @Test fun connected() = check(wifi.copy(connected = true, latencyMs = 8), CardKind.CONNECTED, CardAction.OPEN_REMOTE, CardAction.DISCONNECT)
    @Test fun lost() = check(bt.copy(lost = true), CardKind.CONNECTION_LOST, CardAction.RECONNECT, CardAction.CONNECTION_SETTINGS)
    @Test fun pinRejected() = check(wifi.copy(pinRejected = true), CardKind.PAIRING_FAILED, CardAction.SET_UP)
    @Test fun bluetoothOff() = check(bt.copy(bluetoothOn = false), CardKind.BLUETOOTH_OFF, CardAction.ENABLE_BLUETOOTH, CardAction.USE_WIFI)
    @Test fun permission() = check(bt.copy(permissionGranted = false), CardKind.PERMISSION_NEEDED, CardAction.GRANT_PERMISSION, CardAction.USE_WIFI)
    @Test fun unsupported() = check(bt.copy(hidSupported = false), CardKind.UNSUPPORTED, CardAction.USE_WIFI, CardAction.TRY_AGAIN)
    @Test fun wifiUnavailable() = check(wifi.copy(wifiAvailable = false), CardKind.WIFI_UNAVAILABLE, CardAction.WIFI_SETTINGS)
    @Test fun serviceStopped() = check(bt.copy(serviceRunning = false), CardKind.SERVICE_STOPPED, CardAction.START_SERVICE)

    @Test fun bluetoothProblemsDoNotAffectWifi() =
        check(wifi.copy(bluetoothOn = false, hidSupported = false, permissionGranted = false), CardKind.DISCONNECTED, CardAction.CONNECT, CardAction.CONNECTION_SETTINGS)

    @Test fun connectedShowsNameMethodAndSignal() {
        val c = connectionCardState(wifi.copy(connected = true, latencyMs = 30))
        assertEquals("Office PC", c.computerName); assertEquals(Method.WIFI, c.method); assertEquals("Good signal", c.signal)
        assertNull(connectionCardState(bt.copy(connected = true)).signal) // Bluetooth HID reports no RSSI
    }
}
