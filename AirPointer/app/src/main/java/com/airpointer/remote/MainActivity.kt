package com.airpointer.remote

import android.os.Bundle
import android.view.KeyEvent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.airpointer.remote.ui.AirPointerRoot
import com.airpointer.remote.ui.theme.AirPointerTheme

class MainActivity : ComponentActivity() {

    /** Set by the remote screen while it is visible: volume keys become slide controls. */
    @Volatile var volumeKeysCaptured = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            AirPointerTheme {
                AirPointerRoot(this)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        graph.hid.refresh()
        graph.pairing.refresh()
    }

    private fun volumeRouted(keyCode: Int): Boolean {
        if (keyCode != KeyEvent.KEYCODE_VOLUME_UP && keyCode != KeyEvent.KEYCODE_VOLUME_DOWN) return false
        return volumeKeysCaptured && graph.settings.current.volumeKeysEnabled && graph.hid.state.value.connected
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (!volumeRouted(keyCode)) return super.onKeyDown(keyCode, event)
        if (event.repeatCount == 0) {
            val s = graph.settings.current
            graph.presenter.perform(if (keyCode == KeyEvent.KEYCODE_VOLUME_UP) s.volumeUpAction else s.volumeDownAction)
        }
        return true // consumed: the system volume does not change
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean =
        if (volumeRouted(keyCode)) true else super.onKeyUp(keyCode, event)
}
