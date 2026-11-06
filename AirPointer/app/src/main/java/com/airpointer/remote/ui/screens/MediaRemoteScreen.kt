package com.airpointer.remote.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.automirrored.rounded.VolumeDown
import androidx.compose.material.icons.automirrored.rounded.VolumeOff
import androidx.compose.material.icons.automirrored.rounded.VolumeUp
import androidx.compose.material.icons.rounded.FastForward
import androidx.compose.material.icons.rounded.FastRewind
import androidx.compose.material.icons.rounded.Forward10
import androidx.compose.material.icons.rounded.Fullscreen
import androidx.compose.material.icons.rounded.Pause
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.Replay10
import androidx.compose.material.icons.rounded.SkipNext
import androidx.compose.material.icons.rounded.SkipPrevious
import androidx.compose.material.icons.rounded.Stop
import androidx.compose.material.icons.rounded.Subtitles
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.airpointer.remote.AppGraph
import com.airpointer.remote.media.MediaBackend
import com.airpointer.remote.media.MediaCap
import com.airpointer.remote.media.MediaException
import com.airpointer.remote.media.MediaStatus
import com.airpointer.remote.media.MpvBackend
import com.airpointer.remote.media.PlayState
import com.airpointer.remote.media.VlcBackend
import com.airpointer.remote.media.formatTime
import com.airpointer.remote.transport.WifiCompanionClient
import com.airpointer.remote.ui.Route
import com.airpointer.remote.ui.components.Panel
import com.airpointer.remote.ui.components.PrimaryButton
import com.airpointer.remote.ui.components.RemoteKey
import com.airpointer.remote.ui.components.SecondaryButton
import com.airpointer.remote.ui.components.Segmented
import com.airpointer.remote.ui.components.StatusDot
import com.airpointer.remote.ui.theme.Palette
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private val SPEEDS = listOf(0.5, 0.75, 1.0, 1.25, 1.5, 2.0)

