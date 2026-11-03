package com.airpointer.remote.hid

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ReportAccumulatorTest {
    @Test
    fun coalescesAndRateLimits() {
        val a = ReportAccumulator(minIntervalNs = 8_000_000)
        a.add(3, -2); a.add(4, 1)
        assertEquals(0, a.waitNs(0))
        val c = a.drain(0)
        assertEquals(7, c.dx); assertEquals(-1, c.dy)
        assertFalse(a.hasPending)
        a.add(1, 0)
        assertEquals(8_000_000, a.waitNs(0))
        assertEquals(3_000_000, a.waitNs(5_000_000))
        assertEquals(0, a.waitNs(9_000_000))
    }

    @Test
    fun carriesOverflowIntoNextReport() {
        val a = ReportAccumulator()
        a.add(40_000, 0, wheel = 200)
        val c1 = a.drain(0)
        assertEquals(32767, c1.dx); assertEquals(127, c1.wheel)
        assertTrue(a.hasPending)
        val c2 = a.drain(10_000_000)
        assertEquals(40_000 - 32767, c2.dx); assertEquals(73, c2.wheel)
    }
}
