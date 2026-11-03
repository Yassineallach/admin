package com.airpointer.remote.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Random
import kotlin.math.PI
import kotlin.math.abs

class AirMouseProcessorTest {

    private val linear = MotionConfig(sensitivity = 1.0, acceleration = 0.0, smoothing = 0.3, deadzone = 0.0, autoDriftCompensation = false)

    private fun sim(cfg: MotionConfig = linear, orientation: Array<DoubleArray> = MotionSimulator.identity()): MotionSimulator {
        val p = AirMouseProcessor(cfg)
        return MotionSimulator(p, orientation).also { it.run(0.3) } // settle gravity + filters
    }

    @Test
    fun yawLeftMovesCursorLeftByExpectedAmount() {
        val s = sim()
        val out = s.run(1.0, worldOmega = Vec3(0.0, 0.0, 0.5)) // turn left 0.5 rad
        s.run(0.5) // let the filter catch up
        val total = s.totalX
        // 0.5 rad × 1100 counts/rad = 550 counts to the left.
        assertEquals(-550.0, total.toDouble(), 20.0)
        assertTrue("vertical leak ${s.totalY}", abs(s.totalY) <= 5)
        assertTrue(out.dx < 0)
    }

    @Test
    fun pitchUpMovesCursorUp() {
        val s = sim()
        s.run(1.0, worldOmega = Vec3(0.4, 0.0, 0.0)) // top of the phone tilts up
        s.run(0.5)
        assertEquals(-440.0, s.totalY.toDouble(), 20.0)
        assertTrue("horizontal leak ${s.totalX}", abs(s.totalX) <= 5)
    }

    @Test
    fun pointerIsIndependentOfRollInTheHand() {
        // Phone rolled 50° about its pointing (Y) axis, then turned about the world vertical.
        val rolled = MotionSimulator.about(Vec3.Y, 50 * PI / 180)
        val s = sim(orientation = rolled)
        s.run(1.0, worldOmega = Vec3(0.0, 0.0, -0.5)) // turn right
        s.run(0.5)
        assertEquals(550.0, s.totalX.toDouble(), 25.0)
        assertTrue("vertical leak ${s.totalY}", abs(s.totalY) <= 10)
    }

    @Test
    fun pointerIsIndependentOfTiltTowardsTheUser() {
        // Screen tilted 40° toward the user (typical remote grip), yaw about world vertical.
        val tilted = MotionSimulator.about(Vec3.X, 40 * PI / 180)
        val s = sim(orientation = tilted)
        s.run(1.0, worldOmega = Vec3(0.0, 0.0, 0.5))
        s.run(0.5)
        assertEquals(-550.0, s.totalX.toDouble(), 25.0)
        assertTrue("vertical leak ${s.totalY}", abs(s.totalY) <= 10)
    }

    @Test
    fun calibrationRemovesGyroBias() {
        val p = AirMouseProcessor(linear)
        val s = MotionSimulator(p)
        val bias = Vec3(0.02, -0.015, 0.03)
        var done: CalibrationState? = null
        p.calibrationListener = { if (it is CalibrationState.Done) done = it }
        s.run(0.2, gyroBias = bias)
        p.startCalibration(1.0)
        s.run(1.5, gyroBias = bias)
        assertTrue(done is CalibrationState.Done)
        assertEquals(bias.x, p.bias.x, 1e-3); assertEquals(bias.y, p.bias.y, 1e-3); assertEquals(bias.z, p.bias.z, 1e-3)
        s.totalX = 0; s.totalY = 0
        s.run(10.0, gyroBias = bias)
        assertTrue("drift after calibration ${s.totalX},${s.totalY}", abs(s.totalX) <= 2 && abs(s.totalY) <= 2)
    }

