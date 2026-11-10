// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.power

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.net.Uri
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.util.Calendar

/**
 * Information regarding an active sleep timer.
 */
data class SleepTimerInfo(
    val pcId: String,
    val pcName: String,
    val action: PowerActionType,
    val triggerAtMillis: Long,
) {
    fun toJson(): JSONObject {
        val json = JSONObject()
        json.put("pcId", pcId)
        json.put("pcName", pcName)
        json.put("action", action.name)
        json.put("triggerAtMillis", triggerAtMillis)
        return json
    }

    companion object {
        fun fromJson(json: JSONObject): SleepTimerInfo {
            return SleepTimerInfo(
                pcId = json.getString("pcId"),
                pcName = json.optString("pcName", ""),
                action = PowerActionType.fromString(json.getString("action")),
                triggerAtMillis = json.getLong("triggerAtMillis"),
            )
        }
    }
}

/**
 * Manages power schedules and countdown sleep timers.
 * Handles persistence in SharedPreferences and exact alarm registrations via [AlarmManager].
 */
class PowerSchedulerManager(private val context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val lock = Any()

    /**
     * Returns all saved schedules, optionally filtered by [pcId].
     */
    fun getSchedules(pcId: String? = null): List<PowerSchedule> {
        val all = loadSchedules()
        return if (pcId != null) {
            all.filter { it.pcId == pcId }
        } else {
            all
        }
    }

    /**
     * Returns a specific schedule by [id], or null if not found.
     */
    fun getSchedule(id: String): PowerSchedule? {
        return loadSchedules().firstOrNull { it.id == id }
    }

    /**
     * Adds a new schedule or replaces an existing one with matching ID,
     * then schedules the exact alarm if enabled.
     */
    fun addSchedule(schedule: PowerSchedule) {
        synchronized(lock) {
            val list = loadSchedules().toMutableList()
            val existingIndex = list.indexOfFirst { it.id == schedule.id }
            if (existingIndex >= 0) {
                list[existingIndex] = schedule
            } else {
                list.add(schedule)
            }
            saveSchedules(list)
        }
        if (schedule.enabled) {
            scheduleAlarm(schedule)
        } else {
            cancelAlarm(schedule.id)
        }
    }

    /**
     * Updates an existing schedule and refreshes its alarm.
     */
    fun updateSchedule(schedule: PowerSchedule) {
        addSchedule(schedule)
    }

    /**
     * Removes the schedule with matching [id] and cancels any pending alarm.
     */
    fun removeSchedule(id: String) {
        synchronized(lock) {
            val list = loadSchedules().filterNot { it.id == id }
            saveSchedules(list)
        }
        cancelAlarm(id)
    }

    /**
     * Enables or disables a schedule by [id].
     */
    fun toggleSchedule(id: String, enabled: Boolean) {
        val existing = getSchedule(id) ?: return
        val updated = existing.copy(enabled = enabled)
        addSchedule(updated)
    }

    /**
     * Records the execution timestamp of a schedule.
     */
    fun recordTrigger(id: String, timestamp: Long = System.currentTimeMillis()) {
        synchronized(lock) {
            val list = loadSchedules().toMutableList()
            val index = list.indexOfFirst { it.id == id }
            if (index >= 0) {
                list[index] = list[index].copy(lastTriggered = timestamp)
                saveSchedules(list)
            }
        }
    }

    /**
     * Calculates the next epoch timestamp (in milliseconds) for the given [schedule].
     */
    fun calculateNextTriggerMillis(
        schedule: PowerSchedule,
        nowMillis: Long = System.currentTimeMillis(),
    ): Long {
        if (schedule.daysOfWeek.isEmpty()) {
            val target = Calendar.getInstance().apply {
                timeInMillis = nowMillis
                set(Calendar.HOUR_OF_DAY, schedule.hour)
                set(Calendar.MINUTE, schedule.minute)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
                if (timeInMillis <= nowMillis) {
                    add(Calendar.DAY_OF_YEAR, 1)
                }
            }
            return target.timeInMillis
        }

        for (offset in 0..7) {
            val candidate = Calendar.getInstance().apply {
                timeInMillis = nowMillis
                add(Calendar.DAY_OF_YEAR, offset)
                set(Calendar.HOUR_OF_DAY, schedule.hour)
                set(Calendar.MINUTE, schedule.minute)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }
            val dayOfWeek = candidate.get(Calendar.DAY_OF_WEEK)
            if (schedule.daysOfWeek.contains(dayOfWeek) && candidate.timeInMillis > nowMillis) {
                return candidate.timeInMillis
            }
        }

        return Calendar.getInstance().apply {
            timeInMillis = nowMillis
            add(Calendar.DAY_OF_YEAR, 1)
            set(Calendar.HOUR_OF_DAY, schedule.hour)
            set(Calendar.MINUTE, schedule.minute)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }.timeInMillis
    }

    /**
     * Registers an exact alarm for the given [schedule] via [AlarmManager.setExactAndAllowWhileIdle].
     */
    fun scheduleAlarm(schedule: PowerSchedule) {
        if (!schedule.enabled) {
            cancelAlarm(schedule.id)
            return
        }

        val triggerAtMillis = calculateNextTriggerMillis(schedule)
        val intent = Intent(context, PowerScheduleReceiver::class.java).apply {
            action = PowerScheduleReceiver.ACTION_SCHEDULE_TRIGGER
            data = Uri.parse("nectarlink://power_schedule/${schedule.id}")
            putExtra(PowerScheduleReceiver.EXTRA_SCHEDULE_ID, schedule.id)
            putExtra(PowerScheduleReceiver.EXTRA_PC_ID, schedule.pcId)
            putExtra(PowerScheduleReceiver.EXTRA_PC_NAME, schedule.pcName)
            putExtra(PowerScheduleReceiver.EXTRA_ACTION, schedule.action.name)
            putExtra(PowerScheduleReceiver.EXTRA_IS_SLEEP_TIMER, false)
        }

        val pendingIntent = PendingIntent.getBroadcast(
            context,
            schedule.id.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        setAlarm(triggerAtMillis, pendingIntent)
    }

    /**
     * Cancels any pending alarm for the given [scheduleId].
     */
    fun cancelAlarm(scheduleId: String) {
        val intent = Intent(context, PowerScheduleReceiver::class.java).apply {
            action = PowerScheduleReceiver.ACTION_SCHEDULE_TRIGGER
            data = Uri.parse("nectarlink://power_schedule/$scheduleId")
        }
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            scheduleId.hashCode(),
            intent,
            PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE,
        )
        if (pendingIntent != null) {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager
            alarmManager?.cancel(pendingIntent)
            pendingIntent.cancel()
        }
    }

    /**
     * Re-registers all active schedules and sleep timers with AlarmManager.
     * Useful after system reboot or package update.
     */
    fun rescheduleAll() {
        val schedules = loadSchedules()
        for (schedule in schedules) {
            if (schedule.enabled) {
                scheduleAlarm(schedule)
            } else {
                cancelAlarm(schedule.id)
            }
        }

        val now = System.currentTimeMillis()
        val sleepTimers = loadAllSleepTimers()
        for ((pcId, info) in sleepTimers) {
            if (info.triggerAtMillis > now) {
                val timerId = "sleep_timer_$pcId"
                val intent = Intent(context, PowerScheduleReceiver::class.java).apply {
                    action = PowerScheduleReceiver.ACTION_SCHEDULE_TRIGGER
                    data = Uri.parse("nectarlink://sleep_timer/$pcId")
                    putExtra(PowerScheduleReceiver.EXTRA_SCHEDULE_ID, timerId)
                    putExtra(PowerScheduleReceiver.EXTRA_PC_ID, info.pcId)
                    putExtra(PowerScheduleReceiver.EXTRA_PC_NAME, info.pcName)
                    putExtra(PowerScheduleReceiver.EXTRA_ACTION, info.action.name)
                    putExtra(PowerScheduleReceiver.EXTRA_IS_SLEEP_TIMER, true)
                }
                val pendingIntent = PendingIntent.getBroadcast(
                    context,
                    timerId.hashCode(),
                    intent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
                )
                setAlarm(info.triggerAtMillis, pendingIntent)
            } else {
                clearSleepTimer(pcId)
            }
        }
    }

    // ---- Sleep Timer Support ----

    /**
     * Starts a countdown sleep timer for [pcId] to trigger [action] in [minutes] minutes.
     */
    fun startSleepTimer(
        pcId: String,
        pcName: String,
        action: PowerActionType,
        minutes: Int,
    ) {
        val timerId = "sleep_timer_$pcId"
        val triggerAtMillis = System.currentTimeMillis() + (minutes * 60_000L)
        val info = SleepTimerInfo(
            pcId = pcId,
            pcName = pcName,
            action = action,
            triggerAtMillis = triggerAtMillis,
        )

        saveSleepTimer(info)

        val intent = Intent(context, PowerScheduleReceiver::class.java).apply {
            action = PowerScheduleReceiver.ACTION_SCHEDULE_TRIGGER
            data = Uri.parse("nectarlink://sleep_timer/$pcId")
            putExtra(PowerScheduleReceiver.EXTRA_SCHEDULE_ID, timerId)
            putExtra(PowerScheduleReceiver.EXTRA_PC_ID, pcId)
            putExtra(PowerScheduleReceiver.EXTRA_PC_NAME, pcName)
            putExtra(PowerScheduleReceiver.EXTRA_ACTION, action.name)
            putExtra(PowerScheduleReceiver.EXTRA_IS_SLEEP_TIMER, true)
        }

        val pendingIntent = PendingIntent.getBroadcast(
            context,
            timerId.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        setAlarm(triggerAtMillis, pendingIntent)
    }

    /**
     * Cancels an ongoing sleep timer for [pcId].
     */
    fun cancelSleepTimer(pcId: String) {
        val timerId = "sleep_timer_$pcId"
        val intent = Intent(context, PowerScheduleReceiver::class.java).apply {
            action = PowerScheduleReceiver.ACTION_SCHEDULE_TRIGGER
            data = Uri.parse("nectarlink://sleep_timer/$pcId")
        }
        val pendingIntent = PendingIntent.getBroadcast(
            context,
            timerId.hashCode(),
            intent,
            PendingIntent.FLAG_NO_CREATE or PendingIntent.FLAG_IMMUTABLE,
        )
        if (pendingIntent != null) {
            val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as? AlarmManager
            alarmManager?.cancel(pendingIntent)
            pendingIntent.cancel()
        }
        clearSleepTimer(pcId)
    }

    /**
     * Retrieves active sleep timer info for [pcId] if exists and still in future.
     */
    fun getSleepTimer(pcId: String): SleepTimerInfo? {
        val raw = prefs.getString(KEY_SLEEP_TIMER_PREFIX + pcId, null) ?: return null
        return try {
            val info = SleepTimerInfo.fromJson(JSONObject(raw))
            if (info.triggerAtMillis > System.currentTimeMillis()) {
                info
            } else {
                clearSleepTimer(pcId)
                null
            }
        } catch (_: Exception) {
            clearSleepTimer(pcId)
            null
        }
    }

    /**
     * Clears sleep timer data for [pcId].
     */
    fun clearSleepTimer(pcId: String) {
        prefs.edit().remove(KEY_SLEEP_TIMER_PREFIX + pcId).apply()
    }

    // ---- Private Helpers ----

    private fun setAlarm(triggerAtMillis: Long, pendingIntent: PendingIntent) {
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

    private fun loadSchedules(): List<PowerSchedule> {
        val raw = prefs.getString(KEY_SCHEDULES, null) ?: return emptyList()
        return try {
            val array = JSONArray(raw)
            val result = mutableListOf<PowerSchedule>()
            for (i in 0 until array.length()) {
                result.add(PowerSchedule.fromJson(array.getJSONObject(i)))
            }
            result
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun saveSchedules(list: List<PowerSchedule>) {
        val array = JSONArray()
        for (item in list) {
            array.put(item.toJson())
        }
        prefs.edit().putString(KEY_SCHEDULES, array.toString()).apply()
    }

    private fun saveSleepTimer(info: SleepTimerInfo) {
        prefs.edit()
            .putString(KEY_SLEEP_TIMER_PREFIX + info.pcId, info.toJson().toString())
            .apply()
    }

    private fun loadAllSleepTimers(): Map<String, SleepTimerInfo> {
        val result = mutableMapOf<String, SleepTimerInfo>()
        for ((key, value) in prefs.all) {
            if (key.startsWith(KEY_SLEEP_TIMER_PREFIX) && value is String) {
                try {
                    val info = SleepTimerInfo.fromJson(JSONObject(value))
                    result[info.pcId] = info
                } catch (_: Exception) {
                    // Ignore corrupted entries
                }
            }
        }
        return result
    }

    companion object {
        private const val PREFS_NAME = "power_schedules_prefs"
        private const val KEY_SCHEDULES = "schedules_data"
        private const val KEY_SLEEP_TIMER_PREFIX = "sleep_timer_"
    }
}
