package com.airpointer.remote.core

import kotlin.math.abs
import kotlin.math.hypot

/**
 * Turns hand landmarks (MediaPipe's 21-point hand model, normalised image coordinates, image
 * upright and mirrored so the user's right is +x) into mouse actions — a camera air mouse
 * operated entirely with gestures in the air:
 *
 *  • move the hand / index finger   → cursor moves
 *  • pinch thumb + index            → left click; pinch twice = double click
 *  • pinch thumb + index and hold   → drag (left button held) until the pinch opens
 *  • pinch thumb + middle           → right click
 *  • index + middle raised (✌)      → scroll: move the hand up / down
 *  • fist                           → pause (move the hand freely without moving the cursor)
 *
 * Landmark indices: 0 wrist, 4 thumb tip, 5/6/8 index MCP/PIP/tip, 9/10/12 middle, 13/14/16 ring,
 * 17/18/20 pinky. Distances are divided by the hand size (wrist → middle MCP) so the gestures
 * work at any distance from the camera.
 */
class HandGestureMouse(
    var sensitivity: Double = 1.0,
    var acceleration: Double = 0.8,
    var pointer: PointerJoint = PointerJoint.KNUCKLE,
    var invertX: Boolean = false,
    var invertY: Boolean = false,
) {
    enum class PointerJoint { KNUCKLE, FINGERTIP }
    enum class Pose { NO_HAND, POINTING, LEFT_PINCH, RIGHT_PINCH, SCROLL, FIST }

    sealed interface Action {
        data class Move(val dx: Int, val dy: Int) : Action
        data class Scroll(val steps: Int) : Action
        data object LeftClick : Action
        data object RightClick : Action
        data object DragStart : Action
        data object DragEnd : Action
    }

    data class P(val x: Float, val y: Float)

    var pose = Pose.NO_HAND
        private set
    val dragging get() = leftState == PinchState.DRAG

    private enum class PinchState { OPEN, PRESSED, DRAG }
    private var leftState = PinchState.OPEN
    private var leftSince = 0L
    private var rightPressed = false
    private var rightSince = 0L
    private var leftOnFrames = 0
    private var rightOnFrames = 0

    private val fx = OneEuroFilter(MIN_CUTOFF, BETA)
    private val fy = OneEuroFilter(MIN_CUTOFF, BETA)
    private var last: Pair<Double, Double>? = null
    private var lastTs = 0L
    private var resX = 0.0
    private var resY = 0.0
    private var scrollAccum = 0.0
    private var freezeUntil = 0L

    /** Feed one camera frame. [hand] is null when no hand is visible. */
    fun update(hand: List<P>?, timestampMs: Long): List<Action> {
        val out = mutableListOf<Action>()
        if (hand == null || hand.size < 21) {
            if (leftState == PinchState.DRAG) out += Action.DragEnd
            leftState = PinchState.OPEN; rightPressed = false; leftOnFrames = 0; rightOnFrames = 0
            pose = Pose.NO_HAND
            resetMotion()
            return out
        }
        val size = dist(hand[0], hand[9]).coerceAtLeast(1e-4f)
        val dIndex = dist(hand[4], hand[8]) / size
        val dMiddle = dist(hand[4], hand[12]) / size
        fun extended(tip: Int, pip: Int) = dist(hand[tip], hand[0]) > dist(hand[pip], hand[0]) * 1.12f
        val index = extended(8, 6); val middle = extended(12, 10)
        val ring = extended(16, 14); val pinky = extended(20, 18)

        // Pinch detection with hysteresis and a 2-frame confirmation against flicker.
        // Index and middle fingertips sit close together, so a new pinch only counts for the finger
        // the thumb is clearly nearer to; once a pinch has started, hysteresis keeps it.
        val leftNow = if (leftState == PinchState.OPEN) dIndex < PINCH_ON && dIndex < dMiddle * NEARER else dIndex < PINCH_OFF
        leftOnFrames = if (leftNow) leftOnFrames + 1 else 0
        val rightNow = leftState == PinchState.OPEN && !leftNow &&
            (if (rightPressed) dMiddle < PINCH_OFF else dMiddle < PINCH_ON && dMiddle < dIndex * NEARER)
        rightOnFrames = if (rightNow) rightOnFrames + 1 else 0

        // ---- left pinch: click or drag
        when (leftState) {
            PinchState.OPEN -> if (leftOnFrames >= CONFIRM_FRAMES) {
                leftState = PinchState.PRESSED; leftSince = timestampMs
                freezeUntil = timestampMs + HOLD_FOR_DRAG_MS // keep the cursor still for the click
            }
            PinchState.PRESSED -> when {
                !leftNow -> { out += Action.LeftClick; leftState = PinchState.OPEN; freezeUntil = timestampMs + 120 }
                timestampMs - leftSince >= HOLD_FOR_DRAG_MS -> { out += Action.DragStart; leftState = PinchState.DRAG; freezeUntil = 0 }
            }
            PinchState.DRAG -> if (!leftNow) { out += Action.DragEnd; leftState = PinchState.OPEN; freezeUntil = timestampMs + 120 }
        }
        // ---- right pinch: click on release
        if (!rightPressed && rightOnFrames >= CONFIRM_FRAMES && leftState == PinchState.OPEN) {
            rightPressed = true; rightSince = timestampMs; freezeUntil = timestampMs + 600
        } else if (rightPressed && !rightNow) {
            rightPressed = false
            if (timestampMs - rightSince <= 800) out += Action.RightClick
            freezeUntil = timestampMs + 120
        }

        val scrollPose = index && middle && !ring && !pinky && leftState == PinchState.OPEN && !rightPressed
        val fist = !index && !middle && !ring && !pinky && leftState == PinchState.OPEN && !rightPressed
        pose = when {
            leftState != PinchState.OPEN -> Pose.LEFT_PINCH
            rightPressed -> Pose.RIGHT_PINCH
            scrollPose -> Pose.SCROLL
            fist -> Pose.FIST
            else -> Pose.POINTING
        }

        // ---- motion
        val p = if (pointer == PointerJoint.KNUCKLE) hand[5] else hand[8]
        val dt = if (lastTs == 0L) 0.033 else ((timestampMs - lastTs) / 1000.0).coerceIn(0.005, 0.2)
        lastTs = timestampMs
        val sx = fx.filter(p.x.toDouble(), dt); val sy = fy.filter(p.y.toDouble(), dt)
        val prev = last
        last = sx to sy
        if (prev == null) return out
        var ddx = sx - prev.first; var ddy = sy - prev.second

        if (pose == Pose.FIST) { resX = 0.0; resY = 0.0; scrollAccum = 0.0; return out }
        if (pose == Pose.SCROLL) {
            scrollAccum += ddy
            while (abs(scrollAccum) >= SCROLL_STEP) {
                val dir = if (scrollAccum > 0) 1 else -1
                out += Action.Scroll(-dir) // hand up (y decreases) → wheel up
                scrollAccum -= dir * SCROLL_STEP
            }
            return out
        }
        scrollAccum = 0.0
        if (timestampMs < freezeUntil) { resX = 0.0; resY = 0.0; return out }

        if (abs(ddx) < DEADZONE) ddx = 0.0
        if (abs(ddy) < DEADZONE) ddy = 0.0
        val speed = hypot(ddx, ddy) / dt // frame widths per second
        val gain = BASE_COUNTS * sensitivity * (1 + acceleration * (speed / 1.5).coerceIn(0.0, 2.0))
        val cx = ddx * gain * (if (invertX) -1 else 1) + resX
        val cy = ddy * gain * (if (invertY) -1 else 1) + resY
        val ix = cx.toInt(); val iy = cy.toInt()
        resX = cx - ix; resY = cy - iy
        if (ix != 0 || iy != 0) out += Action.Move(ix, iy)
        return out
    }

    private fun resetMotion() {
        fx.reset(); fy.reset(); last = null; lastTs = 0L; resX = 0.0; resY = 0.0; scrollAccum = 0.0; freezeUntil = 0
    }

    private fun dist(a: P, b: P) = hypot((a.x - b.x).toDouble(), (a.y - b.y).toDouble()).toFloat()

    companion object {
        const val PINCH_ON = 0.30f
        const val PINCH_OFF = 0.45f
        const val CONFIRM_FRAMES = 2
        const val NEARER = 0.8f
        const val HOLD_FOR_DRAG_MS = 380L
        const val SCROLL_STEP = 0.035   // fraction of the image height per wheel notch
        const val DEADZONE = 0.0008     // fraction of the image per frame (camera/landmark jitter)
        const val BASE_COUNTS = 1400.0  // counts per full image width at sensitivity 1
        const val MIN_CUTOFF = 1.2
        const val BETA = 6.0
    }
}
