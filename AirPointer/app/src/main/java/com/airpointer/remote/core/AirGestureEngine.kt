package com.airpointer.remote.core

import kotlin.math.abs
import kotlin.math.hypot

/**
 * Finger gestures for the air mouse and the table mouse (the phone itself moves the cursor;
 * fingers only click, scroll and switch tracking on and off):
 *
 *  • hold a finger on the screen → [Action.Tracking] on: the cursor follows the phone
 *    (when [touchToTrack] is set); sliding the finger nudges the cursor for fine positioning
 *  • tap → left click (a double tap therefore arrives at the PC as a double click)
 *  • two-finger tap → right click
 *  • two-finger drag → scroll
 *  • tap, then touch again and hold → drag: the left button stays down until the finger lifts
 *
 * Tracking only starts after [trackDelayMs] or once the finger slides, so the short contact of
 * a tap never moves the cursor before the click.
 */
class AirGestureEngine(
    private val touchSlopPx: Float,
    private val scrollStepPx: Float,
    var touchToTrack: Boolean = true,
    var fineSensitivity: Float = 0.6f,
    var naturalScroll: Boolean = true,
    private val tapTimeoutMs: Long = 180,
    private val trackDelayMs: Long = 180,
    private val doubleTapGapMs: Long = 300,
) {
    sealed interface Action {
        data class Tracking(val on: Boolean) : Action
        data class Move(val dx: Int, val dy: Int) : Action
        data class Scroll(val steps: Int) : Action
        data object LeftClick : Action
        data object RightClick : Action
        data object DragStart : Action
        data object DragEnd : Action
    }

    private class Finger(val downX: Float, val downY: Float, var x: Float, var y: Float)

    private val fingers = linkedMapOf<Long, Finger>()
    private var downAt = 0L
    private var maxFingers = 0
    private var moved = false
    private var tracking = false
    private var dragging = false
    private var dragArmed = false
    private var lastTapAt = Long.MIN_VALUE / 2
    private var scrollAccum = 0f
    private var resX = 0f
    private var resY = 0f

    val isTracking get() = tracking
    val isDragging get() = dragging

    fun down(id: Long, x: Float, y: Float, t: Long): List<Action> {
        val out = mutableListOf<Action>()
        if (fingers.isEmpty()) {
            downAt = t; maxFingers = 0; moved = false; scrollAccum = 0f
            dragArmed = t - lastTapAt <= doubleTapGapMs
        }
        fingers[id] = Finger(x, y, x, y)
        maxFingers = maxOf(maxFingers, fingers.size)
        if (fingers.size == 2) {
            // Two fingers: scroll / right click. Stop pointing so the hand movement does not drag the cursor.
            dragArmed = false
            if (tracking) { tracking = false; out += Action.Tracking(false) }
        }
        return out
    }

    fun move(id: Long, x: Float, y: Float, t: Long): List<Action> {
        val f = fingers[id] ?: return emptyList()
        val dx = x - f.x; val dy = y - f.y
        f.x = x; f.y = y
        if (!moved && hypot(x - f.downX, y - f.downY) > touchSlopPx) moved = true
        val out = mutableListOf<Action>()
        if (fingers.size >= 2 || maxFingers >= 2) {
            if (fingers.size < 2 || fingers.keys.first() != id || !moved) return out
            scrollAccum += dy
            while (abs(scrollAccum) >= scrollStepPx) {
                val dir = if (scrollAccum > 0) 1 else -1
                out += Action.Scroll(if (naturalScroll) dir else -dir)
                scrollAccum -= dir * scrollStepPx
            }
            return out
        }
        if (moved) out += startTracking()
        if (moved && fineSensitivity > 0f) {
            val cx = dx * fineSensitivity + resX; val cy = dy * fineSensitivity + resY
            val ix = cx.toInt(); val iy = cy.toInt()
            resX = cx - ix; resY = cy - iy
            if (ix != 0 || iy != 0) out += Action.Move(ix, iy)
        }
        return out
    }

    /** Call every ~30 ms while a finger is down. */
    fun tick(t: Long): List<Action> =
        if (fingers.size == 1 && maxFingers == 1 && t - downAt >= trackDelayMs) startTracking() else emptyList()

    private fun startTracking(): List<Action> {
        val out = mutableListOf<Action>()
        if (dragArmed && !dragging) { dragging = true; out += Action.DragStart }
        if (touchToTrack && !tracking) { tracking = true; out += Action.Tracking(true) }
        return out
    }

    fun up(id: Long, t: Long): List<Action> {
        fingers.remove(id) ?: return emptyList()
        if (fingers.isNotEmpty()) return emptyList()
        val out = mutableListOf<Action>()
        val duration = t - downAt
        val wasPointing = tracking || dragging
        if (tracking) { tracking = false; out += Action.Tracking(false) }
        if (dragging) { dragging = false; out += Action.DragEnd }
        when {
            maxFingers >= 2 && !moved && duration <= tapTimeoutMs + 150 -> out += Action.RightClick
            maxFingers == 1 && !moved && !wasPointing && duration <= tapTimeoutMs -> {
                out += Action.LeftClick
                lastTapAt = t
            }
        }
        resX = 0f; resY = 0f
        return out
    }

    fun cancel(): List<Action> {
        fingers.clear()
        val out = mutableListOf<Action>()
        if (tracking) { tracking = false; out += Action.Tracking(false) }
        if (dragging) { dragging = false; out += Action.DragEnd }
        return out
    }
}
