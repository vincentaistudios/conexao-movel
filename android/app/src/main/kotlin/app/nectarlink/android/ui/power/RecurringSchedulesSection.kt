// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.power

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.nectarlink.android.R
import app.nectarlink.android.core.Device
import app.nectarlink.android.power.PowerActionType
import app.nectarlink.android.power.PowerSchedule
import app.nectarlink.android.power.PowerSchedulerManager
import app.nectarlink.android.ui.theme.LocalGlassTheme
import app.nectarlink.android.ui.theme.bentoWell
import app.nectarlink.android.ui.theme.glassModalContainerColor
import java.util.Calendar
import java.util.Locale
import java.util.UUID

/**
 * Secao de agendamentos de energia (recorrentes e disparo unico).
 */
@Composable
internal fun RecurringSchedulesSection(
    device: Device,
    schedulerManager: PowerSchedulerManager,
    modifier: Modifier = Modifier,
) {
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onSurface
    var schedules by remember(device.id) { mutableStateOf(schedulerManager.getSchedules(device.id)) }
    var showCreateDialog by remember { mutableStateOf(false) }
    var deleteScheduleId by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .bentoWell(22.dp, ink.copy(alpha = if (isGlass) 0.09f else 0.05f), ink.copy(alpha = if (isGlass) 0.14f else 0.09f))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.weight(1f)) {
                Icon(painterResource(R.drawable.ic_schedule), null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
                Text(
                    text = stringResource(R.string.power_section_schedules),
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            FilledTonalButton(
                onClick = { showCreateDialog = true },
                shape = RoundedCornerShape(14.dp),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                modifier = Modifier.heightIn(min = 34.dp),
            ) {
                Text("+ ${stringResource(R.string.power_schedule_add)}", style = MaterialTheme.typography.labelMedium)
            }
        }

        if (schedules.isEmpty()) {
            Text(
                text = stringResource(R.string.power_schedule_empty),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(vertical = 12.dp, horizontal = 4.dp),
            )
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                schedules.forEach { schedule ->
                    ScheduleCardItem(
                        schedule = schedule,
                        onToggleEnabled = { isEnabled ->
                            schedulerManager.toggleSchedule(schedule.id, isEnabled)
                            schedules = schedulerManager.getSchedules(device.id)
                        },
                        onDelete = { deleteScheduleId = schedule.id },
                    )
                }
            }
        }
    }

    if (showCreateDialog) {
        CreateScheduleDialog(
            device = device,
            onSave = { newSchedule ->
                schedulerManager.addSchedule(newSchedule)
                schedules = schedulerManager.getSchedules(device.id)
                showCreateDialog = false
            },
            onDismiss = { showCreateDialog = false },
        )
    }

    deleteScheduleId?.let { targetId ->
        DeleteScheduleConfirmDialog(
            onConfirm = {
                schedulerManager.removeSchedule(targetId)
                schedules = schedulerManager.getSchedules(device.id)
                deleteScheduleId = null
            },
            onDismiss = { deleteScheduleId = null },
        )
    }
}

