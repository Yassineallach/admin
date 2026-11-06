package com.airpointer.remote.core

import com.airpointer.remote.core.TouchpadGestureEngine.Action
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TouchpadGestureEngineTest {
    private fun engine() = TouchpadGestureEngine(touchSlopPx = 10f, scrollStepPx = 30f, sensitivity = 1f, acceleration = 0f)

    @Test
    fun oneFingerTapIsLeftClick() {
        val e = engine()
        e.down(1, 100f, 100f, 0)
        e.move(1, 103f, 101f, 50)
        assertEquals(listOf(Action.LeftClick), e.up(1, 120))
    }

    @Test
    fun twoFingerTapIsRightClick() {
        val e = engine()
        e.down(1, 100f, 100f, 0); e.down(2, 200f, 100f, 20)
        assertTrue(e.up(1, 150).isEmpty())
        assertEquals(listOf(Action.RightClick), e.up(2, 170))
    }

    @Test
    fun oneFingerDragMovesPointer() {
        val e = engine()
        e.down(1, 0f, 0f, 0)
        val moves = (1..10).flatMap { e.move(1, it * 5f, it * -2f, it * 16L) }
        val dx = moves.filterIsInstance<Action.Move>().sumOf { it.dx }
        val dy = moves.filterIsInstance<Action.Move>().sumOf { it.dy }
        assertTrue("dx $dx", dx in 38..50); assertTrue("dy $dy", dy in -20..-12)
        assertTrue("no click after moving", e.up(1, 200).isEmpty())
    }

    @Test
    fun twoFingerDragScrolls() {
        val e = engine()
        e.down(1, 100f, 300f, 0); e.down(2, 160f, 300f, 5)
        val out = (1..10).flatMap { i -> e.move(1, 100f, 300f - i * 12f, i * 16L) + e.move(2, 160f, 300f - i * 12f, i * 16L) }
        val steps = out.filterIsInstance<Action.Scroll>().sumOf { it.steps }
        assertEquals("120 px up at 30 px/step scrolls down 4", -4, steps)
        assertTrue(out.none { it is Action.Move })
    }

    @Test
    fun longPressStartsDragUntilLift() {
        val e = engine()
        e.down(1, 50f, 50f, 0)
        assertTrue(e.tick(200).isEmpty())
        assertEquals(listOf(Action.DragStart), e.tick(500))
        val moves = e.move(1, 90f, 50f, 520)
        assertTrue(moves.any { it is Action.Move })
        assertEquals(listOf(Action.DragEnd), e.up(1, 700))
    }
}
