package app.voxcpm.studio.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import app.voxcpm.studio.MainViewModel

@Composable
fun SettingsScreen(vm: MainViewModel, modifier: Modifier = Modifier) {
    Column(
        modifier.verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Server", style = MaterialTheme.typography.headlineSmall)
        Text(
            "VoxCPM2 is a 2B-parameter model that needs a GPU (~8 GB VRAM), so the app talks to a " +
                "VoxCPM server you run on a PC or in Google Colab.",
            style = MaterialTheme.typography.bodyMedium,
        )
        OutlinedTextField(
            value = vm.serverUrl,
            onValueChange = { vm.serverUrl = it },
            label = { Text("Server URL") },
            placeholder = { Text("http://192.168.1.20:8000") },
            singleLine = true,
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

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("How to get a server", style = MaterialTheme.typography.titleSmall)
                Text(
                    "• Free: open VoxCPM_Server_Colab.ipynb (voxcpm-app/server in the repo) in Google Colab " +
                        "with a T4 GPU and run all cells. Paste the printed https://….trycloudflare.com URL here.",
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
