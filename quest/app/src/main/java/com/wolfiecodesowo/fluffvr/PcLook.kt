package com.wolfiecodesowo.fluffvr

import android.content.Context
import android.graphics.Canvas
import android.graphics.ColorFilter
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.RadialGradient
import android.graphics.RectF
import android.graphics.Shader
import android.graphics.drawable.Drawable
import android.view.View
import android.view.ViewGroup
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.sin

/**
 * v0.10: the PC menu's look, ported. Same hand-drawn tab icons (ui.py tab_icon), the big furry frame with
 * ears + the pride stripe collar, faint paw prints, the heart toggle switch, and a 2-column masonry like
 * the PC's side-by-side panels.
 */

/** PC tab icons, drawn the same way (sizes are in the PC's pixels, scaled by [u]) */
class TabIcon(private val name: String, private val col: Int, private val hole: Int, private val d: Float) : Drawable() {
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = col; style = Paint.Style.FILL }
    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = col; style = Paint.Style.STROKE; strokeWidth = 2.6f * d; strokeCap = Paint.Cap.ROUND; strokeJoin = Paint.Join.ROUND
    }
    private val holeP = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = hole; style = Paint.Style.FILL }

    override fun getIntrinsicWidth() = (30 * d).toInt()
    override fun getIntrinsicHeight() = (30 * d).toInt()

    override fun draw(c: Canvas) {
        val u = bounds.width() / 30f          // 1 PC pixel
        val cx = bounds.exactCenterX(); val cy = bounds.exactCenterY()
        fun R(x0: Float, y0: Float, x1: Float, y1: Float) = RectF(cx + x0 * u, cy + y0 * u, cx + x1 * u, cy + y1 * u)
        fun poly(vararg p: Float, paint: Paint = fill) {
            val path = Path(); path.moveTo(cx + p[0] * u, cy + p[1] * u)
            var i = 2; while (i < p.size) { path.lineTo(cx + p[i] * u, cy + p[i + 1] * u); i += 2 }
            path.close(); c.drawPath(path, paint)
        }
        fun ln(x0: Float, y0: Float, x1: Float, y1: Float, w: Float = 3f) {
            line.strokeWidth = w * u; c.drawLine(cx + x0 * u, cy + y0 * u, cx + x1 * u, cy + y1 * u, line)
        }
        fun heart(x: Float, y: Float, r: Float, p: Paint) {
            val path = Path()
            path.moveTo(cx + x * u, cy + (y + r) * u)
            path.cubicTo(cx + (x - r * 2) * u, cy + (y - r * 0.4f) * u, cx + (x - r * 0.9f) * u, cy + (y - r * 1.6f) * u, cx + x * u, cy + (y - r * 0.5f) * u)
            path.cubicTo(cx + (x + r * 0.9f) * u, cy + (y - r * 1.6f) * u, cx + (x + r * 2) * u, cy + (y - r * 0.4f) * u, cx + x * u, cy + (y + r) * u)
            c.drawPath(path, p)
        }
        line.strokeWidth = 3 * u
        when (name) {
            "Home" -> { poly(-12f, -1f, 0f, -12f, 12f, -1f); c.drawRoundRect(R(-9f, -3f, 9f, 11f), 3 * u, 3 * u, fill); heart(0f, 4f, 4f, holeP) }
            "Chatbox" -> {
                c.drawRoundRect(R(-12f, -9f, 12f, 6f), 6 * u, 6 * u, line)
                poly(2f, 5f, 8f, 5f, 9f, 11f)
                for (i in listOf(-6f, 0f, 6f)) c.drawOval(R(i - 2, -3f, i + 2, 1f), fill)
            }
            "Mods" -> { c.drawRoundRect(R(-12f, -6f, 12f, 6f), 6 * u, 6 * u, line); c.drawOval(R(1f, -4f, 9f, 4f), fill) }
            "Body" -> {
                c.drawOval(R(-4f, -12f, 4f, -4f), line); ln(0f, -4f, 0f, 4f); ln(-8f, -1f, 8f, -1f)
                ln(0f, 4f, -6f, 12f); ln(0f, 4f, 6f, 12f)
            }
            "Global" -> {
                c.drawOval(R(-11f, -11f, 11f, 11f), line)
                c.drawOval(R(-5f, -11f, 5f, 11f), line.apply { strokeWidth = 2 * u }); ln(-11f, 0f, 11f, 0f, 2f)
                heart(8f, -9f, 3.5f, fill)
            }
            "Avatar" -> {
                poly(-10f, -2f, -9f, -13f, -2f, -7f); poly(10f, -2f, 9f, -13f, 2f, -7f)
                c.drawOval(R(-10f, -8f, 10f, 10f), fill)
                c.drawOval(R(-5f, -1f, -2f, 2f), holeP); c.drawOval(R(2f, -1f, 5f, 2f), holeP)
            }
            "Music" -> {
                c.drawOval(R(-8f, 1f, -0.8f, 7f), fill)
                c.drawRect(R(-1.7f, -8.6f, 0f, 4f), fill)
                poly(-1.7f, -8.6f, 4.6f, -5.6f, 4.6f, -2.6f, 0f, -5.3f)
            }
            "Cam" -> {      // camera
                c.drawRoundRect(R(-12f, -7f, 12f, 9f), 4 * u, 4 * u, line); c.drawRect(R(-5f, -11f, 3f, -7f), fill)
                c.drawOval(R(-5f, -4f, 5f, 6f), line)
            }
            "Remote" -> {   // phone
                c.drawRoundRect(R(-7f, -12f, 7f, 12f), 3 * u, 3 * u, line); c.drawOval(R(-1.5f, 6.5f, 1.5f, 9.5f), fill)
            }
            "Settings" -> {
                for (i in 0 until 8) {
                    val a = i * Math.PI / 4
                    ln((cos(a) * 7).toFloat(), (sin(a) * 7).toFloat(), (cos(a) * 12).toFloat(), (sin(a) * 12).toFloat(), 4f)
                }
                c.drawOval(R(-8f, -8f, 8f, 8f), line.apply { strokeWidth = 4 * u })
            }
            "Thanks" -> heart(0f, 1f, 7f, fill)
            else -> c.drawOval(R(-3f, -3f, 3f, 3f), fill)
        }
    }

    override fun setAlpha(alpha: Int) {}
    override fun setColorFilter(cf: ColorFilter?) {}
    @Deprecated("Deprecated in Java") override fun getOpacity() = PixelFormat.TRANSLUCENT
}

