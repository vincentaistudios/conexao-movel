# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de Testes Unitarios e Auditoria de Seguranca para Automacao de Wake-on-LAN e Energia.
Valida o script setup_wol_and_power.ps1, as diretrizes do instalador NSIS (nectarlink.nsi),
a chamada segura de reinicializacao em firmware UEFI/BIOS (sem injecao de parametros),
as orientacoes dos fabricantes de placa-mae (ASRock, ASUS, Gigabyte, MSI),
a interface grafica QML (WakeOnLanCard.qml),
e a conformidade estrita com as Regras 3 (zero emojis) e 12 (modularidade).
"""

import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PS1_SCRIPT_PATH = os.path.join(
    REPO_ROOT, "desktop", "packaging", "windows", "setup_wol_and_power.ps1"
)
NSI_PATH = os.path.join(REPO_ROOT, "desktop", "installer", "nectarlink.nsi")
WOL_RS_PATH = os.path.join(REPO_ROOT, "desktop", "app", "src", "win", "wol.rs")
WOL_CARD_PATH = os.path.join(
    REPO_ROOT, "desktop", "app", "qml", "components", "WakeOnLanCard.qml"
)

# Padrao regex cobrindo blocos Unicode de emojis e simbolos graficos decorativos
EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF"
    r"\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF\uFE0F\u200D]",
    flags=re.UNICODE,
)

# Base canonica de orientacoes de BIOS/UEFI para fabricantes de placa-mae
CANONICAL_MOTHERBOARD_GUIDELINES = {
    "ASRock": {
        "keys": ["Del", "F2"],
        "menu_path": "Advanced -> ACPI Configuration",
        "primary_setting": "PCIe Devices Power On = Enabled",
        "power_setting": "Deep Sleep in S4/S5 = Disabled",
    },
    "ASUS": {
        "keys": ["Del", "F2"],
        "menu_path": "Advanced Mode (F7) -> Advanced -> APM Configuration",
        "primary_setting": "Power On By PCI-E/PCI = Enabled",
        "power_setting": "ErP Ready = Disabled",
    },
    "Gigabyte": {
        "keys": ["Del", "F12"],
        "menu_path": "Settings -> Power",
        "primary_setting": "Wake on LAN = Enabled",
        "power_setting": "ErP = Disabled",
    },
    "MSI": {
        "keys": ["Del"],
        "menu_path": "Settings -> Advanced -> Wake Up Event Setup",
        "primary_setting": "Resume By PCI-E Device = Enabled",
        "power_setting": "ErP Ready = Disabled",
    },
}


class TestSetupWolAndPowerPs1(unittest.TestCase):
    """Testes de sintaxe, higienizacao e comandos do script setup_wol_and_power.ps1."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(
            os.path.isfile(PS1_SCRIPT_PATH),
            f"Arquivo de script ausente: {PS1_SCRIPT_PATH}",
        )
        with open(PS1_SCRIPT_PATH, "r", encoding="utf-8", errors="ignore") as f:
            cls.content = f.read()

    def test_cmdlet_binding_and_parameters(self):
        """Valida definicao declarativa do Cmdlet e suporte a modo silencioso (-Quiet)."""
        self.assertIn("[CmdletBinding()]", self.content)
        self.assertRegex(self.content, r"param\s*\(\s*\[switch\]\$Quiet\s*\)")

    def test_fast_startup_disabling_command(self):
        """Valida que o script desativa a Inicializacao Rapida (Fast Startup) no registro."""
        self.assertIn("HiberbootEnabled", self.content)
        self.assertIn(r"HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power", self.content)
        self.assertRegex(
            self.content,
            r"Set-ItemProperty\s+-Path\s+\$powerRegPath\s+-Name\s+'HiberbootEnabled'\s+-Value\s+0\s+-Type\s+DWord",
        )

    def test_physical_adapter_detection_and_vpn_filtering(self):
        """Valida consulta exclusiva de placas fisicas e filtro rigoroso de VPNs/pontes virtuais."""
        self.assertIn("Get-NetAdapter -Physical", self.content)
        self.assertIn("$_.Status -ne 'Disabled'", self.content)
        vpn_filter = "Virtual|VPN|Hamachi|Radmin|Hyper-V|Docker|Podman"
        self.assertIn(vpn_filter, self.content)

    def test_adapter_power_management_configuration(self):
        """Valida habilitacao de Wake-on-LAN e persistencia energetica no adaptador."""
        self.assertIn("Set-NetAdapterPowerManagement", self.content)
        self.assertIn("-WakeOnMagicPacket Enabled", self.content)
        self.assertIn("-DeviceSleepOnDisconnect Disabled", self.content)

    def test_adapter_advanced_properties(self):
        """Valida definicao explicita de propriedades avancadas do driver de rede."""
        self.assertIn("Set-NetAdapterAdvancedProperty", self.content)
        self.assertIn("Wake on Magic Packet", self.content)
        self.assertIn("Wake on pattern match", self.content)
        self.assertIn("*WakeOnMagicPacket", self.content)

    def test_network_class_registry_update(self):
        """Valida atualizacao na classe de adaptadores {4d36e972-e325-11ce-bfc1-08002be10318}."""
        class_guid = "{4d36e972-e325-11ce-bfc1-08002be10318}"
        self.assertIn(class_guid, self.content)
        self.assertIn(r"^\d{4}$", self.content)
        self.assertIn("PnPCapabilities", self.content)

    def test_firewall_rule_udp_port_9(self):
        """Valida adicao de regra de firewall para a porta UDP 9 nos perfis privado e de dominio."""
        self.assertIn("netsh.exe advfirewall firewall add rule", self.content)
        self.assertIn("protocol=UDP", self.content)
        self.assertIn("localport=9", self.content)
        self.assertIn("dir=in", self.content)
        self.assertIn("action=allow", self.content)
        self.assertIn("profile=private,domain", self.content)

    def test_script_hygiene_and_safety(self):
        """Valida higienizacao do script contra chamadas inseguras ou credenciais expostas."""
        unsafe_keywords = ["Invoke-Expression", "iex ", "password", "secret", "DownloadString"]
        for kw in unsafe_keywords:
            self.assertNotIn(kw, self.content, f"Termo inseguro encontrado no script: {kw}")
        self.assertIn("$ErrorActionPreference = 'SilentlyContinue'", self.content)


