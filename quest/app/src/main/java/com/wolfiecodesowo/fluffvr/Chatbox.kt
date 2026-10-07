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
    var headpatParam: String get() = p.getString("patparam", "HeadPat")!!; set(v) = p.edit().putString("patparam", v).apply()
    var headpats: Int get() = p.getInt("headpats", 0); set(v) = p.edit().putInt("headpats", v).apply()
    var city: String get() = p.getString("city", "")!!; set(v) = p.edit().putString("city", v).apply()
    var fahrenheit: Boolean get() = p.getBoolean("fahr", true); set(v) = p.edit().putBoolean("fahr", v).apply()
    var timerEnd: Long get() = p.getLong("timer_end", 0L); set(v) = p.edit().putLong("timer_end", v).apply()
    var stopwatchStart: Long get() = p.getLong("sw_start", 0L); set(v) = p.edit().putLong("sw_start", v).apply()
    var counterLabel: String get() = p.getString("cnt_label", "water sips")!!; set(v) = p.edit().putString("cnt_label", v).apply()
    var counter: Int get() = p.getInt("cnt", 0); set(v) = p.edit().putInt("cnt", v).apply()
    var hydrateMin: Int get() = p.getInt("hydrate_min", 30); set(v) = p.edit().putInt("hydrate_min", v).apply()

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
        /** Quest-only mods (shown in the Mods tab) */
        val MODS = listOf(
            Triple("afk", "💤 AFK detector", "shows \"AFK 5m\" when u take the headset off"),
            Triple("wifi", "📶 Wi-Fi signal", "ur Wi-Fi bars, handy for wireless play"),
            Triple("ping", "🏓 Ping", "ur internet delay in ms"),
            Triple("timer", "⏳ Timer / stopwatch", "a countdown or stopwatch everyone can see"),
            Triple("weather", "🌤️ Weather", "temp + sky for ur city"),
            Triple("headpats", "🐾 Headpat counter", "counts headpats (avatar needs a headpat contact)"),
            Triple("muted", "🔇 Mute indicator", "shows when ur mic is muted"),
            Triple("temp", "🌡️ Headset temp", "battery temperature, see if ur Quest is cooking"),
            Triple("ram", "🧠 Free memory", "how much RAM the Quest has left"),
            Triple("lowbatt", "🪫 Low battery warning", "big warning in the chatbox under 15%"),
            Triple("hydrate", "💧 Hydration reminder", "pops \"sip time!\" in ur chatbox every few minutes"),
            Triple("counter", "🔢 Custom counter", "count anything: water, deaths, boops..."),
            Triple("date", "📅 Date", "today's date next to the time"),
            Triple("kaomoji", "(=^･ω･^=) Kaomoji", "a cute rotating face at the end"),
        )
        val DEFAULT_ON = setOf("status", "time", "battery", "song", "afk", "timer")
    }
}

/** Builds the chatbox text, same idea as chatbox.py on PC (max 144 chars, 9 lines). */
object Chatbox {
    const val LIMIT = 144
    const val MAX_LINES = 9
    var sessionStart = System.currentTimeMillis()

    private val CUTE = mapOf("status" to "✨", "time" to "⏰", "battery" to "🔋", "session" to "⏱️", "song" to "🎵",
        "afk" to "💤", "wifi" to "📶", "ping" to "🏓", "timer" to "⏳", "weather" to "🌤️", "headpats" to "🐾", "muted" to "🔇",
        "temp" to "🌡️", "ram" to "🧠", "lowbatt" to "🪫", "hydrate" to "💧", "counter" to "🔢", "date" to "📅")
    private val KAO = listOf("(=^･ω･^=)", "(◕ᴗ◕✿)", "(｡•ᴗ•｡)", "ʕ•ᴥ•ʔ", "(≧◡≦)", "(•ω•)", "ฅ^•ﻌ•^ฅ", "(｡♥‿♥｡)")
    private val SIMPLE = mapOf("status" to "♡", "song" to "♪", "afk" to "zzz")

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
        val m = MusicState.snapshot()
        val afk = QuestMods.afkSince
        if (s.line("afk") && afk > 0) {
            val m = (now - afk) / 60000
            lines += tag("afk", if (m >= 1) "AFK ${m}m" else "AFK")
        }
        val batt = battery(ctx)
        if (s.line("lowbatt") && batt != null && batt.first < 15 && !batt.second) lines += tag("lowbatt", "LOW BATTERY ${batt.first}%!!")
        if (s.line("hydrate")) {
            val every = maxOf(5, s.hydrateMin) * 60_000L
            if ((now - sessionStart) > 60_000 && (now - sessionStart) % every < 45_000) lines += tag("hydrate", "sip time! drink some water")
        }
        if (s.line("status")) currentStatus(s, now).takeIf { it.isNotEmpty() }?.let { lines += tag("status", short(it, 60)) }
        val row = mutableListOf<String>()
        if (s.line("time")) {
            val f = SimpleDateFormat(if (s.h24) "HH:mm" else "h:mm a", Locale.getDefault())
            row += tag("time", f.format(Date(now)))
        }
        if (s.line("date")) row += tag("date", SimpleDateFormat("MMM d", Locale.getDefault()).format(Date(now)))
        if (s.line("battery")) batt?.let { (pct, chg) -> row += tag("battery", "$pct%" + if (chg) "⚡" else "") }
        if (s.line("session")) {
            val sec = (now - sessionStart) / 1000
            row += tag("session", if (sec >= 3600) "${sec / 3600}h ${"%02d".format(sec % 3600 / 60)}m" else "${sec / 60}m in VR")
        }
        if (s.line("wifi")) QuestMods.wifiBars(ctx)?.let { b -> row += tag("wifi", "▮".repeat(b.coerceIn(0, 4) + 1)) }
        if (s.line("ping")) QuestMods.pingMs?.let { row += tag("ping", "${it}ms") }
        if (row.isNotEmpty()) lines += row.joinToString("  ")
        if (s.line("timer")) QuestMods.timerText(s, now)?.let { lines += tag("timer", it) }
        if (s.line("song") && m.title.isNotEmpty() && m.playing) {
            lines += tag("song", short(if (m.artist.isNotEmpty()) "${m.title} - ${m.artist}" else m.title, 48))
            if (s.line("song_bar")) songBar(m.position(), m.duration)?.let { lines += it }
        }
        val extra = mutableListOf<String>()
        if (s.line("weather")) QuestMods.weather?.let { extra += tag("weather", it) }
        if (s.line("headpats") && s.headpats > 0) extra += tag("headpats", "${s.headpats} headpats")
        if (s.line("muted") && QuestMods.muted == true) extra += tag("muted", "muted")
        if (s.line("counter")) extra += tag("counter", "${s.counter} ${s.counterLabel}")
        if (s.line("temp")) QuestMods.tempC(ctx)?.let { c -> extra += tag("temp", if (s.fahrenheit) "${Math.round(c * 9 / 5 + 32)}°F" else "${Math.round(c)}°C") }
        if (s.line("ram")) QuestMods.freeRamGb(ctx)?.let { extra += tag("ram", "%.1fGB free".format(it)) }
        if (extra.isNotEmpty()) lines += extra.joinToString("  ")
        if (s.line("kaomoji") && lines.isNotEmpty()) {
            lines[lines.size - 1] = lines.last() + " " + KAO[((now / 20000) % KAO.size).toInt()]
        }
        var out = lines.take(MAX_LINES).toMutableList()
        while (out.isNotEmpty() && out.joinToString("\n").length > LIMIT) out = out.dropLast(1).toMutableList()
        return out.joinToString("\n")
    }
}
