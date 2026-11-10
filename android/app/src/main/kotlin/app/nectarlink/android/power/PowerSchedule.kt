// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.power

import org.json.JSONArray
import org.json.JSONObject

/**
 * Types of power actions that can be triggered on a paired PC.
 */
enum class PowerActionType {
    Wake,
    Sleep,
    Shutdown,
    Reboot,
    Lock;

    companion object {
        fun fromString(value: String): PowerActionType =
            entries.firstOrNull { it.name.equals(value.trim(), ignoreCase = true) } ?: Lock
    }
}

/**
 * Represents a scheduled power management task for a paired PC.
 *
 * [daysOfWeek] contains days of week using java.util.Calendar constants (1 = Sunday ... 7 = Saturday).
 * An empty set indicates a one-shot execution at the specified [hour] and [minute].
 */
data class PowerSchedule(
    val id: String,
    val pcId: String,
    val pcName: String,
    val action: PowerActionType,
    val hour: Int,
    val minute: Int,
    val daysOfWeek: Set<Int>,
    val enabled: Boolean,
    val lastTriggered: Long = 0L,
) {
    fun toJson(): JSONObject {
        val json = JSONObject()
        json.put("id", id)
        json.put("pcId", pcId)
        json.put("pcName", pcName)
        json.put("action", action.name)
        json.put("hour", hour)
        json.put("minute", minute)
        val daysArray = JSONArray()
        daysOfWeek.forEach { daysArray.put(it) }
        json.put("daysOfWeek", daysArray)
        json.put("enabled", enabled)
        json.put("lastTriggered", lastTriggered)
        return json
    }

    companion object {
        fun fromJson(json: JSONObject): PowerSchedule {
            val daysSet = mutableSetOf<Int>()
            val daysArray = json.optJSONArray("daysOfWeek")
            if (daysArray != null) {
                for (i in 0 until daysArray.length()) {
                    daysSet.add(daysArray.getInt(i))
                }
            }
            return PowerSchedule(
                id = json.getString("id"),
                pcId = json.getString("pcId"),
                pcName = json.optString("pcName", ""),
                action = PowerActionType.fromString(json.getString("action")),
                hour = json.getInt("hour"),
                minute = json.getInt("minute"),
                daysOfWeek = daysSet,
                enabled = json.getBoolean("enabled"),
                lastTriggered = json.optLong("lastTriggered", 0L),
            )
        }
    }
}