/** the PC's dash_bg: soft accent glow top-left, 2nd glow bottom-right, faint paw prints */
class PawBackground(private val accent: Int, private val accent2: Int, private val paw: Int, private val d: Float) : Drawable() {
    override fun draw(c: Canvas) {
        val b = bounds
        val p = Paint(Paint.ANTI_ALIAS_FLAG)
        p.shader = RadialGradient(b.left + b.width() * 0.08f, b.top + b.height() * 0.1f, max(b.width(), b.height()) * 0.45f,
            (accent and 0x00FFFFFF) or (0x2A shl 24), 0, Shader.TileMode.CLAMP)
        c.drawRect(b, p)
        p.shader = RadialGradient(b.right - b.width() * 0.06f, b.bottom - b.height() * 0.08f, max(b.width(), b.height()) * 0.42f,
            (accent2 and 0x00FFFFFF) or (0x20 shl 24), 0, Shader.TileMode.CLAMP)
        c.drawRect(b, p)
        p.shader = null
        p.color = (paw and 0x00FFFFFF) or (0x10 shl 24)
        val rnd = java.util.Random(7)
        repeat((b.width() * b.height() / (140 * 140 * d * d)).toInt().coerceIn(10, 40)) {
            val x = b.left + rnd.nextFloat() * b.width(); val y = b.top + rnd.nextFloat() * b.height()
            val r = (5 + rnd.nextFloat() * 4) * d
            c.drawOval(RectF(x - r * 0.75f, y - r * 0.2f, x + r * 0.75f, y + r * 0.95f), p)
            for ((dx, dy) in listOf(-0.9f to -0.75f, -0.32f to -1.25f, 0.32f to -1.25f, 0.9f to -0.75f)) {
                val tr = r * 0.32f
                c.drawOval(RectF(x + dx * r - tr, y + dy * r - tr, x + dx * r + tr, y + dy * r + tr), p)
            }
        }
    }

    override fun setAlpha(alpha: Int) {}
    override fun setColorFilter(cf: ColorFilter?) {}
    @Deprecated("Deprecated in Java") override fun getOpacity() = PixelFormat.TRANSLUCENT
}

