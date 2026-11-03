package com.airpointer.remote.hid

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothClass
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import androidx.core.content.IntentCompat
import com.airpointer.remote.diagnostics.DiagnosticsLog
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update

/** Device discovery, bonding and the bonded-device list for the pairing screen. */
@SuppressLint("MissingPermission")
class BluetoothPairingManager(
    private val context: Context,
    private val log: DiagnosticsLog,
) {
    data class Device(
        val name: String,
        val address: String,
        val bonded: Boolean,
        val kind: Kind,
        val rssi: Int? = null,
    )

    enum class Kind(val label: String) { COMPUTER("Computer"), PHONE("Phone"), AUDIO("Audio"), PERIPHERAL("Peripheral"), OTHER("Device") }

    data class State(
        val bonded: List<Device> = emptyList(),
        val discovered: List<Device> = emptyList(),
        val scanning: Boolean = false,
        val discoverable: Boolean = false,
        val bondingAddress: String? = null,
        val message: String? = null,
    )

    private val adapter: BluetoothAdapter? = context.getSystemService(BluetoothManager::class.java)?.adapter
    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state
    private var listeners = 0
    private var onBonded: ((String) -> Unit)? = null

    val localName: String
        get() = (if (hasConnect()) try { adapter?.name } catch (_: SecurityException) { null } else null) ?: "this phone"

    fun hasConnect() = Build.VERSION.SDK_INT < Build.VERSION_CODES.S ||
        granted(Manifest.permission.BLUETOOTH_CONNECT)

    fun hasScan() = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) granted(Manifest.permission.BLUETOOTH_SCAN)
    else granted(Manifest.permission.ACCESS_FINE_LOCATION)

    private fun granted(p: String) = ContextCompat.checkSelfPermission(context, p) == PackageManager.PERMISSION_GRANTED

    /** Start observing Bluetooth broadcasts (pairing screen visible). */
    fun attach() {
        if (listeners++ == 0) {
            val f = IntentFilter().apply {
                addAction(BluetoothDevice.ACTION_FOUND)
                addAction(BluetoothDevice.ACTION_BOND_STATE_CHANGED)
                addAction(BluetoothDevice.ACTION_NAME_CHANGED)
                addAction(BluetoothAdapter.ACTION_DISCOVERY_STARTED)
                addAction(BluetoothAdapter.ACTION_DISCOVERY_FINISHED)
                addAction(BluetoothAdapter.ACTION_SCAN_MODE_CHANGED)
            }
            ContextCompat.registerReceiver(context, receiver, f, ContextCompat.RECEIVER_EXPORTED)
        }
        refresh()
    }

    fun detach() {
        if (--listeners == 0) {
            stopScan()
            try { context.unregisterReceiver(receiver) } catch (_: IllegalArgumentException) {}
        }
    }

    fun refresh() {
        val a = adapter ?: return
        if (!hasConnect()) return
        val bonded = try { a.bondedDevices.orEmpty() } catch (_: SecurityException) { emptySet() }
        val discoverable = try { a.scanMode == BluetoothAdapter.SCAN_MODE_CONNECTABLE_DISCOVERABLE } catch (_: SecurityException) { false }
        _state.update { s ->
            s.copy(
                bonded = bonded.map { toDevice(it, null) }.sortedWith(deviceOrder),
                discovered = s.discovered.filter { d -> bonded.none { it.address == d.address } },
                discoverable = discoverable,
            )
        }
    }

    fun startScan(): Boolean {
        val a = adapter ?: return false
        if (!hasScan()) {
            _state.update { it.copy(message = "Scanning needs the Nearby devices permission.") }
            return false
        }
        return try {
            if (a.isDiscovering) a.cancelDiscovery()
            _state.update { it.copy(discovered = emptyList(), message = null) }
            val ok = a.startDiscovery()
            if (!ok) _state.update {
                it.copy(message = if (Build.VERSION.SDK_INT < Build.VERSION_CODES.S)
                    "Could not start scanning. On Android 11 and older, Location must be switched on." else "Could not start scanning.")
            }
            log.i(TAG, "Discovery started=$ok")
            ok
        } catch (e: SecurityException) {
            log.e(TAG, "startDiscovery: ${e.message}"); false
        }
    }

    fun stopScan() {
        try { if (hasScan()) adapter?.cancelDiscovery() } catch (_: SecurityException) {}
    }

    /** Bond with [address]; [then] is invoked with the address once bonded (or immediately if already bonded). */
    fun pair(address: String, then: (String) -> Unit) {
        val a = adapter ?: return
        val d = try { a.getRemoteDevice(address) } catch (_: IllegalArgumentException) { return }
        stopScan()
        try {
            if (d.bondState == BluetoothDevice.BOND_BONDED) { then(address); return }
            onBonded = then
            _state.update { it.copy(bondingAddress = address, message = "Pairing… confirm the code on both devices.") }
            val ok = d.createBond()
            log.i(TAG, "createBond(${d.address}) = $ok")
            if (!ok) _state.update { it.copy(bondingAddress = null, message = "Pairing could not be started.") }
        } catch (e: SecurityException) {
            log.e(TAG, "createBond: ${e.message}")
        }
    }

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(c: Context, intent: Intent) {
            when (intent.action) {
                BluetoothDevice.ACTION_FOUND -> {
                    val d = IntentCompat.getParcelableExtra(intent, BluetoothDevice.EXTRA_DEVICE, BluetoothDevice::class.java) ?: return
                    val rssi = intent.getShortExtra(BluetoothDevice.EXTRA_RSSI, Short.MIN_VALUE).toInt().takeIf { it != Short.MIN_VALUE.toInt() }
                    val dev = toDevice(d, rssi)
                    if (dev.bonded) return
                    _state.update { s ->
                        s.copy(discovered = (s.discovered.filter { it.address != dev.address } + dev).sortedWith(deviceOrder))
                    }
                }
                BluetoothAdapter.ACTION_DISCOVERY_STARTED -> _state.update { it.copy(scanning = true) }
                BluetoothAdapter.ACTION_DISCOVERY_FINISHED -> _state.update { it.copy(scanning = false) }
                BluetoothAdapter.ACTION_SCAN_MODE_CHANGED -> refresh()
                BluetoothDevice.ACTION_NAME_CHANGED -> refresh()
                BluetoothDevice.ACTION_BOND_STATE_CHANGED -> {
                    val d = IntentCompat.getParcelableExtra(intent, BluetoothDevice.EXTRA_DEVICE, BluetoothDevice::class.java) ?: return
                    val bond = intent.getIntExtra(BluetoothDevice.EXTRA_BOND_STATE, BluetoothDevice.BOND_NONE)
                    log.i(TAG, "Bond state ${d.address}: ${bondName(bond)}")
                    if (_state.value.bondingAddress == d.address) {
                        when (bond) {
                            BluetoothDevice.BOND_BONDED -> {
                                _state.update { it.copy(bondingAddress = null, message = "Paired. Connecting…") }
                                onBonded?.invoke(d.address); onBonded = null
                            }
                            BluetoothDevice.BOND_NONE -> _state.update { it.copy(bondingAddress = null, message = "Pairing failed or was cancelled.") }
                        }
                    }
                    refresh()
                }
            }
        }
    }

    private fun toDevice(d: BluetoothDevice, rssi: Int?): Device {
        val name = (try { d.name } catch (_: SecurityException) { null })?.takeIf { it.isNotBlank() } ?: d.address
        val bonded = try { d.bondState == BluetoothDevice.BOND_BONDED } catch (_: SecurityException) { false }
        val major = try { d.bluetoothClass?.majorDeviceClass } catch (_: SecurityException) { null }
        val kind = when (major) {
            BluetoothClass.Device.Major.COMPUTER -> Kind.COMPUTER
            BluetoothClass.Device.Major.PHONE -> Kind.PHONE
            BluetoothClass.Device.Major.AUDIO_VIDEO -> Kind.AUDIO
            BluetoothClass.Device.Major.PERIPHERAL -> Kind.PERIPHERAL
            else -> Kind.OTHER
        }
        return Device(name, d.address, bonded, kind, rssi)
    }

    private val deviceOrder = compareBy<Device>({ if (it.kind == Kind.COMPUTER) 0 else 1 }, { it.name.lowercase() })

    private fun bondName(b: Int) = when (b) {
        BluetoothDevice.BOND_BONDED -> "BONDED"; BluetoothDevice.BOND_BONDING -> "BONDING"; else -> "NONE"
    }

    companion object { private const val TAG = "Pairing" }
}
