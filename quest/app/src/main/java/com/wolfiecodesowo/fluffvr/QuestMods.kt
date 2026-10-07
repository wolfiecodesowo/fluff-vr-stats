package com.wolfiecodesowo.fluffvr

import android.content.Context
import android.net.wifi.WifiManager
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetSocketAddress
import java.net.Socket
import java.net.URL
import java.net.URLEncoder
import java.nio.ByteBuffer
import java.util.concurrent.ConcurrentHashMap

/**
 * Quest-only mods (the PC overlay mods can't run on standalone Quest, so these replace them):
 *  - listens to VRChat's OSC (port 9001): mute state, headpats, ur avatar's parameters
 *  - AFK detection (headset taken off = screen off)
 *  - Wi-Fi signal + ping (great for wireless Quest)
 *  - timer / stopwatch in the chatbox
 *  - weather for ur city
 */
object QuestMods {
    // ---- live state
    @Volatile var muted: Boolean? = null
    @Volatile var avatarId: String = ""
    @Volatile var afkSince: Long = 0L                 // 0 = not AFK
    @Volatile var pingMs: Int? = null
    @Volatile var weather: String? = null
    @Volatile var oscSeen: Long = 0L                  // last time VRChat talked to us
    val params = ConcurrentHashMap<String, Any>()     // every avatar parameter VRChat sent us
    private var patWasOn = false
    private var listener: Thread? = null
    @Volatile private var listening = false

    // ---- OSC listener (VRChat sends to 127.0.0.1:9001 by default)
    fun startListener(ctx: Context) {
        if (listening) return
        listening = true
        listener = Thread {
            var sock: DatagramSocket? = null
            try {
                sock = DatagramSocket(null).apply { reuseAddress = true; soTimeout = 1000; bind(InetSocketAddress(9001)) }
                val buf = ByteArray(4096)
                while (listening) {
                    val pk = DatagramPacket(buf, buf.size)
                    try { sock.receive(pk) } catch (_: java.net.SocketTimeoutException) { continue }
                    try { for (msg in parseAll(pk.data, 0, pk.length)) handle(ctx, msg) } catch (_: Exception) {}
                }
            } catch (_: Exception) {
            } finally {
                sock?.close()
                listening = false
            }
        }.apply { isDaemon = true; start() }
    }

    fun stopListener() { listening = false }

    private fun readString(b: ByteArray, start: Int, len: Int): Pair<String, Int> {
        var end = start
        while (end < len && b[end] != 0.toByte()) end++
        val s = String(b, start, end - start, Charsets.UTF_8)
        var next = end + 1
        while (next % 4 != 0) next++
        return s to next
    }

    /** All messages in a packet (handles OSC bundles too). */
    fun parseAll(b: ByteArray, off: Int, len: Int): List<Pair<String, List<Any>>> {
        val end = off + len
        if (len >= 16 && String(b, off, 7, Charsets.US_ASCII) == "#bundle") {
            val out = mutableListOf<Pair<String, List<Any>>>()
            var i = off + 16
            while (i + 4 <= end) {
                val n = ByteBuffer.wrap(b, i, 4).int
                if (n <= 0 || i + 4 + n > end) break
                out += parseAll(b, i + 4, n)
                i += 4 + n
            }
            return out
        }
        val copy = b.copyOfRange(off, end)
        return listOf(parse(copy, copy.size))
    }

    fun parse(b: ByteArray, len: Int): Pair<String, List<Any>> {
        val (addr, p1) = readString(b, 0, len)
        if (p1 >= len) return addr to emptyList()
        val (tags, p2) = readString(b, p1, len)
        var p = p2
        val args = mutableListOf<Any>()
        for (t in tags.drop(1)) {
            when (t) {
                'i' -> { args += ByteBuffer.wrap(b, p, 4).int; p += 4 }
                'f' -> { args += ByteBuffer.wrap(b, p, 4).float; p += 4 }
                's' -> { val (s, n) = readString(b, p, len); args += s; p = n }
                'T' -> args += true
                'F' -> args += false
            }
        }
        return addr to args
    }

