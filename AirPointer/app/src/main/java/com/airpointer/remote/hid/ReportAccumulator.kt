package com.airpointer.remote.hid

/**
 * Coalesces motion produced at sensor rate (~200 Hz) into HID reports sent at most every
 * [minIntervalNs]. Nothing is lost: movement that exceeds one report's range is carried over.
 * Pure logic so it can be unit tested; the caller owns scheduling.
 */
class ReportAccumulator(val minIntervalNs: Long = 7_500_000L) {
    var pendingX = 0L; private set
    var pendingY = 0L; private set
    var pendingWheel = 0; private set
    var pendingPan = 0; private set
    private var lastSendNs = Long.MIN_VALUE / 2

    val hasPending get() = pendingX != 0L || pendingY != 0L || pendingWheel != 0 || pendingPan != 0

    fun add(dx: Int, dy: Int, wheel: Int = 0, pan: Int = 0) {
        pendingX += dx; pendingY += dy; pendingWheel += wheel; pendingPan += pan
    }

    /** Nanoseconds until a report may be sent (0 = now). */
    fun waitNs(nowNs: Long): Long = (lastSendNs + minIntervalNs - nowNs).coerceAtLeast(0L)

    data class Chunk(val dx: Int, val dy: Int, val wheel: Int, val pan: Int)

    /** Take the next report's worth of movement and mark it as sent at [nowNs]. */
    fun drain(nowNs: Long): Chunk {
        val dx = pendingX.coerceIn(-32767L, 32767L).toInt()
        val dy = pendingY.coerceIn(-32767L, 32767L).toInt()
        val w = pendingWheel.coerceIn(-127, 127)
        val p = pendingPan.coerceIn(-127, 127)
        pendingX -= dx; pendingY -= dy; pendingWheel -= w; pendingPan -= p
        lastSendNs = nowNs
        return Chunk(dx, dy, w, p)
    }

    fun clear() {
        pendingX = 0; pendingY = 0; pendingWheel = 0; pendingPan = 0
    }
}
