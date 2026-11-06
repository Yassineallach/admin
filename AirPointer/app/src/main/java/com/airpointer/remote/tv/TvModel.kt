package com.airpointer.remote.tv

import kotlinx.coroutines.flow.StateFlow

/** Every button on the universal TV remote. */
enum class TvKey(val label: String) {
    POWER("Power"), VOLUME_UP("Vol +"), VOLUME_DOWN("Vol −"), MUTE("Mute"),
    CHANNEL_UP("Ch +"), CHANNEL_DOWN("Ch −"),
    HOME("Home"), BACK("Back"), MENU("Menu"), SETTINGS("Settings"), SOURCE("Input"), INFO("Info"), EXIT("Exit"),
    UP("Up"), DOWN("Down"), LEFT("Left"), RIGHT("Right"), OK("OK"),
    PLAY_PAUSE("Play/Pause"), PLAY("Play"), PAUSE("Pause"), STOP("Stop"), REWIND("Rewind"), FAST_FORWARD("Fast forward"),
    NUM_0("0"), NUM_1("1"), NUM_2("2"), NUM_3("3"), NUM_4("4"), NUM_5("5"), NUM_6("6"), NUM_7("7"), NUM_8("8"), NUM_9("9"),
    VOICE("Voice"),
    ;
    companion object {
        val digits = listOf(NUM_0, NUM_1, NUM_2, NUM_3, NUM_4, NUM_5, NUM_6, NUM_7, NUM_8, NUM_9)
    }
}

/** How the phone talks to a TV. The protocol decides which keys exist. */
enum class TvProtocol(val label: String, val brandHint: String, val needsIp: Boolean) {
    ANDROID_TV("Android TV / Google TV (Wi-Fi)", "Sony, TCL, Hisense, Philips, Xiaomi, Chromecast with Google TV…", true),
    SAMSUNG_TIZEN("Samsung Smart TV (Wi-Fi)", "Samsung Tizen TVs, 2016 and newer", true),
    LG_WEBOS("LG Smart TV (Wi-Fi)", "LG webOS TVs, 2014 and newer", true),
    INFRARED("Infrared", "Any TV — needs an IR blaster in the phone", false),
    BLUETOOTH_HID("Bluetooth keyboard", "Android TV / Google TV and most smart TVs that accept Bluetooth keyboards", false),
}

/** A TV the user has set up. Credentials are the per-protocol pairing result (token / client key / IR code set). */
data class SavedTv(
    val id: String,
    val name: String,
    val protocol: TvProtocol,
    val host: String? = null,
    val mac: String? = null,
    val credential: String? = null,
    val irCodeSet: String? = null,
    /** SHA-256 of the TV's TLS certificate, pinned on first contact. */
    val certPin: String? = null,
)

sealed interface TvConnState {
    data object Disconnected : TvConnState
    data object Connecting : TvConnState
    /** The TV is waiting for the user: [message] says what to do (accept on TV, enter code…). */
    data class NeedsUser(val message: String, val needsCode: Boolean = false) : TvConnState
    data object Connected : TvConnState
    data class Failed(val reason: String) : TvConnState
}

interface TvConnection {
    val protocol: TvProtocol
    val state: StateFlow<TvConnState>
    /** Keys this protocol can send. Others are shown disabled with an explanation. */
    val supportedKeys: Set<TvKey>
    val supportsText: Boolean
    /** Human-readable limits shown under the remote. */
    val limitations: List<String>

    suspend fun connect()
    /** Answer a [TvConnState.NeedsUser] that asked for a code (Android TV pairing). */
    suspend fun submitCode(code: String) {}
    suspend fun send(key: TvKey)
    suspend fun sendText(text: String) {}
    fun close()
    /** Updated credential after pairing, to persist in [SavedTv.credential]. */
    val credential: String? get() = null
    /** Certificate fingerprint seen on the last connection (to pin), if the protocol uses TLS. */
    val certificatePin: String? get() = null
}
