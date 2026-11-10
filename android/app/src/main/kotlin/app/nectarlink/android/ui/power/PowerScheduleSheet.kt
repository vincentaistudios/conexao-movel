// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.power

import android.content.Context
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilledTonalIconButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.nectarlink.android.R
import app.nectarlink.android.core.Device
import app.nectarlink.android.core.WakeState
import app.nectarlink.android.power.PowerActionType
import app.nectarlink.android.power.PowerSchedule
import app.nectarlink.android.power.PowerSchedulerManager
import app.nectarlink.android.power.SleepTimerInfo
import app.nectarlink.android.ui.theme.LocalGlassTheme
import app.nectarlink.android.ui.theme.bentoWell
import app.nectarlink.android.ui.theme.glassModalContainerColor
import app.nectarlink.android.ui.theme.glassModalScrimColor
import kotlinx.coroutines.delay
import java.util.Calendar
import java.util.UUID

private val CloseIcon: ImageVector by lazy {
    ImageVector.Builder(
        name = "CloseIcon",
        defaultWidth = 24.dp,
        defaultHeight = 24.dp,
        viewportWidth = 24f,
        viewportHeight = 24f,
    ).addPath(
        pathData = PathParser().parsePathString("M18,6L6,18 M6,6L18,18").toNodes(),
        fill = null,
        stroke = SolidColor(Color.White),
        strokeLineWidth = 2f,
        strokeLineCap = StrokeCap.Round,
        strokeLineJoin = StrokeJoin.Round,
    ).build()
}

private val LockIcon: ImageVector by lazy {
    ImageVector.Builder(
        name = "LockIcon",
        defaultWidth = 24.dp,
        defaultHeight = 24.dp,
        viewportWidth = 24f,
        viewportHeight = 24f,
    ).addPath(
        pathData = PathParser().parsePathString("M5,11h14a2,2 0 0,1 2,2v7a2,2 0 0,1 -2,2H5a2,2 0 0,1 -2,-2v-7a2,2 0 0,1 2,-2z M8,11V7a4,4 0 0,1 8,0v4").toNodes(),
        fill = null,
        stroke = SolidColor(Color.White),
        strokeLineWidth = 1.85f,
        strokeLineCap = StrokeCap.Round,
        strokeLineJoin = StrokeJoin.Round,
    ).build()
}

private val TrashIcon: ImageVector by lazy {
    ImageVector.Builder(
        name = "TrashIcon",
        defaultWidth = 24.dp,
        defaultHeight = 24.dp,
        viewportWidth = 24f,
        viewportHeight = 24f,
    ).addPath(
        pathData = PathParser().parsePathString("M3,6h18 M8,6V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2 M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6 M10,11v6 M14,11v6").toNodes(),
        fill = null,
        stroke = SolidColor(Color.White),
        strokeLineWidth = 1.85f,
        strokeLineCap = StrokeCap.Round,
        strokeLineJoin = StrokeJoin.Round,
    ).build()
}

