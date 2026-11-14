package com.airpointer.remote.ui.screens

import android.content.Intent
import android.speech.RecognizerIntent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import com.airpointer.remote.ui.Tone
import com.airpointer.remote.ui.components.BannerTone
import com.airpointer.remote.ui.components.NotificationBanner
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.VolumeDown
import androidx.compose.material.icons.automirrored.rounded.VolumeOff
import androidx.compose.material.icons.automirrored.rounded.VolumeUp
import androidx.compose.material.icons.rounded.Dialpad
import androidx.compose.material.icons.rounded.FastForward
import androidx.compose.material.icons.rounded.FastRewind
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.Input
import androidx.compose.material.icons.rounded.KeyboardArrowDown
import androidx.compose.material.icons.rounded.KeyboardArrowUp
import androidx.compose.material.icons.rounded.Menu
import androidx.compose.material.icons.rounded.Mic
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.PowerSettingsNew
import androidx.compose.material.icons.rounded.Settings
import androidx.compose.material.icons.rounded.Stop
import androidx.compose.material.icons.rounded.Tv
import androidx.compose.material.icons.automirrored.rounded.Undo
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowLeft
import androidx.compose.material.icons.automirrored.rounded.KeyboardArrowRight
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.ads.AdPlacement
import com.airpointer.remote.ui.components.NativeAdCard
import com.airpointer.remote.tv.IrCodeSet
import com.airpointer.remote.tv.IrRemote
import com.airpointer.remote.tv.SavedTv
import com.airpointer.remote.tv.TvConnState
import com.airpointer.remote.tv.TvConnection
import com.airpointer.remote.tv.TvDiscovery
import com.airpointer.remote.tv.TvKey
import com.airpointer.remote.tv.TvProtocol
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.components.Divider
import com.airpointer.remote.ui.components.IconBadge
import com.airpointer.remote.ui.components.Panel
import com.airpointer.remote.ui.components.PrimaryButton
import com.airpointer.remote.ui.components.RemoteKey
import com.airpointer.remote.ui.components.ScreenScaffold
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.SectionLabel
import com.airpointer.remote.ui.components.SettingChoice
import com.airpointer.remote.ui.components.StatusDot
import com.airpointer.remote.ui.theme.Palette
import kotlinx.coroutines.launch
import java.util.UUID

