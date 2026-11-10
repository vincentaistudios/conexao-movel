// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.toggles

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.roundToInt

class PhoneTogglesLogicTest {

    @Test
    fun cleanSsidRemovesSurroundingQuotesAndDiscardsUnknown() {
        assertEquals("MinhaRede_5G", cleanSsidHelper("\"MinhaRede_5G\""))
        assertEquals("MinhaRede_2G", cleanSsidHelper("MinhaRede_2G"))
        assertNull(cleanSsidHelper("<unknown ssid>"))
        assertNull(cleanSsidHelper("\"<unknown ssid>\""))
        assertNull(cleanSsidHelper(""))
        assertNull(cleanSsidHelper("   "))
        assertNull(cleanSsidHelper("0x"))
        assertNull(cleanSsidHelper("\"0x\""))
        assertNull(cleanSsidHelper(null))
    }

    @Test
    fun scaleRssiToSignalLevelMapsDbmToPercentage() {
        assertEquals(0, scaleRssiHelper(-127))
        assertEquals(0, scaleRssiHelper(-130))
        assertEquals(0, scaleRssiHelper(0))
        assertEquals(0, scaleRssiHelper(5))

        assertEquals(100, scaleRssiHelper(-50))
        assertEquals(100, scaleRssiHelper(-40))
        assertEquals(0, scaleRssiHelper(-100))
        assertEquals(60, scaleRssiHelper(-70))
        assertEquals(40, scaleRssiHelper(-80))
    }

    @Test
    fun isCapabilitiesSecureDetectsSecurityProtocols() {
        assertTrue(isCapabilitiesSecureHelper("[WPA2-PSK-CCMP][RSN-PSK-CCMP][ESS]"))
        assertTrue(isCapabilitiesSecureHelper("[WPA-PSK-TKIP][ESS]"))
        assertTrue(isCapabilitiesSecureHelper("[WEP][ESS]"))
        assertTrue(isCapabilitiesSecureHelper("[WPA3-SAE][ESS]"))
        assertTrue(isCapabilitiesSecureHelper("[EAP/SHA256][ESS]"))
        assertFalse(isCapabilitiesSecureHelper("[ESS]"))
        assertFalse(isCapabilitiesSecureHelper(""))
    }

    @Test
    fun classifyBtDeviceMapsDeviceClassesCorrectly() {
        val audioMajor = 0x0400 // BluetoothClass.Device.Major.AUDIO_VIDEO
        val peripheralMajor = 0x0500 // BluetoothClass.Device.Major.PERIPHERAL
        val wearableMajor = 0x0700 // BluetoothClass.Device.Major.WEARABLE
        val phoneMajor = 0x0200 // BluetoothClass.Device.Major.PHONE
        val computerMajor = 0x0100 // BluetoothClass.Device.Major.COMPUTER

        assertEquals("audio", classifyBtDeviceHelper(audioMajor, 0))
        assertEquals("teclado/controle", classifyBtDeviceHelper(peripheralMajor, 0))
        assertEquals("relogio", classifyBtDeviceHelper(wearableMajor, 0))
        assertEquals("smartphone", classifyBtDeviceHelper(phoneMajor, 0))
        assertEquals("computador", classifyBtDeviceHelper(computerMajor, 0))
        assertEquals("outro", classifyBtDeviceHelper(0x1F00, 0))
        assertEquals("outro", classifyBtDeviceHelper(null, null))
    }

    @Test
    fun macRegexValidatesStandardMacFormats() {
        val macRegex = Regex("^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")
        assertTrue(macRegex.matches("00:11:22:33:44:55"))
        assertTrue(macRegex.matches("AA:BB:CC:DD:EE:FF"))
        assertTrue(macRegex.matches("aa-bb-cc-dd-ee-ff"))
        assertFalse(macRegex.matches("00:11:22:33:44"))
        assertFalse(macRegex.matches("00:11:22:33:44:55:66"))
        assertFalse(macRegex.matches("00:11:22:33:44:55; rm -rf /"))
        assertFalse(macRegex.matches("invalid"))
        assertFalse(macRegex.matches(""))
    }

