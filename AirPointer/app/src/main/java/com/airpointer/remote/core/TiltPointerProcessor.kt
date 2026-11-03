package com.airpointer.remote.core

import kotlin.math.abs
import kotlin.math.asin
import kotlin.math.sign

/**
 * Fallback for phones WITHOUT a gyroscope: joystick-style pointer driven by the accelerometer.
 * Tilting the phone away from the reference orientation moves the cursor with a velocity
 * proportional to the tilt angle. Much less precise than gyro pointing but keeps the app usable.
 */
class TiltPointerProcessor(initialConfig: MotionConfig = MotionConfig()) {
    @Volatile
    var config: MotionConfig = initialConfig

    private var reference: Vec3? = null
    private var smoothed: Vec3? = null
    private var lastTs = 0L
    private var residualX = 0.0
    private var residualY = 0.0

    fun recenter() {
        reference = smoothed
        residualX = 0.0
        residualY = 0.0
    }

    fun onAccelerometer(x: Double, y: Double, z: Double, timestampNs: Long, emit: Boolean): PointerDelta {
        val a = Vec3(x, y, z).normalized()
        val s = smoothed?.let { (it * 0.85 + a * 0.15).normalized() } ?: a
        smoothed = s
        if (reference == null) reference = s
        if (lastTs == 0L) { lastTs = timestampNs; return PointerDelta.ZERO }
        val dt = ((timestampNs - lastTs) * 1e-9).coerceIn(0.0, 0.1)
        lastTs = timestampNs
        val ref = reference!!
        // Roll (left/right tilt) and pitch (forward/back tilt) relative to the reference.
        val roll = asin((s.x - ref.x).coerceIn(-1.0, 1.0))
        val pitch = asin((s.y - ref.y).coerceIn(-1.0, 1.0))
        if (!emit) { residualX = 0.0; residualY = 0.0; return PointerDelta.ZERO }
        val cfg = config
        val vx = shape(-roll) * TILT_GAIN * cfg.sensitivity
        val vy = shape(pitch) * TILT_GAIN * cfg.sensitivity
        val cx = vx * dt * (if (cfg.invertX) -1 else 1) + residualX
        val cy = vy * dt * (if (cfg.invertY) -1 else 1) + residualY
        val ix = cx.toInt(); val iy = cy.toInt()
        residualX = cx - ix; residualY = cy - iy
        return PointerDelta(ix, iy)
    }

    private fun shape(angle: Double): Double {
        val m = abs(angle) - DEADZONE
        return if (m <= 0) 0.0 else sign(angle) * m * (1 + m * 3)
    }

    companion object {
        const val DEADZONE = 0.05 // ~3°
        const val TILT_GAIN = 2500.0 // counts per second per radian
    }
}
