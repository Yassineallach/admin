package com.airpointer.remote.core

import kotlin.math.PI
import kotlin.math.abs

/**
 * 1€ filter (Casiez, Roussel, Vogel — CHI 2012).
 *
 * An adaptive low-pass filter: at low speeds the cutoff is [minCutoff] which removes hand
 * tremor; as speed increases the cutoff rises by [beta] × speed so fast movements are not lagged.
 * This is the standard choice for pointing devices because it trades jitter vs. latency
 * dynamically instead of with a single fixed constant.
 */
class OneEuroFilter(
    var minCutoff: Double,
    var beta: Double,
    var derivativeCutoff: Double = 1.0,
) {
    private var prevValue = 0.0
    private var prevDerivative = 0.0
    private var initialized = false

    val value: Double get() = prevValue

    fun reset() {
        initialized = false
        prevDerivative = 0.0
    }

    /** Shift the internal state by [offset] (used to rebase accumulated angles without a jump). */
    fun shift(offset: Double) {
        prevValue += offset
    }

    fun filter(x: Double, dt: Double): Double {
        if (!initialized) {
            prevValue = x
            prevDerivative = 0.0
            initialized = true
            return x
        }
        if (dt <= 0.0) return prevValue
        val rawDerivative = (x - prevValue) / dt
        val d = lerp(prevDerivative, rawDerivative, alpha(derivativeCutoff, dt))
        val cutoff = minCutoff + beta * abs(d)
        val result = lerp(prevValue, x, alpha(cutoff, dt))
        prevValue = result
        prevDerivative = d
        return result
    }

    private fun lerp(a: Double, b: Double, t: Double) = a + (b - a) * t

    private fun alpha(cutoff: Double, dt: Double): Double {
        val tau = 1.0 / (2.0 * PI * cutoff)
        return 1.0 / (1.0 + tau / dt)
    }
}
