package com.wolfiecodesowo.fluffvr

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import java.net.DatagramSocket

/**
 * Phone <-> Quest sockets always go over Wi-Fi. Lots of phones quietly send traffic over mobile data instead
 * (Samsung "switch to mobile data", Pixel "adaptive connectivity", a VPN...), so the Quest never hears them.
 */
object Net {
    @Volatile private var app: Context? = null

    fun init(ctx: Context) { app = ctx.applicationContext }

    /** a UDP socket pinned to the Wi-Fi network (plain socket if there's no Wi-Fi or we can't pin it) */
    fun udp(): DatagramSocket {
        val sock = DatagramSocket()
        try {
            val cm = app?.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return sock
            @Suppress("DEPRECATION")
            val wifi = cm.allNetworks.firstOrNull { cm.getNetworkCapabilities(it)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true }
            wifi?.bindSocket(sock)
        } catch (_: Exception) {}
        return sock
    }

    /** what the phone is on right now, for the status line */
    fun onWifi(): Boolean = try {
        val cm = app?.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
        @Suppress("DEPRECATION")
        cm?.allNetworks?.any { cm.getNetworkCapabilities(it)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true } ?: true
    } catch (_: Exception) { true }
}
