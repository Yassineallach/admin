@file:OptIn(ExperimentalMaterial3Api::class)

package com.opengenerativeai.imagestudio.ui

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.opengenerativeai.imagestudio.data.Generation
import com.opengenerativeai.imagestudio.data.JobStatus
import com.opengenerativeai.imagestudio.data.Mode

@Composable
fun CreateScreen(vm: StudioViewModel, onOpenImage: (String) -> Unit, modifier: Modifier = Modifier) {
    var pickingModel by remember { mutableStateOf(false) }
    val model = vm.model
    val current = vm.history.firstOrNull { it.id == vm.currentId }

    Column(
        modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
            listOf(Mode.TEXT_TO_IMAGE to "Text → Image", Mode.IMAGE_TO_IMAGE to "Image → Image")
                .forEachIndexed { index, (m, label) ->
                    SegmentedButton(
                        selected = vm.mode == m,
                        onClick = { vm.selectMode(m) },
                        shape = SegmentedButtonDefaults.itemShape(index, 2),
                    ) { Text(label) }
                }
        }

        ResultPanel(current, vm.stage, onOpenImage, onClear = vm::clearCurrent)

        Surface(
            onClick = { pickingModel = true },
            shape = RoundedCornerShape(14.dp),
            color = MaterialTheme.colorScheme.surfaceContainer,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Model", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(model.name, style = MaterialTheme.typography.titleMedium)
                    if (model.provider.isNotEmpty()) {
                        Text(model.provider, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                Icon(Icons.Default.ArrowDropDown, contentDescription = "Change model")
            }
        }

        if (model.mode == Mode.IMAGE_TO_IMAGE) ReferencePicker(vm)

        if (model.hasPrompt) {
            OutlinedTextField(
                value = vm.prompt,
                onValueChange = { vm.prompt = it },
                label = { Text(if (model.mode == Mode.IMAGE_TO_IMAGE) "Describe the edit" else "Prompt") },
                placeholder = { Text("A neon-lit street market in the rain, cinematic…") },
                minLines = 3,
                maxLines = 8,
                modifier = Modifier.fillMaxWidth(),
            )
        }

        if (model.params.isNotEmpty()) {
            ParamControls(model.params, vm.paramValues, vm::setParam)
        }

        Button(
            onClick = vm::generate,
            enabled = current?.status != JobStatus.PENDING,
            modifier = Modifier.fillMaxWidth().height(52.dp),
            shape = RoundedCornerShape(14.dp),
        ) {
            Icon(Icons.Default.Star, contentDescription = null)
            Spacer(Modifier.width(8.dp))
            Text("Generate", style = MaterialTheme.typography.titleMedium)
        }
        Spacer(Modifier.height(8.dp))
    }

    if (pickingModel) {
        ModelPickerSheet(
            models = vm.catalog.forMode(vm.mode),
            selectedId = model.id,
            onPick = { vm.selectModel(it); pickingModel = false },
            onDismiss = { pickingModel = false },
        )
    }
}

@Composable
private fun ResultPanel(
    generation: Generation?,
    stage: String?,
    onOpenImage: (String) -> Unit,
    onClear: () -> Unit,
) {
    val shape = RoundedCornerShape(18.dp)
    Box(
        Modifier
            .fillMaxWidth()
            .aspectRatio(1f)
            .clip(shape)
            .background(MaterialTheme.colorScheme.surfaceContainer)
            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, shape),
        contentAlignment = Alignment.Center,
    ) {
        when (generation?.status) {
            null -> Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(24.dp)) {
                Text("What will you create?", style = MaterialTheme.typography.headlineSmall)
                Spacer(Modifier.height(6.dp))
                Text(
                    "Pick a model, describe an image and tap Generate.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
            }
            JobStatus.PENDING -> Column(horizontalAlignment = Alignment.CenterHorizontally) {
                CircularProgressIndicator()
                Spacer(Modifier.height(14.dp))
                Text(stage ?: "Generating…", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            JobStatus.FAILED -> Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(24.dp)) {
                Icon(Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                Spacer(Modifier.height(8.dp))
                Text(generation.error ?: "Generation failed", textAlign = TextAlign.Center)
                TextButton(onClick = onClear) { Text("Dismiss") }
            }
            JobStatus.SUCCEEDED -> {
                val outputs = generation.outputs
                if (outputs.size == 1) {
                    AsyncImage(
                        model = outputs.first(),
                        contentDescription = generation.prompt,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxSize().clickable { onOpenImage(outputs.first()) },
                    )
                } else {
                    LazyRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxSize().padding(8.dp),
                    ) {
                        items(outputs) { url ->
                            AsyncImage(
                                model = url,
                                contentDescription = generation.prompt,
                                contentScale = ContentScale.Crop,
                                modifier = Modifier
                                    .fillMaxHeight()
                                    .aspectRatio(0.8f)
                                    .clip(RoundedCornerShape(12.dp))
                                    .clickable { onOpenImage(url) },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReferencePicker(vm: StudioViewModel) {
    val max = vm.model.maxImages
    val single = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        uri?.let { vm.addReferences(listOf(it)) }
    }
    // PickMultipleVisualMedia requires a limit of at least 2.
    val multiple = rememberLauncherForActivityResult(
        ActivityResultContracts.PickMultipleVisualMedia(maxOf(2, max)),
    ) { uris -> vm.addReferences(uris) }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            if (max > 1) "Reference images (up to $max)" else "Reference image",
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            items(vm.references, key = { it.uri.toString() }) { ref ->
                Box(Modifier.size(88.dp)) {
                    AsyncImage(
                        model = ref.uri,
                        contentDescription = null,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(12.dp)),
                    )
                    Box(
                        Modifier
                            .align(Alignment.TopEnd)
                            .padding(4.dp)
                            .size(24.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.background.copy(alpha = 0.75f))
                            .clickable { vm.removeReference(ref) },
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Default.Close, contentDescription = "Remove", modifier = Modifier.size(16.dp))
                    }
                }
            }
            if (vm.references.size < max) {
                item {
                    val shape = RoundedCornerShape(12.dp)
                    Box(
                        Modifier
                            .size(88.dp)
                            .clip(shape)
                            .border(1.dp, MaterialTheme.colorScheme.outline, shape)
                            .clickable {
                                val request = PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                                if (max - vm.references.size > 1) multiple.launch(request) else single.launch(request)
                            },
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Default.Add, contentDescription = "Add image", tint = Accent)
                    }
                }
            }
        }
    }
}
