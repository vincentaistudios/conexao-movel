// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.power

import android.content.Context
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.nectarlink.android.R
import app.nectarlink.android.power.PowerActionType
import app.nectarlink.android.ui.theme.LocalGlassTheme
import app.nectarlink.android.ui.theme.glassModalContainerColor
import java.util.Calendar
import java.util.Locale

internal val CloseIcon: ImageVector by lazy {
    buildStrokeVector("CloseIcon", "M18,6L6,18 M6,6L18,18", 2f)
}

internal val LockIcon: ImageVector by lazy {
    buildStrokeVector(
        "LockIcon",
        "M5,11h14a2,2 0 0,1 2,2v7a2,2 0 0,1 -2,2H5a2,2 0 0,1 -2,-2v-7a2,2 0 0,1 2,-2z M8,11V7a4,4 0 0,1 8,0v4",
        1.85f,
    )
}

internal val TrashIcon: ImageVector by lazy {
    buildStrokeVector(
        "TrashIcon",
        "M3,6h18 M8,6V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2 M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6 M10,11v6 M14,11v6",
        1.85f,
    )
}

private fun buildStrokeVector(name: String, pathData: String, strokeWidth: Float): ImageVector =
    ImageVector.Builder(
        name = name,
        defaultWidth = 24.dp,
        defaultHeight = 24.dp,
        viewportWidth = 24f,
        viewportHeight = 24f,
    ).addPath(
        pathData = PathParser().parsePathString(pathData).toNodes(),
        fill = null,
        stroke = SolidColor(Color.White),
        strokeLineWidth = strokeWidth,
        strokeLineCap = StrokeCap.Round,
        strokeLineJoin = StrokeJoin.Round,
    ).build()

/**
 * Botao imediato de acao de energia com cantos arredondados de 18dp.
 */
@Composable
internal fun PowerImmediateButton(
    icon: Int,
    label: String,
    isHighlighted: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    isDestructive: Boolean = false,
) {
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onSurface

    val colors = when {
        isHighlighted -> ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
            disabledContainerColor = ink.copy(alpha = 0.04f),
            disabledContentColor = ink.copy(alpha = 0.38f),
        )
        isDestructive -> ButtonDefaults.filledTonalButtonColors(
            containerColor = MaterialTheme.colorScheme.errorContainer.copy(alpha = if (isGlass) 0.35f else 0.22f),
            contentColor = MaterialTheme.colorScheme.error,
            disabledContainerColor = ink.copy(alpha = 0.04f),
            disabledContentColor = ink.copy(alpha = 0.38f),
        )
        else -> ButtonDefaults.filledTonalButtonColors(
            containerColor = ink.copy(alpha = if (isGlass) 0.12f else 0.08f),
            contentColor = ink,
            disabledContainerColor = ink.copy(alpha = 0.04f),
            disabledContentColor = ink.copy(alpha = 0.38f),
        )
    }

    val border = when {
        !enabled -> BorderStroke(1.dp, ink.copy(alpha = 0.08f))
        isHighlighted -> BorderStroke(1.dp, MaterialTheme.colorScheme.primary)
        isDestructive -> BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.25f))
        else -> BorderStroke(1.dp, ink.copy(alpha = 0.12f))
    }

    FilledTonalButton(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(18.dp),
        colors = colors,
        border = border,
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 12.dp),
        modifier = modifier.heightIn(min = 52.dp),
    ) {
        Icon(painter = painterResource(icon), contentDescription = null, modifier = Modifier.size(17.dp))
        Spacer(Modifier.width(8.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelLarge,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

/** Dialogo de confirmacao para desligar o PC. */
@Composable
internal fun PowerShutdownConfirmDialog(deviceName: String, onConfirm: () -> Unit, onDismiss: () -> Unit) {
    PowerConfirmDialog(
        title = stringResource(R.string.power_dialog_shutdown_title, deviceName),
        message = stringResource(R.string.power_dialog_shutdown_message),
        confirmLabel = stringResource(R.string.power_dialog_shutdown_confirm),
        isDestructive = true,
        onConfirm = onConfirm,
        onDismiss = onDismiss,
    )
}

/** Dialogo de confirmacao para reiniciar o PC. */
@Composable
internal fun PowerRestartConfirmDialog(deviceName: String, onConfirm: () -> Unit, onDismiss: () -> Unit) {
    PowerConfirmDialog(
        title = stringResource(R.string.power_dialog_restart_title, deviceName),
        message = stringResource(R.string.power_dialog_restart_message),
        confirmLabel = stringResource(R.string.power_dialog_restart_confirm),
        isDestructive = false,
        onConfirm = onConfirm,
        onDismiss = onDismiss,
    )
}

/** Dialogo de confirmacao para excluir um agendamento de energia. */
@Composable
internal fun DeleteScheduleConfirmDialog(onConfirm: () -> Unit, onDismiss: () -> Unit) {
    PowerConfirmDialog(
        title = stringResource(R.string.power_schedule_delete),
        message = stringResource(R.string.power_schedule_delete_confirm_msg),
        confirmLabel = stringResource(R.string.power_schedule_delete),
        isDestructive = true,
        onConfirm = onConfirm,
        onDismiss = onDismiss,
    )
}

@Composable
private fun PowerConfirmDialog(
    title: String,
    message: String,
    confirmLabel: String,
    isDestructive: Boolean,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = glassModalContainerColor(),
        title = { Text(text = title, style = MaterialTheme.typography.titleLarge) },
        text = { Text(text = message, style = MaterialTheme.typography.bodyMedium) },
        confirmButton = {
            TextButton(
                onClick = onConfirm,
                colors = if (isDestructive) {
                    ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)
                } else {
                    ButtonDefaults.textButtonColors()
                },
            ) {
                Text(confirmLabel, fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.power_dialog_cancel)) }
        },
    )
}

