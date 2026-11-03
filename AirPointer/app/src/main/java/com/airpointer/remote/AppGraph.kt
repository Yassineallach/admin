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
    val hid = BluetoothHidController(app, io, log, settings)
    val pairing = BluetoothPairingManager(app, log)
    val motion = SensorMotionSource(app, io, log)
    val presenter = PresenterController(hid, motion, settings, io, log, appScope)
}

val Context.graph: AppGraph get() = (applicationContext as AirPointerApp).graph
