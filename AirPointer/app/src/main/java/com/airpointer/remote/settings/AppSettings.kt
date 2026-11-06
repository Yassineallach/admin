package com.airpointer.remote.settings

import com.airpointer.remote.core.MotionConfig
import com.airpointer.remote.presenter.PointerMode
import com.airpointer.remote.presenter.RemoteAction
import com.airpointer.remote.presenter.SlideKeys
import com.airpointer.remote.transport.TransportKind

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
    val hostWidth: Int = 1920,
    val hostHeight: Int = 1080,
    val scrollStepDp: Int = 22,
    // Presentation
    val slideKeys: SlideKeys = SlideKeys.ARROWS,
    val volumeKeysEnabled: Boolean = true,
    val volumeUpAction: RemoteAction = RemoteAction.PREVIOUS_SLIDE,
    val volumeDownAction: RemoteAction = RemoteAction.NEXT_SLIDE,
    // The pad is where the gripping thumb rests, so by default it never clicks: a click there
    // lands wherever the moving cursor happens to be (taskbar, desktop icons, context menus).
    val tapAction: RemoteAction = RemoteAction.NONE,
    val doubleTapAction: RemoteAction = RemoteAction.NONE,
    val longPressAction: RemoteAction = RemoteAction.NONE,
    val swipeLeftAction: RemoteAction = RemoteAction.NEXT_SLIDE,
    val swipeRightAction: RemoteAction = RemoteAction.PREVIOUS_SLIDE,
    val swipeUpAction: RemoteAction = RemoteAction.NONE,
    val swipeDownAction: RemoteAction = RemoteAction.NONE,
    val haptics: Boolean = true,
    val keepScreenOn: Boolean = true,
    // Connection
    val transport: TransportKind = TransportKind.BLUETOOTH,
    val wifiHost: String? = null,
    val wifiPort: Int = 47778,
    val wifiPin: String? = null,
    val wifiName: String? = null,
    // Media player remote
    val mediaPlayer: String = "VLC",
    val vlcHost: String? = null,
    val vlcPort: Int = 8080,
    val vlcPassword: String? = null,
    /**
     * Maximum mouse reports per second. The HID QoS asks the link for ~800 bytes/s; a report
     * costs ~10 bytes on air, so streaming above ~70 Hz overruns it and the stack silently
     * queues or drops reports (the cursor freezes even though every send "succeeds").
     */
    val reportRateHz: Int = 60,
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
