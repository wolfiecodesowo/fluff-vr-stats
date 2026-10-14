package com.wolfiecodesowo.fluffvr

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.ParcelUuid
import org.json.JSONArray
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.URL
import java.util.UUID
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * v0.10 Body tab: heart rate, Standable (full-body estimation from VRChat's own OSC), the phone-camera tracker
 * relay, VCam and YouTube search. Same features as the PC app's Body / Cam / YouTube pages.
 */

// ===================================================================================== heart rate ===
object Heart {
    @Volatile var bpm: Int? = null
    @Volatile var lastAt = 0L
    @Volatile var status = "off"
    val history = ArrayDeque<Int>()
    @Volatile var minBpm: Int? = null
    @Volatile var maxBpm: Int? = null
    private var sum = 0L
    private var n = 0
    val found = java.util.concurrent.CopyOnWriteArrayList<Pair<String, String>>()   // (name, address) from a scan
    @Volatile private var running = false
    private var gatt: BluetoothGatt? = null
    private var gattAddr = ""
    private val HR_SERVICE = UUID.fromString("0000180d-0000-1000-8000-00805f9b34fb")
    private val HR_MEASURE = UUID.fromString("00002a37-0000-1000-8000-00805f9b34fb")
    private val CCCD = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    fun bpmNow(): Int? = bpm?.takeIf { System.currentTimeMillis() - lastAt < 8000 }
    fun avg(): Int? = if (n > 0) (sum / n).toInt() else null

    /** Bluetooth Heart Rate Measurement (0x2A37): bit 0 of the flags says 8 or 16 bit bpm */
    fun parseBle(d: ByteArray): Int? {
        if (d.size < 2) return null
        return if (d[0].toInt() and 1 == 1) { if (d.size < 3) null else (d[1].toInt() and 255) or ((d[2].toInt() and 255) shl 8) }
        else d[1].toInt() and 255
    }

    fun got(ctx: Context, v: Int?) {
        if (v == null || v !in 25..250) return
        bpm = v; lastAt = System.currentTimeMillis()
        synchronized(history) { history.addLast(v); while (history.size > 90) history.removeFirst() }
        minBpm = minOf(minBpm ?: v, v); maxBpm = maxOf(maxBpm ?: v, v); sum += v; n++
        val s = Settings(ctx)
        if (s.heartParams) sendParams(s, true)
    }

    private fun sendParams(s: Settings, on: Boolean) {
        val b = if (on) (bpm ?: 0) else 0
        Osc.send(s.host, s.port, "/avatar/parameters/HR", minOf(255, b))
        Osc.send(s.host, s.port, "/avatar/parameters/HeartRate", b)
        Osc.send(s.host, s.port, "/avatar/parameters/HeartRateFloat", minOf(255, b) / 127.5f - 1f)
        Osc.send(s.host, s.port, "/avatar/parameters/HeartRatePercent", minOf(255, b) / 255f)
        Osc.send(s.host, s.port, "/avatar/parameters/isHRConnected", on)
    }

    fun start(ctx: Context) {
        if (running) return
        running = true
        val app = ctx.applicationContext
        Thread {
            var beat = false
            var nextBeat = 0L
            var lastPoll = 0L
            var wasOn = false
            while (running) {
                val s = Settings(app)
                val now = System.currentTimeMillis()
                try {
                    when (s.heartSource) {
                        "pulsoid" -> if (now - lastPoll >= 1000) { lastPoll = now; pollPulsoid(app, s) }
                        "ble" -> ensureBle(app, s)
                        else -> { status = "off"; closeBle() }
                    }
                } catch (e: Exception) { status = "error: ${e.message}".take(90) }
                val on = bpmNow() != null
                if (on && s.heartParams && now >= nextBeat) {      // HeartBeatToggle flips every beat
                    beat = !beat
                    Osc.send(s.host, s.port, "/avatar/parameters/HeartBeatToggle", beat)
                    nextBeat = now + 60_000L / maxOf(30, bpm ?: 60)
                }
                if (wasOn && !on && s.heartParams) sendParams(s, false)
                wasOn = on
                Thread.sleep(100)
            }
        }.apply { isDaemon = true; name = "fluff-heart"; start() }
    }

    private fun pollPulsoid(ctx: Context, s: Settings) {
        val token = s.pulsoidToken.trim()
        if (token.isEmpty()) { status = "paste ur Pulsoid token below"; return }
        val c = URL("https://dev.pulsoid.net/api/v1/data/heart_rate/latest").openConnection() as HttpURLConnection
        c.connectTimeout = 5000; c.readTimeout = 5000
        c.setRequestProperty("Authorization", "Bearer $token")
        try {
            when (c.responseCode) {
                200 -> {
                    val j = JSONObject(c.inputStream.bufferedReader().readText())
                    val at = j.optLong("measured_at", 0L)
                    val v = j.optJSONObject("data")?.optInt("heart_rate", 0) ?: 0
                    if (v > 0 && (at == 0L || System.currentTimeMillis() - at < 15_000)) { got(ctx, v); status = "live (Pulsoid)" }
                    else status = "Pulsoid is on but no heartbeat yet ~ start ur watch/strap"
                }
                401, 403 -> status = "Pulsoid says that token isn't right ~ paste it again"
                404, 412 -> status = "Pulsoid is on but no heartbeat yet ~ start ur watch/strap"
                else -> status = "Pulsoid error ${c.responseCode}"
            }
        } catch (_: Exception) { status = "can't reach Pulsoid (offline?)" } finally { c.disconnect() }
    }

    @SuppressLint("MissingPermission")
    fun scan(ctx: Context, secs: Int = 8) {
        val bt = (ctx.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter
        if (bt == null || !bt.isEnabled) { status = "turn Bluetooth on first"; return }
        val sc = bt.bluetoothLeScanner ?: run { status = "Bluetooth scan isn't available"; return }
        found.clear()
        status = "looking for heart rate devices…"
        val cb = object : ScanCallback() {
            override fun onScanResult(type: Int, r: ScanResult) {
                val a = r.device.address
                if (found.none { it.second == a }) found += ((try { r.device.name } catch (_: SecurityException) { null } ?: "heart rate device") to a)
            }
        }
        try {
            sc.startScan(listOf(ScanFilter.Builder().setServiceUuid(ParcelUuid(HR_SERVICE)).build()),
                ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), cb)
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                try { sc.stopScan(cb) } catch (_: Exception) {}
                status = if (found.isEmpty()) "nothing found ~ turn on ur strap / 'broadcast HR' on ur watch" else "found ${found.size} ~ tap urs"
            }, secs * 1000L)
        } catch (e: SecurityException) { status = "allow Bluetooth for Fluff VR Stats first" }
    }

    @SuppressLint("MissingPermission")
    private fun ensureBle(ctx: Context, s: Settings) {
        val addr = s.bleAddr
        if (addr.isEmpty()) { if (gatt == null) status = "tap 'find my strap', then pick it"; return }
        if (gatt != null && gattAddr == addr) {
            if (bpmNow() == null && status.startsWith("live")) status = "strap connected, waiting for a beat…"
            return
        }
        closeBle()
        val bt = (ctx.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter ?: return
        val dev: BluetoothDevice = try { bt.getRemoteDevice(addr) } catch (_: Exception) { status = "that device address looks wrong"; return }
        status = "connecting to ur strap…"
        gattAddr = addr
        gatt = try {
            dev.connectGatt(ctx, true, object : BluetoothGattCallback() {
                override fun onConnectionStateChange(g: BluetoothGatt, st: Int, ns: Int) {
                    if (ns == BluetoothProfile.STATE_CONNECTED) g.discoverServices()
                    else if (ns == BluetoothProfile.STATE_DISCONNECTED) status = "strap disconnected ~ trying again…"
                }
                override fun onServicesDiscovered(g: BluetoothGatt, st: Int) {
                    val ch = g.getService(HR_SERVICE)?.getCharacteristic(HR_MEASURE) ?: run { status = "that device has no heart rate"; return }
                    g.setCharacteristicNotification(ch, true)
                    ch.getDescriptor(CCCD)?.let { d ->
                        @Suppress("DEPRECATION")
                        d.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                        @Suppress("DEPRECATION") g.writeDescriptor(d)
                    }
                    status = "live (Bluetooth)"
                }
                @Deprecated("Deprecated in Java")
                override fun onCharacteristicChanged(g: BluetoothGatt, ch: BluetoothGattCharacteristic) {
                    @Suppress("DEPRECATION") ch.value?.let { got(ctx, parseBle(it)) }
                }
            })
        } catch (e: SecurityException) { status = "allow Bluetooth for Fluff VR Stats first"; null }
    }

    @SuppressLint("MissingPermission")
    private fun closeBle() {
        try { gatt?.close() } catch (_: Exception) {}
        gatt = null; gattAddr = ""
    }
}

