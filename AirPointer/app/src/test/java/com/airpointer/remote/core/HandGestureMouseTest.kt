package com.airpointer.remote.core

import com.airpointer.remote.core.HandGestureMouse.Action
import com.airpointer.remote.core.HandGestureMouse.P
import com.airpointer.remote.core.HandGestureMouse.Pose
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Random

class HandGestureMouseTest {

    enum class Thumb { AWAY, ON_INDEX, ON_MIDDLE }

    /** Synthetic right hand facing the camera, fingers up; hand size (wrist→middle MCP) = 0.15. */
    private fun hand(cx: Float, cy: Float, index: Boolean = true, middle: Boolean = false, ring: Boolean = false,
                     pinky: Boolean = false, thumb: Thumb = Thumb.AWAY): List<P> {
        val pts = Array(21) { P(0f, 0f) }
        pts[0] = P(cx, cy + 0.15f)
        fun finger(base: Int, x: Float, ext: Boolean) {
            pts[base] = P(cx + x, cy)
            if (ext) { pts[base + 1] = P(cx + x, cy - 0.04f); pts[base + 2] = P(cx + x, cy - 0.07f); pts[base + 3] = P(cx + x, cy - 0.10f) }
            else { pts[base + 1] = P(cx + x, cy - 0.03f); pts[base + 2] = P(cx + x, cy - 0.01f); pts[base + 3] = P(cx + x, cy + 0.02f) }
        }
        finger(5, -0.03f, index); finger(9, 0f, middle); finger(13, 0.03f, ring); finger(17, 0.06f, pinky)
        pts[1] = P(cx - 0.04f, cy + 0.12f); pts[2] = P(cx - 0.07f, cy + 0.08f); pts[3] = P(cx - 0.09f, cy + 0.04f)
        pts[4] = when (thumb) {
            Thumb.AWAY -> P(cx - 0.11f, cy + 0.01f)
            Thumb.ON_INDEX -> P(pts[8].x + 0.005f, pts[8].y + 0.005f)
            Thumb.ON_MIDDLE -> P(pts[12].x + 0.005f, pts[12].y + 0.005f)
        }
        return pts.toList()
    }

    private class Clock { var t = 1000L; fun next(): Long { t += 33; return t } }

    private fun HandGestureMouse.frames(n: Int, c: Clock, h: (Int) -> List<P>?): List<Action> =
        (0 until n).flatMap { update(h(it), c.next()) }

    @Test
    fun movingTheHandMovesTheCursorInTheSameDirection() {
        val m = HandGestureMouse(acceleration = 0.0); val c = Clock()
        m.frames(5, c) { hand(0.5f, 0.5f) }
        val out = m.frames(30, c) { i -> hand(0.5f + i * 0.005f, 0.5f - i * 0.003f) }
        val dx = out.filterIsInstance<Action.Move>().sumOf { it.dx }
        val dy = out.filterIsInstance<Action.Move>().sumOf { it.dy }
        assertTrue("right: $dx", dx > 120); assertTrue("up: $dy", dy < -60)
        assertEquals(Pose.POINTING, m.pose)
    }

    @Test
    fun steadyHandWithLandmarkJitterDoesNotMoveTheCursor() {
        val m = HandGestureMouse(); val c = Clock(); val r = Random(1)
        m.frames(10, c) { hand(0.5f, 0.5f) }
        val out = m.frames(90, c) { hand(0.5f + (r.nextGaussian() * 0.0015).toFloat(), 0.5f + (r.nextGaussian() * 0.0015).toFloat()) }
        val total = out.filterIsInstance<Action.Move>().sumOf { kotlin.math.abs(it.dx) + kotlin.math.abs(it.dy) }
        assertTrue("jitter moved $total counts in 3 s", total < 40)
    }

