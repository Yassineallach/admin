package com.airpointer.remote.ui.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/**
 * Air Pointer palette. Contrast (WCAG) against Surface #14151A:
 * TextPrimary 16.6:1, TextSecondary 7.2:1, Accent 5.8:1, Positive 8.6:1, Warning 10.5:1.
 * TextTertiary ("muted", 3.5:1) is NOT used for readable text — only disabled controls and decoration.
 */
object Palette {
    val Background = Color(0xFF090A0D)
    val Surface = Color(0xFF14151A)        // primary surface
    val SurfaceHigh = Color(0xFF1B1D24)    // secondary surface
    val SurfaceHighest = Color(0xFF23252D) // pressed / selected
    val Outline = Color(0xFF272932)
    val Accent = Color(0xFFFF5752)         // coral — signature + primary actions
    val AccentDim = Color(0x26FF5752)
    val OnAccent = Color(0xFF090A0D)       // 6.4:1 on coral (white would be 3.1:1)
    val TextPrimary = Color(0xFFF4F4F6)
    val TextSecondary = Color(0xFFA0A2AC)
    val TextTertiary = Color(0xFF696C78)   // muted: disabled / decorative only
    val Positive = Color(0xFF35C98A)
    val PositiveDim = Color(0x2635C98A)
    val Warning = Color(0xFFF5BB4F)
    val WarningDim = Color(0x26F5BB4F)
    val Negative = Color(0xFFFF5752)
}

/** 8dp-based spacing system. */
object Spacing {
    val screen = 20.dp
    val headerToCard = 24.dp
    val section = 28.dp
    val grid = 14.dp
    val setupItem = 12.dp
    val card = 18.dp
    val connectionCard = 20.dp
}

private val Sans = FontFamily.SansSerif // Roboto (or the device's system sans)

val AppTypography = Typography(
    // Main title 28–32 Regular
    displaySmall = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Normal, fontSize = 30.sp, lineHeight = 36.sp, letterSpacing = (-0.3).sp),
    headlineSmall = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Normal, fontSize = 22.sp, lineHeight = 28.sp),
    titleLarge = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Medium, fontSize = 18.sp, lineHeight = 24.sp),
    // Card titles 16–17 Medium
    titleMedium = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Medium, fontSize = 16.5.sp, lineHeight = 22.sp),
    bodyLarge = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Normal, fontSize = 15.sp, lineHeight = 21.sp),
    // Descriptions 13–14 Regular
    bodyMedium = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Normal, fontSize = 13.sp, lineHeight = 18.sp),
    // Buttons 15–16 SemiBold
    labelLarge = TextStyle(fontFamily = Sans, fontWeight = FontWeight.SemiBold, fontSize = 15.sp, lineHeight = 20.sp, letterSpacing = 0.1.sp),
    // Status labels 11–12 SemiBold
    labelMedium = TextStyle(fontFamily = Sans, fontWeight = FontWeight.SemiBold, fontSize = 11.5.sp, lineHeight = 16.sp, letterSpacing = 0.8.sp),
    // Section headings 13–14 Medium
    labelSmall = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Medium, fontSize = 13.sp, lineHeight = 18.sp, letterSpacing = 1.1.sp),
)

private val Colors = darkColorScheme(
    primary = Palette.Accent,
    onPrimary = Palette.OnAccent,
    primaryContainer = Palette.AccentDim,
    onPrimaryContainer = Palette.Accent,
    secondary = Palette.Positive,
    background = Palette.Background,
    onBackground = Palette.TextPrimary,
    surface = Palette.Surface,
    onSurface = Palette.TextPrimary,
    surfaceVariant = Palette.SurfaceHigh,
    onSurfaceVariant = Palette.TextSecondary,
    surfaceContainerHigh = Palette.SurfaceHigh,
    surfaceContainerHighest = Palette.SurfaceHighest,
    outline = Palette.Outline,
    outlineVariant = Palette.Outline,
    error = Palette.Negative,
)

@Composable
fun AirPointerTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = Colors,
        typography = AppTypography,
        shapes = Shapes(
            small = RoundedCornerShape(12.dp),   // small buttons
            medium = RoundedCornerShape(20.dp),  // standard cards
            large = RoundedCornerShape(24.dp),   // connection card
        ),
    ) {
        // Text without an explicit colour must stay readable on every dark surface (Material's
        // default outside a Surface is black — "Nothing playing" was invisible).
        CompositionLocalProvider(LocalContentColor provides Palette.TextPrimary, content = content)
    }
}
