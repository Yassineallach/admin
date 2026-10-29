package com.opengenerativeai.imagestudio.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Dark-by-default palette with the electric cyan accent of Open Generative AI's web studio.
val Accent = Color(0xFF22D3EE)
private val AppBackground = Color(0xFF050505)
private val Panel = Color(0xFF111114)
private val PanelHigh = Color(0xFF1A1A1F)

private val Colors = darkColorScheme(
    primary = Accent,
    onPrimary = Color(0xFF00242B),
    primaryContainer = Color(0xFF0B3B44),
    onPrimaryContainer = Color(0xFFB8F3FC),
    secondary = Color(0xFF94A3B8),
    // Selected chips, segments and the nav indicator use the secondary container.
    secondaryContainer = Color(0xFF0B3B44),
    onSecondaryContainer = Color(0xFFB8F3FC),
    background = AppBackground,
    onBackground = Color(0xFFEDEDF0),
    surface = AppBackground,
    onSurface = Color(0xFFEDEDF0),
    surfaceVariant = PanelHigh,
    onSurfaceVariant = Color(0xFFA1A1AA),
    surfaceContainerLowest = AppBackground,
    surfaceContainerLow = Panel,
    surfaceContainer = Panel,
    surfaceContainerHigh = PanelHigh,
    surfaceContainerHighest = Color(0xFF232329),
    outline = Color(0xFF3F3F46),
    outlineVariant = Color(0xFF27272A),
    error = Color(0xFFF87171),
)

@Composable
fun ImageStudioTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Colors, content = content)
}
