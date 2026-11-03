package com.airpointer.remote.core

import kotlin.math.cos
import kotlin.math.sin

/**
 * Synthesises IMU samples for a phone with a given orientation that is rotated about WORLD axes.
 * World frame: Z up. The phone's orientation is a rotation matrix R (device → world).
 * Gyro reads ω_device = Rᵀ ω_world; accelerometer at rest reads Rᵀ (0, 0, g).
 */
class MotionSimulator(
    private val processor: AirMouseProcessor,
    /** Device→world rotation, row-major 3×3. */
    var r: Array<DoubleArray> = identity(),
    val rateHz: Double = 200.0,
) {
    var t = 1_000_000_000L
    val dtNs = (1e9 / rateHz).toLong()
    var totalX = 0L
    var totalY = 0L

    fun toDevice(w: Vec3) = Vec3(
        r[0][0] * w.x + r[1][0] * w.y + r[2][0] * w.z,
        r[0][1] * w.x + r[1][1] * w.y + r[2][1] * w.z,
        r[0][2] * w.x + r[1][2] * w.y + r[2][2] * w.z,
    )

    /** Run for [seconds] with constant world angular velocity; returns summed output. */
    fun run(seconds: Double, worldOmega: Vec3 = Vec3.ZERO, gyroBias: Vec3 = Vec3.ZERO, emit: Boolean = true,
            noise: (() -> Vec3)? = null): PointerDelta {
        val n = (seconds * rateHz).toInt()
        var sx = 0; var sy = 0
        repeat(n) {
            val a = toDevice(Vec3(0.0, 0.0, AirMouseProcessor.GRAVITY))
            processor.onAccelerometer(a.x, a.y, a.z)
            val w = toDevice(worldOmega) + gyroBias + (noise?.invoke() ?: Vec3.ZERO)
            val d = processor.onGyroscope(w.x, w.y, w.z, t, emit)
            sx += d.dx; sy += d.dy
            t += dtNs
            // integrate orientation: R ← exp(ω_world dt) R
            r = mul(rotation(worldOmega, 1.0 / rateHz), r)
        }
        totalX += sx; totalY += sy
        return PointerDelta(sx, sy)
    }

    companion object {
        fun identity() = arrayOf(doubleArrayOf(1.0, 0.0, 0.0), doubleArrayOf(0.0, 1.0, 0.0), doubleArrayOf(0.0, 0.0, 1.0))

        fun mul(a: Array<DoubleArray>, b: Array<DoubleArray>) = Array(3) { i -> DoubleArray(3) { j -> (0..2).sumOf { a[i][it] * b[it][j] } } }

        /** Rodrigues rotation for axis-angle ω·dt. */
        fun rotation(omega: Vec3, dt: Double): Array<DoubleArray> {
            val angle = omega.norm() * dt
            if (angle < 1e-15) return identity()
            val k = omega.normalized()
            val c = cos(angle); val s = sin(angle); val v = 1 - c
            return arrayOf(
                doubleArrayOf(c + k.x * k.x * v, k.x * k.y * v - k.z * s, k.x * k.z * v + k.y * s),
                doubleArrayOf(k.y * k.x * v + k.z * s, c + k.y * k.y * v, k.y * k.z * v - k.x * s),
                doubleArrayOf(k.z * k.x * v - k.y * s, k.z * k.y * v + k.x * s, c + k.z * k.z * v),
            )
        }

        /** Rotation about a world axis by [angle] radians. */
        fun about(axis: Vec3, angle: Double) = rotation(axis, angle)
    }
}
