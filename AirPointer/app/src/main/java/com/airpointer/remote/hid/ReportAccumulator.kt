package com.airpointer.remote.hid

/**
 * Coalesces motion produced at sensor rate (~200 Hz) into HID reports sent at most every
 * [minIntervalNs]. Nothing is lost: movement that exceeds one report's range is carried over.
 * Pure logic so it can be unit tested; the caller owns scheduling.
 */
class ReportAccumulator(
    var minIntervalNs: Long = 16_666_667L,
    val maxDelta: Int = HidDescriptor.MOUSE_MAX_DELTA,
) {
    var pendingX = 0L; private set
    var pendingY = 0L; private set
    var pendingWheel = 0; private set
    private var lastSendNs = Long.MIN_VALUE / 2

    val hasPending get() = pendingX != 0L || pendingY != 0L || pendingWheel != 0

    fun add(dx: Int, dy: Int, wheel: Int = 0) {
        pendingX += dx; pendingY += dy; pendingWheel += wheel
    }

    /** Nanoseconds until a report may be sent (0 = now). */
    fun waitNs(nowNs: Long): Long = (lastSendNs + minIntervalNs - nowNs).coerceAtLeast(0L)

    data class Chunk(val dx: Int, val dy: Int, val wheel: Int)

    /** Take the next report's worth of movement and mark it as sent at [nowNs]. */
    fun drain(nowNs: Long): Chunk {
        val m = maxDelta.toLong()
        val dx = pendingX.coerceIn(-m, m).toInt()
        val dy = pendingY.coerceIn(-m, m).toInt()
        val w = pendingWheel.coerceIn(-127, 127)
        pendingX -= dx; pendingY -= dy; pendingWheel -= w
        lastSendNs = nowNs
        return Chunk(dx, dy, w)
    }

    fun clear() {
        pendingX = 0; pendingY = 0; pendingWheel = 0
    }
}
