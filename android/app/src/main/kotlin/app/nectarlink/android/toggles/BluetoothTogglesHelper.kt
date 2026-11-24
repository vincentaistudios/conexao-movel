// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.toggles

import android.bluetooth.BluetoothClass
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.content.Context
import android.os.Build
import android.provider.Settings
import android.util.Log
import app.nectarlink.android.elevated.Elevated

/**
 * Utilitario auxiliar para gestao, leitura de dispositivos pareados/conectados e comandos Bluetooth.
 */
class BluetoothTogglesHelper(
    private val context: Context,
    private val bluetooth: BluetoothManager?,
) {
    fun readBluetooth(): Boolean =
        runCatching { bluetooth?.adapter?.isEnabled }.getOrNull()
            ?: runCatching {
                Settings.Global.getInt(context.contentResolver, Settings.Global.BLUETOOTH_ON, 0) != 0
            }.getOrDefault(false)

    fun setBluetooth(on: Boolean): Boolean {
        if (Elevated.running) {
            val ran = Elevated.runCommand(if (on) "svc bluetooth enable" else "svc bluetooth disable")
            if (ran) return true
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            Log.w(TAG, "Alternancia silenciosa de Bluetooth rejeitada: Modo Elevado necessario no Android 10+")
            return false
        }
        return runCatching {
            val adapter = bluetooth?.adapter ?: return@runCatching false
            if (on) adapter.enable() else adapter.disable()
        }.getOrDefault(false)
    }

    fun readBtDevices(): List<Map<String, Any>> = runCatching {
        val btManager = bluetooth ?: return@runCatching emptyList()
        val adapter = btManager.adapter ?: return@runCatching emptyList()
        val bonded = runCatching { adapter.bondedDevices }.getOrNull().orEmpty()

        bonded.map { device ->
            val name = runCatching { device.name }.getOrNull().orEmpty().ifBlank { DEFAULT_BT_DEVICE_NAME }
            val mac = runCatching { device.address }.getOrNull().orEmpty()
            val btClass = runCatching { device.bluetoothClass }.getOrNull()
            val category = classifyBtDevice(btClass)

            val isConnected = runCatching {
                val isConnectedMethod = device.javaClass.getMethod("isConnected")
                (isConnectedMethod.invoke(device) as? Boolean) == true
            }.getOrNull() ?: runCatching {
                val a2dpState = btManager.getConnectionState(device, BluetoothProfile.A2DP)
                val headsetState = btManager.getConnectionState(device, BluetoothProfile.HEADSET)
                a2dpState == BluetoothProfile.STATE_CONNECTED || headsetState == BluetoothProfile.STATE_CONNECTED
            }.getOrDefault(false)

            mapOf(
                "name" to name,
                "mac" to mac,
                "address" to mac,
                "is_connected" to isConnected,
                "connected" to isConnected,
                "is_paired" to true,
                "paired" to true,
                "category" to category,
                "type" to category,
            )
        }.sortedWith(
            compareByDescending<Map<String, Any>> { it["is_connected"] as? Boolean == true }
                .thenBy { (it["name"] as? String).orEmpty() }
        )
    }.getOrElse {
        Log.w(TAG, "falha ao ler dispositivos bluetooth", it)
        emptyList()
    }

    fun connectBluetoothDevice(mac: String): Boolean {
        val trimmed = mac.trim()
        if (!MAC_REGEX.matches(trimmed)) return false
        if (Elevated.running) {
            val ok = Elevated.runCommand("cmd bluetooth_manager connect $trimmed")
            if (ok) return true
            val okAlt = Elevated.runCommand("cmd bluetooth connect $trimmed")
            if (okAlt) return true
        }
        return runCatching {
            val adapter = bluetooth?.adapter ?: return@runCatching false
            val device = adapter.getRemoteDevice(trimmed) ?: return@runCatching false
            val method = device.javaClass.getMethod("connect")
            method.invoke(device) as? Boolean ?: true
        }.getOrElse { false }
    }

    fun disconnectBluetoothDevice(mac: String): Boolean {
        val trimmed = mac.trim()
        if (!MAC_REGEX.matches(trimmed)) return false
        if (Elevated.running) {
            val ok = Elevated.runCommand("cmd bluetooth_manager disconnect $trimmed")
            if (ok) return true
            val okAlt = Elevated.runCommand("cmd bluetooth disconnect $trimmed")
            if (okAlt) return true
        }
        return runCatching {
            val adapter = bluetooth?.adapter ?: return@runCatching false
            val device = adapter.getRemoteDevice(trimmed) ?: return@runCatching false
            val method = device.javaClass.getMethod("disconnect")
            method.invoke(device) as? Boolean ?: true
        }.getOrElse { false }
    }

    fun classifyBtDevice(btClass: BluetoothClass?): String {
        if (btClass == null) return "outro"
        val major = btClass.majorDeviceClass
        val deviceClass = btClass.deviceClass

        return when {
            major == BluetoothClass.Device.Major.AUDIO_VIDEO ||
                deviceClass == BluetoothClass.Device.AUDIO_VIDEO_HEADPHONES ||
                deviceClass == BluetoothClass.Device.AUDIO_VIDEO_WEARABLE_HEADSET ||
                deviceClass == BluetoothClass.Device.AUDIO_VIDEO_LOUDSPEAKER -> "audio"

            major == BluetoothClass.Device.Major.PERIPHERAL ||
                deviceClass == BluetoothClass.Device.Major.PERIPHERAL -> "teclado/controle"

            major == BluetoothClass.Device.Major.WEARABLE ||
                deviceClass == BluetoothClass.Device.WEARABLE_WRIST_WATCH -> "relogio"

            major == BluetoothClass.Device.Major.PHONE -> "smartphone"

            major == BluetoothClass.Device.Major.COMPUTER -> "computador"

            else -> "outro"
        }
    }

    companion object {
        private const val TAG = "BtTogglesHelper"
        private const val DEFAULT_BT_DEVICE_NAME = "Dispositivo Bluetooth"
        val MAC_REGEX = Regex("^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")
    }
}

