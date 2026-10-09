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
    var boopParam: String get() = p.getString("boopparam", "")!!; set(v) = p.edit().putString("boopparam", v).apply()
    var boops: Int get() = p.getInt("boops", 0); set(v) = p.edit().putInt("boops", v).apply()
    var jumps: Int get() = p.getInt("jumps", 0); set(v) = p.edit().putInt("jumps", v).apply()
    var walkedM: Float get() = p.getFloat("walked", 0f); set(v) = p.edit().putFloat("walked", v).apply()
    var countdownName: String get() = p.getString("cd_name", "my birthday")!!; set(v) = p.edit().putString("cd_name", v).apply()
    var countdownDate: String get() = p.getString("cd_date", "")!!; set(v) = p.edit().putString("cd_date", v).apply()
    var bedtime: String get() = p.getString("bedtime", "01:00")!!; set(v) = p.edit().putString("bedtime", v).apply()
    var eyeMin: Int get() = p.getInt("eye_min", 20); set(v) = p.edit().putInt("eye_min", v).apply()
    var postureMin: Int get() = p.getInt("posture_min", 30); set(v) = p.edit().putInt("posture_min", v).apply()
    var vrDate: String get() = p.getString("vr_date", "")!!; set(v) = p.edit().putString("vr_date", v).apply()
    var vrTodayS: Long get() = p.getLong("vr_today", 0L); set(v) = p.edit().putLong("vr_today", v).apply()
    var vrStreak: Int get() = p.getInt("vr_streak", 0); set(v) = p.edit().putInt("vr_streak", v).apply()
    var hydrateMin: Int get() = p.getInt("hydrate_min", 30); set(v) = p.edit().putInt("hydrate_min", v).apply()

    // v0.9.0: picked status + rotation anchor (so the one u pick shows right away)
    var statusIdx: Int get() = p.getInt("status_idx", 0); set(v) = p.edit().putInt("status_idx", v).apply()
    var rotateFrom: Long get() = p.getLong("rotate_from", 0L); set(v) = p.edit().putLong("rotate_from", v).apply()
    var rotate: Boolean get() = p.getBoolean("rotate_on", true); set(v) = p.edit().putBoolean("rotate_on", v).apply()
    var mood: String get() = p.getString("mood", MOODS[0])!!; set(v) = p.edit().putString("mood", v).apply()
    var sips: Int get() = p.getInt("sips", 0); set(v) = p.edit().putInt("sips", v).apply()
    var sipDate: String get() = p.getString("sip_date", "")!!; set(v) = p.edit().putString("sip_date", v).apply()
    var clock2Name: String get() = p.getString("clock2_name", "Tokyo")!!; set(v) = p.edit().putString("clock2_name", v).apply()
    var clock2Off: Float get() = p.getFloat("clock2_off", 9f); set(v) = p.edit().putFloat("clock2_off", v).apply()
    var quietFrom: String get() = p.getString("quiet_from", "23:00")!!; set(v) = p.edit().putString("quiet_from", v).apply()
    var quietTo: String get() = p.getString("quiet_to", "08:00")!!; set(v) = p.edit().putString("quiet_to", v).apply()
    var playLimitH: Int get() = p.getInt("play_limit_h", 3); set(v) = p.edit().putInt("play_limit_h", v).apply()
    var patGoal: Int get() = p.getInt("pat_goal", 50); set(v) = p.edit().putInt("pat_goal", v).apply()
    var patGoalDate: String get() = p.getString("pat_goal_date", "")!!; set(v) = p.edit().putString("pat_goal_date", v).apply()
    var patGoalStart: Int get() = p.getInt("pat_goal_start", 0); set(v) = p.edit().putInt("pat_goal_start", v).apply()
    var swaps: Int get() = p.getInt("swaps", 0); set(v) = p.edit().putInt("swaps", v).apply()
    var swapDate: String get() = p.getString("swap_date", "")!!; set(v) = p.edit().putString("swap_date", v).apply()
    var modFilter: String get() = p.getString("mod_filter", "all")!!; set(v) = p.edit().putString("mod_filter", v).apply()
    var seenNews: Int get() = p.getInt("seen_news", 0); set(v) = p.edit().putInt("seen_news", v).apply()

    fun statusList() = statuses.lines().map { it.trim() }.filter { it.isNotEmpty() }
    /** pick a status: it shows right now, rotation carries on from it */
    fun pickStatus(i: Int) { statusIdx = i; rotateFrom = System.currentTimeMillis() }

    /** 4-digit code the phone remote needs (made once, random) */
    val pairCode: String get() = p.getString("pair", null) ?: (1000 + java.util.Random().nextInt(9000)).toString().also { p.edit().putString("pair", it).apply() }
    var remoteIp: String get() = p.getString("remote_ip", "")!!; set(v) = p.edit().putString("remote_ip", v).apply()
    var remoteCode: String get() = p.getString("remote_code", "")!!; set(v) = p.edit().putString("remote_code", v).apply()

    // global chat + lil kitty
    var gchatName: String get() = p.getString("gc_name", "")!!; set(v) = p.edit().putString("gc_name", v).apply()
    var gchatOn: Boolean get() = p.getBoolean("gc_on", true); set(v) = p.edit().putBoolean("gc_on", v).apply()
    var gchatNotify: Boolean get() = p.getBoolean("gc_notify", false); set(v) = p.edit().putBoolean("gc_notify", v).apply()
    val gchatSid: String get() = p.getString("gc_sid", null) ?: (1..10).map { "abcdefghijklmnopqrstuvwxyz0123456789".random() }
        .joinToString("").also { p.edit().putString("gc_sid", it).apply() }
    var gchatMuted: Set<String> get() = p.getStringSet("gc_muted", emptySet())!!.toSet(); set(v) = p.edit().putStringSet("gc_muted", v).apply()
    var kittyPats: Int get() = p.getInt("kitty_pats", 0); set(v) = p.edit().putInt("kitty_pats", v).apply()
    var autoUpdate: Boolean get() = p.getBoolean("auto_update", true); set(v) = p.edit().putBoolean("auto_update", v).apply()
    var goalMin: Int get() = p.getInt("goal_min", 60); set(v) = p.edit().putInt("goal_min", v).apply()
    var ears: String get() = p.getString("ears", "cat")!!; set(v) = p.edit().putString("ears", v).apply()
    var kittyName: String get() = p.getString("kitty_name", "Mochi")!!; set(v) = p.edit().putString("kitty_name", v).apply()

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
            Triple("pat_party", "🎉 Pat party", "alert when u get 5 headpats in 30s"),
            Triple("boops", "👃 Boop counter", "counts nose boops (auto-finds the contact)"),
            Triple("jumps", "🐇 Jump counter", "counts every hop"),
            Triple("yap", "🗣️ Yap meter", "how long u've been talking"),
            Triple("zoomies", "👣 Zoomies meter", "distance u walked in VRChat"),
            Triple("height", "📏 Avatar height", "how tall ur avi is"),
            Triple("batt_eta", "⌛ Battery time left", "guesses how long ur Quest will last"),
            Triple("countdown", "🎉 Countdown", "days until ur big day"),
            Triple("today", "🥽 VR today", "how long u've been in VR today"),
            Triple("streak", "🔥 VR streak", "days in a row u've played"),
            Triple("quote", "💭 Cute quote", "a new sweet quote every hour"),
            Triple("milestones", "🏆 VR milestones", "celebrates every hour in VR"),
            Triple("mute_nudge", "🔇 Still-muted nudge", "reminds u after 10 min muted"),
            Triple("eye_break", "👀 Eye break", "20-20-20 rule for tired eyes"),
            Triple("posture", "🧍 Posture check", "sit up straight nudges"),
            Triple("bedtime", "🌙 Bedtime alert", "gentle nudge at ur bedtime"),
            Triple("combo", "💥 Pat combo", "combo meter for back-to-back pats + big alerts"),
            Triple("vibe", "🕺 Vibe meter", "chillin / vibing / vibing hard, from how much u move"),
            Triple("goal", "🎯 Daily VR goal", "progress to ur daily VR time goal"),
            Triple("fortune", "🍀 Lucky paw", "a cute fortune every day"),
            Triple("chime", "🔔 Hourly chime", "a soft notification every hour"),
            Triple("ram_alert", "🧠 Low memory alert", "warns u when the Quest is almost out of RAM"),
            Triple("hot_alert", "🔥 Too hot alert", "warns u when ur headset is cooking (42°C+)"),
            Triple("batt_alerts", "🔋 Battery steps", "a heads up at 50%, 30% and 15%"),
            // ---- v0.9.0
            Triple("water", "🥤 Water tracker", "tap 💧 sip on Home for every sip, shows today's count"),
            Triple("mood", "😊 Mood", "ur mood in the chatbox, change it from Home"),
            Triple("compliment", "💖 Compliments", "a sweet note in ur chatbox + a pop-up every 30 min"),
            Triple("clock2", "🌏 2nd clock", "a friend's time zone next to urs"),
            Triple("steps", "🚶 Step counter", "steps walked in VRChat this session"),
            Triple("swaps", "👗 Avatar swaps", "how many avis u tried today"),
            Triple("pat_goal", "🏅 Headpat goal", "daily headpat goal with a big alert when u hit it"),
            Triple("speed", "💨 Speedometer", "how fast u're moving rn"),
            Triple("afk_recap", "📋 AFK recap", "a lil session recap when u take the headset off"),
            Triple("dance", "💃 Dance party", "notices when u're dancing"),
            Triple("play_limit", "⏰ Playtime check", "gentle nudge after a few hours in VR"),
            Triple("charge", "🔌 Charge reminder", "AFK + low battery? reminds u to plug in"),
            Triple("quiet", "🌙 Quiet hours", "no pop-ups at night (warnings still show)"),
            Triple("batt_saver", "🪫 Battery saver", "under 20%: chatbox updates slower + ping/weather pause"),
            Triple("talking", "🎙️ Talking dot", "shows 🎙️ while u're talking"),
        )
        /** category for each mod (Mods tab filter) */
        val CATS = listOf("all" to "✨ all", "new" to "🆕 new", "chat" to "💬 chatbox", "alert" to "🔔 alerts", "comfy" to "😌 comfy", "fun" to "🎉 fun")
        val NEW = setOf("water", "mood", "compliment", "clock2", "steps", "swaps", "pat_goal", "speed", "afk_recap", "dance",
            "play_limit", "charge", "quiet", "batt_saver", "talking")
        fun catOf(k: String) = when (k) {
            "pat_party", "milestones", "mute_nudge", "chime", "ram_alert", "hot_alert", "batt_alerts", "afk_recap", "charge", "lowbatt" -> "alert"
            "eye_break", "posture", "bedtime", "hydrate", "quiet", "play_limit", "batt_saver" -> "comfy"
            "kaomoji", "quote", "fortune", "vibe", "combo", "compliment", "mood", "dance" -> "fun"
            else -> "chat"
        }
        val MOODS = listOf("😊 happy", "😴 sleepy", "🥰 cuddly", "😎 chillin", "🤪 chaotic", "🥺 need hugs", "🎉 hyped", "🤫 quiet mode")
        val COMPLIMENTS = listOf("ur avatar looks so good today", "u make every instance cozier", "ur laugh is contagious",
            "u're doing amazing, fr", "ur vibe is immaculate", "someone is glad u're here rn", "u deserve all the headpats",
            "u're a good friend", "ur outfit? 10/10", "proud of u :3", "u light up the room", "u matter <3")
        val QUOTES = listOf("u are so loved <3", "stay hydrated, stay fluffy", "be the headpat u wish to see", "tail wags only",
            "chaos but make it cute", "small steps still count", "u matter more than u know", "nap later, vibe now",
            "everyone deserves a hug", "being silly is a lifestyle", "kindness is free, spread it", "ur doing amazing")
        val DEFAULT_ON = setOf("status", "time", "battery", "song", "afk", "timer", "pat_party", "milestones", "mute_nudge", "streak", "batt_saver")
    }
}

