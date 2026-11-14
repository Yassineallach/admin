package com.airpointer.remote.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.os.Build
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.airpointer.remote.presenter.PresenterController
import com.airpointer.remote.ui.components.Divider
import com.airpointer.remote.ui.components.InfoRow
import com.airpointer.remote.ui.components.Panel
import com.airpointer.remote.ui.components.ScreenScaffold
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.SectionLabel
import com.airpointer.remote.ui.components.SettingSwitch
import com.airpointer.remote.ui.theme.Palette

@Composable
fun DiagnosticsScreen(graph: AppGraph, onBack: () -> Unit) {
    val hid by graph.hid.state.collectAsStateWithLifecycle()
    val snap by graph.presenter.snapshot.collectAsStateWithLifecycle()
    val tracking by graph.presenter.tracking.collectAsStateWithLifecycle()
    val log by graph.log.entries.collectAsStateWithLifecycle()
    val caps = graph.motion.capabilities
    val context = LocalContext.current

    DisposableEffect(Unit) { onDispose { graph.presenter.setPreview(false) } }

    ScreenScaffold("Diagnostics", onBack) {
        SectionLabel("Bluetooth HID")
        Panel {
            InfoRow("Adapter", if (hid.adapterPresent) (if (hid.bluetoothOn) "On" else "Off") else "Absent", ok(hid.adapterPresent && hid.bluetoothOn))
            InfoRow("Permission", if (hid.permissionGranted) "Granted" else "Missing", ok(hid.permissionGranted))
            InfoRow("Service", if (hid.serviceRunning) "Running" else "Stopped", ok(hid.serviceRunning))
            InfoRow("HID Device profile", hid.support.name.lowercase().replaceFirstChar { it.uppercase() },
                when (hid.support) {
                    com.airpointer.remote.hid.BluetoothHidController.Support.SUPPORTED -> Palette.Positive
                    com.airpointer.remote.hid.BluetoothHidController.Support.UNSUPPORTED -> Palette.Negative
                    else -> Palette.TextPrimary
                })
            InfoRow("Registered", if (hid.registered) "Yes" else "No", ok(hid.registered))
            InfoRow("Connection", hid.phase.name.lowercase(), if (hid.connected) Palette.Positive else Palette.TextPrimary)
            InfoRow("Host", hid.host?.let { "${it.name}\n${it.address}" } ?: "—")
            InfoRow("Protocol", if (hid.bootProtocol) "Boot (limited)" else "Report")
            if (hid.reconnectAttempt > 0) InfoRow("Reconnect attempt", "${hid.reconnectAttempt}")
            Divider()
            InfoRow("Reports sent", "${snap.reportsSent}")
            InfoRow("Report rate", "%.0f Hz".format(snap.reportRateHz))
            InfoRow("Send failures", "${snap.reportFailures}", if (snap.reportFailures > 0) Palette.Warning else Palette.TextPrimary)
            hid.unsupportedReason?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = Palette.Negative) }
            hid.lastError?.let { Text("Last error: $it", style = MaterialTheme.typography.bodySmall, color = Palette.Warning) }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryButton("Test square", enabled = hid.connected) { graph.presenter.sendTestPattern() }
                SecondaryButton("Test click", enabled = hid.connected) { graph.presenter.click(com.airpointer.remote.hid.MouseButtons.LEFT) }
                SecondaryButton("Re-register") { graph.hid.restart() }
            }
        }

        SectionLabel("Wi-Fi companion")
        Panel {
            val wifi by graph.wifi.state.collectAsStateWithLifecycle()
            val settings by graph.settings.settings.collectAsStateWithLifecycle()
            InfoRow("Selected link", settings.transport.label)
            InfoRow("State", wifi.phase.name.lowercase(), if (wifi.phase == com.airpointer.remote.transport.WifiCompanionClient.Phase.CONNECTED) Palette.Positive else Palette.TextPrimary)
            InfoRow("Computer", wifi.serverName?.let { "$it (${wifi.serverOs})\n${wifi.host}:${wifi.port}" } ?: wifi.host ?: "—")
            InfoRow("Round trip", wifi.latencyMs?.let { "$it ms" } ?: "—")
            InfoRow("Features", wifi.features.joinToString().ifBlank { "—" })
            InfoRow("Reports sent", "${graph.wifi.reportsSent.get()}")
            wifi.error?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = Palette.Warning) }
        }

        SectionLabel("Motion sensors")
        Panel {
            InfoRow("Mode", graph.presenter.sensorMode.label)
            InfoRow("Gyroscope", caps.gyroscope?.let { "${it.name}\n${it.vendor} · min ${it.minDelayUs} µs" } ?: "Not present",
                if (caps.gyroscope == null) Palette.Negative else Palette.TextPrimary)
            InfoRow("Accelerometer", caps.accelerometer?.let { "${it.name}\n${it.vendor}" } ?: "Not present",
                if (caps.accelerometer == null) Palette.Negative else Palette.TextPrimary)
            InfoRow("Sensors running", if (tracking.sensorsRunning) "Yes" else "No (start preview or connect)")
            InfoRow("Gyro rate", "%.0f Hz".format(snap.gyroRateHz))
            InfoRow("Accel rate", "%.0f Hz".format(snap.accelRateHz))
            InfoRow("Processing", "%.0f µs / sample".format(snap.processingUs))
            InfoRow("Yaw / pitch", "%+.3f / %+.3f rad/s".format(snap.yawRate, snap.pitchRate))
            InfoRow("Gyro bias", "%+.4f %+.4f %+.4f".format(snap.bias.x, snap.bias.y, snap.bias.z))
            InfoRow("Gravity (up)", "%+.2f %+.2f %+.2f".format(snap.up.x, snap.up.y, snap.up.z))
            InfoRow("Still", if (snap.still) "Yes — bias adapting" else "No", if (snap.still) Palette.Positive else Palette.TextPrimary)
        }

        SectionLabel("Motion preview")
        Panel {
            SettingSwitch("Preview pointer locally", tracking.preview, { graph.presenter.setPreview(it) },
                "Runs the full gyroscope → pointer pipeline and draws the cursor here. Works without a computer.")
            if (tracking.paused) Text("Tracking is paused on the remote screen.", style = MaterialTheme.typography.bodySmall, color = Palette.Warning)
            if (!tracking.pointerActive) Text("Pointer is off — turn it on from the remote screen.", style = MaterialTheme.typography.bodySmall, color = Palette.Warning)
            PreviewPad(snap)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryButton("Recenter") { graph.presenter.recenter() }
                SecondaryButton(if (tracking.pointerActive) "Pointer on" else "Pointer off") { graph.presenter.togglePointer() }
            }
        }

        SectionLabel("Device")
        Panel {
            InfoRow("Model", "${Build.MANUFACTURER} ${Build.MODEL}")
            InfoRow("Android", "${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
            InfoRow("App", com.airpointer.remote.BuildConfig.VERSION_NAME)
        }

        SectionLabel("Event log")
        Panel {
            SecondaryButton("Copy log") {
                val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                cm.setPrimaryClip(ClipData.newPlainText("Air Pointer log", graph.log.asText()))
            }
            if (log.isEmpty()) Text("No events yet.", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
            log.takeLast(60).asReversed().forEach { e ->
                Text(
                    e.format(), style = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace),
                    color = when (e.level) {
                        DiagnosticsLog.Level.ERROR -> Palette.Negative
                        DiagnosticsLog.Level.WARN -> Palette.Warning
                        else -> Palette.TextSecondary
                    },
                )
            }
        }
    }
}

