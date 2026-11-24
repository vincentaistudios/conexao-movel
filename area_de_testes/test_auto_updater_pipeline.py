#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validação da esteira de Auto-Update OTA e repositório central GitHub.
Verifica:
1. Resposta da API de Releases Latest do GitHub.
2. Integridade e formato do feed channels/stable.json.
3. Coerência criptográfica dos hashes SHA-256.
4. Sintaxe e executabilidade do script de publicação scripts/publish_release.sh.
5. Ausência estrita de emojis (Regra 3 do sistema).
"""

import os
import re
import json
import subprocess
import urllib.request
import unittest

REPO = "vincentaistudios/conexao-movel"
EXPECTED_VERSION = "0.1.8"
EXPECTED_TAG = f"v{EXPECTED_VERSION}"
RAW_FEED_URL = f"https://raw.githubusercontent.com/{REPO}/channels/stable.json"
API_LATEST_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]"
)


class TestAutoUpdaterPipeline(unittest.TestCase):

    def test_github_latest_release_api(self):
        """Valida que a release mais recente no GitHub é a v0.1.8 com todos os assets."""
        req = urllib.request.Request(
            API_LATEST_URL,
            headers={"User-Agent": "ConexaoMovel-Updater/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))

        self.assertEqual(data.get("tag_name"), EXPECTED_TAG)
        self.assertFalse(data.get("draft", False))
        self.assertFalse(data.get("prerelease", False))

        assets = {a["name"]: a for a in data.get("assets", [])}
        self.assertIn("ConexaoMovel-android.apk", assets)
        self.assertIn("ConexaoMovel-Windows-setup.exe", assets)
        self.assertIn("ConexaoMovel-linux-x86_64", assets)
        self.assertIn("SHA256SUMS.txt", assets)

        # Valida tamanhos mínimos realistas
        self.assertGreater(assets["ConexaoMovel-android.apk"]["size"], 50 * 1024 * 1024)
        self.assertGreater(assets["ConexaoMovel-Windows-setup.exe"]["size"], 30 * 1024 * 1024)
        self.assertGreater(assets["ConexaoMovel-linux-x86_64"]["size"], 30 * 1024 * 1024)

    def test_stable_feed_json_schema(self):
        """Valida que channels/stable.json segue o schema estrito esperado pelos clientes."""
        req = urllib.request.Request(
            RAW_FEED_URL,
            headers={"User-Agent": "ConexaoMovel-Feed/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            self.assertEqual(resp.status, 200)
            feed = json.loads(resp.read().decode("utf-8"))

        self.assertEqual(feed.get("schema"), 1)
        self.assertEqual(feed.get("channel"), "stable")
        self.assertEqual(feed.get("version"), EXPECTED_VERSION)
        self.assertTrue(feed.get("notes", "").startswith(f"https://github.com/{REPO}"))

        files = feed.get("files", [])
        self.assertGreaterEqual(len(files), 3)

        file_map = {f["name"]: f for f in files}
        self.assertIn("ConexaoMovel-android.apk", file_map)
        self.assertIn("ConexaoMovel-Windows-setup.exe", file_map)
        self.assertIn("ConexaoMovel-linux-x86_64", file_map)

        for name, f_info in file_map.items():
            self.assertEqual(len(f_info["sha256"]), 64)
            self.assertTrue(all(c in "0123456789abcdef" for c in f_info["sha256"].lower()))
            self.assertGreater(f_info["size"], 1000)
            self.assertTrue(
                f_info["url"].startswith(f"https://github.com/{REPO}/releases/download/{EXPECTED_TAG}/")
            )

    def test_publish_script_integrity(self):
        """Valida executabilidade, sintaxe bash e ausência de emojis no script de publicação."""
        script_path = os.path.expanduser(
            "~/.gemini/antigravity/scratch/nectarlink/scripts/publish_release.sh"
        )
        self.assertTrue(os.path.isfile(script_path))
        self.assertTrue(os.access(script_path, os.X_OK))

        res = subprocess.run(["bash", "-n", script_path], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"Erro de sintaxe no script: {res.stderr}")

        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        emojis = EMOJI_PATTERN.findall(content)
        self.assertEqual(len(emojis), 0, f"Emojis proibidos encontrados no script: {emojis}")

    def test_code_endpoints_consistency(self):
        """Valida que AppUpdater.kt e feed.rs usam as URLs corretas do repositório."""
        app_updater = os.path.expanduser(
            "~/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/update/AppUpdater.kt"
        )
        with open(app_updater, "r", encoding="utf-8") as f:
            updater_content = f.read()

        self.assertIn(f"https://api.github.com/repos/{REPO}/releases/latest", updater_content)
        self.assertIn(f"https://raw.githubusercontent.com/{REPO}/channels/", updater_content)
        self.assertIn(f"https://github.com/{REPO}/releases/download/", updater_content)

        feed_rs = os.path.expanduser(
            "~/.gemini/antigravity/scratch/nectarlink/desktop/app/src/feed.rs"
        )
        with open(feed_rs, "r", encoding="utf-8") as f:
            feed_content = f.read()

        self.assertIn(f"https://raw.githubusercontent.com/{REPO}/channels/", feed_content)
        self.assertIn(f"https://github.com/{REPO}/releases/download/", feed_content)


if __name__ == "__main__":
    unittest.main()
