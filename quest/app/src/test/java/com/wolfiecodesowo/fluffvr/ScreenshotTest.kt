package com.wolfiecodesowo.fluffvr

import android.graphics.Bitmap
import android.graphics.Canvas
import android.view.View
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import java.io.File
import java.io.FileOutputStream

/**
 * Renders every tab to PNGs in quest/screens/ so the look can be checked without a headset:
 *   gradlew testDebugUnitTest --tests "*ScreenshotTest*"
 * "quest" = the Quest's landscape window, "phone" = a phone in portrait (the remote).
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [33])
class ScreenshotTest {
    private val out = File(System.getProperty("user.dir"), "../screens").apply { mkdirs() }

    private fun shoot(name: String, tabs: List<String>) {
        val ctl = Robolectric.buildActivity(MainActivity::class.java).setup()
        val act = ctl.get()
        val tabField = MainActivity::class.java.getDeclaredField("tab").apply { isAccessible = true }
        val build = MainActivity::class.java.getDeclaredMethod("build").apply { isAccessible = true }
        for (t in tabs) {
            tabField.set(act, t)
            build.invoke(act)
            shadowOf(android.os.Looper.getMainLooper()).idle()
            val root: View = act.window.decorView.rootView
            val w = act.resources.displayMetrics.widthPixels
            val h = act.resources.displayMetrics.heightPixels
            root.measure(View.MeasureSpec.makeMeasureSpec(w, View.MeasureSpec.EXACTLY),
                View.MeasureSpec.makeMeasureSpec(h, View.MeasureSpec.EXACTLY))
            root.layout(0, 0, w, h)
            val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
            root.draw(Canvas(bmp))
            FileOutputStream(File(out, "${name}_${t.lowercase().replace("<3", "thanks")}.png")).use {
                bmp.compress(Bitmap.CompressFormat.PNG, 100, it)
            }
        }
        ctl.pause().stop().destroy()
    }

    private val ALL = listOf("Home", "Chatbox", "Mods", "Body", "Cam", "Global", "Avatar", "Music", "Remote", "Settings", "Thanks")

    @Test @Config(qualifiers = "w1024dp-h640dp-land-mdpi")
    fun quest() = shoot("quest", ALL)

    @Test @Config(qualifiers = "w400dp-h860dp-port-xhdpi")
    fun phone() = shoot("phone", listOf("Home", "Body", "Mods"))
}