@Composable
fun TvRemoteScreen(graph: AppGraph, onBack: () -> Unit, navigate: (Route) -> Unit) {
    val tvs by graph.tvRepository.tvs.collectAsStateWithLifecycle()
    val selectedId by graph.tvRepository.selectedId.collectAsStateWithLifecycle()
    val conn by graph.tv.connection.collectAsStateWithLifecycle()
    val state by graph.tv.state.collectAsStateWithLifecycle()
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val selected = tvs.firstOrNull { it.id == selectedId }
    var numpad by rememberSaveable { mutableStateOf(false) }
    var showLimits by remember { mutableStateOf(false) }

    LaunchedEffect(selectedId) { graph.tv.connectSelected() }

    val voice = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { r ->
        val text = r.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
        if (!text.isNullOrBlank()) graph.tv.sendText(text)
    }

    val tvStatus: Pair<Tone, String> = when (state) {
        TvConnState.Connected -> Tone.SUCCESS to "CONNECTED · ${selected?.name?.uppercase() ?: "TV"}"
        TvConnState.Connecting -> Tone.PROGRESS to "CONNECTING"
        is TvConnState.NeedsUser -> Tone.WARNING to "ACTION NEEDED ON TV"
        is TvConnState.Failed -> Tone.ERROR to "TV UNREACHABLE"
        TvConnState.Disconnected -> Tone.NEUTRAL to if (selected == null) "NO TV SET UP" else "NOT CONNECTED"
    }
    RemoteFrame(graph, selected?.name ?: "TV Remote", onBack, navigate, requiresComputer = false, status = tvStatus, actions = {
        IconButton(onClick = { navigate(Route.TV_DEVICES) }) { Icon(Icons.Rounded.Tv, "Choose TV", tint = Palette.TextPrimary) }
    }) {
        if (selected == null || conn == null) {
            Panel {
                Text("Add your TV", style = MaterialTheme.typography.titleMedium)
                Text("Pick the brand, search the network or use infrared/Bluetooth, and pair once.", style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary)
                PrimaryButton("Add a TV", Modifier.fillMaxWidth()) { navigate(Route.TV_DEVICES) }
            }
            return@RemoteFrame
        }
        val c = conn!!

        when (val s = state) {
            is TvConnState.NeedsUser -> Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                NotificationBanner("ACTION NEEDED ON TV", s.message, BannerTone.WARNING)
                if (s.needsCode) CodeEntry { graph.tv.submitCode(it) }
            }
            is TvConnState.Failed -> NotificationBanner(
                "TV UNREACHABLE", s.reason, BannerTone.ERROR,
                primary = "Retry" to { graph.tv.connect(selected) },
                secondary = "Choose TV" to { navigate(Route.TV_DEVICES) },
            )
            else -> {}
        }

        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                TvButton(graph, c, TvKey.POWER, Icons.Rounded.PowerSettingsNew, Modifier.weight(1f), settings.haptics, accent = true)
                TvButton(graph, c, TvKey.SOURCE, Icons.Rounded.Input, Modifier.weight(1f), settings.haptics)
                TvButton(graph, c, TvKey.SETTINGS, Icons.Rounded.Settings, Modifier.weight(1f), settings.haptics)
                VoiceButton(c, Modifier.weight(1f), settings.haptics, onSend = { graph.tv.send(TvKey.VOICE) }) {
                    runCatching { voice.launch(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                        .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                        .putExtra(RecognizerIntent.EXTRA_PROMPT, "Say what to search on the TV")) }
                }
            }

            // D-pad
            // Directional pad: as large as the screen allows (up to 300dp), with 72dp+ arrow targets.
            BoxWithConstraints(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                val pad = minOf(maxWidth * 0.88f, 300.dp)
                val arrow = pad * 0.27f
                Column(Modifier.size(pad).clip(CircleShape).background(Palette.Surface).border(1.dp, Palette.Outline, CircleShape),
                    horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.SpaceEvenly) {
                    TvButton(graph, c, TvKey.UP, Icons.Rounded.KeyboardArrowUp, Modifier.size(arrow * 1.3f, arrow), settings.haptics, height = arrow)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        TvButton(graph, c, TvKey.LEFT, Icons.AutoMirrored.Rounded.KeyboardArrowLeft, Modifier.size(arrow, arrow * 1.3f), settings.haptics, height = arrow * 1.3f)
                        TvButton(graph, c, TvKey.OK, null, Modifier.size(pad * 0.32f), settings.haptics, accent = true, text = "OK", height = pad * 0.32f)
                        TvButton(graph, c, TvKey.RIGHT, Icons.AutoMirrored.Rounded.KeyboardArrowRight, Modifier.size(arrow, arrow * 1.3f), settings.haptics, height = arrow * 1.3f)
                    }
                    TvButton(graph, c, TvKey.DOWN, Icons.Rounded.KeyboardArrowDown, Modifier.size(arrow * 1.3f, arrow), settings.haptics, height = arrow)
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                TvButton(graph, c, TvKey.BACK, Icons.AutoMirrored.Rounded.Undo, Modifier.weight(1f), settings.haptics)
                TvButton(graph, c, TvKey.HOME, Icons.Rounded.Home, Modifier.weight(1f), settings.haptics)
                TvButton(graph, c, TvKey.MENU, Icons.Rounded.Menu, Modifier.weight(1f), settings.haptics)
            }

            // Volume / channel rockers
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    TvButton(graph, c, TvKey.VOLUME_UP, Icons.AutoMirrored.Rounded.VolumeUp, Modifier.fillMaxWidth(), settings.haptics)
                    TvButton(graph, c, TvKey.VOLUME_DOWN, Icons.AutoMirrored.Rounded.VolumeDown, Modifier.fillMaxWidth(), settings.haptics)
                }
                Column(Modifier.weight(0.7f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    TvButton(graph, c, TvKey.MUTE, Icons.AutoMirrored.Rounded.VolumeOff, Modifier.fillMaxWidth(), settings.haptics, height = 118.dp)
                }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    TvButton(graph, c, TvKey.CHANNEL_UP, null, Modifier.fillMaxWidth(), settings.haptics, text = "CH +")
                    TvButton(graph, c, TvKey.CHANNEL_DOWN, null, Modifier.fillMaxWidth(), settings.haptics, text = "CH −")
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                TvButton(graph, c, TvKey.REWIND, Icons.Rounded.FastRewind, Modifier.weight(1f), settings.haptics)
                TvButton(graph, c, TvKey.PLAY_PAUSE, Icons.Rounded.PlayArrow, Modifier.weight(1f), settings.haptics)
                TvButton(graph, c, TvKey.STOP, Icons.Rounded.Stop, Modifier.weight(1f), settings.haptics)
                TvButton(graph, c, TvKey.FAST_FORWARD, Icons.Rounded.FastForward, Modifier.weight(1f), settings.haptics)
            }

            SecondaryButton(if (numpad) "Hide number pad" else "Number pad", Modifier.fillMaxWidth()) { numpad = !numpad }
            if (numpad) {
                for (row in listOf(listOf(1, 2, 3), listOf(4, 5, 6), listOf(7, 8, 9))) Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    for (n in row) TvButton(graph, c, TvKey.digits[n], null, Modifier.weight(1f), settings.haptics, text = "$n")
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    TvButton(graph, c, TvKey.INFO, null, Modifier.weight(1f), settings.haptics, text = "Info")
                    TvButton(graph, c, TvKey.NUM_0, null, Modifier.weight(1f), settings.haptics, text = "0")
                    TvButton(graph, c, TvKey.EXIT, null, Modifier.weight(1f), settings.haptics, text = "Exit")
                }
            }

            val unsupported = TvKey.entries.filter { it !in c.supportedKeys && !(it == TvKey.VOICE && c.supportsText) }
            Panel(padding = 14.dp) {
                Text("Limitations of ${c.protocol.label}", style = MaterialTheme.typography.labelSmall, color = Palette.TextSecondary)
                if (unsupported.isNotEmpty()) Text("Not available with this connection: " + unsupported.joinToString { it.label },
                    style = MaterialTheme.typography.bodySmall, color = Palette.Warning)
                if (showLimits) c.limitations.forEach { Text("• $it", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary) }
                TextButton(onClick = { showLimits = !showLimits }) { Text(if (showLimits) "Less" else "More details", color = Palette.TextSecondary) }
            }
            // End of the scroll, well below every key.
            NativeAdCard(AdPlacement.TV, allowed = true, modifier = Modifier.padding(top = 16.dp))
        }
    }
}

