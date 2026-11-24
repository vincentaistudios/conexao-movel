// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.power

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import app.nectarlink.android.R
import app.nectarlink.android.core.Device
import app.nectarlink.android.power.PowerActionType
import app.nectarlink.android.power.PowerSchedulerManager
import app.nectarlink.android.power.SleepTimerInfo
import app.nectarlink.android.ui.theme.LocalGlassTheme
import app.nectarlink.android.ui.theme.bentoWell
import app.nectarlink.android.ui.theme.glassModalContainerColor
import kotlinx.coroutines.delay
import java.util.Locale

/**
 * Secao do temporizador regressivo (Sleep Timer) com chips rapidos, barra de progresso e dialogo customizado.
 */
@Composable
internal fun SleepTimerSection(
    device: Device,
    schedulerManager: PowerSchedulerManager,
    modifier: Modifier = Modifier,
) {
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onSurface

    var sleepTimer by remember(device.id) { mutableStateOf(schedulerManager.getSleepTimer(device.id)) }
    var selectedTimerMinutes by remember { mutableIntStateOf(30) }
    var selectedTimerAction by remember { mutableStateOf(PowerActionType.Sleep) }
    var showCustomTimerDialog by remember { mutableStateOf(false) }

    var timerInitialTotalSeconds by remember(device.id) {
        mutableLongStateOf(
            sleepTimer?.let { maxOf(1L, (it.triggerAtMillis - System.currentTimeMillis()) / 1000L) } ?: (30 * 60L),
        )
    }
    var remainingSeconds by remember(sleepTimer) {
        mutableLongStateOf(
            sleepTimer?.let { maxOf(0L, (it.triggerAtMillis - System.currentTimeMillis()) / 1000L) } ?: 0L,
        )
    }

    // Ticker regressivo a cada segundo enquanto houver temporizador ativo
    LaunchedEffect(sleepTimer) {
        val active = sleepTimer ?: return@LaunchedEffect
        while (true) {
            val rem = maxOf(0L, (active.triggerAtMillis - System.currentTimeMillis()) / 1000L)
            remainingSeconds = rem
            if (rem <= 0L) {
                sleepTimer = schedulerManager.getSleepTimer(device.id)
                break
            }
            delay(1000L)
        }
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .bentoWell(
                cornerRadius = 22.dp,
                fillColor = ink.copy(alpha = if (isGlass) 0.09f else 0.05f),
                borderColor = ink.copy(alpha = if (isGlass) 0.14f else 0.09f),
            )
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Icon(
                painter = painterResource(R.drawable.ic_timer),
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(20.dp),
            )
            Column {
                Text(
                    text = stringResource(R.string.power_section_timer),
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                )
                Text(
                    text = stringResource(R.string.power_timer_subtitle),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        val activeTimer = sleepTimer
        if (activeTimer != null) {
            ActiveSleepTimerCard(
                timer = activeTimer,
                remainingSeconds = remainingSeconds,
                totalSeconds = timerInitialTotalSeconds,
                onCancel = {
                    schedulerManager.cancelSleepTimer(device.id)
                    sleepTimer = null
                },
            )
        } else {
            SleepTimerSetupControls(
                selectedAction = selectedTimerAction,
                selectedMinutes = selectedTimerMinutes,
                enabled = device.online,
                onSelectAction = { selectedTimerAction = it },
                onSelectMinutes = { selectedTimerMinutes = it },
                onOpenCustomDialog = { showCustomTimerDialog = true },
                onStart = {
                    timerInitialTotalSeconds = selectedTimerMinutes * 60L
                    schedulerManager.startSleepTimer(device.id, device.name, selectedTimerAction, selectedTimerMinutes)
                    sleepTimer = schedulerManager.getSleepTimer(device.id)
                },
            )
        }
    }

    if (showCustomTimerDialog) {
        CustomTimerDialog(
            initialMinutes = selectedTimerMinutes,
            onConfirm = { mins ->
                selectedTimerMinutes = mins
                showCustomTimerDialog = false
            },
            onDismiss = { showCustomTimerDialog = false },
        )
    }
}

@Composable
private fun ActiveSleepTimerCard(
    timer: SleepTimerInfo,
    remainingSeconds: Long,
    totalSeconds: Long,
    onCancel: () -> Unit,
) {
    val progressFraction = (remainingSeconds.toFloat() / maxOf(1L, totalSeconds).toFloat()).coerceIn(0f, 1f)
    val animatedProgress by animateFloatAsState(targetValue = progressFraction, label = "timer_progress")
    val actionLabel = powerActionLabel(timer.action)

    val hrs = remainingSeconds / 3600
    val mins = (remainingSeconds % 3600) / 60
    val secs = remainingSeconds % 60
    val timerText = if (hrs > 0) {
        String.format(Locale.getDefault(), "%02d:%02d:%02d", hrs, mins, secs)
    } else {
        String.format(Locale.getDefault(), "%02d:%02d", mins, secs)
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .bentoWell(
                cornerRadius = 18.dp,
                fillColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
                borderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.25f),
            )
            .padding(14.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = stringResource(R.string.power_timer_active_title),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
            )
            Surface(shape = RoundedCornerShape(10.dp), color = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)) {
                Text(
                    text = actionLabel,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                )
            }
        }

        Text(
            text = timerText,
            style = MaterialTheme.typography.displaySmall.copy(
                fontFamily = FontFamily.Monospace,
                fontFeatureSettings = "tnum",
                fontWeight = FontWeight.Bold,
            ),
            color = MaterialTheme.colorScheme.primary,
        )

        LinearProgressIndicator(
            progress = { animatedProgress },
            modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
            strokeCap = StrokeCap.Round,
            color = MaterialTheme.colorScheme.primary,
            trackColor = MaterialTheme.colorScheme.surfaceContainerHighest,
        )

        OutlinedButton(
            onClick = onCancel,
            shape = RoundedCornerShape(14.dp),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.5f)),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
            modifier = Modifier.fillMaxWidth().heightIn(min = 40.dp),
        ) {
            Text(stringResource(R.string.power_timer_cancel), style = MaterialTheme.typography.labelMedium)
        }
    }
}

