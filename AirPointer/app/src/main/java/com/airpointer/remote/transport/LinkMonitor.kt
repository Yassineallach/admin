package com.airpointer.remote.transport

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import com.airpointer.remote.hid.BluetoothHidController
import com.airpointer.remote.settings.SettingsRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

/**
 * Watches the selected link for the UI: tells an intentional disconnect apart from a lost
 * connection, tracks Wi-Fi availability, and offers one set of connect/cancel/disconnect actions
 * used by the home card, the notification banner and the remotes.
 */
class LinkMonitor(
    context: Context,
    private val link: TransportRouter,
    private val hid: BluetoothHidController,
    private val wifi: WifiCompanionClient,
    private val settings: SettingsRepository,
    scope: CoroutineScope,
) {
    sealed interface Event {
        data class Lost(val name: String?) : Event
        data class Restored(val name: String?) : Event
    }

    private val _lost = MutableStateFlow(false)
    val lost: StateFlow<Boolean> = _lost
    private val _events = MutableSharedFlow<Event>(extraBufferCapacity = 4)
    val events: SharedFlow<Event> = _events
    private val _wifiAvailable = MutableStateFlow(true)
    val wifiAvailable: StateFlow<Boolean> = _wifiAvailable

    @Volatile private var intentional = false

    private val name: String?
        get() = if (settings.current.transport == TransportKind.WIFI) wifi.state.value.serverName ?: settings.current.wifiName
        else hid.state.value.host?.name ?: settings.current.lastHostName

    init {
        scope.launch {
            var was = link.connectedFlow.value
            link.connectedFlow.collect { now ->
                if (was && !now && !intentional) { _lost.value = true; _events.tryEmit(Event.Lost(name)) }
                if (!was && now) {
                    if (_lost.value) _events.tryEmit(Event.Restored(name))
                    _lost.value = false; intentional = false
                }
                was = now
            }
        }
        // Switching transport is a deliberate change, not a lost connection.
        scope.launch {
            settings.settings.map { it.transport }.distinctUntilChanged().drop(1).collect { intentional = true; _lost.value = false }
        }
        val cm = context.getSystemService(ConnectivityManager::class.java)
        runCatching {
            cm.registerDefaultNetworkCallback(object : ConnectivityManager.NetworkCallback() {
                override fun onCapabilitiesChanged(network: Network, caps: NetworkCapabilities) {
                    _wifiAvailable.value = caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                        caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
                }
                override fun onLost(network: Network) { _wifiAvailable.value = false }
            })
        }
    }

    /** True when a computer has been set up for the selected transport. */
    val configured: Boolean
        get() = settings.current.let {
            if (it.transport == TransportKind.WIFI) it.wifiHost != null && it.wifiPin != null else it.lastHostAddress != null
        }

    /** Connect to the saved computer. Returns false when nothing is set up yet (show the setup screen). */
    fun connect(): Boolean {
        val s = settings.current
        intentional = false
        return if (s.transport == TransportKind.WIFI) {
            if (s.wifiHost == null || s.wifiPin == null) false else { wifi.connect(s.wifiHost, s.wifiPort, s.wifiPin); true }
        } else {
            val addr = s.lastHostAddress ?: return false
            hid.connect(addr); true
        }
    }

    fun cancel() = disconnect()

    fun disconnect() {
        intentional = true
        _lost.value = false
        if (settings.current.transport == TransportKind.WIFI) wifi.disconnect() else hid.disconnect()
    }

    fun dismissLost() { _lost.value = false }
}
