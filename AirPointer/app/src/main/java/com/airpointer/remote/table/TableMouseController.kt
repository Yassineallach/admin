package com.airpointer.remote.table

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.SystemClock
import com.airpointer.remote.core.TableMotionProcessor
import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.airpointer.remote.presenter.PresenterController
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Table mouse from the gyroscope + accelerometer (see [TableMotionProcessor]). Sensor events
 * arrive on the shared io thread at 200 Hz; deltas go through the presenter's normal report path.
 */
class TableMouseController(
    context: Context,
    private val presenter: PresenterController,
    private val io: Handler,
    private val log: DiagnosticsLog,
) : SensorEventListener {

    data class Status(
        val running: Boolean = false,
        val still: Boolean = true,
        val flat: Boolean = true,
        val speedCmPerSec: Float = 0f,
        val message: String? = null,
    )

    private val _status = MutableStateFlow(Status())
    val status: StateFlow<Status> = _status

    private val sm = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val gyro = sm.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
    private val accel = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    val available: Boolean get() = gyro != null && accel != null

    val processor = TableMotionProcessor()

    /** True while a finger touches the screen (a tap shakes the phone): motion is ignored. */
    @Volatile var touchHold = false
    @Volatile var speed = 1f
        set(v) { field = v; processor.countsPerMeter = BASE_COUNTS_PER_METER * v }
    private var lastUi = 0L

    fun start() {
        if (!available) {
            _status.value = Status(message = "This phone needs both a gyroscope and an accelerometer for the table mouse.")
            return
        }
        io.post {
            processor.reset()
            sm.registerListener(this, gyro, SAMPLING_US, io)
            sm.registerListener(this, accel, SAMPLING_US, io)
        }
        _status.value = Status(running = true, message = "Keep the phone flat and slide it like a mouse.")
        log.i(TAG, "Table mouse started (gyroscope + accelerometer)")
    }

    fun stop() {
        sm.unregisterListener(this)
        _status.value = Status()
    }

    override fun onSensorChanged(e: SensorEvent) {
        val v = e.values
        when (e.sensor.type) {
            Sensor.TYPE_GYROSCOPE -> processor.onGyroscope(v[0].toDouble(), v[1].toDouble(), v[2].toDouble())
            Sensor.TYPE_ACCELEROMETER -> {
                val d = processor.onAccelerometer(v[0].toDouble(), v[1].toDouble(), v[2].toDouble(), e.timestamp, !touchHold)
                if (!d.isZero) presenter.moveBy(d.dx, d.dy)
                val now = SystemClock.elapsedRealtime()
                if (now - lastUi > 100) {
                    lastUi = now
                    _status.value = _status.value.copy(
                        still = processor.isStill, flat = processor.isFlat,
                        speedCmPerSec = (processor.speed * 100).toFloat(),
                        message = if (!processor.isFlat) "Lay the phone flat on the desk." else null,
                    )
                }
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor, accuracy: Int) {}

    companion object {
        private const val TAG = "TableMouse"
        const val SAMPLING_US = 5_000
        const val BASE_COUNTS_PER_METER = 25_000.0
    }
}
