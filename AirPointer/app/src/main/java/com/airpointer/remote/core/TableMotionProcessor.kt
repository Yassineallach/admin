package com.airpointer.remote.core

import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.hypot

/**
 * "Table mouse" from the gyroscope + accelerometer: the phone lies flat and is pushed around
 * the desk like a mouse.
 *
 * The accelerometer measures acceleration, not position, so position comes from integrating
 * twice. Done naively that drifts away within a second. This processor keeps it usable the way
 * inertial foot-trackers do, with **zero-velocity updates (ZUPT)**:
 *  • the gyroscope tracks the rest vector (gravity + accelerometer bias) through rotations, and
 *    with the accelerometer it detects when the phone is at rest;
 *  • at rest, velocity is reset to exactly zero and the rest vector is re-learned, so each
 *    push of the mouse is integrated on its own and errors cannot build up between pushes;
 *  • a small dead band and a velocity leak keep sensor noise from creeping in mid-stroke.
 *
 * Result: quick, short pushes map well to cursor movement (like a mouse on a low-DPI setting);
 * very slow glides below the dead band register less. Device frame, phone flat, screen up,
 * top pointing away from the user: +X = right, +Y = forward (cursor up).
 */
class TableMotionProcessor(
    var countsPerMeter: Double = 25_000.0, // ≈ 250 counts per cm of phone travel
    var invertX: Boolean = false,
    var invertY: Boolean = false,
) {
    private var rest: Vec3? = null
    private var omega = Vec3.ZERO
    private var lastTs = 0L
    private var stillTime = 0.0
    private var vx = 0.0
    private var vy = 0.0
    private var resX = 0.0
    private var resY = 0.0

    var isStill = true
        private set
    var isFlat = true
        private set
    var speed = 0.0 // m/s, for the UI
        private set

    fun reset() {
        rest = null; lastTs = 0L; vx = 0.0; vy = 0.0; resX = 0.0; resY = 0.0; stillTime = 0.0
    }

    fun onGyroscope(x: Double, y: Double, z: Double) { omega = Vec3(x, y, z) }

    /** Accelerometer sample (m/s², device frame). Returns the cursor delta to send. */
    fun onAccelerometer(x: Double, y: Double, z: Double, timestampNs: Long, emit: Boolean): PointerDelta {
        val a = Vec3(x, y, z)
        val r0 = rest
        if (r0 == null || lastTs == 0L) { rest = r0 ?: a; lastTs = timestampNs; return PointerDelta.ZERO }
        val dt = (timestampNs - lastTs) * 1e-9
        lastTs = timestampNs
        if (dt <= 0 || dt > 0.1) { vx = 0.0; vy = 0.0; return PointerDelta.ZERO }

        // Keep the rest vector aligned with the phone as it yaws on the desk (v̇ = v × ω).
        var r = (r0 + (r0 cross omega) * dt)
        isFlat = abs(r.z) / r.norm() > 0.94 // within ~20° of horizontal

        val lin = a - r
        val linXY = hypot(lin.x, lin.y)
        val rotating = omega.norm()
        val quiet = linXY < STILL_ACCEL && abs(lin.z) < STILL_ACCEL * 2 && rotating < STILL_GYRO
        stillTime = if (quiet) stillTime + dt else 0.0
        isStill = stillTime >= STILL_TIME

        if (isStill) {
            // Zero-velocity update: the phone is resting → velocity is exactly zero; re-learn bias.
            vx = 0.0; vy = 0.0
            r = r + (a - r) * (dt / (REST_TAU + dt))
            rest = r
            speed = 0.0
            return PointerDelta.ZERO
        }
        rest = r

        // Integrate horizontal acceleration (dead band removes noise and residual tilt).
        val ax = deadband(lin.x); val ay = deadband(lin.y)
        vx += ax * dt; vy += ay * dt
        val leak = exp(-dt / VELOCITY_TAU)
        vx *= leak; vy *= leak
        speed = hypot(vx, vy)

        if (!emit || !isFlat) { resX = 0.0; resY = 0.0; return PointerDelta.ZERO }
        val cx = vx * dt * countsPerMeter * (if (invertX) -1 else 1) + resX
        val cy = -vy * dt * countsPerMeter * (if (invertY) -1 else 1) + resY // forward = up
        val ix = cx.toInt(); val iy = cy.toInt()
        resX = cx - ix; resY = cy - iy
        return PointerDelta(ix, iy)
    }

    private fun deadband(v: Double) = when {
        v > DEADBAND -> v - DEADBAND
        v < -DEADBAND -> v + DEADBAND
        else -> 0.0
    }

    companion object {
        const val STILL_ACCEL = 0.12   // m/s²
        const val STILL_GYRO = 0.06    // rad/s
        const val STILL_TIME = 0.06    // s of quiet before a zero-velocity update
        const val DEADBAND = 0.05      // m/s²
        const val REST_TAU = 0.25      // s, rest-vector learning while still
        const val VELOCITY_TAU = 0.8   // s, mid-stroke velocity leak
    }
}
