package com.airpointer.remote.ui.components

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight
import androidx.compose.material.icons.rounded.Bluetooth
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.ErrorOutline
import androidx.compose.material.icons.rounded.Info
import androidx.compose.material.icons.rounded.MoreVert
import androidx.compose.material.icons.rounded.Wifi
import androidx.compose.material.icons.rounded.WarningAmber
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.airpointer.remote.R
import com.airpointer.remote.ui.CardAction
import com.airpointer.remote.ui.CardKind
import com.airpointer.remote.ui.CardState
import com.airpointer.remote.ui.Method
import com.airpointer.remote.ui.Tone
import com.airpointer.remote.ui.theme.Palette
import com.airpointer.remote.ui.theme.Spacing

// ------------------------------------------------------------------ IconContainer

/** Circular icon background (50 % radius). Decorative: the parent provides the spoken label. */
@Composable
fun IconContainer(icon: ImageVector, size: Dp = 48.dp, tint: Color = Palette.Accent, background: Color = Palette.AccentDim) {
    Box(Modifier.size(size).clip(CircleShape).background(background), contentAlignment = Alignment.Center) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(size * 0.46f))
    }
}

// ------------------------------------------------------------------ StatusIndicator

fun toneColor(t: Tone) = when (t) {
    Tone.NEUTRAL -> Palette.TextTertiary
    Tone.PROGRESS -> Palette.Warning
    Tone.SUCCESS -> Palette.Positive
    Tone.WARNING -> Palette.Warning
    Tone.ERROR -> Palette.Negative
}

/** Coloured dot + text label, so status never relies on colour alone. Pulses while in progress. */
@Composable
fun StatusIndicator(tone: Tone, label: String, modifier: Modifier = Modifier) {
    val color by animateColorAsState(toneColor(tone), tween(250), label = "status")
    Row(modifier.semantics(mergeDescendants = true) { liveRegion = LiveRegionMode.Polite },
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        StatusDot(color, pulsing = tone == Tone.PROGRESS || tone == Tone.SUCCESS, size = 8.dp)
        Text(label, style = MaterialTheme.typography.labelMedium, color = if (tone == Tone.NEUTRAL) Palette.TextSecondary else color)
    }
}

// ------------------------------------------------------------------ SectionHeader

@Composable
fun SectionHeader(text: String, modifier: Modifier = Modifier, trailing: @Composable RowScope.() -> Unit = {}) {
    Row(modifier.fillMaxWidth().semantics { heading() }, verticalAlignment = Alignment.CenterVertically) {
        Text(text.uppercase(), style = MaterialTheme.typography.labelSmall, color = Palette.TextSecondary, modifier = Modifier.weight(1f))
        trailing()
    }
}

// ------------------------------------------------------------------ AppHeader

data class MenuEntry(val label: String, val icon: ImageVector? = null, val onClick: () -> Unit)

/** Compact branded header (≈56dp): icon, name, REMOTE CONTROL subtitle and an overflow menu. */
@Composable
fun AppHeader(menu: List<MenuEntry>) {
    var open by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth().heightIn(min = 56.dp).padding(start = Spacing.screen, end = 8.dp),
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Box(Modifier.size(40.dp).clip(CircleShape).background(Palette.SurfaceHigh), contentAlignment = Alignment.Center) {
            Image(painterResource(R.drawable.ic_launcher_foreground), contentDescription = null, modifier = Modifier.size(56.dp))
        }
        Column(Modifier.weight(1f).semantics(mergeDescendants = true) { heading() }) {
            Text("Air Pointer", style = MaterialTheme.typography.titleLarge, color = Palette.TextPrimary)
            Text("REMOTE CONTROL", style = MaterialTheme.typography.labelMedium, color = Palette.TextSecondary)
        }
        Box {
            IconButton(onClick = { open = true }) { Icon(Icons.Rounded.MoreVert, "More options", tint = Palette.TextPrimary) }
            DropdownMenu(open, onDismissRequest = { open = false }, containerColor = Palette.SurfaceHigh) {
                for (m in menu) DropdownMenuItem(
                    text = { Text(m.label, style = MaterialTheme.typography.bodyLarge, color = Palette.TextPrimary) },
                    leadingIcon = m.icon?.let { { Icon(it, null, tint = Palette.TextSecondary) } },
                    onClick = { open = false; m.onClick() },
                )
            }
        }
    }
}