    // ---- contact detection (headpats + boops): finds the param by name, works with bool/int/float contacts
    private val PAT_RE = Regex("(head.?pat|headpat|(^|[_ .-])pat(ted|ting|s)?$|^pat($|s$|ted|ting|[_ .-])|head.?(touch|contact|rub)|(touch|contact|rub).?head|pett?ing|^pets?$|^head$)", RegexOption.IGNORE_CASE)
    private val BOOP_RE = Regex("(boop|nose.?(touch|contact|boop)|(touch|contact).?nose|^nose$)", RegexOption.IGNORE_CASE)
    private val BUILTIN = setOf("VelocityX", "VelocityY", "VelocityZ", "VelocityMagnitude", "AngularY", "Upright",
        "Grounded", "Seated", "AFK", "TrackingType", "VRMode", "MuteSelf", "InStation", "Earmuffs", "IsLocal",
        "Viseme", "Voice", "GestureLeft", "GestureRight", "GestureLeftWeight", "GestureRightWeight",
        "IsOnFriendsList", "AvatarVersion", "ScaleModified", "ScaleFactor", "ScaleFactorInverse", "EyeHeightAsMeters",
        "EyeHeightAsPercent", "IsAnimatorEnabled", "PreviewMode")
    @Volatile var oscMsgs = 0L
    @Volatile var recent: List<String> = emptyList()
    // learn mode: "pat me now" -> whatever avatar param turns on becomes the headpat/boop param
    @Volatile var learnKind: String? = null
    @Volatile var learnUntil = 0L
    @Volatile var learnResult = ""
    private val learnSeen = HashMap<String, Boolean>()
    fun startLearn(kind: String) { learnSeen.clear(); learnKind = kind; learnUntil = System.currentTimeMillis() + 60_000; learnResult = "" }
    fun learnTick(now: Long = System.currentTimeMillis()) {
        if (learnKind != null && now > learnUntil) { learnKind = null; learnResult = "didn't see a contact turn on. is OSC on, and is it in ur Expression Parameters?" }
    }
    private val contact = HashMap<String, Pair<Boolean, Long>>()
    @Volatile var patParam: String? = null
    @Volatile var boopParam: String? = null
    @Volatile var heightM: Double? = null
    @Volatile var seated = false
    private var grounded: Boolean? = null
    private var talkSince = 0L
    @Volatile var talkMs = 0L
    @Volatile private var velX = 0f
    @Volatile private var velZ = 0f
    private var lastMoveTick = 0L
    @Volatile var speed = 0f              // how fast ur avatar moves in VRChat (thumbstick too), m/s

    /** called a few times a second: adds up the distance u moved (VRChat only sends speed when it changes) */
    fun moveTick(s: Settings, now: Long = System.currentTimeMillis()) {
        val last = lastMoveTick
        lastMoveTick = now
        if (last == 0L) return
        val dt = minOf(now - last, 15_000L) / 1000f
        speed = if (seated || now - oscSeen > 30_000) 0f else Math.sqrt((velX * velX + velZ * velZ).toDouble()).toFloat()
        if (speed in 0.3f..15f) s.walkedM = s.walkedM + speed * dt
    }
    val zoomies get() = speed > 3.2f

