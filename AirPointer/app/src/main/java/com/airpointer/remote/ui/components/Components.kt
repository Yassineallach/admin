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
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight
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
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.layout.heightIn
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.disabled
import androidx.compose.ui.semantics.onClick
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import com.airpointer.remote.ui.theme.Palette
import com.airpointer.remote.ui.theme.Spacing

@Composable
fun ScreenScaffold(
    title: String,
    onBack: (() -> Unit)?,
    scrollable: Boolean = true,
    actions: @Composable RowScope.() -> Unit = {},
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(Modifier.fillMaxSize().background(Palette.Background).statusBarsPadding().navigationBarsPadding()) {
        RemoteToolbar(title = title, onBack = onBack, actions = actions)
        val m = Modifier.fillMaxSize().padding(horizontal = Spacing.screen)
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
            .clip(RoundedCornerShape(20.dp))
            .background(Palette.Surface)
            .border(1.dp, Palette.Outline, RoundedCornerShape(20.dp))
            .padding(padding),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        content = content,
    )
}

@Composable
fun SectionLabel(text: String, modifier: Modifier = Modifier) = SectionHeader(text, modifier.padding(top = 8.dp))

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
 * Rounded remote-control key with press animation and haptic feedback.
 * [onPress]/[onRelease] give raw down/up (mouse buttons, so drag works); [onClick] fires on release.
 * Icon-only keys must pass [contentDescription]: it is read by TalkBack, and TalkBack's double-tap
 * activates the key through the semantics action.
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
    contentDescription: String? = null,
    stacked: Boolean = false,
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
    val scale by animateFloatAsState(if (pressed) 0.96f else 1f, spring(dampingRatio = 0.6f, stiffness = 900f), label = "s")
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
        accent -> Palette.OnAccent
        active -> Palette.Accent
        else -> Palette.TextPrimary
    }
    val spoken = contentDescription ?: label
    Box(
        modifier
            .heightIn(min = maxOf(height, 48.dp))
            .scale(scale)
            .clip(RoundedCornerShape(16.dp))
            .background(bg)
            .border(1.dp, if (active) Palette.Accent.copy(alpha = 0.5f) else Palette.Outline, RoundedCornerShape(16.dp))
            .semantics {
                role = Role.Button
                this.contentDescription = spoken
                if (!enabled) disabled()
                if (enabled) onClick(spoken) {
                    currentOnPress.value?.invoke(); currentOnRelease.value?.invoke(); currentOnClick.value?.invoke(); true
                }
            }
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
        if (stacked) Column(Modifier.padding(horizontal = 4.dp, vertical = 8.dp), horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(4.dp)) {
            if (icon != null) Icon(icon, contentDescription = null, tint = fg, modifier = Modifier.size(22.dp))
            if (label.isNotEmpty()) Text(label, style = MaterialTheme.typography.labelMedium.copy(letterSpacing = 0.2.sp), color = fg,
                maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
        } else Row(Modifier.padding(horizontal = 10.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            if (icon != null) Icon(icon, contentDescription = null, tint = fg, modifier = Modifier.size(22.dp))
            if (label.isNotEmpty()) Text(label, style = MaterialTheme.typography.labelLarge, color = fg, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
fun PrimaryButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, icon: ImageVector? = null, onClick: () -> Unit) {
    Row(
        modifier.heightIn(min = 52.dp).clip(RoundedCornerShape(12.dp))
            .background(if (enabled) Palette.Accent else Palette.SurfaceHigh)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = 20.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
    ) {
        val fg = if (enabled) Palette.OnAccent else Palette.TextTertiary
        if (icon != null) Icon(icon, null, tint = fg, modifier = Modifier.size(20.dp))
        Text(text, style = MaterialTheme.typography.labelLarge, color = fg, textAlign = TextAlign.Center)
    }
}

@Composable
fun SecondaryButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, icon: ImageVector? = null, onClick: () -> Unit) {
    Row(
        modifier.heightIn(min = 52.dp).clip(RoundedCornerShape(12.dp)).background(Palette.SurfaceHigh)
            .border(1.dp, Palette.Outline, RoundedCornerShape(12.dp))
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
    ) {
        val fg = if (enabled) Palette.TextPrimary else Palette.TextTertiary
        if (icon != null) Icon(icon, null, tint = fg, modifier = Modifier.size(18.dp))
        Text(text, style = MaterialTheme.typography.labelLarge, color = fg, textAlign = TextAlign.Center)
    }
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
            Text(valueLabel, style = MaterialTheme.typography.labelLarge, color = Palette.TextPrimary)
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
    Row(Modifier.fillMaxWidth().heightIn(min = 48.dp).clip(RoundedCornerShape(12.dp)).clickable(role = Role.Button) { open = true }
        .padding(vertical = 8.dp).semantics(mergeDescendants = true) {}, verticalAlignment = Alignment.CenterVertically) {
        Text(label, style = MaterialTheme.typography.titleMedium, color = Palette.TextPrimary, modifier = Modifier.weight(1f))
        Text(labelOf(selected), style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary, maxLines = 2, overflow = TextOverflow.Ellipsis,
            textAlign = TextAlign.End, modifier = Modifier.padding(start = 12.dp).widthIn(max = 220.dp))
        Icon(Icons.AutoMirrored.Rounded.KeyboardArrowRight, null, tint = Palette.TextSecondary, modifier = Modifier.padding(start = 4.dp).size(20.dp))
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

/** Rounded segmented selector. */
@Composable
fun <T> Segmented(options: List<T>, selected: T, label: (T) -> String, modifier: Modifier = Modifier, onSelect: (T) -> Unit) {
    Row(
        modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(Palette.Surface)
            .border(1.dp, Palette.Outline, RoundedCornerShape(16.dp)).padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        for (o in options) {
            val active = o == selected
            Box(
                Modifier.weight(1f).heightIn(min = 44.dp).clip(RoundedCornerShape(12.dp))
                    .background(if (active) Palette.SurfaceHighest else Color.Transparent)
                    .border(1.dp, if (active) Palette.Outline else Color.Transparent, RoundedCornerShape(12.dp))
                    .clickable(role = Role.Tab) { onSelect(o) }.semantics { this.selected = active },
                contentAlignment = Alignment.Center,
            ) {
                Text(label(o), style = MaterialTheme.typography.labelLarge, color = if (active) Palette.TextPrimary else Palette.TextSecondary,
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

/** Inline banner on remote screens when the selected link is down. */
@Composable
fun NotConnectedBanner(text: String, action: String, onAction: () -> Unit) =
    NotificationBanner(title = "NOT CONNECTED", message = text, tone = BannerTone.WARNING, primary = action to onAction)

/** Low-emphasis action (secondary choices next to a primary button): text only, 48dp target, ripple. */
@Composable
fun TertiaryButton(text: String, modifier: Modifier = Modifier, color: Color = Palette.TextPrimary, onClick: () -> Unit) {
    Box(
        modifier.heightIn(min = 48.dp).clip(RoundedCornerShape(12.dp))
            .clickable(role = Role.Button, onClick = onClick).padding(horizontal = 16.dp, vertical = 10.dp),
        contentAlignment = Alignment.Center,
    ) { Text(text, style = MaterialTheme.typography.labelLarge, color = color, textAlign = TextAlign.Center) }
}
