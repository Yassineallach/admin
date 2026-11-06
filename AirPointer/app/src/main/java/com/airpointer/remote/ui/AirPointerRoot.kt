package com.airpointer.remote.ui

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.airpointer.remote.MainActivity
import com.airpointer.remote.graph
import com.airpointer.remote.service.AirPointerService
import com.airpointer.remote.ui.screens.DiagnosticsScreen
import com.airpointer.remote.ui.screens.HomeScreen
import com.airpointer.remote.ui.screens.PairingScreen
import com.airpointer.remote.ui.screens.RemoteScreen
import com.airpointer.remote.ui.screens.MediaRemoteScreen
import com.airpointer.remote.ui.screens.PcMouseScreen
import com.airpointer.remote.ui.screens.SettingsScreen
import com.airpointer.remote.ui.screens.TvDevicesScreen
import com.airpointer.remote.ui.screens.TvRemoteScreen
import com.airpointer.remote.ui.theme.Palette

enum class Route { HOME, PAIRING, REMOTE, PC_MOUSE, TV, TV_DEVICES, MEDIA, SETTINGS, DIAGNOSTICS }

/** Runtime permissions. Only BLUETOOTH_CONNECT is strictly required for HID on Android 12+. */
object Permissions {
    val required: Array<String> = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S)
        arrayOf(Manifest.permission.BLUETOOTH_CONNECT) else emptyArray()

    val all: Array<String> = buildList {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            add(Manifest.permission.BLUETOOTH_CONNECT)
            add(Manifest.permission.BLUETOOTH_SCAN)
            add(Manifest.permission.BLUETOOTH_ADVERTISE)
        } else {
            add(Manifest.permission.ACCESS_COARSE_LOCATION)
            add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) add(Manifest.permission.POST_NOTIFICATIONS)
    }.toTypedArray()
}

class AppActions(
    val requestPermissions: () -> Unit,
    val enableBluetooth: () -> Unit,
    val makeDiscoverable: () -> Unit,
    val permissionsGranted: Boolean,
)

@Composable
fun AirPointerRoot(activity: MainActivity) {
    val graph = activity.graph
    val backStack = remember { mutableStateListOf(Route.HOME) }
    var permissionsGranted by remember { mutableStateOf(hasRequired(activity)) }

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        permissionsGranted = hasRequired(activity)
        graph.hid.refresh()
        graph.pairing.refresh()
        if (permissionsGranted) AirPointerService.start(activity)
    }
    val enableBtLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) {
        graph.hid.refresh()
    }
    val discoverableLauncher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) {
        graph.pairing.refresh()
    }

    LaunchedEffect(Unit) {
        if (permissionsGranted) AirPointerService.start(activity)
        else permissionLauncher.launch(Permissions.all)
    }


    val actions = AppActions(
        requestPermissions = { permissionLauncher.launch(Permissions.all) },
        enableBluetooth = {
            try { enableBtLauncher.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)) } catch (_: SecurityException) {}
        },
        makeDiscoverable = {
            try {
                discoverableLauncher.launch(
                    Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE).putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, 180),
                )
            } catch (_: SecurityException) {}
        },
        permissionsGranted = permissionsGranted,
    )

    val navigate: (Route) -> Unit = { backStack.add(it) }
    val back: () -> Unit = { if (backStack.size > 1) backStack.removeAt(backStack.lastIndex) }
    BackHandler(enabled = backStack.size > 1, onBack = back)

    Box(Modifier.fillMaxSize().background(Palette.Background)) {
        AnimatedContent(
            targetState = backStack.last(),
            transitionSpec = {
                val forward = targetState.ordinal >= initialState.ordinal
                (fadeIn(tween(220)) + slideInHorizontally(tween(260)) { if (forward) it / 8 else -it / 8 }) togetherWith
                    (fadeOut(tween(160)) + slideOutHorizontally(tween(260)) { if (forward) -it / 8 else it / 8 })
            },
            label = "nav",
        ) { route ->
            when (route) {
                Route.HOME -> HomeScreen(
                    graph, actions, navigate,
                    onStart = { AirPointerService.start(activity) },
                    onStop = { AirPointerService.stop(activity) },
                )
                Route.PAIRING -> PairingScreen(graph, actions, back)
                Route.REMOTE -> RemoteScreen(graph, activity, back, navigate)
                Route.PC_MOUSE -> PcMouseScreen(graph, activity, back, navigate)
                Route.TV -> TvRemoteScreen(graph, back, navigate)
                Route.TV_DEVICES -> TvDevicesScreen(graph, back)
                Route.MEDIA -> MediaRemoteScreen(graph, back, navigate)
                Route.SETTINGS -> SettingsScreen(graph, back)
                Route.DIAGNOSTICS -> DiagnosticsScreen(graph, back)
            }
        }
    }
}

private fun hasRequired(activity: MainActivity) = Permissions.required.all {
    ContextCompat.checkSelfPermission(activity, it) == PackageManager.PERMISSION_GRANTED
}
