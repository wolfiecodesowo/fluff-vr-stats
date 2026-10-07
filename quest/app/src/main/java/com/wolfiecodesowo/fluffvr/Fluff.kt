package com.wolfiecodesowo.fluffvr

import android.graphics.Canvas
import android.graphics.ColorFilter
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.RectF
import android.graphics.drawable.Drawable

/**
 * Hand-inked furry card (same look as the PC menu): thick ink outline, little fur tufts poking out,
 * optional ears on top. Content should be padded by [insetTop]/[insetSide]/[insetBottom].
 */
class FluffDrawable(
    private val fill: Int, private val ink: Int, private val inner: Int, private val radius: Float,
    private val d: Float, private val ears: String = "none", private val tufts: Boolean = true, private val seed: Int = 7,
) : Drawable() {
    val earH = if (ears == "none") 0f else 13 * d
    val insetTop get() = (earH + 3 * d).toInt()
    val insetSide get() = (6 * d).toInt()
    val insetBottom get() = ((if (tufts) 8 else 4) * d).toInt()

    private val pFill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = fill; style = Paint.Style.FILL }
    private val pInk = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ink; style = Paint.Style.STROKE; strokeWidth = 3.2f * d; strokeJoin = Paint.Join.ROUND
    }
    private val pInner = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = inner; style = Paint.Style.FILL }

    override fun draw(c: Canvas) {
        val b = bounds
        val r = RectF(b.left + insetSide.toFloat(), b.top + insetTop.toFloat(), b.right - insetSide.toFloat(), b.bottom - insetBottom.toFloat())
        val shapes = ArrayList<Path>()
        val rr = minOf(radius, r.height() / 2)
        shapes += Path().apply { addRoundRect(r, rr, rr, Path.Direction.CW) }
        val rnd = java.util.Random((seed * 31 + b.width() * 7 + b.height()).toLong())
        if (tufts) {
            // tuft on the bottom edge + one on a side
            val bx = r.left + rr + rnd.nextFloat() * (r.width() * 0.35f)
            for (k in 0 until 3) {
                val x = bx + k * 7 * d
                shapes += Path().apply { moveTo(x - 4 * d, r.bottom - 3 * d); lineTo(x + 4 * d, r.bottom - 3 * d)
                    lineTo(x + (rnd.nextFloat() - 0.5f) * 4 * d, r.bottom + (4 + rnd.nextFloat() * 3) * d); close() }
            }
            if (r.height() > 70 * d) {
                val sy = r.top + r.height() * (0.35f + rnd.nextFloat() * 0.3f)
                val right = rnd.nextBoolean()
                val ex = if (right) r.right else r.left
                val sg = if (right) 1 else -1
                for (k in 0 until 2) {
                    val y = sy + k * 7 * d
                    shapes += Path().apply { moveTo(ex - sg * 3 * d, y - 4 * d); lineTo(ex - sg * 3 * d, y + 4 * d)
                        lineTo(ex + sg * (5 + rnd.nextFloat() * 3) * d, y + 1 * d); close() }
                }
            }
        }
        val innerEars = ArrayList<Path>()
        if (ears != "none") {
            val s = earH
            for ((side, cx) in listOf(-1 to r.left + s * 1.6f, 1 to r.right - s * 1.6f)) {
                when (ears) {
                    "bunny" -> {
                        val w = s * 0.5f
                        shapes += Path().apply { addOval(RectF(cx - w, r.top - s * 1.1f, cx + w, r.top + s * 0.6f), Path.Direction.CW) }
                        innerEars += Path().apply { addOval(RectF(cx - w * 0.45f, r.top - s * 0.85f, cx + w * 0.45f, r.top + s * 0.1f), Path.Direction.CW) }
                    }
                    "bear" -> {
                        shapes += Path().apply { addCircle(cx, r.top, s * 0.75f, Path.Direction.CW) }
                        innerEars += Path().apply { addCircle(cx, r.top + s * 0.05f, s * 0.38f, Path.Direction.CW) }
                    }
                    else -> {   // cat / fox / wolf: pointy
                        val tip = side * s * (if (ears == "wolf") 0.3f else 0.12f)
                        val h = s * (if (ears == "fox") 1.25f else 1.0f)
                        shapes += Path().apply { moveTo(cx - s * 0.85f, r.top + s * 0.4f); lineTo(cx + s * 0.85f, r.top + s * 0.4f); lineTo(cx + tip, r.top - h); close() }
                        innerEars += Path().apply { moveTo(cx - s * 0.45f, r.top + s * 0.15f); lineTo(cx + s * 0.45f, r.top + s * 0.15f); lineTo(cx + tip * 0.8f, r.top - h * 0.55f); close() }
                    }
                }
            }
        }
        for (p in shapes) c.drawPath(p, pInk)
        for (p in shapes) c.drawPath(p, pFill)
        for (p in innerEars) c.drawPath(p, pInner)
        // doodled fur strokes in the bottom-right corner
        if (r.height() > 60 * d && r.width() > 120 * d) {
            val soft = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = blend(fill, ink, 0.45f); style = Paint.Style.STROKE; strokeWidth = 2 * d; strokeCap = Paint.Cap.ROUND }
            val fx = r.right - rr * 0.9f; val fy = r.bottom - 12 * d
            for (k in 0 until 2) c.drawArc(RectF(fx - 7 * d, fy - k * 8 * d - 5 * d, fx + 7 * d, fy - k * 8 * d + 5 * d), 20f + k * 15, 130f, false, soft)
        }
    }

    override fun setAlpha(alpha: Int) {}
    override fun setColorFilter(cf: ColorFilter?) {}
    @Deprecated("Deprecated in Java") override fun getOpacity() = PixelFormat.TRANSLUCENT

    companion object {
        fun blend(a: Int, b: Int, k: Float): Int {
            fun ch(sh: Int) = (((a shr sh) and 255) * (1 - k) + ((b shr sh) and 255) * k).toInt()
            return (255 shl 24) or (ch(16) shl 16) or (ch(8) shl 8) or ch(0)
        }
    }
}
