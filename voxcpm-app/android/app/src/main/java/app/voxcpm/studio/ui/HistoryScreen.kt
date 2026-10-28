package app.voxcpm.studio.ui

import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import app.voxcpm.studio.MainViewModel
import app.voxcpm.studio.data.HistoryItem
import java.text.DateFormat
import java.util.Date

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
        items(vm.history, key = { it.id }) { HistoryCard(it, vm, onReuse) }
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
                if (onReuse != null) {
                    IconButton(onClick = { onReuse(item) }) { Icon(Icons.Default.Edit, "Reuse settings") }
                }
                IconButton(onClick = { vm.delete(item) }) { Icon(Icons.Default.Delete, "Delete") }
            }
        }
    }
}
