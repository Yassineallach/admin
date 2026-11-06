package com.airpointer.remote.tv

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONArray
import org.json.JSONObject

/** Saved TVs (and which one is selected), persisted as JSON in SharedPreferences. */
class TvRepository(context: Context) {
    private val prefs = context.getSharedPreferences("air_pointer_tvs", Context.MODE_PRIVATE)
    private val _tvs = MutableStateFlow(load())
    val tvs: StateFlow<List<SavedTv>> = _tvs
    private val _selectedId = MutableStateFlow(prefs.getString("selected", null))
    val selectedId: StateFlow<String?> = _selectedId

    val selected: SavedTv? get() = _tvs.value.firstOrNull { it.id == _selectedId.value }

    @Synchronized fun save(tv: SavedTv) {
        _tvs.value = _tvs.value.filter { it.id != tv.id } + tv
        persist()
    }

    @Synchronized fun remove(id: String) {
        _tvs.value = _tvs.value.filter { it.id != id }
        if (_selectedId.value == id) select(_tvs.value.firstOrNull()?.id)
        persist()
    }

    fun select(id: String?) {
        _selectedId.value = id
        prefs.edit().putString("selected", id).apply()
    }

    private fun persist() {
        val arr = JSONArray()
        for (t in _tvs.value) arr.put(JSONObject()
            .put("id", t.id).put("name", t.name).put("protocol", t.protocol.name)
            .putOpt("host", t.host).putOpt("mac", t.mac).putOpt("credential", t.credential).putOpt("ir", t.irCodeSet).putOpt("pin", t.certPin))
        prefs.edit().putString("tvs", arr.toString()).apply()
    }

    private fun load(): List<SavedTv> = runCatching {
        val arr = JSONArray(prefs.getString("tvs", "[]"))
        (0 until arr.length()).mapNotNull { i ->
            val o = arr.getJSONObject(i)
            val protocol = TvProtocol.entries.firstOrNull { it.name == o.optString("protocol") } ?: return@mapNotNull null
            SavedTv(o.getString("id"), o.getString("name"), protocol,
                o.optString("host").ifBlank { null }, o.optString("mac").ifBlank { null },
                o.optString("credential").ifBlank { null }, o.optString("ir").ifBlank { null },
                o.optString("pin").ifBlank { null })
        }
    }.getOrDefault(emptyList())
}
