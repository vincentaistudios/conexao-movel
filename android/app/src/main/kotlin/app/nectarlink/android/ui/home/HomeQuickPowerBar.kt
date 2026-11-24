// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.home

import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
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
import app.nectarlink.android.power.PowerActionType
import app.nectarlink.android.power.PowerSchedulerManager
import app.nectarlink.android.ui.theme.LocalGlassTheme
import app.nectarlink.android.ui.theme.bentoWell

/**
 * Faixa compacta de acoes rapidas de energia exibida no topo do cartao do PC.
 * Permite ligar via WoL ou abrir imediatamente Energia e Agendamento sem rolar a tela.
 */
@Composable
internal fun HomeQuickPowerBar(
    device: Device,
    refreshKey: Int,
    onWake: (String) -> Unit,
    onOpenPowerSchedule: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onPrimaryContainer
    val schedulerManager = remember(context) { PowerSchedulerManager(context) }

    val activeTimer = remember(device.id, refreshKey) {
        schedulerManager.getSleepTimer(device.id)
    }
    val activeSchedulesCount = remember(device.id, refreshKey) {
        schedulerManager.getSchedules(device.id).count { it.enabled }
    }

    val timerActionLabel = when (activeTimer?.action) {
        PowerActionType.Wake -> stringResource(R.string.power_action_wake)
        PowerActionType.Sleep -> stringResource(R.string.power_action_sleep)
        PowerActionType.Shutdown -> stringResource(R.string.power_action_shutdown)
        PowerActionType.Reboot -> stringResource(R.string.power_action_restart)
        PowerActionType.Lock -> stringResource(R.string.power_action_lock)
        null -> ""
    }

    val subBadgeText = when {
        activeTimer != null -> stringResource(R.string.quick_power_timer_active, timerActionLabel)
        activeSchedulesCount > 0 -> stringResource(R.string.quick_power_schedules_active, activeSchedulesCount)
        !device.online && device.canWake -> stringResource(R.string.quick_power_wol_ready)
        !device.online -> stringResource(R.string.quick_power_offline_hint)
        else -> stringResource(R.string.quick_power_online_hint)
    }

    val canQuickWake = !device.online && device.canWake && device.wakeState != WakeState.Waking
    val badgeIcon = if (canQuickWake) R.drawable.ic_wake else R.drawable.ic_power

    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .bentoWell(
                cornerRadius = 18.dp,
                fillColor = ink.copy(alpha = if (isGlass) 0.12f else 0.08f),
                borderColor = if (isGlass) ink.copy(alpha = 0.18f) else ink.copy(alpha = 0.08f),
            )
            .clickable { onOpenPowerSchedule(device.id) }
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Box(
            modifier = Modifier
                .size(34.dp)
                .clip(CircleShape)
                .bentoWell(
                    cornerRadius = 17.dp,
                    fillColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.18f),
                    borderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.34f),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                painter = painterResource(badgeIcon),
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(16.dp),
            )
        }

        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = stringResource(R.string.quick_power_title),
                style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.SemiBold),
                color = ink,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                text = subBadgeText,
                style = MaterialTheme.typography.bodySmall,
                color = if (activeTimer != null || activeSchedulesCount > 0) {
                    MaterialTheme.colorScheme.primary
                } else {
                    ink.copy(alpha = 0.72f)
                },
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }

        if (canQuickWake) {
            FilledTonalButton(
                onClick = { onWake(device.id) },
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    contentColor = MaterialTheme.colorScheme.onPrimary,
                ),
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                modifier = Modifier.heightIn(min = 36.dp),
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_wake),
                    contentDescription = null,
                    modifier = Modifier.size(14.dp),
                )
                Spacer(Modifier.width(5.dp))
                Text(
                    text = stringResource(R.string.power_action_wake),
                    style = MaterialTheme.typography.labelMedium,
                    maxLines = 1,
                )
            }
            FilledTonalButton(
                onClick = { onOpenPowerSchedule(device.id) },
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = ink.copy(alpha = if (isGlass) 0.16f else 0.12f),
                    contentColor = ink,
                ),
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp),
                modifier = Modifier.heightIn(min = 36.dp),
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_schedule),
                    contentDescription = stringResource(R.string.quick_power_schedule_button),
                    modifier = Modifier.size(15.dp),
                )
            }
        } else {
            FilledTonalButton(
                onClick = { onOpenPowerSchedule(device.id) },
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.filledTonalButtonColors(
                    containerColor = ink.copy(alpha = if (isGlass) 0.16f else 0.12f),
                    contentColor = ink,
                ),
                contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp),
                modifier = Modifier.heightIn(min = 36.dp),
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_power),
                    contentDescription = null,
                    modifier = Modifier.size(14.dp),
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    text = stringResource(R.string.quick_power_manage_button),
                    style = MaterialTheme.typography.labelMedium,
                    maxLines = 1,
                )
            }
        }
    }
}
