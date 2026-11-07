package com.airpointer.remote.hand

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.SystemClock
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.airpointer.remote.core.HandGestureMouse
import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.airpointer.remote.hid.MouseButtons
import com.airpointer.remote.presenter.PresenterController
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarker
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarkerResult
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.concurrent.Executors

/**
 * Camera air mouse: CameraX frames → MediaPipe Hand Landmarker (on-device, bundled model) →
 * [HandGestureMouse] → the presenter's normal report path (Bluetooth or Wi-Fi).
 */
class HandTrackingController(
    private val context: Context,
    private val presenter: PresenterController,
    private val log: DiagnosticsLog,
) {
    enum class Facing(val label: String) { FRONT("Front camera"), BACK("Back camera") }

    data class Status(
        val running: Boolean = false,
        val pose: HandGestureMouse.Pose = HandGestureMouse.Pose.NO_HAND,
        val fps: Float = 0f,
        val inferenceMs: Long = 0,
        val landmarks: List<HandGestureMouse.P> = emptyList(),
        val error: String? = null,
    )

    private val _status = MutableStateFlow(Status())
    val status: StateFlow<Status> = _status

    val gestures = HandGestureMouse()
    @Volatile var facing = Facing.FRONT

    private val analysisExecutor = Executors.newSingleThreadExecutor()
    private var provider: ProcessCameraProvider? = null
    private var landmarker: HandLandmarker? = null
    private var frames = 0
    private var fpsStart = 0L
    @Volatile private var lastFrameStart = 0L

    fun start(owner: LifecycleOwner) {
        try {
            landmarker = HandLandmarker.createFromOptions(context, HandLandmarker.HandLandmarkerOptions.builder()
                .setBaseOptions(BaseOptions.builder().setModelAssetPath(MODEL).build())
                .setRunningMode(RunningMode.LIVE_STREAM)
                .setNumHands(1)
                .setMinHandDetectionConfidence(0.5f)
                .setMinHandPresenceConfidence(0.5f)
                .setMinTrackingConfidence(0.5f)
                .setResultListener(::onResult)
                .setErrorListener { e -> _status.value = _status.value.copy(error = "Hand tracking error: ${e.message}") }
                .build())
        } catch (e: Throwable) { // UnsatisfiedLinkError on processors MediaPipe has no native code for (x86_64)
            _status.value = Status(error = if (e is UnsatisfiedLinkError) "Hand tracking is not available on this processor (MediaPipe supports ARM phones)."
                else "Hand tracking unavailable on this phone: ${e.message}")
            log.e(TAG, "HandLandmarker: ${e.message}")
            return
        }
        val future = ProcessCameraProvider.getInstance(context)
        future.addListener({
            try {
                val p = future.get(); provider = p
                p.unbindAll()
                val selector = if (facing == Facing.FRONT) CameraSelector.DEFAULT_FRONT_CAMERA else CameraSelector.DEFAULT_BACK_CAMERA
                if (!p.hasCamera(selector)) { _status.value = Status(error = "No ${facing.label.lowercase()} on this phone."); return@addListener }
                val analysis = ImageAnalysis.Builder()
                    .setResolutionSelector(ResolutionSelector.Builder().setResolutionStrategy(
                        ResolutionStrategy(Size(640, 480), ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER)).build())
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                    .build()
                analysis.setAnalyzer(analysisExecutor, ::analyze)
                p.bindToLifecycle(owner, selector, analysis)
                fpsStart = SystemClock.elapsedRealtime(); frames = 0
                _status.value = Status(running = true)
                log.i(TAG, "Hand tracking started (${facing.label})")
            } catch (e: Exception) {
                _status.value = Status(error = "Camera unavailable: ${e.message}")
            }
        }, ContextCompat.getMainExecutor(context))
    }

    fun stop() {
        provider?.unbindAll()
        analysisExecutor.execute { runCatching { landmarker?.close() }; landmarker = null }
        // Never leave the button held if the camera stops mid-drag.
        if (gestures.dragging) presenter.setButton(MouseButtons.LEFT, false)
        gestures.update(null, SystemClock.uptimeMillis())
        _status.value = Status()
    }

    private fun analyze(image: ImageProxy) {
        val lm = landmarker ?: run { image.close(); return }
        val upright = try {
            val bmp = image.toBitmap()
            // Rotate to upright and mirror, so moving the hand to the user's right moves the cursor right.
            val m = Matrix().apply {
                postRotate(image.imageInfo.rotationDegrees.toFloat())
                if (facing == Facing.FRONT) postScale(-1f, 1f)
            }
            Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, false)
        } finally {
            image.close()
        }
        lastFrameStart = SystemClock.uptimeMillis()
        lm.detectAsync(BitmapImageBuilder(upright).build(), lastFrameStart)
    }

    private fun onResult(result: HandLandmarkerResult, @Suppress("UNUSED_PARAMETER") input: com.google.mediapipe.framework.image.MPImage) {
        val now = SystemClock.uptimeMillis()
        val hand = result.landmarks().firstOrNull()?.map { HandGestureMouse.P(it.x(), it.y()) }
        val actions = gestures.update(hand, result.timestampMs())
        for (a in actions) when (a) {
            is HandGestureMouse.Action.Move -> presenter.moveBy(a.dx, a.dy)
            is HandGestureMouse.Action.Scroll -> presenter.scroll(a.steps)
            HandGestureMouse.Action.LeftClick -> presenter.click(MouseButtons.LEFT)
            HandGestureMouse.Action.RightClick -> presenter.click(MouseButtons.RIGHT)
            HandGestureMouse.Action.DragStart -> presenter.setButton(MouseButtons.LEFT, true)
            HandGestureMouse.Action.DragEnd -> presenter.setButton(MouseButtons.LEFT, false)
        }
        frames++
        val span = now - fpsStart
        val fps = if (span >= 1000) frames * 1000f / span else _status.value.fps
        if (span >= 1000) { frames = 0; fpsStart = now }
        _status.value = _status.value.copy(pose = gestures.pose, fps = fps, inferenceMs = now - result.timestampMs(),
            landmarks = hand.orEmpty(), error = null)
    }

    companion object {
        private const val TAG = "HandTracking"
        const val MODEL = "hand_landmarker.task"

        /** Skeleton connections for the on-screen hand drawing. */
        val CONNECTIONS = listOf(
            0 to 1, 1 to 2, 2 to 3, 3 to 4, 0 to 5, 5 to 6, 6 to 7, 7 to 8, 5 to 9, 9 to 10, 10 to 11, 11 to 12,
            9 to 13, 13 to 14, 14 to 15, 15 to 16, 13 to 17, 17 to 18, 18 to 19, 19 to 20, 0 to 17,
        )
    }
}
