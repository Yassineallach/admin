package com.airpointer.remote.core

import kotlin.math.abs
import kotlin.math.hypot

/**
 * Converts gyroscope + accelerometer samples into relative mouse deltas.
 *
 * Pipeline per gyroscope sample:
 *  1. Bias removal (manual calibration + optional automatic drift compensation while still).
 *  2. Gravity tracking: complementary filter (gyro-propagated, accelerometer-corrected) giving
 *     the world "up" direction expressed in the device frame.
 *  3. Gravity-compensated rates: yaw = ω·up (rotation about the world vertical) and
 *     pitch = ω·right where right = normalize(deviceY × up). This makes the pointer independent
 *     of how the phone is rolled/tilted in the hand — turning the wrist left always moves the
 *     cursor left, as on commercial air mice.
 *  4. Soft dead zone, integration to angles, 1€ adaptive smoothing.
 *  5. Pointer acceleration curve, gain, sub-count residual accumulation.
 *
 * Not thread-safe: call all methods from a single thread (the sensor/HID I/O thread).
 * [config] may be swapped from any thread.
 */
class AirMouseProcessor(initialConfig: MotionConfig = MotionConfig()) {

    @Volatile
    var config: MotionConfig = initialConfig

    var bias: Vec3 = Vec3.ZERO
        private set
    var up: Vec3 = Vec3.Z
        private set
    var hasGravity = false
        private set
    var isStill = false
        private set
    var yawRate = 0.0
        private set
    var pitchRate = 0.0
        private set
    var calibrationState: CalibrationState = CalibrationState.Idle
        private set

    var calibrationListener: ((CalibrationState) -> Unit)? = null

    private var lastAccel: Vec3? = null
    private var lastGyroTs = 0L
    private var stillTime = 0.0

    private var angleX = 0.0
    private var angleY = 0.0
    private val filterX = OneEuroFilter(initialConfig.minCutoffHz(), BETA)
    private val filterY = OneEuroFilter(initialConfig.minCutoffHz(), BETA)
    private var prevFilteredX = 0.0
    private var prevFilteredY = 0.0
    private var filtersPrimed = false
    private var residualX = 0.0
    private var residualY = 0.0
    private var speedEma = 0.0

    private var calibration: CalibrationRun? = null

    fun setBias(b: Vec3) {
        bias = b.clampEach(MAX_BIAS)
    }

    /** Reset filters and residuals (e.g. after recentering or a sensor pause). */
    fun resetMotion() {
        filtersPrimed = false
        residualX = 0.0
        residualY = 0.0
        speedEma = 0.0
    }

    /** Full reset including the timestamp chain and gravity estimate. */
    fun resetAll() {
        resetMotion()
        lastGyroTs = 0L
        hasGravity = false
        lastAccel?.let { if (it.norm() > 1e-3) { up = it.normalized(); hasGravity = true } }
        stillTime = 0.0
    }

    fun onAccelerometer(x: Double, y: Double, z: Double) {
        val a = Vec3(x, y, z)
        lastAccel = a
        if (!hasGravity && a.norm() > 1e-3) {
            up = a.normalized()
            hasGravity = true
        }
    }

    fun startCalibration(durationSeconds: Double = 1.5) {
        calibration = CalibrationRun(durationSeconds)
        publishCalibration(CalibrationState.Running(0f, 0))
    }

    fun cancelCalibration() {
        if (calibration != null) {
            calibration = null
            publishCalibration(CalibrationState.Idle)
        }
    }

