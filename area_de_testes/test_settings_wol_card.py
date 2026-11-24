#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de Testes Unitarios e de Integracao: Card de Diagnostico e Reparo Wake-on-LAN (QML / Desktop UX).
Valida a integracao na tela de configuracoes (SettingsPage.qml), o componente modular WakeOnLanCard.qml,
a presenca do dialogo modal de confirmacao de BIOS, zero emojis Unicode e diretrizes visuais Fluent/Sonoma.
"""

import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WOL_CARD_PATH = os.path.join(
    REPO_ROOT, "desktop", "app", "qml", "components", "WakeOnLanCard.qml"
)
SETTINGS_PAGE_PATH = os.path.join(
    REPO_ROOT, "desktop", "app", "qml", "pages", "SettingsPage.qml"
)
BUILD_RS_PATH = os.path.join(
    REPO_ROOT, "desktop", "app", "build.rs"
)

EMOJI_REGEX = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF"
    r"\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF\uFE0F\u200D]"
)


class TestSettingsWolCard(unittest.TestCase):
    """Testes de conformidade arquitetural e de UX para o Wake-on-LAN no desktop."""

    @classmethod
    def setUpClass(cls):
        with open(WOL_CARD_PATH, "r", encoding="utf-8") as f:
            cls.wol_card_content = f.read()
        with open(SETTINGS_PAGE_PATH, "r", encoding="utf-8") as f:
            cls.settings_page_content = f.read()
        with open(BUILD_RS_PATH, "r", encoding="utf-8") as f:
            cls.build_rs_content = f.read()

    def test_files_exist(self):
        """Valida que todos os arquivos do card e da pagina existem."""
        self.assertTrue(os.path.isfile(WOL_CARD_PATH), f"WakeOnLanCard.qml ausente em: {WOL_CARD_PATH}")
        self.assertTrue(os.path.isfile(SETTINGS_PAGE_PATH), f"SettingsPage.qml ausente em: {SETTINGS_PAGE_PATH}")
        self.assertTrue(os.path.isfile(BUILD_RS_PATH), f"build.rs ausente em: {BUILD_RS_PATH}")

    def test_zero_emojis_in_qml_files(self):
        """Garante ausencia absoluta de emojis Unicode em WakeOnLanCard.qml e SettingsPage.qml."""
        card_matches = EMOJI_REGEX.findall(self.wol_card_content)
        self.assertEqual(card_matches, [], f"Emojis encontrados em WakeOnLanCard.qml: {card_matches}")

        settings_matches = EMOJI_REGEX.findall(self.settings_page_content)
        self.assertEqual(settings_matches, [], f"Emojis encontrados em SettingsPage.qml: {settings_matches}")

    def test_registered_in_build_rs(self):
        """Valida que WakeOnLanCard.qml esta devidamente registrado no QML_FILES do build.rs."""
        self.assertIn("qml/components/WakeOnLanCard.qml", self.build_rs_content)

    def test_wol_card_title_and_grouping(self):
        """Valida o titulo do grupo elegante: 'Inicializacao Remota e Energia (Wake-on-LAN)'."""
        self.assertIn("Inicialização Remota e Energia (Wake-on-LAN)", self.wol_card_content)

    def test_three_status_diagnostics_present(self):
        """Valida a presenca dos 3 status de diagnostico: Fast Startup, Ethernet Magic Packet e Firewall UDP 9."""
        # 1. Fast Startup
        self.assertIn("Inicialização Rápida do Windows (Fast Startup)", self.wol_card_content)
        self.assertIn("Desativada (Otimizada)", self.wol_card_content)
        self.assertIn("Ativada (Pendente)", self.wol_card_content)

        # 2. Ethernet Magic Packet
        self.assertIn("Placa de Rede Ethernet (Magic Packet)", self.wol_card_content)
        self.assertIn("Habilitada (Pronta)", self.wol_card_content)

        # 3. Firewall UDP 9
        self.assertIn("Regra de Firewall (Porta UDP 9)", self.wol_card_content)
        self.assertIn("Liberada (Pronta)", self.wol_card_content)

    def test_primary_action_button_present(self):
        """Valida o botao primario destacado [ Otimizar Sistema Automaticamente ]."""
        self.assertIn("Otimizar Sistema Automaticamente", self.wol_card_content)
        self.assertIn('variant: "fill"', self.wol_card_content)

    def test_convenience_bios_reboot_button(self):
        """Valida o botao de conveniencia [ Reiniciar Direto na BIOS ]."""
        self.assertIn("Reiniciar Direto na BIOS", self.wol_card_content)
        self.assertIn("requestBiosReboot", self.wol_card_content)

    def test_motherboard_guide_and_breadcrumbs(self):
        """Valida a indicacao visual da placa-mae ASRock e a sequencia de navegacao na BIOS."""
        self.assertIn("ASRock", self.wol_card_content)
        self.assertIn("B660M Phantom Gaming 4", self.wol_card_content)
        self.assertIn("Del ou F2 ao ligar", self.wol_card_content)
        self.assertIn("F6 Modo Avançado", self.wol_card_content)
        self.assertIn("Advanced", self.wol_card_content)
        self.assertIn("ACPI Configuration", self.wol_card_content)
        self.assertIn("PCIe Devices Power On = Enabled", self.wol_card_content)
        self.assertIn("Deep Sleep in S4/S5", self.wol_card_content)

    def test_settings_page_integration(self):
        """Valida a integracao do WakeOnLanCard e do dialogo modal na SettingsPage.qml."""
        self.assertIn("WakeOnLanCard", self.settings_page_content)
        self.assertIn("biosRebootSheet", self.settings_page_content)

    def test_bios_modal_dialog_message(self):
        """Valida o dialogo modal de confirmacao e a mensagem solicitada."""
        expected_msg = (
            "O computador sera reiniciado e abrira diretamente a tela da BIOS. "
            "Na BIOS, verifique se a opcao PCIe Devices Power On (ou Wake on LAN) esta definida como Enabled."
        )
        # Normaliza espacos e quebras de linha para comparacao robusta
        norm_settings = " ".join(self.settings_page_content.split())
        norm_expected = " ".join(expected_msg.split())
        self.assertIn(norm_expected, norm_settings)

    def test_modular_size_limits(self):
        """Valida conformidade com a Regra 12 de modularidade (WakeOnLanCard < 500 linhas)."""
        lines = self.wol_card_content.splitlines()
        self.assertLess(len(lines), 500, f"WakeOnLanCard.qml excede 500 linhas: {len(lines)}")


if __name__ == "__main__":
    unittest.main()
