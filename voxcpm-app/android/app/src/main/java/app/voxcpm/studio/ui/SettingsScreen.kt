package app.voxcpm.studio.ui

import android.widget.Toast
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.OpenInBrowser
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import app.voxcpm.studio.MainViewModel

private const val REPO_PATH = "yassineallach/admin/blob/claude/android-voxcpm-voice-app-8pkl1u/voxcpm-app/server"
private const val NOTEBOOK_BASE =
    "https://raw.githubusercontent.com/yassineallach/admin/claude/android-voxcpm-voice-app-8pkl1u/voxcpm-app/server"
private const val KAGGLE_NEW_NOTEBOOK_URL = "https://www.kaggle.com/code/new"

/** Notebooks with MODEL preset, written by server/make_notebooks.py. */
private fun colabUrl(model: String) = "https://colab.research.google.com/github/$REPO_PATH/notebooks/Colab_$model.ipynb"
private fun kaggleUrl(model: String) =
    "https://www.kaggle.com/kernels/welcome?src=https://github.com/$REPO_PATH/notebooks/Kaggle_$model.ipynb"

/** Models the notebooks can start, with what each is good at. */
private val serverModels = linkedMapOf(
    "VoxCPM2" to "Default voice, voice design and cloning, 30 languages.",
    "IndexTTS-2.5" to "Cloning with 8 emotions; English, Chinese, Japanese, Spanish, Arabic.",
    "OmniVoice" to "Default voice, voice design and cloning, 600+ languages. Smallest download.",
    "Chatterbox" to "Built-in voice and cloning in 23 languages, expressiveness control.",
    "Chatterbox-Turbo" to "Fast, English only, sound tags like [laugh].",
)

/**
 * Fallback for when Kaggle doesn't open a notebook from GitHub: the one cell to paste into an empty
 * notebook. It fetches the latest server notebook
 * and runs its install, start and tunnel cells with [model].
 */
