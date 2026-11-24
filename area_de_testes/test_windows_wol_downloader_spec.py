# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de Testes Unitarios e de Integracao Arquitetural para o Windows Downloader e Wake-on-LAN.
Valida esquema do manifesto de empacotamento, integridade das diretrizes de registro,
ausencia de emojis e conformidade com limites modulares.
"""

import json
import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANIFEST_PATH = os.path.join(
    REPO_ROOT, "desktop", "packaging", "windows", "downloader_manifest.json"
)
SPEC_PATH = os.path.join(
    REPO_ROOT, "desktop", "docs", "WINDOWS_WOL_DOWNLOADER_SPEC.md"
)

EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF"
    r"\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF\uFE0F\u200D]"
)


class TestWindowsWolDownloaderSpec(unittest.TestCase):
    """Testes de conformidade arquitetural do manifesto e da documentacao de especificacao."""

    def test_manifest_file_exists_and_valid_json(self):
        """Valida que o arquivo downloader_manifest.json existe e possui JSON valido."""
        self.assertTrue(os.path.isfile(MANIFEST_PATH), f"Manifesto ausente: {MANIFEST_PATH}")
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("manifest_version"), "1.0.0")
        self.assertEqual(data.get("target_os"), "windows-x64")

    def test_service_configuration_and_zero_trust(self):
        """Valida que o servico opera na porta 28795 com politica Zero-Trust em loopback."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        service = data.get("service", {})
        self.assertEqual(service.get("host"), "127.0.0.1")
        self.assertEqual(service.get("port"), 28795)
        self.assertEqual(service.get("protocol"), "http")

        zero_trust = service.get("zero_trust", {})
        self.assertTrue(zero_trust.get("bind_address_only_loopback"))
        self.assertTrue(zero_trust.get("reject_external_origins"))
        allowed = zero_trust.get("allowed_origins", [])
        self.assertIn("http://127.0.0.1", allowed)
        self.assertIn("http://localhost", allowed)

    def test_components_contain_scripts_and_binaries(self):
        """Valida a especificacao de scripts Python e binarios essenciais de extracao."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        components = data.get("components", {})

        # Scripts
        scripts = {s["filename"]: s for s in components.get("scripts", [])}
        self.assertIn("downloader_server.py", scripts)
        self.assertIn("downloader_service.py", scripts)
        self.assertIn("google_bridge_routes.py", scripts)

        # Binarios
        binaries = {b["filename"]: b for b in components.get("binaries", [])}
        self.assertIn("yt-dlp.exe", binaries)
        self.assertIn("ffmpeg.exe", binaries)
        self.assertIn("ffprobe.exe", binaries)

    def test_fast_startup_and_wol_registry_rules(self):
        """Valida que o manifesto descreve a desativacao do Fast Startup e ativacao de WOL."""
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        sys_cfg = data.get("system_configuration", {})

        # Fast Startup
        fs = sys_cfg.get("fast_startup", {})
        self.assertEqual(fs.get("action"), "disable")
        self.assertEqual(fs.get("cli_command"), "powercfg.exe -h off")
        reg_fs = fs.get("registry", {})
        self.assertEqual(reg_fs.get("value_name"), "HiberbootEnabled")
        self.assertEqual(reg_fs.get("target_value"), 0)

        # Wake on LAN
        wol = sys_cfg.get("wake_on_lan", {})
        self.assertEqual(wol.get("action"), "enable")
        reg_keys = {k["name"]: k for k in wol.get("registry_keys", [])}
        self.assertIn("*WakeOnMagicPacket", reg_keys)
        self.assertEqual(reg_keys["*WakeOnMagicPacket"]["value"], "1")
        self.assertIn("PnPCapabilities", reg_keys)
        self.assertEqual(reg_keys["PnPCapabilities"]["operation"], "clear_bit_0x10")

    def test_spec_markdown_document_contents(self):
        """Valida que o documento WINDOWS_WOL_DOWNLOADER_SPEC.md possui todas as secoes requeridas."""
        self.assertTrue(os.path.isfile(SPEC_PATH), f"Documento de especificacao ausente: {SPEC_PATH}")
        with open(SPEC_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        required_keywords = [
            "nectarlink-desktop.exe",
            "downloader_server.py",
            "downloader_service.py",
            "28795",
            "yt-dlp.exe",
            "ffmpeg.exe",
            "powercfg.exe -h off",
            "HiberbootEnabled",
            "WakeOnMagicPacket",
            "PnPCapabilities",
            "4d36e972-e325-11ce-bfc1-08002be10318",
            "Zero-Trust",
        ]
        for kw in required_keywords:
            self.assertIn(kw, content, f"Termo mandatorio ausente na especificacao: {kw}")

    def test_files_under_500_lines_and_zero_emojis(self):
        """Valida conformidade modular (limite estrito de 500 linhas) e zero emojis."""
        for path in [MANIFEST_PATH, SPEC_PATH]:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.splitlines()
            self.assertLess(
                len(lines),
                500,
                f"Arquivo {os.path.basename(path)} excedeu 500 linhas ({len(lines)} linhas)",
            )
            emojis = EMOJI_PATTERN.findall(content)
            self.assertEqual(
                emojis,
                [],
                f"Emojis detectados em {os.path.basename(path)}: {emojis}",
            )


if __name__ == "__main__":
    unittest.main()
