// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.toggles

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.wifi.WifiInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Handler
import android.util.Log
import app.nectarlink.android.elevated.Elevated
import kotlin.math.roundToInt

/**
 * Utilitario auxiliar para gestao, leitura de SSID/sinal e varredura de redes Wi-Fi.
 */
class WifiTogglesHelper(
    private val context: Context,
    private val wifi: WifiManager?,
    private val connectivity: ConnectivityManager?,
) {
    fun readWifi(): Boolean = runCatching { wifi?.isWifiEnabled == true }.getOrDefault(false)

    fun setWifi(on: Boolean): Boolean {
        if (Elevated.running) {
            val ran = Elevated.runCommand(if (on) "svc wifi enable" else "svc wifi disable")
            if (ran) return true
        }
        return runCatching {
            @Suppress("DEPRECATION")
            wifi?.setWifiEnabled(on) == true
        }.getOrDefault(false)
    }

    fun triggerWifiScan(mainHandler: Handler, onScanned: () -> Unit): Boolean {
        runCatching {
            @Suppress("DEPRECATION")
            wifi?.startScan()
        }
        if (Elevated.running) {
            Elevated.runCommand("cmd wifi list-scan-results")
        }
        mainHandler.postDelayed({ onScanned() }, WIFI_SCAN_PUSH_DELAY_MS)
        return true
    }

    fun readWifiSsid(): String? = runCatching {
        if (!readWifi()) return@runCatching null

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && connectivity != null) {
            val active = connectivity.activeNetwork
            val caps = connectivity.getNetworkCapabilities(active)
            if (caps != null && caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                val wifiInfo = caps.transportInfo as? WifiInfo
                val candidate = cleanSsid(wifiInfo?.ssid)
                if (candidate != null) return@runCatching candidate
            }
        }

        @Suppress("DEPRECATION")
        val info = runCatching { wifi?.connectionInfo }.getOrNull()
        if (info != null && info.networkId != -1) {
            val candidate = cleanSsid(info.ssid)
            if (candidate != null) return@runCatching candidate
        }

        null
    }.getOrNull()

    fun readWifiSignal(): Int = runCatching {
        if (!readWifi()) return@runCatching 0

        var rssi: Int? = null
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && connectivity != null) {
            val active = connectivity.activeNetwork
            val caps = connectivity.getNetworkCapabilities(active)
            if (caps != null && caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                val wifiInfo = caps.transportInfo as? WifiInfo
                if (wifiInfo != null) {
                    rssi = wifiInfo.rssi
                }
            }
        }
        if (rssi == null || rssi <= -127 || rssi >= 0) {
            @Suppress("DEPRECATION")
            val info = runCatching { wifi?.connectionInfo }.getOrNull()
            if (info != null && info.networkId != -1) {
                rssi = info.rssi
            }
        }
        val currentRssi = rssi ?: return@runCatching 0
        scaleRssiToSignalLevel(currentRssi)
    }.getOrDefault(0)

    fun readWifiNetworks(): List<Map<String, Any>> = runCatching {
        val currentSsid = readWifiSsid()
        val savedSsids = runCatching {
            @Suppress("DEPRECATION")
            wifi?.configuredNetworks?.mapNotNull { cleanSsid(it.SSID) }?.toSet()
        }.getOrNull().orEmpty()

        val scanResults = runCatching { wifi?.scanResults }.getOrNull().orEmpty()
        if (scanResults.isEmpty() && Elevated.running) {
            Elevated.runCommand("cmd wifi list-scan-results")
        }

        val networkMap = mutableMapOf<String, MutableMap<String, Any>>()
        for (result in scanResults) {
            val ssid = cleanSsid(result.SSID) ?: continue
            val signalLevel = scaleRssiToSignalLevel(result.level)
            val isConnected = (currentSsid != null && currentSsid == ssid)
            val isSaved = savedSsids.contains(ssid) || isConnected
            val caps = result.capabilities.orEmpty()
            val isSecure = isCapabilitiesSecure(caps)

            val existing = networkMap[ssid]
            if (existing == null) {
                networkMap[ssid] = mutableMapOf(
                    "ssid" to ssid,
                    "signal_level" to signalLevel,
                    "signal" to signalLevel,
                    "is_connected" to isConnected,
                    "is_saved" to isSaved,
                    "is_secure" to isSecure,
                    "security" to if (isSecure) "WPA2" else "OPEN",
                )
            } else {
                val previousSignal = (existing["signal_level"] as? Int) ?: 0
                if (signalLevel > previousSignal) {
                    existing["signal_level"] = signalLevel
                    existing["signal"] = signalLevel
                }
                if (isConnected) {
                    existing["is_connected"] = true
                    existing["is_saved"] = true
                }
                if (isSaved) {
                    existing["is_saved"] = true
                }
                if (isSecure) {
                    existing["is_secure"] = true
                    existing["security"] = "WPA2"
                }
            }
        }

        if (currentSsid != null && !networkMap.containsKey(currentSsid)) {
            val sig = readWifiSignal()
            networkMap[currentSsid] = mutableMapOf(
                "ssid" to currentSsid,
                "signal_level" to sig,
                "signal" to sig,
                "is_connected" to true,
                "is_saved" to true,
                "is_secure" to true,
                "security" to "WPA2",
            )
        }

        networkMap.values.sortedWith(
            compareByDescending<MutableMap<String, Any>> { it["is_connected"] as? Boolean == true }
                .thenByDescending { (it["signal_level"] as? Int) ?: 0 }
        )
    }.getOrElse {
        Log.w(TAG, "falha ao ler redes wifi", it)
        emptyList()
    }

    fun scaleRssiToSignalLevel(rssiDbm: Int): Int {
        if (rssiDbm <= -127 || rssiDbm >= 0) return 0
        return runCatching {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && wifi != null) {
                val max = wifi.maxSignalLevel
                if (max > 0) {
                    val level = wifi.calculateSignalLevel(rssiDbm)
                    ((level.toFloat() / max) * 100).roundToInt().coerceIn(0, 100)
                } else {
                    @Suppress("DEPRECATION")
                    WifiManager.calculateSignalLevel(rssiDbm, 101).coerceIn(0, 100)
                }
            } else {
                @Suppress("DEPRECATION")
                WifiManager.calculateSignalLevel(rssiDbm, 101).coerceIn(0, 100)
            }
        }.getOrElse {
            (((rssiDbm + 100).toFloat() / 50f) * 100f).roundToInt().coerceIn(0, 100)
        }
    }

    fun cleanSsid(rawSsid: String?): String? {
        if (rawSsid.isNullOrBlank()) return null
        val clean = rawSsid.removeSurrounding("\"").trim()
        if (clean.isEmpty() || clean == UNKNOWN_SSID || clean == "0x") return null
        return clean
    }

    fun isCapabilitiesSecure(capabilities: String): Boolean =
        capabilities.contains("WPA", ignoreCase = true) ||
            capabilities.contains("WEP", ignoreCase = true) ||
            capabilities.contains("EAP", ignoreCase = true) ||
            capabilities.contains("PSK", ignoreCase = true) ||
            capabilities.contains("SAE", ignoreCase = true)

    companion object {
        private const val TAG = "WifiTogglesHelper"
        private const val UNKNOWN_SSID = "<unknown ssid>"
        const val WIFI_SCAN_PUSH_DELAY_MS = 1000L
    }
}