@Composable
private fun SleepTimerSetupControls(
    selectedAction: PowerActionType,
    selectedMinutes: Int,
    enabled: Boolean,
    onSelectAction: (PowerActionType) -> Unit,
    onSelectMinutes: (Int) -> Unit,
    onOpenCustomDialog: () -> Unit,
    onStart: () -> Unit,
) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        FilterChip(
            selected = selectedAction == PowerActionType.Sleep,
            onClick = { onSelectAction(PowerActionType.Sleep) },
            label = { Text(stringResource(R.string.power_timer_action_sleep)) },
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.weight(1f),
        )
        FilterChip(
            selected = selectedAction == PowerActionType.Shutdown,
            onClick = { onSelectAction(PowerActionType.Shutdown) },
            label = { Text(stringResource(R.string.power_timer_action_shutdown)) },
            shape = RoundedCornerShape(12.dp),
            modifier = Modifier.weight(1f),
        )
    }

    val pills = listOf(
        15 to stringResource(R.string.power_timer_pill_15m),
        30 to stringResource(R.string.power_timer_pill_30m),
        45 to stringResource(R.string.power_timer_pill_45m),
        60 to stringResource(R.string.power_timer_pill_1h),
        120 to stringResource(R.string.power_timer_pill_2h),
    )
    val isCustom = pills.none { it.first == selectedMinutes }
    val chipColors = FilterChipDefaults.filterChipColors(
        selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
        selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
    )

    Row(
        modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        pills.forEach { (mins, label) ->
            FilterChip(
                selected = selectedMinutes == mins,
                onClick = { onSelectMinutes(mins) },
                label = {
                    Text(label, style = MaterialTheme.typography.labelMedium.copy(fontFeatureSettings = "tnum"))
                },
                shape = RoundedCornerShape(16.dp),
                colors = chipColors,
            )
        }
        FilterChip(
            selected = isCustom,
            onClick = onOpenCustomDialog,
            label = {
                Text(
                    text = if (isCustom) "${selectedMinutes}m" else stringResource(R.string.power_timer_pill_custom),
                    style = MaterialTheme.typography.labelMedium.copy(fontFeatureSettings = "tnum"),
                )
            },
            shape = RoundedCornerShape(16.dp),
            colors = chipColors,
        )
    }

    Button(
        onClick = onStart,
        enabled = enabled,
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp),
    ) {
        Icon(painter = painterResource(R.drawable.ic_timer), contentDescription = null, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(8.dp))
        Text(text = stringResource(R.string.power_timer_start), style = MaterialTheme.typography.labelLarge)
    }
}

/**
 * Dialogo para definicao manual da duracao do temporizador (1 a 1440 minutos).
 */
@Composable
internal fun CustomTimerDialog(
    initialMinutes: Int,
    onConfirm: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    var customInput by remember(initialMinutes) { mutableStateOf(initialMinutes.coerceIn(1, 1440).toString()) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = glassModalContainerColor(),
        title = { Text(stringResource(R.string.power_timer_custom_dialog_title)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(stringResource(R.string.power_timer_custom_dialog_minutes), style = MaterialTheme.typography.bodyMedium)
                OutlinedTextField(
                    value = customInput,
                    onValueChange = { customInput = it.filter { c -> c.isDigit() }.take(4) },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { onConfirm(customInput.toIntOrNull()?.coerceIn(1, 1440) ?: 60) }) {
                Text(stringResource(R.string.power_timer_custom_dialog_set), fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.power_dialog_cancel)) }
        },
    )
}
