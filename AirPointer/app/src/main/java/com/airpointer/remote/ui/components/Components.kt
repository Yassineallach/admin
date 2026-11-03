package com.airpointer.remote.ui.components

import android.view.HapticFeedbackConstants
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.waitForUpOrCancellation
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.Check
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.airpointer.remote.ui.theme.Palette

@Composable
fun ScreenScaffold(
    title: String,
    onBack: (() -> Unit)?,
    scrollable: Boolean = true,
    actions: @Composable RowScope.() -> Unit = {},
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        Modifier.fillMaxSize().background(Palette.Background).statusBarsPadding().navigationBarsPadding(),
    ) {
        Row(
            Modifier.fillMaxWidth().height(60.dp).padding(horizontal = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (onBack != null) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Back", tint = Palette.TextPrimary)
                }
            } else Spacer(Modifier.width(12.dp))
            Text(title, style = MaterialTheme.typography.titleLarge, color = Palette.TextPrimary, modifier = Modifier.weight(1f))
            actions()
        }
        val m = Modifier.fillMaxSize().padding(horizontal = 20.dp)
        Column(
            if (scrollable) m.verticalScroll(rememberScrollState()) else m,
            verticalArrangement = Arrangement.spacedBy(14.dp),
            content = {
                content()
                Spacer(Modifier.height(24.dp))
            },
        )
    }
}

@Composable
fun Panel(modifier: Modifier = Modifier, padding: Dp = 18.dp, content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(24.dp))
            .background(Palette.Surface)
            .border(1.dp, Palette.Outline.copy(alpha = 0.6f), RoundedCornerShape(24.dp))
            .padding(padding),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        content = content,
    )
}

@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier) {
    Text(text.uppercase(), style = MaterialTheme.typography.labelSmall, color = Palette.TextTertiary, modifier = modifier.padding(top = 8.dp, start = 4.dp))
}

@Composable
fun StatusDot(color: Color, pulsing: Boolean, size: Dp = 10.dp) {
    val transition = rememberInfiniteTransition(label = "pulse")
    val pulse by transition.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1400), RepeatMode.Restart), label = "p",
    )
    val animatedColor by animateColorAsState(color, tween(400), label = "c")
    Box(
        Modifier.size(size * 2.2f).drawBehind {
            val r = this.size.minDimension / 2
            if (pulsing) drawCircle(animatedColor.copy(alpha = (1f - pulse) * 0.45f), radius = r * (0.45f + 0.55f * pulse))
            drawCircle(animatedColor, radius = size.toPx() / 2)
        },
    )
}

/**
 * Rounded remote control key with press animation and haptic feedback.
 * [onPress]/[onRelease] give raw down/up (used for mouse buttons so drag works);
 * [onClick] is fired on release inside the key.
 */