// ------------------------------------------------------------------ ConnectionCard

/** The home screen's main card: connection state, computer, method, signal and the next action. */
@Composable
fun ConnectionCard(state: CardState, onAction: (CardAction) -> Unit, modifier: Modifier = Modifier) {
    val borderColor by animateColorAsState(
        when (state.tone) { Tone.SUCCESS -> Palette.Positive.copy(alpha = 0.45f); Tone.ERROR -> Palette.Negative.copy(alpha = 0.45f); else -> Palette.Outline },
        tween(250), label = "border",
    )
    Column(
        modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp)).background(Palette.Surface)
            .border(1.dp, borderColor, RoundedCornerShape(24.dp)).padding(Spacing.connectionCard),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            StatusIndicator(state.tone, state.title, Modifier.weight(1f))
            MethodChip(state.method)
        }
        AnimatedContent(state, transitionSpec = { fadeIn(tween(200)) togetherWith fadeOut(tween(150)) },
            contentKey = { it.kind to it.description }, label = "card") { s ->
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                if (s.kind == CardKind.CONNECTED) {
                    Text(s.computerName ?: "Your computer", style = MaterialTheme.typography.displaySmall, color = Palette.TextPrimary,
                        maxLines = 2, overflow = TextOverflow.Ellipsis)
                    Text(listOfNotNull("via ${s.method.label}", s.signal).joinToString(" · "),
                        style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
                } else {
                    Text(s.description, style = MaterialTheme.typography.bodyLarge, color = Palette.TextSecondary)
                }
            }
        }
        if (state.kind == CardKind.CONNECTING) LinearProgressIndicator(Modifier.fillMaxWidth().height(3.dp).clip(RoundedCornerShape(2.dp)),
            color = Palette.Warning, trackColor = Palette.SurfaceHighest)
        state.primary?.let { p ->
            val secondary = state.secondary
            if (p == CardAction.CANCEL) SecondaryButton(p.label, Modifier.fillMaxWidth()) { onAction(p) }
            else PrimaryButton(p.label, Modifier.fillMaxWidth()) { onAction(p) }
            if (secondary != null) TertiaryButton(secondary.label, Modifier.fillMaxWidth(),
                color = if (secondary == CardAction.DISCONNECT) Palette.TextSecondary else Palette.TextPrimary) { onAction(secondary) }
        }
    }
}

@Composable
private fun MethodChip(method: Method) {
    Row(Modifier.clip(RoundedCornerShape(12.dp)).background(Palette.SurfaceHigh).padding(horizontal = 10.dp, vertical = 6.dp)
        .semantics(mergeDescendants = true) { contentDescription = "Connection method: ${method.label}" },
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Icon(if (method == Method.WIFI) Icons.Rounded.Wifi else Icons.Rounded.Bluetooth, null, tint = Palette.TextSecondary, modifier = Modifier.size(16.dp))
        Text(method.label, style = MaterialTheme.typography.labelMedium, color = Palette.TextSecondary)
    }
}

// ------------------------------------------------------------------ RemoteCard

/** Preset tile: 48dp icon container, 18dp padding, 20dp radius, subtle border, press-scale feedback. */
@Composable
fun RemoteCard(
    icon: ImageVector, title: String, description: String, modifier: Modifier = Modifier,
    badge: String? = null, onClick: () -> Unit,
) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val scale by animateFloatAsState(if (pressed) 0.97f else 1f, tween(150), label = "press")
    Column(
        modifier.scale(scale).heightIn(min = 156.dp).clip(RoundedCornerShape(20.dp)).background(Palette.Surface)
            .border(1.dp, Palette.Outline, RoundedCornerShape(20.dp))
            .clickable(interactionSource = interaction, indication = androidx.compose.material3.ripple(), role = Role.Button, onClick = onClick)
            .padding(Spacing.card)
            .semantics(mergeDescendants = true) {},
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(verticalAlignment = Alignment.Top) {
            IconContainer(icon)
            Spacer(Modifier.weight(1f))
            if (badge != null) Text(badge, style = MaterialTheme.typography.labelMedium, color = Palette.Accent)
        }
        // No weight here: inside a scrolling screen there is no finite height to share, and a
        // weighted text block collapses (descriptions were clipped). Rows equalise card heights instead.
        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = Palette.TextPrimary)
            Text(description, style = MaterialTheme.typography.bodySmall.copy(fontSize = MaterialTheme.typography.bodyMedium.fontSize * 0.96f),
                color = Palette.TextSecondary, maxLines = 3, overflow = TextOverflow.Ellipsis)
        }
        Spacer(Modifier.weight(1f))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            Icon(Icons.AutoMirrored.Rounded.KeyboardArrowRight, null, tint = Palette.TextSecondary, modifier = Modifier.size(20.dp))
        }
    }
}