@Composable
private fun TvButton(
    graph: AppGraph, c: TvConnection, key: TvKey, icon: ImageVector?, modifier: Modifier, haptics: Boolean,
    accent: Boolean = false, text: String? = null, height: androidx.compose.ui.unit.Dp = 56.dp,
) {
    val supported = key in c.supportedKeys
    RemoteKey(text ?: if (icon == null) key.label else "", icon, modifier, accent = accent && supported, enabled = supported,
        height = height, haptics = haptics,
        contentDescription = if (supported) key.label else "${key.label}, not available with this TV connection",
        onClick = { graph.tv.send(key) })
}

@Composable
private fun VoiceButton(c: TvConnection, modifier: Modifier, haptics: Boolean, onSend: () -> Unit, onDictate: () -> Unit) {
    val enabled = c.supportsText || TvKey.VOICE in c.supportedKeys
    RemoteKey("", Icons.Rounded.Mic, modifier, enabled = enabled, height = 56.dp, haptics = haptics, contentDescription = "Voice search",
        onClick = { if (c.supportsText) onDictate() else onSend() })
}

@Composable
private fun CodeEntry(onSubmit: (String) -> Unit) {
    var code by remember { mutableStateOf("") }
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        OutlinedTextField(code, { v -> code = v.uppercase().filter { it in "0123456789ABCDEF" }.take(6) }, Modifier.weight(1f),
            singleLine = true, placeholder = { Text("6-character code") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii))
        PrimaryButton("Pair", enabled = code.length == 6) { onSubmit(code) }
    }
}

private fun stateText(s: TvConnState) = when (s) {
    TvConnState.Connected -> "connected"
    TvConnState.Connecting -> "connecting…"
    is TvConnState.NeedsUser -> "waiting for you"
    is TvConnState.Failed -> "not connected"
    TvConnState.Disconnected -> "disconnected"
}

private fun stateColor(s: TvConnState) = when (s) {
    TvConnState.Connected -> Palette.Positive
    TvConnState.Connecting, is TvConnState.NeedsUser -> Palette.Warning
    is TvConnState.Failed -> Palette.Negative
    TvConnState.Disconnected -> Palette.TextTertiary
}

// ---------------------------------------------------------------------- device setup

