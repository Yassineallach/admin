package com.airpointer.remote.settings

import com.airpointer.remote.core.MotionConfig
import com.airpointer.remote.presenter.PointerMode
import com.airpointer.remote.presenter.RecenterMethod
import com.airpointer.remote.presenter.RemoteAction
import com.airpointer.remote.presenter.SlideKeys

data class AppSettings(
    // Pointer
    val sensitivity: Float = 1.0f,
    val acceleration: Float = 0.6f,
    val smoothing: Float = 0.5f,
    val deadzone: Float = 0.012f,
    val autoDriftCompensation: Boolean = true,
    val invertX: Boolean = false,
    val invertY: Boolean = false,
    val pointerMode: PointerMode = PointerMode.TOGGLE,
    val recenterOnActivate: Boolean = false,
    val laserOnActivate: Boolean = false,
    val recenterMethod: RecenterMethod = RecenterMethod.ABSOLUTE,
    val hostWidth: Int = 1920,
    val hostHeight: Int = 1080,
    val scrollStepDp: Int = 22,
    // Presentation
    val slideKeys: SlideKeys = SlideKeys.ARROWS,
    val volumeKeysEnabled: Boolean = true,
    val volumeUpAction: RemoteAction = RemoteAction.PREVIOUS_SLIDE,
    val volumeDownAction: RemoteAction = RemoteAction.NEXT_SLIDE,
    val tapAction: RemoteAction = RemoteAction.LEFT_CLICK,
    val doubleTapAction: RemoteAction = RemoteAction.NONE,
    val longPressAction: RemoteAction = RemoteAction.RIGHT_CLICK,
    val swipeLeftAction: RemoteAction = RemoteAction.NEXT_SLIDE,
    val swipeRightAction: RemoteAction = RemoteAction.PREVIOUS_SLIDE,
    val swipeUpAction: RemoteAction = RemoteAction.NONE,
    val swipeDownAction: RemoteAction = RemoteAction.NONE,
    val haptics: Boolean = true,
    val keepScreenOn: Boolean = true,
    // Connection
    val autoReconnect: Boolean = true,
    val lastHostAddress: String? = null,
    val lastHostName: String? = null,
    // Calibration (persisted gyro bias, rad/s)
    val gyroBiasX: Float = 0f,
    val gyroBiasY: Float = 0f,
    val gyroBiasZ: Float = 0f,
    val calibratedAtMs: Long = 0L,
) {
    fun motionConfig() = MotionConfig(
        sensitivity = sensitivity.toDouble(),
        acceleration = acceleration.toDouble(),
        smoothing = smoothing.toDouble(),
        deadzone = deadzone.toDouble(),
        autoDriftCompensation = autoDriftCompensation,
        invertX = invertX,
        invertY = invertY,
    )
}
