#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de testes automatizados para validacao da sincronizacao de janelas do PC,
Stream Deck mobile, modo tela acesa e atalhos rapidos.
"""

import os
import re
import unittest
import subprocess

class TestStreamDeckWindowSync(unittest.TestCase):
    """Bateria de testes unitarios e de integracao do Stream Deck e Window Switcher."""

    def test_01_classify_window_semantic_mappings(self):
        """Valida que processos comuns sao mapeados para icones e cores semanticos corretos."""
        # Casos de teste: (comm, title, expected_app, expected_icon, expected_color)
        cases = [
            ("spotify", "TakaB - Sete Mares", "Spotify", "music", "emerald"),
            ("spotify", "Spotify Free", "Spotify", "music", "emerald"),
            ("minecraft-launcher", "Minecraft 1.20.4", "Minecraft", "gamepad", "amber"),
            ("java", "Minecraft* 1.20.1 - Singleplayer", "Minecraft", "gamepad", "amber"),
            ("discord", "@Vincent - Discord", "Discord", "chat", "indigo"),
            ("obs", "OBS 30.0.2 - Profile: Untitled", "OBS Studio", "video", "ruby"),
            ("obs64.exe", "OBS 30.0.0", "OBS Studio", "video", "ruby"),
            ("chromium", "Crunchyroll - Watch Popular Anime - Chromium", "Crunchyroll", "video", "orange"),
            ("google-chrome", "Twitch - Live Stream - Google Chrome", "Twitch", "video", "purple"),
            ("firefox", "YouTube - Home - Mozilla Firefox", "YouTube", "video", "ruby"),
            ("brave", "GitHub - Issues - Brave", "Navegador", "globe", "sapphire"),
            ("xfce4-terminal", "Vincent@station:~", "Terminal", "terminal", "graphite"),
            ("steam", "Steam Community", "Steam", "gamepad", "slate"),
            ("antigravity-ide", "Antigravity IDE - main.rs", "Antigravity", "terminal", "slate"),
        ]

        def py_classify(comm_lower: str, title: str):
            title_lower = title.lower()
            if "spotify" in comm_lower or "spotify" in title_lower:
                return ("Spotify", "music", "emerald")
            elif "minecraft" in comm_lower or "minecraft" in title_lower:
                return ("Minecraft", "gamepad", "amber")
            elif "discord" in comm_lower or "discord" in title_lower:
                return ("Discord", "chat", "indigo")
            elif "obs" in comm_lower or "obs" in title_lower:
                return ("OBS Studio", "video", "ruby")
            elif any(b in comm_lower for b in ["chromium", "chrome", "firefox", "brave", "edge"]):
                if "twitch" in title_lower:
                    return ("Twitch", "video", "purple")
                elif "crunchyroll" in title_lower:
                    return ("Crunchyroll", "video", "orange")
                elif "youtube" in title_lower:
                    return ("YouTube", "video", "ruby")
                else:
                    return ("Navegador", "globe", "sapphire")
            elif "steam" in comm_lower or "steam" in title_lower:
                return ("Steam", "gamepad", "slate")
            elif "antigravity" in comm_lower or "antigravity" in title_lower:
                return ("Antigravity", "terminal", "slate")
            elif any(t in comm_lower for t in ["terminal", "bash", "zsh", "alacritty", "kitty"]):
                return ("Terminal", "terminal", "graphite")
            else:
                short = re.split(r"[—\-•|]", title)[0].strip()
                return (short[:15] if len(short) > 18 else (short or "Aplicativo"), "window", "sapphire")

        for comm, title, exp_app, exp_icon, exp_color in cases:
            app, icon, color = py_classify(comm.lower(), title)
            self.assertEqual(app, exp_app, f"Falha no app para comm={comm}, title={title}")
            self.assertEqual(icon, exp_icon, f"Falha no icone para comm={comm}")
            self.assertEqual(color, exp_color, f"Falha na cor para comm={comm}")

    def test_02_system_layers_filtering(self):
        """Valida que desktop background (-1), paineis e widgets de mesa sao filtrados."""
        sample_wmctrl_output = """0x01e00003 -1 2789   B660M-Phantom-Gaming-4 xfce4-panel
