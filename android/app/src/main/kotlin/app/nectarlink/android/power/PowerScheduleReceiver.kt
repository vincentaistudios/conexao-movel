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

/**
 * Handles power scheduling alarms, Wake-on-LAN dispatch, and countdown notifications
 * with interactive Cancel and Snooze options before executing sleep, shutdown, reboot, or lock.
 */
class PowerScheduleReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACTION_SCHEDULE_TRIGGER -> handleScheduleTrigger(context, intent)
            ACTION_EXECUTE_POWER -> handleExecutePower(context, intent)
            ACTION_CANCEL_POWER -> handleCancelPower(context, intent)
            ACTION_SNOOZE_POWER -> handleSnoozePower(context, intent)
            Intent.ACTION_BOOT_COMPLETED,
            Intent.ACTION_MY_PACKAGE_REPLACED -> {
                val manager = PowerSchedulerManager(context)
                manager.rescheduleAll()
            }
        }
    }

    private fun handleScheduleTrigger(context: Context, intent: Intent) {
        val scheduleId = intent.getStringExtra(EXTRA_SCHEDULE_ID) ?: return
        val pcId = intent.getStringExtra(EXTRA_PC_ID) ?: return
        val pcName = intent.getStringExtra(EXTRA_PC_NAME) ?: pcId
        val action = PowerActionType.fromString(intent.getStringExtra(EXTRA_ACTION) ?: "Lock")
        val isSleepTimer = intent.getBooleanExtra(EXTRA_IS_SLEEP_TIMER, false)

        val manager = PowerSchedulerManager(context)

        if (action == PowerActionType.Wake) {
            val app = context.applicationContext as? NectarlinkApplication
            app?.core?.start()
            app?.core?.wake(pcId)

            if (isSleepTimer) {
                manager.clearSleepTimer(pcId)
            } else {
                manager.recordTrigger(scheduleId)
                val schedule = manager.getSchedule(scheduleId)
                if (schedule != null && schedule.daysOfWeek.isNotEmpty() && schedule.enabled) {
                    manager.scheduleAlarm(schedule)
                }
            }
            return
        }

        // For Shutdown, Reboot, Sleep, or Lock: post warning notification 60s ahead
        val notifId = getNotificationId(scheduleId)
        createNotificationChannel(context)

        val contentText = when (action) {
            PowerActionType.Shutdown -> context.getString(R.string.power_schedule_warning_shutdown, pcName)
            PowerActionType.Reboot -> context.getString(R.string.power_schedule_warning_reboot, pcName)
            PowerActionType.Sleep -> context.getString(R.string.power_schedule_warning_sleep, pcName)
            PowerActionType.Lock -> context.getString(R.string.power_schedule_warning_lock, pcName)
            PowerActionType.Wake -> ""
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

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(context.getString(R.string.power_schedule_warning_title, pcName))
            .setContentText(contentText)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setOngoing(true)
            .setAutoCancel(false)
            .addAction(0, context.getString(R.string.power_schedule_action_cancel), cancelPendingIntent)
            .addAction(0, context.getString(R.string.power_schedule_action_snooze), snoozePendingIntent)
            .build()

        if (hasNotificationPermission(context)) {
            NotificationManagerCompat.from(context).notify(notifId, notification)
        }

        // Schedule final execution 60 seconds from now
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
        val scheduleId = intent.getStringExtra(EXTRA_SCHEDULE_ID) ?: return
        val pcId = intent.getStringExtra(EXTRA_PC_ID) ?: return
        val action = PowerActionType.fromString(intent.getStringExtra(EXTRA_ACTION) ?: "Lock")
        val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, getNotificationId(scheduleId))
        val isSleepTimer = intent.getBooleanExtra(EXTRA_IS_SLEEP_TIMER, false)

        NotificationManagerCompat.from(context).cancel(notifId)

        val app = context.applicationContext as? NectarlinkApplication
        app?.core?.start()
        app?.core?.pcPower(pcId, action.name)

        val manager = PowerSchedulerManager(context)
        if (isSleepTimer) {
            manager.clearSleepTimer(pcId)
        } else {
            manager.recordTrigger(scheduleId)
            val schedule = manager.getSchedule(scheduleId)
            if (schedule != null && schedule.daysOfWeek.isNotEmpty() && schedule.enabled) {
                manager.scheduleAlarm(schedule)
            }
        }
    }

    private fun handleCancelPower(context: Context, intent: Intent) {
        val scheduleId = intent.getStringExtra(EXTRA_SCHEDULE_ID) ?: return
        val pcId = intent.getStringExtra(EXTRA_PC_ID) ?: return
        val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, getNotificationId(scheduleId))
        val isSleepTimer = intent.getBooleanExtra(EXTRA_IS_SLEEP_TIMER, false)

        cancelExecuteAlarm(context, scheduleId)
        NotificationManagerCompat.from(context).cancel(notifId)

        val manager = PowerSchedulerManager(context)
        if (isSleepTimer) {
            manager.clearSleepTimer(pcId)
        } else {
            val schedule = manager.getSchedule(scheduleId)
            if (schedule != null && schedule.daysOfWeek.isNotEmpty() && schedule.enabled) {
                manager.scheduleAlarm(schedule)
            }
        }
    }

    private fun handleSnoozePower(context: Context, intent: Intent) {
        val scheduleId = intent.getStringExtra(EXTRA_SCHEDULE_ID) ?: return
        val pcId = intent.getStringExtra(EXTRA_PC_ID) ?: return
        val pcName = intent.getStringExtra(EXTRA_PC_NAME) ?: pcId
        val action = PowerActionType.fromString(intent.getStringExtra(EXTRA_ACTION) ?: "Lock")
        val notifId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, getNotificationId(scheduleId))
        val isSleepTimer = intent.getBooleanExtra(EXTRA_IS_SLEEP_TIMER, false)

        cancelExecuteAlarm(context, scheduleId)
        NotificationManagerCompat.from(context).cancel(notifId)

        val triggerIntent = Intent(context, PowerScheduleReceiver::class.java).apply {
            this.action = ACTION_SCHEDULE_TRIGGER
            data = Uri.parse("nectarlink://power_schedule/$scheduleId")
            putExtra(EXTRA_SCHEDULE_ID, scheduleId)
            putExtra(EXTRA_PC_ID, pcId)
            putExtra(EXTRA_PC_NAME, pcName)
            putExtra(EXTRA_ACTION, action.name)
            putExtra(EXTRA_IS_SLEEP_TIMER, isSleepTimer)
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
        } catch (e: SecurityException) {
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
                enableVibration(true)
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
        return 0x505752 + (scheduleId.hashCode() and 0x000FFFFF) // "PWR" base
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

        const val CHANNEL_ID = "power_schedule"
        private const val WARNING_DELAY_MS = 60_000L
        private const val SNOOZE_DELAY_MS = 10 * 60_000L
    }
}
