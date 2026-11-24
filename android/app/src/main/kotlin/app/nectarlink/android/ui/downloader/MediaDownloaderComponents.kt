// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.downloader

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.nectarlink.android.R
import app.nectarlink.android.ui.theme.LocalGlassTheme
import app.nectarlink.android.ui.theme.bentoWell
import java.util.Locale

@Composable
internal fun InspectedMediaCard(media: InspectedMedia, modifier: Modifier = Modifier) {
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onSurface
    val durationText = formatMediaDuration(media.durationSeconds, stringResource(R.string.downloader_duration_unknown))

    Column(
        modifier = modifier
            .fillMaxWidth()
            .bentoWell(
                cornerRadius = 18.dp,
                fillColor = MaterialTheme.colorScheme.primary.copy(alpha = if (isGlass) 0.12f else 0.08f),
                borderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.28f),
            )
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Surface(shape = RoundedCornerShape(8.dp), color = MaterialTheme.colorScheme.primary.copy(alpha = 0.18f)) {
                Text(
                    text = media.extractor.uppercase(Locale.getDefault()),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                )
            }
            Text(
                text = durationText,
                style = MaterialTheme.typography.labelMedium.copy(fontFeatureSettings = "tnum"),
                color = ink.copy(alpha = 0.78f),
            )
        }
        Text(
            text = media.title,
            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        Text(
            text = media.uploader,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
internal fun ActiveDownloadProgressCard(
    task: DownloadTaskState,
    onCancel: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val ink = MaterialTheme.colorScheme.onSurface
    val statusText = when (task.status) {
        "completed" -> stringResource(R.string.downloader_status_completed)
        "failed" -> stringResource(R.string.downloader_status_failed)
        "cancelled" -> stringResource(R.string.downloader_status_cancelled)
        else -> stringResource(R.string.downloader_status_downloading)
    }
    val statusColor = when (task.status) {
        "failed" -> MaterialTheme.colorScheme.error
        "cancelled" -> ink.copy(alpha = 0.6f)
        else -> MaterialTheme.colorScheme.primary
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .bentoWell(18.dp, statusColor.copy(alpha = 0.08f), statusColor.copy(alpha = 0.28f))
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(text = statusText, style = MaterialTheme.typography.labelMedium, color = statusColor)
            Text(
                text = "${task.progress.toInt()}%",
                style = MaterialTheme.typography.labelLarge.copy(
                    fontFamily = FontFamily.Monospace,
                    fontFeatureSettings = "tnum",
                    fontWeight = FontWeight.Bold,
                ),
                color = statusColor,
            )
        }
        Text(text = task.title, style = MaterialTheme.typography.bodyMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
        LinearProgressIndicator(
            progress = { (task.progress / 100f).coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
            strokeCap = StrokeCap.Round,
            color = statusColor,
            trackColor = MaterialTheme.colorScheme.surfaceContainerHighest,
        )
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = task.speed.ifBlank { "--" },
                style = MaterialTheme.typography.labelSmall.copy(fontFeatureSettings = "tnum"),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                text = stringResource(R.string.downloader_eta_prefix, task.eta),
                style = MaterialTheme.typography.labelSmall.copy(fontFeatureSettings = "tnum"),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        task.error?.let { err ->
            Text(text = err, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
        }
        if (task.status == "completed") {
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.3f)),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 9.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Icon(
                        imageVector = CheckIcon,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(18.dp),
                    )
                    Text(
                        text = stringResource(R.string.downloader_saved_to_folder),
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }
        }
        if (task.isActive) {
            OutlinedButton(
                onClick = onCancel,
                shape = RoundedCornerShape(14.dp),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.error.copy(alpha = 0.5f)),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error),
                modifier = Modifier.fillMaxWidth().heightIn(min = 40.dp),
            ) {
                Text(stringResource(R.string.downloader_cancel), style = MaterialTheme.typography.labelMedium)
            }
        }
    }
}

@Composable
internal fun RecentDownloadsSection(
    history: List<DownloadHistoryItem>,
    expanded: Boolean,
    onToggleExpanded: () -> Unit,
    onRefresh: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val isGlass = LocalGlassTheme.current
    val ink = MaterialTheme.colorScheme.onSurface

    Column(
        modifier = modifier
            .fillMaxWidth()
            .bentoWell(20.dp, ink.copy(alpha = if (isGlass) 0.08f else 0.04f), ink.copy(alpha = if (isGlass) 0.14f else 0.08f))
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).clickable(onClick = onToggleExpanded),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "${stringResource(R.string.downloader_history_title)} (${history.size})",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
            )
            TextButton(onClick = onRefresh) {
                Icon(imageVector = RefreshIcon, contentDescription = null, modifier = Modifier.size(15.dp))
                Spacer(Modifier.size(4.dp))
                Text(stringResource(R.string.downloader_refresh_history), style = MaterialTheme.typography.labelMedium)
            }
        }
        AnimatedVisibility(visible = expanded) {
            if (history.isEmpty()) {
                Text(
                    text = stringResource(R.string.downloader_history_empty),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    history.take(8).forEach { HistoryRow(it) }
                }
            }
        }
    }
}

@Composable
private fun HistoryRow(item: DownloadHistoryItem) {
    val ink = MaterialTheme.colorScheme.onSurface
    val statusLabel = when (item.status) {
        "completed" -> stringResource(R.string.downloader_status_completed)
        "failed" -> stringResource(R.string.downloader_status_failed)
        "cancelled" -> stringResource(R.string.downloader_status_cancelled)
        else -> stringResource(R.string.downloader_status_downloading)
    }
    val fmtLabel = when (item.format) {
        "audio" -> stringResource(R.string.downloader_format_audio)
        "both" -> stringResource(R.string.downloader_format_both)
        else -> stringResource(R.string.downloader_format_video)
    }
    Surface(
        shape = RoundedCornerShape(12.dp),
        color = ink.copy(alpha = 0.05f),
        border = BorderStroke(1.dp, ink.copy(alpha = 0.08f)),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(text = item.title, style = MaterialTheme.typography.bodySmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(
                    text = "$fmtLabel · ${item.destination.uppercase(Locale.getDefault())}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Text(
                text = statusLabel,
                style = MaterialTheme.typography.labelSmall,
                color = if (item.status == "failed") MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
            )
        }
    }
}
