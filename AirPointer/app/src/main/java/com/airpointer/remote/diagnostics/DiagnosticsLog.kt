package com.airpointer.remote.diagnostics

import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Thread-safe ring buffer of connection/sensor events shown on the diagnostics screen. */
class DiagnosticsLog(private val capacity: Int = 200) {

    enum class Level { INFO, WARN, ERROR }

    data class Entry(val timeMs: Long, val level: Level, val tag: String, val message: String) {
        fun format(): String = "${FORMAT.get()!!.format(Date(timeMs))} ${level.name.first()} [$tag] $message"
    }

    private val buffer = ArrayDeque<Entry>()
    private val _entries = MutableStateFlow<List<Entry>>(emptyList())
    val entries: StateFlow<List<Entry>> = _entries

    fun i(tag: String, msg: String) = add(Level.INFO, tag, msg)
    fun w(tag: String, msg: String) = add(Level.WARN, tag, msg)
    fun e(tag: String, msg: String) = add(Level.ERROR, tag, msg)

    private fun add(level: Level, tag: String, msg: String) {
        when (level) {
            Level.INFO -> Log.i("AirPointer/$tag", msg)
            Level.WARN -> Log.w("AirPointer/$tag", msg)
            Level.ERROR -> Log.e("AirPointer/$tag", msg)
        }
        synchronized(buffer) {
            buffer.addLast(Entry(System.currentTimeMillis(), level, tag, msg))
            while (buffer.size > capacity) buffer.removeFirst()
            _entries.value = buffer.toList()
        }
    }

    fun asText(): String = synchronized(buffer) { buffer.joinToString("\n") { it.format() } }

    private companion object {
        val FORMAT = object : ThreadLocal<SimpleDateFormat>() {
            override fun initialValue() = SimpleDateFormat("HH:mm:ss.SSS", Locale.US)
        }
    }
}
