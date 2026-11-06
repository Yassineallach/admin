package com.airpointer.remote.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import android.view.HapticFeedbackConstants
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.CenterFocusStrong
import androidx.compose.material.icons.rounded.Pause
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.input.pointer.PointerEventType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.MainActivity
import com.airpointer.remote.core.CalibrationState
import com.airpointer.remote.core.TouchpadGestureEngine
import com.airpointer.remote.hid.MouseButtons
import com.airpointer.remote.table.TableMouseController
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.components.NotConnectedBanner
import com.airpointer.remote.ui.components.Panel
import com.airpointer.remote.ui.components.PrimaryButton
import com.airpointer.remote.ui.components.RemoteKey
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.Segmented
import com.airpointer.remote.ui.components.SettingChoice
import com.airpointer.remote.ui.components.SettingSlider
import com.airpointer.remote.ui.components.SettingSwitch
import com.airpointer.remote.ui.components.StatusDot
import com.airpointer.remote.ui.rememberLinkStatus
import com.airpointer.remote.ui.theme.Palette
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

private enum class MouseMode(val label: String) { AIR("Air mouse"), TOUCHPAD("Touchpad"), TABLE("Table") }

@Composable
fun PcMouseScreen(graph: AppGraph, activity: MainActivity, onBack: () -> Unit, navigate: (Route) -> Unit) {
    var mode by rememberSaveable { mutableStateOf(MouseMode.AIR) }
    val link = rememberLinkStatus(graph)
    val view = LocalView.current
    DisposableEffect(Unit) {
        view.keepScreenOn = true
        onDispose { view.keepScreenOn = false; graph.presenter.releaseAll() }
    }
    Column(
        Modifier.fillMaxSize().background(Palette.Background).statusBarsPadding().navigationBarsPadding().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(Modifier.fillMaxWidth().height(56.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Rounded.ArrowBack, "Back", tint = Palette.TextPrimary) }
            StatusDot(link.info.color, link.info.pulsing, 7.dp)
            Column(Modifier.weight(1f).padding(start = 4.dp)) {
                Text("PC Mouse", style = MaterialTheme.typography.titleMedium)
                Text(link.info.detail, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary, maxLines = 1)
            }
        }
        Segmented(MouseMode.entries.toList(), mode, { it.label }) { mode = it }
        if (!link.connected) NotConnectedBanner("Not connected to a computer.", "Connection") { navigate(Route.PAIRING) }
        when (mode) {
            MouseMode.AIR -> AirMousePane(graph, Modifier.weight(1f))
            MouseMode.TOUCHPAD -> TouchpadPane(graph, Modifier.weight(1f))
            MouseMode.TABLE -> TablePane(graph, Modifier.weight(1f))
        }
    }
}

// ---------------------------------------------------------------------- air mouse

@Composable
private fun AirMousePane(graph: AppGraph, modifier: Modifier) {
    val presenter = graph.presenter
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val tracking by presenter.tracking.collectAsStateWithLifecycle()
    val drag by presenter.dragLock.collectAsStateWithLifecycle()
    val calibration by presenter.calibration.collectAsStateWithLifecycle()
    val active = tracking.pointerActive && !tracking.paused

    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Column(Modifier.weight(1f).fillMaxHeight().verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Panel {
                    SettingSwitch("Motion tracking", active, { on ->
                        if (tracking.paused) presenter.setPaused(false)
                        if (on != tracking.pointerActive) presenter.togglePointer()
                    }, "Move the phone to move the cursor. Turn off to stop the cursor while you put the phone down.")
                    SettingSlider("Sensitivity", settings.sensitivity, 0.2f..3f, "%.2f×".format(settings.sensitivity),
                        { v -> graph.settings.update { it.copy(sensitivity = (v * 20).roundToInt() / 20f) } })
                    SettingSlider("Acceleration", settings.acceleration, 0f..2f, "%.1f".format(settings.acceleration),
                        { v -> graph.settings.update { it.copy(acceleration = (v * 10).roundToInt() / 10f) } })
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        SecondaryButton(if (calibration is CalibrationState.Running) "Calibrating…" else "Calibrate") { presenter.calibrate() }
                        Text(when (val c = calibration) {
                            is CalibrationState.Running -> "Hold still ${(c.progress * 100).roundToInt()}%"
                            is CalibrationState.Done -> "Drift removed"
                            is CalibrationState.Failed -> "Hold the phone still"
                            else -> "Lay the phone still"
                        }, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                    }
                }
            }
            ScrollStrip(graph, settings.scrollStepDp, Modifier.width(52.dp).fillMaxHeight())
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            RemoteKey("Left", null, Modifier.weight(1f), height = 64.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.LEFT, true) }, onRelease = { presenter.setButton(MouseButtons.LEFT, false) })
            RemoteKey("Right", null, Modifier.weight(1f), height = 64.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.RIGHT, true) }, onRelease = { presenter.setButton(MouseButtons.RIGHT, false) })
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            RemoteKey("Double", null, Modifier.weight(1f), height = 52.dp, haptics = settings.haptics, onClick = { presenter.doubleClick() })
            RemoteKey(if (drag) "Drop" else "Drag", null, Modifier.weight(1f), height = 52.dp, active = drag, haptics = settings.haptics,
                onClick = { presenter.setDragLock(!drag) })
            RemoteKey("", Icons.Rounded.CenterFocusStrong, Modifier.weight(0.7f), height = 52.dp, haptics = settings.haptics,
                onClick = { presenter.recenter() })
            RemoteKey("", if (tracking.paused) Icons.Rounded.PlayArrow else Icons.Rounded.Pause, Modifier.weight(0.7f), height = 52.dp,
                active = tracking.paused, haptics = settings.haptics, onClick = { presenter.setPaused(!tracking.paused) })
        }
    }
}

