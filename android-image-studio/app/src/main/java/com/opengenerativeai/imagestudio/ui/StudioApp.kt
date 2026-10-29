package com.opengenerativeai.imagestudio.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Create
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.viewmodel.compose.viewModel

private enum class Tab(val label: String, val icon: ImageVector) {
    CREATE("Create", Icons.Default.Create),
    HISTORY("History", Icons.Default.DateRange),
    SETTINGS("Settings", Icons.Default.Settings),
}

@Composable
fun StudioApp(vm: StudioViewModel = viewModel()) {
    var tab by rememberSaveable { mutableStateOf(if (vm.apiKey.isEmpty()) Tab.SETTINGS else Tab.CREATE) }
    var viewing by remember { mutableStateOf<String?>(null) }
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(vm.message) {
        vm.message?.let {
            snackbar.showSnackbar(it)
            vm.message = null
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        bottomBar = {
            NavigationBar {
                Tab.entries.forEach { t ->
                    NavigationBarItem(
                        selected = tab == t,
                        onClick = { tab = t },
                        icon = { Icon(t.icon, contentDescription = null) },
                        label = { Text(t.label) },
                    )
                }
            }
        },
    ) { padding ->
        val modifier = Modifier.padding(padding)
        when (tab) {
            Tab.CREATE -> CreateScreen(vm, onOpenImage = { viewing = it }, modifier = modifier)
            Tab.HISTORY -> HistoryScreen(
                vm,
                onOpenImage = { viewing = it },
                onReuse = { vm.reuse(it); tab = Tab.CREATE },
                modifier = modifier,
            )
            Tab.SETTINGS -> SettingsScreen(vm, onDone = { tab = Tab.CREATE }, modifier = modifier)
        }
    }

    viewing?.let { url ->
        ImageViewer(url = url, onSave = { vm.saveImage(url) }, onDismiss = { viewing = null })
    }
}
