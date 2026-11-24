// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.power

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Calendar

class PowerScheduleTest {

    private fun calendarAt(
        year: Int,
        month: Int,
        day: Int,
        hour: Int,
        minute: Int,
        second: Int = 0,
    ): Calendar = Calendar.getInstance().apply {
        set(Calendar.YEAR, year)
        set(Calendar.MONTH, month)
        set(Calendar.DAY_OF_MONTH, day)
        set(Calendar.HOUR_OF_DAY, hour)
        set(Calendar.MINUTE, minute)
        set(Calendar.SECOND, second)
        set(Calendar.MILLISECOND, 0)
    }

    @Test
    fun powerActionTypeFromString() {
        assertEquals(PowerActionType.Wake, PowerActionType.fromString("wake"))
        assertEquals(PowerActionType.Wake, PowerActionType.fromString("Wake"))
        assertEquals(PowerActionType.Sleep, PowerActionType.fromString("sleep"))
        assertEquals(PowerActionType.Shutdown, PowerActionType.fromString("shutdown"))
        assertEquals(PowerActionType.Reboot, PowerActionType.fromString("reboot"))
        assertEquals(PowerActionType.Lock, PowerActionType.fromString("lock"))
        // Compatibilidade de fallback para chamadores legados
        assertEquals(PowerActionType.Lock, PowerActionType.fromString("invalid_action"))
    }

    @Test
    fun powerActionTypeFromStringOrNullIsFailClosed() {
        assertEquals(PowerActionType.Wake, PowerActionType.fromStringOrNull("wake"))
        assertEquals(PowerActionType.Sleep, PowerActionType.fromStringOrNull("  SLEEP "))
        assertEquals(PowerActionType.Shutdown, PowerActionType.fromStringOrNull("Shutdown"))
        assertEquals(PowerActionType.Reboot, PowerActionType.fromStringOrNull("reboot"))
        assertEquals(PowerActionType.Lock, PowerActionType.fromStringOrNull("lock"))

        assertNull(PowerActionType.fromStringOrNull(null))
        assertNull(PowerActionType.fromStringOrNull(""))
        assertNull(PowerActionType.fromStringOrNull("   "))
        assertNull(PowerActionType.fromStringOrNull("invalid_action"))
        assertNull(PowerActionType.fromStringOrNull("hibernate"))
    }

    @Test
    fun powerScheduleSerializationRoundTrip() {
        val original = PowerSchedule(
            id = "sched_123",
            pcId = "pc_456",
            pcName = "Desktop-Principal",
            action = PowerActionType.Shutdown,
            hour = 23,
            minute = 30,
            daysOfWeek = setOf(Calendar.MONDAY, Calendar.WEDNESDAY, Calendar.FRIDAY),
            enabled = true,
            lastTriggered = 1700000000000L,
        )

        val json = original.toJson()
        val restored = PowerSchedule.fromJson(json)

        assertEquals(original.id, restored.id)
        assertEquals(original.pcId, restored.pcId)
        assertEquals(original.pcName, restored.pcName)
        assertEquals(original.action, restored.action)
        assertEquals(original.hour, restored.hour)
        assertEquals(original.minute, restored.minute)
        assertEquals(original.daysOfWeek, restored.daysOfWeek)
        assertEquals(original.enabled, restored.enabled)
        assertEquals(original.lastTriggered, restored.lastTriggered)
    }

    @Test
    fun powerScheduleFromJsonRejectsInvalidAction() {
        val invalid = JSONObject().apply {
            put("id", "bad_1")
            put("pcId", "pc_1")
            put("pcName", "PC")
            put("action", "hibernate")
            put("hour", 10)
            put("minute", 0)
            put("enabled", true)
        }
        assertThrows(IllegalArgumentException::class.java) {
            PowerSchedule.fromJson(invalid)
        }
    }

