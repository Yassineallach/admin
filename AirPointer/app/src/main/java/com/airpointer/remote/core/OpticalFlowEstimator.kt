package com.airpointer.remote.core

import kotlin.math.sqrt

/**
 * Global image translation between consecutive camera frames (block matching on an image
 * pyramid with sub-pixel refinement): the same principle as an optical mouse sensor, which
 * correlates successive images of the surface under it.
 *
 * Input: 8-bit luma (Y plane). Frames are reduced to [width]×[height] (default 80×60), normalised
 * (zero mean, unit variance) so exposure changes do not register as motion, then matched
 * coarse-to-fine. Maximum trackable shift ≈ ±22 px of 80 per frame (≈ 27 % of the view).
 *
 * The result carries a confidence (0–1) combining scene texture and match distinctness, so the
 * caller can stop the cursor instead of producing fake motion on blank or blurred surfaces.
 */
class OpticalFlowEstimator(val width: Int = 80, val height: Int = 60) {

    data class Result(val dx: Float, val dy: Float, val confidence: Float, val texture: Float)

    private var prev: FloatArray? = null
    private var prevPyramid: List<Level>? = null

    private class Level(val w: Int, val h: Int, val px: FloatArray)

    fun reset() { prev = null; prevPyramid = null }

    /** Downsample a Y plane (with row stride) into the working grid. */
    fun prepare(y: ByteArray, srcW: Int, srcH: Int, rowStride: Int): FloatArray {
        val out = FloatArray(width * height)
        val sx = srcW.toFloat() / width
        val sy = srcH.toFloat() / height
        for (j in 0 until height) {
            val y0 = (j * sy).toInt(); val y1 = ((j + 1) * sy).toInt().coerceAtMost(srcH).coerceAtLeast(y0 + 1)
            for (i in 0 until width) {
                val x0 = (i * sx).toInt(); val x1 = ((i + 1) * sx).toInt().coerceAtMost(srcW).coerceAtLeast(x0 + 1)
                var sum = 0; var n = 0
                // Sparse sampling (every 2nd pixel) keeps this ~O(grid) per frame.
                var yy = y0
                while (yy < y1) {
                    var xx = x0
                    val row = yy * rowStride
                    while (xx < x1) { sum += y[row + xx].toInt() and 0xFF; n++; xx += 2 }
                    yy += 2
                }
                out[j * width + i] = sum.toFloat() / n
            }
        }
        return out
    }

    /** Feed one prepared frame; returns the shift of the scene from the previous frame (px of the grid). */
    fun update(frame: FloatArray): Result? {
        val (norm, texture) = normalise(frame)
        val pyr = pyramid(norm)
        val p = prevPyramid
        prevPyramid = pyr
        prev = norm
        if (p == null) return null

        // Coarse to fine: level 2 (¼) exhaustive ±4, then refine ±2 at each finer level.
        var bx = 0; var by = 0
        for (lvl in 2 downTo 0) {
            val radius = if (lvl == 2) 4 else 2
            val a = p[lvl]; val b = pyr[lvl]
            if (lvl < 2) { bx *= 2; by *= 2 }
            var best = Float.MAX_VALUE; var nbx = bx; var nby = by
            for (dy in by - radius..by + radius) for (dx in bx - radius..bx + radius) {
                val c = cost(a, b, dx, dy)
                if (c < best) { best = c; nbx = dx; nby = dy }
            }
            bx = nbx; by = nby
        }
        val a = p[0]; val b = pyr[0]
        val c0 = cost(a, b, bx, by)
        // Sub-pixel: parabola through the cost minimum and its neighbours on each axis.
        val subX = parabola(cost(a, b, bx - 1, by), c0, cost(a, b, bx + 1, by))
        val subY = parabola(cost(a, b, bx, by - 1), c0, cost(a, b, bx, by + 1))
        // Distinctness: how much worse the surrounding positions are than the best one.
        var ring = 0f; var n = 0
        for (dy in -2..2) for (dx in -2..2) {
            if (dx == 0 && dy == 0) continue
            ring += cost(a, b, bx + dx, by + dy); n++
        }
        ring /= n
        val distinct = if (ring <= 1e-6f) 0f else ((ring - c0) / ring).coerceIn(0f, 1f)
        val textureScore = (texture / 12f).coerceIn(0f, 1f) // std-dev of luma in grey levels
        val confidence = (distinct * 1.6f).coerceIn(0f, 1f) * textureScore
        return Result(bx + subX, by + subY, confidence, texture)
    }

    /** Mean squared difference over the overlap of a(x) and b(x + d). Scene moved by d. */
    private fun cost(a: Level, b: Level, dx: Int, dy: Int): Float {
        val x0 = maxOf(0, -dx); val x1 = minOf(a.w, a.w - dx)
        val y0 = maxOf(0, -dy); val y1 = minOf(a.h, a.h - dy)
        if (x1 - x0 < a.w / 2 || y1 - y0 < a.h / 2) return Float.MAX_VALUE / 4
        var sum = 0f
        for (y in y0 until y1) {
            val ra = y * a.w; val rb = (y + dy) * b.w + dx
            for (x in x0 until x1) { val d = a.px[ra + x] - b.px[rb + x]; sum += d * d }
        }
        return sum / ((x1 - x0) * (y1 - y0))
    }

    private fun parabola(l: Float, c: Float, r: Float): Float {
        if (l >= Float.MAX_VALUE / 8 || r >= Float.MAX_VALUE / 8) return 0f
        val denom = l - 2 * c + r
        return if (denom <= 1e-9f) 0f else ((l - r) / (2 * denom)).coerceIn(-0.5f, 0.5f)
    }

    private fun normalise(f: FloatArray): Pair<FloatArray, Float> {
        var mean = 0.0
        for (v in f) mean += v
        mean /= f.size
        var varSum = 0.0
        for (v in f) { val d = v - mean; varSum += d * d }
        val std = sqrt(varSum / f.size).toFloat()
        val inv = if (std < 1e-3f) 0f else 1f / std
        return FloatArray(f.size) { ((f[it] - mean) * inv).toFloat() } to std
    }

    private fun pyramid(base: FloatArray): List<Level> {
        val l0 = Level(width, height, base)
        val l1 = half(l0)
        return listOf(l0, l1, half(l1))
    }

    private fun half(l: Level): Level {
        val w = l.w / 2; val h = l.h / 2
        val out = FloatArray(w * h)
        for (y in 0 until h) for (x in 0 until w) {
            val i = 2 * y * l.w + 2 * x
            out[y * w + x] = (l.px[i] + l.px[i + 1] + l.px[i + l.w] + l.px[i + l.w + 1]) * 0.25f
        }
        return Level(w, h, out)
    }
}