/** Builds the chatbox text, same idea as chatbox.py on PC (max 144 chars, 9 lines). */
object Chatbox {
    const val LIMIT = 144
    const val MAX_LINES = 9
    var sessionStart = System.currentTimeMillis()

    private val CUTE = mapOf("status" to "✨", "time" to "⏰", "battery" to "🔋", "session" to "⏱️", "song" to "🎵",
        "afk" to "💤", "wifi" to "📶", "ping" to "🏓", "timer" to "⏳", "weather" to "🌤️", "headpats" to "🐾", "muted" to "🔇",
        "temp" to "🌡️", "ram" to "🧠", "lowbatt" to "🪫", "hydrate" to "💧", "counter" to "🔢", "date" to "📅",
        "boops" to "👃", "jumps" to "🐇", "yap" to "🗣️", "zoomies" to "👣", "height" to "📏", "batt_eta" to "⌛",
        "countdown" to "🎉", "today" to "🥽", "streak" to "🔥", "quote" to "💭", "combo" to "💥", "vibe" to "🕺",
        "goal" to "🎯", "fortune" to "🍀",
        "water" to "🥤", "mood" to "", "compliment" to "💖", "clock2" to "🌏", "steps" to "🚶", "swaps" to "👗",
        "pat_goal" to "🏅", "speed" to "💨")
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

