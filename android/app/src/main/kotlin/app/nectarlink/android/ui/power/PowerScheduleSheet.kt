// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.power

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.nectarlink.android.R
import app.nectarlink.android.core.Device
import app.nectarlink.android.core.WakeState
import app.nectarlink.android.power.PowerSchedulerManager
import app.nectarlink.android.ui.theme.LocalGlassTheme
import app.nectarlink.android.ui.theme.bentoWell
import app.nectarlink.android.ui.theme.glassModalContainerColor
import app.nectarlink.android.ui.theme.glassModalScrimColor

/**
 * Modal inferior de controle de energia do PC, temporizador regressivo e agendamentos.
 * Segue a linguagem visual Dark Glass / Fluent do Conexao Movel sem emojis Unicode.
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
    val schedulerManager = remember(context) { PowerSchedulerManager(context) }

    var confirmShutdown by remember { mutableStateOf(false) }
    var confirmRestart by remember { mutableStateOf(false) }
    var showWakeNotReadyHint by remember(device.id) { mutableStateOf(false) }

    // Oculta automaticamente o aviso de WoL indisponivel caso o PC fique pronto ou online
    LaunchedEffect(device.online, device.canWake) {
        if (device.online || device.canWake) {
            showWakeNotReadyHint = false
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
            PowerSheetHeader(
                deviceName = device.name,
                onDismiss = onDismiss,
            )

            ImmediatePowerActionsSection(
                device = device,
                showWakeNotReadyHint = showWakeNotReadyHint,
                onWakeClick = {
                    if (!device.canWake) {
                        showWakeNotReadyHint = true
                    } else {
                        showWakeNotReadyHint = false
                        onWake()
                    }
                },
                onDismissWakeHint = { showWakeNotReadyHint = false },
                onSleep = onSleep,
                onLock = onLock,
                onRequestShutdown = { confirmShutdown = true },
                onRequestRestart = { confirmRestart = true },
            )

            SleepTimerSection(
                device = device,
                schedulerManager = schedulerManager,
            )

            RecurringSchedulesSection(
                device = device,
                schedulerManager = schedulerManager,
            )
        }
    }

    if (confirmShutdown) {
        PowerShutdownConfirmDialog(
            deviceName = device.name,
            onConfirm = {
                confirmShutdown = false
                onShutdown()
            },
            onDismiss = { confirmShutdown = false },
        )
    }

    if (confirmRestart) {
        PowerRestartConfirmDialog(
            deviceName = device.name,
            onConfirm = {
                confirmRestart = false
                onRestart()
            },
            onDismiss = { confirmRestart = false },
        )
    }
}

@Composable
private fun PowerSheetHeader(
    deviceName: String,
    onDismiss: () -> Unit,
) {
    val ink = MaterialTheme.colorScheme.onSurface
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
                text = "$deviceName · ${stringResource(R.string.power_schedule_device_subtitle)}",
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
}

@Composable
private fun ImmediatePowerActionsSection(
    device: Device,
    showWakeNotReadyHint: Boolean,
    onWakeClick: () -> Unit,
    onDismissWakeHint: () -> Unit,
    onSleep: () -> Unit,
    onLock: () -> Unit,
    onRequestShutdown: () -> Unit,
    onRequestRestart: () -> Unit,
) {
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onSurface

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(
            text = stringResource(R.string.power_section_immediate),
            style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
            color = ink.copy(alpha = 0.72f),
            modifier = Modifier.padding(start = 2.dp),
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            val canHighlightWake = !device.online && device.canWake
            PowerImmediateButton(
                icon = R.drawable.ic_wake,
                label = stringResource(R.string.power_action_wake),
                isHighlighted = canHighlightWake,
                enabled = !device.online && device.wakeState != WakeState.Waking,
                onClick = onWakeClick,
                modifier = Modifier.weight(1f),
            )

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
            PowerImmediateButton(
                icon = R.drawable.ic_power,
                label = stringResource(R.string.power_action_shutdown),
                isHighlighted = false,
                isDestructive = true,
                enabled = device.online,
                onClick = onRequestShutdown,
                modifier = Modifier.weight(1f),
            )

            PowerImmediateButton(
                icon = R.drawable.ic_restart,
                label = stringResource(R.string.power_action_restart),
                isHighlighted = false,
                enabled = device.online,
                onClick = onRequestRestart,
                modifier = Modifier.weight(1f),
            )
        }

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

        AnimatedVisibility(visible = !device.online && device.wakeState == WakeState.Waking) {
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = stringResource(R.string.wake_waking, device.name),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
                LinearProgressIndicator(
                    modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(4.dp)),
                )
            }
        }

        AnimatedVisibility(visible = showWakeNotReadyHint && !device.online && !device.canWake) {
            Surface(
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.85f),
                contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.25f)),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Icon(
                        painter = painterResource(R.drawable.ic_wake),
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Text(
                        text = stringResource(R.string.wake_not_ready, device.name),
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(
                        onClick = onDismissWakeHint,
                        modifier = Modifier.size(28.dp),
                    ) {
                        Icon(
                            imageVector = CloseIcon,
                            contentDescription = stringResource(R.string.power_dialog_cancel),
                            modifier = Modifier.size(16.dp),
                        )
                    }
                }
            }
        }
    }
}
