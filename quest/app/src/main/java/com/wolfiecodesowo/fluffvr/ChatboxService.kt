package com.wolfiecodesowo.fluffvr

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
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
    }

    private val tick = object : Runnable {
        override fun run() {
            val s = Settings(this@ChatboxService)
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