internal fun powerActionIcon(action: PowerActionType): Int = when (action) {
    PowerActionType.Wake -> R.drawable.ic_wake
    PowerActionType.Reboot -> R.drawable.ic_restart
    PowerActionType.Sleep, PowerActionType.Shutdown, PowerActionType.Lock -> R.drawable.ic_power
}

@Composable
internal fun powerActionLabel(action: PowerActionType, forSchedule: Boolean = false): String = when (action) {
    PowerActionType.Wake -> stringResource(if (forSchedule) R.string.power_schedule_action_wake else R.string.power_action_wake)
    PowerActionType.Sleep -> stringResource(if (forSchedule) R.string.power_schedule_action_sleep else R.string.power_action_sleep)
    PowerActionType.Shutdown -> stringResource(if (forSchedule) R.string.power_schedule_action_shutdown else R.string.power_action_shutdown)
    PowerActionType.Reboot -> stringResource(R.string.power_action_restart)
    PowerActionType.Lock -> stringResource(R.string.power_action_lock)
}

/**
 * Formata o resumo legivel dos dias selecionados; retorna "Uma vez" para disparo unico.
 */
internal fun formatDaysSummary(context: Context, days: Set<Int>): String {
    if (days.isEmpty()) return context.getString(R.string.power_schedule_days_once)
    if (days.size == 7) return context.getString(R.string.power_schedule_days_everyday)
    val weekdays = setOf(Calendar.MONDAY, Calendar.TUESDAY, Calendar.WEDNESDAY, Calendar.THURSDAY, Calendar.FRIDAY)
    if (days == weekdays) return context.getString(R.string.power_schedule_days_weekdays)
    val weekends = setOf(Calendar.SUNDAY, Calendar.SATURDAY)
    if (days == weekends) return context.getString(R.string.power_schedule_days_weekends)

    val dayLetters = mapOf(
        Calendar.SUNDAY to context.getString(R.string.day_sun_letter),
        Calendar.MONDAY to context.getString(R.string.day_mon_letter),
        Calendar.TUESDAY to context.getString(R.string.day_tue_letter),
        Calendar.WEDNESDAY to context.getString(R.string.day_wed_letter),
        Calendar.THURSDAY to context.getString(R.string.day_thu_letter),
        Calendar.FRIDAY to context.getString(R.string.day_fri_letter),
        Calendar.SATURDAY to context.getString(R.string.day_sat_letter),
    )
    return days.sorted().mapNotNull { dayLetters[it] }.joinToString(", ")
}

@Composable
internal fun TimeSpinnerColumn(value: Int, label: String, onIncrement: () -> Unit, onDecrement: () -> Unit) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        FilledTonalIconButton(onClick = onIncrement, shape = RoundedCornerShape(10.dp), modifier = Modifier.size(36.dp)) {
            Text("+", style = MaterialTheme.typography.titleMedium)
        }
        Text(
            text = String.format(Locale.getDefault(), "%02d", value),
            style = MaterialTheme.typography.headlineMedium.copy(fontFamily = FontFamily.Monospace, fontFeatureSettings = "tnum", fontWeight = FontWeight.Bold),
            modifier = Modifier.padding(vertical = 4.dp),
        )
        FilledTonalIconButton(onClick = onDecrement, shape = RoundedCornerShape(10.dp), modifier = Modifier.size(36.dp)) {
            Text("-", style = MaterialTheme.typography.titleMedium)
        }
        Text(text = label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
internal fun DaysPresetChip(label: String, selected: Boolean, onClick: () -> Unit, modifier: Modifier = Modifier) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text(label, style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis) },
        shape = RoundedCornerShape(12.dp),
        colors = FilterChipDefaults.filterChipColors(
            selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
            selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
        ),
        modifier = modifier,
    )
}
