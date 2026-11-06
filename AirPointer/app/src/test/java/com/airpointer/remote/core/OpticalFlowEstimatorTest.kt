package com.airpointer.remote.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Random
import kotlin.math.floor

class OpticalFlowEstimatorTest {

    /** Smooth random texture (like a ceiling, wood grain or desk mat) sampled with bilinear interpolation. */
    private class Texture(seed: Long, val size: Int = 512) {
        private val px = FloatArray(size * size)
        init {
            val r = Random(seed)
            val coarse = FloatArray(64 * 64) { r.nextFloat() * 255f }
            for (y in 0 until size) for (x in 0 until size) px[y * size + x] = sampleGrid(coarse, 64, x / 8f, y / 8f)
        }
        private fun sampleGrid(g: FloatArray, n: Int, x: Float, y: Float): Float {
            val x0 = floor(x).toInt().coerceIn(0, n - 2); val y0 = floor(y).toInt().coerceIn(0, n - 2)
            val fx = x - x0; val fy = y - y0
            val a = g[y0 * n + x0]; val b = g[y0 * n + x0 + 1]; val c = g[(y0 + 1) * n + x0]; val d = g[(y0 + 1) * n + x0 + 1]
            return a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy
        }
        fun at(x: Float, y: Float) = sampleGrid(px, size, x, y)
    }

    /** Render a 320×240 camera frame of the texture viewed at offset (ox, oy). */
    private fun frame(t: Texture, ox: Float, oy: Float, brightness: Float = 1f, noise: Random? = null): ByteArray {
        val w = 320; val h = 240
        return ByteArray(w * h) { i ->
            val x = i % w; val y = i / w
            var v = t.at(100 + ox + x * 0.5f, 100 + oy + y * 0.5f) * brightness
            if (noise != null) v += noise.nextGaussian().toFloat() * 3f
            v.coerceIn(0f, 255f).toInt().toByte()
        }
    }

    private fun shift(est: OpticalFlowEstimator, a: ByteArray, b: ByteArray): OpticalFlowEstimator.Result {
        est.reset()
        est.update(est.prepare(a, 320, 240, 320))
        return est.update(est.prepare(b, 320, 240, 320))!!
    }

    @Test
    fun recoversIntegerAndSubPixelShifts() {
        val t = Texture(1)
        val est = OpticalFlowEstimator()
        // Camera moves +ox in texture → scene appears to move -ox. One grid px = 4 frame px = 2 texture units.
        for ((ox, oy) in listOf(6f to 0f, 0f to -8f, 10f to 14f, -21f to 5f, 3f to 1f)) {
            val r = shift(est, frame(t, 0f, 0f), frame(t, ox, oy))
            assertEquals("dx for $ox,$oy", -ox / 2, r.dx, 0.35f)
            assertEquals("dy for $ox,$oy", -oy / 2, r.dy, 0.35f)
            assertTrue("confident on texture: ${r.confidence}", r.confidence > 0.5f)
        }
    }

    @Test
    fun largeShiftsUpToAQuarterOfTheView() {
        val t = Texture(2)
        val r = shift(OpticalFlowEstimator(), frame(t, 0f, 0f), frame(t, 40f, -30f))
        assertEquals(-20f, r.dx, 0.5f); assertEquals(15f, r.dy, 0.5f)
    }

    @Test
    fun exposureChangeIsNotMotion() {
        val t = Texture(3)
        val r = shift(OpticalFlowEstimator(), frame(t, 0f, 0f), frame(t, 0f, 0f, brightness = 0.7f))
        assertEquals(0f, r.dx, 0.2f); assertEquals(0f, r.dy, 0.2f)
    }

    @Test
    fun sensorNoiseDoesNotCreateDrift() {
        val t = Texture(4)
        val noise = Random(9)
        val est = OpticalFlowEstimator()
        est.update(est.prepare(frame(t, 0f, 0f, noise = noise), 320, 240, 320))
        var sx = 0f; var sy = 0f
        repeat(60) {
            val r = est.update(est.prepare(frame(t, 0f, 0f, noise = noise), 320, 240, 320))!!
            sx += r.dx; sy += r.dy
        }
        assertTrue("accumulated drift $sx,$sy", kotlin.math.abs(sx) < 3 && kotlin.math.abs(sy) < 3)
    }

    @Test
    fun blankSurfaceHasNoConfidence() {
        val flat = ByteArray(320 * 240) { 128.toByte() }
        val r = shift(OpticalFlowEstimator(), flat, flat)
        assertTrue("confidence ${r.confidence}", r.confidence < 0.05f)
    }

    @Test
    fun handlesRowStridePadding() {
        val t = Texture(5)
        fun padded(src: ByteArray) = ByteArray(336 * 240) { i -> val x = i % 336; val y = i / 336; if (x < 320) src[y * 320 + x] else 0 }
        val est = OpticalFlowEstimator()
        est.update(est.prepare(padded(frame(t, 0f, 0f)), 320, 240, 336))
        val r = est.update(est.prepare(padded(frame(t, 8f, 0f)), 320, 240, 336))!!
        assertEquals(-4f, r.dx, 0.35f)
    }
}
