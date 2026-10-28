package app.voxcpm.studio.ui

import android.content.Intent
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AudioFile
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.FolderZip
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import app.voxcpm.studio.MainViewModel
import app.voxcpm.studio.data.HistoryItem
import kotlinx.coroutines.launch
import java.text.DateFormat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun HistoryScreen(vm: MainViewModel, modifier: Modifier = Modifier, onReuse: (HistoryItem) -> Unit) {
    if (vm.history.isEmpty()) {
        Box(modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
            Text("Nothing generated yet.", style = MaterialTheme.typography.bodyLarge)
        }
        return
    }
    LazyColumn(
        modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item(key = "header") {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("${vm.history.size} clips", Modifier.weight(1f), style = MaterialTheme.typography.titleMedium)
                // Oldest first, so the numbers follow the order the clips were made in.
                DownloadAllButton(vm) { vm.history.reversed() }
            }
        }
        items(vm.history, key = { it.id }) { HistoryCard(it, vm, onReuse) }
    }
}

/** Saves the clips from [items] as one zip with files named 1.wav, 2.wav, … */
@Composable
fun DownloadAllButton(vm: MainViewModel, items: () -> List<HistoryItem>) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var zipping by remember { mutableStateOf(false) }
    var toExport by remember { mutableStateOf<List<HistoryItem>>(emptyList()) }
    // (audio, texts) for the zip being saved
    var contents by remember { mutableStateOf(true to false) }
    var menuOpen by remember { mutableStateOf(false) }
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/zip")) { uri ->
        val clips = toExport
        if (uri != null && clips.isNotEmpty()) {
            zipping = true
            scope.launch {
                val message = vm.exportZip(clips, uri, audio = contents.first, texts = contents.second)
                zipping = false
                Toast.makeText(context, message, Toast.LENGTH_LONG).show()
            }
        }
    }
    fun export(audio: Boolean, texts: Boolean, name: String) {
        menuOpen = false
        contents = audio to texts
        toExport = items()
        val stamp = SimpleDateFormat("yyyyMMdd_HHmm", Locale.US).format(Date())
        launcher.launch("voxcpm_${name}_$stamp.zip")
    }
    Box {
        OutlinedButton(onClick = { menuOpen = true }, enabled = !zipping) {
            Icon(Icons.Default.FolderZip, null)
            Spacer(Modifier.width(6.dp))
            Text(if (zipping) "Zipping…" else "Download all (ZIP)")
        }
        DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
            DropdownMenuItem(
                text = { Text("Audio only (1.wav, 2.wav…)") },
                leadingIcon = { Icon(Icons.Default.AudioFile, null) },
                onClick = { export(audio = true, texts = false, name = "clips") },
            )
            DropdownMenuItem(
                text = { Text("Texts only (1.txt, 2.txt…)") },
                leadingIcon = { Icon(Icons.Default.Description, null) },
                onClick = { export(audio = false, texts = true, name = "texts") },
            )
            DropdownMenuItem(
                text = { Text("Audio + texts") },
                leadingIcon = { Icon(Icons.Default.FolderZip, null) },
                onClick = { export(audio = true, texts = true, name = "clips_texts") },
            )
        }
    }
}

@Composable
fun HistoryCard(item: HistoryItem, vm: MainViewModel, onReuse: ((HistoryItem) -> Unit)?) {
    val context = LocalContext.current
    var pendingExport by remember { mutableStateOf<HistoryItem?>(null) }
    val exportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("audio/wav")) { uri ->
        val target = pendingExport
        if (uri != null && target != null) vm.exportTo(target, uri)
        pendingExport = null
    }

    var editing by remember { mutableStateOf(false) }
    if (editing) {
        RegenerateDialog(
            item = item,
            onDismiss = { editing = false },
            onConfirm = { text, newSeed ->
                editing = false
                vm.regenerate(item, text, newSeed)
            },
        )
    }
    val regenerating = vm.regeneratingId == item.id

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            Text(item.text, maxLines = 3, overflow = TextOverflow.Ellipsis)
            val meta = buildList {
                add(item.mode)
                if (item.control.isNotBlank()) add("“${item.control}”")
                item.durationSec?.let { add("%.1fs".format(it)) }
                item.seed?.let { add("seed $it") }
                add(DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(item.createdAt)))
            }.joinToString(" · ")
            Text(meta, style = MaterialTheme.typography.bodySmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
            if (regenerating) {
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(vm.progressText.ifEmpty { "Regenerating…" }, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
                    TextButton(onClick = vm::cancelGeneration) { Text("Stop") }
                }
                val fraction = vm.progressFraction
                if (fraction != null) {
                    LinearProgressIndicator(progress = { fraction }, modifier = Modifier.fillMaxWidth())
                } else {
                    LinearProgressIndicator(Modifier.fillMaxWidth())
                }
            }
            vm.regenerateResult?.takeIf { it.first == item.id && !regenerating }?.let { (_, message, failed) ->
                Text(
                    message,
                    style = MaterialTheme.typography.bodySmall,
                    color = if (failed) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                )
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                val playing = vm.playingId == item.id
                IconButton(onClick = { vm.togglePlay(item) }) {
                    Icon(if (playing) Icons.Default.Stop else Icons.Default.PlayArrow, if (playing) "Stop" else "Play")
                }
                IconButton(onClick = {
                    pendingExport = item
                    exportLauncher.launch("voxcpm_${item.id.take(8)}.wav")
                }) { Icon(Icons.Default.Download, "Save to device") }
                IconButton(onClick = {
                    val uri = FileProvider.getUriForFile(
                        context, "${context.packageName}.files", item.file(vm.historyDir),
                    )
                    val send = Intent(Intent.ACTION_SEND)
                        .setType("audio/wav")
                        .putExtra(Intent.EXTRA_STREAM, uri)
                        .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    context.startActivity(Intent.createChooser(send, "Share audio"))
                }) { Icon(Icons.Default.Share, "Share") }
                IconButton(onClick = { editing = true }, enabled = !vm.isGenerating) {
                    Icon(Icons.Default.Refresh, "Edit text and regenerate")
                }
                if (onReuse != null) {
                    IconButton(onClick = { onReuse(item) }) { Icon(Icons.Default.ContentCopy, "Reuse settings") }
                }
                IconButton(onClick = { vm.delete(item) }, enabled = !regenerating) { Icon(Icons.Default.Delete, "Delete") }
            }
        }
    }
}

@Composable
private fun RegenerateDialog(item: HistoryItem, onDismiss: () -> Unit, onConfirm: (String, Boolean) -> Unit) {
    var text by remember { mutableStateOf(item.text) }
    var newSeed by remember { mutableStateOf(true) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Regenerate clip") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                OutlinedTextField(
                    value = text,
                    onValueChange = { text = it },
                    label = { Text("Text") },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 120.dp),
                )
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = newSeed, onCheckedChange = { newSeed = it })
                    Text("New random take (different seed)", style = MaterialTheme.typography.bodyMedium)
                }
                Text(
                    "Uses the same voice settings as before. The new audio replaces this clip.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { onConfirm(text, newSeed) }, enabled = text.isNotBlank()) { Text("Regenerate") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
