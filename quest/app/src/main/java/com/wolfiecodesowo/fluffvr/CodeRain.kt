package com.wolfiecodesowo.fluffvr

import android.graphics.Canvas
import android.graphics.ColorFilter
import android.graphics.Paint
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.Drawable
import android.os.Handler
import android.os.Looper

/**
 * Normie Mode wall: falling code behind the whole app (same idea as the PC's coderain.py).
 * Warm terracotta streams; columns near the pointer / finger light up. ~15 fps, a few hundred glyphs a frame,
 * and it stops by itself when the drawable is replaced (rebuild) or the app is paused.
 */
class CodeRain(private val d: Float) : Drawable() {
    private val glyphs = "01{}[]()<>;=+-/&|!?#\$%@:_~^abcdefxyz".toCharArray()
    private val cell = 15f * d
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { typeface = Typeface.MONOSPACE; textSize = 12f * d }
    private val handler = Handler(Looper.getMainLooper())
    private val t0 = System.nanoTime()
    private val tick = object : Runnable {
        override fun run() {
            if (callback == null) return                       // replaced by a rebuild: stop
            if (!paused) invalidateSelf()
            handler.postDelayed(this, 66)
        }
    }

    init { handler.postDelayed(tick, 66) }

    private fun h(a: Int, b: Int): Int { var x = a * 73856093 xor b * 19349663; x = x xor (x ushr 13); return x and 0x7fffffff }

    override fun draw(c: Canvas) {
        val b = bounds
        c.drawColor(0xFF14161B.toInt())
        val cols = (b.width() / cell).toInt() + 1
        val rows = (b.height() / cell).toInt() + 2
        val t = (System.nanoTime() - t0) / 1e9f
        val px = pointerX; val py = pointerY
        for (col in 0 until cols) {
            val x = b.left + col * cell
            val speed = 3f + (h(col, 1) % 600) / 100f             // rows per second
            val len = 8 + h(col, 2) % 16
            val head = ((t * speed + h(col, 3) % 1000) % (rows + len + 6)) - len
            val hot = px >= 0 && Math.abs(x + cell / 2 - px) < 90f * d
            for (k in 0 until len) {
                val row = head - k
                if (row < 0 || row > rows) continue
                val fade = (1f - k.toFloat() / len)
                val a = (fade * fade * (if (hot) 255 else 135)).toInt()
                paint.color = if (k == 0) (a shl 24) or (if (hot) 0xFFEBD2 else 0xF0D7BE)
                    else (a shl 24) or (if (hot) 0xFF8C50 else 0x964E34)
                val ch = glyphs[h(col * 131 + row.toInt(), 5) % glyphs.size]
                c.drawText(ch.toString(), x, b.top + row * cell, paint)
            }
        }
    }

    override fun setAlpha(alpha: Int) {}
    override fun setColorFilter(cf: ColorFilter?) {}
    @Deprecated("Deprecated in Java") override fun getOpacity() = PixelFormat.OPAQUE

    companion object {
        @Volatile var paused = false
        @Volatile var pointerX = -1f
        @Volatile var pointerY = -1f
    }
}
