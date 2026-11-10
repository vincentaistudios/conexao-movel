# SPDX-License-Identifier: GPL-3.0-or-later
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

current_dir = os.path.dirname(os.path.abspath(__file__))
scratch_root = os.path.dirname(current_dir)
sys.path.insert(0, os.path.join(scratch_root, "desktop", "downloader"))

from downloader_service import MediaDownloader, get_yt_dlp_binary

class TestMediaDownloaderService(unittest.TestCase):
    def setUp(self):
        self.downloader = MediaDownloader()
        self.test_url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"

    def test_destination_directory_is_downloads(self):
        """Valida que o destino padrao e obrigatoriamente a pasta Downloads do usuario"""
        expected_dir = os.path.expanduser("~/Downloads")
        self.assertEqual(self.downloader.output_dir, expected_dir)
        self.assertTrue(os.path.isdir(self.downloader.output_dir))

    def test_yt_dlp_binary_found(self):
        """Valida que o binario yt-dlp e localizado e executavel"""
        binary = get_yt_dlp_binary()
        self.assertTrue(os.path.exists(binary))
        self.assertTrue(os.access(binary, os.X_OK))

    def test_inspect_url_structure(self):
        """Valida a extracao de metadados com campos necessarios para a UI"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"title": "Musica Teste", "uploader": "Artista Teste", "duration": 180, "thumbnail": "https://img.youtube.com/vi/123/hqdefault.jpg"}'
            )
            data = self.downloader.inspect_url(self.test_url)
            self.assertTrue(data["success"])
            self.assertEqual(data["title"], "Musica Teste")
            self.assertEqual(data["uploader"], "Artista Teste")
            self.assertEqual(data["duration"], 180)
            self.assertIn("https://", data["thumbnail"])

    def test_inspect_invalid_url(self):
        """Valida tratamento seguro contra URLs invalidas"""
        data = self.downloader.inspect_url("invalid-link")
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_start_download_task_registration(self):
        """Valida inicializacao e registro de tarefa de download"""
        with patch.object(self.downloader, "_run_download_thread"):
            res = self.downloader.start_download(
                task_id="task_unit_1",
                url=self.test_url,
                media_format="audio",
                destination="pc"
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["task_id"], "task_unit_1")
            
            task = self.downloader.get_task_status("task_unit_1")
            self.assertIsNotNone(task)
            self.assertEqual(task["format"], "audio")
            self.assertEqual(task["destination"], "pc")
            self.assertEqual(task["status"], "downloading")

    def test_cancel_download_task(self):
        """Valida cancelamento seguro de tarefa em andamento"""
        with patch.object(self.downloader, "_run_download_thread"):
            self.downloader.start_download(
                task_id="task_cancel_1",
                url=self.test_url,
                media_format="video",
                destination="phone"
            )
            cancelled = self.downloader.cancel_download("task_cancel_1")
            self.assertTrue(cancelled)
            task = self.downloader.get_task_status("task_cancel_1")
            self.assertEqual(task["status"], "cancelled")

    def test_recent_history(self):
        """Valida listagem de historico recente de downloads"""
        with patch.object(self.downloader, "_run_download_thread"):
            self.downloader.start_download("task_h1", self.test_url, "video", "pc")
            self.downloader.start_download("task_h2", self.test_url, "audio", "both")
            
            history = self.downloader.get_recent_history(limit=5)
            self.assertGreaterEqual(len(history), 2)
            ids = [t["id"] for t in history]
            self.assertIn("task_h1", ids)
            self.assertIn("task_h2", ids)

if __name__ == "__main__":
    unittest.main()
