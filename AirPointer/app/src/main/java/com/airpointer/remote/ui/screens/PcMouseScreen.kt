package com.airpointer.remote.ui.screens

import android.view.HapticFeedbackConstants
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.material.icons.automirrored.rounded.Backspace
import androidx.compose.material.icons.rounded.Keyboard
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.TextButton
import com.airpointer.remote.hid.KeyCodes
import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.core.content.ContextCompat
import com.airpointer.remote.core.HandGestureMouse
import com.airpointer.remote.hand.HandTrackingController
import com.airpointer.remote.ui.components.PrimaryButton
import com.airpointer.remote.ui.components.SettingChoice
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
import androidx.compose.material.icons.rounded.Pause
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.ads.AdPlacement
import com.airpointer.remote.ui.components.NativeAdCard
import com.airpointer.remote.MainActivity
import com.airpointer.remote.core.AirGestureEngine
import com.airpointer.remote.core.TouchpadGestureEngine
import com.airpointer.remote.hid.MouseButtons
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.components.NotConnectedBanner
import com.airpointer.remote.ui.components.Panel
import com.airpointer.remote.ui.components.RemoteKey
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.Segmented
import com.airpointer.remote.ui.components.SettingSlider
import com.airpointer.remote.ui.components.SettingSwitch
import com.airpointer.remote.ui.components.StatusDot
import com.airpointer.remote.ui.rememberLinkStatus
import com.airpointer.remote.ui.theme.Palette
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

private enum class MouseMode(val label: String) { TOUCHPAD("Touchpad"), AIR("Air mouse"), TABLE("Table") }

@Composable
fun PcMouseScreen(graph: AppGraph, activity: MainActivity, onBack: () -> Unit, navigate: (Route) -> Unit) {
    var mode by rememberSaveable { mutableStateOf(MouseMode.TOUCHPAD) }
    var keyboard by rememberSaveable { mutableStateOf(false) }
    val view = LocalView.current
    DisposableEffect(Unit) {
        view.keepScreenOn = true
        onDispose { view.keepScreenOn = false; graph.presenter.releaseAll() }
    }
    RemoteFrame(graph, "PC Mouse", onBack, navigate, actions = {
        IconButton(onClick = { keyboard = true }) { Icon(Icons.Rounded.Keyboard, "Keyboard", tint = Palette.TextPrimary) }
    }) {
        // Compact ad at the top edge, above the tabs — never beside the touchpad's Left/Right buttons.
        NativeAdCard(AdPlacement.PC_MOUSE, allowed = true)
        Segmented(MouseMode.entries.toList(), mode, { it.label }) { mode = it }
        when (mode) {
            MouseMode.TOUCHPAD -> TouchpadPane(graph, Modifier.weight(1f))
            MouseMode.AIR -> AirMousePane(graph, Modifier.weight(1f))
            MouseMode.TABLE -> TablePane(graph, Modifier.weight(1f))
        }
    }
    if (keyboard) KeyboardDialog(graph) { keyboard = false }
}

/** Type text and send common keys to the computer (works over Bluetooth and Wi-Fi). */
@Composable
private fun KeyboardDialog(graph: AppGraph, onDismiss: () -> Unit) {
    var text by rememberSaveable { mutableStateOf("") }
    var skipped by remember { mutableIntStateOf(0) }
    val presenter = graph.presenter
    val haptics = graph.settings.current.haptics
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = Palette.SurfaceHigh,
        title = { Text("Keyboard", style = MaterialTheme.typography.titleLarge) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(text, { text = it }, Modifier.fillMaxWidth(), minLines = 2, maxLines = 5,
                    label = { Text("Text to type on the computer") })
                if (skipped > 0) Text("$skipped character(s) skipped: no key on a US keyboard.",
                    style = MaterialTheme.typography.bodySmall, color = Palette.Warning)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    RemoteKey("Enter", null, Modifier.weight(1f), height = 48.dp, haptics = haptics, onClick = { presenter.key(KeyCodes.ENTER) })
                    RemoteKey("", Icons.AutoMirrored.Rounded.Backspace, Modifier.weight(1f), height = 48.dp, haptics = haptics,
                        contentDescription = "Backspace", onClick = { presenter.key(KeyCodes.BACKSPACE) })
                    RemoteKey("Esc", null, Modifier.weight(1f), height = 48.dp, haptics = haptics, contentDescription = "Escape",
                        onClick = { presenter.key(KeyCodes.ESCAPE) })
                    RemoteKey("Tab", null, Modifier.weight(1f), height = 48.dp, haptics = haptics, onClick = { presenter.key(KeyCodes.TAB) })
                }
            }
        },
        confirmButton = {
            TextButton(enabled = text.isNotEmpty(), onClick = { skipped = presenter.typeText(text); text = "" }) {
                Text("Type it", color = Palette.Accent, style = MaterialTheme.typography.labelLarge)
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Close", color = Palette.TextSecondary, style = MaterialTheme.typography.labelLarge) } },
    )
}