// ============================================================================= tracker math (shared) ===
/** VRChat OSC trackers: Unity space, meters, +Y up, left-handed, euler degrees. docs.vrchat.com/docs/osc-trackers */
object Trackers {
    val SLOT = mapOf("hip" to 1, "foot_l" to 2, "foot_r" to 3, "knee_l" to 4, "knee_r" to 5, "chest" to 6, "elbow_l" to 7, "elbow_r" to 8)

    /** OSC messages for a set of parts: name -> (x, y, z, yaw) */
    fun messages(parts: Map<String, FloatArray>, head: FloatArray?, headYaw: Float?): List<ByteArray> {
        val out = ArrayList<ByteArray>()
        for ((name, v) in parts) {
            val slot = SLOT[name] ?: continue
            out += Osc.message("/tracking/trackers/$slot/position", v[0], v[1], v[2])
            out += Osc.message("/tracking/trackers/$slot/rotation", 0f, v[3], 0f)
        }
        if (head != null) out += Osc.message("/tracking/trackers/head/position", head[0], head[1], head[2])
        if (headYaw != null) out += Osc.message("/tracking/trackers/head/rotation", 0f, headYaw, 0f)
        return out
    }
}

/** planted feet that take a step when the body moves away from them (the "standable" bit) */
class Legs(private val stepDist: Float = 0.22f) {
    private class Foot(var x: Float, var z: Float) { var fx = x; var fz = z; var tx = x; var tz = z; var t = 1f; var lift = 0f }
    private var feet: Array<Foot>? = null
    val ANKLE = 0.07f