    @Test
    fun uncalibratedBiasDriftsButAutoCompensationStopsIt() {
        val bias = Vec3(0.0, 0.0, 0.01) // 0.57°/s yaw drift
        val raw = MotionSimulator(AirMouseProcessor(linear)).apply { run(0.3, gyroBias = bias) }
        raw.totalX = 0
        raw.run(10.0, gyroBias = bias)
        assertTrue("expected drift without compensation, got ${raw.totalX}", abs(raw.totalX) > 80)

        val comp = MotionSimulator(AirMouseProcessor(linear.copy(autoDriftCompensation = true, deadzone = 0.012)))
        comp.run(0.3, gyroBias = bias)
        comp.totalX = 0
        comp.run(10.0, gyroBias = bias)
        assertTrue("drift with compensation ${comp.totalX}", abs(comp.totalX) <= 3)
    }

    @Test
    fun calibrationRestartsWhenThePhoneMoves() {
        val p = AirMouseProcessor(linear)
        val s = MotionSimulator(p)
        var last: CalibrationState? = null
        p.calibrationListener = { last = it }
        s.run(0.2)
        p.startCalibration(1.0)
        s.run(0.3)
        s.run(0.2, worldOmega = Vec3(0.0, 0.0, 1.0)) // bump
        assertTrue((last as CalibrationState.Running).restarts > 0)
        s.run(1.5)
        assertTrue(last is CalibrationState.Done)
        assertEquals(0.0, p.bias.norm(), 2e-3)
    }

    @Test
    fun handTremorIsSuppressed() {
        val rnd = Random(42)
        val cfg = linear.copy(smoothing = 0.6, deadzone = 0.012)
        val s = sim(cfg)
        s.totalX = 0; s.totalY = 0
        s.run(5.0, noise = { Vec3(rnd.nextGaussian() * 0.008, rnd.nextGaussian() * 0.008, rnd.nextGaussian() * 0.008) })
        assertTrue("jitter ${s.totalX},${s.totalY}", abs(s.totalX) <= 6 && abs(s.totalY) <= 6)
    }

    @Test
    fun slowMovementIsNotLostToRounding() {
        val s = sim()
        s.run(4.0, worldOmega = Vec3(0.0, 0.0, -0.02)) // 0.08 rad very slowly → ~88 counts
        s.run(0.5)
        assertEquals(88.0, s.totalX.toDouble(), 6.0)
    }

    @Test
    fun accelerationBoostsFastMovesOnly() {
        val accel = linear.copy(acceleration = 1.0)
        val slow = sim(accel).apply { run(4.0, worldOmega = Vec3(0.0, 0.0, -0.05)); run(0.5) }
        assertEquals(220.0, slow.totalX.toDouble(), 12.0) // 0.2 rad below threshold: unchanged
        val fast = sim(accel).apply { run(0.2, worldOmega = Vec3(0.0, 0.0, -2.0)); run(0.5) }
        assertTrue("fast ${fast.totalX} should exceed linear 440", fast.totalX > 600)
    }

    @Test
    fun closedGateProducesNothingAndDoesNotJumpWhenReopened() {
        val s = sim()
        val off = s.run(1.0, worldOmega = Vec3(0.0, 0.0, 1.0), emit = false)
        assertEquals(PointerDelta.ZERO, off)
        s.totalX = 0
        s.run(0.5, emit = true)
        assertTrue("jump after reopening ${s.totalX}", abs(s.totalX) <= 3)
    }

    @Test
    fun invertAndSensitivityApply() {
        val s = sim(linear.copy(sensitivity = 2.0, invertX = true))
        s.run(1.0, worldOmega = Vec3(0.0, 0.0, 0.25))
        s.run(0.5)
        assertEquals(550.0, s.totalX.toDouble(), 20.0)
    }

    @Test
    fun sensorGapResetsWithoutSpike() {
        val p = AirMouseProcessor(linear)
        val s = MotionSimulator(p).apply { run(0.5) }
        s.t += 2_000_000_000L // 2 s pause (sensors unregistered)
        val d = s.run(0.5)
        assertTrue(abs(d.dx) <= 1 && abs(d.dy) <= 1)
    }

    @Test
    fun rightAxisFallbackWhenPointingStraightUp() {
        val r = AirMouseProcessor.rightAxis(Vec3(0.0, 1.0, 0.0))
        assertEquals(1.0, r.norm(), 1e-9)
        assertEquals(0.0, r dot Vec3(0.0, 1.0, 0.0), 1e-9)
    }
}
