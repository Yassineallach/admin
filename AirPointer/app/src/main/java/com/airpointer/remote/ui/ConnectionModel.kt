package com.airpointer.remote.ui

/**
 * Everything the home screen's connection card can show, derived from the link state by a pure
 * function ([connectionCardState]) so every state and its recovery action is unit-tested.
 */
enum class CardKind {
    CONNECTED, CONNECTING, DISCONNECTED, NOT_SET_UP, CONNECTION_LOST, PAIRING_FAILED,
    BLUETOOTH_OFF, PERMISSION_NEEDED, WIFI_UNAVAILABLE, UNSUPPORTED, SERVICE_STOPPED,
}

enum class Tone { NEUTRAL, PROGRESS, SUCCESS, WARNING, ERROR }

enum class CardAction(val label: String) {
    CONNECT("Connect now"),
    SET_UP("Set up connection"),
    RECONNECT("Reconnect"),
    CANCEL("Cancel"),
    OPEN_REMOTE("Open remote"),
    DISCONNECT("Disconnect"),
    ENABLE_BLUETOOTH("Turn on Bluetooth"),
    GRANT_PERMISSION("Allow Bluetooth access"),
    WIFI_SETTINGS("Open Wi-Fi settings"),
    USE_WIFI("Use Wi-Fi instead"),
    CONNECTION_SETTINGS("Connection settings"),
    START_SERVICE("Start"),
    TRY_AGAIN("Try again"),
}

enum class Method(val label: String) { BLUETOOTH("Bluetooth"), WIFI("Wi-Fi") }

/** Transport-independent snapshot of the link, filled from the Bluetooth and Wi-Fi controllers. */
data class LinkSnapshot(
    val method: Method,
    val connected: Boolean = false,
    val connecting: Boolean = false,
    val computerName: String? = null,
    /** Bluetooth: a computer was paired before; Wi-Fi: address + PIN saved. */
    val configured: Boolean = false,
    val reconnectAttempt: Int = 0,
    val latencyMs: Int? = null,
    val error: String? = null,
    // Bluetooth only
    val permissionGranted: Boolean = true,
    val bluetoothOn: Boolean = true,
    val hidSupported: Boolean = true,
    val serviceRunning: Boolean = true,
    // Wi-Fi only
    val wifiAvailable: Boolean = true,
    val pinRejected: Boolean = false,
    /** The link dropped without the user asking (from LinkMonitor). */
    val lost: Boolean = false,
)

data class CardState(
    val kind: CardKind,
    val tone: Tone,
    val title: String,
    val description: String,
    val primary: CardAction?,
    val secondary: CardAction? = null,
    val computerName: String? = null,
    val method: Method,
    val signal: String? = null,
)

fun signalQuality(latencyMs: Int?): String? = when {
    latencyMs == null -> null
    latencyMs < 15 -> "Excellent signal"
    latencyMs < 40 -> "Good signal"
    latencyMs < 100 -> "Fair signal"
    else -> "Weak signal"
}

fun connectionCardState(s: LinkSnapshot): CardState {
    val m = s.method
    fun card(kind: CardKind, tone: Tone, title: String, desc: String, p: CardAction?, sec: CardAction? = null) =
        CardState(kind, tone, title, desc, p, sec, s.computerName, m)
    if (m == Method.BLUETOOTH) {
        if (!s.permissionGranted) return card(CardKind.PERMISSION_NEEDED, Tone.WARNING, "PERMISSION NEEDED",
            "Bluetooth mode needs the Nearby devices permission to act as a mouse and keyboard.", CardAction.GRANT_PERMISSION, CardAction.USE_WIFI)
        if (!s.bluetoothOn) return card(CardKind.BLUETOOTH_OFF, Tone.WARNING, "BLUETOOTH IS OFF",
            "Turn on Bluetooth to connect to your computer.", CardAction.ENABLE_BLUETOOTH, CardAction.USE_WIFI)
        if (!s.hidSupported) return card(CardKind.UNSUPPORTED, Tone.ERROR, "BLUETOOTH MOUSE UNSUPPORTED",
            "This phone's firmware can't act as a Bluetooth mouse. Wi-Fi works on every phone.", CardAction.USE_WIFI, CardAction.TRY_AGAIN)
        if (!s.serviceRunning) return card(CardKind.SERVICE_STOPPED, Tone.NEUTRAL, "PAUSED",
            "The Bluetooth service is stopped.", CardAction.START_SERVICE)
    } else if (!s.wifiAvailable && !s.connected) {
        return card(CardKind.WIFI_UNAVAILABLE, Tone.WARNING, "WI-FI UNAVAILABLE",
            "Join the same Wi-Fi network as your computer.", CardAction.WIFI_SETTINGS)
    }
    return when {
        s.connected -> CardState(CardKind.CONNECTED, Tone.SUCCESS, "CONNECTED",
            s.computerName ?: "Your computer", CardAction.OPEN_REMOTE, CardAction.DISCONNECT, s.computerName, m, signalQuality(s.latencyMs))
        s.pinRejected -> card(CardKind.PAIRING_FAILED, Tone.ERROR, "PAIRING UNSUCCESSFUL",
            "The computer rejected the PIN. Check the PIN shown in the companion window.", CardAction.SET_UP)
        s.connecting || s.reconnectAttempt > 0 -> card(CardKind.CONNECTING, Tone.PROGRESS, "CONNECTING",
            if (s.reconnectAttempt > 0) "Reconnecting to ${s.computerName ?: "your computer"} (attempt ${s.reconnectAttempt})."
            else "Establishing connection with ${s.computerName ?: "your computer"}.", CardAction.CANCEL)
        s.lost -> card(CardKind.CONNECTION_LOST, Tone.ERROR, "CONNECTION LOST",
            "${s.computerName ?: "Your computer"} is no longer reachable.", CardAction.RECONNECT, CardAction.CONNECTION_SETTINGS)
        !s.configured -> card(CardKind.NOT_SET_UP, Tone.NEUTRAL, "NOT CONNECTED",
            if (m == Method.WIFI) "No computer set up yet. Run the Air Pointer Companion on your PC, then find it here."
            else "No computer paired yet. Pair your PC once over Bluetooth.", CardAction.SET_UP)
        else -> card(CardKind.DISCONNECTED, Tone.NEUTRAL, "NOT CONNECTED",
            "Connect to your PC to start controlling it.", CardAction.CONNECT, CardAction.CONNECTION_SETTINGS)
    }
}
