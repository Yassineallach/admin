package com.airpointer.remote.ui.screens

import android.view.HapticFeedbackConstants
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.CenterFocusStrong
import androidx.compose.material.icons.rounded.DarkMode
import androidx.compose.material.icons.rounded.Pause
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.Slideshow
import androidx.compose.material.icons.rounded.StopCircle
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material.icons.rounded.UnfoldMore
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.MainActivity
import com.airpointer.remote.hid.MouseButtons
import com.airpointer.remote.presenter.PointerMode
import com.airpointer.remote.presenter.RemoteAction
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.components.RemoteKey
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.StatusDot
import com.airpointer.remote.ui.statusOf
import com.airpointer.remote.ui.theme.Palette
import kotlin.math.abs

@Composable
fun RemoteScreen(graph: AppGraph, activity: MainActivity, onBack: () -> Unit, navigate: (Route) -> Unit) {
    val hid by graph.hid.state.collectAsStateWithLifecycle()
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val tracking by graph.presenter.tracking.collectAsStateWithLifecycle()
    val presenter = graph.presenter
    val view = LocalView.current
    val status = statusOf(hid, true)

    DisposableEffect(settings.keepScreenOn) {
        view.keepScreenOn = settings.keepScreenOn
        activity.volumeKeysCaptured = true
        onDispose {
            view.keepScreenOn = false
            activity.volumeKeysCaptured = false
        }
    }

    Column(
        Modifier.fillMaxSize().background(Palette.Background).statusBarsPadding().navigationBarsPadding()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        // Header
        Row(Modifier.fillMaxWidth().height(56.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Rounded.ArrowBack, "Back", tint = Palette.TextPrimary) }
            StatusDot(status.color, status.pulsing, 7.dp)
            Column(Modifier.weight(1f).padding(start = 4.dp)) {
                Text(status.title, style = MaterialTheme.typography.titleMedium)
                Text(
                    hid.host?.name ?: status.detail, style = MaterialTheme.typography.bodySmall,
                    color = Palette.TextSecondary, maxLines = 1,
                )
            }
            IconButton(onClick = { navigate(Route.SETTINGS) }) { Icon(Icons.Rounded.Tune, "Settings", tint = Palette.TextSecondary) }
        }

        AnimatedVisibility(!hid.connected, enter = expandVertically() + fadeIn(), exit = shrinkVertically() + fadeOut()) {
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Palette.SurfaceHigh).padding(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Not connected — controls are inactive.", style = MaterialTheme.typography.bodyMedium,
                    color = Palette.TextSecondary, modifier = Modifier.weight(1f))
                val last = settings.lastHostAddress
                if (last != null && hid.registered) SecondaryButton("Connect") { graph.hid.connect(last) }
                else SecondaryButton("Pair") { navigate(Route.PAIRING) }
            }
        }

        // Gesture pad + scroll strip
        Row(Modifier.fillMaxWidth().weight(1f), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            GesturePad(graph, Modifier.weight(1f).fillMaxHeight())
            ScrollStrip(graph, settings.scrollStepDp, Modifier.width(52.dp).fillMaxHeight())
        }

        // Pointer activation
        PointerButton(
            active = tracking.pointerActive && !tracking.paused,
            paused = tracking.paused,
            mode = settings.pointerMode,
            onToggle = { presenter.togglePointer() },
            onHold = { presenter.setPointerHeld(it) },
        )

        // Mouse buttons (press/release so drag works while moving the phone)
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            RemoteKey("Left click", null, Modifier.weight(1f), height = 58.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.LEFT, true) },
                onRelease = { presenter.setButton(MouseButtons.LEFT, false) })
            RemoteKey("Right click", null, Modifier.weight(1f), height = 58.dp, haptics = settings.haptics,
                onPress = { presenter.setButton(MouseButtons.RIGHT, true) },
                onRelease = { presenter.setButton(MouseButtons.RIGHT, false) })
        }

        // Slides
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            RemoteKey("Previous", Icons.AutoMirrored.Rounded.KeyboardArrowLeft, Modifier.weight(1f), height = 84.dp,
                haptics = settings.haptics, onClick = { presenter.previousSlide() })
            RemoteKey("Next", Icons.AutoMirrored.Rounded.KeyboardArrowRight, Modifier.weight(1.4f), height = 84.dp, accent = true,
                haptics = settings.haptics, onClick = { presenter.nextSlide() })
        }

        // Utility row
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            RemoteKey("", Icons.Rounded.CenterFocusStrong, Modifier.weight(1f), height = 52.dp, haptics = settings.haptics,
                onClick = { presenter.recenter() })
            RemoteKey("", if (tracking.paused) Icons.Rounded.PlayArrow else Icons.Rounded.Pause, Modifier.weight(1f), height = 52.dp,
                active = tracking.paused, haptics = settings.haptics, onClick = { presenter.setPaused(!tracking.paused) })
            RemoteKey("", Icons.Rounded.DarkMode, Modifier.weight(1f), height = 52.dp, haptics = settings.haptics,
                onClick = { presenter.perform(RemoteAction.BLACK_SCREEN) })
            RemoteKey("", Icons.Rounded.Slideshow, Modifier.weight(1f), height = 52.dp, haptics = settings.haptics,
                onClick = { presenter.perform(RemoteAction.START_SLIDESHOW) })
            RemoteKey("", Icons.Rounded.StopCircle, Modifier.weight(1f), height = 52.dp, haptics = settings.haptics,
                onClick = { presenter.perform(RemoteAction.END_SLIDESHOW) })
        }
        Text(
            "Recenter · Pause · Black screen · Start show · End show",
            style = MaterialTheme.typography.labelSmall.copy(letterSpacing = MaterialTheme.typography.labelMedium.letterSpacing),
            color = Palette.TextTertiary, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(4.dp))
    }
}

