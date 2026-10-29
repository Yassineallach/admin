package com.opengenerativeai.imagestudio.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import com.opengenerativeai.imagestudio.data.Mode
import com.opengenerativeai.imagestudio.data.ServerLink

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(vm: StudioViewModel, onDone: () -> Unit, modifier: Modifier = Modifier) {
    // Which panel is open; starts on the active backend, but browsing it does not switch.
    var panel by rememberSaveable { mutableStateOf(vm.backend) }

    Column(
        modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text("Where images are made", style = MaterialTheme.typography.headlineSmall)
        SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
            listOf(Backend.SERVER to "My GPU · free", Backend.MUAPI to "MuAPI · paid")
                .forEachIndexed { index, (b, label) ->
                    SegmentedButton(
                        selected = panel == b,
                        onClick = { panel = b },
                        shape = SegmentedButtonDefaults.itemShape(index, 2),
                    ) { Text(label) }
                }
        }
        when (panel) {
            Backend.SERVER -> ServerPanel(vm, onDone)
            Backend.MUAPI -> MuapiPanel(vm, onDone)
        }
    }
}

@Composable
private fun ActiveBadge(text: String) {
    Surface(color = MaterialTheme.colorScheme.primaryContainer, shape = RoundedCornerShape(10.dp)) {
        Row(Modifier.padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Accent, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(text, color = MaterialTheme.colorScheme.onPrimaryContainer, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun ServerPanel(vm: StudioViewModel, onDone: () -> Unit) {
    val context = LocalContext.current
    var address by remember { mutableStateOf(vm.server?.url.orEmpty()) }
    var token by remember { mutableStateOf(vm.server?.token.orEmpty()) }
    var reveal by remember { mutableStateOf(false) }

    fun accept(text: String): Boolean {
        val link = ServerLink.parse(text) ?: return false
        address = link.url
        token = link.token
        return true
    }

    if (vm.backend == Backend.SERVER && vm.server != null) {
        val count = vm.catalog.forMode(Mode.TEXT_TO_IMAGE).size
        ActiveBadge("In use: $count model(s) on ${Uri.parse(vm.server!!.url).host}")
    }
    Text(
        "Run open models such as SDXL Turbo on a free Kaggle or Colab GPU. Open the Image Studio " +
            "notebook (android-image-studio/server/image_studio_server.ipynb), turn on the GPU, choose " +
            "Run all, then scan the QR code it shows.",
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    Button(
        onClick = {
            val options = GmsBarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_QR_CODE).build()
            GmsBarcodeScanning.getClient(context, options).startScan()
                .addOnSuccessListener { code ->
                    if (accept(code.rawValue.orEmpty())) vm.connectServer(address, token)
                    else vm.message = "That QR code is not from the Image Studio notebook."
                }
                .addOnFailureListener { vm.message = "Scanner unavailable: ${it.message}. Paste the link instead." }
        },
        enabled = !vm.connecting,
        modifier = Modifier.fillMaxWidth(),
    ) { Text("Scan QR code") }
    OutlinedTextField(
        value = address,
        // Pasting the notebook's whole imagestudio:// link fills both fields.
        onValueChange = { if (!accept(it)) address = it },
        label = { Text("Server address or connect link") },
        placeholder = { Text("https://….trycloudflare.com") },
        singleLine = true,
        modifier = Modifier.fillMaxWidth(),
    )
    OutlinedTextField(
        value = token,
        onValueChange = { token = it },
        label = { Text("Access token") },
        singleLine = true,
        visualTransformation = if (reveal) VisualTransformation.None else PasswordVisualTransformation(),
        trailingIcon = {
            IconButton(onClick = { reveal = !reveal }) {
                Icon(Icons.Default.Lock, contentDescription = if (reveal) "Hide token" else "Show token")
            }
        },
        modifier = Modifier.fillMaxWidth(),
    )
    OutlinedButton(
        onClick = { vm.connectServer(address, token) },
        enabled = !vm.connecting,
        modifier = Modifier.fillMaxWidth(),
    ) {
        if (vm.connecting) {
            CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
            Spacer(Modifier.width(10.dp))
            Text("Connecting…")
        } else {
            Text("Connect")
        }
    }
    if (vm.backend == Backend.SERVER) {
        OutlinedButton(onClick = onDone, modifier = Modifier.fillMaxWidth()) { Text("Start creating") }
    }
    Text(
        "Each notebook session gets a new address, so scan again whenever you restart it. " +
            "Images you make are copied to this phone, so they outlive the session.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

@Composable
private fun MuapiPanel(vm: StudioViewModel, onDone: () -> Unit) {
    val context = LocalContext.current
    var key by remember { mutableStateOf(vm.apiKey) }
    var reveal by remember { mutableStateOf(false) }

    if (vm.backend == Backend.MUAPI && vm.apiKey.isNotEmpty()) ActiveBadge("In use: MuAPI")
    Text(
        "MuAPI runs 150 models, including Nano Banana, GPT Image, Seedream and Midjourney. Each " +
            "generation is billed to your MuAPI account. Your key is stored only on this device.",
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
            if (key.isBlank()) {
                vm.message = "API key removed"
            } else {
                vm.useMuapi()
                vm.message = "Using MuAPI"
                onDone()
            }
        },
        modifier = Modifier.fillMaxWidth(),
    ) { Text("Save and use MuAPI") }
    OutlinedButton(
        onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://muapi.ai"))) },
        modifier = Modifier.fillMaxWidth(),
    ) { Text("Get a key at muapi.ai") }
}