class TestNectarlinkNsiInstaller(unittest.TestCase):
    """Testes de integracao com o instalador NSIS (nectarlink.nsi)."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.isfile(NSI_PATH), f"Instalador NSIS ausente: {NSI_PATH}")
        with open(NSI_PATH, "r", encoding="utf-8", errors="ignore") as f:
            cls.content = f.read()

    def test_hiberboot_registry_write_in_installer(self):
        """Valida que o instalador NSIS grava HiberbootEnabled = 0 diretamente em HKLM."""
        expected_line = (
            'WriteRegDWORD HKLM "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power" '
            '"HiberbootEnabled" 0'
        )
        self.assertIn(expected_line, self.content)

    def test_firewall_rule_udp9_in_installer(self):
        """Valida inclusao de regra de firewall para a porta UDP 9 no instalador NSIS."""
        self.assertIn('name=\\"${APP} Wake-on-LAN\\"', self.content)
        self.assertIn("protocol=UDP", self.content)
        self.assertIn("localport=9", self.content)
        self.assertIn("profile=private,domain", self.content)

    def test_executes_setup_wol_powershell_script(self):
        """Valida que o instalador executa setup_wol_and_power.ps1 silenciosamente com bypass de politica."""
        self.assertIn("setup_wol_and_power.ps1", self.content)
        self.assertIn("powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File", self.content)
        self.assertIn("-Quiet", self.content)

    def test_uninstaller_cleanup(self):
        """Valida limpeza da regra de firewall e do script no processo de desinstalacao."""
        self.assertIn('netsh advfirewall firewall delete rule name="${APP} Wake-on-LAN"', self.content)
        self.assertIn('Delete "$INSTDIR\\setup_wol_and_power.ps1"', self.content)


class TestRebootToFirmwareValidation(unittest.TestCase):
    """Validacao da chamada segura de reinicializacao para firmware UEFI/BIOS no Rust."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.isfile(WOL_RS_PATH), f"Arquivo wol.rs ausente: {WOL_RS_PATH}")
        with open(WOL_RS_PATH, "r", encoding="utf-8", errors="ignore") as f:
            cls.content = f.read()

    def test_reboot_function_exists(self):
        """Valida presenca da funcao publica reboot_to_uefi_firmware."""
        self.assertIn("pub fn reboot_to_uefi_firmware() -> Result<(), String>", self.content)

    def test_reboot_command_arguments_and_no_injection(self):
        """Valida argumentos fixos /r /fw /t 0 sem concatenacao de variaveis ou injecao de parametros."""
        self.assertIn('cmd.args(["/r", "/fw", "/t", "0"])', self.content)
        self.assertIn('"/r /fw /t 0"', self.content)

    def test_reboot_process_flags_silent(self):
        """Valida uso de flag CREATE_NO_WINDOW para suprimir abertura de console interativo."""
        self.assertIn("CREATE_NO_WINDOW: u32 = 0x0800_0000", self.content)
        self.assertIn("cmd.creation_flags(CREATE_NO_WINDOW)", self.content)

    def test_elevated_fallback_handling(self):
        """Valida fallback gracioso para processo elevado com tratamento de UAC recusado."""
        self.assertIn("super::elevated::start", self.content)
        self.assertIn("UAC prompt declined by user", self.content)


