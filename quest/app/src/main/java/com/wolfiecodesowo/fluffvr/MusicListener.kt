package com.wolfiecodesowo.fluffvr

import android.content.ComponentName
import android.content.Context
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.SystemClock
import android.provider.Settings as SysSettings
import android.service.notification.NotificationListenerService

/** What's playing right now (Spotify, YouTube Music, anything with media controls). */
object MusicState {
    data class Snap(val title: String, val artist: String, val playing: Boolean,
                    val pos: Long, val duration: Long, val at: Long) {
        fun position(): Long = if (playing) pos + (SystemClock.elapsedRealtime() - at) / 1000 else pos
    }

    @Volatile private var snap = Snap("", "", false, 0, 0, 0)
    @Volatile var controller: MediaController? = null

    fun snapshot() = snap

    fun update(c: MediaController?) {
        controller = c
        if (c == null) { snap = Snap("", "", false, 0, 0, 0); return }
        val md: MediaMetadata? = c.metadata
        val st: PlaybackState? = c.playbackState
        snap = Snap(
            md?.getString(MediaMetadata.METADATA_KEY_TITLE) ?: "",
            md?.getString(MediaMetadata.METADATA_KEY_ARTIST) ?: "",
            st?.state == PlaybackState.STATE_PLAYING,
            (st?.position ?: 0L) / 1000,
            (md?.getLong(MediaMetadata.METADATA_KEY_DURATION) ?: 0L) / 1000,
            st?.lastPositionUpdateTime ?: SystemClock.elapsedRealtime()
        )
    }

    fun hasAccess(ctx: Context): Boolean {
        val flat = SysSettings.Secure.getString(ctx.contentResolver, "enabled_notification_listeners") ?: return false
        return flat.contains(ctx.packageName)
    }

    /** Re-reads the active music session. Needs notification access (optional). */
    fun refresh(ctx: Context) {
        if (!hasAccess(ctx)) return
        try {
            val msm = ctx.getSystemService(Context.MEDIA_SESSION_SERVICE) as MediaSessionManager
            val list = msm.getActiveSessions(ComponentName(ctx, MusicListener::class.java))
            val playing = list.firstOrNull { it.playbackState?.state == PlaybackState.STATE_PLAYING }
            update(playing ?: list.firstOrNull())
        } catch (_: SecurityException) {
        } catch (_: Exception) {
        }
    }

    fun command(cmd: String) {
        val t = controller?.transportControls ?: return
        when (cmd) {
            "play_pause" -> if (snap.playing) t.pause() else t.play()
            "next" -> t.skipToNext()
            "prev" -> t.skipToPrevious()
        }
    }
}

/** Android only lets apps read media sessions if they're a notification listener. */
class MusicListener : NotificationListenerService()