    @Test
    fun wifiNetworksDeduplicationKeepsStrongestSignalAndConnectedStatus() {
        data class RawScan(val ssid: String, val level: Int, val caps: String)

        val scans = listOf(
            RawScan("Escritorio", -75, "[WPA2-PSK-CCMP][ESS]"),
            RawScan("Escritorio", -55, "[WPA2-PSK-CCMP][ESS]"),
            RawScan("Visitantes", -80, "[ESS]"),
            RawScan("<unknown ssid>", -50, "[WPA2-PSK-CCMP][ESS]"),
        )

        val currentConnectedSsid = "Escritorio"
        val savedSsids = setOf("Escritorio", "RedeCasa")

        val networkMap = mutableMapOf<String, MutableMap<String, Any>>()
        for (scan in scans) {
            val ssid = cleanSsidHelper(scan.ssid) ?: continue
            val signal = scaleRssiHelper(scan.level)
            val isConnected = (currentConnectedSsid == ssid)
            val isSaved = savedSsids.contains(ssid) || isConnected
            val isSecure = isCapabilitiesSecureHelper(scan.caps)

            val existing = networkMap[ssid]
            if (existing == null) {
                networkMap[ssid] = mutableMapOf(
                    "ssid" to ssid,
                    "signal_level" to signal,
                    "is_connected" to isConnected,
                    "is_saved" to isSaved,
                    "is_secure" to isSecure,
                )
            } else {
                val prevSignal = existing["signal_level"] as Int
                if (signal > prevSignal) {
                    existing["signal_level"] = signal
                }
                if (isConnected) {
                    existing["is_connected"] = true
                    existing["is_saved"] = true
                }
            }
        }

        assertEquals(2, networkMap.size)
        val escritorio = networkMap["Escritorio"]
        org.junit.Assert.assertNotNull(escritorio)
        assertEquals(90, escritorio!!["signal_level"]) // -55 dBm mapeado para 90%
        assertTrue(escritorio["is_connected"] as Boolean)
        assertTrue(escritorio["is_saved"] as Boolean)
        assertTrue(escritorio["is_secure"] as Boolean)

        val visitantes = networkMap["Visitantes"]
        org.junit.Assert.assertNotNull(visitantes)
        assertFalse(visitantes!!["is_connected"] as Boolean)
        assertFalse(visitantes["is_secure"] as Boolean)
    }

    private fun cleanSsidHelper(rawSsid: String?): String? {
        if (rawSsid.isNullOrBlank()) return null
        val clean = rawSsid.removeSurrounding("\"").trim()
        if (clean.isEmpty() || clean == "<unknown ssid>" || clean == "0x") return null
        return clean
    }

    private fun scaleRssiHelper(rssiDbm: Int): Int {
        if (rssiDbm <= -127 || rssiDbm >= 0) return 0
        return (((rssiDbm + 100).toFloat() / 50f) * 100f).roundToInt().coerceIn(0, 100)
    }

    private fun isCapabilitiesSecureHelper(capabilities: String): Boolean =
        capabilities.contains("WPA", ignoreCase = true) ||
            capabilities.contains("WEP", ignoreCase = true) ||
            capabilities.contains("EAP", ignoreCase = true) ||
            capabilities.contains("PSK", ignoreCase = true) ||
            capabilities.contains("SAE", ignoreCase = true)

    private fun classifyBtDeviceHelper(major: Int?, deviceClass: Int?): String {
        if (major == null) return "outro"
        return when {
            major == 0x0400 -> "audio"
            major == 0x0500 -> "teclado/controle"
            major == 0x0700 -> "relogio"
            major == 0x0200 -> "smartphone"
            major == 0x0100 -> "computador"
            else -> "outro"
        }
    }
}
