package com.airpointer.remote.core

import com.airpointer.remote.core.AirGestureEngine.Action
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AirGestureEngineTest {
    private fun e() = AirGestureEngine(touchSlopPx = 10f, scrollStepPx = 30f, fineSensitivity = 1f)

    @Test
    fun quickTapClicksWithoutTracking() {
        val g = e()
        g.down(1, 100f, 100f, 0)
        assertTrue(g.tick(100).isEmpty())
        assertEquals(listOf(Action.LeftClick), g.up(1, 120))
    }

    @Test
    fun holdingAFingerTracksThePhoneUntilLift() {
        val g = e()
        g.down(1, 100f, 100f, 0)
        assertEquals(listOf(Action.Tracking(true)), g.tick(200))
        assertEquals(listOf(Action.Tracking(false)), g.up(1, 1500))
    }

    @Test
    fun slidingStartsTrackingAndNudgesTheCursor() {
        val g = e()
        g.down(1, 0f, 0f, 0)
        val out = g.move(1, 20f, 0f, 30) + g.move(1, 30f, 5f, 60)
        assertTrue(Action.Tracking(true) in out)
        assertEquals(30, out.filterIsInstance<Action.Move>().sumOf { it.dx })
        assertTrue("no click after a slide", g.up(1, 100).none { it == Action.LeftClick })
    }

    @Test
    fun doubleTapIsTwoClicks() {
        val g = e()
        g.down(1, 50f, 50f, 0); val a = g.up(1, 90)
        g.down(2, 52f, 50f, 200); val b = g.up(2, 280)
        assertEquals(listOf(Action.LeftClick), a); assertEquals(listOf(Action.LeftClick), b)
    }

    @Test
    fun tapThenHoldDrags() {
        val g = e()
        g.down(1, 50f, 50f, 0); g.up(1, 90)
        g.down(2, 50f, 50f, 250)
        assertEquals(listOf(Action.DragStart, Action.Tracking(true)), g.tick(450))
        assertEquals(listOf(Action.Tracking(false), Action.DragEnd), g.up(2, 2000))
    }

    @Test
    fun twoFingerTapRightClicksAndTwoFingerDragScrolls() {
        val g = e()
        g.down(1, 100f, 100f, 0); g.down(2, 160f, 100f, 10)
        g.up(1, 120)
        assertEquals(listOf(Action.RightClick), g.up(2, 140))

        g.down(3, 100f, 300f, 1000); g.down(4, 160f, 300f, 1005)
        val out = (1..10).flatMap { i -> g.move(3, 100f, 300f - i * 12f, 1000L + i * 16) + g.move(4, 160f, 300f - i * 12f, 1000L + i * 16) }
        assertEquals(-4, out.filterIsInstance<Action.Scroll>().sumOf { it.steps })
        assertTrue(out.none { it is Action.Tracking && it.on })
    }

    @Test
    fun alwaysOnModeNeverTogglesTracking() {
        val g = e().apply { touchToTrack = false }
        g.down(1, 0f, 0f, 0)
        assertTrue(g.tick(500).isEmpty())
        assertTrue(g.up(1, 900).isEmpty())
    }
}
