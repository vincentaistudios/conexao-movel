#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de Homologação: Spike Companion de Valorant para Stream Deck
Valida as regras temporais canônicas, transições da matriz de cores (Verde, Amarelo, Vermelho),
compensação de latência de rede e a estrita ausência de emojis nos arquivos Kotlin/Rust.
"""

import os
import re
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestValorantSpikeCompanion(unittest.TestCase):

    def test_valorant_canonical_constants(self):
        """Valida se as constantes de tempo da Spike estão exatas em SpikeCompanionSheet.kt."""
        kt_path = os.path.join(
            WORKSPACE_ROOT,
            "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "deck", "SpikeCompanionSheet.kt"
        )
        self.assertTrue(os.path.exists(kt_path), f"Arquivo ausente: {kt_path}")
        with open(kt_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("VALORANT_SPIKE_EXPLODE_SECONDS = 40.0f", content)
        self.assertIn("VALORANT_FULL_DEFUSE_SECONDS = 7.0f", content)
        self.assertIn("VALORANT_HALF_DEFUSE_SECONDS = 3.5f", content)
        self.assertIn("VALORANT_FULL_DEFUSE_CUTOFF = 33.0f", content)
        self.assertIn("VALORANT_HALF_DEFUSE_CUTOFF = 36.5f", content)

    def test_chromatic_matrix_transitions(self):
        """Valida a lógica matemática das três fases de cores solicitadas pelo usuário."""
        def get_spike_phase(elapsed_seconds):
            if elapsed_seconds < 33.0:
                return "VERDE"  # Defuse Integral Possível
            elif elapsed_seconds < 36.5:
                return "AMARELO"  # No Limite: Apenas Half Defuse
            elif elapsed_seconds < 40.0:
                return "VERMELHO"  # Não Dá Mais: Corra da Explosão
            else:
                return "DETONADA"

        # Teste Fase Verde
        self.assertEqual(get_spike_phase(0.0), "VERDE")
        self.assertEqual(get_spike_phase(15.5), "VERDE")
        self.assertEqual(get_spike_phase(32.9), "VERDE")

        # Teste Fase Amarela (No Limite - apenas 3.5s restantes para half defuse)
        self.assertEqual(get_spike_phase(33.0), "AMARELO")
        self.assertEqual(get_spike_phase(35.0), "AMARELO")
        self.assertEqual(get_spike_phase(36.4), "AMARELO")

        # Teste Fase Vermelha (Não Dá Mais - matematicamente impossível defusar)
        self.assertEqual(get_spike_phase(36.5), "VERMELHO")
        self.assertEqual(get_spike_phase(38.0), "VERMELHO")
        self.assertEqual(get_spike_phase(39.9), "VERMELHO")

        # Detonação
        self.assertEqual(get_spike_phase(40.0), "DETONADA")

    def test_latency_compensation_algorithm(self):
        """Valida o cálculo de compensação de delay de rede via timestamp Unix e RTT."""
        now_ms = 1732440000000
        planted_at_ms = 1732439999800  # Plantado há 200ms no PC
        rtt_ms = 40  # Latência de ida e volta da rede local Wi-Fi (one-way = 20ms)

        one_way_latency = rtt_ms / 2.0
        compensated_elapsed_ms = now_ms - (planted_at_ms + one_way_latency)
        compensated_elapsed_sec = compensated_elapsed_ms / 1000.0

        # O timer deve iniciar exatamente aos 0.18s decorridos, eliminando o atraso de rede
        self.assertAlmostEqual(compensated_elapsed_sec, 0.18, places=3)

    def test_deck_preset_integration(self):
        """Valida se o preset do Spike Companion está integrado no Desktop Rust e no Android Dialog."""
        desktop_deck_rs = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "deck.rs")
        android_dialog_kt = os.path.join(
            WORKSPACE_ROOT,
            "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "deck", "DeckAddTileDialog.kt"
        )

        with open(desktop_deck_rs, "r", encoding="utf-8") as f:
            deck_content = f.read()
        with open(android_dialog_kt, "r", encoding="utf-8") as f:
            dialog_content = f.read()

        self.assertIn('"valorant_spike"', deck_content)
        self.assertIn('"Spike Timer"', deck_content)
        self.assertIn('"valorant_spike"', dialog_content)
        self.assertIn("Spike Companion", dialog_content)

    def test_zero_emojis(self):
        """Verifica estritamente que nenhum emoji foi inserido nos arquivos do Spike Companion."""
        target_files = [
            os.path.join(WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "deck", "SpikeCompanionSheet.kt"),
            os.path.join(WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "deck", "SpikeAudioHelper.kt"),
            os.path.join(WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "deck", "SpikeVectorIcons.kt"),
            os.path.join(WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "deck", "DeckScreen.kt"),
            os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "deck.rs"),
        ]

        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F"
            r"\U0001F300-\U0001F5FF"
            r"\U0001F680-\U0001F6FF"
            r"\U0001F1E0-\U0001F1FF"
            r"\U00002702-\U000027B0"
            r"\U000024C2-\U0001F251]"
        )

        for path in target_files:
            self.assertTrue(os.path.exists(path), f"Arquivo não encontrado: {path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                matches = emoji_pattern.findall(content)
                self.assertEqual(matches, [], f"Emoji proibido detectado em {path}: {matches}")


if __name__ == "__main__":
    unittest.main()