// ---------------------------------------------------------------------- shared finger-gesture surface

/**
 * Full-area touch surface feeding an [AirGestureEngine]. The phone (gyro or table motion) moves the
 * cursor; fingers click, scroll, drag and — in air mode — switch tracking on while touching.
 */
@Composable
private fun GestureSurface(
    engine: AirGestureEngine,
    modifier: Modifier,
    hint: String,
    active: Boolean,
    onTouching: (Boolean) -> Unit = {},
    onActions: (List<AirGestureEngine.Action>) -> Unit,
) {
    var fingers by remember { mutableIntStateOf(0) }
    val handler by rememberUpdatedState(onActions)
    val touching by rememberUpdatedState(onTouching)
    LaunchedEffect(fingers > 0) {
        while (fingers > 0) { handler(engine.tick(System.currentTimeMillis())); delay(30) }
    }
    Box(
        modifier.clip(RoundedCornerShape(28.dp))
            .background(if (active) Palette.AccentDim else Palette.Surface)
            .border(1.dp, if (active) Palette.Accent else Palette.Outline, RoundedCornerShape(28.dp))
            .pointerInput(engine) {
                awaitPointerEventScope {
                    while (true) {
                        val e = awaitPointerEvent()
                        val t = System.currentTimeMillis()
                        val before = fingers
                        for (c in e.changes) {
                            val id = c.id.value
                            when {
                                c.pressed && !c.previousPressed -> handler(engine.down(id, c.position.x, c.position.y, t))
                                c.pressed -> handler(engine.move(id, c.position.x, c.position.y, t))
                                !c.pressed && c.previousPressed -> handler(engine.up(id, t))
                            }
                            c.consume()
                        }
                        fingers = e.changes.count { it.pressed }
                        if ((before > 0) != (fingers > 0)) touching(fingers > 0)
                        if (e.type == PointerEventType.Exit && fingers == 0) handler(engine.cancel())
                    }
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        Text(hint, style = MaterialTheme.typography.bodySmall, color = if (active) Palette.TextPrimary else Palette.TextSecondary,
            textAlign = TextAlign.Center, modifier = Modifier.padding(16.dp))
    }
}

/** Applies gesture actions to the presenter. Returns true while a drag holds the left button. */
private fun applyGestures(presenter: com.airpointer.remote.presenter.PresenterController, actions: List<AirGestureEngine.Action>, onTracking: (Boolean) -> Unit) {
    for (a in actions) when (a) {
        is AirGestureEngine.Action.Tracking -> onTracking(a.on)
        is AirGestureEngine.Action.Move -> presenter.moveBy(a.dx, a.dy)
        is AirGestureEngine.Action.Scroll -> presenter.scroll(a.steps)
        AirGestureEngine.Action.LeftClick -> presenter.click(MouseButtons.LEFT)
        AirGestureEngine.Action.RightClick -> presenter.click(MouseButtons.RIGHT)
        AirGestureEngine.Action.DragStart -> presenter.setButton(MouseButtons.LEFT, true)
        AirGestureEngine.Action.DragEnd -> presenter.setButton(MouseButtons.LEFT, false)
    }
}

// ---------------------------------------------------------------------- air mouse (camera hand tracking)

@Composable
private fun AirMousePane(graph: AppGraph, modifier: Modifier) {
    val context = LocalContext.current
    val owner = LocalLifecycleOwner.current
    val hand = graph.handMouse
    val presenter = graph.presenter
    val status by hand.status.collectAsStateWithLifecycle()
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    var granted by remember {
        mutableStateOf(ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
    }
    var facing by rememberSaveable { mutableStateOf(HandTrackingController.Facing.FRONT) }
    var pointer by rememberSaveable { mutableStateOf(HandGestureMouse.PointerJoint.KNUCKLE) }
    var invertX by rememberSaveable { mutableStateOf(false) }
    var invertY by rememberSaveable { mutableStateOf(false) }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ok ->
        granted = ok
        if (ok) { hand.facing = facing; hand.start(owner) }
    }
    hand.gestures.sensitivity = settings.handSpeed.toDouble()
    hand.gestures.pointer = pointer
    hand.gestures.invertX = invertX; hand.gestures.invertY = invertY

    DisposableEffect(Unit) {
        val wasPaused = presenter.tracking.value.paused
        presenter.setPaused(true) // phone-motion pointing off: only the hand moves the cursor
        if (granted) { hand.facing = facing; hand.start(owner) }
        onDispose { hand.stop(); if (!wasPaused) presenter.setPaused(false) }
    }

    Column(modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        // Live hand skeleton (no camera image is shown or stored).
        Box(
            Modifier.fillMaxWidth().height(260.dp).clip(RoundedCornerShape(28.dp)).background(Palette.Surface)
                .border(1.dp, if (status.pose == HandGestureMouse.Pose.NO_HAND) Palette.Outline else Palette.Accent, RoundedCornerShape(28.dp)),
            contentAlignment = Alignment.Center,
        ) {
            if (status.landmarks.isNotEmpty()) Canvas(Modifier.fillMaxSize().padding(12.dp)) {
                val pts = status.landmarks.map { Offset(it.x * size.width, it.y * size.height) }
                for ((i, j) in HandTrackingController.CONNECTIONS) drawLine(Palette.TextSecondary, pts[i], pts[j], strokeWidth = 4f)
                pts.forEachIndexed { i, p -> drawCircle(if (i == 4 || i == 8 || i == 12) Palette.Accent else Palette.TextPrimary, if (i == 5) 11f else 7f, p) }
            } else Text(
                when {
                    !granted -> "Camera permission needed"
                    status.error != null -> status.error!!
                    !status.running -> "Camera off"
                    else -> "Show your hand to the camera"
                },
                style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary, textAlign = TextAlign.Center,
                modifier = Modifier.padding(24.dp),
            )
            Text(poseLabel(status.pose), style = MaterialTheme.typography.labelLarge,
                color = if (status.pose == HandGestureMouse.Pose.NO_HAND) Palette.TextSecondary else Palette.Accent,
                modifier = Modifier.align(Alignment.TopStart).padding(16.dp))
            if (status.running) Text("%.0f fps".format(status.fps), style = MaterialTheme.typography.labelSmall, color = Palette.TextSecondary,
                modifier = Modifier.align(Alignment.TopEnd).padding(16.dp))
        }

        Panel(padding = 14.dp) {
            if (!granted) PrimaryButton("Allow camera", Modifier.fillMaxWidth()) { launcher.launch(Manifest.permission.CAMERA) }
            else if (!status.running) PrimaryButton("Start hand tracking", Modifier.fillMaxWidth()) { hand.facing = facing; hand.start(owner) }
            else SecondaryButton("Stop", Modifier.fillMaxWidth()) { hand.stop() }
            Text(
                "Pinch thumb + index · left click   (twice = double click)\n" +
                    "Pinch and hold · drag, open to drop\n" +
                    "Pinch thumb + middle · right click\n" +
                    "Raise index + middle (✌) and move up/down · scroll\n" +
                    "Make a fist · pause, to reposition your hand",
                style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary,
            )
        }
        Panel(padding = 14.dp) {
            SettingSlider("Speed", settings.handSpeed, 0.25f..4f, "%.2f×".format(settings.handSpeed),
                { v -> graph.settings.update { it.copy(handSpeed = (v * 20).roundToInt() / 20f) } })
            SettingChoice("Cursor follows", HandGestureMouse.PointerJoint.entries.toList(), pointer,
                { if (it == HandGestureMouse.PointerJoint.KNUCKLE) "Index knuckle (steady clicks)" else "Index fingertip" }) { pointer = it }
            SettingChoice("Camera", HandTrackingController.Facing.entries.toList(), facing, { it.label }) { f ->
                facing = f
                if (status.running) { hand.stop(); hand.facing = f; hand.start(owner) }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryButton(if (invertX) "X inverted" else "Invert X") { invertX = !invertX }
                SecondaryButton(if (invertY) "Y inverted" else "Invert Y") { invertY = !invertY }
            }
            Text(
                "Prop the phone up facing you (or lay it flat and hold your hand above it), 30–60 cm away, with your hand well lit. " +
                    "Tracking runs on the phone with Google's MediaPipe hand model; no images leave the phone.",
                style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary,
            )
        }
    }
}

private fun poseLabel(p: HandGestureMouse.Pose) = when (p) {
    HandGestureMouse.Pose.NO_HAND -> "No hand"
    HandGestureMouse.Pose.POINTING -> "Pointing"
    HandGestureMouse.Pose.LEFT_PINCH -> "Left button"
    HandGestureMouse.Pose.RIGHT_PINCH -> "Right click"
    HandGestureMouse.Pose.SCROLL -> "Scrolling"
    HandGestureMouse.Pose.FIST -> "Paused"
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
                style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary, textAlign = TextAlign.Center,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            RemoteKey("Left", null, Modifier.weight(1f), height = 56.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.LEFT, true) }, onRelease = { presenter.setButton(MouseButtons.LEFT, false) })
            RemoteKey("Right", null, Modifier.weight(1f), height = 56.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.RIGHT, true) }, onRelease = { presenter.setButton(MouseButtons.RIGHT, false) })
        }
        var more by rememberSaveable { mutableStateOf(false) }
        SettingSlider("Pointer sensitivity", speed, 0.5f..4f, "%.1f×".format(speed), { speed = (it * 10).roundToInt() / 10f })
        AnimatedVisibility(more) {
            SettingSwitch("Natural scrolling", natural, { natural = it }, "Content follows your fingers, like Windows and macOS touchpads.")
        }
        TextButton(onClick = { more = !more }) {
            Text(if (more) "Fewer options" else "More options", color = Palette.TextSecondary, style = MaterialTheme.typography.labelLarge)
        }
    }
}

