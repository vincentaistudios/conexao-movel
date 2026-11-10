// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.toggles

import android.app.NotificationManager
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.database.ContentObserver
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.media.AudioManager
import android.net.ConnectivityManager
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.util.Log
import androidx.core.content.ContextCompat
import app.nectarlink.android.elevated.Elevated
import app.nectarlink.core.PhoneToggleValue
import app.nectarlink.core.PhoneToggles as CorePhoneToggles
import kotlin.math.roundToInt

/**
 * Leitura, monitoramento e alteracao das configuracoes rapidas do telefone para
 * computadores pareados (docs/protocol/toggles.md).
 */
class PhoneToggles(
    context: Context,
    private val onChanged: (CorePhoneToggles) -> Unit,
    private val onCapabilitiesChanged: () -> Unit,
) {
    private val context = context.applicationContext
    private val mainHandler = Handler(Looper.getMainLooper())
    private val audio = this.context.getSystemService(AudioManager::class.java)
    private val notifications = this.context.getSystemService(NotificationManager::class.java)
    private val camera = this.context.getSystemService(CameraManager::class.java)
    private val wifi = this.context.getSystemService(WifiManager::class.java)
    private val bluetooth = this.context.getSystemService(BluetoothManager::class.java)
    private val connectivity = this.context.getSystemService(ConnectivityManager::class.java)

    private val wifiHelper = WifiTogglesHelper(this.context, wifi, connectivity)
    private val btHelper = BluetoothTogglesHelper(this.context, bluetooth)

    private val torchCameraId: String? by lazy { findTorchCamera() }
    @Volatile private var torchOn: Boolean = false
    private var started = false
    private var lastSent: CorePhoneToggles? = null

    private val emitRunnable = Runnable { pushIfChanged() }
    private val followUpRunnable = Runnable { pushIfChanged() }

    private val torchCallback = object : CameraManager.TorchCallback() {
        override fun onTorchModeChanged(cameraId: String, enabled: Boolean) {
            if (cameraId == torchCameraId && torchOn != enabled) {
                torchOn = enabled
                schedulePush()
            }
        }
    }

    private val settingsObserver = object : ContentObserver(mainHandler) {
        override fun onChange(selfChange: Boolean) {
            schedulePush()
        }
    }

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action == NotificationManager.ACTION_NOTIFICATION_POLICY_ACCESS_GRANTED_CHANGED) {
                onCapabilitiesChanged()
            }
            schedulePush()
        }
    }

    fun start() {
        if (started) return
        started = true
        if (torchCameraId != null) {
            runCatching { camera?.registerTorchCallback(torchCallback, mainHandler) }
                .onFailure { Log.w(TAG, "falha ao registrar callback de lanterna", it) }
        }
        runCatching {
            context.contentResolver.registerContentObserver(
                Settings.System.getUriFor(Settings.System.SCREEN_BRIGHTNESS),
                false,
                settingsObserver,
            )
            context.contentResolver.registerContentObserver(
                Settings.Global.getUriFor(Settings.Global.BLUETOOTH_ON),
                false,
                settingsObserver,
            )
        }.onFailure { Log.w(TAG, "falha ao registrar observer de configuracoes", it) }

        val filter = IntentFilter().apply {
            addAction(NotificationManager.ACTION_INTERRUPTION_FILTER_CHANGED)
            addAction(NotificationManager.ACTION_NOTIFICATION_POLICY_ACCESS_GRANTED_CHANGED)
            addAction(AudioManager.RINGER_MODE_CHANGED_ACTION)
            addAction(VOLUME_CHANGED_ACTION)
            addAction(WifiManager.WIFI_STATE_CHANGED_ACTION)
            addAction(WifiManager.NETWORK_STATE_CHANGED_ACTION)
            addAction(WifiManager.SCAN_RESULTS_AVAILABLE_ACTION)
            addAction(BluetoothAdapter.ACTION_STATE_CHANGED)
            addAction(BluetoothAdapter.ACTION_CONNECTION_STATE_CHANGED)
            addAction(BluetoothDevice.ACTION_BOND_STATE_CHANGED)
            addAction(BluetoothDevice.ACTION_ACL_CONNECTED)
            addAction(BluetoothDevice.ACTION_ACL_DISCONNECTED)
        }
        ContextCompat.registerReceiver(context, receiver, filter, ContextCompat.RECEIVER_EXPORTED)
        pushNow()
    }

    fun stop() {
        if (!started) return
        started = false
        mainHandler.removeCallbacks(emitRunnable)
        mainHandler.removeCallbacks(followUpRunnable)
        if (torchCameraId != null) {
            runCatching { camera?.unregisterTorchCallback(torchCallback) }
        }
        runCatching { context.contentResolver.unregisterContentObserver(settingsObserver) }
        runCatching { context.unregisterReceiver(receiver) }
    }

    /** Capacidades toggles.* oferecidas pelo telefone no momento. */
    fun capabilities(): List<String> = buildList {
        add("toggles.read")
        add("toggles.ringer")
        add("toggles.volume")
        if (torchCameraId != null) add("toggles.flashlight")
        if (canChangeDnd(context)) add("toggles.dnd")
        if (canChangeBrightness(context)) add("toggles.brightness")
        if (Elevated.running || canChangeWifi(context)) {
            add("toggles.wifi")
        }
        if (Elevated.running || canChangeBluetooth()) {
            add("toggles.bluetooth")
        }
    }

    /** Leitura do estado consolidado de todas as configuracoes rapidas. */
    fun snapshot(): CorePhoneToggles = CorePhoneToggles(
        dnd = readDnd(),
        ringer = readRinger(),
        flashlight = if (torchCameraId != null) torchOn else null,
        volume = readVolume().toUByte(),
        brightness = readBrightness().toUByte(),
        wifi = wifiHelper.readWifi(),
        bluetooth = btHelper.readBluetooth(),
    )

    /** Envia imediatamente o snapshot atual para o nectarlink-core. */
    @Synchronized
    fun pushNow() {
        val current = snapshot()
        lastSent = current
        onChanged(current)
    }

    /** Obtem o SSID conectado atual via helper de Wi-Fi. */
    fun readWifiSsid(): String? = wifiHelper.readWifiSsid()

    /** Calcula o nivel de sinal da conexao Wi-Fi ativa (0..100). */
    fun readWifiSignal(): Int = wifiHelper.readWifiSignal()

    /** Realiza varredura de redes Wi-Fi acessiveis com deduplicacao. */
    fun readWifiNetworks(): List<Map<String, Any>> = wifiHelper.readWifiNetworks()

    /** Enumera dispositivos Bluetooth pareados/conectados. */
    fun readBtDevices(): List<Map<String, Any>> = btHelper.readBtDevices()

    fun set(id: String, value: PhoneToggleValue): Boolean {
        val ok = runCatching {
            when {
                id == "dnd" -> {
                    val on = (value as? PhoneToggleValue.Bool)?.on ?: return false
                    setDnd(on)
                }
                id == "ringer" -> {
                    val mode = (value as? PhoneToggleValue.Mode)?.mode ?: return false
                    setRinger(mode)
                }
                id == "flashlight" -> {
                    val on = (value as? PhoneToggleValue.Bool)?.on ?: return false
                    setFlashlight(on)
                }
                id == "volume" -> {
                    val level = (value as? PhoneToggleValue.Percent)?.percent?.toInt() ?: return false
                    setVolume(level)
                }
                id == "brightness" -> {
                    val level = (value as? PhoneToggleValue.Percent)?.percent?.toInt() ?: return false
                    setBrightness(level)
                }
                id == "wifi" -> {
                    val on = (value as? PhoneToggleValue.Bool)?.on ?: return false
                    wifiHelper.setWifi(on)
                }
                id == "bluetooth" -> {
                    val on = (value as? PhoneToggleValue.Bool)?.on ?: return false
                    btHelper.setBluetooth(on)
                }
                id == "wifi_scan" -> {
                    wifiHelper.triggerWifiScan(mainHandler) { pushNow() }
                }
                id == "bt_connect" -> {
                    val targetMac = if (value is PhoneToggleValue.Bool) {
                        ""
                    } else {
                        (value as? PhoneToggleValue.Mode)?.mode.orEmpty()
                    }
                    btHelper.connectBluetoothDevice(targetMac)
                }
                id == "bt_disconnect" -> {
                    val targetMac = if (value is PhoneToggleValue.Bool) {
                        ""
                    } else {
                        (value as? PhoneToggleValue.Mode)?.mode.orEmpty()
                    }
                    btHelper.disconnectBluetoothDevice(targetMac)
                }
                id == "hotspot" -> {
                    val on = (value as? PhoneToggleValue.Bool)?.on ?: return false
                    Elevated.runCommand(if (on) "hotspot on" else "hotspot off")
                }
                id == "pc_active" -> {
                    val on = (value as? PhoneToggleValue.Bool)?.on ?: return false
                    app.nectarlink.android.notifications.NotificationListener.setPcActive(on)
                    true
                }
                else -> false
            }
        }.onFailure { Log.w(TAG, "toggle $id falhou", it) }.getOrDefault(false)

        if (ok && id != "pc_active" && id != "wifi_scan") {
            pushIfChanged()
            schedulePush()
            mainHandler.removeCallbacks(followUpRunnable)
            mainHandler.postDelayed(followUpRunnable, FOLLOW_UP_MS)
        }
        return ok
    }

    private fun schedulePush() {
        mainHandler.removeCallbacks(emitRunnable)
        mainHandler.postDelayed(emitRunnable, DEBOUNCE_MS)
    }

    @Synchronized
    private fun pushIfChanged() {
        val current = snapshot()
        if (current != lastSent) {
            lastSent = current
            onChanged(current)
        }
    }

    private fun readDnd(): Boolean {
        val filter = notifications?.currentInterruptionFilter ?: return false
        return filter != NotificationManager.INTERRUPTION_FILTER_ALL &&
            filter != NotificationManager.INTERRUPTION_FILTER_UNKNOWN
    }

    private fun setDnd(on: Boolean): Boolean {
        val nm = notifications ?: return false
        if (!nm.isNotificationPolicyAccessGranted) return false
        nm.setInterruptionFilter(
            if (on) NotificationManager.INTERRUPTION_FILTER_PRIORITY
            else NotificationManager.INTERRUPTION_FILTER_ALL,
        )
        return true
    }

    private fun readRinger(): String = when (audio?.ringerMode) {
        AudioManager.RINGER_MODE_SILENT -> "silent"
        AudioManager.RINGER_MODE_VIBRATE -> "vibrate"
        else -> "ring"
    }

    private fun setRinger(mode: String): Boolean {
        val am = audio ?: return false
        val target = when (mode) {
            "ring" -> AudioManager.RINGER_MODE_NORMAL
            "vibrate" -> AudioManager.RINGER_MODE_VIBRATE
            "silent" -> {
                if (notifications?.isNotificationPolicyAccessGranted != true) return false
                AudioManager.RINGER_MODE_SILENT
            }
            else -> return false
        }
        if (am.ringerMode == AudioManager.RINGER_MODE_SILENT &&
            notifications?.isNotificationPolicyAccessGranted == false
        ) {
            return false
        }
        am.ringerMode = target
        return true
    }

    private fun setFlashlight(on: Boolean): Boolean {
        val camId = torchCameraId ?: return false
        val cm = camera ?: return false
        cm.setTorchMode(camId, on)
        torchOn = on
        return true
    }

    private fun readVolume(): Int {
        val am = audio ?: return 0
        val min = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            am.getStreamMinVolume(AudioManager.STREAM_MUSIC)
        } else {
            0
        }
        val max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC).coerceAtLeast(min + 1)
        val cur = am.getStreamVolume(AudioManager.STREAM_MUSIC).coerceIn(min, max)
        return (((cur - min) * 100f) / (max - min)).roundToInt().coerceIn(0, 100)
    }

    private fun setVolume(level: Int): Boolean {
        val am = audio ?: return false
        val clamped = level.coerceIn(0, 100)
        val min = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            am.getStreamMinVolume(AudioManager.STREAM_MUSIC)
        } else {
            0
        }
        val max = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC).coerceAtLeast(min + 1)
        val index = min + ((clamped / 100f) * (max - min)).roundToInt()
        val wanted = index.coerceIn(min, max)
        am.setStreamVolume(AudioManager.STREAM_MUSIC, wanted, 0)
        if (am.getStreamVolume(AudioManager.STREAM_MUSIC) != wanted && Elevated.running) {
            Elevated.setMusicVolume(wanted)
        }
        return true
    }

    private fun readBrightness(): Int {
        val raw = runCatching {
            Settings.System.getInt(context.contentResolver, Settings.System.SCREEN_BRIGHTNESS, 128)
        }.getOrDefault(128)
        return ((raw.coerceIn(0, 255) * 100f) / 255f).roundToInt().coerceIn(0, 100)
    }

    private fun setBrightness(level: Int): Boolean {
        val raw = ((level.coerceIn(0, 100) * 255f) / 100f).roundToInt().coerceIn(0, 255)
        if (Settings.System.canWrite(context)) {
            return Settings.System.putInt(
                context.contentResolver,
                Settings.System.SCREEN_BRIGHTNESS,
                raw,
            )
        }
        if (Elevated.running) {
            return Elevated.runCommand("settings put system screen_brightness $raw")
        }
        return false
    }

    private fun findTorchCamera(): String? = runCatching {
        if (Build.HARDWARE == "ranchu" || Build.HARDWARE == "goldfish" || Build.MODEL.contains("sdk_gphone")) {
            return null
        }
        val cm = camera ?: return null
        var fallback: String? = null
        for (id in cm.cameraIdList) {
            val chars = cm.getCameraCharacteristics(id)
            if (chars.get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true) {
                if (chars.get(CameraCharacteristics.LENS_FACING) == CameraCharacteristics.LENS_FACING_BACK) {
                    return id
                }
                if (fallback == null) fallback = id
            }
        }
        fallback
    }.getOrNull()

    companion object {
        private const val TAG = "PhoneToggles"
        private const val DEBOUNCE_MS = 120L
        private const val FOLLOW_UP_MS = 450L
        private const val VOLUME_CHANGED_ACTION = "android.media.VOLUME_CHANGED_ACTION"

        fun hasDndAccess(context: Context): Boolean =
            context.getSystemService(NotificationManager::class.java)?.isNotificationPolicyAccessGranted == true

        fun hasWriteSettings(context: Context): Boolean = Settings.System.canWrite(context)

        fun canChangeDnd(context: Context): Boolean = hasDndAccess(context)

        fun canChangeBrightness(context: Context): Boolean =
            hasWriteSettings(context) || Elevated.running

        fun canChangeWifi(context: Context): Boolean =
            Elevated.running || Build.VERSION.SDK_INT < Build.VERSION_CODES.Q

        fun canChangeBluetooth(): Boolean = true

        fun dndSettingsIntent(): Intent =
            Intent(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        fun writeSettingsIntent(context: Context): Intent =
            Intent(
                Settings.ACTION_MANAGE_WRITE_SETTINGS,
                Uri.fromParts("package", context.packageName, null),
            ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }
}