private fun starterCell(model: String, notebook: String) = """
    |MODEL = "$model"
    |API_KEY = ""
    |import json, urllib.request
    |nb = json.load(urllib.request.urlopen("$NOTEBOOK_BASE/$notebook"))
    |for cell in nb["cells"][2:5]:  # install, start the server, open the tunnel
    |    result = get_ipython().run_cell("".join(cell["source"]))
    |    if not result.success:
    |        raise SystemExit("Stopped: see the error above.")
""".trimMargin()

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ServerLaunchCard(vm: MainViewModel) {
    val uriHandler = LocalUriHandler.current
    val clipboard = LocalClipboardManager.current
    val context = LocalContext.current
    // Start from the model the server ran last time.
    var model by rememberSaveable {
        mutableStateOf(vm.serverInfo.displayName.takeIf { it in serverModels } ?: "VoxCPM2")
    }

    fun open(url: String) {
        try {
            uriHandler.openUri(url)
        } catch (e: Exception) {
            Toast.makeText(context, "No browser found to open $url", Toast.LENGTH_LONG).show()
        }
    }

    fun copyCell(site: String, notebook: String) {
        clipboard.setText(AnnotatedString(starterCell(model, notebook)))
        Toast.makeText(context, "$site cell for $model copied — paste it into the new notebook", Toast.LENGTH_LONG).show()
    }

    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Start a free server", style = MaterialTheme.typography.titleSmall)

            Text("1. Choose the model", style = MaterialTheme.typography.labelLarge)
            Row(
                Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                serverModels.keys.forEach { m ->
                    FilterChip(selected = model == m, onClick = { model = m }, label = { Text(m) })
                }
            }
            Text(serverModels.getValue(model), style = MaterialTheme.typography.bodySmall)
            Text(
                "A running server keeps its model: to switch, start a new one.",
                style = MaterialTheme.typography.bodySmall,
            )

            Text("2. Open a notebook with $model ready", style = MaterialTheme.typography.labelLarge)
            Button(
                onClick = { open(colabUrl(model)) },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF9AB00), contentColor = Color.Black),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.OpenInBrowser, null); Spacer(Modifier.width(8.dp)); Text("Open in Google Colab")
            }
            Text(
                "In Colab: Runtime → Change runtime type → T4 GPU, then Runtime → Run all.",
                style = MaterialTheme.typography.bodySmall,
            )
            Button(
                onClick = { open(kaggleUrl(model)) },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF20BEFF), contentColor = Color.Black),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.OpenInBrowser, null); Spacer(Modifier.width(8.dp)); Text("Open in Kaggle")
            }
            Text(
                "In Kaggle (about 30 free GPU hours a week): under Session options turn on GPU T4 x2 and " +
                    "Internet, then Run All.",
                style = MaterialTheme.typography.bodySmall,
            )
            var showFallback by rememberSaveable { mutableStateOf(false) }
            TextButton(onClick = { showFallback = !showFallback }) {
                Text(if (showFallback) "Hide" else "Kaggle didn't open the notebook?")
            }
            if (showFallback) {
                Text(
                    "Copy a starter cell for $model, open an empty Kaggle notebook, paste it into the cell and Run All.",
                    style = MaterialTheme.typography.bodySmall,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { copyCell("Kaggle", "VoxCPM_Server_Kaggle.ipynb") }, modifier = Modifier.weight(1f)) {
                        Icon(Icons.Default.ContentCopy, null); Spacer(Modifier.width(6.dp)); Text("Copy cell")
                    }
                    OutlinedButton(onClick = { open(KAGGLE_NEW_NOTEBOOK_URL) }, modifier = Modifier.weight(1f)) {
                        Icon(Icons.Default.OpenInBrowser, null); Spacer(Modifier.width(6.dp)); Text("Empty notebook")
                    }
                }
            }
            Text(
                "When it shows \"$model is ready\" and a https://….trycloudflare.com address, copy the address " +
                    "and tap Paste next to Server URL above, then Test connection.",
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
fun SettingsScreen(vm: MainViewModel, modifier: Modifier = Modifier) {
    val clipboard = LocalClipboardManager.current
    Column(
        modifier.verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Server", style = MaterialTheme.typography.headlineSmall)
        Text(
            "The voice models (VoxCPM2, IndexTTS-2.5, OmniVoice, Chatterbox) need a GPU, so the app talks to a server you run " +
                "on a PC or in Google Colab / Kaggle.",
            style = MaterialTheme.typography.bodyMedium,
        )
        OutlinedTextField(
            value = vm.serverUrl,
            onValueChange = { vm.serverUrl = it },
            label = { Text("Server URL") },
            placeholder = { Text("http://192.168.1.20:8000") },
            singleLine = true,
            trailingIcon = {
                TextButton(onClick = {
                    clipboard.getText()?.text?.trim()?.takeIf { it.isNotEmpty() }?.let { vm.serverUrl = it }
                }) { Text("Paste") }
            },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = vm.apiKey,
            onValueChange = { vm.apiKey = it },
            label = { Text("API key (optional)") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = vm::saveSettings) { Text("Save") }
            OutlinedButton(onClick = vm::testConnection) { Text("Test connection") }
        }
        vm.connectionStatus?.let { Text(it) }

        ServerLaunchCard(vm)

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("More about servers", style = MaterialTheme.typography.titleSmall)
                Text(
                    "• Models: the notebooks run VoxCPM2, IndexTTS-2.5, OmniVoice or Chatterbox (pick it in the first cell). The app " +
                        "adapts to whichever one the server runs; tap Test connection after switching.",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "• No GPU left? In Colab keep the runtime type as CPU and run the same notebook. It works " +
                        "but is slow (about 1–3 minutes per sentence): set Inference steps to 4 under Advanced.",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "• Colab limit reached? Kaggle gives about 30 free GPU hours per week (buttons above).",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "• Permanent address: deploy modal_app.py on modal.com (monthly free credits, " +
                        "pay only while generating). The URL never changes.",
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    "• Own PC with an NVIDIA GPU: pip install -r requirements.txt, then " +
                        "python server.py --port 8000. Use http://<PC-IP>:8000 on the same Wi-Fi.",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}
