package com.airpointer.remote.transport

import kotlinx.coroutines.flow.StateFlow
import java.util.concurrent.atomic.AtomicLong

/**
 * Destination for input reports (HID report layouts from [com.airpointer.remote.hid.HidDescriptor]).
 * Implemented by the Bluetooth HID controller and the Wi-Fi companion client, so every remote
 * mode (presentation, air mouse, touchpad, table mouse, media keys) works over either link.
 */
interface ReportSink {
    /** True when reports can be delivered right now. Read from the io thread. */
    val isConnected: Boolean
    val connectedFlow: StateFlow<Boolean>
    val reportsSent: AtomicLong
    val reportFailures: AtomicLong

    /** Send one input report. Called on the io thread. */
    fun sendReport(id: Int, data: ByteArray): Boolean
}

enum class TransportKind(val label: String) {
    BLUETOOTH("Bluetooth (no PC software)"),
    WIFI("Wi-Fi (desktop companion)"),
}
