package com.airpointer.remote.core

import kotlin.math.abs
import kotlin.math.hypot

/**
 * Laptop-style touchpad gestures, independent of Android so it can be unit tested.
 *
 *  • one finger moves the pointer (with optional acceleration)
 *  • one-finger tap → left click
 *  • two-finger tap → right click
 *  • two-finger drag → scroll (natural direction optional)
 *  • long press (finger held still) → drag mode: left button held until the finger lifts
 *
 * Feed it pointer events with positions in pixels and times in milliseconds.
 */
class TouchpadGestureEngine(
    private val touchSlopPx: Float,
    private val scrollStepPx: Float,
    var sensitivity: Float = 1.6f,
    var acceleration: Float = 0.6f,
    /** Windows precision touchpads and macOS default to natural scrolling: content follows the fingers. */
    var naturalScroll: Boolean = true,
    private val tapTimeoutMs: Long = 220,
    private val longPressMs: Long = 450,
) {
    sealed interface Action {
        data class Move(val dx: Int, val dy: Int) : Action
        data class Scroll(val steps: Int) : Action
        data object LeftClick : Action
        data object RightClick : Action
        data object DragStart : Action
        data object DragEnd : Action
    }

    private data class Finger(val downX: Float, val downY: Float, var x: Float, var y: Float, val downAt: Long)

    private val fingers = linkedMapOf<Long, Finger>()
    private var gestureStart = 0L
    private var maxFingers = 0
    private var moved = false
    private var dragging = false
    private var residualX = 0f
    private var residualY = 0f
    private var scrollAccum = 0f
    private var lastMoveAt = 0L

    val isDragging get() = dragging

    fun down(id: Long, x: Float, y: Float, t: Long): List<Action> {
        if (fingers.isEmpty()) {
            gestureStart = t; maxFingers = 0; moved = false; scrollAccum = 0f
        }
        fingers[id] = Finger(x, y, x, y, t)
        maxFingers = maxOf(maxFingers, fingers.size)
        return emptyList()
    }

    fun move(id: Long, x: Float, y: Float, t: Long): List<Action> {
        val f = fingers[id] ?: return emptyList()
        val dx = x - f.x; val dy = y - f.y
        f.x = x; f.y = y
        if (!moved && hypot(x - f.downX, y - f.downY) > touchSlopPx) moved = true
        if (!moved && !dragging) return emptyList()
        val out = mutableListOf<Action>()
        if (fingers.size >= 2) {
            // Scroll with the average of the fingers: use this finger's share of the movement.
            if (fingers.keys.first() != id) return emptyList()
            scrollAccum += dy
            while (abs(scrollAccum) >= scrollStepPx) {
                val dir = if (scrollAccum > 0) 1 else -1
                // Natural: fingers up (dir −1) → wheel −1 → page scrolls down, content follows the fingers.
                out += Action.Scroll(if (naturalScroll) dir else -dir)
                scrollAccum -= dir * scrollStepPx
            }
            return out
        }
        val dt = (t - lastMoveAt).coerceIn(1, 100)
        lastMoveAt = t
        val speed = hypot(dx, dy) / dt // px per ms
        val gain = sensitivity * (1f + acceleration * (speed / 1.5f).coerceIn(0f, 2f))
        val cx = dx * gain + residualX
        val cy = dy * gain + residualY
        val ix = cx.toInt(); val iy = cy.toInt()
        residualX = cx - ix; residualY = cy - iy
        if (ix != 0 || iy != 0) out += Action.Move(ix, iy)
        return out
    }

    /** Call periodically (e.g. every 50 ms) while fingers are down to detect long presses. */
    fun tick(t: Long): List<Action> {
        if (!dragging && !moved && fingers.size == 1 && maxFingers == 1 && t - gestureStart >= longPressMs) {
            dragging = true
            return listOf(Action.DragStart)
        }
        return emptyList()
    }

    fun up(id: Long, t: Long): List<Action> {
        fingers.remove(id) ?: return emptyList()
        if (fingers.isNotEmpty()) return emptyList()
        val out = mutableListOf<Action>()
        val duration = t - gestureStart
        when {
            dragging -> { dragging = false; out += Action.DragEnd }
            !moved && duration <= tapTimeoutMs && maxFingers == 1 -> out += Action.LeftClick
            !moved && duration <= tapTimeoutMs + 120 && maxFingers >= 2 -> out += Action.RightClick
        }
        residualX = 0f; residualY = 0f
        return out
    }

    fun cancel(): List<Action> {
        fingers.clear()
        return if (dragging) { dragging = false; listOf(Action.DragEnd) } else emptyList()
    }
}