// ------------------------------------------------------------------ SetupItem

@Composable
fun SetupItem(icon: ImageVector, title: String, description: String, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 72.dp).clip(RoundedCornerShape(20.dp)).background(Palette.Surface)
            .border(1.dp, Palette.Outline, RoundedCornerShape(20.dp))
            .clickable(role = Role.Button, onClick = onClick).padding(horizontal = 16.dp, vertical = 14.dp)
            .semantics(mergeDescendants = true) {},
        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        IconContainer(icon, size = 44.dp, tint = Palette.TextPrimary, background = Palette.SurfaceHigh)
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = Palette.TextPrimary)
            Text(description, style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
        }
        Icon(Icons.AutoMirrored.Rounded.KeyboardArrowRight, null, tint = Palette.TextSecondary)
    }
}

// ------------------------------------------------------------------ RemoteToolbar

/** Shared compact top bar for every screen: back, title, live connection status, actions. */
@Composable
fun RemoteToolbar(
    title: String,
    onBack: (() -> Unit)?,
    status: Pair<Tone, String>? = null,
    actions: @Composable RowScope.() -> Unit = {},
) {
    Row(Modifier.fillMaxWidth().heightIn(min = 56.dp).padding(horizontal = 4.dp), verticalAlignment = Alignment.CenterVertically) {
        if (onBack != null) IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Rounded.ArrowBack, "Back", tint = Palette.TextPrimary) }
        else Spacer(Modifier.width(16.dp))
        Column(Modifier.weight(1f).padding(start = 4.dp)) {
            Text(title, style = MaterialTheme.typography.titleLarge, color = Palette.TextPrimary, maxLines = 1, overflow = TextOverflow.Ellipsis,
                modifier = Modifier.semantics { heading() })
            if (status != null) StatusIndicator(status.first, status.second)
        }
        actions()
    }
}

// ------------------------------------------------------------------ NotificationBanner

enum class BannerTone { INFO, SUCCESS, WARNING, ERROR }

/** Errors and connection events, with up to two recovery actions. */
@Composable
fun NotificationBanner(
    title: String,
    message: String,
    tone: BannerTone,
    modifier: Modifier = Modifier,
    primary: Pair<String, () -> Unit>? = null,
    secondary: Pair<String, () -> Unit>? = null,
    onDismiss: (() -> Unit)? = null,
) {
    val (color, icon) = when (tone) {
        BannerTone.INFO -> Palette.TextSecondary to Icons.Rounded.Info
        BannerTone.SUCCESS -> Palette.Positive to Icons.Rounded.CheckCircle
        BannerTone.WARNING -> Palette.Warning to Icons.Rounded.WarningAmber
        BannerTone.ERROR -> Palette.Negative to Icons.Rounded.ErrorOutline
    }
    Column(
        modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(Palette.SurfaceHigh)
            .border(1.dp, color.copy(alpha = 0.45f), RoundedCornerShape(20.dp)).padding(16.dp)
            .semantics { liveRegion = LiveRegionMode.Polite },
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(verticalAlignment = Alignment.Top, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(icon, null, tint = color, modifier = Modifier.size(22.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(title, style = MaterialTheme.typography.labelMedium, color = color)
                Text(message, style = MaterialTheme.typography.bodyMedium, color = Palette.TextPrimary)
            }
            if (onDismiss != null) IconButton(onClick = onDismiss, modifier = Modifier.size(48.dp)) {
                Icon(Icons.Rounded.Close, "Dismiss", tint = Palette.TextSecondary)
            }
        }
        if (primary != null || secondary != null) Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            primary?.let { (label, action) -> PrimaryButton(label, Modifier.weight(1f), onClick = action) }
            secondary?.let { (label, action) -> SecondaryButton(label, Modifier.weight(1f), onClick = action) }
        }
    }
}
