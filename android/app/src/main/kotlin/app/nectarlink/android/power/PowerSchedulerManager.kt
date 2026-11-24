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
 * Informacoes persistidas sobre um temporizador de sono ativo.
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
            val rawAction = json.optString("action", "")
            val parsedAction = PowerActionType.fromStringOrNull(rawAction)
                ?: throw IllegalArgumentException("Acao de temporizador invalida no JSON: $rawAction")
            return SleepTimerInfo(
                pcId = json.getString("pcId"),
                pcName = json.optString("pcName", ""),
                action = parsedAction,
                triggerAtMillis = json.getLong("triggerAtMillis"),
            )
        }
    }
}

/**
 * Gerencia agendamentos de energia e temporizadores regressivos via SharedPreferences e AlarmManager.
 */
class PowerSchedulerManager(private val context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
    private val lock = Any()

    fun getSchedules(pcId: String? = null): List<PowerSchedule> {
        val all = loadSchedules()
        return if (pcId != null) all.filter { it.pcId == pcId } else all
    }

    fun getSchedule(id: String): PowerSchedule? = loadSchedules().firstOrNull { it.id == id }

    fun addSchedule(schedule: PowerSchedule) {
        synchronized(lock) {
            val list = loadSchedules().toMutableList()
            val existingIndex = list.indexOfFirst { it.id == schedule.id }
            if (existingIndex >= 0) list[existingIndex] = schedule else list.add(schedule)
            saveSchedules(list)
        }
        if (schedule.enabled) scheduleAlarm(schedule) else cancelAlarm(schedule.id)
    }

    fun updateSchedule(schedule: PowerSchedule) {
        addSchedule(schedule)
    }

    fun removeSchedule(id: String) {
        synchronized(lock) {
            saveSchedules(loadSchedules().filterNot { it.id == id })
        }
        cancelAlarm(id)
    }

    fun toggleSchedule(id: String, enabled: Boolean) {
        val existing = getSchedule(id) ?: return
        addSchedule(existing.copy(enabled = enabled))
    }

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

    fun calculateNextTriggerMillis(
        schedule: PowerSchedule,
        nowMillis: Long = System.currentTimeMillis(),
    ): Long = Companion.calculateNextTriggerMillis(schedule, nowMillis)

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

    fun rescheduleAll() {
        for (schedule in loadSchedules()) {
            if (schedule.enabled) scheduleAlarm(schedule) else cancelAlarm(schedule.id)
        }
        val now = System.currentTimeMillis()
        for ((pcId, info) in loadAllSleepTimers()) {
            if (info.triggerAtMillis > now) {
                scheduleSleepTimerAlarm(info)
            } else {
                clearSleepTimer(pcId)
            }
        }
    }

    // ---- Suporte ao Temporizador de Sono ----

    fun startSleepTimer(
        pcId: String,
        pcName: String,
        action: PowerActionType,
        minutes: Int,
    ) {
        // Evita disparo residual caso um novo timer seja iniciado dentro da janela de aviso de 60s
        cancelPendingExecuteAlarm(sleepTimerId(pcId))
        val info = SleepTimerInfo(
            pcId = pcId,
            pcName = pcName,
            action = action,
            triggerAtMillis = System.currentTimeMillis() + (minutes * 60_000L),
        )
        saveSleepTimer(info)
        scheduleSleepTimerAlarm(info)
    }

    /**
     * Persiste e reagenda o temporizador apos adiamento (snooze) usando URI e requestCode canonicos.
     */
    fun rescheduleSleepTimerSnooze(
        pcId: String,
        pcName: String,
        action: PowerActionType,
        delayMillis: Long,
        nowMillis: Long = System.currentTimeMillis(),
    ): Long {
        val info = buildSnoozedSleepTimer(pcId, pcName, action, delayMillis, nowMillis)
        saveSleepTimer(info)
        scheduleSleepTimerAlarm(info)
        return info.triggerAtMillis
    }

    fun cancelSleepTimer(pcId: String) {
        val timerId = sleepTimerId(pcId)
        cancelPendingExecuteAlarm(timerId)
        val intent = Intent(context, PowerScheduleReceiver::class.java).apply {
            action = PowerScheduleReceiver.ACTION_SCHEDULE_TRIGGER
            data = sleepTimerUri(pcId)
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
     * Retorna o temporizador ativo se existir e estiver no futuro (somente leitura para a UI,
     * preservando a entrada persistida durante a janela de aviso de 60s ate a execucao).
     */
    fun getSleepTimer(pcId: String): SleepTimerInfo? =
        filterFutureSleepTimer(getSleepTimerEntry(pcId))

    /**
     * Retorna a entrada persistida mesmo durante a janela de aviso de 60s apos o disparo inicial,
     * permitindo que o receptor valide se o temporizador ainda existe e nao foi cancelado.
     */
    fun getSleepTimerEntry(pcId: String): SleepTimerInfo? {
        val raw = prefs.getString(KEY_SLEEP_TIMER_PREFIX + pcId, null) ?: return null
        return try {
            SleepTimerInfo.fromJson(JSONObject(raw))
        } catch (_: Exception) {
            clearSleepTimer(pcId)
            null
        }
    }

    fun clearSleepTimer(pcId: String) {
        prefs.edit().remove(KEY_SLEEP_TIMER_PREFIX + pcId).apply()
    }

    private fun scheduleSleepTimerAlarm(info: SleepTimerInfo) {
        val timerId = sleepTimerId(info.pcId)
        val intent = Intent(context, PowerScheduleReceiver::class.java).apply {
            action = PowerScheduleReceiver.ACTION_SCHEDULE_TRIGGER
            data = sleepTimerUri(info.pcId)
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
    }

    private fun cancelPendingExecuteAlarm(scheduleId: String) {
        val executeIntent = Intent(context, PowerScheduleReceiver::class.java).apply {
            action = PowerScheduleReceiver.ACTION_EXECUTE_POWER
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

    private fun sleepTimerId(pcId: String): String = "sleep_timer_$pcId"

    private fun sleepTimerUri(pcId: String): Uri = Uri.parse("nectarlink://sleep_timer/$pcId")

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
        } catch (_: SecurityException) {
            alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAtMillis, pendingIntent)
        }
    }

    private fun loadSchedules(): List<PowerSchedule> {
        val raw = prefs.getString(KEY_SCHEDULES, null) ?: return emptyList()
        return try {
            val array = JSONArray(raw)
            val result = mutableListOf<PowerSchedule>()
            for (i in 0 until array.length()) {
                runCatching { PowerSchedule.fromJson(array.getJSONObject(i)) }
                    .getOrNull()
                    ?.let { result.add(it) }
            }
            result
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun saveSchedules(list: List<PowerSchedule>) {
        val array = JSONArray()
        for (item in list) array.put(item.toJson())
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
                    // Ignora entradas corrompidas
                }
            }
        }
        return result
    }

    companion object {
        private const val PREFS_NAME = "power_schedules_prefs"
        private const val KEY_SCHEDULES = "schedules_data"
        private const val KEY_SLEEP_TIMER_PREFIX = "sleep_timer_"

        /**
         * Filtra o temporizador somente para exibicao na UI quando ainda esta no futuro,
         * sem apagar a entrada persistida usada na validacao da janela de 60s.
         */
        fun filterFutureSleepTimer(
            info: SleepTimerInfo?,
            nowMillis: Long = System.currentTimeMillis(),
        ): SleepTimerInfo? = info?.takeIf { it.triggerAtMillis > nowMillis }

        /**
         * Constroi o SleepTimerInfo atualizado para adiamento (snooze) sem depender de Context.
         */
        fun buildSnoozedSleepTimer(
            pcId: String,
            pcName: String,
            action: PowerActionType,
            delayMillis: Long,
            nowMillis: Long = System.currentTimeMillis(),
        ): SleepTimerInfo = SleepTimerInfo(
            pcId = pcId,
            pcName = pcName,
            action = action,
            triggerAtMillis = nowMillis + delayMillis,
        )

        /**
         * Calcula o proximo timestamp em milissegundos para disparo unico (daysOfWeek vazio)
         * ou recorrencia semanal sem depender de Context Android.
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
    }
}
