package com.airpointer.remote.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Random
import kotlin.math.abs

class TableMotionProcessorTest {
    private val g = 9.80665
    private val rate = 200
    private val dtNs = 1_000_000_000L / rate

    private class Run(val p: TableMotionProcessor) { var t = 1_000_000_000L; var x = 0; var y = 0 }

    private fun Run.feed(seconds: Double, ax: (Double) -> Double = { 0.0 }, ay: (Double) -> Double = { 0.0 },
                         bias: Vec3 = Vec3.ZERO, yawRate: Double = 0.0, noise: Random? = null) {
        val n = (seconds * rate).toInt()
        for (i in 0 until n) {
            val s = i.toDouble() / rate
            val nz = { noise?.nextGaussian()?.times(0.02) ?: 0.0 }
            p.onGyroscope(nz(), nz(), yawRate + nz())
            val d = p.onAccelerometer(ax(s) + bias.x + nz(), ay(s) + bias.y + nz(), g + bias.z + nz(), t, true)
            x += d.dx; y += d.dy; t += dtNs
        }
    }

    /** A mouse push: accelerate for [half] s, decelerate for [half] s. Distance = a·half². */
    private fun push(a: Double, half: Double): (Double) -> Double = { s -> if (s < half) a else if (s < 2 * half) -a else 0.0 }

    private fun settled(): Run = Run(TableMotionProcessor()).apply { feed(0.5) }

    @Test
    fun pushRightMovesCursorRightByTravel() {
        val r = settled()
        r.feed(0.6, ax = push(2.0, 0.1)) // 2 cm push
        r.feed(0.3)
        // 0.02 m × 25 000 counts/m = 500 counts (dead band + leak cost a little)
        assertTrue("dx ${r.x}", r.x in 380..520)
        assertTrue("dy leak ${r.y}", abs(r.y) <= 10)
    }

    @Test
    fun pushForwardMovesCursorUp() {
        val r = settled()
        r.feed(0.6, ay = push(2.0, 0.1))
        r.feed(0.3)
        assertTrue("dy ${r.y}", r.y in -520..-380)
        assertTrue(abs(r.x) <= 10)
    }

    @Test
    fun pushAndReturnEndsNearStart() {
        val r = settled()
        r.feed(0.4, ax = push(2.0, 0.1)); r.feed(0.3)
        r.feed(0.4, ax = push(-2.0, 0.1)); r.feed(0.3)
        assertTrue("net ${r.x}", abs(r.x) <= 60)
    }

    @Test
    fun restingPhoneNeverDriftsEvenWithBiasAndNoise() {
        val r = Run(TableMotionProcessor())
        r.feed(10.0, bias = Vec3(0.08, -0.06, 0.1), noise = Random(3))
        assertTrue("drift ${r.x},${r.y}", abs(r.x) <= 3 && abs(r.y) <= 3)
    }

    @Test
    fun turningThePhoneInPlaceIsNotMovement() {
        val r = settled()
        r.feed(1.0, yawRate = 1.5) // spin on the desk
        assertTrue("spin moved ${r.x},${r.y}", abs(r.x) <= 5 && abs(r.y) <= 5)
    }

    @Test
    fun repeatedPushesAccumulateWithoutDrift() {
        val r = settled()
        repeat(5) { r.feed(0.4, ax = push(2.0, 0.1)); r.feed(0.25) }
        assertTrue("5 pushes ${r.x}", r.x in 1900..2600)
        val before = r.x
        r.feed(3.0) // rest
        assertEquals(before, r.x)
    }
}