@Composable
fun TvDevicesScreen(graph: AppGraph, onBack: () -> Unit) {
    val context = LocalContext.current
    val tvs by graph.tvRepository.tvs.collectAsStateWithLifecycle()
    val selectedId by graph.tvRepository.selectedId.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()
    var protocol by rememberSaveable { mutableStateOf(TvProtocol.ANDROID_TV) }
    var scanning by remember { mutableStateOf(false) }
    var found by remember { mutableStateOf<List<TvDiscovery.Found>>(emptyList()) }
    var searched by remember { mutableStateOf(false) }
    var manualIp by remember { mutableStateOf("") }
    var irSet by rememberSaveable { mutableStateOf(IrCodeSet.SAMSUNG) }
    val hasIr = remember { IrRemote.hasIrBlaster(context) }

    fun add(tv: SavedTv) {
        graph.tvRepository.save(tv)
        graph.tv.connect(tv)
        onBack()
    }

    ScreenScaffold("TVs", onBack) {
        if (tvs.isNotEmpty()) {
            SectionLabel("Saved TVs")
            Panel {
                tvs.forEachIndexed { i, tv ->
                    if (i > 0) Divider()
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        IconBadge(Icons.Rounded.Tv, tint = if (tv.id == selectedId) Palette.Accent else Palette.TextSecondary)
                        Column(Modifier.weight(1f)) {
                            Text(tv.name, style = MaterialTheme.typography.titleMedium, maxLines = 1)
                            Text(listOfNotNull(tv.protocol.label, tv.host, tv.irCodeSet).joinToString(" · "),
                                style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary, maxLines = 1)
                        }
                        if (tv.id != selectedId) SecondaryButton("Use") { graph.tv.connect(tv); onBack() }
                        TextButton(onClick = { if (tv.id == selectedId) graph.tv.disconnect(); graph.tvRepository.remove(tv.id) }) {
                            Text("Forget", color = Palette.TextSecondary)
                        }
                    }
                }
            }
        }

        SectionLabel("Add a TV")
        Panel {
            SettingChoice("TV type", TvProtocol.entries.toList(), protocol, { it.label }) { protocol = it; found = emptyList() }
            Text(protocol.brandHint, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        }

        when (protocol) {
            TvProtocol.INFRARED -> Panel {
                if (!hasIr) Text("This phone has no infrared blaster. Choose a Wi-Fi or Bluetooth connection instead.",
                    style = MaterialTheme.typography.bodyMedium, color = Palette.Negative)
                SettingChoice("TV brand codes", IrCodeSet.entries.toList(), irSet, { it.label }) { irSet = it }
                PrimaryButton("Add infrared remote", Modifier.fillMaxWidth(), enabled = hasIr) {
                    add(SavedTv(UUID.randomUUID().toString(), "${irSet.label} TV (IR)", TvProtocol.INFRARED, irCodeSet = irSet.name))
                }
            }
            TvProtocol.BLUETOOTH_HID -> Panel {
                Text("1. Select Bluetooth as the connection (Connection screen) and wait for \"Ready\".", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                Text("2. On the TV open Settings → Remotes & Accessories → Add accessory (Android TV / Google TV), or its Bluetooth device list, and pick this phone.",
                    style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                Text("3. The phone then acts as the TV's keyboard and media remote.", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                PrimaryButton("Add Bluetooth remote", Modifier.fillMaxWidth()) {
                    add(SavedTv(UUID.randomUUID().toString(), "TV (Bluetooth)", TvProtocol.BLUETOOTH_HID))
                }
            }
            else -> {
                Panel {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(when {
                            scanning -> "Searching the network…"
                            !searched -> "Search your Wi-Fi for this TV."
                            found.none { it.protocol == protocol } -> "No ${protocol.label.substringBefore(" (")} found. Is it on and on this Wi-Fi?"
                            else -> "${found.count { it.protocol == protocol }} found"
                        },
                            style = MaterialTheme.typography.bodyMedium, color = Palette.TextSecondary, modifier = Modifier.weight(1f))
                        if (scanning) CircularProgressIndicator(Modifier.size(20.dp), color = Palette.Accent, strokeWidth = 2.dp)
                        else SecondaryButton("Search") {
                            scanning = true
                            scope.launch { found = graph.tvDiscovery.scan(); scanning = false; searched = true }
                        }
                    }
                    found.filter { it.protocol == protocol }.forEach { f ->
                        Divider()
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            IconBadge(Icons.Rounded.Tv, tint = Palette.Accent)
                            Column(Modifier.weight(1f)) {
                                Text(f.name, style = MaterialTheme.typography.titleMedium, maxLines = 1)
                                Text(f.host, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                            }
                            SecondaryButton("Connect") { add(SavedTv(UUID.randomUUID().toString(), f.name, protocol, host = f.host)) }
                        }
                    }
                    val others = found.filter { it.protocol != protocol }
                    if (others.isNotEmpty()) Text("Also found: " + others.joinToString { "${it.name} (${it.protocol.label})" },
                        style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                    Divider()
                    Text("Not listed? Enter the TV's IP address (TV Settings → Network → Status).", style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        OutlinedTextField(manualIp, { manualIp = it.trim() }, Modifier.weight(1f), singleLine = true,
                            placeholder = { Text("192.168.1.50") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
                        SecondaryButton("Add", enabled = manualIp.isNotBlank()) {
                            add(SavedTv(UUID.randomUUID().toString(), protocol.label.substringBefore(" ("), protocol, host = manualIp))
                        }
                    }
                }
                Panel {
                    Text(when (protocol) {
                        TvProtocol.ANDROID_TV -> "The TV shows a 6-character code the first time; type it on the phone. Uses the same protocol as Google's TV remote."
                        TvProtocol.SAMSUNG_TIZEN -> "The TV asks to allow \"Air Pointer\" the first time. The token is saved for next time."
                        else -> "The TV asks to accept \"Air Pointer\" the first time. The key is saved for next time."
                    }, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                }
            }
        }
    }
}