    /** hip (x, y, z) in, foot_l / foot_r / knee_l / knee_r out. facing +Z */
    fun update(hx: Float, hy: Float, hz: Float, dt: Float, legLen: Float): Map<String, FloatArray> {
        val stance = 0.11f
        val tgt = arrayOf(floatArrayOf(hx - stance, hz + 0.03f), floatArrayOf(hx + stance, hz + 0.03f))
        val f = feet
        if (f == null || f.indices.any { hypot(f[it].x - tgt[it][0], f[it].z - tgt[it][1]) > 1.2f }) {
            feet = arrayOf(Foot(tgt[0][0], tgt[0][1]), Foot(tgt[1][0], tgt[1][1]))
        }
        val ff = feet!!
        for (i in 0..1) {
            val ft = ff[i]; val other = ff[1 - i]
            if (ft.t < 1f) {
                ft.t = min(1f, ft.t + dt / 0.3f)
                val k = ft.t * ft.t * (3 - 2 * ft.t)
                ft.x = ft.fx + (ft.tx - ft.fx) * k; ft.z = ft.fz + (ft.tz - ft.fz) * k
                ft.lift = sin(Math.PI * ft.t).toFloat() * 0.07f
            } else if (other.t >= 1f) {
                val d = hypot(ft.x - tgt[i][0], ft.z - tgt[i][1])
                val od = hypot(other.x - tgt[1 - i][0], other.z - tgt[1 - i][1])
                if (d > stepDist && d >= od - 0.02f) {
                    ft.fx = ft.x; ft.fz = ft.z
                    ft.tx = tgt[i][0] + (tgt[i][0] - ft.x) * 0.25f; ft.tz = tgt[i][1] + (tgt[i][1] - ft.z) * 0.25f
                    ft.t = 0f
                }
            }
        }
        val out = HashMap<String, FloatArray>()
        for ((i, side) in listOf(0 to "l", 1 to "r")) {
            val ft = ff[i]
            val fy = ANKLE + ft.lift
            out["foot_$side"] = floatArrayOf(ft.x, fy, ft.z, 0f)
            val d = max(1e-3f, sqrt((hx - ft.x) * (hx - ft.x) + (hy - fy) * (hy - fy) + (hz - ft.z) * (hz - ft.z)))
            val bend = sqrt(max(0f, (legLen / 2) * (legLen / 2) - (min(d, legLen) / 2) * (min(d, legLen) / 2)))
            out["knee_$side"] = floatArrayOf((hx + ft.x) / 2, (hy + fy) / 2, (hz + ft.z) / 2 + bend + 0.03f, 0f)
        }
        return out
    }