/**
 * Modal bottom sheet for PC Power Control, Sleep Timer, and Recurring Schedules.
 * Strictly implements the Dark Glass / Fluent design language of NectarLink with zero emojis.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PowerScheduleSheet(
    device: Device,
    onWake: () -> Unit,
    onSleep: () -> Unit,
    onLock: () -> Unit,
    onShutdown: () -> Unit = onSleep,
    onRestart: () -> Unit = onSleep,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onSurface

    val schedulerManager = remember { PowerSchedulerManager(context) }

    // Schedules and active sleep timer backed by PowerSchedulerManager
    var schedules by remember(device.id) {
        mutableStateOf(schedulerManager.getSchedules(device.id))
    }
    var sleepTimer by remember(device.id) {
        mutableStateOf(schedulerManager.getSleepTimer(device.id))
    }

    // Confirmation & sub-dialog states
    var confirmShutdown by remember { mutableStateOf(false) }
    var confirmRestart by remember { mutableStateOf(false) }
    var deleteScheduleId by remember { mutableStateOf<String?>(null) }
    var showCreateScheduleDialog by remember { mutableStateOf(false) }
    var showCustomTimerDialog by remember { mutableStateOf(false) }

    // Quick selection timer values
    var selectedTimerMinutes by remember { mutableIntStateOf(30) }
    var selectedTimerAction by remember { mutableStateOf(PowerActionType.Sleep) }
    var timerInitialTotalSeconds by remember(device.id) {
        mutableLongStateOf(
            sleepTimer?.let {
                maxOf(1L, (it.triggerAtMillis - System.currentTimeMillis()) / 1000L)
            } ?: (30 * 60L)
        )
    }

    // Sleep Timer countdown ticker
    var remainingSeconds by remember(sleepTimer) {
        mutableLongStateOf(
            sleepTimer?.let { maxOf(0L, (it.triggerAtMillis - System.currentTimeMillis()) / 1000L) } ?: 0L
        )
    }

    LaunchedEffect(sleepTimer) {
        val active = sleepTimer ?: return@LaunchedEffect
        while (true) {
            val now = System.currentTimeMillis()
            val rem = maxOf(0L, (active.triggerAtMillis - now) / 1000L)
            remainingSeconds = rem
            if (rem <= 0L) {
                sleepTimer = schedulerManager.getSleepTimer(device.id)
                break
            }
            delay(1000L)
        }
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = glassModalContainerColor(),
        scrimColor = glassModalScrimColor(),
        shape = RoundedCornerShape(topStart = 28.dp, topEnd = 28.dp),
        modifier = modifier,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp)
                .padding(bottom = 36.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            // Header: Title, Device Subtitle, Close Button
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier = Modifier
                        .size(42.dp)
                        .clip(CircleShape)
                        .bentoWell(
                            cornerRadius = 21.dp,
                            fillColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.16f),
                            borderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.35f),
                        ),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        painter = painterResource(R.drawable.ic_power),
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(20.dp),
                    )
                }
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = stringResource(R.string.power_schedule_title),
                        style = MaterialTheme.typography.titleLarge,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                    Text(
                        text = "${device.name} · ${stringResource(R.string.power_schedule_device_subtitle)}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                IconButton(onClick = onDismiss) {
                    Icon(
                        imageVector = CloseIcon,
                        contentDescription = stringResource(R.string.desk_exit),
                        tint = ink.copy(alpha = 0.7f),
                        modifier = Modifier.size(20.dp),
                    )
                }
            }

            // ==========================================
            // SEÇÃO 1: AÇÕES IMEDIATAS DO PC
            // ==========================================
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    text = stringResource(R.string.power_section_immediate),
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                    color = ink.copy(alpha = 0.72f),
                    modifier = Modifier.padding(start = 2.dp),
                )

                // Grid 2x2 with 18dp rounded corner buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    // 1. Ligar PC (Destacado se offline e canWake)
                    val canHighlightWake = !device.online && device.canWake
                    PowerImmediateButton(
                        icon = R.drawable.ic_wake,
                        label = stringResource(R.string.power_action_wake),
                        isHighlighted = canHighlightWake,
                        enabled = (!device.online && device.canWake) || (!device.online && device.wakeState != WakeState.Waking),
                        onClick = onWake,
                        modifier = Modifier.weight(1f),
                    )

                    // 2. Suspender PC
                    PowerImmediateButton(
                        icon = R.drawable.ic_power,
                        label = stringResource(R.string.power_action_sleep),
                        isHighlighted = false,
                        enabled = device.online,
                        onClick = onSleep,
                        modifier = Modifier.weight(1f),
                    )
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    // 3. Desligar PC (com diálogo de confirmação)
                    PowerImmediateButton(
                        icon = R.drawable.ic_power,
                        label = stringResource(R.string.power_action_shutdown),
                        isHighlighted = false,
                        isDestructive = true,
                        enabled = device.online,
                        onClick = { confirmShutdown = true },
                        modifier = Modifier.weight(1f),
                    )

                    // 4. Reiniciar PC (com diálogo de confirmação)
                    PowerImmediateButton(
                        icon = R.drawable.ic_restart,
                        label = stringResource(R.string.power_action_restart),
                        isHighlighted = false,
                        enabled = device.online,
                        onClick = { confirmRestart = true },
                        modifier = Modifier.weight(1f),
                    )
                }

                // 5. Bloquear PC
                FilledTonalButton(
                    onClick = onLock,
                    enabled = device.online,
                    shape = RoundedCornerShape(18.dp),
                    colors = ButtonDefaults.filledTonalButtonColors(
                        containerColor = ink.copy(alpha = if (isGlass) 0.12f else 0.08f),
                        contentColor = ink,
                        disabledContainerColor = ink.copy(alpha = 0.04f),
                        disabledContentColor = ink.copy(alpha = 0.38f),
                    ),
                    border = BorderStroke(1.dp, ink.copy(alpha = 0.12f)),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                    modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                ) {
                    Icon(
                        imageVector = LockIcon,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = stringResource(R.string.power_action_lock),
                        style = MaterialTheme.typography.labelLarge,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }

            // ==========================================
            // SEÇÃO 2: TEMPORIZADOR REGRESSIVO ("SLEEP TIMER")
            // ==========================================
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .bentoWell(
                        cornerRadius = 22.dp,
                        fillColor = ink.copy(alpha = if (isGlass) 0.09f else 0.05f),
                        borderColor = ink.copy(alpha = if (isGlass) 0.14f else 0.09f),
                    )
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
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

                if (sleepTimer != null) {
                    // LIVE COUNTDOWN DISPLAY & PROGRESS BAR
                    val totalSec = maxOf(1L, timerInitialTotalSeconds)
                    val progressFraction = (remainingSeconds.toFloat() / totalSec.toFloat()).coerceIn(0f, 1f)
                    val animatedProgress by animateFloatAsState(
                        targetValue = progressFraction,
                        label = "timer_progress",
                    )

                    val actionLabel = when (sleepTimer?.action) {
                        PowerActionType.Wake -> stringResource(R.string.power_action_wake)
                        PowerActionType.Sleep -> stringResource(R.string.power_action_sleep)
                        PowerActionType.Shutdown -> stringResource(R.string.power_action_shutdown)
                        PowerActionType.Reboot -> stringResource(R.string.power_action_restart)
                        PowerActionType.Lock -> stringResource(R.string.power_action_lock)
                        null -> ""
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
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f),
                            ) {
                                Text(
                                    text = actionLabel,
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                                )
                            }
                        }

                        // Formatted mm:ss or hh:mm:ss
                        val hrs = remainingSeconds / 3600
                        val mins = (remainingSeconds % 3600) / 60
                        val secs = remainingSeconds % 60
                        val timerText = if (hrs > 0) {
                            String.format("%02d:%02d:%02d", hrs, mins, secs)
                        } else {
                            String.format("%02d:%02d", mins, secs)
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
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(8.dp)
                                .clip(RoundedCornerShape(4.dp)),
                            strokeCap = StrokeCap.Round,
                            color = MaterialTheme.colorScheme.primary,
                            trackColor = MaterialTheme.colorScheme.surfaceContainerHighest,
                        )

                        OutlinedButton(
                            onClick = {
                                schedulerManager.cancelSleepTimer(device.id)
                                sleepTimer = null
                            },
                            shape = RoundedCornerShape(14.dp),
                            border = BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.5f)),
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                            modifier = Modifier.fillMaxWidth().heightIn(min = 40.dp),
                        ) {
                            Text(stringResource(R.string.power_timer_cancel), style = MaterialTheme.typography.labelMedium)
                        }
                    }
                } else {
                    // Action selector: Suspender ou Desligar
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        FilterChip(
                            selected = selectedTimerAction == PowerActionType.Sleep,
                            onClick = { selectedTimerAction = PowerActionType.Sleep },
                            label = { Text(stringResource(R.string.power_timer_action_sleep)) },
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.weight(1f),
                        )
                        FilterChip(
                            selected = selectedTimerAction == PowerActionType.Shutdown,
                            onClick = { selectedTimerAction = PowerActionType.Shutdown },
                            label = { Text(stringResource(R.string.power_timer_action_shutdown)) },
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.weight(1f),
                        )
                    }

                    // Quick duration selection pills: 15m, 30m, 45m, 1h, 2h, Personalizado
                    val pills = listOf(
                        15 to stringResource(R.string.power_timer_pill_15m),
                        30 to stringResource(R.string.power_timer_pill_30m),
                        45 to stringResource(R.string.power_timer_pill_45m),
                        60 to stringResource(R.string.power_timer_pill_1h),
                        120 to stringResource(R.string.power_timer_pill_2h),
                    )

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        pills.forEach { (mins, label) ->
                            val isSelected = selectedTimerMinutes == mins
                            FilterChip(
                                selected = isSelected,
                                onClick = { selectedTimerMinutes = mins },
                                label = {
                                    Text(
                                        text = label,
                                        style = MaterialTheme.typography.labelMedium.copy(fontFeatureSettings = "tnum"),
                                    )
                                },
                                shape = RoundedCornerShape(16.dp),
                                colors = FilterChipDefaults.filterChipColors(
                                    selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                    selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                                ),
                            )
                        }

                        // Custom pill
                        val isCustom = pills.none { it.first == selectedTimerMinutes }
                        FilterChip(
                            selected = isCustom,
                            onClick = { showCustomTimerDialog = true },
                            label = {
                                Text(
                                    text = if (isCustom) "${selectedTimerMinutes}m" else stringResource(R.string.power_timer_pill_custom),
                                    style = MaterialTheme.typography.labelMedium.copy(fontFeatureSettings = "tnum"),
                                )
                            },
                            shape = RoundedCornerShape(16.dp),
                            colors = FilterChipDefaults.filterChipColors(
                                selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                            ),
                        )
                    }

                    Button(
                        onClick = {
                            val durationSec = selectedTimerMinutes * 60L
                            timerInitialTotalSeconds = durationSec
                            schedulerManager.startSleepTimer(
                                pcId = device.id,
                                pcName = device.name,
                                action = selectedTimerAction,
                                minutes = selectedTimerMinutes,
                            )
                            sleepTimer = schedulerManager.getSleepTimer(device.id)
                        },
                        enabled = device.online,
                        shape = RoundedCornerShape(16.dp),
                        modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp),
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_timer),
                            contentDescription = null,
                            modifier = Modifier.size(16.dp),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(
                            text = stringResource(R.string.power_timer_start),
                            style = MaterialTheme.typography.labelLarge,
                        )
                    }
                }
            }

            // ==========================================
            // SEÇÃO 3: AGENDAMENTOS RECORRENTES
            // ==========================================
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .bentoWell(
                        cornerRadius = 22.dp,
                        fillColor = ink.copy(alpha = if (isGlass) 0.09f else 0.05f),
                        borderColor = ink.copy(alpha = if (isGlass) 0.14f else 0.09f),
                    )
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_schedule),
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(20.dp),
                        )
                        Text(
                            text = stringResource(R.string.power_section_schedules),
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                        )
                    }

                    FilledTonalButton(
                        onClick = { showCreateScheduleDialog = true },
                        shape = RoundedCornerShape(14.dp),
                        contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                        modifier = Modifier.heightIn(min = 34.dp),
                    ) {
                        Text(
                            text = "+ ${stringResource(R.string.power_schedule_add)}",
                            style = MaterialTheme.typography.labelMedium,
                        )
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
        }
    }

    // ==========================================
    // DIÁLOGOS DE CONFIRMAÇÃO E FORMULÁRIOS
    // ==========================================

    // Confirmação Desligar PC
    if (confirmShutdown) {
        AlertDialog(
            onDismissRequest = { confirmShutdown = false },
            containerColor = glassModalContainerColor(),
            title = {
                Text(
                    text = stringResource(R.string.power_dialog_shutdown_title, device.name),
                    style = MaterialTheme.typography.titleLarge,
                )
            },
            text = {
                Text(
                    text = stringResource(R.string.power_dialog_shutdown_message),
                    style = MaterialTheme.typography.bodyMedium,
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        confirmShutdown = false
                        onShutdown()
                    },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error),
                ) {
                    Text(stringResource(R.string.power_dialog_shutdown_confirm), fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { confirmShutdown = false }) {
                    Text(stringResource(R.string.power_dialog_cancel))
                }
            },
        )
    }

    // Confirmação Reiniciar PC
    if (confirmRestart) {
        AlertDialog(
            onDismissRequest = { confirmRestart = false },
            containerColor = glassModalContainerColor(),
            title = {
                Text(
                    text = stringResource(R.string.power_dialog_restart_title, device.name),
                    style = MaterialTheme.typography.titleLarge,
                )
            },
            text = {
                Text(
                    text = stringResource(R.string.power_dialog_restart_message),
                    style = MaterialTheme.typography.bodyMedium,
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        confirmRestart = false
                        onRestart()
                    },
                ) {
                    Text(stringResource(R.string.power_dialog_restart_confirm), fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { confirmRestart = false }) {
                    Text(stringResource(R.string.power_dialog_cancel))
                }
            },
        )
    }

    // Confirmação Excluir Agendamento
    if (deleteScheduleId != null) {
        val targetId = deleteScheduleId
        AlertDialog(
            onDismissRequest = { deleteScheduleId = null },
            containerColor = glassModalContainerColor(),
            title = { Text(stringResource(R.string.power_schedule_delete)) },
            text = { Text(stringResource(R.string.power_schedule_delete_confirm_msg)) },
            confirmButton = {
                TextButton(
                    onClick = {
                        if (targetId != null) {
                            schedulerManager.removeSchedule(targetId)
                            schedules = schedulerManager.getSchedules(device.id)
                        }
                        deleteScheduleId = null
                    },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error),
                ) {
                    Text(stringResource(R.string.power_schedule_delete), fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { deleteScheduleId = null }) {
                    Text(stringResource(R.string.power_dialog_cancel))
                }
            },
        )
    }

    // Diálogo Temporizador Personalizado
    if (showCustomTimerDialog) {
        var customInput by remember { mutableStateOf("60") }
        AlertDialog(
            onDismissRequest = { showCustomTimerDialog = false },
            containerColor = glassModalContainerColor(),
            title = { Text(stringResource(R.string.power_timer_custom_dialog_title)) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = stringResource(R.string.power_timer_custom_dialog_minutes),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    OutlinedTextField(
                        value = customInput,
                        onValueChange = { customInput = it.filter { c -> c.isDigit() }.take(4) },
                        singleLine = true,
                        shape = RoundedCornerShape(14.dp),
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        val mins = customInput.toIntOrNull()?.coerceIn(1, 1440) ?: 60
                        selectedTimerMinutes = mins
                        showCustomTimerDialog = false
                    },
                ) {
                    Text(stringResource(R.string.power_timer_custom_dialog_set), fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showCustomTimerDialog = false }) {
                    Text(stringResource(R.string.power_dialog_cancel))
                }
            },
        )
    }

    // Diálogo / Formulário Novo Agendamento
    if (showCreateScheduleDialog) {
        var newHour by remember { mutableIntStateOf(8) }
        var newMinute by remember { mutableIntStateOf(0) }
        var newAction by remember { mutableStateOf(PowerActionType.Wake) }
        var newDays by remember { mutableStateOf(setOf(2, 3, 4, 5, 6)) }

        AlertDialog(
            onDismissRequest = { showCreateScheduleDialog = false },
            containerColor = glassModalContainerColor(),
            title = {
                Text(
                    text = stringResource(R.string.power_schedule_dialog_title),
                    style = MaterialTheme.typography.titleLarge,
                )
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    // 1. Seletor de Ação
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(
                            text = stringResource(R.string.power_schedule_action_label),
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                        ) {
                            FilterChip(
                                selected = newAction == PowerActionType.Wake,
                                onClick = { newAction = PowerActionType.Wake },
                                label = { Text(stringResource(R.string.power_action_wake), maxLines = 1) },
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier.weight(1f),
                            )
                            FilterChip(
                                selected = newAction == PowerActionType.Sleep,
                                onClick = { newAction = PowerActionType.Sleep },
                                label = { Text(stringResource(R.string.power_action_sleep), maxLines = 1) },
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier.weight(1f),
                            )
                            FilterChip(
                                selected = newAction == PowerActionType.Shutdown,
                                onClick = { newAction = PowerActionType.Shutdown },
                                label = { Text(stringResource(R.string.power_action_shutdown), maxLines = 1) },
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }

                    // 2. Seletor de Hora e Minuto com numérico tnum
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(
                            text = stringResource(R.string.power_schedule_time_label),
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        ScheduleTimeSelector(
                            hour = newHour,
                            minute = newMinute,
                            onHourChange = { newHour = it },
                            onMinuteChange = { newMinute = it },
                        )
                    }

                    // 3. Seletor de Dias da Semana (D, S, T, Q, Q, S, S) com atalhos
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(
                            text = stringResource(R.string.power_schedule_days_label),
                            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        ScheduleDaysSelector(
                            selectedDays = newDays,
                            onDaysChange = { newDays = it },
                        )
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val newSchedule = PowerSchedule(
                            id = UUID.randomUUID().toString(),
                            pcId = device.id,
                            pcName = device.name,
                            action = newAction,
                            hour = newHour,
                            minute = newMinute,
                            daysOfWeek = if (newDays.isEmpty()) setOf(2, 3, 4, 5, 6) else newDays,
                            enabled = true,
                        )
                        schedulerManager.addSchedule(newSchedule)
                        schedules = schedulerManager.getSchedules(device.id)
                        showCreateScheduleDialog = false
                    },
                    shape = RoundedCornerShape(14.dp),
                ) {
                    Text(stringResource(R.string.power_schedule_save), fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showCreateScheduleDialog = false }) {
                    Text(stringResource(R.string.power_dialog_cancel))
                }
            },
        )
    }
}

/**
 * Item individual de agendamento na lista com Switch e botão de excluir.
 */
