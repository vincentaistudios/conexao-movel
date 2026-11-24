// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.desk

import android.text.format.DateFormat
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalLocale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.nectarlink.android.R
import app.nectarlink.android.core.Device
import app.nectarlink.android.core.WakeState
import kotlinx.coroutines.delay
import java.text.SimpleDateFormat
import java.util.Date

@Composable
internal fun DeskActionButton(
    label: String,
    enabled: Boolean,
    isSecondary: Boolean = false,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    FilledTonalButton(
        onClick = onClick,
        enabled = enabled,
        shape = RoundedCornerShape(18.dp),
        colors = ButtonDefaults.filledTonalButtonColors(
            containerColor = if (isSecondary) Color(0xFF12141B) else Color(0xFF171B24),
            contentColor = if (isSecondary) Color(0xFFD1D5DB) else Color(0xFFF3F4F6),
            disabledContainerColor = Color(0xFF0C0E12),
            disabledContentColor = Color(0xFF4B5563),
        ),
        border = BorderStroke(
            1.dp,
            if (isSecondary) Color(0xFF262A36) else Color(0xFF2B3140),
        ),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 13.dp),
        modifier = modifier,
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.labelLarge,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
internal fun DeskClockDisplay() {
    var nowMs by remember { mutableLongStateOf(System.currentTimeMillis()) }
    LaunchedEffect(Unit) {
        while (true) {
            val current = System.currentTimeMillis()
            nowMs = current
            delay((1_000L - (current % 1_000L)).coerceIn(100L, 1_000L))
        }
    }

    val locale = LocalLocale.current.platformLocale
    val timeFormat = remember(locale) { SimpleDateFormat("HH:mm", locale) }
    val secFormat = remember(locale) { SimpleDateFormat(":ss", locale) }
    val dateFormat = remember(locale) {
        val pattern = DateFormat.getBestDateTimePattern(locale, "EEEEMMMMd")
        SimpleDateFormat(pattern, locale)
    }

    val minuteKey = nowMs / 60_000L
    val secondKey = nowMs / 1_000L
    val timeText = remember(minuteKey, locale) { timeFormat.format(Date(minuteKey * 60_000L)) }
    val dateText = remember(minuteKey, locale) { dateFormat.format(Date(minuteKey * 60_000L)) }
    val secText = remember(secondKey, locale) { secFormat.format(Date(secondKey * 1_000L)) }

    Row(
        verticalAlignment = Alignment.Bottom,
        horizontalArrangement = Arrangement.Center,
    ) {
        Text(
            text = timeText,
            fontSize = 84.sp,
            lineHeight = 88.sp,
            fontWeight = FontWeight.Light,
            fontFamily = FontFamily.Monospace,
            color = Color(0xFFF3F4F6),
        )
        Text(
            text = secText,
            fontSize = 28.sp,
            fontWeight = FontWeight.Normal,
            fontFamily = FontFamily.Monospace,
            color = Color(0xFF9CA3AF),
            modifier = Modifier.padding(bottom = 12.dp, start = 4.dp),
        )
    }

    Text(
        text = dateText,
        style = MaterialTheme.typography.titleMedium,
        color = Color(0xFF9CA3AF),
    )
}

@Composable
internal fun DeskOfflineWakeCard(
    device: Device,
    onWake: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        shape = RoundedCornerShape(26.dp),
        color = Color(0xFF0E1015),
        border = BorderStroke(1.dp, Color(0xFF222631)),
        modifier = modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(horizontal = 20.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            when {
                device.wakeState == WakeState.Waking -> {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_wake),
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(24.dp),
                        )
                        Text(
                            text = stringResource(R.string.wake_waking, device.name),
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                            color = Color(0xFFF3F4F6),
                        )
                    }
                    Text(
                        text = stringResource(R.string.wake_magic_packet_sent),
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFF9CA3AF),
                        textAlign = TextAlign.Center,
                    )
                    LinearProgressIndicator(
                        modifier = Modifier.fillMaxWidth().height(6.dp),
                        color = MaterialTheme.colorScheme.primary,
                        trackColor = Color(0xFF222631),
                    )
                    OutlinedButton(
                        onClick = onWake,
                        border = BorderStroke(1.dp, Color(0xFF2E3444)),
                    ) {
                        Text(stringResource(R.string.wake_retry_packet), color = Color(0xFFD1D5DB))
                    }
                }
                device.wakeState == WakeState.TimedOut -> {
                    Text(
                        text = stringResource(R.string.wake_timeout_title, device.name),
                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                        color = MaterialTheme.colorScheme.error,
                    )
                    Text(
                        text = stringResource(R.string.wake_timeout_text, device.name),
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFF9CA3AF),
                        textAlign = TextAlign.Center,
                    )
                    FilledTonalButton(
                        onClick = onWake,
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer,
                            contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                        ),
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_wake),
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(stringResource(R.string.power_action_wake))
                    }
                }
                else -> {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_power),
                            contentDescription = null,
                            tint = Color(0xFF9CA3AF),
                            modifier = Modifier.size(20.dp),
                        )
                        Text(
                            text = "${device.name} · Offline",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                            color = Color(0xFFF3F4F6),
                        )
                    }
                    Text(
                        text = stringResource(R.string.wake_offline_card_desc),
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFF9CA3AF),
                        textAlign = TextAlign.Center,
                    )
                    if (!device.canWake) {
                        Text(
                            text = stringResource(R.string.wake_not_ready_hint, device.name),
                            style = MaterialTheme.typography.labelSmall,
                            color = Color(0xFF6B7280),
                            textAlign = TextAlign.Center,
                        )
                    }
                    FilledTonalButton(
                        onClick = onWake,
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer,
                            contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                        ),
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_wake),
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(Modifier.width(8.dp))
                        Text(stringResource(R.string.power_action_wake))
                    }
                }
            }
        }
    }
}
