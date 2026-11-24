// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.power

import android.Manifest
import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import app.nectarlink.android.NectarlinkApplication
import app.nectarlink.android.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Gerencia alarmes de agendamento de energia, disparo Wake-on-LAN e notificacoes
 * de contagem regressiva com opcoes de Cancelar e Adiar antes de executar acoes no PC.
 */
class PowerScheduleReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACTION_SCHEDULE_TRIGGER -> handleScheduleTrigger(context, intent)
            ACTION_EXECUTE_POWER -> handleExecutePower(context, intent)
            ACTION_CANCEL_POWER -> handleCancelPower(context, intent)
            ACTION_SNOOZE_POWER -> handleSnoozePower(context, intent)
        }
    }

    private fun handleScheduleTrigger(context: Context, intent: Intent) {
        val scheduleId = intent.getStringExtra(EXTRA_SCHEDULE_ID)?.takeIf { it.isNotBlank() } ?: return
        val pcId = intent.getStringExtra(EXTRA_PC_ID)?.takeIf { it.isNotBlank() } ?: return
        val pcName = intent.getStringExtra(EXTRA_PC_NAME)?.takeIf { it.isNotBlank() } ?: pcId
        val action = PowerActionType.fromStringOrNull(intent.getStringExtra(EXTRA_ACTION)) ?: return
        val isSleepTimer = intent.getBooleanExtra(EXTRA_IS_SLEEP_TIMER, false)

        val manager = PowerSchedulerManager(context)
        if (!isTaskActive(manager, scheduleId, pcId, isSleepTimer)) return

        if (action == PowerActionType.Wake) {
            dispatchAsyncPowerAction(context, scheduleId, pcId, isSleepTimer) {
                val app = context.applicationContext as? NectarlinkApplication
                app?.core?.let { core ->
                    core.start()
                    core.wakeNow(pcId)
                }
            }
            return
        }

        // Pre-aquecimento do no durante o aviso de 60s para garantir conexao pronta na execucao
        (context.applicationContext as? NectarlinkApplication)?.core?.start()

        val notifId = getNotificationId(scheduleId)
        createNotificationChannel(context)

        val contentText = when (action) {
            PowerActionType.Shutdown -> context.getString(R.string.power_schedule_warning_shutdown, pcName)
            PowerActionType.Reboot -> context.getString(R.string.power_schedule_warning_reboot, pcName)
            PowerActionType.Sleep -> context.getString(R.string.power_schedule_warning_sleep, pcName)
            PowerActionType.Lock -> context.getString(R.string.power_schedule_warning_lock, pcName)
            PowerActionType.Wake -> return
        }

        val cancelIntent = Intent(context, PowerScheduleReceiver::class.java).apply {
            this.action = ACTION_CANCEL_POWER
            data = Uri.parse("nectarlink://power_cancel/$scheduleId")
            putExtra(EXTRA_SCHEDULE_ID, scheduleId)
            putExtra(EXTRA_PC_ID, pcId)
            putExtra(EXTRA_NOTIFICATION_ID, notifId)
            putExtra(EXTRA_IS_SLEEP_TIMER, isSleepTimer)
        }
        val cancelPendingIntent = PendingIntent.getBroadcast(
            context,
            (scheduleId + "_cancel").hashCode(),
            cancelIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val snoozeIntent = Intent(context, PowerScheduleReceiver::class.java).apply {
            this.action = ACTION_SNOOZE_POWER
            data = Uri.parse("nectarlink://power_snooze/$scheduleId")
            putExtra(EXTRA_SCHEDULE_ID, scheduleId)
            putExtra(EXTRA_PC_ID, pcId)
            putExtra(EXTRA_PC_NAME, pcName)
            putExtra(EXTRA_ACTION, action.name)
            putExtra(EXTRA_NOTIFICATION_ID, notifId)
            putExtra(EXTRA_IS_SLEEP_TIMER, isSleepTimer)
        }
        val snoozePendingIntent = PendingIntent.getBroadcast(
            context,
            (scheduleId + "_snooze").hashCode(),
            snoozeIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(context.getString(R.string.power_schedule_warning_title, pcName))
            .setContentText(contentText)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setOngoing(true)
            .setAutoCancel(false)
            .addAction(0, context.getString(R.string.power_schedule_action_cancel), cancelPendingIntent)
            .addAction(0, context.getString(R.string.power_schedule_action_snooze), snoozePendingIntent)
        app.nectarlink.android.notifications.NotificationSoundHelper.applyBuilderSound(builder)
        val notification = builder.build()

        if (hasNotificationPermission(context)) {
            NotificationManagerCompat.from(context).notify(notifId, notification)
        }

        val executeIntent = Intent(context, PowerScheduleReceiver::class.java).apply {
            this.action = ACTION_EXECUTE_POWER
            data = Uri.parse("nectarlink://power_execute/$scheduleId")
            putExtra(EXTRA_SCHEDULE_ID, scheduleId)
            putExtra(EXTRA_PC_ID, pcId)
            putExtra(EXTRA_PC_NAME, pcName)
            putExtra(EXTRA_ACTION, action.name)
            putExtra(EXTRA_NOTIFICATION_ID, notifId)
            putExtra(EXTRA_IS_SLEEP_TIMER, isSleepTimer)
        }
        val executePendingIntent = PendingIntent.getBroadcast(
            context,
            (scheduleId + "_execute").hashCode(),
            executeIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        setAlarm(context, System.currentTimeMillis() + WARNING_DELAY_MS, executePendingIntent)
    }

    private fun handleExecutePower(context: Context, intent: Intent) {
        val scheduleId = intent.getStringExtra(EXTRA_SCHEDULE_ID)?.takeIf { it.isNotBlank() } ?: return
        val pcId = intent.getStringExtra(EXTRA_PC_ID)?.takeIf { it.isNotBlank() } ?: return
        val action = PowerActionType.fromStringOrNull(intent.getStringExtra(EXTRA_ACTION)) ?: return
        val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, getNotificationId(scheduleId))
        val isSleepTimer = intent.getBooleanExtra(EXTRA_IS_SLEEP_TIMER, false)

        NotificationManagerCompat.from(context).cancel(notifId)

        // Validacao fail-closed: garante que o agendamento ou temporizador nao foi cancelado/excluido na janela de 60s
        val manager = PowerSchedulerManager(context)
        if (!isTaskActive(manager, scheduleId, pcId, isSleepTimer)) return

        dispatchAsyncPowerAction(context, scheduleId, pcId, isSleepTimer) {
            val app = context.applicationContext as? NectarlinkApplication
            app?.core?.let { core ->
                core.start()
                core.pcPowerNow(pcId, action.name)
            }
        }
    }

    private fun isTaskActive(
        manager: PowerSchedulerManager,
        scheduleId: String,
        pcId: String,
        isSleepTimer: Boolean,
    ): Boolean {
        return if (isSleepTimer) {
            manager.getSleepTimerEntry(pcId) != null
        } else {
            manager.getSchedule(scheduleId)?.enabled == true
        }
    }

    /**
     * Usa goAsync() em Dispatchers.IO para manter o BroadcastReceiver ativo em modo Doze
     * ate a conclusao do disparo de energia e atualizacao do estado do agendamento.
     */
    private fun dispatchAsyncPowerAction(
        context: Context,
        scheduleId: String,
        pcId: String,
        isSleepTimer: Boolean,
        block: suspend () -> Unit,
    ) {
        val pendingResult = goAsync()
        receiverScope.launch {
            try {
                withTimeoutOrNull(GO_ASYNC_TIMEOUT_MS) {
                    block()
                }
            } finally {
                runCatching {
                    finalizeScheduleExecution(context, scheduleId, pcId, isSleepTimer)
                }
                pendingResult.finish()
            }
        }
    }

    private fun finalizeScheduleExecution(
        context: Context,
        scheduleId: String,
        pcId: String,
        isSleepTimer: Boolean,
    ) {
        val manager = PowerSchedulerManager(context)
        if (isSleepTimer) {
            manager.clearSleepTimer(pcId)
            return
        }
        manager.recordTrigger(scheduleId)
        val schedule = manager.getSchedule(scheduleId) ?: return
        if (!schedule.enabled) return
        if (schedule.daysOfWeek.isEmpty()) {
            // Desativa automaticamente agendamentos de disparo unico apos execucao
            manager.toggleSchedule(scheduleId, false)
        } else {
            manager.scheduleAlarm(schedule)
        }
    }

    private fun handleCancelPower(context: Context, intent: Intent) {
        val scheduleId = intent.getStringExtra(EXTRA_SCHEDULE_ID)?.takeIf { it.isNotBlank() } ?: return
        val pcId = intent.getStringExtra(EXTRA_PC_ID)?.takeIf { it.isNotBlank() } ?: return
        val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, getNotificationId(scheduleId))
        val isSleepTimer = intent.getBooleanExtra(EXTRA_IS_SLEEP_TIMER, false)

        cancelExecuteAlarm(context, scheduleId)
        NotificationManagerCompat.from(context).cancel(notifId)

        val manager = PowerSchedulerManager(context)
        if (isSleepTimer) {
            manager.clearSleepTimer(pcId)
        } else {
            val schedule = manager.getSchedule(scheduleId) ?: return
            if (!schedule.enabled) return
            if (schedule.daysOfWeek.isEmpty()) {
                manager.toggleSchedule(scheduleId, false)
            } else {
                manager.scheduleAlarm(schedule)
            }
        }
    }

    private fun handleSnoozePower(context: Context, intent: Intent) {
        val scheduleId = intent.getStringExtra(EXTRA_SCHEDULE_ID)?.takeIf { it.isNotBlank() } ?: return
        val pcId = intent.getStringExtra(EXTRA_PC_ID)?.takeIf { it.isNotBlank() } ?: return
        val pcName = intent.getStringExtra(EXTRA_PC_NAME)?.takeIf { it.isNotBlank() } ?: pcId
        val action = PowerActionType.fromStringOrNull(intent.getStringExtra(EXTRA_ACTION)) ?: return
        val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, getNotificationId(scheduleId))
        val isSleepTimer = intent.getBooleanExtra(EXTRA_IS_SLEEP_TIMER, false)

        cancelExecuteAlarm(context, scheduleId)
        NotificationManagerCompat.from(context).cancel(notifId)

        val manager = PowerSchedulerManager(context)
        if (isSleepTimer) {
            // Persiste novo horario adiado e agenda com URI/requestCode canonicos do sleep timer
            manager.rescheduleSleepTimerSnooze(pcId, pcName, action, SNOOZE_DELAY_MS)
            return
        }

        if (manager.getSchedule(scheduleId)?.enabled != true) return

        val triggerIntent = Intent(context, PowerScheduleReceiver::class.java).apply {
            this.action = ACTION_SCHEDULE_TRIGGER
            data = Uri.parse("nectarlink://power_schedule/$scheduleId")
            putExtra(EXTRA_SCHEDULE_ID, scheduleId)
            putExtra(EXTRA_PC_ID, pcId)
            putExtra(EXTRA_PC_NAME, pcName)
            putExtra(EXTRA_ACTION, action.name)
            putExtra(EXTRA_IS_SLEEP_TIMER, false)
        }

        val triggerPendingIntent = PendingIntent.getBroadcast(
            context,
            scheduleId.hashCode(),
            triggerIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        setAlarm(context, System.currentTimeMillis() + SNOOZE_DELAY_MS, triggerPendingIntent)
    }

    private fun cancelExecuteAlarm(context: Context, scheduleId: String) {
        val executeIntent = Intent(context, PowerScheduleReceiver::class.java).apply {
            this.action = ACTION_EXECUTE_POWER
            data = Uri.parse("nectarlink://power_execute/$scheduleId")
        }
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            (scheduleId + "_execute").hashCode(),
            executeIntent,
            PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE,
        )
        if (pendingIntent != null) {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager
            alarmManager?.cancel(pendingIntent)
            pendingIntent.cancel()
        }
    }

    private fun setAlarm(context: Context, triggerAtMillis: Long, pendingIntent: PendingIntent) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                if (alarmManager.canScheduleExactAlarms()) {
                    alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAtMillis, pendingIntent)
                } else {
                    alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAtMillis, pendingIntent)
                }
            } else {
                alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAtMillis, pendingIntent)
            }
        } catch (_: SecurityException) {
            alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAtMillis, pendingIntent)
        }
    }

    private fun createNotificationChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                context.getString(R.string.channel_power_schedule),
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                description = context.getString(R.string.channel_power_schedule_desc)
                app.nectarlink.android.notifications.NotificationSoundHelper.configureChannel(this)
            }
            val nm = context.getSystemService(NotificationManager::class.java)
            nm?.createNotificationChannel(channel)
        }
    }

    private fun hasNotificationPermission(context: Context): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        } else {
            true
        }
    }

    private fun getNotificationId(scheduleId: String): Int {
        return 0x505752 + (scheduleId.hashCode() and 0x000FFFFF)
    }

    companion object {
        const val ACTION_SCHEDULE_TRIGGER = "app.nectarlink.android.power.ACTION_SCHEDULE_TRIGGER"
        const val ACTION_EXECUTE_POWER = "app.nectarlink.android.power.ACTION_EXECUTE_POWER"
        const val ACTION_CANCEL_POWER = "app.nectarlink.android.power.ACTION_CANCEL_POWER"
        const val ACTION_SNOOZE_POWER = "app.nectarlink.android.power.ACTION_SNOOZE_POWER"

        const val EXTRA_SCHEDULE_ID = "schedule_id"
        const val EXTRA_PC_ID = "pc_id"
        const val EXTRA_PC_NAME = "pc_name"
        const val EXTRA_ACTION = "power_action"
        const val EXTRA_IS_SLEEP_TIMER = "is_sleep_timer"
        const val EXTRA_NOTIFICATION_ID = "notification_id"

        const val CHANNEL_ID = "power_schedule_v2"
        private const val WARNING_DELAY_MS = 60_000L
        private const val SNOOZE_DELAY_MS = 10 * 60_000L
        private const val GO_ASYNC_TIMEOUT_MS = 8_000L
        private val receiverScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    }
}
