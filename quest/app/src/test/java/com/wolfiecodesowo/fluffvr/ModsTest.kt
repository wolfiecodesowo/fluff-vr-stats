package com.wolfiecodesowo.fluffvr

import android.content.Context
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.annotation.Config
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

/** the Quest mods actually count things (v0.10 fix) + the Body tab math */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [33])
class ModsTest {
    private val ctx: Context get() = RuntimeEnvironment.getApplication()

    private fun vrchat(addr: String, v: Any) {
        val b = Osc.message(addr, v)
        DatagramSocket().use { it.send(DatagramPacket(b, b.size, InetAddress.getByName("127.0.0.1"), 9001)) }
        Thread.sleep(60)
    }

    private fun waitFor(what: String, ok: () -> Boolean) {
        val end = System.currentTimeMillis() + 3000
        while (!ok() && System.currentTimeMillis() < end) Thread.sleep(30)
        assertTrue(what, ok())
    }

    @Test
    fun countersCountFromVRChatOsc() {
        val s = Settings(ctx)
        s.headpats = 0; s.boops = 0; s.jumps = 0
        QuestMods.startListener(ctx)
        Thread.sleep(300)
        vrchat("/avatar/change", "avtr_test")
        // headpat contact (bool) on -> off -> on (after the 0.8s debounce) = 2 pats
        vrchat("/avatar/parameters/HeadPat", true); vrchat("/avatar/parameters/HeadPat", false)
        Thread.sleep(900)
        vrchat("/avatar/parameters/HeadPat", true); vrchat("/avatar/parameters/HeadPat", false)
        waitFor("2 headpats") { s.headpats == 2 }
        // float contact named like a boop
        vrchat("/avatar/parameters/NoseBoop", 0.9f); vrchat("/avatar/parameters/NoseBoop", 0f)
        waitFor("1 boop") { s.boops == 1 }
        // jump = Grounded true -> false
        vrchat("/avatar/parameters/Grounded", true); vrchat("/avatar/parameters/Grounded", false); vrchat("/avatar/parameters/Grounded", true)
        waitFor("1 jump") { s.jumps == 1 }
        vrchat("/avatar/parameters/MuteSelf", true)
        waitFor("muted") { QuestMods.muted == true }
        vrchat("/avatar/parameters/VelocityZ", 2.5f)
        waitFor("speed") { QuestMods.velZ == 2.5f }
        // restart the listener (used to kill itself: the old thread turned the new one off)
        QuestMods.stopListener(); Thread.sleep(50); QuestMods.startListener(ctx); Thread.sleep(1500)
        vrchat("/avatar/parameters/HeadPat", true); vrchat("/avatar/parameters/HeadPat", false)
        waitFor("still counting after a restart") { s.headpats == 3 }
        QuestMods.stopListener()
    }

    @Test
    fun standablePlantsFeetAndSteps() {
        val s = Settings(ctx); s.trackHeight = 1.7f
        var out = emptyMap<String, FloatArray>()
        repeat(30) { out = Standable.compute(s, 0f, 0f, 1f, 0.033f) }
        val l0 = out["foot_l"]!!.copyOf()
        repeat(10) { out = Standable.compute(s, 0.03f, 0.02f, 1f, 0.033f) }      // lil lean: feet stay
        assertEquals(l0[0], out["foot_l"]!![0], 1e-3f)
        repeat(60) { i -> out = Standable.compute(s, 0f, i * 0.02f, 1f, 0.033f) }  // walk 1.2 m: feet follow
        repeat(30) { out = Standable.compute(s, 0f, 1.2f, 1f, 0.033f) }
        assertTrue("feet stepped", out["foot_l"]!![2] > 0.9f)
        val crouch = Standable.compute(s, 0f, 1.2f, 0.4f, 0.033f)
        assertTrue("crouch lowers hip", crouch["hip"]!![1] < out["hip"]!![1] - 0.2f)
    }

    @Test
    fun cameraMathMakesTrackers() {
        val m = PoseMath(1.7f)
        // a person standing facing the camera (image pixels, y down)
        val p = mapOf("hip_l" to floatArrayOf(340f, 300f, 0f), "hip_r" to floatArrayOf(300f, 300f, 0f),
            "ank_l" to floatArrayOf(345f, 470f, 0f), "ank_r" to floatArrayOf(295f, 470f, 0f),
            "toe_l" to floatArrayOf(345f, 480f, -20f), "toe_r" to floatArrayOf(295f, 480f, -20f),
            "knee_l" to floatArrayOf(343f, 385f, -5f), "knee_r" to floatArrayOf(297f, 385f, -5f),
            "ear_l" to floatArrayOf(330f, 120f, 0f), "ear_r" to floatArrayOf(310f, 120f, 0f))
        val (parts, head) = m.trackers(p, true)!!
        val hip = parts["hip"]!!; val fl = parts["foot_l"]!!; val fr = parts["foot_r"]!!
        assertEquals("hip ~0.9m up", 0.9f, hip[1], 0.12f)
        assertTrue("feet on the floor", fl[1] < 0.12f && fr[1] < 0.12f)
        assertTrue("left foot is on ur left (image right)", fl[0] < fr[0])
        assertTrue("head above hip", head[1] > hip[1] + 0.5f)
        assertNotNull(parts["knee_l"])
    }

    @Test
    fun heartRateAndYouTubeParse() {
        assertEquals(72, Heart.parseBle(byteArrayOf(0, 72)))
        assertEquals(300, Heart.parseBle(byteArrayOf(1, 0x2c, 0x01)))
        val json = """{"contents":{"a":[{"videoRenderer":{"videoId":"abc","title":{"runs":[{"text":"lofi"}]},
            "ownerText":{"runs":[{"text":"Lofi Girl"}]},"lengthText":{"simpleText":"3:21"},"shortViewCountText":{"simpleText":"1M views"}}}]}}"""
        val r = YouTube.parse(json)
        assertEquals(1, r.size); assertEquals("lofi", r[0].title); assertEquals("3:21", r[0].length)
    }
}
