package com.airpointer.remote.core

import kotlin.math.ln
import kotlin.math.exp

/** Tunable parameters of the gyroscope → pointer pipeline. All angular values in rad/s. */
data class MotionConfig(
    /** User speed multiplier (0.2 … 3.0). */
    val sensitivity: Double = 1.0,
    /** Mouse counts produced per radian of rotation at sensitivity 1.0 and no acceleration. */
    val countsPerRadian: Double = 1100.0,
    /** Pointer acceleration amount (0 = linear … 2 = strong). */
    val acceleration: Double = 0.6,
    /** Smoothing (0 = raw/fastest … 1 = smoothest). Maps to the 1€ filter min cutoff. */
    val smoothing: Double = 0.5,
    /** Soft dead zone on angular speed, removes residual drift and micro-tremor. */
    val deadzone: Double = 0.012,
    /** Continuously re-estimate gyro bias while the phone is still. */
    val autoDriftCompensation: Boolean = true,
    val invertX: Boolean = false,
    val invertY: Boolean = false,
) {
    /** 1€ min cutoff in Hz: smoothing 0 → 6 Hz, 1 → 0.4 Hz (log interpolation). */
    fun minCutoffHz(): Double {
        val s = smoothing.coerceIn(0.0, 1.0)
        return exp(ln(6.0) + (ln(0.4) - ln(6.0)) * s)
    }
}

data class PointerDelta(val dx: Int, val dy: Int) {
    val isZero get() = dx == 0 && dy == 0

    companion object {
        val ZERO = PointerDelta(0, 0)
    }
}

sealed interface CalibrationState {
    data object Idle : CalibrationState
    data class Running(val progress: Float, val restarts: Int) : CalibrationState
    data class Done(val bias: Vec3) : CalibrationState
    data class Failed(val reason: String) : CalibrationState
}
