// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.power

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Calendar

class PowerScheduleTest {

    @Test
    fun powerActionTypeFromString() {
        assertEquals(PowerActionType.Wake, PowerActionType.fromString("wake"))
        assertEquals(PowerActionType.Wake, PowerActionType.fromString("Wake"))
        assertEquals(PowerActionType.Sleep, PowerActionType.fromString("sleep"))
        assertEquals(PowerActionType.Shutdown, PowerActionType.fromString("shutdown"))
        assertEquals(PowerActionType.Reboot, PowerActionType.fromString("reboot"))
        assertEquals(PowerActionType.Lock, PowerActionType.fromString("lock"))
        // Fallback for unknown
        assertEquals(PowerActionType.Lock, PowerActionType.fromString("invalid_action"))
    }

    @Test
    fun powerScheduleSerializationRoundTrip() {
        val original = PowerSchedule(
            id = "sched_123",
            pcId = "pc_456",
            pcName = "Vincent-Desktop",
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
    fun sleepTimerInfoSerializationRoundTrip() {
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
    }
}