/** Item individual de agendamento na lista com Switch e botao de excluir. */
@Composable
internal fun ScheduleCardItem(
    schedule: PowerSchedule,
    onToggleEnabled: (Boolean) -> Unit,
    onDelete: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onSurface
    val formattedTime = String.format(Locale.getDefault(), "%02d:%02d", schedule.hour, schedule.minute)
    val daysSummary = formatDaysSummary(context, schedule.daysOfWeek)

    Surface(
        shape = RoundedCornerShape(16.dp),
        color = ink.copy(alpha = if (isGlass) 0.08f else 0.04f),
        border = BorderStroke(1.dp, ink.copy(alpha = if (isGlass) 0.12f else 0.08f)),
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Box(
                modifier = Modifier.size(36.dp).clip(CircleShape).bentoWell(
                    cornerRadius = 18.dp,
                    fillColor = MaterialTheme.colorScheme.primary.copy(alpha = if (schedule.enabled) 0.14f else 0.05f),
                    borderColor = MaterialTheme.colorScheme.primary.copy(alpha = if (schedule.enabled) 0.28f else 0.10f),
                ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    painter = painterResource(powerActionIcon(schedule.action)),
                    contentDescription = null,
                    tint = if (schedule.enabled) MaterialTheme.colorScheme.primary else ink.copy(alpha = 0.38f),
                    modifier = Modifier.size(16.dp),
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = formattedTime,
                        style = MaterialTheme.typography.titleLarge.copy(
                            fontFamily = FontFamily.Monospace,
                            fontFeatureSettings = "tnum",
                            fontWeight = FontWeight.Bold,
                        ),
                        color = if (schedule.enabled) ink else ink.copy(alpha = 0.45f),
                    )
                    Text(
                        text = powerActionLabel(schedule.action, forSchedule = true),
                        style = MaterialTheme.typography.labelSmall,
                        color = if (schedule.enabled) MaterialTheme.colorScheme.primary else ink.copy(alpha = 0.45f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                Text(
                    text = daysSummary,
                    style = MaterialTheme.typography.bodySmall,
                    color = ink.copy(alpha = if (schedule.enabled) 0.65f else 0.35f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Switch(checked = schedule.enabled, onCheckedChange = onToggleEnabled)
            IconButton(onClick = onDelete, modifier = Modifier.size(32.dp)) {
                Icon(
                    imageVector = TrashIcon,
                    contentDescription = stringResource(R.string.power_schedule_delete),
                    tint = MaterialTheme.colorScheme.error.copy(alpha = 0.75f),
                    modifier = Modifier.size(18.dp),
                )
            }
        }
    }
}

/** Dialogo de criacao de novo agendamento com suporte explicito ao modo "Uma vez" (set vazio). */
@Composable
private fun CreateScheduleDialog(device: Device, onSave: (PowerSchedule) -> Unit, onDismiss: () -> Unit) {
    var newHour by remember { mutableIntStateOf(8) }
    var newMinute by remember { mutableIntStateOf(0) }
    var newAction by remember { mutableStateOf(PowerActionType.Wake) }
    var newDays by remember { mutableStateOf(setOf(Calendar.MONDAY, Calendar.TUESDAY, Calendar.WEDNESDAY, Calendar.THURSDAY, Calendar.FRIDAY)) }
    val actions = listOf(
        PowerActionType.Wake to stringResource(R.string.power_action_wake),
        PowerActionType.Sleep to stringResource(R.string.power_action_sleep),
        PowerActionType.Shutdown to stringResource(R.string.power_action_shutdown),
    )

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = glassModalContainerColor(),
        title = { Text(stringResource(R.string.power_schedule_dialog_title), style = MaterialTheme.typography.titleLarge) },
        text = {
            Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                ScheduleFieldGroup(R.string.power_schedule_action_label) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        actions.forEach { (actionType, label) ->
                            FilterChip(
                                selected = newAction == actionType,
                                onClick = { newAction = actionType },
                                label = { Text(label, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }
                ScheduleFieldGroup(R.string.power_schedule_time_label) {
                    ScheduleTimeSelector(newHour, newMinute, { newHour = it }, { newMinute = it })
                }
                ScheduleFieldGroup(R.string.power_schedule_days_label) {
                    ScheduleDaysSelector(selectedDays = newDays, onDaysChange = { newDays = it })
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    // Preserva daysOfWeek vazio para agendamentos de disparo unico ("Uma vez")
                    onSave(PowerSchedule(UUID.randomUUID().toString(), device.id, device.name, newAction, newHour, newMinute, newDays, enabled = true))
                },
                shape = RoundedCornerShape(14.dp),
            ) {
                Text(stringResource(R.string.power_schedule_save), fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.power_dialog_cancel)) } },
    )
}

@Composable
private fun ScheduleFieldGroup(labelRes: Int, content: @Composable () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            text = stringResource(labelRes),
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        content()
    }
}

/** Seletor de Hora e Minuto com botoes +/- e exibicao tabular. */
@Composable
internal fun ScheduleTimeSelector(
    hour: Int,
    minute: Int,
    onHourChange: (Int) -> Unit,
    onMinuteChange: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val ink = MaterialTheme.colorScheme.onSurface
    val isGlass = LocalGlassTheme.current
    Row(
        modifier = modifier
            .fillMaxWidth()
            .bentoWell(16.dp, ink.copy(alpha = if (isGlass) 0.08f else 0.04f), ink.copy(alpha = 0.12f))
            .padding(12.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TimeSpinnerColumn(hour, stringResource(R.string.power_schedule_hour_label), { onHourChange((hour + 1) % 24) }, { onHourChange(if (hour == 0) 23 else hour - 1) })
        Text(
            text = ":",
            style = MaterialTheme.typography.headlineLarge.copy(fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold),
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp),
        )
        TimeSpinnerColumn(minute, stringResource(R.string.power_schedule_minute_label), { onMinuteChange((minute + 5) % 60) }, { onMinuteChange(if (minute < 5) 55 else minute - 5) })
    }
}

/** Seletor de dias da semana com atalho explicito para disparo unico ("Uma vez"). */
@Composable
internal fun ScheduleDaysSelector(selectedDays: Set<Int>, onDaysChange: (Set<Int>) -> Unit, modifier: Modifier = Modifier) {
    val days = listOf(
        Calendar.SUNDAY to stringResource(R.string.day_sun_letter),
        Calendar.MONDAY to stringResource(R.string.day_mon_letter),
        Calendar.TUESDAY to stringResource(R.string.day_tue_letter),
        Calendar.WEDNESDAY to stringResource(R.string.day_wed_letter),
        Calendar.THURSDAY to stringResource(R.string.day_thu_letter),
        Calendar.FRIDAY to stringResource(R.string.day_fri_letter),
        Calendar.SATURDAY to stringResource(R.string.day_sat_letter),
    )
    val weekdays = setOf(Calendar.MONDAY, Calendar.TUESDAY, Calendar.WEDNESDAY, Calendar.THURSDAY, Calendar.FRIDAY)
    val everyday = days.map { it.first }.toSet()
    val weekends = setOf(Calendar.SUNDAY, Calendar.SATURDAY)

    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            days.forEach { (dayId, letter) ->
                val isSelected = selectedDays.contains(dayId)
                Surface(
                    shape = CircleShape,
                    color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
                    border = BorderStroke(1.dp, if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant),
                    modifier = Modifier.size(36.dp).clip(CircleShape).clickable {
                        onDaysChange(if (isSelected) selectedDays - dayId else selectedDays + dayId)
                    },
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            text = letter,
                            style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold),
                            color = if (isSelected) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurface,
                        )
                    }
                }
            }
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            DaysPresetChip(stringResource(R.string.power_schedule_days_once), selectedDays.isEmpty(), { onDaysChange(emptySet()) }, Modifier.weight(1f))
            DaysPresetChip(stringResource(R.string.power_schedule_days_weekdays), selectedDays == weekdays, { onDaysChange(weekdays) }, Modifier.weight(1f))
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            DaysPresetChip(stringResource(R.string.power_schedule_days_everyday), selectedDays == everyday, { onDaysChange(everyday) }, Modifier.weight(1f))
            DaysPresetChip(stringResource(R.string.power_schedule_days_weekends), selectedDays == weekends, { onDaysChange(weekends) }, Modifier.weight(1f))
        }
    }
}