// ---------------------------------------------------------------------- table (gyroscope + accelerometer)

@Composable
private fun TablePane(graph: AppGraph, modifier: Modifier) {
    val presenter = graph.presenter
    val table = graph.tableMouse
    val view = LocalView.current
    val density = LocalDensity.current
    val status by table.status.collectAsStateWithLifecycle()
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    var dragging by remember { mutableStateOf(false) }
    var invertX by rememberSaveable { mutableStateOf(false) }
    var invertY by rememberSaveable { mutableStateOf(false) }
    val engine = remember {
        AirGestureEngine(touchSlopPx = with(density) { 10.dp.toPx() }, scrollStepPx = with(density) { 18.dp.toPx() },
            touchToTrack = false, fineSensitivity = 0f)
    }
    table.speed = settings.tableSpeed
    table.processor.invertX = invertX; table.processor.invertY = invertY

    DisposableEffect(Unit) {
        val wasPaused = presenter.tracking.value.paused
        presenter.setPaused(true) // the air-mouse gyro pipeline stays out of it
        table.start()
        onDispose { table.stop(); if (!wasPaused) presenter.setPaused(false) }
    }

    Column(modifier, verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            GestureSurface(
                engine, Modifier.weight(1f).fillMaxHeight(),
                hint = if (dragging) "Dragging — slide the phone, lift to drop"
                else "Slide the phone on the desk\n\nTap · left click     Double tap · double click\n" +
                    "Two-finger tap · right click     Two fingers · scroll\nTap, then hold · drag",
                active = dragging || (!status.still && status.running),
                // Tapping shakes the phone: ignore its motion while a finger is down, except during a drag.
                onTouching = { down -> table.touchHold = down && !engine.isDragging },
            ) { actions ->
                for (a in actions) {
                    if (a == AirGestureEngine.Action.DragStart) {
                        dragging = true; table.touchHold = false
                        if (settings.haptics) view.performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
                    }
                    if (a == AirGestureEngine.Action.DragEnd) dragging = false
                }
                applyGestures(presenter, actions) {}
            }
            ScrollStrip(graph, settings.scrollStepDp, Modifier.width(48.dp).fillMaxHeight())
        }
        Panel(padding = 14.dp) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                StatusDot(when { !status.running -> Palette.TextTertiary; !status.flat -> Palette.Warning; status.still -> Palette.Positive; else -> Palette.Accent },
                    status.running && !status.still, 6.dp)
                Text(when {
                    !status.running -> status.message ?: "Motion sensors off"
                    !status.flat -> "Lay the phone flat"
                    status.still -> "Resting — ready"
                    else -> "Moving · ${status.speedCmPerSec.roundToInt()} cm/s"
                }, style = MaterialTheme.typography.titleMedium)
            }
            SettingSlider("Speed", settings.tableSpeed, 0.25f..4f, "%.2f×".format(settings.tableSpeed),
                { v -> graph.settings.update { it.copy(tableSpeed = (v * 20).roundToInt() / 20f) } }, "Cursor travel per centimetre the phone moves.")
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SecondaryButton(if (invertX) "X inverted" else "Invert X") { invertX = !invertX }
                SecondaryButton(if (invertY) "Y inverted" else "Invert Y") { invertY = !invertY }
            }
            Text(
                "Uses the gyroscope and accelerometer. They measure motion, not position, so the app adds up each push and " +
                    "resets the moment the phone comes to rest — that keeps the cursor from drifting. Short, brisk pushes work best, " +
                    "like lifting and repositioning a real mouse; very slow glides register less. Keep the top of the phone pointing away from you.",
                style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary,
            )
        }
    }
}
