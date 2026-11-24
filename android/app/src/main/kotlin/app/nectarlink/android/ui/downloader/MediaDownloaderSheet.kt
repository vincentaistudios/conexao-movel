// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.downloader

import android.content.ClipboardManager
import android.widget.Toast
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SnackbarDuration
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.nectarlink.android.R
import app.nectarlink.android.core.Device
import app.nectarlink.android.core.WakeState
import app.nectarlink.android.files.ReceivedFiles
import app.nectarlink.android.ui.theme.bentoWell
import app.nectarlink.android.ui.theme.glassModalContainerColor
import app.nectarlink.android.ui.theme.glassModalScrimColor
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.json.JSONObject

/**
 * Modal inferior de download de midias remotas no PC (YouTube, Instagram, TikTok, X e links diretos).
 * Comunica-se com o PC via callback [onRpc] para inspect, start, status, cancel e history.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MediaDownloaderSheet(
    device: Device,
    onRpc: suspend (op: String, payloadJson: String) -> Result<String>,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val scope = rememberCoroutineScope()

    var urlInput by remember { mutableStateOf("") }
    var selectedFormat by remember { mutableStateOf("video") }
    var selectedDestination by remember { mutableStateOf("phone") }
    var inspecting by remember { mutableStateOf(false) }
    var starting by remember { mutableStateOf(false) }
    var inspectedMedia by remember { mutableStateOf<InspectedMedia?>(null) }
    var activeTask by remember { mutableStateOf<DownloadTaskState?>(null) }
    var history by remember { mutableStateOf<List<DownloadHistoryItem>>(emptyList()) }
    var historyExpanded by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val snackbarHostState = remember { SnackbarHostState() }

    val fallbackTitle = stringResource(R.string.downloader_unknown_title)
    val fallbackAuthor = stringResource(R.string.downloader_unknown_author)
    val clipboardEmptyText = stringResource(R.string.downloader_clipboard_empty)
    val inspectErrorText = stringResource(R.string.downloader_inspect_error)
    val startErrorText = stringResource(R.string.downloader_start_error)

    fun refreshHistory() {
        if (!device.online) return
        scope.launch {
            onRpc("history", "{}").onSuccess { raw ->
                runCatching { parseDownloadHistory(raw, fallbackTitle) }.onSuccess { history = it }
            }.onFailure {
                if (!device.online || device.wakeState == WakeState.Waking) {
                    errorMessage = friendlyDownloaderError(it.message, true)
                }
            }
        }
    }

    LaunchedEffect(device.id, device.online) { if (device.online) refreshHistory() }

    // Polling de progresso a cada 800ms enquanto o download estiver ativo
    LaunchedEffect(activeTask?.id, activeTask?.isActive) {
        val current = activeTask ?: return@LaunchedEffect
        if (!current.isActive) return@LaunchedEffect
        while (true) {
            delay(800L)
            onRpc("status", JSONObject().put("task_id", current.id).toString()).onSuccess { raw ->
                val updated = runCatching { parseDownloadTask(raw, current.id, current.title) }.getOrNull()
                if (updated != null) {
                    activeTask = updated
                    if (!updated.isActive) {
                        if (updated.status == "completed") {
                            ReceivedFiles.ensureDirectory(context)
                            val toastMsg = context.getString(R.string.downloader_completed_toast, updated.title)
                            Toast.makeText(context, toastMsg, Toast.LENGTH_LONG).show()
                            scope.launch {
                                snackbarHostState.showSnackbar(
                                    message = toastMsg,
                                    duration = SnackbarDuration.Short,
                                )
                            }
                        }
                        refreshHistory()
                        return@LaunchedEffect
                    }
                }
            }
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
        Box(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp)
                    .padding(bottom = 36.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                DownloaderSheetHeader(deviceName = device.name, onDismiss = onDismiss)
                if (device.wakeState == WakeState.Waking) {
                    DownloaderNoticeBanner(text = stringResource(R.string.downloader_service_starting), isError = false)
                } else if (!device.online) {
                    DownloaderNoticeBanner(text = stringResource(R.string.downloader_offline_hint), isError = false)
                }

            OutlinedTextField(
                value = urlInput,
                onValueChange = { urlInput = it; errorMessage = null },
                label = { Text(stringResource(R.string.downloader_url_label)) },
                placeholder = { Text(stringResource(R.string.downloader_url_placeholder)) },
                singleLine = true,
                shape = RoundedCornerShape(16.dp),
                trailingIcon = {
                    if (urlInput.isNotEmpty()) {
                        IconButton(onClick = { urlInput = ""; inspectedMedia = null }) {
                            Icon(ClearIcon, stringResource(R.string.downloader_clear_url), modifier = Modifier.size(18.dp))
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            )

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                FilledTonalButton(
                    onClick = {
                        val cm = context.getSystemService(ClipboardManager::class.java)
                        val clip = cm?.primaryClip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(context)?.toString()?.trim().orEmpty()
                        if (clip.isNotBlank()) { urlInput = clip; errorMessage = null } else { errorMessage = clipboardEmptyText }
                    },
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.weight(1f).heightIn(min = 46.dp),
                ) {
                    Icon(PasteIcon, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(6.dp))
                    Text(stringResource(R.string.downloader_paste), maxLines = 1)
                }

                Button(
                    onClick = {
                        val targetUrl = urlInput.trim()
                        if (targetUrl.isBlank()) return@Button
                        inspecting = true; errorMessage = null
                        scope.launch {
                            val res = onRpc("inspect", JSONObject().put("url", targetUrl).toString())
                            inspecting = false
                            val isWakingOrOffline = !device.online || device.wakeState == WakeState.Waking
                            res.onSuccess { raw ->
                                parseInspectedMedia(raw, fallbackTitle, fallbackAuthor, inspectErrorText)
                                    .onSuccess { inspectedMedia = it }
                                    .onFailure { errorMessage = friendlyDownloaderError(it.message, isWakingOrOffline) }
                            }.onFailure { errorMessage = friendlyDownloaderError(it.message, isWakingOrOffline) }
                        }
                    },
                    enabled = device.online && urlInput.isNotBlank() && !inspecting,
                    shape = RoundedCornerShape(14.dp),
                    modifier = Modifier.weight(1.4f).heightIn(min = 46.dp),
                ) {
                    Text(stringResource(if (inspecting) R.string.downloader_inspecting else R.string.downloader_inspect), maxLines = 1)
                }
            }

            errorMessage?.let { DownloaderNoticeBanner(text = it, isError = true) }
            inspectedMedia?.let { InspectedMediaCard(media = it) }

            OptionChipsGroup(
                label = stringResource(R.string.downloader_format_label),
                options = listOf(
                    "video" to stringResource(R.string.downloader_format_video),
                    "audio" to stringResource(R.string.downloader_format_audio),
                    "both" to stringResource(R.string.downloader_format_both),
                ),
                selectedKey = selectedFormat,
                onSelect = { selectedFormat = it },
            )

            OptionChipsGroup(
                label = stringResource(R.string.downloader_destination_label),
                options = listOf(
                    "phone" to stringResource(R.string.downloader_dest_phone),
                    "pc" to stringResource(R.string.downloader_dest_pc),
                    "both" to stringResource(R.string.downloader_dest_both),
                ),
                selectedKey = selectedDestination,
                onSelect = { selectedDestination = it },
            )

            Button(
                onClick = {
                    val targetUrl = urlInput.trim()
                    if (targetUrl.isBlank()) return@Button
                    starting = true; errorMessage = null
                    scope.launch {
                        val payload = JSONObject().put("url", targetUrl).put("format", selectedFormat).put("destination", selectedDestination).toString()
                        val res = onRpc("start", payload)
                        starting = false
                        val isWakingOrOffline = !device.online || device.wakeState == WakeState.Waking
                        res.onSuccess { raw ->
                            runCatching { JSONObject(raw) }.onSuccess { json ->
                                if (!json.optBoolean("success", true)) {
                                    errorMessage = friendlyDownloaderError(json.optString("error").ifBlank { startErrorText }, isWakingOrOffline)
                                    return@onSuccess
                                }
                                val taskId = json.optString("task_id").ifBlank { json.optString("id") }
                                if (taskId.isNotBlank()) {
                                    activeTask = DownloadTaskState(
                                        id = taskId,
                                        title = inspectedMedia?.title ?: targetUrl,
                                        status = "downloading",
                                        progress = 0f,
                                        speed = "",
                                        eta = "--:--",
                                        error = null,
                                        destination = selectedDestination,
                                    )
                                }
                            }.onFailure { errorMessage = friendlyDownloaderError(it.message, isWakingOrOffline) }
                        }.onFailure { errorMessage = friendlyDownloaderError(it.message, isWakingOrOffline) }
                    }
                },
                enabled = device.online && urlInput.isNotBlank() && !starting && activeTask?.isActive != true,
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
            ) {
                Icon(DownloaderIcon, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text(stringResource(if (starting) R.string.downloader_starting else R.string.downloader_start), style = MaterialTheme.typography.labelLarge)
            }

            activeTask?.let { task ->
                ActiveDownloadProgressCard(
                    task = task,
                    onCancel = {
                        scope.launch {
                            onRpc("cancel", JSONObject().put("task_id", task.id).toString()).onSuccess {
                                activeTask = task.copy(status = "cancelled", speed = "")
                                refreshHistory()
                            }
                        }
                    },
                )
            }

            RecentDownloadsSection(
                history = history,
                expanded = historyExpanded,
                onToggleExpanded = { historyExpanded = !historyExpanded; if (historyExpanded) refreshHistory() },
                onRefresh = { refreshHistory() },
            )
        }

        SnackbarHost(
            hostState = snackbarHostState,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 12.dp, start = 16.dp, end = 16.dp),
        )
    }
}
}

@Composable
private fun DownloaderSheetHeader(deviceName: String, onDismiss: () -> Unit) {
    val ink = MaterialTheme.colorScheme.onSurface
    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier.size(42.dp).clip(CircleShape).bentoWell(
                cornerRadius = 21.dp,
                fillColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.16f),
                borderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.35f),
            ),
            contentAlignment = Alignment.Center,
        ) {
            Icon(DownloaderIcon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
        }
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(stringResource(R.string.downloader_title), style = MaterialTheme.typography.titleLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                text = "$deviceName · ${stringResource(R.string.downloader_subtitle)}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        IconButton(onClick = onDismiss) {
            Icon(ClearIcon, stringResource(R.string.desk_exit), tint = ink.copy(alpha = 0.7f), modifier = Modifier.size(20.dp))
        }
    }
}

@Composable
private fun OptionChipsGroup(label: String, options: List<Pair<String, String>>, selectedKey: String, onSelect: (String) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(label, style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold), color = MaterialTheme.colorScheme.onSurfaceVariant)
        Row(modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            options.forEach { (key, title) ->
                FilterChip(
                    selected = selectedKey == key,
                    onClick = { onSelect(key) },
                    label = { Text(title, style = MaterialTheme.typography.labelMedium, maxLines = 1) },
                    shape = RoundedCornerShape(14.dp),
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                        selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer,
                    ),
                )
            }
        }
    }
}

@Composable
private fun DownloaderNoticeBanner(text: String, isError: Boolean) {
    val container = if (isError) MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.75f) else MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.8f)
    val content = if (isError) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onSecondaryContainer
    Surface(shape = RoundedCornerShape(14.dp), color = container, contentColor = content, border = BorderStroke(1.dp, content.copy(alpha = 0.2f)), modifier = Modifier.fillMaxWidth()) {
        Text(text = text, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp))
    }
}