    fun reset() { feet = null }
}

// ====================================================================== Standable on standalone Quest ===
/**
 * A Quest app can't see ur headset's position while VRChat is open, so this uses what VRChat itself sends
 * over OSC: how fast u move (VelocityX/Z), how upright u are (Upright = crouching), Grounded and Seated.
 * Our head is pinned to VRChat's (the head tracker message lines the spaces up every frame), so the hip
 * follows u, the feet stay planted and take a step when u move. Calibrate FBT in VRChat like normal.
 */
object Standable {
    @Volatile var status = "off"
    @Volatile var rate = 0f
    @Volatile var last: Map<String, FloatArray> = emptyMap()
    @Volatile private var running = false
    private val legs = Legs()
    private var px = 0f
    private var pz = 0f

    fun start(ctx: Context) {
        if (running) return
        running = true
        val app = ctx.applicationContext
        Thread {
            var sock: DatagramSocket? = null
            var t0 = System.nanoTime()
            var count = 0; var rateT = System.currentTimeMillis()
            while (running) {
                val s = Settings(app)
                val now = System.currentTimeMillis()
                val t1 = System.nanoTime()
                val dt = min(0.1f, (t1 - t0) / 1e9f); t0 = t1
                if (!s.standable) {
                    if (status != "off") android.util.Log.i("FluffStandable", "off")
                    status = "off"; legs.reset(); Thread.sleep(250); continue
                }
                // always send (standing trackers are enough for VRChat to offer "Calibrate FBT");
                // VRChat's own OSC (if we hear it) adds walking, crouching + sitting on top
                val hearing = now - QuestMods.oscSeen < 4000
                if (hearing && QuestMods.seated) { status = "sitting ~ resting till u stand up"; Thread.sleep(250); continue }
                val vx = if (hearing) QuestMods.velX.coerceIn(-8f, 8f) else 0f
                val vz = if (hearing) QuestMods.velZ.coerceIn(-8f, 8f) else 0f
                if (abs(vx) + abs(vz) > 0.05f) { px += vx * dt; pz += vz * dt }
                val out = compute(s, px, pz, if (hearing) QuestMods.upright else 1f, dt, now, abs(vx) + abs(vz) > 0.3f)
                last = out
                try {
                    if (sock == null) sock = DatagramSocket()
                    val addr = InetAddress.getByName(s.host)
                    val parts = out.filterKeys { s.trackFull || it in setOf("hip", "foot_l", "foot_r") }
                    for (m in Trackers.messages(parts, out["head"], 0f))
                        sock.send(DatagramPacket(m, m.size, addr, s.port))
                    status = if (hearing) (if (sitting) "live ~ sitting :3" else "live ~ walk, crouch, sit + stand :3")
                        else "sending trackers ~ calibrate FBT in VRChat. (not hearing VRChat's OSC, so walking won't move ur feet yet)"
                } catch (e: Exception) { status = "couldn't send (${e.message})" }
                count++
                if (now - rateT >= 1000) {
                    rate = count * 1000f / (now - rateT); count = 0; rateT = now
                    // shows up in `adb logcat -s FluffStandable` (helps when VRChat won't show Calibrate FBT)
                    if ((now / 1000) % 5 == 0L) android.util.Log.i("FluffStandable", "sending ${rate.toInt()}/s to ${s.host}:${s.port} · " +
                        "hearing VRChat=${now - QuestMods.oscSeen < 4000} · $status")
                }
                Thread.sleep(33)
            }
            sock?.close()
        }.apply { isDaemon = true; name = "fluff-standable"; start() }
    }

