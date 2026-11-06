package com.airpointer.remote.hid

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothHidDevice
import android.bluetooth.BluetoothHidDeviceAppQosSettings
import android.bluetooth.BluetoothHidDeviceAppSdpSettings
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.SystemClock
import androidx.core.content.ContextCompat
import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.airpointer.remote.settings.SettingsRepository
import com.airpointer.remote.transport.ReportSink
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import java.util.concurrent.Executor
import java.util.concurrent.atomic.AtomicLong

/**
 * Owns the Android Bluetooth HID Device profile (API 28+): obtains the profile proxy, registers
 * the SDP record + report descriptor, tracks the host connection, reconnects, and sends reports.
 *
 * All HID callbacks are delivered on the [io] thread, and [sendReport] must be called from it,
 * which keeps report ordering strict without locks.
 */
@SuppressLint("MissingPermission") // every entry point checks hasConnectPermission()
class BluetoothHidController(
    private val context: Context,
    private val io: Handler,
    private val log: DiagnosticsLog,
    private val settings: SettingsRepository,
    scope: CoroutineScope,
) : ReportSink {
    enum class Support { UNKNOWN, CHECKING, SUPPORTED, UNSUPPORTED }
    enum class Phase { IDLE, REGISTERING, READY, CONNECTING, CONNECTED, DISCONNECTING }

    data class Host(val name: String, val address: String)

    data class State(
        val adapterPresent: Boolean = true,
        val bluetoothOn: Boolean = false,
        val permissionGranted: Boolean = false,
        val serviceRunning: Boolean = false,
        val support: Support = Support.UNKNOWN,
        val unsupportedReason: String? = null,
        val registered: Boolean = false,
        val phase: Phase = Phase.IDLE,
        val host: Host? = null,
        val reconnectAttempt: Int = 0,
        val lastError: String? = null,
        val bootProtocol: Boolean = false,
        val connectedSinceMs: Long = 0L,
    ) {
        val connected get() = phase == Phase.CONNECTED
    }

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state

    override val reportsSent = AtomicLong()
    override val reportFailures = AtomicLong()
    override val connectedFlow: StateFlow<Boolean> =
        _state.map { it.connected }.stateIn(scope, SharingStarted.Eagerly, false)

    private val adapter: BluetoothAdapter? =
        context.getSystemService(BluetoothManager::class.java)?.adapter

    @Volatile private var hid: BluetoothHidDevice? = null
    @Volatile private var connectedDevice: BluetoothDevice? = null
    @Volatile private var started = false
    private var userDisconnect = false
    private var reconnectAttempts = 0
    private var reconnectTarget: BluetoothDevice? = null
    private var proxyRequested = false

    private val executor = Executor { io.post(it) }

    // ------------------------------------------------------------------ lifecycle

    fun hasConnectPermission(): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.S ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_CONNECT) ==
            PackageManager.PERMISSION_GRANTED

    /** Called by the foreground service when it starts. Main thread. */
    fun start() {
        if (started) return
        started = true
        _state.update { it.copy(serviceRunning = true) }
        ContextCompat.registerReceiver(
            context, adapterReceiver, IntentFilter(BluetoothAdapter.ACTION_STATE_CHANGED),
            ContextCompat.RECEIVER_NOT_EXPORTED,
        )
        refresh()
    }

    /** Re-evaluate permissions / adapter state (e.g. after the user granted a permission). Any thread. */
    fun refresh() {
        io.post { refreshInternal() }
    }

    private fun refreshInternal() {
        val a = adapter
        if (a == null) {
            _state.update {
                it.copy(adapterPresent = false, support = Support.UNSUPPORTED,
                    unsupportedReason = "This device has no Bluetooth adapter.")
            }
            return
        }
        val perm = hasConnectPermission()
        val on = try { a.isEnabled } catch (_: SecurityException) { false }
        _state.update { it.copy(permissionGranted = perm, bluetoothOn = on) }
        if (started && perm && on && hid == null && !proxyRequested) acquireProxy()
    }

    /** Called by the foreground service when it stops. Main thread. */
    fun stop() {
        if (!started) return
        started = false
        try { context.unregisterReceiver(adapterReceiver) } catch (_: IllegalArgumentException) {}
        io.post {
            cancelReconnect()
            releaseProxy(unregister = true)
            _state.update { it.copy(serviceRunning = false, registered = false, phase = Phase.IDLE, host = null) }
            log.i(TAG, "HID service stopped")
        }
    }

    /** Tear down and register again (user pressed "Retry"). */
    fun restart() {
        io.post {
            releaseProxy(unregister = true)
            _state.update { it.copy(support = Support.UNKNOWN, unsupportedReason = null, lastError = null) }
            refreshInternal()
        }
    }

    private fun acquireProxy() {
        val a = adapter ?: return
        proxyRequested = true
        _state.update { it.copy(support = Support.CHECKING) }
        log.i(TAG, "Requesting HID Device profile proxy")
        val ok = try {
            a.getProfileProxy(context, profileListener, BluetoothProfile.HID_DEVICE)
        } catch (e: SecurityException) {
            log.e(TAG, "getProfileProxy: ${e.message}")
            false
        }
        if (!ok) {
            proxyRequested = false
            markUnsupported("The Bluetooth HID Device profile is not available on this phone. " +
                "The manufacturer has disabled the HID peripheral role in the firmware.")
            return
        }
        io.postDelayed(proxyTimeout, PROXY_TIMEOUT_MS)
    }

    private val proxyTimeout = Runnable {
        if (hid == null && proxyRequested) {
            proxyRequested = false
            markUnsupported("The HID Device profile did not respond. This phone's Bluetooth stack " +
                "most likely does not implement the HID peripheral role.")
        }
    }

    private fun markUnsupported(reason: String) {
        log.e(TAG, reason)
        _state.update { it.copy(support = Support.UNSUPPORTED, unsupportedReason = reason, registered = false, phase = Phase.IDLE) }
    }

    private val profileListener = object : BluetoothProfile.ServiceListener {
        override fun onServiceConnected(profile: Int, proxy: BluetoothProfile) {
            if (profile != BluetoothProfile.HID_DEVICE) return
            io.post {
                io.removeCallbacks(proxyTimeout)
                if (!started) {
                    adapter?.closeProfileProxy(BluetoothProfile.HID_DEVICE, proxy)
                    proxyRequested = false
                    return@post
                }
                hid = proxy as BluetoothHidDevice
                _state.update { it.copy(support = Support.SUPPORTED, unsupportedReason = null) }
                log.i(TAG, "HID Device profile proxy connected")
                registerApp()
            }
        }

        override fun onServiceDisconnected(profile: Int) {
            if (profile != BluetoothProfile.HID_DEVICE) return
            io.post {
                log.w(TAG, "HID Device profile proxy disconnected")
                hid = null
                proxyRequested = false
                connectedDevice = null
                _state.update { it.copy(registered = false, phase = Phase.IDLE) }
            }
        }
    }

    private fun registerApp() {
        val h = hid ?: return
        if (!hasConnectPermission()) return
        val sdp = BluetoothHidDeviceAppSdpSettings(
            SDP_NAME, SDP_DESCRIPTION, SDP_PROVIDER,
            BluetoothHidDevice.SUBCLASS1_COMBO, HidDescriptor.DESCRIPTOR,
        )
        // Same QoS the AOSP sample / WearMouse use: best effort, ~11 ms latency target.
        val qos = BluetoothHidDeviceAppQosSettings(
            BluetoothHidDeviceAppQosSettings.SERVICE_BEST_EFFORT, 800, 9, 0, 11250,
            BluetoothHidDeviceAppQosSettings.MAX,
        )
        _state.update { it.copy(phase = Phase.REGISTERING, lastError = null) }
        val ok = try { h.registerApp(sdp, null, qos, executor, hidCallback) } catch (e: SecurityException) {
            log.e(TAG, "registerApp: ${e.message}"); false
        }
        if (!ok) {
            fail("Registration was rejected. Another app (keyboard/mouse emulator) may own the " +
                "HID Device role — only one app can hold it at a time. Close it and press Retry.")
            _state.update { it.copy(phase = Phase.IDLE) }
        } else {
            log.i(TAG, "registerApp() requested")
        }
    }

    private fun releaseProxy(unregister: Boolean) {
        io.removeCallbacks(proxyTimeout)
        val h = hid
        hid = null
        proxyRequested = false
        connectedDevice = null
        if (h != null && hasConnectPermission()) {
            try {
                if (unregister) h.unregisterApp()
            } catch (e: Exception) {
                log.w(TAG, "unregisterApp: ${e.message}")
            }
            try { adapter?.closeProfileProxy(BluetoothProfile.HID_DEVICE, h) } catch (_: Exception) {}
        }
        _state.update { it.copy(registered = false, phase = Phase.IDLE) }
    }

    // ------------------------------------------------------------------ HID callback

    private val hidCallback = object : BluetoothHidDevice.Callback() {
        override fun onAppStatusChanged(pluggedDevice: BluetoothDevice?, registered: Boolean) {
            log.i(TAG, "App status: registered=$registered plugged=${pluggedDevice?.address}")
            if (registered) {
                _state.update { it.copy(registered = true, phase = if (it.connected) it.phase else Phase.READY, lastError = null) }
                val s = settings.current
                val target = pluggedDevice ?: s.lastHostAddress?.let { addr -> device(addr) }
                if (target != null && s.autoReconnect && connectedDevice == null) {
                    log.i(TAG, "Auto-connecting to ${label(target)}")
                    connectInternal(target)
                }
            } else {
                val wasRegistered = _state.value.registered
                connectedDevice = null
                _state.update { it.copy(registered = false, phase = Phase.IDLE, host = null) }
                if (started) {
                    fail(if (wasRegistered) "The HID registration was revoked by the system (another app may have registered)."
                    else "The system refused to register the HID app. Another app may own the HID Device role.")
                }
            }
        }

        override fun onConnectionStateChanged(device: BluetoothDevice, state: Int) {
            val host = Host(label(device), device.address)
            when (state) {
                BluetoothProfile.STATE_CONNECTING -> {
                    log.i(TAG, "Connecting to ${host.name}")
                    _state.update { it.copy(phase = Phase.CONNECTING, host = host) }
                }
                BluetoothProfile.STATE_CONNECTED -> {
                    io.removeCallbacks(connectTimeout)
                    connectedDevice = device
                    userDisconnect = false
                    cancelReconnect()
                    log.i(TAG, "Connected to ${host.name} (${host.address})")
                    _state.update {
                        it.copy(phase = Phase.CONNECTED, host = host, reconnectAttempt = 0,
                            lastError = null, connectedSinceMs = System.currentTimeMillis())
                    }
                    settings.update { it.copy(lastHostAddress = host.address, lastHostName = host.name) }
                }
                BluetoothProfile.STATE_DISCONNECTING -> {
                    _state.update { it.copy(phase = Phase.DISCONNECTING) }
                }
                BluetoothProfile.STATE_DISCONNECTED -> {
                    io.removeCallbacks(connectTimeout)
                    val current = connectedDevice
                    if (current != null && current.address != device.address) return
                    connectedDevice = null
                    log.i(TAG, "Disconnected from ${host.name}${if (userDisconnect) " (by user)" else ""}")
                    _state.update {
                        it.copy(phase = if (it.registered) Phase.READY else Phase.IDLE,
                            host = if (userDisconnect) null else it.host, bootProtocol = false)
                    }
                    if (!userDisconnect && started && settings.current.autoReconnect) scheduleReconnect(device)
                }
            }
        }

        override fun onGetReport(device: BluetoothDevice, type: Byte, id: Byte, bufferSize: Int) {
            val h = hid ?: return
            if (type == BluetoothHidDevice.REPORT_TYPE_INPUT) {
                val data = when (id.toInt()) {
                    HidDescriptor.REPORT_ID_MOUSE -> ByteArray(HidDescriptor.MOUSE_REPORT_SIZE)
                    HidDescriptor.REPORT_ID_KEYBOARD -> ByteArray(HidDescriptor.KEYBOARD_REPORT_SIZE)
                    else -> null
                }
                if (data != null) { h.replyReport(device, type, id, data); return }
            }
            h.reportError(device, BluetoothHidDevice.ERROR_RSP_UNSUPPORTED_REQ)
        }

        override fun onSetReport(device: BluetoothDevice, type: Byte, id: Byte, data: ByteArray?) {
            hid?.reportError(device, BluetoothHidDevice.ERROR_RSP_SUCCESS)
        }

        override fun onSetProtocol(device: BluetoothDevice, protocol: Byte) {
            val boot = protocol == BluetoothHidDevice.PROTOCOL_BOOT_MODE
            log.i(TAG, "Host set protocol: ${if (boot) "BOOT" else "REPORT"}")
            _state.update { it.copy(bootProtocol = boot) }
        }

        override fun onInterruptData(device: BluetoothDevice, reportId: Byte, data: ByteArray?) {
            // Output reports (e.g. keyboard LEDs) — not used.
        }

        override fun onVirtualCableUnplug(device: BluetoothDevice) {
            log.w(TAG, "Virtual cable unplugged by ${label(device)} — host removed this device")
            connectedDevice = null
            cancelReconnect()
            _state.update { it.copy(phase = if (it.registered) Phase.READY else Phase.IDLE, host = null) }
            if (settings.current.lastHostAddress == device.address) {
                settings.update { it.copy(lastHostAddress = null, lastHostName = null) }
            }
        }
    }

    // ------------------------------------------------------------------ connection control

    fun connect(address: String) = io.post {
        val d = device(address) ?: return@post fail("Unknown device $address")
        userDisconnect = false
        cancelReconnect()
        connectInternal(d)
    }

    fun disconnect() = io.post {
        userDisconnect = true
        cancelReconnect()
        io.removeCallbacks(connectTimeout)
        val h = hid
        val d = connectedDevice ?: hid?.let { _ -> _state.value.host?.address?.let { device(it) } }
        if (h != null && d != null && hasConnectPermission()) {
            log.i(TAG, "Disconnect requested")
            try { h.disconnect(d) } catch (e: SecurityException) { fail("disconnect: ${e.message}") }
        }
        _state.update { it.copy(phase = if (it.registered) Phase.READY else Phase.IDLE, host = null, reconnectAttempt = 0) }
    }

    private fun connectInternal(d: BluetoothDevice) {
        val h = hid ?: return fail("HID profile not ready yet")
        if (!hasConnectPermission()) return fail("Bluetooth permission missing")
        val current = connectedDevice
        if (current != null && current.address == d.address) return
        if (current != null) {
            try { h.disconnect(current) } catch (_: SecurityException) {}
        }
        _state.update { it.copy(phase = Phase.CONNECTING, host = Host(label(d), d.address), lastError = null) }
        val ok = try { h.connect(d) } catch (e: SecurityException) { false }
        if (!ok) {
            _state.update { it.copy(phase = if (it.registered) Phase.READY else Phase.IDLE) }
            fail("connect() was refused by the Bluetooth stack.")
            return
        }
        io.removeCallbacks(connectTimeout)
        io.postDelayed(connectTimeout, CONNECT_TIMEOUT_MS)
    }

    private val connectTimeout = Runnable {
        if (_state.value.phase == Phase.CONNECTING) {
            log.w(TAG, "Connection attempt timed out")
            _state.update {
                it.copy(phase = if (it.registered) Phase.READY else Phase.IDLE,
                    lastError = "The computer did not accept the connection. Check that it is on, in range, " +
                        "and that the phone was paired while Air Pointer was running.")
            }
            reconnectTarget?.let { scheduleReconnect(it) }
        }
    }

    private fun scheduleReconnect(d: BluetoothDevice) {
        if (reconnectAttempts >= RECONNECT_DELAYS_MS.size) {
            log.w(TAG, "Gave up reconnecting after $reconnectAttempts attempts")
            reconnectAttempts = 0
            reconnectTarget = null
            _state.update { it.copy(reconnectAttempt = 0, host = null) }
            return
        }
        reconnectTarget = d
        val delay = RECONNECT_DELAYS_MS[reconnectAttempts]
        reconnectAttempts++
        val attempt = reconnectAttempts
        _state.update { it.copy(reconnectAttempt = attempt) }
        log.i(TAG, "Reconnect attempt $attempt in ${delay / 1000}s")
        io.removeCallbacks(reconnectRunnable)
        io.postDelayed(reconnectRunnable, delay)
    }

    private val reconnectRunnable = Runnable {
        val d = reconnectTarget ?: return@Runnable
        if (connectedDevice != null || !_state.value.registered) return@Runnable
        connectInternal(d)
    }

    private fun cancelReconnect() {
        io.removeCallbacks(reconnectRunnable)
        reconnectAttempts = 0
        reconnectTarget = null
        _state.update { it.copy(reconnectAttempt = 0) }
    }

    // ------------------------------------------------------------------ reports

    /** Send an input report. Must be called on the io thread. */
    override fun sendReport(id: Int, data: ByteArray): Boolean {
        val h = hid ?: return false
        val d = connectedDevice ?: return false
        val ok = try { h.sendReport(d, id, data) } catch (e: SecurityException) { false }
        if (ok) reportsSent.incrementAndGet() else reportFailures.incrementAndGet()
        return ok
    }

    override val isConnected: Boolean get() = connectedDevice != null

    // ------------------------------------------------------------------ helpers

    private fun fail(msg: String) {
        log.e(TAG, msg)
        _state.update { it.copy(lastError = msg) }
    }

    private fun device(address: String): BluetoothDevice? =
        try { adapter?.getRemoteDevice(address) } catch (_: IllegalArgumentException) { null }

    private fun label(d: BluetoothDevice): String =
        (try { d.name } catch (_: SecurityException) { null }) ?: d.address

    private val adapterReceiver = object : BroadcastReceiver() {
        override fun onReceive(c: Context, intent: Intent) {
            when (intent.getIntExtra(BluetoothAdapter.EXTRA_STATE, BluetoothAdapter.ERROR)) {
                BluetoothAdapter.STATE_ON -> {
                    log.i(TAG, "Bluetooth turned on")
                    _state.update { it.copy(bluetoothOn = true) }
                    refresh()
                }
                BluetoothAdapter.STATE_TURNING_OFF, BluetoothAdapter.STATE_OFF -> {
                    if (_state.value.bluetoothOn) log.w(TAG, "Bluetooth turned off")
                    io.post {
                        cancelReconnect()
                        releaseProxy(unregister = false)
                        _state.update { it.copy(bluetoothOn = false, host = null) }
                    }
                }
            }
        }
    }

    companion object {
        private const val TAG = "HID"
        const val SDP_NAME = "Air Pointer"
        const val SDP_DESCRIPTION = "Gyroscope presentation pointer"
        const val SDP_PROVIDER = "Air Pointer"
        private const val PROXY_TIMEOUT_MS = 5_000L
        private const val CONNECT_TIMEOUT_MS = 15_000L
        private val RECONNECT_DELAYS_MS = longArrayOf(2_000, 4_000, 8_000, 15_000, 30_000, 30_000)

        @Suppress("unused")
        private fun now() = SystemClock.elapsedRealtime()
    }
}
