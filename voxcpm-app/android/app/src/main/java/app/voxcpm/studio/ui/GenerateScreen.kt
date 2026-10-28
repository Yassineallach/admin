package app.voxcpm.studio.ui

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AudioFile
import androidx.compose.material.icons.filled.BookmarkAdd
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.runtime.remember
import app.voxcpm.studio.data.SavedVoice
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import app.voxcpm.studio.MainViewModel
import app.voxcpm.studio.VoiceMode
import kotlin.math.roundToInt

private val voicePresets = listOf(
    "A young woman, gentle and sweet voice",
    "A deep, calm male narrator voice",
    "An energetic young man, excited tone",
    "An elderly man, warm and slow storyteller",
    "A cheerful little girl",
    "A professional news anchor, clear and neutral",
)

private val stylePresets = listOf(
    "slightly faster, cheerful tone",
    "slow and calm",
    "whispering",
    "angry and loud",
    "sad, soft voice",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GenerateScreen(vm: MainViewModel, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var showAdvanced by rememberSaveable { mutableStateOf(false) }

    val pickAudio = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let(vm::setReferenceFromUri)
    }
    val micPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) vm.startRecording() else vm.error = "Microphone permission is needed to record"
    }

    Column(
        modifier
            .verticalScroll(rememberScrollState())
            .imePadding()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("VoxCPM Studio", style = MaterialTheme.typography.headlineSmall)

        val clipCount = vm.pendingTexts().size
        OutlinedTextField(
            value = vm.text,
            onValueChange = { vm.text = it },
            label = { Text(if (vm.batchMode) "Texts to speak — one per line" else "Text to speak") },
            placeholder = {
                Text(
                    if (vm.batchMode) "Hello and welcome.\nToday we talk about the weather.\nThanks for listening!"
                    else "Type in any of 30 languages — no language tag needed",
                )
            },
            supportingText = {
                Text(if (vm.batchMode) "$clipCount clips" else "${vm.text.length} characters")
            },
            modifier = Modifier.fillMaxWidth().heightIn(min = 140.dp),
        )
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Multiple texts", style = MaterialTheme.typography.titleSmall)
                Text(
                    "Each line becomes its own clip, all with the same voice settings.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            Switch(checked = vm.batchMode, onCheckedChange = { vm.batchMode = it }, enabled = !vm.isGenerating)
        }

        SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
            VoiceMode.entries.forEachIndexed { i, m ->
                SegmentedButton(
                    selected = vm.mode == m,
                    onClick = { vm.mode = m },
                    shape = SegmentedButtonDefaults.itemShape(i, VoiceMode.entries.size),
                ) { Text(m.label, maxLines = 1) }
            }
        }

        when (vm.mode) {
            VoiceMode.Default -> Text(
                "VoxCPM2 picks a natural voice that fits the text.",
                style = MaterialTheme.typography.bodySmall,
            )
            VoiceMode.Design -> {
                OutlinedTextField(
                    value = vm.voiceDescription,
                    onValueChange = { vm.voiceDescription = it },
                    label = { Text("Describe the voice") },
                    placeholder = { Text("e.g. A young woman, gentle and sweet voice") },
                    modifier = Modifier.fillMaxWidth(),
                )
                PresetRow(voicePresets) { vm.voiceDescription = it }
                Text(
                    "Voice design can vary between runs — try a couple of seeds.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            VoiceMode.Clone -> {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        MyVoices(vm)
                        HorizontalDivider()
                        Text("New voice", style = MaterialTheme.typography.titleSmall)
                        if (vm.referenceName != null && vm.selectedVoiceId == null) {
                            var naming by rememberSaveable { mutableStateOf(false) }
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(Icons.Default.AudioFile, null)
                                Spacer(Modifier.width(8.dp))
                                Text(vm.referenceName!!, Modifier.weight(1f), maxLines = 1)
                                IconButton(onClick = vm::clearReference) { Icon(Icons.Default.Close, "Remove") }
                            }
                            FilledTonalButton(onClick = { naming = true }) {
                                Icon(Icons.Default.BookmarkAdd, null); Spacer(Modifier.width(6.dp)); Text("Save to My voices")
                            }
                            if (naming) {
                                NameDialog(
                                    title = "Save voice",
                                    initial = "",
                                    confirmLabel = "Save",
                                    note = "The transcript below is saved with the voice.",
                                    onDismiss = { naming = false },
                                    onConfirm = { naming = false; vm.saveCurrentVoice(it) },
                                )
                            }
                        } else {
                            Text(
                                "Pick or record a clean 5–20 second clip, then save it to reuse it any time.",
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { pickAudio.launch(arrayOf("audio/*")) }, enabled = !vm.isRecording) {
                                Icon(Icons.Default.AudioFile, null); Spacer(Modifier.width(6.dp)); Text("Pick file")
                            }
                            if (vm.isRecording) {
                                FilledTonalButton(onClick = vm::stopRecording) {
                                    Icon(Icons.Default.Stop, null); Spacer(Modifier.width(6.dp)); Text("Stop")
                                }
                            } else {
                                OutlinedButton(onClick = {
                                    val granted = ContextCompat.checkSelfPermission(
                                        context, Manifest.permission.RECORD_AUDIO,
                                    ) == PackageManager.PERMISSION_GRANTED
                                    if (granted) vm.startRecording() else micPermission.launch(Manifest.permission.RECORD_AUDIO)
                                }) {
                                    Icon(Icons.Default.Mic, null); Spacer(Modifier.width(6.dp)); Text("Record")
                                }
                            }
                        }
                        if (vm.isRecording) Text("Recording… speak clearly, then press Stop.", color = MaterialTheme.colorScheme.error)
                    }
                }
                OutlinedTextField(
                    value = vm.promptText,
                    onValueChange = { vm.promptText = it; vm.updateSelectedVoiceTranscript() },
                    label = { Text("Transcript of the reference (optional)") },
                    supportingText = { Text("Adding the exact words spoken in the clip gives the closest match.") },
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = vm.styleControl,
                    onValueChange = { vm.styleControl = it },
                    label = { Text("Style control (optional)") },
                    placeholder = { Text("e.g. slightly faster, cheerful tone") },
                    modifier = Modifier.fillMaxWidth(),
                )
                PresetRow(stylePresets) { vm.styleControl = it }
            }
        }

        TextButton(onClick = { showAdvanced = !showAdvanced }) {
            Text(if (showAdvanced) "Hide advanced settings" else "Advanced settings")
        }
        if (showAdvanced) {
            Text("Guidance (CFG): %.1f".format(vm.cfgValue))
            Slider(
                value = vm.cfgValue,
                onValueChange = { vm.cfgValue = (it * 10).roundToInt() / 10f },
                valueRange = 1f..3f, steps = 19,
            )
            Text("Inference steps: ${vm.timesteps} (more = higher quality, slower)")
            Slider(
                value = vm.timesteps.toFloat(),
                onValueChange = { vm.timesteps = it.roundToInt() },
                valueRange = 4f..30f, steps = 25,
            )
            OutlinedTextField(
                value = vm.seedText,
                onValueChange = { v -> vm.seedText = v.filter { it.isDigit() }.take(9) },
                label = { Text("Seed (empty = random)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        if (vm.batchMode && clipCount > 1 && vm.mode != VoiceMode.Clone) {
            Text(
                "Tip: for the exact same voice in every clip, use Voice clone with a reference recording.",
                style = MaterialTheme.typography.bodySmall,
            )
        }

        val pending = vm.pendingBatch
        if (pending != null && !vm.isGenerating) {
            ResumeCard(
                done = pending.nextIndex,
                total = pending.texts.size,
                nextText = pending.texts[pending.nextIndex],
                voice = listOf(pending.mode, pending.control).filter { it.isNotBlank() }.joinToString(" · "),
                onResume = vm::resume,
                onDiscard = vm::discardPending,
            )
        }

        if (vm.isGenerating) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.width(12.dp))
                    Text(vm.progressText.ifEmpty { "Generating…" }, Modifier.weight(1f))
                    OutlinedButton(onClick = vm::cancelGeneration) { Text("Stop") }
                }
                val fraction = vm.progressFraction
                if (fraction != null) {
                    LinearProgressIndicator(progress = { fraction }, modifier = Modifier.fillMaxWidth())
                } else {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                }
            }
        } else {
            Button(
                onClick = vm::generate,
                enabled = !vm.isRecording,
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) {
                Text(if (vm.batchMode && clipCount > 1) "Generate $clipCount clips" else "Generate speech")
            }
        }

        vm.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (!vm.isGenerating) vm.status?.let { Text(it, style = MaterialTheme.typography.bodySmall) }

        if (vm.lastBatch.size > 1) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilledTonalButton(onClick = { vm.playAll(vm.lastBatch.toList()) }) {
                    Icon(Icons.Default.PlayArrow, null); Spacer(Modifier.width(6.dp)); Text("Play all")
                }
                DownloadAllButton(vm) { vm.lastBatch.toList() }
            }
        }
        vm.lastBatch.forEach { item ->
            key(item.id) { HistoryCard(item, vm, onReuse = null) }
        }
    }
}