    fun stop() { running = false }

    @Volatile var sitting = false
    private var lowSince = 0L

    /**
     * head over (px, pz) -> hip, feet, knees, chest + "head" (where we tell VRChat ur head is).
     * upright = VRChat's Upright (ur head height / standing height): 1 standing, ~0.6 crouching, ~0.5 sitting.
     * low + still for 2s = sitting (hips back, legs out in front), stand up again = back to standing.
     */
    fun compute(s: Settings, hx: Float, hz: Float, upright: Float, dt: Float, now: Long = System.currentTimeMillis(),
                moving: Boolean = false): Map<String, FloatArray> {
        val eye = s.trackHeight * 0.93f
        val up = upright.coerceIn(0.25f, 1.05f)
        val headY = eye * up                       // VRChat pins our head to ur real head, so this has to be ur real height
        val legLen = max(0.3f, eye * 0.57f - 0.07f)
        if (up < 0.68f && !moving) { if (lowSince == 0L) lowSince = now } else lowSince = 0L
        if (up > 0.8f) sitting = false
        else if (lowSince > 0 && now - lowSince > 2000) sitting = true
        val out = HashMap<String, FloatArray>()
        out["head"] = floatArrayOf(hx, headY - 0.09f, hz - 0.06f, 0f)
        if (sitting) {
            // seat under ur hips, thighs forward, shins down to the floor
            val hipY = max(0.15f, headY - eye * 0.36f)
            val hipZ = hz - 0.12f
            val thigh = legLen * 0.5f
            val kneeY = max(0.1f, hipY + 0.04f)
            for ((side, dx) in listOf("l" to -0.12f, "r" to 0.12f)) {
                val kz = hipZ + thigh
                val footZ = kz + max(0f, legLen * 0.5f - kneeY) * 0.6f
                out["knee_$side"] = floatArrayOf(hx + dx, kneeY, kz, 0f)
                out["foot_$side"] = floatArrayOf(hx + dx * 1.1f, legs.ANKLE, footZ, 0f)
            }
            out["hip"] = floatArrayOf(hx, hipY, hipZ, 0f)
            out["chest"] = floatArrayOf(hx, hipY + (headY - hipY) * 0.55f, hipZ + 0.02f, 0f)
            legs.reset()                           // feet re-plant under u when u stand up
            return out
        }
        val crouch = (1f - up).coerceIn(0f, 0.75f)
        val torso = eye * 0.4f
        val hipY = max(0.2f, headY - torso * (1f - crouch * 0.3f))
        val hipZ = hz - 0.07f - crouch * 0.3f     // bum goes back when u crouch
        out["hip"] = floatArrayOf(hx, hipY, hipZ, 0f)
        out.putAll(legs.update(hx, hipY, hipZ + crouch * 0.3f, dt, legLen))   // feet stay under ur head
        out["chest"] = floatArrayOf(hx, hipY + (headY - hipY) * 0.55f, hipZ + 0.05f + crouch * 0.15f, 0f)
        return out
    }
}

