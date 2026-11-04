package app.voxcpm.studio.data

import android.content.Context
import org.json.JSONObject

class Settings(context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString("server_url", "") ?: ""
        set(value) = prefs.edit().putString("server_url", value.trim().trimEnd('/')).apply()

    var apiKey: String
        get() = prefs.getString("api_key", "") ?: ""
        set(value) = prefs.edit().putString("api_key", value.trim()).apply()

    /** The saved voice picked last time in Voice clone mode. */
    var selectedVoiceId: String?
        get() = prefs.getString("selected_voice", null)
        set(value) = prefs.edit().putString("selected_voice", value).apply()

    /** Capabilities of the server last connected to, so the UI fits it before the next check. */
    var serverInfo: ServerInfo
        get() = prefs.getString("server_info", null)
            ?.let { runCatching { ServerInfo.fromJson(JSONObject(it)) }.getOrNull() } ?: ServerInfo.VOXCPM
        set(value) = prefs.edit().putString("server_info", value.toJson().toString()).apply()

    /** Learned generation speed of the server, used for time estimates. 0 = not measured yet. */
    var secPerChar: Float
        get() = prefs.getFloat("sec_per_char", 0f)
        set(value) = prefs.edit().putFloat("sec_per_char", value).apply()
}