/** the whole window: a big furry card with cat ears + the pride stripe across its top edge (like the PC menu) */
class FrameDrawable(private val card: FluffDrawable, private val stripe: IntArray, private val radius: Float,
                    private val d: Float, private val inner: Drawable? = null) : Drawable() {
    override fun draw(c: Canvas) {
        card.bounds = bounds
        card.draw(c)
        val r = RectF(bounds.left + card.insetSide.toFloat(), bounds.top + card.insetTop.toFloat(),
            bounds.right - card.insetSide.toFloat(), bounds.bottom - card.insetBottom.toFloat())
        c.save()
        val clip = Path().apply { addRoundRect(r, radius, radius, Path.Direction.CW) }
        c.clipPath(clip)
        inner?.let { it.setBounds(r.left.toInt(), r.top.toInt(), r.right.toInt(), r.bottom.toInt()); it.draw(c) }
        val h = 9 * d
        val w = r.width() / stripe.size
        val p = Paint(Paint.ANTI_ALIAS_FLAG)
        stripe.forEachIndexed { i, col -> p.color = col; c.drawRect(r.left + i * w, r.top, r.left + (i + 1) * w + 1, r.top + h, p) }
        p.color = 0x55000000; c.drawRect(r.left, r.top + h, r.right, r.top + h + 1.5f * d, p)
        c.restore()
        c.drawRoundRect(r, radius, radius, Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = 0xFF0E0912.toInt(); style = Paint.Style.STROKE; strokeWidth = 3f * d })
    }

    val stripeH get() = (9 * d).toInt()

    override fun setAlpha(alpha: Int) {}
    override fun setColorFilter(cf: ColorFilter?) {}
    @Deprecated("Deprecated in Java") override fun getOpacity() = PixelFormat.TRANSLUCENT
}

/** the PC's switch: pill, white knob, lil heart on the knob when it's on */
class HeartSwitch(private val on: Boolean, private val accent: Int, private val off: Int, private val d: Float) : Drawable() {
    override fun getIntrinsicWidth() = (46 * d).toInt()
    override fun getIntrinsicHeight() = (26 * d).toInt()
    override fun draw(c: Canvas) {
        val b = RectF(bounds)
        val p = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = if (on) accent else off }
        c.drawRoundRect(b, b.height() / 2, b.height() / 2, p)
        val k = b.height() - 7 * d
        val kx = if (on) b.right - k - 3.5f * d else b.left + 3.5f * d
        p.color = 0xFFFFFFFF.toInt()
        c.drawOval(RectF(kx, b.top + 3.5f * d, kx + k, b.top + 3.5f * d + k), p)
        if (on) {
            p.color = accent
            val x = kx + k / 2; val y = b.top + 3.5f * d + k / 2 + d; val r = k * 0.2f
            val path = Path()
            path.moveTo(x, y + r)
            path.cubicTo(x - r * 2, y - r * 0.4f, x - r * 0.9f, y - r * 1.6f, x, y - r * 0.5f)
            path.cubicTo(x + r * 0.9f, y - r * 1.6f, x + r * 2, y - r * 0.4f, x, y + r)
            c.drawPath(path, p)
        }
    }

    override fun setAlpha(alpha: Int) {}
    override fun setColorFilter(cf: ColorFilter?) {}
    @Deprecated("Deprecated in Java") override fun getOpacity() = PixelFormat.TRANSLUCENT
}

/** side-by-side panels like the PC: each card drops into whichever column is shorter */
class Masonry(ctx: Context, private val cols: Int, private val gap: Int) : ViewGroup(ctx) {
    private val colOf = HashMap<View, Int>()
    private val topOf = HashMap<View, Int>()

    override fun onMeasure(wSpec: Int, hSpec: Int) {
        val w = MeasureSpec.getSize(wSpec)
        val n = if (cols < 2 || w < 600 * resources.displayMetrics.density) 1 else cols
        val cw = (w - paddingLeft - paddingRight - gap * (n - 1)) / n
        val heights = IntArray(n)
        for (i in 0 until childCount) {
            val v = getChildAt(i)
            if (v.visibility == GONE) continue
            val lp = v.layoutParams as? MarginLayoutParams
            val full = (v.getTag(R.id.masonry_full) as? Boolean) == true && n > 1
            val width = if (full) w - paddingLeft - paddingRight else cw
            v.measure(MeasureSpec.makeMeasureSpec(width, MeasureSpec.EXACTLY), MeasureSpec.makeMeasureSpec(0, MeasureSpec.UNSPECIFIED))
            val mb = lp?.bottomMargin ?: 0
            if (full) {
                val top = heights.max()
                colOf[v] = -1; topOf[v] = top
                for (k in 0 until n) heights[k] = top + v.measuredHeight + mb
            } else {
                var col = 0
                for (k in 1 until n) if (heights[k] < heights[col]) col = k
                colOf[v] = col; topOf[v] = heights[col]
                heights[col] += v.measuredHeight + mb
            }
        }
        setMeasuredDimension(w, (heights.maxOrNull() ?: 0) + paddingTop + paddingBottom)
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val w = r - l
        val n = if (cols < 2 || w < 600 * resources.displayMetrics.density) 1 else cols
        val cw = (w - paddingLeft - paddingRight - gap * (n - 1)) / n
        for (i in 0 until childCount) {
            val v = getChildAt(i)
            if (v.visibility == GONE) continue
            val col = colOf[v] ?: 0
            val x = paddingLeft + if (col < 0) 0 else col * (cw + gap)
            val y = paddingTop + (topOf[v] ?: 0)
            v.layout(x, y, x + v.measuredWidth, y + v.measuredHeight)
        }
    }