// ================================================================ phone camera tracker -> Quest relay ===
/**
 * The phone (TrackerService) sees ur body with its camera and sends VRChat tracker messages to the Quest on
 * UDP 9051, each one starting with "FLT" + the 4-digit pair code. The Quest passes them on to VRChat.
 */
object TrackRelay {
    const val PORT = 9051
    @Volatile var lastAt = 0L
    @Volatile var from = ""
    @Volatile var rate = 0f
    @Volatile private var running = false

    val live get() = System.currentTimeMillis() - lastAt < 2000

    fun start(ctx: Context) {
        if (running) return
        running = true
        val app = ctx.applicationContext
        Thread {
            var sock: DatagramSocket? = null
            var out: DatagramSocket? = null
            var n = 0; var t = System.currentTimeMillis()
            try {
                sock = DatagramSocket(null).apply { reuseAddress = true; soTimeout = 1000; bind(InetSocketAddress(PORT)) }
                out = DatagramSocket()
                val buf = ByteArray(2048)
                while (running) {
                    val pk = DatagramPacket(buf, buf.size)
                    try { sock.receive(pk) } catch (_: java.net.SocketTimeoutException) { continue }
                    if (pk.length < 8 || buf[0] != 'F'.code.toByte() || buf[1] != 'L'.code.toByte() || buf[2] != 'T'.code.toByte()) continue
                    val s = Settings(app)
                    if (String(buf, 3, 4, Charsets.US_ASCII) != s.pairCode) continue
                    out.send(DatagramPacket(buf, 7, pk.length - 7, InetAddress.getByName(s.host), s.port))
                    lastAt = System.currentTimeMillis(); from = pk.address.hostAddress ?: ""
                    n++
                    if (lastAt - t >= 1000) { rate = n * 1000f / (lastAt - t); n = 0; t = lastAt }
                }
            } catch (_: Exception) {
            } finally { sock?.close(); out?.close(); running = false }
        }.apply { isDaemon = true; name = "fluff-track-relay"; start() }
    }

    fun stop() { running = false }

    fun wrap(code: String, osc: ByteArray): ByteArray = "FLT".toByteArray() + code.padStart(4, '0').take(4).toByteArray() + osc
}

/**
 * Turns camera pose landmarks into trackers. Points come in image pixels (x right, y down) with a depth z in
 * the same units; the person faces the camera. Calibrate standing straight so we learn the scale + floor.
 */
class PoseMath(private val heightM: Float) {
    var scale = 0f          // pixels per meter
    var floorY = 0f
    var centerX = 0f
    private val smooth = HashMap<String, FloatArray>()

    fun calibrate(p: Map<String, FloatArray>): Boolean {
        val hl = p["hip_l"] ?: return false; val hr = p["hip_r"] ?: return false
        val al = p["ank_l"] ?: return false; val ar = p["ank_r"] ?: return false
        val leg = (dist(hl, al) + dist(hr, ar)) / 2
        if (leg < 20) return false
        scale = leg / (heightM * 0.47f)
        floorY = (al[1] + ar[1]) / 2
        centerX = (hl[0] + hr[0]) / 2
        smooth.clear()
        return true
    }

    private fun dist(a: FloatArray, b: FloatArray) = hypot(a[0] - b[0], a[1] - b[1])

    /** image point -> Unity meters. u face the camera, so the camera's left is ur right */
    private fun world(p: FloatArray, hipZ: Float) = floatArrayOf(
        -(p[0] - centerX) / scale, (floorY - p[1]) / scale + 0.07f, -(p[2] - hipZ) / scale)

    private fun ema(k: String, v: FloatArray, a: Float = 0.5f): FloatArray {
        val o = smooth[k]
        val r = if (o == null) v else FloatArray(v.size) { o[it] + (v[it] - o[it]) * a }
        smooth[k] = r
        return r
    }

