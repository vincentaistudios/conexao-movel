// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.downloader

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale

internal data class InspectedMedia(
    val title: String,
    val uploader: String,
    val durationSeconds: Long,
    val extractor: String,
)

internal data class DownloadTaskState(
    val id: String,
    val title: String,
    val status: String,
    val progress: Float,
    val speed: String,
    val eta: String,
    val error: String?,
    val destination: String = "phone",
    val generatedFiles: List<String> = emptyList(),
) {
    val isActive: Boolean
        get() = status == "downloading"
}

internal data class DownloadHistoryItem(
    val id: String,
    val title: String,
    val url: String,
    val format: String,
    val destination: String,
    val status: String,
)

internal val DownloaderIcon: ImageVector by lazy {
    buildDownloaderVector("DownloaderIcon", "M12,3v12 M7,10l5,5 5,-5 M4,19h16", 1.9f)
}

internal val PasteIcon: ImageVector by lazy {
    buildDownloaderVector(
        "PasteIcon",
        "M9,4h6 M9,2.5h6a1.5,1.5 0,0 1,1.5 1.5V6h-9V4A1.5,1.5 0,0 1,9 2.5z M7,5H5a2,2 0,0 0,-2 2v13a2,2 0,0 0,2 2h14a2,2 0,0 0,2 -2V7a2,2 0,0 0,-2 -2h-2",
        1.85f,
    )
}

internal val ClearIcon: ImageVector by lazy {
    buildDownloaderVector("ClearIcon", "M18,6L6,18 M6,6L18,18", 2f)
}

internal val RefreshIcon: ImageVector by lazy {
    buildDownloaderVector("RefreshIcon", "M21,12a9,9 0,1 1,-2.64 -6.36 M21,3v6h-6", 1.85f)
}

internal val CheckIcon: ImageVector by lazy {
    buildDownloaderVector("CheckIcon", "M20,6L9,17l-5,-5", 2f)
}

private fun buildDownloaderVector(name: String, pathData: String, strokeWidth: Float): ImageVector =
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

internal fun parseInspectedMedia(
    raw: String,
    fallbackTitle: String,
    fallbackAuthor: String,
    fallbackError: String = "",
): Result<InspectedMedia> =
    runCatching {
        val json = JSONObject(raw)
        if (!json.optBoolean("success", true)) {
            error(json.optString("error").ifBlank { fallbackError })
        }
        InspectedMedia(
            title = json.optString("title").ifBlank { fallbackTitle },
            uploader = json.optString("uploader").ifBlank { fallbackAuthor },
            durationSeconds = json.optLong("duration", 0L),
            extractor = json.optString("extractor").ifBlank { "web" },
        )
    }

internal fun parseDownloadTask(raw: String, fallbackId: String, fallbackTitle: String): DownloadTaskState {
    val root = JSONObject(raw)
    val task = root.optJSONObject("task") ?: root
    val filesArray = task.optJSONArray("generated_files")
    val filesList = buildList {
        if (filesArray != null) {
            for (i in 0 until filesArray.length()) {
                val f = filesArray.optString(i)
                if (f.isNotBlank()) add(f)
            }
        }
    }
    return DownloadTaskState(
        id = task.optString("id").ifBlank { fallbackId },
        title = task.optString("title").ifBlank { fallbackTitle },
        status = task.optString("status", "downloading").lowercase(Locale.ROOT),
        progress = task.optDouble("progress", 0.0).toFloat().coerceIn(0f, 100f),
        speed = task.optString("speed", ""),
        eta = task.optString("eta", "--:--"),
        error = task.optString("error").takeIf { it.isNotBlank() && it != "null" },
        destination = task.optString("destination", "phone"),
        generatedFiles = filesList,
    )
}

internal fun friendlyDownloaderError(rawError: String?, isWaking: Boolean): String {
    val err = rawError?.lowercase(Locale.ROOT).orEmpty()
    return when {
        isWaking ||
        err.contains("indisponível") ||
        err.contains("indisponivel") ||
        err.contains("unavailable") ||
        err.contains("refused") ||
        err.contains("recusada") ||
        err.contains("reset") ||
        err.contains("timeout") ||
        err.contains("não conectado") ||
        err.contains("nao conectado") ||
        err.contains("not connected") ||
        err.contains("offline") ||
        err.contains("starting") ||
        err.contains("iniciando") -> {
            "O computador está ligando ou iniciando o serviço de downloads. Aguarde alguns instantes…"
        }
        err.isNotBlank() -> rawError ?: "Falha na comunicação com o computador."
        else -> "Falha na comunicação com o computador."
    }
}

internal fun parseDownloadHistory(raw: String, fallbackTitle: String): List<DownloadHistoryItem> {
    val trimmed = raw.trim()
    val arr = if (trimmed.startsWith("[")) {
        JSONArray(trimmed)
    } else {
        JSONObject(trimmed).optJSONArray("history") ?: JSONArray()
    }
    return buildList {
        for (i in 0 until arr.length()) {
            val item = arr.optJSONObject(i) ?: continue
            add(
                DownloadHistoryItem(
                    id = item.optString("id"),
                    title = item.optString("title").ifBlank { item.optString("url").ifBlank { fallbackTitle } },
                    url = item.optString("url"),
                    format = item.optString("format", "video"),
                    destination = item.optString("destination", "pc"),
                    status = item.optString("status", "completed").lowercase(Locale.ROOT),
                ),
            )
        }
    }
}

internal fun formatMediaDuration(seconds: Long, unknownLabel: String): String {
    if (seconds <= 0L) return unknownLabel
    val hrs = seconds / 3600L
    val mins = (seconds % 3600L) / 60L
    val secs = seconds % 60L
    return if (hrs > 0L) {
        String.format(Locale.getDefault(), "%d:%02d:%02d", hrs, mins, secs)
    } else {
        String.format(Locale.getDefault(), "%02d:%02d", mins, secs)
    }
}
