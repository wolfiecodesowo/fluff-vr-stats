package com.wolfiecodesowo.fluffvr

import android.util.Base64
import org.json.JSONObject
import java.security.KeyFactory
import java.security.PublicKey
import java.security.Signature
import java.security.spec.X509EncodedKeySpec

/**
 * Signatures, same as the PC app's trust.py: Fluff Bot signs chat messages, app keys and replies with
 * its private key (ECDSA P-256). The app only trusts things with a good signature, so nobody can skip
 * the chat rules by posting to the relay directly.
 *
 * The bot's PUBLIC key gets baked in at build time from ../trust.json (BuildConfig.FLUFF_BOT_KEY).
 * Built without one (before the owner made the keys)? Then everything here is off and the app keeps
 * using the old v1 chat, exactly like the PC app.
 */
object Trust {
    private val key: PublicKey? by lazy {
        val raw = BuildConfig.FLUFF_BOT_KEY
        if (raw.isBlank()) null else try {
            KeyFactory.getInstance("EC").generatePublic(X509EncodedKeySpec(b64d(raw)))
        } catch (_: Exception) { null }
    }

    /** true once this build has Fluff Bot's key (keys + safe chat are on) */
    val on: Boolean get() = key != null

    fun b64d(s: String): ByteArray = Base64.decode(s, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)

    fun verify(data: ByteArray, sig: String?): Boolean {
        val k = key ?: return false
        if (sig.isNullOrEmpty()) return false
        return try {
            Signature.getInstance("SHA256withECDSA").run { initVerify(k); update(data); verify(b64d(sig)) }
        } catch (_: Exception) { false }
    }

    /** checks a signed JSON payload the same way trust.verify_payload does on PC */
    fun verifyPayload(o: JSONObject): Boolean = verify(canonical(o).toByteArray(Charsets.UTF_8), o.optString("sig", ""))

    /**
     * The exact bytes Python's json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False) makes,
     * minus the "sig" field. Fluff Bot only signs flat objects of strings, whole numbers and true/false.
     */
    fun canonical(o: JSONObject): String {
        val keys = o.keys().asSequence().filter { it != "sig" }.sorted().toList()
        val sb = StringBuilder("{")
        keys.forEachIndexed { i, k ->
            if (i > 0) sb.append(',')
            sb.append(jstr(k)).append(':')
            when (val v = o.get(k)) {
                is String -> sb.append(jstr(v))
                is Boolean -> sb.append(if (v) "true" else "false")
                is Int, is Long -> sb.append(v.toString())
                is Number -> { val d = v.toDouble(); if (d == Math.floor(d) && !d.isInfinite()) sb.append(d.toLong()) else sb.append(v.toString()) }
                JSONObject.NULL -> sb.append("null")
                else -> sb.append(jstr(v.toString()))
            }
        }
        return sb.append('}').toString()
    }

    private fun jstr(s: String): String {
        val sb = StringBuilder("\"")
        for (ch in s) {
            when (ch) {
                '"' -> sb.append("\\\"")
                '\\' -> sb.append("\\\\")
                '\n' -> sb.append("\\n")
                '\r' -> sb.append("\\r")
                '\t' -> sb.append("\\t")
                '\b' -> sb.append("\\b")
                '\u000C' -> sb.append("\\f")
                else -> if (ch.code < 0x20) sb.append(String.format("\\u%04x", ch.code)) else sb.append(ch)
            }
        }
        return sb.append('"').toString()
    }

    /** "payload.sig" token from Fluff Bot -> its payload if the signature is good */
    fun readToken(tok: String?): JSONObject? {
        if (tok.isNullOrEmpty() || !on) return null
        val i = tok.lastIndexOf('.')
        if (i <= 0) return null
        return try {
            val raw = b64d(tok.substring(0, i))
            if (!verify(raw, tok.substring(i + 1))) null else JSONObject(String(raw, Charsets.UTF_8))
        } catch (_: Exception) { null }
    }
}
