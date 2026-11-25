#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Validacao da suite de redesign do Stream Deck, layout do mockup SVG,
remocao do botao no topo e inclusao do atalho Valorant na grade.
"""

import os
import re
import unittest

class TestStreamDeckRedesign(unittest.TestCase):
    """Testes de integridade do redesign do Stream Deck."""

    def test_01_deck_screen_no_spike_hud_button_in_header(self):
        """Garante que o botao vermelho 'Spike HUD' nao existe no cabecalho de DeckScreen.kt."""
        deck_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckScreen.kt"
        with open(deck_path, "r", encoding="utf-8") as f:
            content = f.read()

        # O cabecalho nao deve conter mais o FilledTonalButton isolado com 'Spike HUD'
        self.assertNotIn("Spike HUD", content)

    def test_02_deck_screen_has_valorant_tile_in_defaults(self):
        """Garante que o atalho 'Valorant' esta integrado na grade padrao de atalhos."""
        deck_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckScreen.kt"
        with open(deck_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('DeckTile("valorant_spike"', content)
        self.assertIn('"Valorant" -> R.string.deck_default_valorant', content)

    def test_03_deck_add_tile_dialog_has_valorant_preset(self):
        """Garante que o preset no dialogo de atalhos se chama 'Valorant'."""
        dialog_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckAddTileDialog.kt"
        with open(dialog_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('DeckPresetItem("valorant_spike", "Valorant"', content)

    def test_04_desktop_rust_deck_preset_named_valorant(self):
        """Garante que o preset no deck.rs do Rust Desktop esta com label 'Valorant'."""
        rust_deck_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/desktop/app/src/deck.rs"
        with open(rust_deck_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('("Valorant", "gamepad", "ruby"', content)

    def test_05_mockup_svg_dimensions_and_no_overflow(self):
        """Garante que o mockup SVG possui largura expandida e textos contidos."""
        svg_path = "/home/Vincent/.gemini/antigravity/scratch/nectarlink/docs/assets/mockup-stream-deck.svg"
        with open(svg_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Painel direito deve ter 450px de largura
        self.assertIn('width="450"', content)
        # Tecla na grade deve ser VALORANT e nao SPIKE HUD
        self.assertIn('VALORANT', content)
        self.assertNotIn('SPIKE HUD', content)
        # Borda e margens de seguranca
        self.assertIn('width="402"', content)

    def test_06_zero_emojis_in_redesign_assets(self):
        """Garante estrita adesao a diretriz de ZERO emojis (Regra 3)."""
        files = [
            "/home/Vincent/.gemini/antigravity/scratch/nectarlink/docs/assets/mockup-stream-deck.svg",
            "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckScreen.kt",
            "/home/Vincent/.gemini/antigravity/scratch/nectarlink/android/app/src/main/kotlin/app/nectarlink/android/ui/deck/DeckAddTileDialog.kt",
            "/home/Vincent/.gemini/antigravity/scratch/nectarlink/desktop/app/src/deck.rs",
        ]
        emoji_pattern = re.compile(r"[\U0001F600-\U0001FAFF\U00002702-\U000027B0]")
        for file_path in files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                matches = emoji_pattern.findall(content)
                self.assertEqual(len(matches), 0, f"Emoji detectado em {file_path}: {matches}")

if __name__ == "__main__":
    unittest.main()

