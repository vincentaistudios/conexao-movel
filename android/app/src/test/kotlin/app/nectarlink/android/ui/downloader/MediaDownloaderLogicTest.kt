// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.downloader

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MediaDownloaderLogicTest {

    @Test
    fun `parseDownloadTask extrai campos essenciais e arquivos gerados corretamente`() {
        val json = """
            {
                "success": true,
                "task": {
                    "id": "task_100",
                    "title": "Apresentacao Tecnica",
                    "status": "completed",
                    "progress": 100.0,
                    "speed": "5.4 MB/s",
                    "eta": "00:00",
                    "destination": "phone",
                    "generated_files": ["/tmp/video.mp4", "/tmp/audio.mp3"]
                }
            }
        """.trimIndent()

        val parsed = parseDownloadTask(json, "default_id", "default_title")
        assertEquals("task_100", parsed.id)
        assertEquals("Apresentacao Tecnica", parsed.title)
        assertEquals("completed", parsed.status)
        assertEquals(100f, parsed.progress)
        assertEquals("phone", parsed.destination)
        assertEquals(2, parsed.generatedFiles.size)
        assertEquals("/tmp/video.mp4", parsed.generatedFiles[0])
        assertFalse(parsed.isActive)
    }

    @Test
    fun `friendlyDownloaderError trata mensagens de servico iniciando ou reconexao de forma amigavel`() {
        val wakingMsg = friendlyDownloaderError("qualquer erro", isWaking = true)
        assertTrue(wakingMsg.contains("ligando ou iniciando"))

        val offlineMsg = friendlyDownloaderError("Servico local de downloads indisponivel na porta 28795", isWaking = false)
        assertTrue(offlineMsg.contains("ligando ou iniciando"))

        val timeoutMsg = friendlyDownloaderError("java.net.SocketTimeoutException: connection timed out", isWaking = false)
        assertTrue(timeoutMsg.contains("ligando ou iniciando"))

        val refusedMsg = friendlyDownloaderError("Connection refused by peer", isWaking = false)
        assertTrue(refusedMsg.contains("ligando ou iniciando"))

        val customErr = friendlyDownloaderError("URL de plataforma nao suportada", isWaking = false)
        assertEquals("URL de plataforma nao suportada", customErr)
    }

    @Test
    fun `formatMediaDuration formata duracoes corretamente sem emojis`() {
        assertEquals("Desconhecido", formatMediaDuration(0, "Desconhecido"))
        assertEquals("01:30", formatMediaDuration(90, "Desconhecido"))
        assertEquals("1:01:05", formatMediaDuration(3665, "Desconhecido"))
    }

    @Test
    fun `parseInspectedMedia faz parsing seguro com fallback`() {
        val raw = """
            {
                "success": true,
                "title": "Tutorial Conexao Movel",
                "uploader": "Engenharia",
                "duration": 180,
                "extractor": "youtube"
            }
        """.trimIndent()
        val res = parseInspectedMedia(raw, "Sem titulo", "Sem autor")
        assertTrue(res.isSuccess)
        val media = res.getOrThrow()
        assertEquals("Tutorial Conexao Movel", media.title)
        assertEquals("Engenharia", media.uploader)
        assertEquals(180L, media.durationSeconds)
        assertEquals("youtube", media.extractor)
    }
}
