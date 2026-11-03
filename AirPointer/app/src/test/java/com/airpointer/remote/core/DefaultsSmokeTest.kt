package com.airpointer.remote.core

import com.airpointer.remote.settings.AppSettings
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI

class DefaultsSmokeTest {
    @Test
    fun defaultSettingsMoveTheCursor() {
        val p = AirMouseProcessor(AppSettings().motionConfig())
        val s = MotionSimulator(p, MotionSimulator.about(Vec3.X, 40 * PI / 180))
        s.run(1.0)
        s.totalX = 0; s.totalY = 0
        s.run(0.5, worldOmega = Vec3(0.0, 0.0, 0.6))
        s.run(0.5, worldOmega = Vec3(0.3, 0.0, 0.0))
        println("defaults: x=${s.totalX} y=${s.totalY}")
        assertTrue(s.totalX < -200 && s.totalY < -100)
    }
}