    @Test
    fun powerScheduleOneShotSerialization() {
        val original = PowerSchedule(
            id = "oneshot_1",
            pcId = "pc_999",
            pcName = "Office-PC",
            action = PowerActionType.Wake,
            hour = 8,
            minute = 0,
            daysOfWeek = emptySet(),
            enabled = false,
        )

        val json = original.toJson()
        val restored = PowerSchedule.fromJson(json)

        assertEquals(original.id, restored.id)
        assertTrue(restored.daysOfWeek.isEmpty())
        assertFalse(restored.enabled)
        assertEquals(0L, restored.lastTriggered)
    }

    @Test
    fun sleepTimerInfoSerializationAndFailClosedValidation() {
        val info = SleepTimerInfo(
            pcId = "pc_abc",
            pcName = "LivingRoom-PC",
            action = PowerActionType.Sleep,
            triggerAtMillis = 1750000000000L,
        )

        val json = info.toJson()
        val restored = SleepTimerInfo.fromJson(json)

        assertEquals(info.pcId, restored.pcId)
        assertEquals(info.pcName, restored.pcName)
        assertEquals(info.action, restored.action)
        assertEquals(info.triggerAtMillis, restored.triggerAtMillis)

        val invalid = JSONObject().apply {
            put("pcId", "pc_abc")
            put("pcName", "LivingRoom-PC")
            put("action", "unknown_cmd")
            put("triggerAtMillis", 1750000000000L)
        }
        assertThrows(IllegalArgumentException::class.java) {
            SleepTimerInfo.fromJson(invalid)
        }
    }

    @Test
    fun sleepTimerSnoozeBuildsUpdatedFutureTimestampAndPreservesMetadata() {
        val nowMillis = 1760000000000L
        val snoozeDelayMs = 10 * 60_000L
        val snoozed = PowerSchedulerManager.buildSnoozedSleepTimer(
            pcId = "pc_snooze",
            pcName = "Workstation",
            action = PowerActionType.Shutdown,
            delayMillis = snoozeDelayMs,
            nowMillis = nowMillis,
        )

        assertEquals("pc_snooze", snoozed.pcId)
        assertEquals("Workstation", snoozed.pcName)
        assertEquals(PowerActionType.Shutdown, snoozed.action)
        assertEquals(nowMillis + snoozeDelayMs, snoozed.triggerAtMillis)

        val roundTripped = SleepTimerInfo.fromJson(snoozed.toJson())
        assertEquals(snoozed, roundTripped)
    }

    @Test
    fun sleepTimerFutureFilterPreservesPendingWarningWindowWithoutClearing() {
        val triggerAt = 1760000000000L
        val info = SleepTimerInfo(
            pcId = "pc_window",
            pcName = "Desktop",
            action = PowerActionType.Sleep,
            triggerAtMillis = triggerAt,
        )

        // Antes do vencimento: visivel na UI
        assertEquals(info, PowerSchedulerManager.filterFutureSleepTimer(info, nowMillis = triggerAt - 1_000L))
        // Durante a janela de aviso de 60s (triggerAt <= now): UI oculta contagem, entrada segue integra para execucao
        assertNull(PowerSchedulerManager.filterFutureSleepTimer(info, nowMillis = triggerAt))
        assertNull(PowerSchedulerManager.filterFutureSleepTimer(info, nowMillis = triggerAt + 30_000L))
        assertNull(PowerSchedulerManager.filterFutureSleepTimer(null, nowMillis = triggerAt))
    }

    @Test
    fun calculateNextTriggerMillisOneShotTodayWhenFuture() {
        val now = calendarAt(2026, Calendar.NOVEMBER, 12, 10, 0)
        val schedule = PowerSchedule(
            id = "once_today",
            pcId = "pc_1",
            pcName = "PC",
            action = PowerActionType.Wake,
            hour = 14,
            minute = 30,
            daysOfWeek = emptySet(),
            enabled = true,
        )

        val nextMillis = PowerSchedulerManager.calculateNextTriggerMillis(schedule, now.timeInMillis)
        val expected = calendarAt(2026, Calendar.NOVEMBER, 12, 14, 30)
        assertEquals(expected.timeInMillis, nextMillis)
    }

