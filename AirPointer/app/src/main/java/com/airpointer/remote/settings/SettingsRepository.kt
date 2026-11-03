package com.airpointer.remote.settings

import android.content.Context
import android.content.SharedPreferences
import com.airpointer.remote.presenter.RemoteAction
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/** SharedPreferences-backed settings exposed as a StateFlow. Writes are applied asynchronously. */
class SettingsRepository(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("air_pointer_settings", Context.MODE_PRIVATE)

    private val _settings = MutableStateFlow(migrate(load()))
    val settings: StateFlow<AppSettings> = _settings
    val current: AppSettings get() = _settings.value

    @Synchronized
    fun update(transform: (AppSettings) -> AppSettings) {
        val next = transform(_settings.value)
        if (next == _settings.value) return
        _settings.value = next
        save(next)
    }

    fun resetTuning() = update {
        val d = AppSettings()
        d.copy(
            lastHostAddress = it.lastHostAddress,
            lastHostName = it.lastHostName,
            gyroBiasX = it.gyroBiasX, gyroBiasY = it.gyroBiasY, gyroBiasZ = it.gyroBiasZ,
            calibratedAtMs = it.calibratedAtMs,
        )
    }

    private fun migrate(s: AppSettings): AppSettings {
        val schema = prefs.getInt("schema", if (prefs.contains("sensitivity")) 1 else SCHEMA)
        if (schema >= SCHEMA) return s
        val migrated = s.copy(
            tapAction = if (s.tapAction == RemoteAction.LEFT_CLICK) RemoteAction.NONE else s.tapAction,
            longPressAction = if (s.longPressAction == RemoteAction.RIGHT_CLICK) RemoteAction.NONE else s.longPressAction,
        )
        save(migrated)
        return migrated
    }

    private fun load(): AppSettings {
        val d = AppSettings()
        return AppSettings(
            sensitivity = prefs.getFloat("sensitivity", d.sensitivity),
            acceleration = prefs.getFloat("acceleration", d.acceleration),
            smoothing = prefs.getFloat("smoothing", d.smoothing),
            deadzone = prefs.getFloat("deadzone", d.deadzone),
            autoDriftCompensation = prefs.getBoolean("autoDrift", d.autoDriftCompensation),
            invertX = prefs.getBoolean("invertX", d.invertX),
            invertY = prefs.getBoolean("invertY", d.invertY),
            pointerMode = enumOr("pointerMode", d.pointerMode),
            recenterOnActivate = prefs.getBoolean("recenterOnActivate", d.recenterOnActivate),
            laserOnActivate = prefs.getBoolean("laserOnActivate", d.laserOnActivate),
            hostWidth = prefs.getInt("hostWidth", d.hostWidth),
            hostHeight = prefs.getInt("hostHeight", d.hostHeight),
            scrollStepDp = prefs.getInt("scrollStepDp", d.scrollStepDp),
            slideKeys = enumOr("slideKeys", d.slideKeys),
            volumeKeysEnabled = prefs.getBoolean("volumeKeys", d.volumeKeysEnabled),
            volumeUpAction = enumOr("volumeUpAction", d.volumeUpAction),
            volumeDownAction = enumOr("volumeDownAction", d.volumeDownAction),
            tapAction = enumOr("tapAction", d.tapAction),
            doubleTapAction = enumOr("doubleTapAction", d.doubleTapAction),
            longPressAction = enumOr("longPressAction", d.longPressAction),
            swipeLeftAction = enumOr("swipeLeftAction", d.swipeLeftAction),
            swipeRightAction = enumOr("swipeRightAction", d.swipeRightAction),
            swipeUpAction = enumOr("swipeUpAction", d.swipeUpAction),
            swipeDownAction = enumOr("swipeDownAction", d.swipeDownAction),
            haptics = prefs.getBoolean("haptics", d.haptics),
            keepScreenOn = prefs.getBoolean("keepScreenOn", d.keepScreenOn),
            reportRateHz = prefs.getInt("reportRateHz", d.reportRateHz),
            autoReconnect = prefs.getBoolean("autoReconnect", d.autoReconnect),
            lastHostAddress = prefs.getString("lastHostAddress", null),
            lastHostName = prefs.getString("lastHostName", null),
            gyroBiasX = prefs.getFloat("biasX", 0f),
            gyroBiasY = prefs.getFloat("biasY", 0f),
            gyroBiasZ = prefs.getFloat("biasZ", 0f),
            calibratedAtMs = prefs.getLong("calibratedAt", 0L),
        )
    }

    private fun save(s: AppSettings) {
        prefs.edit()
            .putInt("schema", SCHEMA)
            .putFloat("sensitivity", s.sensitivity)
            .putFloat("acceleration", s.acceleration)
            .putFloat("smoothing", s.smoothing)
            .putFloat("deadzone", s.deadzone)
            .putBoolean("autoDrift", s.autoDriftCompensation)
            .putBoolean("invertX", s.invertX)
            .putBoolean("invertY", s.invertY)
            .putString("pointerMode", s.pointerMode.name)
            .putBoolean("recenterOnActivate", s.recenterOnActivate)
            .putBoolean("laserOnActivate", s.laserOnActivate)
            .putInt("hostWidth", s.hostWidth)
            .putInt("hostHeight", s.hostHeight)
            .putInt("scrollStepDp", s.scrollStepDp)
            .putString("slideKeys", s.slideKeys.name)
            .putBoolean("volumeKeys", s.volumeKeysEnabled)
            .putString("volumeUpAction", s.volumeUpAction.name)
            .putString("volumeDownAction", s.volumeDownAction.name)
            .putString("tapAction", s.tapAction.name)
            .putString("doubleTapAction", s.doubleTapAction.name)
            .putString("longPressAction", s.longPressAction.name)
            .putString("swipeLeftAction", s.swipeLeftAction.name)
            .putString("swipeRightAction", s.swipeRightAction.name)
            .putString("swipeUpAction", s.swipeUpAction.name)
            .putString("swipeDownAction", s.swipeDownAction.name)
            .putBoolean("haptics", s.haptics)
            .putBoolean("keepScreenOn", s.keepScreenOn)
            .putInt("reportRateHz", s.reportRateHz)
            .putBoolean("autoReconnect", s.autoReconnect)
            .putString("lastHostAddress", s.lastHostAddress)
            .putString("lastHostName", s.lastHostName)
            .putFloat("biasX", s.gyroBiasX)
            .putFloat("biasY", s.gyroBiasY)
            .putFloat("biasZ", s.gyroBiasZ)
            .putLong("calibratedAt", s.calibratedAtMs)
            .apply()
    }

    private companion object {
        /** 2: gesture pad no longer clicks by default. */
        const val SCHEMA = 2
    }

    private inline fun <reified E : Enum<E>> enumOr(key: String, default: E): E =
        prefs.getString(key, null)?.let { name -> enumValues<E>().firstOrNull { it.name == name } } ?: default
}
