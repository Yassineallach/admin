package com.airpointer.remote.ui.screens

import android.content.Intent
import android.os.Build
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Insights
import androidx.compose.material.icons.rounded.Mouse
import androidx.compose.material.icons.rounded.PlayCircle
import androidx.compose.material.icons.rounded.PowerSettingsNew
import androidx.compose.material.icons.rounded.SettingsInputAntenna
import androidx.compose.material.icons.rounded.Slideshow
import androidx.compose.material.icons.rounded.Tune
import androidx.compose.material.icons.rounded.Tv
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import androidx.compose.material.icons.rounded.PrivacyTip
import com.airpointer.remote.ads.AdPlacement
import com.airpointer.remote.ads.AdPlacementPolicy
import com.airpointer.remote.ui.components.NativeAdCard
import com.airpointer.remote.transport.TransportKind
import com.airpointer.remote.ui.AppActions
import com.airpointer.remote.ui.CardAction
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.components.AppHeader
import com.airpointer.remote.ui.components.ConnectionCard
import com.airpointer.remote.ui.components.MenuEntry
import com.airpointer.remote.ui.components.RemoteCard
import com.airpointer.remote.ui.components.SectionHeader
import com.airpointer.remote.ui.components.SetupItem
import com.airpointer.remote.ui.connectionCardState
import com.airpointer.remote.ui.rememberLinkSnapshot
import com.airpointer.remote.ui.theme.Palette
import com.airpointer.remote.ui.theme.Spacing

/** A remote preset; [needsComputer] remotes send input through the PC link. */
enum class Preset(val route: Route, val title: String, val short: String, val description: String, val icon: ImageVector, val needsComputer: Boolean) {
    PRESENTATION(Route.REMOTE, "Presentation", "Slides", "Slides, laser and air pointer", Icons.Rounded.Slideshow, true),
    MOUSE(Route.PC_MOUSE, "PC Mouse", "Mouse", "Touchpad, air mouse, keyboard", Icons.Rounded.Mouse, true),
    TV(Route.TV, "TV Remote", "TV", "Android TV, Samsung, LG, IR", Icons.Rounded.Tv, false),
    MEDIA(Route.MEDIA, "Media Player", "Media", "VLC and MPV on your PC", Icons.Rounded.PlayCircle, false);

    companion object { fun of(route: String) = entries.firstOrNull { it.route.name == route } }
}