    @Test
    fun calculateNextTriggerMillisOneShotTomorrowWhenPassedOrExact() {
        val schedule = PowerSchedule(
            id = "once_tomorrow",
            pcId = "pc_1",
            pcName = "PC",
            action = PowerActionType.Shutdown,
            hour = 14,
            minute = 30,
            daysOfWeek = emptySet(),
            enabled = true,
        )

        val afterNow = calendarAt(2026, Calendar.NOVEMBER, 12, 16, 0)
        val expectedTomorrow = calendarAt(2026, Calendar.NOVEMBER, 13, 14, 30)
        assertEquals(expectedTomorrow.timeInMillis, PowerSchedulerManager.calculateNextTriggerMillis(schedule, afterNow.timeInMillis))

        val exactNow = calendarAt(2026, Calendar.NOVEMBER, 12, 14, 30, 0)
        assertEquals(expectedTomorrow.timeInMillis, PowerSchedulerManager.calculateNextTriggerMillis(schedule, exactNow.timeInMillis))
    }

    @Test
    fun calculateNextTriggerMillisWeeklySingleDaySameDayAndNextWeek() {
        val schedule = PowerSchedule(
            id = "weekly_fri",
            pcId = "pc_1",
            pcName = "PC",
            action = PowerActionType.Wake,
            hour = 9,
            minute = 0,
            daysOfWeek = setOf(Calendar.FRIDAY),
            enabled = true,
        )

        val fridayMorning = calendarAt(2026, Calendar.NOVEMBER, 13, 8, 15)
        val sameFriday = calendarAt(2026, Calendar.NOVEMBER, 13, 9, 0)
        assertEquals(sameFriday.timeInMillis, PowerSchedulerManager.calculateNextTriggerMillis(schedule, fridayMorning.timeInMillis))

        val fridayLater = calendarAt(2026, Calendar.NOVEMBER, 13, 10, 0)
        val nextFriday = calendarAt(2026, Calendar.NOVEMBER, 20, 9, 0)
        assertEquals(nextFriday.timeInMillis, PowerSchedulerManager.calculateNextTriggerMillis(schedule, fridayLater.timeInMillis))
    }

    @Test
    fun calculateNextTriggerMillisWeekdaysSkipsWeekend() {
        val weekdays = setOf(
            Calendar.MONDAY,
            Calendar.TUESDAY,
            Calendar.WEDNESDAY,
            Calendar.THURSDAY,
            Calendar.FRIDAY,
        )
        val schedule = PowerSchedule(
            id = "weekdays_wake",
            pcId = "pc_1",
            pcName = "PC",
            action = PowerActionType.Wake,
            hour = 8,
            minute = 0,
            daysOfWeek = weekdays,
            enabled = true,
        )

        val fridayNight = calendarAt(2026, Calendar.NOVEMBER, 13, 20, 0)
        val mondayMorning = calendarAt(2026, Calendar.NOVEMBER, 16, 8, 0)
        assertEquals(mondayMorning.timeInMillis, PowerSchedulerManager.calculateNextTriggerMillis(schedule, fridayNight.timeInMillis))
    }

    @Test
    fun calculateNextTriggerMillisMultipleDaysPicksNearestNextDay() {
        val schedule = PowerSchedule(
            id = "tue_thu",
            pcId = "pc_1",
            pcName = "PC",
            action = PowerActionType.Sleep,
            hour = 18,
            minute = 45,
            daysOfWeek = setOf(Calendar.TUESDAY, Calendar.THURSDAY),
            enabled = true,
        )

        val mondayNoon = calendarAt(2026, Calendar.NOVEMBER, 16, 12, 0)
        val tuesdayEvening = calendarAt(2026, Calendar.NOVEMBER, 17, 18, 45)
        assertEquals(tuesdayEvening.timeInMillis, PowerSchedulerManager.calculateNextTriggerMillis(schedule, mondayNoon.timeInMillis))
    }
}
