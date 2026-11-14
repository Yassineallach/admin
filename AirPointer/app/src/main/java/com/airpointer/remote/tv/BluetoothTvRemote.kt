package com.airpointer.remote.tv

import com.airpointer.remote.hid.ConsumerUsages
import com.airpointer.remote.hid.KeyCodes
import com.airpointer.remote.presenter.PresenterController
import com.airpointer.remote.transport.ReportSink
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Controls a TV that is paired with the phone as a Bluetooth keyboard (the phone's own HID
 * keyboard + consumer-control collections). Android TV / Google TV map these to remote keys;
 * many Samsung/LG TVs accept arrows, Enter and media keys from Bluetooth keyboards too.
 */
class BluetoothTvRemote(private val presenter: PresenterController, private val bluetooth: ReportSink) : TvConnection {

    override val protocol = TvProtocol.BLUETOOTH_HID
    private val _state = MutableStateFlow<TvConnState>(TvConnState.Disconnected)
    override val state: StateFlow<TvConnState> = _state
    override val supportsText = false
    override val supportedKeys = KEYS.keys + CONSUMER.keys
    override val limitations = listOf(
        "Pair the phone from the TV: Settings → Remotes & Accessories (Android TV) or Bluetooth device list, while Air Pointer shows \"Ready\".",
        "Bluetooth must be the selected connection; the phone can be connected to one host at a time.",
        "Power works only on TVs that wake from Bluetooth (most Android TV / Google TV devices).",
        "Input/Source and Settings have no standard keyboard key and are not available over Bluetooth.",
    )

    override suspend fun connect() {
        _state.value = if (bluetooth.isConnected) TvConnState.Connected
        else TvConnState.NeedsUser("Pair this phone from the TV's Bluetooth settings (Air Pointer must show Ready), then connect it under Connection.")
    }

    fun refresh(connected: Boolean) {
        if (_state.value != TvConnState.Disconnected) {
            _state.value = if (connected) TvConnState.Connected
            else TvConnState.NeedsUser("Waiting for the TV to connect over Bluetooth…")
        }
    }

    override suspend fun send(key: TvKey) {
        KEYS[key]?.let { presenter.key(it); return }
        CONSUMER[key]?.let { presenter.consumer(it) }
    }

    override fun close() { _state.value = TvConnState.Disconnected }

    companion object {
        val KEYS: Map<TvKey, Int> = mapOf(
            TvKey.UP to KeyCodes.UP_ARROW, TvKey.DOWN to KeyCodes.DOWN_ARROW, TvKey.LEFT to KeyCodes.LEFT_ARROW,
            TvKey.RIGHT to KeyCodes.RIGHT_ARROW, TvKey.OK to KeyCodes.ENTER, TvKey.EXIT to KeyCodes.ESCAPE,
        ) + TvKey.digits.mapIndexed { i, k -> k to if (i == 0) KeyCodes.DIGIT_0 else KeyCodes.DIGIT_1 + i - 1 }

        val CONSUMER: Map<TvKey, Int> = mapOf(
            TvKey.POWER to ConsumerUsages.POWER, TvKey.VOLUME_UP to ConsumerUsages.VOLUME_UP,
            TvKey.VOLUME_DOWN to ConsumerUsages.VOLUME_DOWN, TvKey.MUTE to ConsumerUsages.MUTE,
            TvKey.CHANNEL_UP to ConsumerUsages.CHANNEL_UP, TvKey.CHANNEL_DOWN to ConsumerUsages.CHANNEL_DOWN,
            TvKey.HOME to ConsumerUsages.AC_HOME, TvKey.BACK to ConsumerUsages.AC_BACK, TvKey.MENU to ConsumerUsages.MENU,
            TvKey.INFO to ConsumerUsages.INFO, TvKey.PLAY_PAUSE to ConsumerUsages.PLAY_PAUSE,
            TvKey.PLAY to ConsumerUsages.PLAY_PAUSE, TvKey.PAUSE to ConsumerUsages.PLAY_PAUSE,
            TvKey.STOP to ConsumerUsages.STOP, TvKey.REWIND to ConsumerUsages.REWIND,
            TvKey.FAST_FORWARD to ConsumerUsages.FAST_FORWARD, TvKey.VOICE to ConsumerUsages.AC_SEARCH,
        )
    }
}
