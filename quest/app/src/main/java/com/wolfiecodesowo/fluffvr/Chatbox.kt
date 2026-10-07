package com.wolfiecodesowo.fluffvr

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.SharedPreferences
import android.os.BatteryManager
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** All settings live here (saved on the Quest). */
class Settings(ctx: Context) {
    val p: SharedPreferences = ctx.getSharedPreferences("fluff", Context.MODE_PRIVATE)

    var host: String get() = p.getString("host", "127.0.0.1")!!; set(v) = p.edit().putString("host", v).apply()
    var port: Int get() = p.getInt("port", 9000); set(v) = p.edit().putInt("port", v).apply()
    var interval: Int get() = p.getInt("interval", 3); set(v) = p.edit().putInt("interval", v).apply()
    var statuses: String
        get() = p.getString("statuses", "fluffy vibes only :3\npls give headpats\nrunning on Fluff VR Stats <3")!!
        set(v) = p.edit().putString("statuses", v).apply()
    var rotateSec: Int get() = p.getInt("rotate", 30); set(v) = p.edit().putInt("rotate", v).apply()
    var cute: Boolean get() = p.getBoolean("cute", true); set(v) = p.edit().putBoolean("cute", v).apply()
    var h24: Boolean get() = p.getBoolean("h24", false); set(v) = p.edit().putBoolean("h24", v).apply()
    var theme: Int get() = p.getInt("theme", 0); set(v) = p.edit().putInt("theme", v).apply()

    fun line(key: String): Boolean = p.getBoolean("line_$key", key in DEFAULT_ON)
    fun setLine(key: String, on: Boolean) = p.edit().putBoolean("line_$key", on).apply()

    /** avatar toggles the user added: [{name, type: bool|int|float, value}] */
    var params: JSONArray
        get() = try { JSONArray(p.getString("params", "[]")) } catch (_: Exception) { JSONArray() }
        set(v) = p.edit().putString("params", v.toString()).apply()

    fun addParam(name: String, type: String) {
        val arr = params
        arr.put(JSONObject().put("name", name).put("type", type).put("value", 0))
        params = arr
    }

    fun setParamValue(i: Int, value: Any) {
        val arr = params
        arr.getJSONObject(i).put("value", value)
        params = arr
    }

    fun removeParam(i: Int) {
        val arr = params
        val out = JSONArray()
        for (k in 0 until arr.length()) if (k != i) out.put(arr.get(k))
        params = out
    }

    companion object {
        val LINES = listOf(
            "status" to "Status text", "time" to "Time", "battery" to "Headset battery",
            "session" to "Time in VR", "song" to "Song", "song_bar" to "Song progress"
        )
        val DEFAULT_ON = setOf("status", "time", "battery", "song")
    }
}

/** Builds the chatbox text, same idea as chatbox.py on PC (max 144 chars, 9 lines). */
object Chatbox {
    const val LIMIT = 144
    const val MAX_LINES = 9
    var sessionStart = System.currentTimeMillis()

    private val CUTE = mapOf("status" to "✨", "time" to "⏰", "battery" to "🔋", "session" to "⏱️", "song" to "🎵")
    private val SIMPLE = mapOf("status" to "♡", "song" to "♪")

    fun battery(ctx: Context): Pair<Int, Boolean>? {
        val i = ctx.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)) ?: return null
        val level = i.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = i.getIntExtra(BatteryManager.EXTRA_SCALE, 100)
        if (level < 0) return null
        val status = i.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
        val charging = status == BatteryManager.BATTERY_STATUS_CHARGING || status == BatteryManager.BATTERY_STATUS_FULL
        return (level * 100 / scale) to charging
    }

    fun currentStatus(s: Settings, now: Long): String {
        val list = s.statuses.lines().map { it.trim() }.filter { it.isNotEmpty() }
        if (list.isEmpty()) return ""
        val idx = ((now / 1000) / maxOf(5, s.rotateSec)).toInt() % list.size
        return list[idx]
    }

    private fun fmt(sec: Long) = "${sec / 60}:${"%02d".format(sec % 60)}"

    fun songBar(pos: Long, dur: Long, width: Int = 11): String? {
        if (dur <= 0) return null
        val k = (pos.toDouble() / dur).coerceIn(0.0, 1.0)
        val i = Math.round(k * (width - 1)).toInt()
        return "${fmt(pos)} " + "━".repeat(i) + "◉" + "─".repeat(width - 1 - i) + " ${fmt(dur)}"
    }

    private fun short(t: String, n: Int) = if (t.length <= n) t else t.substring(0, n - 1).trimEnd() + "…"

    fun compose(ctx: Context, s: Settings, now: Long = System.currentTimeMillis()): String {
        val icons = if (s.cute) CUTE else SIMPLE
        fun tag(k: String, text: String): String = icons[k]?.let { "$it $text" } ?: text

        val lines = mutableListOf<String>()
        if (s.line("status")) currentStatus(s, now).takeIf { it.isNotEmpty() }?.let { lines += tag("status", short(it, 60)) }
        val row = mutableListOf<String>()
        if (s.line("time")) {
            val f = SimpleDateFormat(if (s.h24) "HH:mm" else "h:mm a", Locale.getDefault())
            row += tag("time", f.format(Date(now)))
        }
        if (s.line("battery")) battery(ctx)?.let { (pct, chg) -> row += tag("battery", "$pct%" + if (chg) "⚡" else "") }
        if (s.line("session")) {
            val sec = (now - sessionStart) / 1000
            row += tag("session", if (sec >= 3600) "${sec / 3600}h ${"%02d".format(sec % 3600 / 60)}m" else "${sec / 60}m in VR")
        }
        if (row.isNotEmpty()) lines += row.joinToString("  ")
        val m = MusicState.snapshot()
        if (s.line("song") && m.title.isNotEmpty() && m.playing) {
            lines += tag("song", short(if (m.artist.isNotEmpty()) "${m.title} - ${m.artist}" else m.title, 48))
            if (s.line("song_bar")) songBar(m.position(), m.duration)?.let { lines += it }
        }
        var out = lines.take(MAX_LINES).toMutableList()
        while (out.isNotEmpty() && out.joinToString("\n").length > LIMIT) out = out.dropLast(1).toMutableList()
        return out.joinToString("\n")
    }
}