@Composable
private fun ScheduleCardItem(
    schedule: PowerSchedule,
    onToggleEnabled: (Boolean) -> Unit,
    onDelete: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onSurface

    val actionIcon = when (schedule.action) {
        PowerActionType.Wake -> R.drawable.ic_wake
        PowerActionType.Sleep -> R.drawable.ic_power
        PowerActionType.Shutdown -> R.drawable.ic_power
        PowerActionType.Reboot -> R.drawable.ic_restart
        PowerActionType.Lock -> R.drawable.ic_power
    }

    val actionLabel = when (schedule.action) {
        PowerActionType.Wake -> stringResource(R.string.power_schedule_action_wake)
        PowerActionType.Sleep -> stringResource(R.string.power_schedule_action_sleep)
        PowerActionType.Shutdown -> stringResource(R.string.power_schedule_action_shutdown)
        PowerActionType.Reboot -> stringResource(R.string.power_action_restart)
        PowerActionType.Lock -> stringResource(R.string.power_action_lock)
    }

    val formattedTime = String.format("%02d:%02d", schedule.hour, schedule.minute)
    val daysSummary = formatDaysSummary(context, schedule.daysOfWeek)

    Surface(
        shape = RoundedCornerShape(16.dp),
        color = ink.copy(alpha = if (isGlass) 0.08f else 0.04f),
        border = BorderStroke(1.dp, ink.copy(alpha = if (isGlass) 0.12f else 0.08f)),
        modifier = modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Box(
                modifier = Modifier
                    .size(36.dp)
                    .clip(CircleShape)
                    .bentoWell(
                        cornerRadius = 18.dp,
                        fillColor = MaterialTheme.colorScheme.primary.copy(alpha = if (schedule.enabled) 0.14f else 0.05f),
                        borderColor = MaterialTheme.colorScheme.primary.copy(alpha = if (schedule.enabled) 0.28f else 0.10f),
                    ),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    painter = painterResource(actionIcon),
                    contentDescription = null,
                    tint = if (schedule.enabled) MaterialTheme.colorScheme.primary else ink.copy(alpha = 0.38f),
                    modifier = Modifier.size(16.dp),
                )
            }

            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
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
                        text = actionLabel,
                        style = MaterialTheme.typography.labelSmall,
                        color = if (schedule.enabled) MaterialTheme.colorScheme.primary else ink.copy(alpha = 0.45f),
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

            Switch(
                checked = schedule.enabled,
                onCheckedChange = onToggleEnabled,
            )

            IconButton(
                onClick = onDelete,
                modifier = Modifier.size(32.dp),
            ) {
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

/**
 * Seletor de Hora e Minuto com botões +/- e exibição tabular.
 */
@Composable
private fun ScheduleTimeSelector(
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
            .bentoWell(
                cornerRadius = 16.dp,
                fillColor = ink.copy(alpha = if (isGlass) 0.08f else 0.04f),
                borderColor = ink.copy(alpha = 0.12f),
            )
            .padding(12.dp),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        // Horas
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            FilledTonalIconButton(
                onClick = { onHourChange((hour + 1) % 24) },
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier.size(36.dp),
            ) {
                Text("+", style = MaterialTheme.typography.titleMedium)
            }
            Text(
                text = String.format("%02d", hour),
                style = MaterialTheme.typography.headlineMedium.copy(
                    fontFamily = FontFamily.Monospace,
                    fontFeatureSettings = "tnum",
                    fontWeight = FontWeight.Bold,
                ),
                modifier = Modifier.padding(vertical = 4.dp),
            )
            FilledTonalIconButton(
                onClick = { onHourChange(if (hour == 0) 23 else hour - 1) },
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier.size(36.dp),
            ) {
                Text("-", style = MaterialTheme.typography.titleMedium)
            }
            Text(
                text = stringResource(R.string.power_schedule_hour_label),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        Text(
            text = ":",
            style = MaterialTheme.typography.headlineLarge.copy(
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
            ),
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp),
        )

        // Minutos
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            FilledTonalIconButton(
                onClick = { onMinuteChange((minute + 5) % 60) },
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier.size(36.dp),
            ) {
                Text("+", style = MaterialTheme.typography.titleMedium)
            }
            Text(
                text = String.format("%02d", minute),
                style = MaterialTheme.typography.headlineMedium.copy(
                    fontFamily = FontFamily.Monospace,
                    fontFeatureSettings = "tnum",
                    fontWeight = FontWeight.Bold,
                ),
                modifier = Modifier.padding(vertical = 4.dp),
            )
            FilledTonalIconButton(
                onClick = { onMinuteChange(if (minute < 5) 55 else minute - 5) },
                shape = RoundedCornerShape(10.dp),
                modifier = Modifier.size(36.dp),
            ) {
                Text("-", style = MaterialTheme.typography.titleMedium)
            }
            Text(
                text = stringResource(R.string.power_schedule_minute_label),
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/**
 * Seletor de dias da semana com chips D, S, T, Q, Q, S, S e atalhos rápidos.
 */
@Composable
private fun ScheduleDaysSelector(
    selectedDays: Set<Int>,
    onDaysChange: (Set<Int>) -> Unit,
    modifier: Modifier = Modifier,
) {
    val days = listOf(
        Calendar.SUNDAY to stringResource(R.string.day_sun_letter),
        Calendar.MONDAY to stringResource(R.string.day_mon_letter),
        Calendar.TUESDAY to stringResource(R.string.day_tue_letter),
        Calendar.WEDNESDAY to stringResource(R.string.day_wed_letter),
        Calendar.THURSDAY to stringResource(R.string.day_thu_letter),
        Calendar.FRIDAY to stringResource(R.string.day_fri_letter),
        Calendar.SATURDAY to stringResource(R.string.day_sat_letter),
    )

    Column(
        modifier = modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            days.forEach { (dayId, letter) ->
                val isSelected = selectedDays.contains(dayId)
                Surface(
                    shape = CircleShape,
                    color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
                    border = BorderStroke(
                        1.dp,
                        if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant,
                    ),
                    modifier = Modifier
                        .size(36.dp)
                        .clickable {
                            val next = if (isSelected) selectedDays - dayId else selectedDays + dayId
                            onDaysChange(next)
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

        // Atalhos "Dias Úteis", "Todos os Dias", "Fins de Semana"
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            AssistChip(
                onClick = {
                    onDaysChange(setOf(Calendar.MONDAY, Calendar.TUESDAY, Calendar.WEDNESDAY, Calendar.THURSDAY, Calendar.FRIDAY))
                },
                label = { Text(stringResource(R.string.power_schedule_days_weekdays), style = MaterialTheme.typography.labelSmall) },
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.weight(1f),
            )
            AssistChip(
                onClick = {
                    onDaysChange(setOf(Calendar.SUNDAY, Calendar.MONDAY, Calendar.TUESDAY, Calendar.WEDNESDAY, Calendar.THURSDAY, Calendar.FRIDAY, Calendar.SATURDAY))
                },
                label = { Text(stringResource(R.string.power_schedule_days_everyday), style = MaterialTheme.typography.labelSmall) },
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.weight(1f),
            )
            AssistChip(
                onClick = {
                    onDaysChange(setOf(Calendar.SUNDAY, Calendar.SATURDAY))
                },
                label = { Text(stringResource(R.string.power_schedule_days_weekends), style = MaterialTheme.typography.labelSmall) },
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.weight(1f),
            )
        }
    }
}

/**
 * Formata o resumo legível dos dias selecionados.
 */
private fun formatDaysSummary(context: Context, days: Set<Int>): String {
    if (days.size == 7) {
        return context.getString(R.string.power_schedule_days_everyday)
    }
    val weekdays = setOf(Calendar.MONDAY, Calendar.TUESDAY, Calendar.WEDNESDAY, Calendar.THURSDAY, Calendar.FRIDAY)
    if (days == weekdays) {
        return context.getString(R.string.power_schedule_days_weekdays)
    }
    val weekends = setOf(Calendar.SUNDAY, Calendar.SATURDAY)
    if (days == weekends) {
        return context.getString(R.string.power_schedule_days_weekends)
    }
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

/**
 * Botão imediato de ação de energia com cantos arredondados de 18dp.
 */
@Composable
private fun PowerImmediateButton(
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

    val colors = if (isHighlighted) {
        ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
        )
    } else if (isDestructive) {
        ButtonDefaults.filledTonalButtonColors(
            containerColor = MaterialTheme.colorScheme.errorContainer.copy(alpha = if (isGlass) 0.35f else 0.22f),
            contentColor = MaterialTheme.colorScheme.error,
            disabledContainerColor = ink.copy(alpha = 0.04f),
            disabledContentColor = ink.copy(alpha = 0.38f),
        )
    } else {
        ButtonDefaults.filledTonalButtonColors(
            containerColor = ink.copy(alpha = if (isGlass) 0.12f else 0.08f),
            contentColor = ink,
            disabledContainerColor = ink.copy(alpha = 0.04f),
            disabledContentColor = ink.copy(alpha = 0.38f),
        )
    }

    val border = if (isHighlighted) {
        BorderStroke(1.dp, MaterialTheme.colorScheme.primary)
    } else if (isDestructive) {
        BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.25f))
    } else {
        BorderStroke(1.dp, ink.copy(alpha = 0.12f))
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
        Icon(
            painter = painterResource(icon),
            contentDescription = null,
            modifier = Modifier.size(17.dp),
        )
        Spacer(Modifier.width(8.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelLarge,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}
