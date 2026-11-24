// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.notifications

import android.app.Notification
import android.app.NotificationChannel
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.net.Uri
import androidx.core.app.NotificationCompat

/**
 * Utilitario centralizado para padronizacao de som, toque e vibracao
 * nos canais e construtores de notificacao do Conexao Movel (NectarLink).
 */
object NotificationSoundHelper {

    val defaultSoundUri: Uri by lazy {
        RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)
            ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
    }

    val notificationAudioAttributes: AudioAttributes by lazy {
        AudioAttributes.Builder()
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
            .build()
    }

    val defaultVibrationPattern = longArrayOf(0, 250, 150, 250)

    /**
     * Aplica som do sistema, atributos de audio e padrao de vibracao a um canal.
     */
    fun configureChannel(channel: NotificationChannel) {
        channel.setSound(defaultSoundUri, notificationAudioAttributes)
        channel.enableVibration(true)
        channel.vibrationPattern = defaultVibrationPattern
        channel.enableLights(true)
    }

    /**
     * Aplica toque sonoro, vibracao e luzes ao construtor de notificacao AndroidX.
     */
    fun applyBuilderSound(builder: NotificationCompat.Builder, silent: Boolean = false) {
        if (silent) {
            builder.setSilent(true)
        } else {
            builder.setDefaults(
                NotificationCompat.DEFAULT_SOUND or
                    NotificationCompat.DEFAULT_VIBRATE or
                    NotificationCompat.DEFAULT_LIGHTS,
            )
            builder.setSound(defaultSoundUri)
            builder.setVibrate(defaultVibrationPattern)
        }
    }

    /**
     * Aplica toque sonoro, vibracao e luzes ao construtor de notificacao nativo do Android.
     */
    fun applyBuilderSound(builder: Notification.Builder, silent: Boolean = false) {
        if (!silent) {
            builder.setDefaults(
                Notification.DEFAULT_SOUND or
                    Notification.DEFAULT_VIBRATE or
                    Notification.DEFAULT_LIGHTS,
            )
            builder.setSound(defaultSoundUri, notificationAudioAttributes)
            builder.setVibrate(defaultVibrationPattern)
        }
    }
}
