@file:OptIn(ExperimentalMaterial3Api::class)

package com.opengenerativeai.imagestudio.ui

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.clickable
import com.opengenerativeai.imagestudio.data.ImageModel

@Composable
fun ModelPickerSheet(
    models: List<ImageModel>,
    selectedId: String,
    onPick: (ImageModel) -> Unit,
    onDismiss: () -> Unit,
) {
    var query by remember { mutableStateOf("") }
    val filtered = remember(query, models) {
        val q = query.trim()
        if (q.isEmpty()) models
        else models.filter { it.name.contains(q, true) || it.provider.contains(q, true) || it.id.contains(q, true) }
    }
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            placeholder = { Text("Search ${models.size} models") },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        )
        LazyColumn(Modifier.navigationBarsPadding().padding(top = 8.dp)) {
            items(filtered, key = { it.id }) { m ->
                ListItem(
                    headlineContent = { Text(m.name) },
                    supportingContent = {
                        val extra = if (m.maxImages > 1) " · up to ${m.maxImages} images" else ""
                        Text(m.provider + extra, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    },
                    trailingContent = {
                        if (m.id == selectedId) Icon(Icons.Default.Check, contentDescription = "Selected", tint = Accent)
                    },
                    colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
                    modifier = Modifier.clickable { onPick(m) },
                )
            }
        }
    }
}
