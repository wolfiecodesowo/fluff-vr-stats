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
                    try { handle(ctx, parse(pk.data, pk.length)) } catch (_: Exception) {}
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

    /** Returns (address, args) for one OSC message (bundles are skipped, VRChat sends plain messages). */
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

    private fun handle(ctx: Context, msg: Pair<String, List<Any>>) {
        val (addr, args) = msg
        oscSeen = System.currentTimeMillis()
        val v = args.firstOrNull() ?: return
        if (addr == "/avatar/change") {
            avatarId = v.toString(); params.clear(); return
        }
        if (!addr.startsWith("/avatar/parameters/")) return
        val name = addr.removePrefix("/avatar/parameters/")
        params[name] = v
        if (name == "MuteSelf") muted = v == true
        val s = Settings(ctx)
        if (name.equals(s.headpatParam, ignoreCase = true)) {
            val on = when (v) { is Boolean -> v; is Float -> v > 0.5f; is Int -> v > 0; else -> false }
            if (on && !patWasOn) s.headpats = s.headpats + 1
            patWasOn = on
        }
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
