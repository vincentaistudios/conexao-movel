# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de Testes Unitarios e de Validacao Arquitetural para Automacao do Instalador Windows.
Valida o script setup_wol_and_power.ps1, a integracao no instalador NSIS (nectarlink.nsi),
a adicao de regras de firewall, registro e ausencia estrita de emojis.
"""

import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PS1_SCRIPT_PATH = os.path.join(
    REPO_ROOT, "desktop", "packaging", "windows", "setup_wol_and_power.ps1"
)
NSI_PATH = os.path.join(REPO_ROOT, "desktop", "installer", "nectarlink.nsi")
PACKAGE_PS1_PATH = os.path.join(REPO_ROOT, "scripts", "package.ps1")

EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]",
    flags=re.UNICODE,
)


class TestWindowsWolInstallerAutomation(unittest.TestCase):
    """Testes de conformidade e integracao para configuracao de Wake-on-LAN e energia no Windows."""

    def test_setup_wol_script_exists_and_line_count(self):
        """Valida presenca do script setup_wol_and_power.ps1 e limite modular (< 300 linhas)."""
        self.assertTrue(
            os.path.isfile(PS1_SCRIPT_PATH),
            f"Script PowerShell ausente em {PS1_SCRIPT_PATH}",
        )
        with open(PS1_SCRIPT_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertLess(
            len(lines),
            300,
            f"Script excede 300 linhas: possui {len(lines)} linhas",
        )
        self.assertGreater(
            len(lines),
            30,
            "Script setup_wol_and_power.ps1 muito curto ou incompleto",
        )

    def test_setup_wol_script_zero_emojis(self):
        """Garante ausencia total de emojis em setup_wol_and_power.ps1."""
        with open(PS1_SCRIPT_PATH, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        matches = EMOJI_PATTERN.findall(content)
        self.assertEqual(
            len(matches),
            0,
            f"Emojis detectados no script: {matches}",
        )

    def test_setup_wol_script_fast_startup_registry(self):
        """Valida que o script desativa a Inicializacao Rapida no registro."""
        with open(PS1_SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("HiberbootEnabled", content)
        self.assertIn("Session Manager\\Power", content)
        self.assertRegex(
            content,
            r"Set-ItemProperty\s+.*'HiberbootEnabled'\s+-Value\s+0",
        )

    def test_setup_wol_script_physical_adapter_filtering(self):
        """Valida deteccao e filtragem de adaptadores fisicos de rede reais."""
        with open(PS1_SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Get-NetAdapter -Physical", content)
        self.assertIn("Virtual|VPN|Hamachi|Radmin|Hyper-V|Docker|Podman", content)
        self.assertIn("Set-NetAdapterPowerManagement", content)
        self.assertIn("WakeOnMagicPacket", content)
        self.assertIn("DeviceSleepOnDisconnect", content)

    def test_setup_wol_script_advanced_properties_and_class_registry(self):
        """Valida configuracao de propriedades avancadas e chaves de registro do adaptador."""
        with open(PS1_SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Wake on Magic Packet", content)
        self.assertIn("Wake on pattern match", content)
        self.assertIn("{4d36e972-e325-11ce-bfc1-08002be10318}", content)
        self.assertIn("PnPCapabilities", content)

    def test_setup_wol_script_firewall_rule(self):
        """Valida criacao de regra no Firewall do Windows para porta UDP 9."""
        with open(PS1_SCRIPT_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("netsh.exe advfirewall firewall add rule", content)
        self.assertIn("protocol=UDP", content)
        self.assertIn("localport=9", content)
        self.assertIn("profile=private,domain", content)

    def test_nsis_installer_zero_emojis(self):
        """Garante ausencia total de emojis em nectarlink.nsi."""
        with open(NSI_PATH, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        matches = EMOJI_PATTERN.findall(content)
        self.assertEqual(
            len(matches),
            0,
            f"Emojis detectados no instalador NSIS: {matches}",
        )

    def test_nsis_installer_hiberboot_registry(self):
        """Valida que o instalador NSIS grava HiberbootEnabled = 0 em HKLM."""
        with open(NSI_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(
            'WriteRegDWORD HKLM "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power" "HiberbootEnabled" 0',
            content,
        )

    def test_nsis_installer_firewall_rule_udp9(self):
        """Valida criacao e exclusao da regra de firewall para UDP 9 no NSIS."""
        with open(NSI_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        # Instalacao
        self.assertIn(
            'netsh advfirewall firewall add rule name=\\"${APP} Wake-on-LAN\\" dir=in action=allow protocol=UDP localport=9 enable=yes profile=private,domain description=\\"Lets paired phones wake this PC over LAN.\\"',
            content,
        )
        # Desinstalacao
        self.assertIn(
            'netsh advfirewall firewall delete rule name="${APP} Wake-on-LAN"',
            content,
        )

    def test_nsis_installer_executes_setup_wol_powershell(self):
        """Valida chamada silenciosa de setup_wol_and_power.ps1 durante a instalacao."""
        with open(NSI_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("setup_wol_and_power.ps1", content)
        self.assertIn(
            'powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$INSTDIR\\setup_wol_and_power.ps1"',
            content,
        )

    def test_package_ps1_copies_wol_script(self):
        """Valida que scripts/package.ps1 inclui setup_wol_and_power.ps1 no stage de empacotamento."""
        with open(PACKAGE_PS1_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("setup_wol_and_power.ps1", content)
        self.assertIn("Copy-Item $wolScript $stage", content)


if __name__ == "__main__":
    unittest.main()
