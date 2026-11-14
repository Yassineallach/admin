package com.airpointer.remote.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.airpointer.remote.AppGraph
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.Tone
import com.airpointer.remote.ui.components.BannerTone
import com.airpointer.remote.ui.components.NotificationBanner
import com.airpointer.remote.ui.components.RemoteToolbar
import com.airpointer.remote.ui.rememberLinkSnapshot
import com.airpointer.remote.ui.theme.Palette
import com.airpointer.remote.ui.theme.Spacing
import com.airpointer.remote.ui.toolbarStatus

/**
 * Shared layout for every remote: compact toolbar with live connection status, a recovery banner
 * when the computer link is down ([requiresComputer]), and the main interaction area.
 */
@Composable
fun RemoteFrame(
    graph: AppGraph,
    title: String,
    onBack: () -> Unit,
    navigate: (Route) -> Unit,
    requiresComputer: Boolean = true,
    status: Pair<Tone, String>? = null,
    actions: @Composable RowScope.() -> Unit = {},
    content: @Composable ColumnScope.() -> Unit,
) {
    val snapshot = rememberLinkSnapshot(graph, permissionsGranted = true)
    Column(Modifier.fillMaxSize().background(Palette.Background).statusBarsPadding().navigationBarsPadding()) {
        RemoteToolbar(title, onBack, status ?: snapshot.toolbarStatus(), actions)
        Column(Modifier.fillMaxSize().padding(horizontal = Spacing.screen).padding(bottom = 12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) {
            AnimatedVisibility(requiresComputer && !snapshot.connected,
                enter = expandVertically(tween(200)) + fadeIn(tween(200)), exit = shrinkVertically(tween(200)) + fadeOut(tween(150))) {
                val connecting = snapshot.connecting || snapshot.reconnectAttempt > 0
                NotificationBanner(
                    title = when { connecting -> "CONNECTING"; snapshot.lost -> "CONNECTION LOST"; else -> "NOT CONNECTED" },
                    message = when {
                        connecting -> "Establishing connection with ${snapshot.computerName ?: "your computer"}…"
                        snapshot.lost -> "${snapshot.computerName ?: "Your computer"} is no longer reachable. Controls resume when it reconnects."
                        else -> "$title needs your computer. Controls are inactive until it connects."
                    },
                    tone = if (connecting) BannerTone.INFO else if (snapshot.lost) BannerTone.ERROR else BannerTone.WARNING,
                    primary = if (connecting) null else (if (snapshot.lost) "Reconnect" else "Connect now") to {
                        if (!graph.linkMonitor.connect()) navigate(Route.PAIRING)
                    },
                    secondary = if (connecting) null else "Settings" to { navigate(Route.PAIRING) },
                )
            }
            content()
        }
    }
}
