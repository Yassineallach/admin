package com.opengenerativeai.imagestudio.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp

@Composable
fun SettingsScreen(vm: StudioViewModel, onDone: () -> Unit, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var key by remember { mutableStateOf(vm.apiKey) }
    var reveal by remember { mutableStateOf(false) }

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("MuAPI key", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Image Studio runs every model through muapi.ai, the engine behind Open Generative AI. " +
                "Paste your API key below; it is stored only on this device.",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            value = key,
            onValueChange = { key = it },
            label = { Text("API key") },
            singleLine = true,
            visualTransformation = if (reveal) VisualTransformation.None else PasswordVisualTransformation(),
            trailingIcon = {
                IconButton(onClick = { reveal = !reveal }) {
                    Icon(Icons.Default.Lock, contentDescription = if (reveal) "Hide key" else "Show key")
                }
            },
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = {
                vm.updateApiKey(key)
                vm.message = if (key.isBlank()) "API key removed" else "API key saved"
                if (key.isNotBlank()) onDone()
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Save") }
        OutlinedButton(
            onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://muapi.ai"))) },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Get a key at muapi.ai") }
        Text(
            "${vm.catalog.models.size} image models available. Generations are billed to your MuAPI account.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