private fun ok(v: Boolean) = if (v) Palette.Positive else Palette.Warning

@Composable
private fun PreviewPad(snap: PresenterController.MotionSnapshot) {
    val trail = remember { mutableStateListOf<Offset>() }
    LaunchedEffect(snap.previewX, snap.previewY) {
        trail.add(Offset(snap.previewX, snap.previewY))
        if (trail.size > 90) trail.removeAt(0)
    }
    Canvas(
        Modifier.fillMaxWidth().aspectRatio(16f / 9f).clip(RoundedCornerShape(16.dp)).background(Palette.Background),
    ) {
        val range = PresenterController.PREVIEW_RANGE
        val scale = minOf(size.width, size.height) / (2 * range) * 1.6f
        val c = Offset(size.width / 2, size.height / 2)
        fun map(p: Offset) = Offset(
            (c.x + p.x * scale).coerceIn(0f, size.width), (c.y + p.y * scale).coerceIn(0f, size.height),
        )
        drawLine(Palette.Outline, Offset(c.x, 0f), Offset(c.x, size.height))
        drawLine(Palette.Outline, Offset(0f, c.y), Offset(size.width, c.y))
        trail.forEachIndexed { i, p ->
            if (i > 0) drawLine(Palette.Accent.copy(alpha = i / trail.size.toFloat() * 0.6f), map(trail[i - 1]), map(p), strokeWidth = 3f)
        }
        val head = map(Offset(snap.previewX, snap.previewY))
        drawCircle(Palette.Accent.copy(alpha = 0.25f), 18f, head)
        drawCircle(Palette.Accent, 7f, head)
        drawCircle(Color.White.copy(alpha = 0.6f), 7f, head, style = Stroke(1.5f))
    }
}