// ---------------------------------------------------------------------- touchpad

@Composable
private fun TouchpadPane(graph: AppGraph, modifier: Modifier) {
    val presenter = graph.presenter
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val density = LocalDensity.current
    val view = LocalView.current
    var speed by rememberSaveable { mutableStateOf(1.6f) }
    var natural by rememberSaveable { mutableStateOf(true) }
    var dragging by remember { mutableStateOf(false) }
    var fingers by remember { mutableIntStateOf(0) }
    val engine = remember {
        TouchpadGestureEngine(touchSlopPx = with(density) { 8.dp.toPx() }, scrollStepPx = with(density) { 18.dp.toPx() })
    }
    engine.sensitivity = speed; engine.naturalScroll = natural
    val haptics by rememberUpdatedState(settings.haptics)

    // Air-mouse motion must not fight the finger: pause it while the touchpad is shown.
    DisposableEffect(Unit) {
        val wasPaused = presenter.tracking.value.paused
        presenter.setPaused(true)
        onDispose { if (!wasPaused) presenter.setPaused(false) }
    }

    fun handle(actions: List<TouchpadGestureEngine.Action>) {
        for (a in actions) when (a) {
            is TouchpadGestureEngine.Action.Move -> presenter.moveBy(a.dx, a.dy)
            is TouchpadGestureEngine.Action.Scroll -> presenter.scroll(a.steps)
            TouchpadGestureEngine.Action.LeftClick -> presenter.click(MouseButtons.LEFT)
            TouchpadGestureEngine.Action.RightClick -> presenter.click(MouseButtons.RIGHT)
            TouchpadGestureEngine.Action.DragStart -> {
                dragging = true
                if (haptics) view.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
                presenter.setButton(MouseButtons.LEFT, true)
            }
            TouchpadGestureEngine.Action.DragEnd -> { dragging = false; presenter.setButton(MouseButtons.LEFT, false) }
        }
    }
    LaunchedEffect(fingers) {
        while (fingers > 0) { handle(engine.tick(System.currentTimeMillis())); delay(50) }
    }

    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(
            Modifier.fillMaxWidth().weight(1f).clip(RoundedCornerShape(28.dp))
                .background(if (dragging) Palette.AccentDim else Palette.Surface)
                .border(1.dp, if (dragging) Palette.Accent else Palette.Outline, RoundedCornerShape(28.dp))
                .pointerInput(Unit) {
                    awaitPointerEventScope {
                        while (true) {
                            val e = awaitPointerEvent()
                            val t = System.currentTimeMillis()
                            for (c in e.changes) {
                                val id = c.id.value
                                when {
                                    c.pressed && !c.previousPressed -> handle(engine.down(id, c.position.x, c.position.y, t))
                                    c.pressed -> handle(engine.move(id, c.position.x, c.position.y, t))
                                    !c.pressed && c.previousPressed -> handle(engine.up(id, t))
                                }
                                c.consume()
                            }
                            fingers = e.changes.count { it.pressed }
                            if (e.type == PointerEventType.Exit && fingers == 0) handle(engine.cancel())
                        }
                    }
                },
            contentAlignment = Alignment.Center,
        ) {
            Text(
                if (dragging) "Dragging — lift to drop" else "TOUCHPAD\n\nTap · click     Two-finger tap · right click\nTwo fingers · scroll     Hold · drag",
                style = MaterialTheme.typography.bodySmall, color = Palette.TextTertiary, textAlign = TextAlign.Center,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            RemoteKey("Left", null, Modifier.weight(1f), height = 56.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.LEFT, true) }, onRelease = { presenter.setButton(MouseButtons.LEFT, false) })
            RemoteKey("Right", null, Modifier.weight(1f), height = 56.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.RIGHT, true) }, onRelease = { presenter.setButton(MouseButtons.RIGHT, false) })
        }
        Panel(padding = 14.dp) {
            SettingSlider("Touchpad speed", speed, 0.5f..4f, "%.1f×".format(speed), { speed = (it * 10).roundToInt() / 10f })
            SettingSwitch("Natural scrolling", natural, { natural = it }, "Content follows your fingers, like Windows and macOS touchpads.")
        }
    }
}