    /** returns parts (x, y, z, yaw) + head position, or null if we can't see enough */
    fun trackers(p: Map<String, FloatArray>, full: Boolean): Pair<Map<String, FloatArray>, FloatArray>? {
        if (scale <= 0f && !calibrate(p)) return null
        val hl = p["hip_l"] ?: return null; val hr = p["hip_r"] ?: return null
        val hipZ = (hl[2] + hr[2]) / 2
        fun w(name: String) = p[name]?.let { world(it, hipZ) }
        val wl = w("hip_l")!!; val wr = w("hip_r")!!
        val hip = floatArrayOf((wl[0] + wr[0]) / 2, (wl[1] + wr[1]) / 2, (wl[2] + wr[2]) / 2)
        val hipYaw = Math.toDegrees(atan2(-(wr[2] - wl[2]).toDouble(), (wr[0] - wl[0]).toDouble())).toFloat()
        val out = HashMap<String, FloatArray>()
        out["hip"] = ema("hip", floatArrayOf(hip[0], hip[1], hip[2], hipYaw))
        for ((part, ank, toe) in listOf(Triple("foot_l", "ank_l", "toe_l"), Triple("foot_r", "ank_r", "toe_r"))) {
            val a = w(ank) ?: continue
            var yaw = hipYaw
            w(toe)?.let { t -> if (hypot(t[0] - a[0], t[2] - a[2]) > 0.04f) yaw = Math.toDegrees(atan2((t[0] - a[0]).toDouble(), (t[2] - a[2]).toDouble())).toFloat() }
            out[part] = ema(part, floatArrayOf(a[0], max(0.07f, a[1]), a[2], yaw))
        }
        if (full) {
            for ((part, lm) in listOf("knee_l" to "knee_l", "knee_r" to "knee_r", "elbow_l" to "el_l", "elbow_r" to "el_r")) {
                w(lm)?.let { out[part] = ema(part, floatArrayOf(it[0], it[1], it[2], hipYaw)) }
            }
            val sl = w("sh_l"); val sr = w("sh_r")
            if (sl != null && sr != null) out["chest"] = ema("chest", floatArrayOf(
                hip[0] + ((sl[0] + sr[0]) / 2 - hip[0]) * 0.6f, hip[1] + ((sl[1] + sr[1]) / 2 - hip[1]) * 0.6f,
                hip[2] + ((sl[2] + sr[2]) / 2 - hip[2]) * 0.6f, hipYaw))
        }
        // head: between the ears (falls back to the nose), a lil lower = the head bone VRChat lines up with
        val el = w("ear_l"); val er = w("ear_r"); val nose = w("nose")
        val head = when {
            el != null && er != null -> floatArrayOf((el[0] + er[0]) / 2, (el[1] + er[1]) / 2 - 0.05f, (el[2] + er[2]) / 2)
            nose != null -> floatArrayOf(nose[0], nose[1] - 0.08f, nose[2] - 0.06f)
            else -> return null
        }
        return out to ema("head", head)
    }
}

// ========================================================================================== VCam ===
/** VRChat's camera over OSC (VRChat 2025.3+): same endpoints as the PC Cam tab */
object VCam {
    val MODES = listOf(1 to "photo", 2 to "stream", 3 to "emoji", 4 to "multi", 5 to "print", 6 to "drone")
    val TOGGLES = listOf("LookAtMe" to "look at me", "SmoothMovement" to "smooth", "Flying" to "flying",
        "GreenScreen" to "green screen", "Lock" to "lock", "LocalPlayer" to "show me", "RemotePlayer" to "show others",
        "Environment" to "show world", "ShowUIInCamera" to "show UI", "AutoLevelRoll" to "auto level")
    val on = HashMap<String, Boolean>()