@Composable
fun MediaRemoteScreen(graph: AppGraph, onBack: () -> Unit, navigate: (Route) -> Unit) {
    val settings by graph.settings.settings.collectAsStateWithLifecycle()
    val wifi by graph.wifi.state.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()
    val player = settings.mediaPlayer

    val backend: MediaBackend? = remember(player, settings.vlcHost, settings.vlcPort, settings.vlcPassword) {
        when {
            player == "MPV" -> MpvBackend(graph.wifi)
            settings.vlcHost != null -> VlcBackend(settings.vlcHost!!, settings.vlcPort, settings.vlcPassword.orEmpty())
            else -> null
        }
    }
    var status by remember { mutableStateOf<MediaStatus?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var seeking by remember { mutableStateOf<Float?>(null) }
    var editVlc by remember { mutableStateOf(false) }

    LaunchedEffect(backend, wifi.phase) {
        status = null; error = null
        while (backend != null) {
            try { status = backend.status(); error = null } catch (e: MediaException) { error = e.message }
            delay(700)
        }
    }
    fun run(block: suspend MediaBackend.() -> Unit) {
        val b = backend ?: return
        scope.launch {
            try { b.block(); status = b.status(); error = null } catch (e: MediaException) { error = e.message }
        }
    }

    Column(
        Modifier.fillMaxSize().background(Palette.Background).statusBarsPadding().navigationBarsPadding().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(Modifier.fillMaxWidth().height(56.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Rounded.ArrowBack, "Back", tint = Palette.TextPrimary) }
            StatusDot(if (status != null && error == null) Palette.Positive else if (error != null) Palette.Negative else Palette.TextTertiary,
                status != null && error == null, 7.dp)
            Column(Modifier.weight(1f).padding(start = 4.dp)) {
                Text("Media Player", style = MaterialTheme.typography.titleMedium)
                Text(status?.title ?: player, style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary, maxLines = 1)
            }
        }
        Segmented(listOf("VLC", "MPV"), player, { it }) { p -> graph.settings.update { it.copy(mediaPlayer = p) } }

        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (player == "VLC" && (settings.vlcHost == null || editVlc)) VlcSetup(graph) { editVlc = false }
            if (player == "MPV" && wifi.phase != WifiCompanionClient.Phase.CONNECTED) Panel {
                Text("MPV is controlled through the Air Pointer Companion", style = MaterialTheme.typography.titleMedium)
                Text("mpv only accepts remote commands on a local socket, so the companion relays them. Connect it under Connection → Wi-Fi, " +
                    "then start mpv with --input-ipc-server (Windows: \\\\.\\pipe\\mpvsocket, Linux: /tmp/mpvsocket) or add that line to mpv.conf.",
                    style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
                PrimaryButton("Open Connection", Modifier.fillMaxWidth()) { navigate(Route.PAIRING) }
            }
            error?.let { Panel(padding = 14.dp) { Text(it, style = MaterialTheme.typography.bodySmall, color = Palette.Negative) } }

            val s = status ?: MediaStatus()
            val caps = backend?.capabilities.orEmpty()
            val ready = status != null && error == null

            // Timeline
            Panel {
                Text(s.title ?: "Nothing playing", style = MaterialTheme.typography.titleMedium, maxLines = 2)
                val dur = s.durationSec.coerceAtLeast(0.0)
                val pos = seeking?.toDouble() ?: s.positionSec
                Slider(
                    value = if (dur > 0) (pos / dur).toFloat().coerceIn(0f, 1f) else 0f,
                    onValueChange = { if (dur > 0) seeking = (it * dur).toFloat() },
                    onValueChangeFinished = { seeking?.let { t -> run { seekTo(t.toDouble()) } }; seeking = null },
                    enabled = ready && dur > 0 && MediaCap.SEEK in caps,
                    colors = SliderDefaults.colors(thumbColor = Palette.TextPrimary, activeTrackColor = Palette.Accent, inactiveTrackColor = Palette.SurfaceHighest),
                )
                Row {
                    Text(formatTime(pos), style = MaterialTheme.typography.labelMedium.copy(fontFamily = FontFamily.Monospace), color = Palette.TextPrimary)
                    Text("  /  ${formatTime(dur)}", style = MaterialTheme.typography.labelMedium.copy(fontFamily = FontFamily.Monospace),
                        color = Palette.TextSecondary, modifier = Modifier.weight(1f))
                    Text("−${formatTime((dur - pos).coerceAtLeast(0.0))}", style = MaterialTheme.typography.labelMedium.copy(fontFamily = FontFamily.Monospace),
                        color = Palette.TextSecondary)
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                MKey(Icons.Rounded.SkipPrevious, ready && MediaCap.PREV_NEXT in caps, Modifier.weight(1f), settings.haptics) { run { previous() } }
                MKey(Icons.Rounded.FastRewind, ready && MediaCap.SEEK in caps, Modifier.weight(1f), settings.haptics) { run { seekRelative(-30.0) } }
                MKey(if (s.state == PlayState.PLAYING) Icons.Rounded.Pause else Icons.Rounded.PlayArrow, ready, Modifier.weight(1.4f), settings.haptics,
                    accent = true, height = 72.dp) { run { playPause() } }
                MKey(Icons.Rounded.FastForward, ready && MediaCap.SEEK in caps, Modifier.weight(1f), settings.haptics) { run { seekRelative(30.0) } }
                MKey(Icons.Rounded.SkipNext, ready && MediaCap.PREV_NEXT in caps, Modifier.weight(1f), settings.haptics) { run { next() } }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                MKey(Icons.Rounded.Replay10, ready && MediaCap.SEEK in caps, Modifier.weight(1f), settings.haptics) { run { seekRelative(-10.0) } }
                MKey(Icons.Rounded.Stop, ready && MediaCap.STOP in caps, Modifier.weight(1f), settings.haptics) { run { stop() } }
                MKey(Icons.Rounded.Fullscreen, ready && MediaCap.FULLSCREEN in caps, Modifier.weight(1f), settings.haptics, active = s.fullscreen) { run { toggleFullscreen() } }
                MKey(Icons.Rounded.Forward10, ready && MediaCap.SEEK in caps, Modifier.weight(1f), settings.haptics) { run { seekRelative(10.0) } }
            }

            // Volume
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                MKey(Icons.AutoMirrored.Rounded.VolumeDown, ready && MediaCap.VOLUME in caps, Modifier.weight(1f), settings.haptics) { run { changeVolume(-5) } }
                Text(if (s.muted) "Muted" else "${s.volumePercent}%", style = MaterialTheme.typography.titleMedium,
                    color = if (s.muted) Palette.Warning else Palette.TextPrimary, modifier = Modifier.weight(0.8f))
                MKey(Icons.AutoMirrored.Rounded.VolumeOff, ready && MediaCap.MUTE in caps, Modifier.weight(1f), settings.haptics, active = s.muted) { run { toggleMute() } }
                MKey(Icons.AutoMirrored.Rounded.VolumeUp, ready && MediaCap.VOLUME in caps, Modifier.weight(1f), settings.haptics) { run { changeVolume(5) } }
            }

            // Speed
            Panel(padding = 14.dp) {
                Text("Playback speed · ${"%.2f".format(s.speed)}×", style = MaterialTheme.typography.labelSmall, color = Palette.TextTertiary)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    for (sp in SPEEDS) RemoteKey("${sp}×".replace(".0×", "×"), null, Modifier.weight(1f), height = 40.dp,
                        active = kotlin.math.abs(s.speed - sp) < 0.01, enabled = ready && MediaCap.SPEED in caps, haptics = settings.haptics,
                        onClick = { run { setSpeed(sp) } })
                }
            }

            // Subtitles & audio
            Panel(padding = 14.dp) {
                Text("Subtitles · delay ${"%+.1f".format(s.subtitleDelaySec)} s" +
                    (s.subtitlesVisible?.let { if (it) " · on" else " · off" } ?: ""), style = MaterialTheme.typography.labelSmall, color = Palette.TextTertiary)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    MKey(Icons.Rounded.Subtitles, ready && MediaCap.SUBTITLE_TOGGLE in caps, Modifier.weight(1f), settings.haptics) { run { toggleSubtitles() } }
                    RemoteKey("Track", null, Modifier.weight(1f), height = 48.dp, enabled = ready && MediaCap.SUBTITLE_TRACK in caps,
                        haptics = settings.haptics, onClick = { run { cycleSubtitleTrack() } })
                    RemoteKey("−0.1 s", null, Modifier.weight(1f), height = 48.dp, enabled = ready && MediaCap.SUBTITLE_DELAY in caps,
                        haptics = settings.haptics, onClick = { run { shiftSubtitleDelay(-0.1) } })
                    RemoteKey("+0.1 s", null, Modifier.weight(1f), height = 48.dp, enabled = ready && MediaCap.SUBTITLE_DELAY in caps,
                        haptics = settings.haptics, onClick = { run { shiftSubtitleDelay(0.1) } })
                }
                RemoteKey("Next audio track" + (s.audioTrack?.let { " (now $it)" } ?: ""), null, Modifier.fillMaxWidth(), height = 44.dp,
                    enabled = ready && MediaCap.AUDIO_TRACK in caps, haptics = settings.haptics, onClick = { run { cycleAudioTrack() } })
            }
            if (player == "VLC" && settings.vlcHost != null && !editVlc) SecondaryButton("VLC: ${settings.vlcHost}:${settings.vlcPort} — change") { editVlc = true }
        }
    }
}

