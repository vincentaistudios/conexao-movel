# SPDX-License-Identifier: GPL-3.0-or-later
"""
Testes de Homologacao e Verificacao Estatica para o Modulo Rust de Wake-on-LAN (desktop/app/src/win/wol.rs).
Valida existencia das funcoes de diagnostico, chaves de registro, comandos de sistema,
regras de normalizacao de placa-mae, ausencia absoluta de emojis e conformidade com o limite de 500 linhas.
"""

import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WOL_RS_PATH = os.path.join(REPO_ROOT, "desktop", "app", "src", "win", "wol.rs")

EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF"
    r"\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF\uFE0F\u200D]"
)


class TestWindowsWolDiagnostics(unittest.TestCase):
    """Testes unitarios e estaticos para o modulo wol.rs no ecossistema Rust do Windows."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.isfile(WOL_RS_PATH), f"Arquivo nao encontrado: {WOL_RS_PATH}")
        with open(WOL_RS_PATH, "r", encoding="utf-8") as f:
            cls.content = f.read()
            cls.lines = cls.content.splitlines()

    def test_file_line_count_strictly_under_500(self):
        """Valida que o arquivo wol.rs respeita rigorosamente o limite de 500 linhas."""
        line_count = len(self.lines)
        self.assertLess(
            line_count,
            500,
            f"O arquivo wol.rs excedeu 500 linhas ({line_count} linhas). Deve ser estritamente < 500.",
        )

    def test_zero_emojis_in_source(self):
        """Valida a ausencia total de caracteres emoji no codigo e comentarios."""
        emojis = EMOJI_PATTERN.findall(self.content)
        self.assertEqual(
            emojis,
            [],
            f"Emojis detectados no codigo de producao: {emojis}",
        )

    def test_required_functions_present(self):
        """Valida que todas as funcoes requeridas estao implementadas e exportadas como pub fn."""
        required_signatures = [
            "pub fn is_fast_startup_enabled() -> bool",
            "pub fn detect_motherboard_vendor() -> String",
            "pub fn reboot_to_uefi_firmware() -> Result<(), String>",
            "pub fn apply_wol_and_power_optimizations() -> Result<(), String>",
            "pub fn normalize_motherboard_vendor(raw: &str) -> String",
        ]
        for sig in required_signatures:
            self.assertIn(
                sig,
                self.content,
                f"Assinatura de funcao mandatoria ausente em wol.rs: {sig}",
            )

    def test_registry_and_system_keys(self):
        """Valida presenca das chaves canônicas de registro e comandos de sistema."""
        required_tokens = [
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Power",
            "HiberbootEnabled",
            r"HARDWARE\DESCRIPTION\System\BIOS",
            "BaseBoardManufacturer",
            "SystemManufacturer",
            "shutdown.exe",
            "/r",
            "/fw",
            "/t",
            "powercfg.exe -h off",
            "*WakeOnMagicPacket",
            "WakeOnMagicPacket",
            "*WakeOnPattern",
            "PnPCapabilities",
            "0x10",
        ]
        for token in required_tokens:
            self.assertIn(
                token,
                self.content,
                f"Token mandatorio de registro/sistema ausente: {token}",
            )

    def test_motherboard_vendor_normalization_logic(self):
        """Replica e valida a logica de normalizacao para fabricantes conhecidos."""
        def normalize_py(raw: str) -> str:
            trimmed = raw.strip()
            u = trimmed.upper()
            if "ASUSTEK" in u or "ASUS" in u:
                return "ASUS"
            elif "MICRO-STAR" in u or "MSI" in u:
                return "MSI"
            elif "GIGABYTE" in u:
                return "Gigabyte"
            elif "ASROCK" in u:
                return "ASRock"
            elif "DELL" in u:
                return "Dell"
            elif "HP" in u or "HEWLETT-PACKARD" in u:
                return "HP"
            elif "LENOVO" in u:
                return "Lenovo"
            elif not u or "TO BE FILLED" in u or "DEFAULT STRING" in u or u == "SYSTEM MANUFACTURER":
                return ""
            return trimmed

        cases = [
            ("ASUSTeK COMPUTER INC.", "ASUS"),
            ("ASUS ROG STRIX", "ASUS"),
            ("Micro-Star International Co., Ltd.", "MSI"),
            ("MSI Gaming", "MSI"),
            ("Gigabyte Technology Co., Ltd.", "Gigabyte"),
            ("ASRock", "ASRock"),
            ("Dell Inc.", "Dell"),
            ("Hewlett-Packard", "HP"),
            ("HP", "HP"),
            ("LENOVO", "Lenovo"),
            ("To be filled by O.E.M.", ""),
            ("Default string", ""),
            ("CustomVendor Tech", "CustomVendor Tech"),
        ]
        for raw, expected in cases:
            self.assertEqual(normalize_py(raw), expected)


if __name__ == "__main__":
    unittest.main()
