package com.wolfiecodesowo.fluffvr

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.BroadcastReceiver
import android.content.Intent
import android.content.IntentFilter
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.PowerManager

/**
 * Runs in the background (as a "foreground service" so the Quest doesn't pause it)
 * and sends ur chatbox stats to VRChat every few seconds, like the PC app does.
 */
class ChatboxService : Service() {
    private lateinit var thread: HandlerThread
    private lateinit var handler: Handler
    private var wake: PowerManager.WakeLock? = null
    private var lastText = ""
    private var lastSent = 0L

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        running = true
        Chatbox.sessionStart = System.currentTimeMillis()
        startForeground(1, notification())
        wake = (getSystemService(Context.POWER_SERVICE) as PowerManager)
            .newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "fluffvr:chatbox").apply { acquire() }
        thread = HandlerThread("chatbox").also { it.start() }
        handler = Handler(thread.looper)
        handler.post(tick)
        handler.post(slow)
        QuestMods.startListener(this)
        RemoteLink.startServer(this)
        GlobalChat.start(this)
        GlobalChat.onMessage = { m ->
            if (!m.mine && Settings(this).gchatNotify) QuestMods.alert(this, "🌐 ${m.name}: ${m.text}")
        }
        registerReceiver(screen, IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_OFF); addAction(Intent.ACTION_SCREEN_ON); addAction(Intent.ACTION_USER_PRESENT)
        })
    }

    private val tick = object : Runnable {
        override fun run() {
            val s = Settings(this@ChatboxService)
            try { QuestMods.moveTick(s) } catch (_: Exception) {}
            try { QuestMods.newModsTick(this@ChatboxService, s) } catch (_: Exception) {}
            try {
                MusicState.refresh(this@ChatboxService)
                val text = Chatbox.compose(this@ChatboxService, s)
                val now = System.currentTimeMillis()
                // only send when something changed, plus a keep-alive so it doesn't fade out
                if (text.isNotEmpty() && (text != lastText || now - lastSent > 25_000)) {
                    Osc.chatbox(s.host, s.port, text)
                    lastText = text
                    lastSent = now
                    preview = text
                }
            } catch (_: Exception) {
            }
            handler.postDelayed(this, maxOf(2, s.interval) * 1000L)
        }
    }

    /** headset off -> screen off -> AFK */
    private val screen = object : BroadcastReceiver() {
        override fun onReceive(c: Context?, i: Intent?) {
            when (i?.action) {
                Intent.ACTION_SCREEN_OFF -> if (QuestMods.afkSince == 0L) QuestMods.afkSince = System.currentTimeMillis()
                else -> QuestMods.afkSince = 0L
            }
        }
    }

    private var lastVrTick = System.currentTimeMillis()
    private var lastEye = System.currentTimeMillis()
    private var lastPosture = System.currentTimeMillis()
    private var milestone = 0
    private var muteWarned = false
    private var bedNight = ""
    private var goalDay = ""
    private var chimeHour = -1
    private var lastRamAlert = 0L
    private var lastHotAlert = 0L
    private var battStep = 101

    /** VR today + streak, milestones and gentle reminders (runs every 15s) */
    private fun reminders(s: Settings) {
        val now = System.currentTimeMillis()
        val today = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US).format(java.util.Date(now))
        if (s.vrDate != today) {
            val yday = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US).format(java.util.Date(now - 86_400_000))
            s.vrStreak = if (s.vrDate == yday) s.vrStreak + 1 else 1
            s.vrDate = today; s.vrTodayS = 0
        }
        s.vrTodayS = s.vrTodayS + (now - lastVrTick) / 1000
        lastVrTick = now
        val hrs = ((now - Chatbox.sessionStart) / 3_600_000).toInt()
        if (s.line("milestones") && hrs > milestone) { milestone = hrs; QuestMods.alert(this, "$hrs hour${if (hrs > 1) "s" else ""} in VR!! 🎉") }
        if (s.line("eye_break")) { if (now - lastEye > maxOf(5, s.eyeMin) * 60_000L) { lastEye = now; QuestMods.alert(this, "eye break! look at something far away for 20 secs 👀") } } else lastEye = now
        if (s.line("posture")) { if (now - lastPosture > maxOf(5, s.postureMin) * 60_000L) { lastPosture = now; QuestMods.alert(this, "posture check!! sit up tall + roll ur shoulders :3") } } else lastPosture = now
        if (s.line("mute_nudge")) {
            val ms = QuestMods.mutedSince
            if (QuestMods.muted == true && ms > 0 && now - ms > 10 * 60_000) { if (!muteWarned) { muteWarned = true; QuestMods.alert(this, "ur still muted! (10+ min) just a heads up") } }
            else muteWarned = false
        }
        if (s.line("goal") && QuestMods.goalPct(s) >= 100 && goalDay != today) { goalDay = today; QuestMods.alert(this, "daily goal done!! ${s.goalMin} min in VR today 🎯") }
        val cal = java.util.Calendar.getInstance()
        if (s.line("chime") && cal.get(java.util.Calendar.MINUTE) == 0 && chimeHour != cal.get(java.util.Calendar.HOUR_OF_DAY)) {
            chimeHour = cal.get(java.util.Calendar.HOUR_OF_DAY)
            QuestMods.alert(this, "it's ${java.text.SimpleDateFormat("h a", java.util.Locale.getDefault()).format(java.util.Date(now))} ~ ding!")
        }
        if (s.line("ram_alert")) QuestMods.freeRamGb(this)?.let { if (it < 0.6 && now - lastRamAlert > 600_000) { lastRamAlert = now; QuestMods.alert(this, "Quest is almost out of memory (${"%.1f".format(it)} GB free)! close other apps") } }
        if (s.line("hot_alert")) QuestMods.tempC(this)?.let { if (it >= 42 && now - lastHotAlert > 600_000) { lastHotAlert = now; QuestMods.alert(this, "ur headset is toasty (${Math.round(it)}°C)! take a lil break") } }
        if (s.line("batt_alerts")) Chatbox.battery(this)?.let { (p, chg) ->
            if (chg) battStep = 101
            else for (step in listOf(50, 30, 15)) if (p <= step && battStep > step) { battStep = step; QuestMods.alert(this, "battery at $p% 🔋"); break }
        }
        if (s.line("bedtime")) {
            val parts = s.bedtime.split(":").mapNotNull { it.toIntOrNull() }
            if (parts.size >= 2) {
                val c = java.util.Calendar.getInstance()
                val since = ((c.get(java.util.Calendar.HOUR_OF_DAY) * 60 + c.get(java.util.Calendar.MINUTE) - (parts[0] * 60 + parts[1])) % 1440 + 1440) % 1440
                val night = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.US).format(java.util.Date(now - 12 * 3_600_000))
                if (since < 240 && bedNight != night) { bedNight = night; QuestMods.alert(this, "it's late... bedtime soon? sleepy fluffs need rest 💤") }
            }
        }
    }

    /** slower stuff: ping every 15s, weather every 15 min */
    private var lastWeather = 0L
    private val slow = object : Runnable {
        override fun run() {
            val s = Settings(this@ChatboxService)
            try { reminders(s) } catch (_: Exception) {}
            if (s.line("ping")) QuestMods.measurePing()
            if (s.line("weather") && System.currentTimeMillis() - lastWeather > 15 * 60_000) {
                lastWeather = System.currentTimeMillis()
                QuestMods.fetchWeather(s)
            }
            handler.postDelayed(this, 15_000)
        }
    }

    private fun notification(): Notification {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.createNotificationChannel(NotificationChannel("chatbox", "Chatbox stats", NotificationManager.IMPORTANCE_LOW))
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE)
        return Notification.Builder(this, "chatbox")
            .setContentTitle("Fluff VR Stats :3")
            .setContentText("sending ur chatbox stats to VRChat")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(open)
            .setOngoing(true)
            .build()
    }

    override fun onDestroy() {
        running = false
        try { unregisterReceiver(screen) } catch (_: Exception) {}
        QuestMods.stopListener()
        RemoteLink.stopServer()
        handler.removeCallbacksAndMessages(null)
        thread.quitSafely()
        wake?.let { if (it.isHeld) it.release() }
        val s = Settings(this)
        Osc.chatbox(s.host, s.port, "")       // clear the bubble when stopped
        super.onDestroy()
    }

    companion object {
        @Volatile var running = false
        @Volatile var preview = ""

        fun start(ctx: Context) = ctx.startForegroundService(Intent(ctx, ChatboxService::class.java))
        fun stop(ctx: Context) = ctx.stopService(Intent(ctx, ChatboxService::class.java))
    }
}