    /** which status is showing rn: the one u picked, then rotating on from it (not jumping to a random one) */
    fun statusIndex(s: Settings, now: Long): Int {
        val list = s.statusList()
        if (list.isEmpty()) return -1
        val sel = Math.floorMod(s.statusIdx, list.size)
        if (!s.rotate || list.size < 2) return sel
        val steps = (maxOf(0L, now - s.rotateFrom) / 1000 / maxOf(5, s.rotateSec)).toInt()
        return (sel + steps) % list.size
    }

    fun currentStatus(s: Settings, now: Long): String = s.statusList().getOrNull(statusIndex(s, now)) ?: ""

    private fun fmt(sec: Long) = "${sec / 60}:${"%02d".format(sec % 60)}"

    fun songBar(pos: Long, dur: Long, width: Int = 11): String? {
        if (dur <= 0) return null
        val k = (pos.toDouble() / dur).coerceIn(0.0, 1.0)
        val i = Math.round(k * (width - 1)).toInt()
        return "${fmt(pos)} " + "━".repeat(i) + "◉" + "─".repeat(width - 1 - i) + " ${fmt(dur)}"
    }

    private fun short(t: String, n: Int) = if (t.length <= n) t else t.substring(0, n - 1).trimEnd() + "…"

    private fun dur(sec: Long) = if (sec >= 3600) "${sec / 3600}h ${"%02d".format(sec % 3600 / 60)}m" else "${sec / 60}m"

