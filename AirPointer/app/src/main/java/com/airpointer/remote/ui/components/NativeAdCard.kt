package com.airpointer.remote.ui.components

import android.view.LayoutInflater
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.ads.AdPlacement
import com.airpointer.remote.ads.NativeAdBinder
import com.airpointer.remote.ads.NativeAdCache
import com.airpointer.remote.graph
import com.airpointer.remote.ui.theme.Palette

/**
 * Reusable native ad slot. Requests (or reuses) the cached ad for [placement] while [allowed],
 * shows a compact skeleton while the first ad loads, and collapses completely — no empty gap —
 * when ads are unavailable (no consent, offline, no fill, error) or not [allowed].
 */
@Composable
fun NativeAdCard(placement: AdPlacement, allowed: Boolean, modifier: Modifier = Modifier) {
    val ads = LocalContext.current.graph.ads
    val ready by ads.ready.collectAsStateWithLifecycle()
    val slots by ads.ads.collectAsStateWithLifecycle()
    LaunchedEffect(placement, allowed, ready) { if (allowed && ready) ads.request(placement) }

    val slot = slots[placement]
    val ad = if (allowed && ready) ads.displayable(placement) else null
    val loading = allowed && ready && ad == null && slot is NativeAdCache.Slot.Loading

    AnimatedVisibility(
        visible = ad != null || loading,
        enter = expandVertically(tween(220)) + fadeIn(tween(220)),
        exit = shrinkVertically(tween(200)) + fadeOut(tween(150)),
        modifier = modifier,
    ) {
        if (ad != null) {
            AndroidView(
                factory = { ctx -> NativeAdBinder.inflate(null, LayoutInflater.from(ctx), compact = placement.compact) },
                update = { view -> NativeAdBinder.bind(view, ad) },
                modifier = Modifier.fillMaxWidth(),
            )
        } else AdSkeleton(compact = placement.compact)
    }
}

/** Loading state: same frame and attribution as the ad, neutral placeholder bars. */
@Composable
private fun AdSkeleton(compact: Boolean) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(Palette.Surface)
            .border(1.dp, Palette.Outline, RoundedCornerShape(20.dp)).padding(16.dp)
            .semantics { contentDescription = "Advertisement loading" },
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        if (!compact) Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Box(Modifier.clip(RoundedCornerShape(6.dp)).border(1.dp, Palette.Accent, RoundedCornerShape(6.dp)).padding(horizontal = 6.dp)) {
                Text("Ad", style = MaterialTheme.typography.labelMedium, color = Palette.Accent)
            }
            Text("Sponsored", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(if (compact) 40.dp else 44.dp).clip(RoundedCornerShape(10.dp)).background(Palette.SurfaceHigh))
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Box(Modifier.fillMaxWidth(0.7f).height(14.dp).clip(RoundedCornerShape(4.dp)).background(Palette.SurfaceHigh))
                Box(Modifier.fillMaxWidth(0.9f).height(12.dp).clip(RoundedCornerShape(4.dp)).background(Palette.SurfaceHigh))
            }
        }
    }
}