    fun send(s: Settings, name: String, v: Any) = Osc.send(s.host, s.port, "/usercamera/$name", v)
    fun mode(s: Settings, m: Int) { s.vcamMode = m; send(s, "Mode", m) }
    fun toggle(s: Settings, name: String) { val v = !(on[name] ?: false); on[name] = v; send(s, name, v) }
    fun zoom(s: Settings, step: Float) { s.vcamZoom = (s.vcamZoom + step).coerceIn(20f, 150f); send(s, "Zoom", s.vcamZoom) }
}

// ================================================================================ YouTube search ===
/** YouTube search with no key or account: asks YouTube's own website search like a browser does */
object YouTube {
    data class Video(val id: String, val title: String, val channel: String, val length: String, val views: String) {
        val url get() = "https://www.youtube.com/watch?v=$id"
    }
    @Volatile var query = ""
    @Volatile var status = ""
    @Volatile var busy = false
    @Volatile var results: List<Video> = emptyList()
    val thumbs = java.util.concurrent.ConcurrentHashMap<String, Bitmap>()
    @Volatile var version = 0

    private fun txt(o: JSONObject?): String {
        if (o == null) return ""
        o.optString("simpleText").takeIf { it.isNotEmpty() }?.let { return it }
        val runs = o.optJSONArray("runs") ?: return ""
        return (0 until runs.length()).joinToString("") { runs.optJSONObject(it)?.optString("text") ?: "" }
    }

    private fun walk(any: Any?, out: MutableList<JSONObject>) {
        when (any) {
            is JSONObject -> {
                any.optJSONObject("videoRenderer")?.let { out += it }
                for (k in any.keys()) if (k != "videoRenderer") walk(any.opt(k), out)
            }
            is JSONArray -> for (i in 0 until any.length()) walk(any.opt(i), out)
        }
    }

    fun parse(json: String, limit: Int = 12): List<Video> {
        val found = ArrayList<JSONObject>()
        walk(JSONObject(json), found)
        val out = ArrayList<Video>()
        for (v in found) {
            val id = v.optString("videoId")
            if (id.isEmpty() || out.any { it.id == id }) continue
            val len = txt(v.optJSONObject("lengthText"))
            out += Video(id, txt(v.optJSONObject("title")), txt(v.optJSONObject("ownerText") ?: v.optJSONObject("longBylineText")),
                len.ifEmpty { "LIVE" }, txt(v.optJSONObject("shortViewCountText") ?: v.optJSONObject("viewCountText")))
            if (out.size >= limit) break
        }
        return out
    }

    fun search(q: String) {
        val query = q.trim()
        if (query.isEmpty() || busy) return
        this.query = query; busy = true; status = "searching…"; version++
        Thread {
            try {
                val c = URL("https://www.youtube.com/youtubei/v1/search?prettyPrint=false").openConnection() as HttpURLConnection
                c.requestMethod = "POST"; c.doOutput = true; c.connectTimeout = 8000; c.readTimeout = 10000
                c.setRequestProperty("Content-Type", "application/json")
                c.setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36")
                val body = JSONObject().put("context", JSONObject().put("client", JSONObject().put("clientName", "WEB")
                    .put("clientVersion", "2.20240101.00.00").put("hl", "en"))).put("query", query)
                c.outputStream.use { it.write(body.toString().toByteArray()) }
                results = parse(c.inputStream.bufferedReader().readText())
                status = if (results.isEmpty()) "no results ~ try other words" else "${results.size} results"
            } catch (_: Exception) { results = emptyList(); status = "couldn't reach YouTube (offline?)" }
            busy = false; version++
            for (r in results) {
                if (thumbs.containsKey(r.id)) continue
                try {
                    URL("https://i.ytimg.com/vi/${r.id}/mqdefault.jpg").openStream().use { st -> BitmapFactory.decodeStream(st)?.let { thumbs[r.id] = it } }
                    version++
                } catch (_: Exception) {}
            }
        }.apply { isDaemon = true; start() }
    }
}