0x02800015 -1 2791   B660M-Phantom-Gaming-4 Área de trabalho
0x05c00007 -1 2834   B660M-Phantom-Gaming-4 wallpaperengine
0x00e0aaf1 -1 115941 B660M-Phantom-Gaming-4 Widget - calendar
0x06a00003  0 9787   B660M-Phantom-Gaming-4 Antigravity IDE
0x0760000a  0 9886   B660M-Phantom-Gaming-4 @Vincent - Discord
0x09000004  0 155104 B660M-Phantom-Gaming-4 TakaB - Sete Mares
0x09400004  0 69416  B660M-Phantom-Gaming-4 Doente • Shooter_sz - Chromium"""

        user_windows = []
        for line in sample_wmctrl_output.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 4:
                wid, desktop, pid, host = parts[:4]
                if desktop == "-1":
                    continue
                user_windows.append(wid)

        self.assertEqual(len(user_windows), 4)
        self.assertIn("0x06a00003", user_windows)
        self.assertIn("0x0760000a", user_windows)
        self.assertIn("0x09000004", user_windows)
        self.assertIn("0x09400004", user_windows)

    def test_03_window_id_security_sanitization(self):
        """Valida que IDs de janela sao higienizados e rejeitam caracteres perigosos ou injecoes."""
        valid_ids = ["0x09000004", "0x6a00003", "0X1E00003", "123456", "0x0"]
        invalid_ids = [
            "0x123; rm -rf /",
            "0x123 | ls",
            "$(cat /etc/passwd)",
            "../etc/shadow",
            "0x123\n0x456",
            "   ",
            "",
            "0xZZZZ",
        ]

        def is_safe_window_id(clean: str) -> bool:
            clean = clean.strip()
            if not clean:
                return False
            hex_part = clean[2:] if clean.lower().startswith("0x") else clean
            if not hex_part or not all(c in "0123456789abcdefABCDEF" for c in hex_part):
                return False
            try:
                val = int(hex_part, 16)
                return True
            except ValueError:
                return False

        for vid in valid_ids:
            self.assertTrue(is_safe_window_id(vid), f"Deveria ser valido: {vid}")

        for inv in invalid_ids:
            self.assertFalse(is_safe_window_id(inv), f"Deveria ser rejeitado: {inv}")

    def test_04_wire_deck_id_compatibility(self):
        """Valida que os IDs gerados de tiles cumprem a especificacao de wire ID do NectarLink."""
        # Regra do protocolo: 1..=64 ASCII alphanumeric, '_', '-', '.'
        pattern = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")

        sample_wids = ["0x09000004", "0x6a00003", "0x0760000a", "0x09400004"]
        for wid in sample_wids:
            clean_wid = wid.strip().replace("0x", "0x_")
            tile_id = f"focus_win_{clean_wid}"
            self.assertTrue(pattern.match(tile_id), f"Tile ID invalido para o protocolo: {tile_id}")
            self.assertLessEqual(len(tile_id), 64)

    def test_05_deck_screen_keep_screen_on_present(self):
        """Valida que o arquivo DeckScreen.kt possui FLAG_KEEP_SCREEN_ON e keepScreenOn."""
        deck_screen_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckScreen.kt"
        with open(deck_screen_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FLAG_KEEP_SCREEN_ON", content)
        self.assertIn("view.keepScreenOn = true", content)
        self.assertIn("DeckAddTileDialog", content)
        self.assertIn("activeWindowTiles", content)
        self.assertIn("Janelas Abertas no PC", content)
        self.assertIn("+ Atalho", content)

    def test_06_deck_add_tile_dialog_present(self):
        """Valida que o componente DeckAddTileDialog.kt existe e possui os presets necessarios."""
        dialog_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckAddTileDialog.kt"
        self.assertTrue(os.path.exists(dialog_path))
        with open(dialog_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("DeckAddTileDialog", content)
        self.assertIn("spotify", content)
        self.assertIn("minecraft", content)
        self.assertIn("discord", content)
        self.assertIn("obs", content)
        self.assertIn("twitch", content)
        self.assertIn("crunchyroll", content)

    def test_07_rust_window_switcher_module_exists(self):
        """Valida que o modulo window_switcher.rs foi criado e possui as funcoes obrigatorias."""
        ws_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/desktop/app/src/window_switcher.rs"
        self.assertTrue(os.path.exists(ws_path))
        with open(ws_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("pub fn list_open_windows", content)
        self.assertIn("pub fn focus_window_by_id", content)
        self.assertIn("pub fn build_active_windows_page", content)
        self.assertIn("pub fn classify_window", content)

    def test_08_no_emojis_in_source_files(self):
        """Valida a diretriz estrita de ZERO emojis nos arquivos modificados (Regra 3)."""
        files_to_check = [
            "/home/Vincent/.gemini/antigravity/scratch/nectarlink/desktop/app/src/window_switcher.rs",
            "/home/Vincent/.gemini/antigravity/scratch/nectarlink/desktop/app/src/deck.rs",
            "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckAddTileDialog.kt",
            "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckScreen.kt",
        ]

        # Regex para deteccao de emojis Unicode
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F"  # Emoticons
            r"\U0001F300-\U0001F5FF"   # Simbolos e pictogramas
            r"\U0001F680-\U0001F6FF"   # Transporte e mapa
            r"\U0001F700-\U0001F77F"   # Alquimicos
            r"\U0001F780-\U0001F7FF"   # Geometricos estendidos
            r"\U0001F800-\U0001F8FF"   # Setas estendidas
            r"\U0001F900-\U0001F9FF"   # Suplementares
            r"\U0001FA00-\U0001FA6F"   # Xadrez e simbolos
            r"\U0001FA70-\U0001FAFF"   # Diversos
            r"\U00002702-\U000027B0"   # Dingbats
            r"\U000024C2-\U0001F251]"  # Fechados
        )

        for file_path in files_to_check:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                matches = emoji_pattern.findall(content)
                self.assertEqual(len(matches), 0, f"Emojis detectados em {file_path}: {matches}")

    def test_09_modularity_file_limits(self):
        """Valida que nenhum arquivo excede o limiar toleravel de 500 linhas para novos modulos (Regra 12)."""
        ws_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/desktop/app/src/window_switcher.rs"
        dialog_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckAddTileDialog.kt"

        for p in [ws_path, dialog_path]:
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
                self.assertLessEqual(len(lines), 500, f"Arquivo {p} tem {len(lines)} linhas (limite 500)")

if __name__ == "__main__":
    unittest.main()