    @Test
    fun quickPinchIsALeftClickAndTheCursorStaysPut() {
        val m = HandGestureMouse(); val c = Clock()
        m.frames(5, c) { hand(0.5f, 0.5f) }
        val out = m.frames(5, c) { hand(0.5f, 0.5f, thumb = Thumb.ON_INDEX) } + m.frames(4, c) { hand(0.5f, 0.5f) }
        assertEquals(listOf(Action.LeftClick), out.filter { it !is Action.Move })
        assertTrue(out.none { it is Action.Move })
    }

    @Test
    fun twoQuickPinchesAreADoubleClick() {
        val m = HandGestureMouse(); val c = Clock()
        m.frames(5, c) { hand(0.5f, 0.5f) }
        val out = (1..2).flatMap { m.frames(4, c) { hand(0.5f, 0.5f, thumb = Thumb.ON_INDEX) } + m.frames(3, c) { hand(0.5f, 0.5f) } }
        assertEquals(2, out.count { it == Action.LeftClick })
    }

    @Test
    fun pinchAndHoldDragsWhileTheHandMoves() {
        val m = HandGestureMouse(acceleration = 0.0); val c = Clock()
        m.frames(5, c) { hand(0.5f, 0.5f) }
        val hold = m.frames(15, c) { hand(0.5f, 0.5f, thumb = Thumb.ON_INDEX) }
        assertTrue(Action.DragStart in hold)
        assertTrue(m.dragging)
        val moving = m.frames(20, c) { i -> hand(0.5f + i * 0.006f, 0.5f, thumb = Thumb.ON_INDEX) }
        assertTrue("drag moves the cursor", moving.filterIsInstance<Action.Move>().sumOf { it.dx } > 100)
        val release = m.frames(3, c) { hand(0.62f, 0.5f) }
        assertTrue(Action.DragEnd in release)
        assertTrue((hold + moving + release).none { it == Action.LeftClick })
    }

    @Test
    fun thumbToMiddleIsARightClick() {
        val m = HandGestureMouse(); val c = Clock()
        m.frames(5, c) { hand(0.5f, 0.5f, middle = true) }
        val out = m.frames(6, c) { hand(0.5f, 0.5f, middle = true, thumb = Thumb.ON_MIDDLE) } + m.frames(3, c) { hand(0.5f, 0.5f, middle = true) }
        assertEquals(listOf(Action.RightClick), out.filter { it !is Action.Move })
    }

    @Test
    fun twoRaisedFingersScrollWithHandHeight() {
        val m = HandGestureMouse(); val c = Clock()
        m.frames(5, c) { hand(0.5f, 0.6f, middle = true) }
        val up = m.frames(20, c) { i -> hand(0.5f, 0.6f - i * 0.01f, middle = true) }
        assertEquals(Pose.SCROLL, m.pose)
        val steps = up.filterIsInstance<Action.Scroll>().sumOf { it.steps }
        assertTrue("hand up scrolls up: $steps", steps >= 4)
        assertTrue("no cursor motion while scrolling", up.none { it is Action.Move })
    }

    @Test
    fun fistPausesTheCursor() {
        val m = HandGestureMouse(); val c = Clock()
        m.frames(5, c) { hand(0.5f, 0.5f, index = false) }
        val out = m.frames(20, c) { i -> hand(0.5f + i * 0.01f, 0.5f, index = false) }
        assertEquals(Pose.FIST, m.pose)
        assertTrue(out.isEmpty())
    }

    @Test
    fun losingTheHandEndsADragAndReappearingDoesNotJump() {
        val m = HandGestureMouse(); val c = Clock()
        m.frames(5, c) { hand(0.5f, 0.5f) }
        m.frames(15, c) { hand(0.5f, 0.5f, thumb = Thumb.ON_INDEX) }
        assertEquals(listOf(Action.DragEnd), m.update(null, c.next()))
        val back = m.frames(3, c) { hand(0.2f, 0.8f) } // hand re-enters far away
        assertTrue("no jump: $back", back.none { it is Action.Move })
    }
}
