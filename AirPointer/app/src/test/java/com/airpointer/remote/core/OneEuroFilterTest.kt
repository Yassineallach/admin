package com.airpointer.remote.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OneEuroFilterTest {
    @Test
    fun convergesToStep() {
        val f = OneEuroFilter(1.0, 0.0)
        f.filter(0.0, 0.005)
        var v = 0.0
        repeat(400) { v = f.filter(1.0, 0.005) }
        assertEquals(1.0, v, 1e-3)
    }

    @Test
    fun higherBetaReducesLagOnFastMotion() {
        fun lag(beta: Double): Double {
            val f = OneEuroFilter(1.0, beta)
            var x = 0.0; var y = 0.0
            repeat(100) { x += 0.01; y = f.filter(x, 0.005) } // 2 rad/s ramp
            return x - y
        }
        assertTrue(lag(18.0) < lag(0.0) / 3)
    }
}