@Composable
fun RemoteKey(
    label: String,
    icon: ImageVector?,
    modifier: Modifier = Modifier,
    accent: Boolean = false,
    active: Boolean = false,
    enabled: Boolean = true,
    height: Dp = 64.dp,
    haptics: Boolean = true,
    onPress: (() -> Unit)? = null,
    onRelease: (() -> Unit)? = null,
    onClick: (() -> Unit)? = null,
) {
    var pressed by remember { mutableStateOf(false) }
    val view = LocalView.current
    val currentOnPress = rememberUpdatedState(onPress)
    val currentOnRelease = rememberUpdatedState(onRelease)
    val currentOnClick = rememberUpdatedState(onClick)
    val currentHaptics = rememberUpdatedState(haptics)
    val scale by animateFloatAsState(if (pressed) 0.95f else 1f, spring(dampingRatio = 0.55f, stiffness = 700f), label = "s")
    val bg by animateColorAsState(
        when {
            !enabled -> Palette.Surface
            pressed && accent -> Palette.Accent.copy(alpha = 0.85f)
            accent -> Palette.Accent
            active -> Palette.AccentDim
            pressed -> Palette.SurfaceHighest
            else -> Palette.SurfaceHigh
        }, tween(120), label = "bg",
    )
    val fg = when {
        !enabled -> Palette.TextTertiary
        accent -> Color.White
        active -> Palette.Accent
        else -> Palette.TextPrimary
    }
    Box(
        modifier
            .height(height)
            .scale(scale)
            .clip(RoundedCornerShape(20.dp))
            .background(bg)
            .border(1.dp, if (active) Palette.Accent.copy(alpha = 0.5f) else Palette.Outline.copy(alpha = 0.5f), RoundedCornerShape(20.dp))
            .pointerInput(enabled) {
                if (!enabled) return@pointerInput
                awaitEachGesture {
                    awaitFirstDown(requireUnconsumed = false)
                    pressed = true
                    if (currentHaptics.value) view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                    currentOnPress.value?.invoke()
                    var released = false
                    try {
                        val up = waitForUpOrCancellation()
                        pressed = false
                        released = true
                        currentOnRelease.value?.invoke()
                        if (up != null) currentOnClick.value?.invoke()
                    } finally {
                        // Gesture coroutine cancelled mid-press: never leave a mouse button held.
                        if (!released) { pressed = false; currentOnRelease.value?.invoke() }
                    }
                }
            },
        contentAlignment = Alignment.Center,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (icon != null) Icon(icon, contentDescription = label, tint = fg, modifier = Modifier.size(22.dp))
            if (label.isNotEmpty()) Text(label, style = MaterialTheme.typography.labelLarge, color = fg, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
fun PrimaryButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    val bg = if (enabled) Palette.Accent else Palette.SurfaceHigh
    Box(
        modifier.height(52.dp).clip(RoundedCornerShape(16.dp)).background(bg)
            .clickable(enabled = enabled, onClick = onClick).padding(horizontal = 20.dp),
        contentAlignment = Alignment.Center,
    ) { Text(text, style = MaterialTheme.typography.labelLarge, color = if (enabled) Color.White else Palette.TextTertiary) }
}

@Composable
fun SecondaryButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    Box(
        modifier.height(44.dp).clip(RoundedCornerShape(14.dp)).background(Palette.SurfaceHigh)
            .border(1.dp, Palette.Outline, RoundedCornerShape(14.dp))
            .clickable(enabled = enabled, onClick = onClick).padding(horizontal = 16.dp),
        contentAlignment = Alignment.Center,
    ) { Text(text, style = MaterialTheme.typography.labelLarge, color = if (enabled) Palette.TextPrimary else Palette.TextTertiary) }
}

@Composable
fun SettingSlider(
    label: String,
    value: Float,
    range: ClosedFloatingPointRange<Float>,
    valueLabel: String,
    onChange: (Float) -> Unit,
    description: String? = null,
) {
    Column {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(label, style = MaterialTheme.typography.titleMedium, color = Palette.TextPrimary, modifier = Modifier.weight(1f))
            Text(valueLabel, style = MaterialTheme.typography.labelMedium.copy(fontFamily = FontFamily.Monospace), color = Palette.Accent)
        }
        if (description != null) Text(description, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        Slider(
            value = value, onValueChange = onChange, valueRange = range,
            colors = SliderDefaults.colors(
                thumbColor = Palette.TextPrimary, activeTrackColor = Palette.Accent,
                inactiveTrackColor = Palette.SurfaceHighest,
            ),
        )
    }
}

@Composable
fun SettingSwitch(label: String, checked: Boolean, onChange: (Boolean) -> Unit, description: String? = null) {
    Row(Modifier.fillMaxWidth().clickable { onChange(!checked) }.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f).padding(end = 12.dp)) {
            Text(label, style = MaterialTheme.typography.titleMedium, color = Palette.TextPrimary)
            if (description != null) Text(description, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        }
        Switch(
            checked = checked, onCheckedChange = onChange,
            colors = SwitchDefaults.colors(
                checkedTrackColor = Palette.Accent, checkedThumbColor = Color.White,
                uncheckedTrackColor = Palette.SurfaceHighest, uncheckedThumbColor = Palette.TextSecondary,
                uncheckedBorderColor = Palette.Outline,
            ),
        )
    }
}

@Composable
fun <T> SettingChoice(label: String, options: List<T>, selected: T, labelOf: (T) -> String, onSelect: (T) -> Unit) {
    var open by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).clickable { open = true }.padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = MaterialTheme.typography.titleMedium, color = Palette.TextPrimary, modifier = Modifier.weight(1f))
        Text(labelOf(selected), style = MaterialTheme.typography.bodyMedium, color = Palette.Accent, maxLines = 1, overflow = TextOverflow.Ellipsis,
            modifier = Modifier.padding(start = 12.dp))
    }
    if (open) {
        AlertDialog(
            onDismissRequest = { open = false },
            containerColor = Palette.SurfaceHigh,
            title = { Text(label, style = MaterialTheme.typography.titleLarge) },
            text = {
                LazyColumn {
                    items(options) { o ->
                        Row(
                            Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp))
                                .clickable { onSelect(o); open = false }.padding(vertical = 12.dp, horizontal = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(labelOf(o), style = MaterialTheme.typography.bodyLarge,
                                color = if (o == selected) Palette.Accent else Palette.TextPrimary, modifier = Modifier.weight(1f))
                            if (o == selected) Icon(Icons.Rounded.Check, null, tint = Palette.Accent)
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { open = false }) { Text("Close", color = Palette.TextSecondary) } },
        )
    }
}

@Composable
fun InfoRow(label: String, value: String, valueColor: Color = Palette.TextPrimary) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
        Text(label, style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary, modifier = Modifier.weight(0.45f))
        Text(value, style = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace), color = valueColor, modifier = Modifier.weight(0.55f))
    }
}

@Composable
fun Divider() {
    Box(Modifier.fillMaxWidth().height(1.dp).background(Palette.Outline.copy(alpha = 0.5f)))
}

@Composable
fun IconBadge(icon: ImageVector, tint: Color = Palette.TextPrimary, bg: Color = Palette.SurfaceHigh, size: Dp = 40.dp) {
    Box(Modifier.size(size).clip(CircleShape).background(bg), contentAlignment = Alignment.Center) {
        Icon(icon, null, tint = tint, modifier = Modifier.size(size * 0.5f))
    }
}