    fun countdownText(s: Settings, now: Long = System.currentTimeMillis()): String? {
        val target = try { SimpleDateFormat("yyyy-MM-dd", Locale.US).parse(s.countdownDate)?.time } catch (_: Exception) { null } ?: return null
        val days = Math.floorDiv(target - now, 86_400_000L) + 1
        val name = s.countdownName.ifBlank { "the big day" }
        return when { days > 1 -> "$name in ${days}d"; days == 1L -> "$name is tomorrow!!"; days == 0L -> "$name is TODAY!!"; else -> null }
    }

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
        if (s.line("batt_eta")) QuestMods.batteryEta(ctx)?.let { row += tag("batt_eta", it) }
        if (row.isNotEmpty()) lines += row.joinToString("  ")
        val vr = mutableListOf<String>()
        if (s.line("today") && s.vrTodayS >= 60) vr += tag("today", dur(s.vrTodayS) + " today")
        if (s.line("streak") && s.vrStreak > 1) vr += tag("streak", "${s.vrStreak} day streak")
        if (vr.isNotEmpty()) lines += vr.joinToString("  ")
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
        if (s.line("boops")) extra += tag("boops", "${s.boops} boops")
        if (s.line("jumps")) extra += tag("jumps", "${s.jumps} jumps")
        if (s.line("temp")) QuestMods.tempC(ctx)?.let { c -> extra += tag("temp", if (s.fahrenheit) "${Math.round(c * 9 / 5 + 32)}°F" else "${Math.round(c)}°C") }
        if (s.line("ram")) QuestMods.freeRamGb(ctx)?.let { extra += tag("ram", "%.1fGB free".format(it)) }
        if (extra.isNotEmpty()) lines += extra.joinToString("  ")
        val more = mutableListOf<String>()
        if (s.line("yap")) QuestMods.talkSeconds(now).takeIf { it >= 30 }?.let { more += tag("yap", "yapped ${dur(it)}") }
        if (s.line("zoomies") && s.walkedM >= 1) more += tag("zoomies", (if (QuestMods.zoomies) "ZOOMIES!! " else "") + if (s.walkedM >= 1000) "walked ${"%.2f".format(s.walkedM / 1000)}km" else "walked ${s.walkedM.toInt()}m")
        if (s.line("height")) QuestMods.heightM?.let { h -> val ft = h * 3.28084; more += tag("height", "%.2fm (%d'%d\")".format(h, ft.toInt(), Math.round((ft % 1) * 12).toInt())) }
        if (more.isNotEmpty()) lines += more.joinToString("  ")
        val fun3 = mutableListOf<String>()
        if (s.line("combo") && QuestMods.combo >= 3) fun3 += tag("combo", "pat combo x${QuestMods.combo}")
        if (s.line("vibe")) fun3 += tag("vibe", if (QuestMods.vibe > 60) "vibing hard" else if (QuestMods.vibe > 25) "vibing" else "chillin")
        if (s.line("goal")) fun3 += tag("goal", "goal ${QuestMods.goalPct(s)}%")
        if (fun3.isNotEmpty()) lines += fun3.joinToString("  ")
        val v9 = mutableListOf<String>()
        if (s.line("mood")) v9 += s.mood
        if (s.line("talking") && QuestMods.talking) v9 += "🎙️"
        if (s.line("water")) v9 += tag("water", "${if (s.sipDate == QuestMods.today(now)) s.sips else 0} sips")
        if (s.line("clock2")) v9 += tag("clock2", QuestMods.clock2(s, now))
        if (s.line("steps") && QuestMods.steps(s) > 0) v9 += tag("steps", "${QuestMods.steps(s)} steps")
        if (s.line("swaps") && s.swapDate == QuestMods.today(now) && s.swaps > 0) v9 += tag("swaps", "${s.swaps} avi swaps")
        if (s.line("pat_goal")) v9 += tag("pat_goal", "${QuestMods.patsToday(s, now)}/${s.patGoal} pats")
        if (s.line("speed") && QuestMods.speed >= 0.3f) v9 += tag("speed", "%.1f m/s".format(QuestMods.speed))
        if (v9.isNotEmpty()) lines += v9.joinToString("  ")
        if (s.line("compliment")) lines += tag("compliment", Settings.COMPLIMENTS[((now / 600_000) % Settings.COMPLIMENTS.size).toInt()])
        if (s.line("fortune")) lines += tag("fortune", short(QuestMods.fortune(now), 44))
        if (s.line("countdown")) countdownText(s, now)?.let { lines += tag("countdown", short(it, 40)) }
        if (s.line("quote")) lines += tag("quote", Settings.QUOTES[((now / 3_600_000) % Settings.QUOTES.size).toInt()])
        val al = QuestMods.alertText
        if (al.isNotEmpty() && now - QuestMods.alertAt < 15_000 && (al.startsWith("PAT PARTY") || al.contains("hour") || al.startsWith("headpat goal") || al.startsWith("DANCE"))) lines.add(0, al)
        if (s.line("kaomoji") && lines.isNotEmpty()) {
            lines[lines.size - 1] = lines.last() + " " + KAO[((now / 20000) % KAO.size).toInt()]
        }
        var out = lines.take(MAX_LINES).toMutableList()
        while (out.isNotEmpty() && out.joinToString("\n").length > LIMIT) out = out.dropLast(1).toMutableList()
        return out.joinToString("\n")
    }
}
