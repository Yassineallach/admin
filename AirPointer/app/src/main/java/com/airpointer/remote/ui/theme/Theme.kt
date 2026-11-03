package com.airpointer.remote.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

object Palette {
    val Background = Color(0xFF0A0B0E)
    val Surface = Color(0xFF121419)
    val SurfaceHigh = Color(0xFF1A1D24)
    val SurfaceHighest = Color(0xFF242832)
    val Outline = Color(0xFF2A2F39)
    val TextPrimary = Color(0xFFF2F3F5)
    val TextSecondary = Color(0xFF9BA1AC)
    val TextTertiary = Color(0xFF636A76)
    val Accent = Color(0xFFFF5A4F)       // "laser" red
    val AccentDim = Color(0x26FF5A4F)
    val Positive = Color(0xFF3DDC97)
    val Warning = Color(0xFFF5B94A)
    val Negative = Color(0xFFFF6B6B)
}

private val Sans = FontFamily.SansSerif

val AppTypography = Typography(
    displayLarge = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Light, fontSize = 44.sp, letterSpacing = (-1.2).sp, lineHeight = 48.sp),
    displaySmall = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Light, fontSize = 32.sp, letterSpacing = (-0.6).sp, lineHeight = 38.sp),
    headlineSmall = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Normal, fontSize = 22.sp, letterSpacing = (-0.2).sp),
    titleLarge = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Medium, fontSize = 20.sp, letterSpacing = (-0.2).sp),
    titleMedium = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Medium, fontSize = 16.sp, letterSpacing = 0.sp),
    bodyLarge = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Normal, fontSize = 16.sp, lineHeight = 23.sp),
    bodyMedium = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 17.sp),
    labelLarge = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Medium, fontSize = 14.sp, letterSpacing = 0.2.sp),
    labelMedium = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Medium, fontSize = 12.sp, letterSpacing = 0.4.sp),
    labelSmall = TextStyle(fontFamily = Sans, fontWeight = FontWeight.Medium, fontSize = 11.sp, letterSpacing = 1.6.sp),
)

private val Colors = darkColorScheme(
    primary = Palette.Accent,
    onPrimary = Color.White,
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
            small = RoundedCornerShape(12.dp),
            medium = RoundedCornerShape(18.dp),
            large = RoundedCornerShape(26.dp),
        ),
        content = content,
    )
}