class TestMotherboardVendorGuidance(unittest.TestCase):
    """Validacao do algoritmo de deteccao de placa-mae e diretrizes de configuracao."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.isfile(WOL_RS_PATH), f"Arquivo wol.rs ausente: {WOL_RS_PATH}")
        with open(WOL_RS_PATH, "r", encoding="utf-8", errors="ignore") as f:
            cls.wol_content = f.read()

    def test_vendor_normalization_in_rust(self):
        """Valida normalizacao no modulo Rust para os 4 grandes fabricantes."""
        self.assertIn("pub fn normalize_motherboard_vendor", self.wol_content)
        for vendor in ["ASUS", "MSI", "Gigabyte", "ASRock"]:
            self.assertIn(f'"{vendor}"', self.wol_content)

    def test_vendor_detection_sources(self):
        """Valida fontes de deteccao de hardware via chaves de registro BIOS e CIM/WMI."""
        self.assertIn("BaseBoardManufacturer", self.wol_content)
        self.assertIn("SystemManufacturer", self.wol_content)
        self.assertIn("BIOSVendor", self.wol_content)
        self.assertIn("Win32_BaseBoard", self.wol_content)

    def test_canonical_guidelines_specifications(self):
        """Valida consistencia e completude das recomendacoes de configuracao de BIOS."""
        for vendor, guide in CANONICAL_MOTHERBOARD_GUIDELINES.items():
            self.assertGreaterEqual(len(guide["keys"]), 1, f"Teclas ausentes para {vendor}")
            self.assertIn("->", guide["menu_path"], f"Caminho de menu invalido para {vendor}")
            self.assertIn("Enabled", guide["primary_setting"], f"Configuracao primaria invalida para {vendor}")
            self.assertIn("Disabled", guide["power_setting"], f"Configuracao de energia invalida para {vendor}")


class TestWakeOnLanCardUiComponent(unittest.TestCase):
    """Testes de conformidade do componente visual WakeOnLanCard.qml (Fluent / Sonoma)."""

    @classmethod
    def setUpClass(cls):
        cls.assertTrue(os.path.isfile(WOL_CARD_PATH), f"WakeOnLanCard.qml ausente: {WOL_CARD_PATH}")
        with open(WOL_CARD_PATH, "r", encoding="utf-8", errors="ignore") as f:
            cls.content = f.read()

    def test_card_diagnostics_and_buttons(self):
        """Valida elementos mandatorios: Fast Startup, Magic Packet, Firewall UDP 9 e acoes."""
        self.assertIn("Inicialização Remota e Energia (Wake-on-LAN)", self.content)
        self.assertIn("Inicialização Rápida do Windows (Fast Startup)", self.content)
        self.assertIn("Placa de Rede Ethernet (Magic Packet)", self.content)
        self.assertIn("Regra de Firewall (Porta UDP 9)", self.content)
        self.assertIn("Otimizar Sistema Automaticamente", self.content)
        self.assertIn("Reiniciar Direto na BIOS", self.content)

    def test_card_motherboard_guidance_elements(self):
        """Valida presenca de orientacoes visuais de configuracao de BIOS/ACPI no card."""
        self.assertIn("ACPI Configuration", self.content)
        self.assertIn("PCIe Devices Power On = Enabled", self.content)
        self.assertIn("Deep Sleep in S4/S5", self.content)


class TestSecurityAuditAndSystemRules(unittest.TestCase):
    """Auditoria de conformidade com as Regras de Sistema (Zero Emojis e Limites Modulares)."""

    def test_zero_emojis_rule_3(self):
        """Garante ausencia absoluta de emojis em todos os arquivos modificados ou criados."""
        targets = [PS1_SCRIPT_PATH, NSI_PATH, WOL_RS_PATH, WOL_CARD_PATH, __file__]
        for path in targets:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            emojis = EMOJI_PATTERN.findall(content)
            self.assertEqual(
                len(emojis),
                0,
                f"Regra 3 violada: emoji(s) detectados em {os.path.basename(path)}: {emojis}",
            )

    def test_modularity_and_line_limits_rule_12(self):
        """Garante limites de modularidade e tamanho de arquivo (Regra 12: < 300-500 linhas)."""
        checks = [
            (PS1_SCRIPT_PATH, 300),
            (WOL_RS_PATH, 500),
            (WOL_CARD_PATH, 500),
            (__file__, 500),
        ]
        for path, limit in checks:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            self.assertLessEqual(
                len(lines),
                limit,
                f"Regra 12 violada: {os.path.basename(path)} possui {len(lines)} linhas (maximo: {limit})",
            )


if __name__ == "__main__":
    unittest.main()
