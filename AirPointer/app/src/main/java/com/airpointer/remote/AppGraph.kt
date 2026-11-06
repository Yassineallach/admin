package com.airpointer.remote

import android.app.Application
import android.content.Context
import android.os.Handler
import android.os.HandlerThread
import android.os.Process
import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.airpointer.remote.hid.BluetoothHidController
import com.airpointer.remote.hid.BluetoothPairingManager
import com.airpointer.remote.motion.SensorMotionSource
import com.airpointer.remote.presenter.PresenterController
import com.airpointer.remote.settings.SettingsRepository
import com.airpointer.remote.table.TableMouseController
import com.airpointer.remote.transport.CompanionDiscovery
import com.airpointer.remote.tv.TvDiscovery
import com.airpointer.remote.tv.TvManager
import com.airpointer.remote.tv.TvRepository
import com.airpointer.remote.transport.TransportKind
import com.airpointer.remote.transport.TransportRouter
import com.airpointer.remote.transport.WifiCompanionClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

class AirPointerApp : Application() {
    lateinit var graph: AppGraph
        private set

    override fun onCreate() {
        super.onCreate()
        graph = AppGraph(this)
    }
}

/** Manual dependency graph: process-wide singletons shared by the service and the UI. */
class AppGraph(app: Application) {
    /** Single real-time thread for sensor events, motion processing and HID report I/O. */
    private val ioThread = HandlerThread("airpointer-io", Process.THREAD_PRIORITY_URGENT_DISPLAY).apply { start() }
    val io = Handler(ioThread.looper)
    val appScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)

    val log = DiagnosticsLog()
    val settings = SettingsRepository(app)
    val hid = BluetoothHidController(app, io, log, settings, appScope)
    val wifi = WifiCompanionClient(log, appScope, "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}")
    val link = TransportRouter(hid, wifi, settings, appScope)
    val companionDiscovery = CompanionDiscovery(app)
    val pairing = BluetoothPairingManager(app, log)
    val motion = SensorMotionSource(app, io, log)
    val presenter = PresenterController(link, motion, settings, io, log, appScope)

    val tvRepository = TvRepository(app)
    val tv = TvManager(app, tvRepository, presenter, hid, appScope)
    val tvDiscovery = TvDiscovery(app)
    val tableMouse = TableMouseController(app, presenter, log)

    init {
        // Reconnect to the saved companion when Wi-Fi is the selected transport.
        settings.current.let { s ->
            if (s.transport == TransportKind.WIFI && s.wifiHost != null && s.wifiPin != null) wifi.connect(s.wifiHost, s.wifiPort, s.wifiPin)
        }
    }
}

val Context.graph: AppGraph get() = (applicationContext as AirPointerApp).graph