@Composable
private fun MKey(
    icon: androidx.compose.ui.graphics.vector.ImageVector, enabled: Boolean, modifier: Modifier, haptics: Boolean,
    accent: Boolean = false, active: Boolean = false, height: androidx.compose.ui.unit.Dp = 56.dp, onClick: () -> Unit,
) = RemoteKey("", icon, modifier, accent = accent && enabled, active = active, enabled = enabled, height = height, haptics = haptics, onClick = onClick)

@Composable
private fun VlcSetup(graph: AppGraph, onDone: () -> Unit) {
    val settings = graph.settings.current
    var host by remember { mutableStateOf(settings.vlcHost ?: settings.wifiHost ?: "") }
    var port by remember { mutableStateOf(settings.vlcPort.toString()) }
    var password by remember { mutableStateOf(settings.vlcPassword ?: "") }
    Panel {
        Text("Connect to VLC", style = MaterialTheme.typography.titleMedium)
        Text("In VLC on the PC: Tools → Preferences → Show settings: All → Interface → Main interfaces → tick \"Web\". " +
            "Then Main interfaces → Lua → set a Lua HTTP password. Restart VLC and allow it through the firewall. " +
            "The phone talks to VLC directly; the companion is not needed.",
            style = MaterialTheme.typography.bodySmall, color = Palette.TextSecondary)
        OutlinedTextField(host, { host = it.trim() }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("PC address") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedTextField(port, { v -> port = v.filter { it.isDigit() }.take(5) }, Modifier.weight(0.4f), singleLine = true,
                label = { Text("Port") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number))
            OutlinedTextField(password, { password = it }, Modifier.weight(0.6f), singleLine = true, label = { Text("Lua HTTP password") },
                visualTransformation = PasswordVisualTransformation())
        }
        PrimaryButton("Save", Modifier.fillMaxWidth(), enabled = host.isNotBlank() && password.isNotBlank()) {
            graph.settings.update { it.copy(vlcHost = host, vlcPort = port.toIntOrNull() ?: 8080, vlcPassword = password) }
            onDone()
        }
    }
}
