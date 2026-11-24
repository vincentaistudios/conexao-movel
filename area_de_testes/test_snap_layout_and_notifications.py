#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de Homologação: Notificações Sem Flood, Printscreen e Snap Layout
Valida a lógica de filtragem de OOM/pressão de memória, detecção de resolução Ultrawide,
e mapeamento de layouts de snap window para o Conexão Móvel (NectarLink).
"""

import os
import re
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestNotificationAndSnapLayout(unittest.TestCase):

    def test_pc_notifications_blacklist(self):
        """Verifica se pc_notifications.rs bloqueia alertas internos de memoria e watchdog."""
        rs_path = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "pc_notifications.rs")
        self.assertTrue(os.path.exists(rs_path), f"Arquivo ausente: {rs_path}")
        with open(rs_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verifica presenca de palavras-chave no bloqueio de notificacoes
        self.assertIn("sys-oom", content)
        self.assertIn("memory-guard", content)
        self.assertIn("pressao critica", content)
        self.assertIn("risco critico", content)
        self.assertIn("alerta de memoria", content)

    def test_screenshot_candidates(self):
        """Verifica se shell.rs inclui scrot e xclip para captura instantanea no X11."""
        shell_path = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "linux", "shell.rs")
        self.assertTrue(os.path.exists(shell_path), f"Arquivo ausente: {shell_path}")
        with open(shell_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('"scrot"', content)
        self.assertIn('"xclip"', content)
        self.assertIn("Captura de Tela Realizada", content)

    def test_wm_class_and_title(self):
        """Verifica se app_helpers.cpp e main.rs configuram o nome e classe de janela corretamente."""
        main_rs = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "main.rs")
        cpp_helpers = os.path.join(WORKSPACE_ROOT, "desktop", "app", "cpp", "app_helpers.cpp")

        with open(main_rs, "r", encoding="utf-8") as f:
            main_content = f.read()
        with open(cpp_helpers, "r", encoding="utf-8") as f:
            cpp_content = f.read()

        self.assertIn('set_application_name(&QString::from("nectarlink"))', main_content)
        self.assertIn('setApplicationDisplayName(QString::fromUtf8("Conexão Móvel"))', cpp_content)

    def test_snap_layout_logic(self):
        """Verifica se window_switcher.rs suporta os layouts solicitados."""
        switcher_path = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "window_switcher.rs")
        with open(switcher_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("get_screen_dimensions", content)
        self.assertIn("snap_window", content)
        self.assertIn('"fullscreen"', content)
        self.assertIn('"maximize"', content)
        self.assertIn('"left"', content)
        self.assertIn('"right"', content)
        self.assertIn('"center"', content)

    def test_deck_snap_integration(self):
        """Verifica se deck.rs processa snap_win_ e focus_win_ com maximizacao."""
        deck_path = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "deck.rs")
        with open(deck_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('tile_id.strip_prefix("snap_win_")', content)
        self.assertIn('snap_window(&raw, "maximize")', content)

    def test_zero_emojis(self):
        """Garante que nenhum emoji Unicode foi adicionado nos arquivos modificados."""
        checked_files = [
            os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "deck.rs"),
            os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "window_switcher.rs"),
            os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "pc_notifications.rs"),
            os.path.join(WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "deck", "SnapLayoutDialog.kt"),
        ]
        # Regex para faixas de emojis
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F"
            r"\U0001F300-\U0001F5FF"
            r"\U0001F680-\U0001F6FF"
            r"\U0001F1E0-\U0001F1FF"
            r"\U00002702-\U000027B0"
            r"\U000024C2-\U0001F251]"
        )
        for path in checked_files:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    matches = emoji_pattern.findall(content)
                    self.assertEqual(matches, [], f"Emoji encontrado em {path}: {matches}")


if __name__ == "__main__":
    unittest.main()