    // ---- v0.5.1 mods: pat combo, vibe meter, daily goal, lucky paw
    private var lastPats = -1
    private val comboTimes = ArrayList<Long>()
    @Volatile var combo = 0
    @Volatile var vibe = 0f                // 0-100, how much u're moving / dancing
    val LUCKY = listOf("today's luck: ✨ amazing", "lucky paw says: get headpats", "fortune: someone thinks ur cute",
        "today's luck: big cuddle energy", "fortune: a new friend is near", "lucky paw: wear the cute outfit",
        "today's luck: 100% fluff", "fortune: dance like nobody's watching", "lucky paw: drink water, then vibe",
        "today's luck: tail wags incoming", "fortune: ur gonna laugh so hard", "lucky paw: be silly on purpose")
    fun fortune(now: Long = System.currentTimeMillis()): String {
        val day = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US).format(java.util.Date(now))
        return LUCKY[day.sumOf { it.code } % LUCKY.size]
    }
    fun goalPct(s: Settings) = minOf(100, (s.vrTodayS * 100 / 60 / maxOf(10, s.goalMin)).toInt())

    fun newModsTick(ctx: Context, s: Settings, now: Long = System.currentTimeMillis()) {
        val pats = s.headpats + s.boops
        if (lastPats in 0 until pats) repeat(minOf(5, pats - lastPats)) { comboTimes += now }
        lastPats = pats
        comboTimes.removeAll { now - it > 20_000 }
        val c = comboTimes.size
        if (c != combo) {
            combo = c
            if (s.line("combo") && c in listOf(5, 10, 20, 50)) alert(ctx, when (c) { 5 -> "pat combo x5!! :3"; 10 -> "PAT COMBO x10!!! ur so loved"; 20 -> "x20 COMBO?! headpat frenzy"; else -> "x50!!! LEGENDARY PATS" })
        }
        vibe = vibe * 0.9f + minOf(1f, speed / 6f) * 100f * 0.1f
    }
    @Volatile var mutedSince = 0L

    private val kindCache = HashMap<String, String>()
    private var kindKey = ""
    private fun names(v: String) = v.split(",").map { it.trim().lowercase() }.filter { it.isNotEmpty() && it != "auto" }.toSet()
    private fun isContact(name: String, cfg: String, rx: Regex) = name.lowercase() in names(cfg) || rx.containsMatchIn(name)
    private fun contactOn(v: Any, was: Boolean) = when (v) {
        is Boolean -> v; is Int -> v > 0; is Float -> if (was) v > 0.2f else v > 0.5f; else -> false
    }

    fun talkSeconds(now: Long = System.currentTimeMillis()) = (talkMs + if (talkSince > 0) now - talkSince else 0L) / 1000

    private fun handle(ctx: Context, msg: Pair<String, List<Any>>) {
        val (addr, args) = msg
        oscSeen = System.currentTimeMillis()
        val now = oscSeen
        val v = args.firstOrNull() ?: return
        if (addr == "/avatar/change") {
            avatarId = v.toString(); params.clear(); contact.clear(); grounded = null
            patParam = null; boopParam = null; heightM = null; velX = 0f; velZ = 0f; return
        }
        if (!addr.startsWith("/avatar/parameters/")) return
        val name = addr.removePrefix("/avatar/parameters/")
        params[name] = v
        oscMsgs++
        if (name !in BUILTIN && recent.lastOrNull() != name) recent = (recent + name).takeLast(4)
        val s = Settings(ctx)
        val lk = learnKind
        if (lk != null && name !in BUILTIN) {
            learnTick(now)
            val was = learnSeen[name] ?: false
            val on = contactOn(v, was)
            learnSeen[name] = on
            if (on && !was && learnKind != null) {
                if (lk == "pat") s.headpatParam = name else s.boopParam = name
                learnKind = null
                learnResult = "got it!! ${if (lk == "pat") "headpats" else "boops"} = \"$name\" :3"
                alert(ctx, learnResult)
            }
        }
        when (name) {
            "MuteSelf" -> { muted = v == true; mutedSince = if (v == true) (if (mutedSince == 0L) now else mutedSince) else 0L; return }
            "Voice" -> {
                val talking = (v as? Float ?: 0f) > 0.05f
                if (talking && talkSince == 0L) talkSince = now
                else if (!talking && talkSince > 0) { talkMs += now - talkSince; talkSince = 0L }
                return
            }
            "Grounded" -> {
                val g = v == true
                if (grounded == true && !g && !seated) s.jumps = s.jumps + 1
                grounded = g; return
            }
            "Seated", "InStation" -> { seated = v == true; return }
            "EyeHeightAsMeters" -> { (v as? Float)?.let { heightM = Math.round(it * 100) / 100.0 }; return }
            "VelocityX", "VelocityZ" -> {
                (v as? Float)?.let { if (name == "VelocityX") velX = it else velZ = it }
                return
            }
        }
        // classify each param name once (VRChat sends hundreds of updates a second)
        val key = s.headpatParam + "|" + s.boopParam
        if (key != kindKey) { kindKey = key; kindCache.clear() }
        val kindOf = kindCache.getOrPut(name) {
            if (name in BUILTIN) "" else if (isContact(name, s.headpatParam, PAT_RE)) "pat" else if (isContact(name, s.boopParam, BOOP_RE)) "boop" else ""
        }
        if (kindOf.isEmpty()) return
        for ((kind, rx) in listOf("pat" to PAT_RE, "boop" to BOOP_RE)) {
            if (kind == kindOf) {
                val (was, last) = contact[name] ?: (false to 0L)
                val on = contactOn(v, was)
                var l = last
                if (on && !was && now - last > 800) {
                    if (kind == "pat") { s.headpats = s.headpats + 1; onPat(ctx, s, now) } else s.boops = s.boops + 1
                    l = now
                }
                contact[name] = on to l
                if (kind == "pat") patParam = name else boopParam = name
                return
            }
        }
    }

    private val patTimes = ArrayDeque<Long>()
    private fun onPat(ctx: Context, s: Settings, now: Long) {
        while (patTimes.isNotEmpty() && now - patTimes.first() > 30_000) patTimes.removeFirst()
        patTimes.addLast(now)
        if (s.line("pat_party") && patTimes.size >= 5) { patTimes.clear(); alert(ctx, "PAT PARTY!! 5 pats in 30s 🎉") }
    }

    // ---- alerts: shown in the app, as a Quest notification, and on ur phone remote
    @Volatile var alertText = ""
    @Volatile var alertAt = 0L
    fun alert(ctx: Context, text: String) {
        alertText = text; alertAt = System.currentTimeMillis()
        try {
            val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as android.app.NotificationManager
            nm.createNotificationChannel(android.app.NotificationChannel("alerts", "Fluff alerts", android.app.NotificationManager.IMPORTANCE_DEFAULT))
            nm.notify(2, android.app.Notification.Builder(ctx, "alerts").setContentTitle("Fluff VR Stats :3")
                .setContentText(text).setSmallIcon(R.mipmap.ic_launcher).setAutoCancel(true).build())
        } catch (_: Exception) {}
    }

    // ---- battery time left (from how fast it's been draining this session)
    private var battStart: Pair<Long, Int>? = null
    fun batteryEta(ctx: Context): String? {
        val (pct, chg) = Chatbox.battery(ctx) ?: return null
        val now = System.currentTimeMillis()
        val st = battStart
        if (chg || st == null || pct > st.second) { battStart = now to pct; return null }
        val used = st.second - pct
        val mins = (now - st.first) / 60000.0
        if (used < 2 || mins < 5) return null
        val left = (pct / (used / mins)).toLong()
        return if (left >= 60) "~${left / 60}h ${left % 60}m left" else "~${left}m left"
    }

    /** Avatar parameters worth showing as toggles (skips VRChat's built-in ones). */
    fun discovered(): List<Pair<String, String>> {
        val builtin = setOf("VelocityX", "VelocityY", "VelocityZ", "VelocityMagnitude", "AngularY", "Upright",
            "Grounded", "Seated", "AFK", "TrackingType", "VRMode", "MuteSelf", "InStation", "Earmuffs", "IsLocal",
            "Viseme", "Voice", "GestureLeft", "GestureRight", "GestureLeftWeight", "GestureRightWeight",
            "IsOnFriendsList", "AvatarVersion", "ScaleModified", "ScaleFactor", "ScaleFactorInverse", "EyeHeightAsMeters",
            "EyeHeightAsPercent", "IsAnimatorEnabled", "PreviewMode")
        return params.entries.filter { it.key !in builtin && !it.key.contains("/") }
            .map { (k, v) -> k to when (v) { is Boolean -> "bool"; is Int -> "int"; else -> "float" } }
            .sortedBy { it.first.lowercase() }
    }

    // ---- Wi-Fi + ping
    fun wifiBars(ctx: Context): Int? = try {
        val wm = ctx.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        @Suppress("DEPRECATION") val rssi = wm.connectionInfo?.rssi ?: -127
        if (rssi <= -127) null else WifiManager.calculateSignalLevel(rssi, 5)
    } catch (_: Exception) { null }

    fun measurePing() {
        try {
            val t0 = System.nanoTime()
            Socket().use { it.connect(InetSocketAddress("1.1.1.1", 443), 2000) }
            pingMs = ((System.nanoTime() - t0) / 1_000_000).toInt()
        } catch (_: Exception) { pingMs = null }
    }

    // ---- weather (Open-Meteo, free, no key)
    fun fetchWeather(s: Settings) {
        val city = s.city.trim()
        if (city.isEmpty()) { weather = null; return }
        try {
            val geo = JSONObject(URL("https://geocoding-api.open-meteo.com/v1/search?count=1&name=" +
                URLEncoder.encode(city, "UTF-8")).readText())
            val r = geo.optJSONArray("results")?.optJSONObject(0) ?: return
            val unit = if (s.fahrenheit) "fahrenheit" else "celsius"
            val wx = JSONObject(URL("https://api.open-meteo.com/v1/forecast?latitude=${r.getDouble("latitude")}" +
                "&longitude=${r.getDouble("longitude")}&current=temperature_2m,weather_code&temperature_unit=$unit").readText())
            val cur = wx.getJSONObject("current")
            val t = Math.round(cur.getDouble("temperature_2m"))
            weather = "$t°${if (s.fahrenheit) "F" else "C"} ${sky(cur.optInt("weather_code"))}"
        } catch (_: Exception) {
        }
    }

    private fun sky(code: Int) = when (code) {
        0 -> "clear"; 1, 2 -> "partly cloudy"; 3 -> "cloudy"; 45, 48 -> "foggy"
        in 51..57 -> "drizzle"; in 61..67, in 80..82 -> "rain"; in 71..77, 85, 86 -> "snow"
        in 95..99 -> "storms"; else -> ""
    }

    // ---- headset temp + memory
    fun tempC(ctx: Context): Double? = try {
        val i = ctx.registerReceiver(null, android.content.IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED))
        val t = i?.getIntExtra(android.os.BatteryManager.EXTRA_TEMPERATURE, -1000) ?: -1000
        if (t <= -1000) null else t / 10.0
    } catch (_: Exception) { null }

    fun freeRamGb(ctx: Context): Double? = try {
        val am = ctx.getSystemService(Context.ACTIVITY_SERVICE) as android.app.ActivityManager
        val mi = android.app.ActivityManager.MemoryInfo().also { am.getMemoryInfo(it) }
        mi.availMem / 1_073_741_824.0
    } catch (_: Exception) { null }

    // ---- timer / stopwatch text
    fun timerText(s: Settings, now: Long): String? {
        if (s.timerEnd > 0) {
            val left = (s.timerEnd - now) / 1000
            return if (left > 0) "${left / 60}:${"%02d".format(left % 60)} left" else "time's up!!"
        }
        if (s.stopwatchStart > 0) {
            val up = (now - s.stopwatchStart) / 1000
            return if (up >= 3600) "${up / 3600}:${"%02d".format(up % 3600 / 60)}:${"%02d".format(up % 60)}"
            else "${up / 60}:${"%02d".format(up % 60)}"
        }
        return null
    }
}