@Composable
fun HomeScreen(graph: AppGraph, actions: AppActions, navigate: (Route) -> Unit, onStart: () -> Unit, onStop: () -> Unit) {
    val context = LocalContext.current
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val hid by graph.hid.state.collectAsStateWithLifecycle()
    val snapshot = rememberLinkSnapshot(graph, actions.permissionsGranted)
    val card = connectionCardState(snapshot)
    val privacyRequired by graph.consent.privacyOptionsRequired.collectAsStateWithLifecycle()
    var gated by rememberSaveable { mutableStateOf<String?>(null) }   // preset waiting for a decision
    var pending by rememberSaveable { mutableStateOf<String?>(null) }  // open this once connected

    fun open(p: Preset) {
        graph.settings.update { it.copy(lastRemote = p.route.name) }
        navigate(p.route)
    }
    fun connectOrSetUp() { if (!graph.linkMonitor.connect()) navigate(Route.PAIRING) }
    fun onAction(a: CardAction) = when (a) {
        CardAction.CONNECT, CardAction.RECONNECT -> connectOrSetUp()
        CardAction.SET_UP, CardAction.CONNECTION_SETTINGS -> navigate(Route.PAIRING)
        CardAction.CANCEL, CardAction.DISCONNECT -> { pending = null; graph.linkMonitor.disconnect() }
        CardAction.OPEN_REMOTE -> open(Preset.of(settings.lastRemote) ?: Preset.PRESENTATION)
        CardAction.ENABLE_BLUETOOTH -> actions.enableBluetooth()
        CardAction.GRANT_PERMISSION -> actions.requestPermissions()
        CardAction.WIFI_SETTINGS -> context.startActivity(
            Intent(if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) Settings.Panel.ACTION_WIFI else Settings.ACTION_WIFI_SETTINGS)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        CardAction.USE_WIFI -> {
            graph.settings.update { it.copy(transport = TransportKind.WIFI) }
            connectOrSetUp()
        }
        CardAction.START_SERVICE -> onStart()
        CardAction.TRY_AGAIN -> graph.hid.restart()
    }

    // A preset tapped while disconnected opens as soon as the connection is up.
    LaunchedEffect(snapshot.connected, pending) {
        val p = pending?.let { Preset.of(it) }
        if (snapshot.connected && p != null) { pending = null; open(p) }
    }

    Column(Modifier.fillMaxSize().background(Palette.Background).statusBarsPadding().navigationBarsPadding()) {
        AppHeader(menu = buildList {
            add(MenuEntry("Connection settings", Icons.Rounded.SettingsInputAntenna) { navigate(Route.PAIRING) })
            add(MenuEntry("Sensitivity & calibration", Icons.Rounded.Tune) { navigate(Route.SETTINGS) })
            add(MenuEntry("Diagnostics", Icons.Rounded.Insights) { navigate(Route.DIAGNOSTICS) })
            if (privacyRequired) add(MenuEntry("Privacy options", Icons.Rounded.PrivacyTip) {
                (context as? android.app.Activity)?.let { graph.consent.showPrivacyOptions(it) }
            })
            if (hid.serviceRunning) add(MenuEntry("Stop Bluetooth service", Icons.Rounded.PowerSettingsNew, onStop))
            else add(MenuEntry("Start Bluetooth service", Icons.Rounded.PowerSettingsNew, onStart))
        })
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = Spacing.screen)) {
            Spacer(Modifier.height(Spacing.headerToCard - 8.dp))
            ConnectionCard(card, ::onAction)

            if (snapshot.connected) {
                Spacer(Modifier.height(Spacing.section))
                SectionHeader("Your remotes")
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    // Last-used first, then the others in their usual order.
                    val last = Preset.of(settings.lastRemote)
                    val ordered = listOfNotNull(last) + Preset.entries.filter { it != last }
                    for (p in ordered) QuickRemote(p, p == last, Modifier.weight(1f)) { open(p) }
                }
            }

            Spacer(Modifier.height(Spacing.section))
            SectionHeader("Remote presets")
            Spacer(Modifier.height(12.dp))
            for (row in Preset.entries.chunked(2)) {
                Row(Modifier.height(IntrinsicSize.Max), horizontalArrangement = Arrangement.spacedBy(Spacing.grid)) {
                    for (p in row) RemoteCard(
                        p.icon, p.title, p.description, Modifier.weight(1f).fillMaxHeight(),
                        badge = if (p.needsComputer && !snapshot.connected) "Needs PC" else null,
                    ) { if (p.needsComputer && !snapshot.connected) gated = p.name else open(p) }
                }
                Spacer(Modifier.height(Spacing.grid))
            }

            Spacer(Modifier.height(Spacing.section - Spacing.grid))
            SectionHeader("Settings")
            Spacer(Modifier.height(12.dp))
            Column(verticalArrangement = Arrangement.spacedBy(Spacing.setupItem)) {
                SetupItem(Icons.Rounded.SettingsInputAntenna, "Connection",
                    "${if (settings.transport == TransportKind.WIFI) "Wi-Fi" else "Bluetooth"} · pairing and computers") { navigate(Route.PAIRING) }
                SetupItem(Icons.Rounded.Tune, "Sensitivity", "Pointer speed, smoothing, calibration") { navigate(Route.SETTINGS) }
                SetupItem(Icons.Rounded.Insights, "Diagnostics", "Link quality, sensors, event log") { navigate(Route.DIAGNOSTICS) }
            }
            // Native ad: bottom of the page (least disruptive), never near the connection card,
            // and only once a computer is set up so first-run onboarding stays ad-free.
            NativeAdCard(AdPlacement.HOME, allowed = AdPlacementPolicy.homeAllowed(snapshot.configured),
                modifier = Modifier.padding(top = Spacing.section))
            Spacer(Modifier.height(24.dp))
        }
    }

    gated?.let { name ->
        val p = Preset.valueOf(name)
        AlertDialog(
            onDismissRequest = { gated = null },
            containerColor = Palette.SurfaceHigh,
            title = { Text("Connect your computer first", style = MaterialTheme.typography.titleLarge) },
            text = {
                Text("${p.title} sends input to your PC, so it needs an active connection. " +
                    "Connect now and it opens as soon as the computer answers.",
                    style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
            },
            confirmButton = {
                TextButton(onClick = {
                    gated = null
                    if (graph.linkMonitor.connect()) pending = p.name else navigate(Route.PAIRING)
                }) { Text("Connect now", color = Palette.Accent, style = MaterialTheme.typography.labelLarge) }
            },
            dismissButton = {
                TextButton(onClick = { gated = null; open(p) }) {
                    Text("Open anyway", color = Palette.TextSecondary, style = MaterialTheme.typography.labelLarge)
                }
            },
        )
    }
}

@Composable
private fun QuickRemote(p: Preset, last: Boolean, modifier: Modifier, onClick: () -> Unit) {
    Column(
        modifier.heightIn(min = 76.dp).clip(RoundedCornerShape(16.dp))
            .background(if (last) Palette.AccentDim else Palette.Surface)
            .border(1.dp, if (last) Palette.Accent.copy(alpha = 0.6f) else Palette.Outline, RoundedCornerShape(16.dp))
            .clickable(role = Role.Button, onClick = onClick).padding(vertical = 12.dp, horizontal = 4.dp)
            .semantics(mergeDescendants = true) { if (last) stateDescription = "Last used" },
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Icon(p.icon, null, tint = if (last) Palette.Accent else Palette.TextPrimary)
        Text(p.short, style = MaterialTheme.typography.labelLarge.copy(fontSize = MaterialTheme.typography.bodySmall.fontSize),
            color = Palette.TextPrimary, textAlign = TextAlign.Center, maxLines = 1)
    }
}
