package com.airpointer.remote.transport

import com.airpointer.remote.hid.BluetoothHidController
import com.airpointer.remote.settings.SettingsRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import java.util.concurrent.atomic.AtomicLong

/** Routes reports to the transport selected in settings (Bluetooth HID or Wi-Fi companion). */
class TransportRouter(
    private val bluetooth: BluetoothHidController,
    val wifi: WifiCompanionClient,
    private val settings: SettingsRepository,
    scope: CoroutineScope,
) : ReportSink {

    private val active: ReportSink
        get() = if (settings.current.transport == TransportKind.WIFI) wifi else bluetooth

    override val isConnected: Boolean get() = active.isConnected

    override val connectedFlow: StateFlow<Boolean> =
        combine(settings.settings, bluetooth.connectedFlow, wifi.connectedFlow) { s, bt, wf ->
            if (s.transport == TransportKind.WIFI) wf else bt
        }.stateIn(scope, SharingStarted.Eagerly, false)

    override val reportsSent: AtomicLong get() = active.reportsSent
    override val reportFailures: AtomicLong get() = active.reportFailures

    override fun sendReport(id: Int, data: ByteArray): Boolean = active.sendReport(id, data)
}