@Composable
private fun PointerButton(active: Boolean, paused: Boolean, mode: PointerMode, onToggle: () -> Unit, onHold: (Boolean) -> Unit) {
    val view = LocalView.current
    var pressed by remember { mutableStateOf(false) }
    val transition = rememberInfiniteTransition(label = "laser")
    val sweep by transition.animateFloat(0f, 1f, infiniteRepeatable(tween(2200), RepeatMode.Restart), label = "sweep")
    val glow by animateFloatAsState(if (active) 1f else 0f, tween(300), label = "glow")
    val scale by animateFloatAsState(if (pressed) 0.97f else 1f, label = "scale")
    val border by animateColorAsState(if (active) Palette.Accent else Palette.Outline, label = "border")
    val label = when {
        paused -> "Tracking paused"
        mode == PointerMode.HOLD -> if (active) "Pointing…" else "Hold to point"
        else -> if (active) "Pointer on" else "Pointer off"
    }
    Box(
        Modifier.fillMaxWidth().height(64.dp).scale(scale).clip(RoundedCornerShape(32.dp))
            .background(Palette.Surface)
            .drawBehind {
                if (glow > 0f) {
                    val x = size.width * sweep
                    drawRoundRect(
                        Brush.horizontalGradient(
                            listOf(Color.Transparent, Palette.Accent.copy(alpha = 0.28f * glow), Color.Transparent),
                            startX = x - size.width * 0.35f, endX = x + size.width * 0.35f,
                        ),
                        cornerRadius = CornerRadius(size.height / 2),
                    )
                }
            }
            .border(1.5.dp, border, RoundedCornerShape(32.dp))
            .pointerInput(mode) {
                awaitEachGesture {
                    awaitFirstDown()
                    pressed = true
                    view.performHapticFeedback(HapticFeedbackConstants.VIRTUAL_KEY)
                    if (mode == PointerMode.HOLD) onHold(true)
                    var done = false
                    try {
                        val up = waitForUpOrCancellation()
                        done = true
                        pressed = false
                        if (mode == PointerMode.HOLD) onHold(false) else if (up != null) onToggle()
                    } finally {
                        if (!done) { pressed = false; if (mode == PointerMode.HOLD) onHold(false) }
                    }
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Box(Modifier.size(10.dp).clip(RoundedCornerShape(5.dp)).background(if (active) Palette.Accent else Palette.TextTertiary))
            Text(label, style = MaterialTheme.typography.titleMedium, color = if (active) Palette.TextPrimary else Palette.TextSecondary)
        }
    }
}

@Composable
private fun GesturePad(graph: AppGraph, modifier: Modifier) {
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val presenter = graph.presenter
    val view = LocalView.current
    val density = LocalDensity.current
    val swipeThreshold = with(density) { 56.dp.toPx() }
    var touching by remember { mutableStateOf(false) }
    val highlight by animateFloatAsState(if (touching) 1f else 0f, tween(180), label = "hl")

    fun fire(a: RemoteAction) {
        if (a == RemoteAction.NONE) return
        if (settings.haptics) view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
        presenter.perform(a)
    }

    Box(
        modifier.clip(RoundedCornerShape(28.dp))
            .background(Brush.verticalGradient(listOf(Palette.Surface, Palette.SurfaceHigh.copy(alpha = 0.6f + 0.4f * highlight))))
            .border(1.dp, Palette.Outline.copy(alpha = 0.6f + 0.4f * highlight), RoundedCornerShape(28.dp))
            .pointerInput(settings.tapAction, settings.doubleTapAction, settings.longPressAction) {
                val tap = settings.tapAction; val dbl = settings.doubleTapAction; val lp = settings.longPressAction
                detectTapGestures(
                    onPress = { touching = true; tryAwaitRelease(); touching = false },
                    onTap = { fire(tap) },
                    onDoubleTap = if (dbl != RemoteAction.NONE) { _ -> fire(dbl) } else null,
                    onLongPress = if (lp != RemoteAction.NONE) { _ -> fire(lp) } else null,
                )
            }
            .pointerInput(settings.swipeLeftAction, settings.swipeRightAction, settings.swipeUpAction, settings.swipeDownAction) {
                var total = Offset.Zero
                detectDragGestures(
                    onDragStart = { total = Offset.Zero; touching = true },
                    onDragCancel = { touching = false },
                    onDragEnd = {
                        touching = false
                        val ax = abs(total.x); val ay = abs(total.y)
                        if (ax > swipeThreshold && ax > ay * 1.3f) fire(if (total.x < 0) settings.swipeLeftAction else settings.swipeRightAction)
                        else if (ay > swipeThreshold && ay > ax * 1.3f) fire(if (total.y < 0) settings.swipeUpAction else settings.swipeDownAction)
                    },
                ) { change, drag -> change.consume(); total += drag }
            },
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("GESTURE PAD", style = MaterialTheme.typography.labelSmall, color = Palette.TextTertiary)
            Text(gestureHint(settings), style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary, textAlign = TextAlign.Center)
        }
    }
}

