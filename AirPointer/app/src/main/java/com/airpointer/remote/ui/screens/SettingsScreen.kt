package com.airpointer.remote.ui.screens

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.compose.ui.unit.dp
import com.airpointer.remote.AppGraph
import com.airpointer.remote.core.CalibrationState
import com.airpointer.remote.presenter.PointerMode
import com.airpointer.remote.presenter.RemoteAction
import com.airpointer.remote.presenter.SlideKeys
import com.airpointer.remote.ui.components.Divider
import com.airpointer.remote.ui.components.Panel
import com.airpointer.remote.ui.components.PrimaryButton
import com.airpointer.remote.ui.components.ScreenScaffold
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.SectionLabel
import com.airpointer.remote.ui.components.SettingChoice
import com.airpointer.remote.ui.components.SettingSlider
import com.airpointer.remote.ui.components.SettingSwitch
import com.airpointer.remote.ui.theme.Palette
import java.text.DateFormat
import java.util.Date
import kotlin.math.roundToInt

private val RESOLUTIONS = listOf(1280 to 720, 1366 to 768, 1920 to 1080, 1920 to 1200, 2560 to 1440, 3840 to 2160)
private val ACTIONS = RemoteAction.entries.toList()

@Composable
fun SettingsScreen(graph: AppGraph, onBack: () -> Unit) {
    val s by graph.settings.settings.collectAsStateWithLifecycle()
    val calibration by graph.presenter.calibration.collectAsStateWithLifecycle()
    val repo = graph.settings
    val presenter = graph.presenter

    DisposableEffect(Unit) { onDispose { presenter.clearCalibrationResult() } }

    ScreenScaffold("Sensitivity & calibration", onBack) {
        SectionLabel("Calibration")
        Panel(Modifier.animateContentSize()) {
            Text("Gyroscope calibration", style = MaterialTheme.typography.titleMedium)
            Text(
                "Place the phone on a table (or hold it perfectly still) and calibrate. This measures the gyroscope's zero-rate offset, " +
                    "which is what makes a pointer drift. Automatic drift compensation keeps refining it whenever the phone is still.",
                style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary,
            )
            when (val c = calibration) {
                is CalibrationState.Running -> {
                    LinearProgressIndicator(progress = { c.progress }, modifier = Modifier.fillMaxWidth(), color = Palette.Accent, trackColor = Palette.SurfaceHighest)
                    Text(if (c.restarts > 0) "Movement detected — keep still… (restart ${c.restarts})" else "Hold still…",
                        style = MaterialTheme.typography.bodySmall, color = if (c.restarts > 0) Palette.Warning else Palette.TextSecondary)
                    SecondaryButton("Cancel") { presenter.cancelCalibration() }
                }
                is CalibrationState.Done -> Text("Calibrated. Bias: %.4f, %.4f, %.4f rad/s".format(c.bias.x, c.bias.y, c.bias.z),
                    style = MaterialTheme.typography.bodySmall, color = Palette.Positive)
                is CalibrationState.Failed -> Text(c.reason, style = MaterialTheme.typography.bodySmall, color = Palette.Negative)
                CalibrationState.Idle -> Text(
                    if (s.calibratedAtMs > 0) "Last calibrated ${DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(Date(s.calibratedAtMs))}"
                    else "Not calibrated yet.", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary,
                )
            }
            if (calibration !is CalibrationState.Running) Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                PrimaryButton("Calibrate", Modifier.weight(1f)) { presenter.calibrate() }
                SecondaryButton("Recenter cursor") { presenter.recenter() }
            }
            SettingSwitch("Automatic drift compensation", s.autoDriftCompensation, { v -> repo.update { it.copy(autoDriftCompensation = v) } },
                "Re-estimates gyro bias whenever the phone is still for about a second.")
        }

        SectionLabel("Pointer")
        Panel {
            SettingSlider("Sensitivity", s.sensitivity, 0.2f..3f, "%.2f×".format(s.sensitivity),
                { v -> repo.update { it.copy(sensitivity = (v * 20).roundToInt() / 20f) } },
                "Cursor travel per degree of rotation.")
            SettingSlider("Acceleration", s.acceleration, 0f..2f, accelLabel(s.acceleration),
                { v -> repo.update { it.copy(acceleration = (v * 10).roundToInt() / 10f) } },
                "Fast flicks travel further; slow movements stay precise.")
            SettingSlider("Smoothing", s.smoothing, 0f..1f, "${(s.smoothing * 100).roundToInt()}%",
                { v -> repo.update { it.copy(smoothing = (v * 20).roundToInt() / 20f) } },
                "Adaptive 1€ filter: removes hand tremor at low speed without adding lag to fast moves.")
            SettingSlider("Dead zone", s.deadzone, 0f..0.05f, "%.1f°/s".format(Math.toDegrees(s.deadzone.toDouble())),
                { v -> repo.update { it.copy(deadzone = (v * 1000).roundToInt() / 1000f) } },
                "Rotation slower than this is ignored, which hides residual drift.")
            Divider()
            SettingChoice("Pointer button", PointerMode.entries.toList(), s.pointerMode, { it.label }) { v -> repo.update { it.copy(pointerMode = v) } }
            SettingSwitch("Recenter when activated", s.recenterOnActivate, { v -> repo.update { it.copy(recenterOnActivate = v) } },
                "Jump the cursor to the screen centre each time the pointer turns on.")
            SettingSwitch("PowerPoint laser mode", s.laserOnActivate, { v -> repo.update { it.copy(laserOnActivate = v) } },
                "In a slideshow, activating the pointer sends Ctrl+L (laser) and deactivating sends Ctrl+A (arrow).")
            SettingSwitch("Invert horizontal", s.invertX, { v -> repo.update { it.copy(invertX = v) } })
            SettingSwitch("Invert vertical", s.invertY, { v -> repo.update { it.copy(invertY = v) } })
            Divider()
            SettingChoice("Computer resolution", RESOLUTIONS, s.hostWidth to s.hostHeight, { "${it.first} × ${it.second}" }) { (w, h) ->
                repo.update { it.copy(hostWidth = w, hostHeight = h) }
            }
            Text("Used by Recenter: the cursor is pushed to the top-left corner, then moved half a screen. " +
                "Turn off Windows 'Enhance pointer precision' for an exact centre.",
                style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        }

        SectionLabel("Presentation")
        Panel {
            SettingChoice("Slide keys", SlideKeys.entries.toList(), s.slideKeys, { it.label }) { v -> repo.update { it.copy(slideKeys = v) } }
            SettingSwitch("Volume buttons", s.volumeKeysEnabled, { v -> repo.update { it.copy(volumeKeysEnabled = v) } },
                "While the remote screen is open, the phone's volume keys trigger actions.")
            if (s.volumeKeysEnabled) {
                SettingChoice("Volume up", ACTIONS, s.volumeUpAction, { it.label }) { v -> repo.update { it.copy(volumeUpAction = v) } }
                SettingChoice("Volume down", ACTIONS, s.volumeDownAction, { it.label }) { v -> repo.update { it.copy(volumeDownAction = v) } }
            }
            Divider()
            Text("Gesture pad", style = MaterialTheme.typography.labelSmall, color = Palette.TextSecondary)
            val clicky = setOf(RemoteAction.LEFT_CLICK, RemoteAction.RIGHT_CLICK)
            if (s.tapAction in clicky || s.doubleTapAction in clicky || s.longPressAction in clicky) {
                Text("A click on the pad lands wherever the cursor is, and the thumb holding the phone often rests on the pad. " +
                    "Use the Left/Right click buttons instead unless you really want this.",
                    style = MaterialTheme.typography.bodySmall, color = Palette.Warning)
            }
            SettingChoice("Tap", ACTIONS, s.tapAction, { it.label }) { v -> repo.update { it.copy(tapAction = v) } }
            SettingChoice("Double tap", ACTIONS, s.doubleTapAction, { it.label }) { v -> repo.update { it.copy(doubleTapAction = v) } }
            SettingChoice("Long press", ACTIONS, s.longPressAction, { it.label }) { v -> repo.update { it.copy(longPressAction = v) } }
            SettingChoice("Swipe left", ACTIONS, s.swipeLeftAction, { it.label }) { v -> repo.update { it.copy(swipeLeftAction = v) } }
            SettingChoice("Swipe right", ACTIONS, s.swipeRightAction, { it.label }) { v -> repo.update { it.copy(swipeRightAction = v) } }
            SettingChoice("Swipe up", ACTIONS, s.swipeUpAction, { it.label }) { v -> repo.update { it.copy(swipeUpAction = v) } }
            SettingChoice("Swipe down", ACTIONS, s.swipeDownAction, { it.label }) { v -> repo.update { it.copy(swipeDownAction = v) } }
            SettingSlider("Scroll strip step", s.scrollStepDp.toFloat(), 10f..48f, "${s.scrollStepDp} dp",
                { v -> repo.update { it.copy(scrollStepDp = v.roundToInt()) } }, "Finger travel per wheel notch.")
            Divider()
            SettingSwitch("Haptic feedback", s.haptics, { v -> repo.update { it.copy(haptics = v) } })
            SettingSwitch("Keep screen on", s.keepScreenOn, { v -> repo.update { it.copy(keepScreenOn = v) } },
                "Recommended: Android may throttle motion sensors when the screen turns off.")
        }

        SectionLabel("Connection")
        Panel {
            SettingChoice("Report rate", listOf(30, 45, 60, 90, 125), s.reportRateHz, { "$it Hz" + if (it == 60) " (default)" else "" }) { v ->
                repo.update { it.copy(reportRateHz = v) }
            }
            Text("Lower it if the cursor freezes or lags behind the phone. Rates above 60 Hz can overrun the Bluetooth link on some PCs.",
                style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
            SettingSwitch("Auto-reconnect", s.autoReconnect, { v -> repo.update { it.copy(autoReconnect = v) } },
                "Reconnect to the last computer on start-up and after an unexpected drop.")
            if (s.lastHostAddress != null) {
                Text("Last computer: ${s.lastHostName ?: ""} (${s.lastHostAddress})", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                SecondaryButton("Forget last computer") { repo.update { it.copy(lastHostAddress = null, lastHostName = null) } }
            }
        }

        SecondaryButton("Reset tuning to defaults", Modifier.fillMaxWidth()) { repo.resetTuning() }
    }
}

private fun accelLabel(v: Float) = when {
    v < 0.05f -> "Off"
    v < 0.5f -> "Low"
    v < 1.2f -> "Medium"
    else -> "High"
} + " (%.1f)".format(v)