    /**
     * Process one gyroscope sample (rad/s, device frame) with timestamp in nanoseconds.
     * @param emit whether movement should be produced; when false the filters keep tracking but
     *             the output is zero and residuals are discarded so re-enabling never jumps.
     */
    fun onGyroscope(gx: Double, gy: Double, gz: Double, timestampNs: Long, emit: Boolean): PointerDelta {
        val raw = Vec3(gx, gy, gz)
        if (lastGyroTs == 0L) {
            lastGyroTs = timestampNs
            return PointerDelta.ZERO
        }
        val dt = (timestampNs - lastGyroTs) * 1e-9
        lastGyroTs = timestampNs
        if (dt <= 0.0) return PointerDelta.ZERO
        if (dt > MAX_DT) {
            // Gap in the sensor stream (sensor re-registered, CPU stall). Restart filters.
            resetMotion()
            return PointerDelta.ZERO
        }

        calibration?.let { feedCalibration(it, raw, dt) }

        val cfg = config
        val omega = raw - bias
        updateStillness(omega, raw, dt, cfg)
        updateGravity(omega, dt)
        if (!hasGravity) return PointerDelta.ZERO

        val u = up
        val right = rightAxis(u)
        val yaw = omega dot u
        val pitch = omega dot right
        yawRate = yaw
        pitchRate = pitch

        // Soft dead zone on the 2D angular speed (continuous: subtracts the dead zone radius).
        val speed = hypot(yaw, pitch)
        val k = if (speed <= cfg.deadzone) 0.0 else (speed - cfg.deadzone) / speed

        // Screen X grows to the right, Y grows downward. Positive yaw (turn left) → move left;
        // positive pitch (top of phone up) → move up.
        angleX += -yaw * k * dt
        angleY += -pitch * k * dt

        val cutoff = cfg.minCutoffHz()
        filterX.minCutoff = cutoff
        filterY.minCutoff = cutoff
        if (!filtersPrimed) {
            filterX.reset(); filterY.reset()
            prevFilteredX = filterX.filter(angleX, dt)
            prevFilteredY = filterY.filter(angleY, dt)
            filtersPrimed = true
            return PointerDelta.ZERO
        }
        val fx = filterX.filter(angleX, dt)
        val fy = filterY.filter(angleY, dt)
        val dAngX = fx - prevFilteredX
        val dAngY = fy - prevFilteredY
        prevFilteredX = fx
        prevFilteredY = fy
        rebaseIfNeeded()

        val instSpeed = hypot(dAngX, dAngY) / dt
        speedEma += (instSpeed - speedEma) * (dt / (SPEED_TAU + dt))
        val accelFactor = 1.0 + cfg.acceleration *
            ((speedEma - ACCEL_LOW_SPEED) / ACCEL_RANGE).coerceIn(0.0, ACCEL_MAX_BOOST)
        val gain = cfg.countsPerRadian * cfg.sensitivity * accelFactor

        if (!emit || calibration != null) {
            // Discard the filter's lag tail too, so motion made while the pointer was off can
            // never leak out once it is re-enabled (filters re-prime at the current angle).
            residualX = 0.0
            residualY = 0.0
            filtersPrimed = false
            return PointerDelta.ZERO
        }

        val cx = dAngX * gain * (if (cfg.invertX) -1.0 else 1.0) + residualX
        val cy = dAngY * gain * (if (cfg.invertY) -1.0 else 1.0) + residualY
        val ix = cx.toInt().coerceIn(-MAX_COUNTS, MAX_COUNTS)
        val iy = cy.toInt().coerceIn(-MAX_COUNTS, MAX_COUNTS)
        residualX = (cx - ix).coerceIn(-1.0, 1.0)
        residualY = (cy - iy).coerceIn(-1.0, 1.0)
        return PointerDelta(ix, iy)
    }

    private fun updateStillness(omega: Vec3, raw: Vec3, dt: Double, cfg: MotionConfig) {
        val accelOk = lastAccel?.let { abs(it.norm() - GRAVITY) < STILL_ACCEL_TOLERANCE } ?: false
        if (omega.norm() < STILL_RATE && accelOk) stillTime += dt else stillTime = 0.0
        isStill = stillTime > STILL_TIME
        if (cfg.autoDriftCompensation && isStill && calibration == null) {
            val a = dt / (BIAS_TAU + dt)
            bias = (bias + (raw - bias) * a).clampEach(MAX_BIAS)
        }
    }