    override fun generateLayoutParams(attrs: android.util.AttributeSet?) = MarginLayoutParams(context, attrs)
    override fun generateDefaultLayoutParams() = MarginLayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT)
    override fun generateLayoutParams(p: LayoutParams?) = MarginLayoutParams(p)
    override fun checkLayoutParams(p: LayoutParams?) = p is MarginLayoutParams
}

/** chips that wrap onto the next line (like the PC's button grids) instead of scrolling sideways */
class FlowRow(ctx: Context) : ViewGroup(ctx) {
    override fun onMeasure(wSpec: Int, hSpec: Int) {
        val maxW = MeasureSpec.getSize(wSpec) - paddingLeft - paddingRight
        var x = 0; var y = 0; var lineH = 0
        for (i in 0 until childCount) {
            val v = getChildAt(i)
            if (v.visibility == GONE) continue
            val lp = v.layoutParams as MarginLayoutParams
            v.measure(MeasureSpec.makeMeasureSpec(maxW, MeasureSpec.AT_MOST), MeasureSpec.makeMeasureSpec(0, MeasureSpec.UNSPECIFIED))
            val w = v.measuredWidth + lp.leftMargin + lp.rightMargin
            if (x > 0 && x + w > maxW) { x = 0; y += lineH; lineH = 0 }
            x += w
            lineH = max(lineH, v.measuredHeight + lp.topMargin + lp.bottomMargin)
        }
        setMeasuredDimension(MeasureSpec.getSize(wSpec), y + lineH + paddingTop + paddingBottom)
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val maxW = r - l - paddingLeft - paddingRight
        // pass 1: which line each child is on + how tall each line is
        val line = IntArray(childCount); val heights = ArrayList<Int>()
        var x = 0; var lineH = 0; var ln = 0
        for (i in 0 until childCount) {
            val v = getChildAt(i)
            if (v.visibility == GONE) continue
            val lp = v.layoutParams as MarginLayoutParams
            val w = v.measuredWidth + lp.leftMargin + lp.rightMargin
            if (x > 0 && x + w > maxW) { heights += lineH; ln++; x = 0; lineH = 0 }
            line[i] = ln; x += w
            lineH = max(lineH, v.measuredHeight + lp.topMargin + lp.bottomMargin)
        }
        heights += lineH
        // pass 2: place them, each one centered in its line (labels line up with the buttons next to them)
        x = 0; var y = 0; var cur = 0
        for (i in 0 until childCount) {
            val v = getChildAt(i)
            if (v.visibility == GONE) continue
            val lp = v.layoutParams as MarginLayoutParams
            while (cur < line[i]) { y += heights[cur]; cur++; x = 0 }
            val h = v.measuredHeight + lp.topMargin + lp.bottomMargin
            val top = paddingTop + y + (heights[cur] - h) / 2 + lp.topMargin
            v.layout(paddingLeft + x + lp.leftMargin, top, paddingLeft + x + lp.leftMargin + v.measuredWidth, top + v.measuredHeight)
            x += v.measuredWidth + lp.leftMargin + lp.rightMargin
        }
    }

    override fun generateLayoutParams(attrs: android.util.AttributeSet?) = MarginLayoutParams(context, attrs)
    override fun generateDefaultLayoutParams() = MarginLayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT)
    override fun generateLayoutParams(p: LayoutParams?) = if (p is MarginLayoutParams) MarginLayoutParams(p) else MarginLayoutParams(p)
    override fun checkLayoutParams(p: LayoutParams?) = p is MarginLayoutParams
}
