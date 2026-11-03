package com.airpointer.remote.presenter

import android.os.Handler
import android.os.SystemClock
import com.airpointer.remote.core.CalibrationState
import com.airpointer.remote.core.PointerDelta
import com.airpointer.remote.core.Vec3
import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.airpointer.remote.hid.BluetoothHidController
import com.airpointer.remote.hid.HidDescriptor
import com.airpointer.remote.hid.HidReports
import com.airpointer.remote.hid.KeyCodes
import com.airpointer.remote.hid.MouseButtons
import com.airpointer.remote.hid.ReportAccumulator
import com.airpointer.remote.motion.SensorMotionSource
import com.airpointer.remote.settings.SettingsRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Orchestrates sensors → motion processor → report coalescing → HID, plus every presentation
 * action (keys, clicks, scrolling, recentering, calibration).
 *
 * Threading: UI calls are posted to the [io] thread; all report state lives on that thread.
 */
class PresenterController(
    private val hid: BluetoothHidController,
    private val motion: SensorMotionSource,
    private val settings: SettingsRepository,
    private val io: Handler,
    private val log: DiagnosticsLog,
    scope: CoroutineScope,
) {
    data class TrackingState(
        val paused: Boolean = false,
        val pointerActive: Boolean = true,
        val sensorsRunning: Boolean = false,
        val preview: Boolean = false,
    )

    data class MotionSnapshot(
        val gyroRateHz: Float = 0f,
        val accelRateHz: Float = 0f,
        val yawRate: Double = 0.0,
        val pitchRate: Double = 0.0,
        val bias: Vec3 = Vec3.ZERO,
        val up: Vec3 = Vec3.Z,
        val still: Boolean = false,
        val reportRateHz: Float = 0f,
        val reportsSent: Long = 0,
        val reportFailures: Long = 0,
        val processingUs: Float = 0f,
        val previewX: Float = 0f,
        val previewY: Float = 0f,
    )

    private val _tracking = MutableStateFlow(TrackingState())
    val tracking: StateFlow<TrackingState> = _tracking

    private val _calibration = MutableStateFlow<CalibrationState>(CalibrationState.Idle)
    val calibration: StateFlow<CalibrationState> = _calibration

    private val _snapshot = MutableStateFlow(MotionSnapshot())
    val snapshot: StateFlow<MotionSnapshot> = _snapshot

    // Gate inputs read from the io thread.
    @Volatile private var paused = false
    @Volatile private var pointerActive = true
    @Volatile private var previewEnabled = false
    @Volatile private var freezeUntilMs = 0L
    @Volatile private var calibrating = false

    // io-thread state.
    private val accumulator = ReportAccumulator()
    private var buttons = 0
    private var flushScheduled = false
    private var previewX = 0f
    private var previewY = 0f
    private var lastReportsSent = 0L
    private var lastSnapshotMs = 0L

    val sensorMode get() = motion.capabilities.mode

    init {
        motion.processor.setBias(settings.current.let { Vec3(it.gyroBiasX.toDouble(), it.gyroBiasY.toDouble(), it.gyroBiasZ.toDouble()) })
        motion.gate = ::gateOpen
        motion.onDelta = ::onMotionDelta
        motion.processor.calibrationListener = ::onCalibration

        scope.launch {
            settings.settings.map { it.motionConfig() }.distinctUntilChanged().collect {
                motion.processor.config = it
                motion.tilt.config = it
            }
        }
        scope.launch {
            settings.settings.map { it.pointerMode }.distinctUntilChanged().collect { mode ->
                setPointerActiveInternal(mode == PointerMode.TOGGLE, sendLaser = false)
            }
        }
        // Run sensors only when someone can use the output.
        scope.launch {
            combine(hid.state.map { it.connected }.distinctUntilChanged(), _tracking, _calibration) { connected, t, c ->
                !t.paused && (connected || t.preview) || c is CalibrationState.Running
            }.distinctUntilChanged().collect { shouldRun ->
                io.post {
                    if (shouldRun) motion.start() else motion.stop()
                    _tracking.update { it.copy(sensorsRunning = motion.running) }
                }
            }
        }
        // When the link drops, release any held buttons so nothing stays "stuck" on reconnect.
        scope.launch {
            hid.state.map { it.connected }.distinctUntilChanged().collect { connected ->
                if (!connected) io.post { buttons = 0; accumulator.clear() }
            }
        }
        io.post { startSnapshotTicker() }
    }

    // ------------------------------------------------------------------ gate & motion

    private fun gateOpen(): Boolean =
        !paused && pointerActive && !calibrating &&
            (hid.isConnected || previewEnabled) &&
            SystemClock.elapsedRealtime() >= freezeUntilMs

    private fun onMotionDelta(d: PointerDelta) {
        if (previewEnabled) {
            previewX = (previewX + d.dx).coerceIn(-PREVIEW_RANGE, PREVIEW_RANGE)
            previewY = (previewY + d.dy).coerceIn(-PREVIEW_RANGE, PREVIEW_RANGE)
        }
        if (!hid.isConnected) return
        accumulator.add(d.dx, d.dy)
        scheduleFlush()
    }

    private fun scheduleFlush() {
        if (!accumulator.hasPending || flushScheduled) return
        val wait = accumulator.waitNs(SystemClock.elapsedRealtimeNanos())
        if (wait == 0L) flush() else {
            flushScheduled = true
            io.postDelayed(flushRunnable, (wait / 1_000_000L).coerceAtLeast(1L))
        }
    }

    private val flushRunnable = Runnable { flushScheduled = false; flush() }

    private fun flush() {
        if (!hid.isConnected) { accumulator.clear(); return }
        val c = accumulator.drain(SystemClock.elapsedRealtimeNanos())
        hid.sendReport(HidDescriptor.REPORT_ID_MOUSE, HidReports.mouse(buttons, c.dx, c.dy, c.wheel, c.pan))
        if (accumulator.hasPending) scheduleFlush()
    }

    /** Sends the current button state immediately together with any pending motion. */
    private fun sendButtonsNow() {
        val c = accumulator.drain(SystemClock.elapsedRealtimeNanos())
        hid.sendReport(HidDescriptor.REPORT_ID_MOUSE, HidReports.mouse(buttons, c.dx, c.dy, c.wheel, c.pan))
    }

    /** Suppress pointer motion briefly so the tap on the screen does not shake the cursor. */
    private fun freezeMotion(ms: Long = CLICK_FREEZE_MS) {
        freezeUntilMs = SystemClock.elapsedRealtime() + ms
    }

    // ------------------------------------------------------------------ public API (any thread)

    fun perform(action: RemoteAction) {
        when (action) {
            RemoteAction.NONE -> Unit
            RemoteAction.NEXT_SLIDE -> nextSlide()
            RemoteAction.PREVIOUS_SLIDE -> previousSlide()
            RemoteAction.LEFT_CLICK -> click(MouseButtons.LEFT)
            RemoteAction.RIGHT_CLICK -> click(MouseButtons.RIGHT)
            RemoteAction.TOGGLE_POINTER -> togglePointer()
            RemoteAction.RECENTER -> recenter()
            RemoteAction.PAUSE_TRACKING -> setPaused(!paused)
            RemoteAction.START_SLIDESHOW -> key(KeyCodes.F5)
            RemoteAction.START_FROM_CURRENT -> key(KeyCodes.F5, KeyCodes.MOD_LEFT_SHIFT)
            RemoteAction.END_SLIDESHOW -> key(KeyCodes.ESCAPE)
            RemoteAction.BLACK_SCREEN -> key(KeyCodes.B)
            RemoteAction.WHITE_SCREEN -> key(KeyCodes.W)
            RemoteAction.LASER_POINTER -> key(KeyCodes.L, KeyCodes.MOD_LEFT_CTRL)
            RemoteAction.SCROLL_UP -> scroll(3)
            RemoteAction.SCROLL_DOWN -> scroll(-3)
        }
    }

    fun nextSlide() = key(if (settings.current.slideKeys == SlideKeys.ARROWS) KeyCodes.RIGHT_ARROW else KeyCodes.PAGE_DOWN)
    fun previousSlide() = key(if (settings.current.slideKeys == SlideKeys.ARROWS) KeyCodes.LEFT_ARROW else KeyCodes.PAGE_UP)

    /** Press + release a key (with optional modifiers). */
    fun key(code: Int, modifiers: Int = 0) = io.post {
        if (!hid.isConnected) return@post
        hid.sendReport(HidDescriptor.REPORT_ID_KEYBOARD, HidReports.keyboard(modifiers, code))
        io.postDelayed({ hid.sendReport(HidDescriptor.REPORT_ID_KEYBOARD, HidReports.keyboard(0)) }, KEY_HOLD_MS)
    }

    fun setButton(button: Int, down: Boolean) {
        freezeMotion()
        io.post {
            buttons = if (down) buttons or button else buttons and button.inv()
            if (hid.isConnected) sendButtonsNow()
        }
    }

    fun click(button: Int) {
        setButton(button, true)
        io.postDelayed({
            buttons = buttons and button.inv()
            if (hid.isConnected) sendButtonsNow()
        }, CLICK_HOLD_MS)
    }

    fun scroll(steps: Int) = io.post {
        if (!hid.isConnected || steps == 0) return@post
        accumulator.add(0, 0, wheel = steps)
        scheduleFlush()
    }

    fun setPaused(value: Boolean) {
        paused = value
        _tracking.update { it.copy(paused = value) }
        log.i(TAG, if (value) "Tracking paused" else "Tracking resumed")
    }

    fun togglePointer() = setPointerActiveInternal(!pointerActive, sendLaser = true)

    /** Hold-to-point: called on press/release of the pointer button. */
    fun setPointerHeld(held: Boolean) = setPointerActiveInternal(held, sendLaser = true)

    private fun setPointerActiveInternal(active: Boolean, sendLaser: Boolean) {
        if (pointerActive == active && sendLaser) return
        pointerActive = active
        _tracking.update { it.copy(pointerActive = active) }
        io.post { motion.processor.resetMotion() }
        if (!sendLaser) return
        val s = settings.current
        if (active && s.recenterOnActivate) recenter()
        if (s.laserOnActivate) {
            // PowerPoint slideshow: Ctrl+L = laser pointer, Ctrl+A = back to arrow.
            if (active) key(KeyCodes.L, KeyCodes.MOD_LEFT_CTRL) else key(KeyCodes.A, KeyCodes.MOD_LEFT_CTRL)
        }
    }

    fun setPreview(enabled: Boolean) {
        previewEnabled = enabled
        io.post { previewX = 0f; previewY = 0f }
        _tracking.update { it.copy(preview = enabled) }
    }

    fun recenter() = io.post {
        motion.processor.resetMotion()
        motion.tilt.recenter()
        previewX = 0f; previewY = 0f
        if (!hid.isConnected) return@post
        accumulator.clear()
        when (settings.current.recenterMethod) {
            RecenterMethod.ABSOLUTE -> {
                val c = HidDescriptor.ABSOLUTE_MAX / 2
                hid.sendReport(HidDescriptor.REPORT_ID_ABSOLUTE, HidReports.absolute(0, c, c))
            }
            RecenterMethod.RELATIVE_SWEEP -> relativeSweep()
        }
        freezeMotion(120)
    }

    /** Fallback recenter for hosts that ignore absolute pointers: slam to the corner, then move. */
    private fun relativeSweep() {
        repeat(4) { hid.sendReport(HidDescriptor.REPORT_ID_MOUSE, HidReports.mouse(buttons, -32767, -32767)) }
        val s = settings.current
        var remainingX = s.hostWidth / 2
        var remainingY = s.hostHeight / 2
        var step = 0
        while (remainingX > 0 || remainingY > 0) {
            val dx = minOf(SWEEP_STEP, remainingX); val dy = minOf(SWEEP_STEP, remainingY)
            remainingX -= dx; remainingY -= dy
            step++
            io.postDelayed({ hid.sendReport(HidDescriptor.REPORT_ID_MOUSE, HidReports.mouse(buttons, dx, dy)) }, step * 8L)
        }
    }

    fun calibrate() {
        calibrating = true
        io.post {
            if (!motion.running) motion.start()
            motion.processor.startCalibration()
        }
    }

    fun cancelCalibration() = io.post { motion.processor.cancelCalibration() }

    private fun onCalibration(state: CalibrationState) {
        _calibration.value = state
        if (state !is CalibrationState.Running) calibrating = false
        if (state is CalibrationState.Done) {
            log.i(TAG, "Calibrated gyro bias: %.4f %.4f %.4f rad/s".format(state.bias.x, state.bias.y, state.bias.z))
            settings.update {
                it.copy(gyroBiasX = state.bias.x.toFloat(), gyroBiasY = state.bias.y.toFloat(),
                    gyroBiasZ = state.bias.z.toFloat(), calibratedAtMs = System.currentTimeMillis())
            }
            recenter()
        } else if (state is CalibrationState.Failed) {
            log.w(TAG, "Calibration failed: ${state.reason}")
        }
    }

    fun clearCalibrationResult() {
        if (_calibration.value !is CalibrationState.Running) _calibration.value = CalibrationState.Idle
    }

    /** Diagnostics: draw a 300-count square with the cursor to verify the HID link without sensors. */
    fun sendTestPattern() = io.post {
        if (!hid.isConnected) return@post
        val dirs = listOf(1 to 0, 0 to 1, -1 to 0, 0 to -1)
        var t = 0L
        for ((sx, sy) in dirs) repeat(30) {
            t += 10
            io.postDelayed({ hid.sendReport(HidDescriptor.REPORT_ID_MOUSE, HidReports.mouse(buttons, sx * 10, sy * 10)) }, t)
        }
    }

    // ------------------------------------------------------------------ diagnostics snapshot

    private fun startSnapshotTicker() = io.post(snapshotTicker)

    private val snapshotTicker = object : Runnable {
        override fun run() {
            val now = SystemClock.elapsedRealtime()
            val sent = hid.reportsSent.get()
            val span = (now - lastSnapshotMs).coerceAtLeast(1)
            val rate = (sent - lastReportsSent) * 1000f / span
            lastReportsSent = sent; lastSnapshotMs = now
            val p = motion.processor
            _snapshot.value = MotionSnapshot(
                gyroRateHz = motion.gyroRateHz,
                accelRateHz = motion.accelRateHz,
                yawRate = p.yawRate,
                pitchRate = p.pitchRate,
                bias = p.bias,
                up = p.up,
                still = p.isStill,
                reportRateHz = rate,
                reportsSent = sent,
                reportFailures = hid.reportFailures.get(),
                processingUs = motion.lastProcessingNs / 1000f,
                previewX = previewX,
                previewY = previewY,
            )
            io.postDelayed(this, if (motion.running) 33L else 500L)
        }
    }

    companion object {
        private const val TAG = "Presenter"
        const val CLICK_FREEZE_MS = 140L
        const val CLICK_HOLD_MS = 35L
        const val KEY_HOLD_MS = 25L
        const val SWEEP_STEP = 40
        const val PREVIEW_RANGE = 1200f
    }
}
