package com.airpointer.remote.core

import kotlin.math.sqrt

/** Small immutable 3-vector used by the motion pipeline (device coordinate frame). */
data class Vec3(val x: Double, val y: Double, val z: Double) {
    operator fun plus(o: Vec3) = Vec3(x + o.x, y + o.y, z + o.z)
    operator fun minus(o: Vec3) = Vec3(x - o.x, y - o.y, z - o.z)
    operator fun times(s: Double) = Vec3(x * s, y * s, z * s)
    operator fun div(s: Double) = Vec3(x / s, y / s, z / s)
    operator fun unaryMinus() = Vec3(-x, -y, -z)

    infix fun dot(o: Vec3) = x * o.x + y * o.y + z * o.z
    infix fun cross(o: Vec3) = Vec3(y * o.z - z * o.y, z * o.x - x * o.z, x * o.y - y * o.x)

    fun norm() = sqrt(x * x + y * y + z * z)
    fun normalized(): Vec3 {
        val n = norm()
        return if (n < 1e-12) this else this / n
    }

    fun clampEach(limit: Double) = Vec3(
        x.coerceIn(-limit, limit),
        y.coerceIn(-limit, limit),
        z.coerceIn(-limit, limit),
    )

    companion object {
        val ZERO = Vec3(0.0, 0.0, 0.0)
        val X = Vec3(1.0, 0.0, 0.0)
        val Y = Vec3(0.0, 1.0, 0.0)
        val Z = Vec3(0.0, 0.0, 1.0)
    }
}