@Composable
private fun PresetRow(presets: List<String>, onPick: (String) -> Unit) {
    Row(
        Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        presets.forEach { AssistChip(onClick = { onPick(it) }, label = { Text(it) }) }
    }
}

@Composable
private fun ResumeCard(
    done: Int,
    total: Int,
    nextText: String,
    voice: String,
    onResume: () -> Unit,
    onDiscard: () -> Unit,
) {
    Card(
        Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
    ) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Generation was interrupted", style = MaterialTheme.typography.titleSmall)
            Text(
                if (total > 1) "$done of $total clips done · ${total - done} left" else "The clip wasn't finished",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text("Next: “$nextText”", style = MaterialTheme.typography.bodySmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
            if (voice.isNotBlank()) Text("Voice: $voice", style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onResume) {
                    Icon(Icons.Default.PlayArrow, null); Spacer(Modifier.width(6.dp)); Text("Resume")
                }
                TextButton(onClick = onDiscard) { Text("Discard") }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun MyVoices(vm: MainViewModel) {
    var renaming by remember { mutableStateOf<SavedVoice?>(null) }
    var deleting by remember { mutableStateOf<SavedVoice?>(null) }

    Text("My voices", style = MaterialTheme.typography.titleSmall)
    if (vm.voices.isEmpty()) {
        Text("No saved voices yet.", style = MaterialTheme.typography.bodySmall)
        return
    }
    Row(
        Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        vm.voices.forEach { voice ->
            val selected = vm.selectedVoiceId == voice.id
            FilterChip(
                selected = selected,
                onClick = { if (selected) vm.clearReference() else vm.selectVoice(voice) },
                label = { Text(voice.name) },
                leadingIcon = if (selected) {
                    { Icon(Icons.Default.Check, null, Modifier.size(18.dp)) }
                } else null,
            )
        }
    }
    vm.voices.firstOrNull { it.id == vm.selectedVoiceId }?.let { voice ->
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Using “${voice.name}”", Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium, maxLines = 1)
            val previewing = vm.playingId == vm.voicePlayId(voice)
            IconButton(onClick = { vm.toggleVoicePreview(voice) }) {
                Icon(if (previewing) Icons.Default.Stop else Icons.Default.PlayArrow, "Listen")
            }
            IconButton(onClick = { renaming = voice }) { Icon(Icons.Default.Edit, "Rename") }
            IconButton(onClick = { deleting = voice }) { Icon(Icons.Default.Delete, "Delete voice") }
        }
    }

    renaming?.let { voice ->
        NameDialog(
            title = "Rename voice",
            initial = voice.name,
            confirmLabel = "Rename",
            onDismiss = { renaming = null },
            onConfirm = { renaming = null; vm.renameVoice(voice, it) },
        )
    }
    deleting?.let { voice ->
        AlertDialog(
            onDismissRequest = { deleting = null },
            title = { Text("Delete “${voice.name}”?") },
            text = { Text("Clips already made with this voice are kept.") },
            confirmButton = { TextButton(onClick = { deleting = null; vm.deleteVoice(voice) }) { Text("Delete") } },
            dismissButton = { TextButton(onClick = { deleting = null }) { Text("Cancel") } },
        )
    }
}

@Composable
private fun NameDialog(
    title: String,
    initial: String,
    confirmLabel: String,
    note: String? = null,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    var name by remember { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it.take(40) },
                    label = { Text("Name") },
                    placeholder = { Text("e.g. My voice, Grandpa, Narrator") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                note?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
            }
        },
        confirmButton = { TextButton(onClick = { onConfirm(name) }) { Text(confirmLabel) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
