package com.airpointer.remote.motion

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.SystemClock
import com.airpointer.remote.core.AirMouseProcessor
import com.airpointer.remote.core.PointerDelta
import com.airpointer.remote.core.TiltPointerProcessor
import com.airpointer.remote.diagnostics.DiagnosticsLog

/**
 * Registers the gyroscope and accelerometer with SensorManager and feeds the motion processor.
 * Sensor events are delivered on the shared [io] thread (the same thread that sends HID reports)
 * so the path sensor → processor → report has no thread hops.
 */
class SensorMotionSource(
    context: Context,
    private val io: Handler,
    private val log: DiagnosticsLog,
) : SensorEventListener {

    data class SensorInfo(val name: String, val vendor: String, val minDelayUs: Int, val maxRangeLabel: String)

    data class Capabilities(
        val gyroscope: SensorInfo?,
        val accelerometer: SensorInfo?,
        val gameRotationVector: Boolean,
    ) {
        val mode: Mode
            get() = when {
                gyroscope != null && accelerometer != null -> Mode.GYRO
                accelerometer != null -> Mode.TILT_FALLBACK
                else -> Mode.NONE
            }
    }

    enum class Mode(val label: String) {
        GYRO("Gyroscope + accelerometer"),
        TILT_FALLBACK("Accelerometer tilt (no gyroscope)"),
        NONE("No motion sensors"),
    }

    private val sm = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val gyro: Sensor? = sm.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
    private val accel: Sensor? = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)

    val capabilities = Capabilities(
        gyroscope = gyro?.let { SensorInfo(it.name, it.vendor, it.minDelay, "%.1f rad/s".format(it.maximumRange)) },
        accelerometer = accel?.let { SensorInfo(it.name, it.vendor, it.minDelay, "%.1f m/s²".format(it.maximumRange)) },
        gameRotationVector = sm.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR) != null,
    )

    val processor = AirMouseProcessor()
    val tilt = TiltPointerProcessor()

    /** Called on the io thread for every non-zero delta. */
    var onDelta: ((PointerDelta) -> Unit)? = null
    /** Evaluated on the io thread for every sample: should movement be emitted? */
    var gate: () -> Boolean = { false }

    @Volatile var running = false
        private set

    // Rate metering (io thread only).
    private var gyroCount = 0
    private var accelCount = 0
    private var meterStartMs = 0L
    @Volatile var gyroRateHz = 0f; private set
    @Volatile var accelRateHz = 0f; private set
    @Volatile var lastProcessingNs = 0L; private set

    fun start(): Boolean {
        if (running) return true
        val mode = capabilities.mode
        if (mode == Mode.NONE) {
            log.e(TAG, "No usable motion sensors on this device")
            return false
        }
        processor.resetAll()
        meterStartMs = SystemClock.elapsedRealtime(); gyroCount = 0; accelCount = 0
        var ok = true
        if (gyro != null) ok = sm.registerListener(this, gyro, GYRO_PERIOD_US, io)
        if (accel != null) ok = sm.registerListener(this, accel, ACCEL_PERIOD_US, io) && ok
        running = ok
        log.i(TAG, "Sensors started (${mode.label}), ok=$ok")
        if (!ok) sm.unregisterListener(this)
        return ok
    }

    fun stop() {
        if (!running) return
        sm.unregisterListener(this)
        running = false
        gyroRateHz = 0f; accelRateHz = 0f
        log.i(TAG, "Sensors stopped")
    }

    override fun onSensorChanged(event: SensorEvent) {
        val t0 = SystemClock.elapsedRealtimeNanos()
        val v = event.values
        when (event.sensor.type) {
            Sensor.TYPE_ACCELEROMETER -> {
                accelCount++
                processor.onAccelerometer(v[0].toDouble(), v[1].toDouble(), v[2].toDouble())
                if (gyro == null) {
                    val d = tilt.onAccelerometer(v[0].toDouble(), v[1].toDouble(), v[2].toDouble(), event.timestamp, gate())
                    if (!d.isZero) onDelta?.invoke(d)
                }
            }
            Sensor.TYPE_GYROSCOPE -> {
                gyroCount++
                val d = processor.onGyroscope(v[0].toDouble(), v[1].toDouble(), v[2].toDouble(), event.timestamp, gate())
                if (!d.isZero) onDelta?.invoke(d)
                lastProcessingNs = SystemClock.elapsedRealtimeNanos() - t0
            }
        }
        val now = SystemClock.elapsedRealtime()
        val span = now - meterStartMs
        if (span >= 1000) {
            gyroRateHz = gyroCount * 1000f / span
            accelRateHz = accelCount * 1000f / span
            gyroCount = 0; accelCount = 0; meterStartMs = now
        }
    }

    override fun onAccuracyChanged(sensor: Sensor, accuracy: Int) {
        if (accuracy <= SensorManager.SENSOR_STATUS_ACCURACY_LOW) {
            log.w(TAG, "${sensor.name} accuracy low ($accuracy)")
        }
    }

    companion object {
        private const val TAG = "Sensors"
        /** 200 Hz gyroscope: the maximum allowed without HIGH_SAMPLING_RATE_SENSORS on Android 12+. */
        const val GYRO_PERIOD_US = 5_000
        const val ACCEL_PERIOD_US = 10_000
    }
}