// ---------------------------------------------------------------------- table (camera)

@Composable
private fun TablePane(graph: AppGraph, modifier: Modifier) {
    val context = LocalContext.current
    val owner = LocalLifecycleOwner.current
    val table = graph.tableMouse
    val status by table.status.collectAsStateWithLifecycle()
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val presenter = graph.presenter
    var cfg by remember { mutableStateOf(table.config) }
    var granted by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
    }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted = it }

    DisposableEffect(Unit) {
        val wasPaused = presenter.tracking.value.paused
        presenter.setPaused(true) // gyro air mouse off: only the camera moves the cursor
        onDispose { table.stop(); if (!wasPaused) presenter.setPaused(false) }
    }

    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        // Mouse buttons fill the top of the screen, like the buttons of a real mouse.
        Row(Modifier.fillMaxWidth().weight(1f), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            RemoteKey("Left", null, Modifier.weight(1f), height = 9999.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.LEFT, true) }, onRelease = { presenter.setButton(MouseButtons.LEFT, false) })
            ScrollStrip(graph, settings.scrollStepDp, Modifier.width(48.dp).fillMaxHeight())
            RemoteKey("Right", null, Modifier.weight(1f), height = 9999.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.RIGHT, true) }, onRelease = { presenter.setButton(MouseButtons.RIGHT, false) })
        }
        Panel(padding = 14.dp) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                StatusDot(if (status.tracking) Palette.Positive else if (status.running) Palette.Warning else Palette.TextTertiary, status.running, 6.dp)
                Text(
                    if (status.running) "Tracking quality ${(status.quality * 100).roundToInt()}% · ${status.fps.roundToInt()} fps" else "Camera off",
                    style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f),
                )
            }
            if (status.running) LinearProgressIndicator(progress = { status.quality }, modifier = Modifier.fillMaxWidth(),
                color = if (status.tracking) Palette.Positive else Palette.Warning, trackColor = Palette.SurfaceHighest)
            status.message?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary) }
            if (!granted) PrimaryButton("Allow camera", Modifier.fillMaxWidth()) { launcher.launch(Manifest.permission.CAMERA) }
            else if (!status.running) PrimaryButton("Start table mouse", Modifier.fillMaxWidth()) { table.config = cfg; table.start(owner) }
            else SecondaryButton("Stop", Modifier.fillMaxWidth()) { table.stop() }
            SettingChoice("Camera", TableMouseController.Facing.entries.toList(), cfg.facing, { it.label }) { f ->
                cfg = cfg.copy(facing = f); table.config = cfg
                if (status.running) { table.stop(); table.start(owner) }
            }
            SettingSlider("Speed", cfg.speed, 0.25f..4f, "%.2f×".format(cfg.speed), {
                cfg = cfg.copy(speed = (it * 20).roundToInt() / 20f); table.config = cfg
            }, "Depends on the ceiling height — raise it in tall rooms.")
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryButton(if (cfg.invertX) "X inverted" else "Invert X") { cfg = cfg.copy(invertX = !cfg.invertX); table.config = cfg }
                SecondaryButton(if (cfg.invertY) "Y inverted" else "Invert Y") { cfg = cfg.copy(invertY = !cfg.invertY); table.config = cfg }
            }
            Text(
                "How it works: like an optical mouse, the camera compares successive images and measures how far the view shifted. " +
                    "The front camera watches the ceiling, so it needs a lit ceiling with some detail (lamps, beams, edges). " +
                    "Phone cameras cannot focus on a desk 1 mm away, so the back camera only works on strongly patterned surfaces. " +
                    "When tracking is unsure the cursor stops instead of drifting. The touchpad is the dependable alternative.",
                style = MaterialTheme.typography.bodySmall, color = Palette.TextTertiary,
            )
        }
    }
}