    private fun updateGravity(omega: Vec3, dt: Double) {
        if (!hasGravity) return
        // A world-fixed vector seen from a frame rotating at ω evolves as dv/dt = v × ω.
        var u = (up + (up cross omega) * dt).normalized()
        lastAccel?.let { a ->
            val n = a.norm()
            if (n > 1e-3) {
                val deviation = abs(n - GRAVITY)
                // Trust the accelerometer less while the hand is accelerating the phone.
                val trust = (1.0 - (deviation - 0.5) / 2.5).coerceIn(0.0, 1.0)
                val w = dt / (GRAVITY_TAU + dt) * trust
                u = (u * (1.0 - w) + (a / n) * w).normalized()
            }
        }
        up = u
    }

    private fun rebaseIfNeeded() {
        if (abs(angleX) > REBASE_LIMIT) {
            val off = -angleX
            angleX += off; prevFilteredX += off; filterX.shift(off)
        }
        if (abs(angleY) > REBASE_LIMIT) {
            val off = -angleY
            angleY += off; prevFilteredY += off; filterY.shift(off)
        }
    }

    private fun feedCalibration(run: CalibrationRun, raw: Vec3, dt: Double) {
        run.total += dt
        if (run.count >= 10) {
            val mean = run.sum / run.count.toDouble()
            if ((raw - mean).norm() > CALIBRATION_MOTION_LIMIT) {
                run.restart()
            }
        }
        run.sum += raw
        run.count++
        run.elapsed += dt
        if (run.total > CALIBRATION_TIMEOUT) {
            calibration = null
            publishCalibration(CalibrationState.Failed("Movement detected. Place the phone on a flat surface or hold it perfectly still and try again."))
            return
        }
        if (run.elapsed >= run.duration && run.count > 20) {
            calibration = null
            setBias(run.sum / run.count.toDouble())
            resetAll()
            lastGyroTs = 0L
            publishCalibration(CalibrationState.Done(bias))
        } else {
            val progress = (run.elapsed / run.duration).toFloat().coerceIn(0f, 1f)
            if (progress - run.lastPublished >= 0.04f || run.restarts != run.lastRestarts) {
                run.lastPublished = progress
                run.lastRestarts = run.restarts
                publishCalibration(CalibrationState.Running(progress, run.restarts))
            }
        }
    }

    private fun publishCalibration(state: CalibrationState) {
        calibrationState = state
        calibrationListener?.invoke(state)
    }

    private class CalibrationRun(val duration: Double) {
        var sum = Vec3.ZERO
        var count = 0
        var elapsed = 0.0
        var total = 0.0
        var restarts = 0
        var lastPublished = 0f
        var lastRestarts = 0
        fun restart() {
            sum = Vec3.ZERO; count = 0; elapsed = 0.0; restarts++
        }
    }

    companion object {
        const val GRAVITY = 9.80665
        const val MAX_DT = 0.1
        const val MAX_COUNTS = 32767
        const val MAX_BIAS = 0.2
        const val BETA = 18.0
        const val STILL_RATE = 0.03
        const val STILL_TIME = 0.8
        const val STILL_ACCEL_TOLERANCE = 0.6
        const val BIAS_TAU = 3.0
        const val GRAVITY_TAU = 0.5
        const val SPEED_TAU = 0.05
        const val ACCEL_LOW_SPEED = 0.25
        const val ACCEL_RANGE = 1.25
        const val ACCEL_MAX_BOOST = 2.0
        const val REBASE_LIMIT = 500.0
        const val CALIBRATION_MOTION_LIMIT = 0.12
        const val CALIBRATION_TIMEOUT = 8.0

        /**
         * Horizontal "right" axis in the device frame for a phone pointed along its +Y axis.
         * right = normalize(Y × up); degenerates only when the phone points straight up/down,
         * in which case the device X axis projected onto the horizontal plane is used.
         */
        fun rightAxis(u: Vec3): Vec3 {
            val c = Vec3(u.z, 0.0, -u.x) // Y × u
            val n = c.norm()
            if (n > 0.3) return c / n
            val p = Vec3.X - u * u.x
            val pn = p.norm()
            return if (pn > 1e-6) p / pn else Vec3.X
        }
    }
}
