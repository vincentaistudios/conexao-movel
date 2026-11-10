# SPDX-License-Identifier: GPL-3.0-or-later
import os
import json
import urllib.request
import subprocess
import unittest

class TestDownloaderIntegration(unittest.TestCase):
    def setUp(self):
        self.bridge_url = "http://127.0.0.1:28795"

    def test_bridge_service_health(self):
        """Valida que o daemon REST sys-downloader-bridge esta ativo e respondendo na porta 28795"""
        req = urllib.request.Request(f"{self.bridge_url}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "ok")
            self.assertEqual(data.get("service"), "sys-downloader-bridge")

    def test_bridge_history_endpoint(self):
        """Valida que o endpoint /history retorna estrutura valida de lista"""
        req = urllib.request.Request(f"{self.bridge_url}/history")
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("success"))
            self.assertIsInstance(data.get("history"), list)

    def test_bridge_inspect_invalid_url(self):
        """Valida tratamento de erro do endpoint /inspect para URLs invalidas"""
        payload = json.dumps({"url": "invalid-url"}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.bridge_url}/inspect",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertFalse(data.get("success"))
            self.assertIn("error", data)

    def test_systemd_bridge_service_active(self):
        """Valida que a unidade systemd de usuario esta em execucao ativa"""
        res = subprocess.run(
            ["systemctl", "--user", "is-active", "sys-downloader-bridge.service"],
            stdout=subprocess.PIPE,
            text=True
        )
        self.assertEqual(res.stdout.strip(), "active")

    def test_qml_downloads_page_exists_and_configured(self):
        """Valida integridade do componente DownloadsPage.qml e integracao com TransferList"""
        qml_path = "/usr/lib/nectarlink/qml/pages/DownloadsPage.qml"
        self.assertTrue(os.path.exists(qml_path))
        with open(qml_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("TransferList.send", content)
        self.assertIn("selectedFormat", content)
        self.assertIn("selectedDestination", content)
        self.assertIn("http://127.0.0.1:28795", content)

    def test_qml_mainwindow_navigation_rail(self):
        """Valida inclusao do item Downloads na barra lateral e no pageLoader"""
        main_qml = "/usr/lib/nectarlink/qml/MainWindow.qml"
        self.assertTrue(os.path.exists(main_qml))
        with open(main_qml, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('text: qsTr("Downloads")', content)
        self.assertIn('case "downloads": return "pages/DownloadsPage.qml"', content)
        self.assertIn('window.page === "downloads" ? qsTr("Downloads de Mídia")', content)

    def test_qml_homepage_quick_action_tile(self):
        """Valida presenca do botao de acao rapida Baixar midia na pagina inicial"""
        home_qml = "/usr/lib/nectarlink/qml/pages/HomePage.qml"
        self.assertTrue(os.path.exists(home_qml))
        with open(home_qml, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('title: qsTr("Baixar mídia")', content)
        self.assertIn('window.page = "downloads"', content)

    def test_modern_flaticon_style_icons_exist(self):
        """Valida que os novos icones em alta definicao estao instalados"""
        svg_path = "/usr/share/icons/hicolor/scalable/apps/sys-device-link.svg"
        self.assertTrue(os.path.exists(svg_path))
        for size in ["512x512", "256x256", "48x48", "32x32", "16x16"]:
            png_path = f"/usr/share/icons/hicolor/{size}/apps/sys-device-link.png"
            self.assertTrue(os.path.exists(png_path))

    def test_no_emojis_in_source_files(self):
        """Garante conformidade com a diretriz de zero emojis em codigo e componentes"""
        qml_path = "/usr/lib/nectarlink/qml/pages/DownloadsPage.qml"
        with open(qml_path, "r", encoding="utf-8") as f:
            content = f.read()
        for char in content:
            code = ord(char)
            # Faixas de emojis Unicode comuns
            self.assertFalse(
                0x1F300 <= code <= 0x1F9FF or 0x2600 <= code <= 0x27BF,
                f"Emoji detectado no codigo: {char} (U+{code:04X})"
            )

if __name__ == "__main__":
    unittest.main()
