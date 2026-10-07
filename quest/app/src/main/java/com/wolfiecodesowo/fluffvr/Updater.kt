package com.wolfiecodesowo.fluffvr

import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.net.Uri
import android.os.Build
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Auto-updater for the Quest / phone app.
 * Checks version.json on the website, downloads the new APK in the background, checks it's really
 * Fluff VR Stats + newer, then hands it to Android's installer. Android always asks u to tap
 * "Update" once (apps aren't allowed to install silently), and ur settings stay.
 */
object Updater {
    const val VERSION_URL = "https://wolfiecodesowo.github.io/fluff-vr-stats/quest/version.json"
    const val PAGE = "https://wolfiecodesowo.github.io/fluff-vr-stats/quest/"

    @Volatile var latestName: String? = null
    @Volatile var latestCode = 0L
    @Volatile var apkUrl = ""
    @Volatile var state = "idle"          // idle / checking / downloading / ready / installing / failed / need_permission
    @Volatile var progress = 0             // 0-100 while downloading
    @Volatile var error = ""
    @Volatile private var apkFile: File? = null
    var onChange: (() -> Unit)? = null

    fun myCode(ctx: Context): Long = try {
        @Suppress("DEPRECATION") ctx.packageManager.getPackageInfo(ctx.packageName, 0).longVersionCode
    } catch (_: Exception) { 0L }

    private fun changed() { onChange?.invoke() }

    /** background check; if [autoDownload] and there's a newer one, grabs it right away */
    fun check(ctx: Context, autoDownload: Boolean) {
        val app = ctx.applicationContext
        Thread {
            try {
                state = "checking"
                val j = JSONObject(URL("$VERSION_URL?t=${System.currentTimeMillis() / 60000}").readText())
                latestCode = j.optLong("versionCode")
                latestName = j.optString("versionName", "new")
                apkUrl = j.optString("apk", PAGE + "FluffVRStats-Quest.apk")
                state = "idle"
                if (latestCode > myCode(app)) { changed(); if (autoDownload) download(app) } else latestName = null
            } catch (e: Exception) { state = "idle" }
            changed()
        }.start()
    }

    fun hasUpdate(ctx: Context) = latestName != null && latestCode > myCode(ctx)

    fun download(ctx: Context) {
        if (state == "downloading" || state == "ready") return
        val app = ctx.applicationContext
        state = "downloading"; progress = 0; error = ""; changed()
        Thread {
            try {
                val dir = File(app.cacheDir, "updates").apply { mkdirs() }
                dir.listFiles()?.forEach { it.delete() }
                val f = File(dir, "fluff-update.apk")
                val c = URL(apkUrl).openConnection() as HttpURLConnection
                c.connectTimeout = 15_000; c.readTimeout = 30_000
                val total = c.contentLengthLong
                c.inputStream.use { inp -> f.outputStream().use { out ->
                    val buf = ByteArray(64 * 1024); var got = 0L; var last = -1
                    while (true) {
                        val n = inp.read(buf); if (n < 0) break
                        out.write(buf, 0, n); got += n
                        if (total > 0) { val p = (got * 100 / total).toInt(); if (p != last) { last = p; progress = p; changed() } }
                    }
                } }
                // make sure it's really us + newer before installing anything
                @Suppress("DEPRECATION")
                val info = app.packageManager.getPackageArchiveInfo(f.path, 0)
                if (info == null || info.packageName != app.packageName) throw Exception("that download isn't Fluff VR Stats")
                if (info.longVersionCode <= myCode(app)) throw Exception("already up to date")
                apkFile = f
                state = "ready"
            } catch (e: Exception) {
                state = "failed"; error = e.message ?: "download failed"
            }
            changed()
        }.start()
    }

    /** opens Android's "Update this app?" prompt. returns false if we first need "install unknown apps" permission */
    fun install(ctx: Context): Boolean {
        val f = apkFile ?: return false
        if (Build.VERSION.SDK_INT >= 26 && !ctx.packageManager.canRequestPackageInstalls()) {
            state = "need_permission"; changed()
            try {
                ctx.startActivity(Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:${ctx.packageName}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            } catch (_: Exception) {}
            return false
        }
        state = "installing"; changed()
        Thread {
            try {
                val pi = ctx.packageManager.packageInstaller
                val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
                    .apply { setAppPackageName(ctx.packageName) }
                val id = pi.createSession(params)
                pi.openSession(id).use { s ->
                    s.openWrite("fluff.apk", 0, f.length()).use { out -> f.inputStream().use { it.copyTo(out) }; s.fsync(out) }
                    val flags = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
                    val cb = PendingIntent.getBroadcast(ctx, 7, Intent(ctx, InstallReceiver::class.java), flags)
                    s.commit(cb.intentSender)
                }
            } catch (e: Exception) {
                state = "failed"; error = e.message ?: "install failed"; changed()
            }
        }.start()
        return true
    }
}

/** Android tells us here how the install went (and hands us the "Update?" prompt to show) */
class InstallReceiver : BroadcastReceiver() {
    override fun onReceive(ctx: Context, intent: Intent) {
        when (intent.getIntExtra(PackageInstaller.EXTRA_STATUS, -999)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                @Suppress("DEPRECATION")
                val confirm = intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
                try { ctx.startActivity(confirm?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } catch (_: Exception) {}
            }
            PackageInstaller.STATUS_SUCCESS -> { Updater.state = "idle" }
            else -> {
                Updater.state = "failed"
                Updater.error = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE) ?: "install was cancelled"
                Updater.onChange?.invoke()
            }
        }
    }
}