private fun gestureHint(s: com.airpointer.remote.settings.AppSettings): String = buildList {
    if (s.tapAction != RemoteAction.NONE) add("Tap — ${s.tapAction.label.lowercase()}")
    if (s.doubleTapAction != RemoteAction.NONE) add("Double tap — ${s.doubleTapAction.label.lowercase()}")
    if (s.longPressAction != RemoteAction.NONE) add("Hold — ${s.longPressAction.label.lowercase()}")
    if (s.swipeLeftAction != RemoteAction.NONE) add("Swipe ← — ${s.swipeLeftAction.label.lowercase()}")
    if (s.swipeRightAction != RemoteAction.NONE) add("Swipe → — ${s.swipeRightAction.label.lowercase()}")
    if (s.swipeUpAction != RemoteAction.NONE) add("Swipe ↑ — ${s.swipeUpAction.label.lowercase()}")
    if (s.swipeDownAction != RemoteAction.NONE) add("Swipe ↓ — ${s.swipeDownAction.label.lowercase()}")
}.joinToString("\n")

@Composable
private fun ScrollStrip(graph: AppGraph, stepDp: Int, modifier: Modifier) {
    val density = LocalDensity.current
    val step = with(density) { stepDp.dp.toPx() }
    val view = LocalView.current
    var active by remember { mutableStateOf(false) }
    var offset by remember { mutableStateOf(0f) }
    Box(
        modifier.clip(RoundedCornerShape(26.dp)).background(if (active) Palette.SurfaceHighest else Palette.Surface)
            .border(1.dp, Palette.Outline.copy(alpha = 0.6f), RoundedCornerShape(26.dp))
            .pointerInput(step) {
                var acc = 0f
                detectVerticalDragGestures(
                    onDragStart = { acc = 0f; active = true },
                    onDragEnd = { active = false },
                    onDragCancel = { active = false },
                ) { change, dy ->
                    change.consume()
                    acc += dy
                    offset = (offset + dy) % (step * 2)
                    while (abs(acc) >= step) {
                        val dir = if (acc > 0) -1 else 1 // drag down = scroll down (wheel toward user)
                        graph.presenter.scroll(dir)
                        view.performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK)
                        acc -= if (acc > 0) step else -step
                    }
                }
            }
            .drawBehind {
                // Wheel ridges that follow the finger.
                val gap = step
                var y = (offset % gap + gap) % gap
                while (y < size.height) {
                    drawLine(Palette.Outline, Offset(size.width * 0.3f, y), Offset(size.width * 0.7f, y), strokeWidth = 2f)
                    y += gap
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        Icon(Icons.Rounded.UnfoldMore, "Scroll", tint = Palette.TextSecondary,
            modifier = Modifier.background(if (active) Palette.SurfaceHighest else Palette.Surface).padding(vertical = 6.dp))
    }
}
