package com.airpointer.remote.table

import android.annotation.SuppressLint
import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.util.Size
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.airpointer.remote.core.OpticalFlowEstimator
import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.airpointer.remote.presenter.PresenterController
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.concurrent.Executors
import kotlin.math.abs
import kotlin.math.sqrt

/**
 * "Table mouse": the phone lies on the desk and is slid like a mouse. Translation is measured by
 * camera optical flow (the same principle as an optical mouse sensor), never by the gyroscope:
 * integrating gyro/accelerometer data cannot recover pure translation without drifting away
 * within a second.
 *
 * Camera choice:
 *  • FRONT (default): looks at the ceiling. Works with a textured/lit ceiling; speed depends on height.
 *  • BACK + torch: looks at the desk through the ~1 mm gap under the camera bump. Phone cameras
 *    cannot focus that close, so this only works on strongly patterned surfaces.
 * Frames with low texture/match confidence, or taken while the phone tilts or is lifted, produce
 * no motion — the cursor stops rather than drifting.
 */
class TableMouseController(
    private val context: Context,
    private val presenter: PresenterController,
    private val log: DiagnosticsLog,
) : SensorEventListener {

    enum class Facing(val label: String) { FRONT("Front camera (ceiling)"), BACK("Back camera + torch (desk)") }

    data class Config(
        val facing: Facing = Facing.FRONT,
        val speed: Float = 1f,
        val invertX: Boolean = false,
        val invertY: Boolean = false,
        val torch: Boolean = true,
    )

    data class Status(
        val running: Boolean = false,
        val fps: Float = 0f,
        val quality: Float = 0f,
        val tracking: Boolean = false,
        val message: String? = null,
    )

    private val _status = MutableStateFlow(Status())
    val status: StateFlow<Status> = _status

    @Volatile var config = Config()
    private val estimator = OpticalFlowEstimator()
    private val executor = Executors.newSingleThreadExecutor()
    private var provider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var buffer = ByteArray(0)
    private var residualX = 0f
    private var residualY = 0f
    private var frames = 0
    private var fpsStart = 0L
    private var smoothQuality = 0f

    // Motion gating from the IMU (written by the sensor thread, read by the analyzer).
    @Volatile private var tiltRate = 0f
    @Volatile private var flat = true
    private val sm = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager

    fun start(owner: LifecycleOwner) {
        val future = ProcessCameraProvider.getInstance(context)
        future.addListener({
            try {
                val p = future.get()
                provider = p
                p.unbindAll()
                val c = config
                val selector = if (c.facing == Facing.FRONT) CameraSelector.DEFAULT_FRONT_CAMERA else CameraSelector.DEFAULT_BACK_CAMERA
                if (!p.hasCamera(selector)) {
                    _status.value = Status(message = "This phone has no ${c.facing.name.lowercase()} camera.")
                    return@addListener
                }
                val analysis = ImageAnalysis.Builder()
                    .setResolutionSelector(ResolutionSelector.Builder()
                        .setResolutionStrategy(ResolutionStrategy(Size(320, 240), ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER))
                        .build())
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                    .build()
                analysis.setAnalyzer(executor, ::analyze)
                camera = p.bindToLifecycle(owner, selector, analysis)
                if (c.facing == Facing.BACK && c.torch && camera?.cameraInfo?.hasFlashUnit() == true) camera?.cameraControl?.enableTorch(true)
                estimator.reset(); residualX = 0f; residualY = 0f; fpsStart = System.nanoTime(); frames = 0
                sm.getDefaultSensor(Sensor.TYPE_GYROSCOPE)?.let { sm.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME) }
                sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)?.let { sm.registerListener(this, it, SensorManager.SENSOR_DELAY_UI) }
                _status.value = Status(running = true, message = "Slide the phone on the desk.")
                log.i(TAG, "Table mouse started (${c.facing})")
            } catch (e: Exception) {
                _status.value = Status(message = "Camera unavailable: ${e.message}")
                log.e(TAG, "camera start: ${e.message}")
            }
        }, ContextCompat.getMainExecutor(context))
    }

    fun stop() {
        runCatching { camera?.cameraControl?.enableTorch(false) }
        provider?.unbindAll()
        sm.unregisterListener(this)
        camera = null
        _status.value = Status()
    }

    @SuppressLint("UnsafeOptInUsageError")
    private fun analyze(image: ImageProxy) {
        image.use {
            val plane = it.planes[0]
            val buf = plane.buffer
            val needed = buf.remaining()
            if (buffer.size < needed) buffer = ByteArray(needed)
            buf.get(buffer, 0, needed)
            val r = estimator.update(estimator.prepare(buffer, it.width, it.height, plane.rowStride)) ?: return
            countFrame()
            smoothQuality += (r.confidence - smoothQuality) * 0.2f
            val c = config
            val moving = flat && tiltRate < MAX_TILT_RATE
            val trusted = r.confidence >= MIN_CONFIDENCE && moving
            _status.value = _status.value.copy(
                quality = smoothQuality, tracking = trusted,
                message = when {
                    !flat -> "Lay the phone flat on the desk."
                    !moving -> "Phone tilted or lifted — paused."
                    r.confidence < MIN_CONFIDENCE && r.texture < 4f ->
                        if (c.facing == Facing.FRONT) "Too little detail above the phone (plain ceiling or dark room)." else "Surface too plain or out of focus."
                    r.confidence < MIN_CONFIDENCE -> "Tracking unsure — move a little slower."
                    else -> null
                },
            )
            if (!trusted) { residualX = 0f; residualY = 0f; return }
            // Rotate the buffer-space shift to the upright (portrait) image.
            val (ux, uy) = when (it.imageInfo.rotationDegrees) {
                90 -> -r.dy to r.dx
                180 -> -r.dx to -r.dy
                270 -> r.dy to -r.dx
                else -> r.dx to r.dy
            }
            // Scene shift → phone motion. Front camera (unmirrored) sees image x = device −X; back camera
            // sees image x = device +X. Both see image y = device −Y. Pushing forward (+Y) = cursor up.
            var cx = if (c.facing == Facing.FRONT) ux else -ux
            var cy = -uy
            if (abs(cx) < DEADZONE_PX) cx = 0f
            if (abs(cy) < DEADZONE_PX) cy = 0f
            val gain = (if (c.facing == Facing.FRONT) FRONT_GAIN else BACK_GAIN) * c.speed
            val mx = cx * gain * (if (c.invertX) -1 else 1) + residualX
            val my = cy * gain * (if (c.invertY) -1 else 1) + residualY
            val ix = mx.toInt(); val iy = my.toInt()
            residualX = mx - ix; residualY = my - iy
            presenter.moveBy(ix, iy)
        }
    }

    private fun countFrame() {
        frames++
        val now = System.nanoTime()
        if (now - fpsStart > 1_000_000_000L) {
            _status.value = _status.value.copy(fps = frames * 1e9f / (now - fpsStart))
            frames = 0; fpsStart = now
        }
    }

    override fun onSensorChanged(e: SensorEvent) {
        when (e.sensor.type) {
            Sensor.TYPE_GYROSCOPE -> {
                // Rotation about the device X/Y axes = tilting or lifting; yaw (Z) is normal mouse use.
                val r = sqrt(e.values[0] * e.values[0] + e.values[1] * e.values[1])
                tiltRate = tiltRate * 0.7f + r * 0.3f
            }
            Sensor.TYPE_ACCELEROMETER -> {
                val n = sqrt(e.values.sumOf { (it * it).toDouble() }).toFloat()
                flat = n > 1f && abs(e.values[2]) / n > 0.94f // within ~20° of horizontal
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor, accuracy: Int) {}

    companion object {
        private const val TAG = "TableMouse"
        const val MIN_CONFIDENCE = 0.35f
        const val MAX_TILT_RATE = 0.6f
        const val DEADZONE_PX = 0.08f
        /** Counts per grid pixel; the ceiling is ~2 m away, so each pixel is a large phone movement. */
        const val FRONT_GAIN = 40f
        const val BACK_GAIN = 8f
    }
}
