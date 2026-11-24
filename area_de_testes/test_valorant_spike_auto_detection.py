#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Suite de Homologação: Detecção 100% Automática da Spike do Valorant
Valida o classificador cromático (#FF4655), máquina de estados de debounce anti-ruído,
integração com o Spike Watcher do Desktop Rust, receptores reativos no Android Kotlin
e conformidade com a política estrita de Zero Emojis (Regra 3 do sistema).
"""

import os
import re
import time
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def classify_pixel_is_spike_red(r: int, g: int, b: int) -> bool:
    """Implementação espelho do algoritmo Rust classify_pixel_is_spike_red."""
    return (
        r > 190
        and g < 115
        and b < 135
        and (r - g) > 90
        and (r - b) > 75
    )


def is_spike_hud_active(pixels: list) -> bool:
    """Implementação espelho do algoritmo Rust is_spike_hud_active."""
    if not pixels:
        return False
    positives = sum(1 for (r, g, b) in pixels if classify_pixel_is_spike_red(r, g, b))
    ratio = positives / len(pixels)
    return ratio >= 0.12


class PythonSpikeStateMachine:
    """Implementação espelho da máquina de estados SpikeStateMachine em Rust."""

    def __init__(self):
        self.status = "Idle"
        self.consecutive_positives = 0
        self.consecutive_negatives = 0
        self.planted_timestamp = None

    def update(self, is_positive: bool, now_sec: float = None):
        if now_sec is None:
            now_sec = time.time()

        if self.status == "Idle":
            if is_positive:
                self.consecutive_positives += 1
                if self.consecutive_positives >= 2:
                    self.status = "Planted"
                    self.planted_timestamp = now_sec
                    self.consecutive_positives = 0
                    self.consecutive_negatives = 0
                    return "planted"
            else:
                self.consecutive_positives = 0
            return None

        elif self.status == "Planted":
            elapsed = now_sec - (self.planted_timestamp or now_sec)
            if elapsed > 45.0:
                self.status = "Idle"
                self.consecutive_negatives = 0
                self.planted_timestamp = None
                return "reset"

            if not is_positive:
                self.consecutive_negatives += 1
                if self.consecutive_negatives >= 8:
                    self.status = "Idle"
                    self.consecutive_negatives = 0
                    self.planted_timestamp = None
                    return "reset"
            else:
                self.consecutive_negatives = 0
            return None


class TestValorantSpikeAutoDetection(unittest.TestCase):

    def test_spike_color_classifier_rgb(self):
        """Valida que o classificador cromático identifica o vermelho Spike e rejeita ruídos."""
        # Cor canônica da Spike do Valorant (#FF4655) -> RGB (255, 70, 85)
        self.assertTrue(classify_pixel_is_spike_red(255, 70, 85))

        # Variações sutis com antialiasing ou iluminação de jogo
        self.assertTrue(classify_pixel_is_spike_red(240, 80, 95))
        self.assertTrue(classify_pixel_is_spike_red(220, 60, 75))

        # Cores que NÃO devem ser classificadas como Spike
        self.assertFalse(classify_pixel_is_spike_red(255, 255, 255))  # Branco puro
        self.assertFalse(classify_pixel_is_spike_red(0, 0, 0))        # Preto
        self.assertFalse(classify_pixel_is_spike_red(70, 180, 255))   # Azul HUD defensores
        self.assertFalse(classify_pixel_is_spike_red(50, 220, 100))   # Verde HUD atacantes
        self.assertFalse(classify_pixel_is_spike_red(200, 190, 50))   # Amarelo
        self.assertFalse(classify_pixel_is_spike_red(120, 120, 120))  # Cinza metálico

    def test_hud_density_ratio(self):
        """Valida se o cálculo de densidade da matriz 16x16 (256 pixels) funciona corretamente."""
        empty_matrix = [(30, 30, 30)] * 256
        self.assertFalse(is_spike_hud_active(empty_matrix))

        # 10 pixels positivos de 256 (~3.9% de densidade) -> Ruído de tiro ou partícula
        noisy_matrix = [(30, 30, 30)] * 246 + [(255, 70, 85)] * 10
        self.assertFalse(is_spike_hud_active(noisy_matrix))

        # 35 pixels positivos de 256 (~13.6% de densidade >= 12%) -> Spike ativa no HUD
        active_matrix = [(30, 30, 30)] * 221 + [(255, 70, 85)] * 35
        self.assertTrue(is_spike_hud_active(active_matrix))

    def test_state_machine_debounce_planted(self):
        """Valida que são necessários 2 frames consecutivos positivos para acionar 'planted'."""
        sm = PythonSpikeStateMachine()

        # 1 frame positivo (ex: tiro vermelho ou flash) NÃO deve disparar
        self.assertIsNone(sm.update(is_positive=True, now_sec=100.0))
        self.assertEqual(sm.status, "Idle")

        # Frame seguinte negativo reseta a contagem
        self.assertIsNone(sm.update(is_positive=False, now_sec=100.08))
        self.assertEqual(sm.status, "Idle")

        # Agora 2 frames consecutivos positivos disparam "planted"
        self.assertIsNone(sm.update(is_positive=True, now_sec=100.16))
        action = sm.update(is_positive=True, now_sec=100.24)
        self.assertEqual(action, "planted")
        self.assertEqual(sm.status, "Planted")

    def test_state_machine_debounce_reset(self):
        """Valida que o encerramento da Spike requer 8 frames negativos consecutivos."""
        sm = PythonSpikeStateMachine()
        # Força status inicial como Planted
        sm.status = "Planted"
        sm.planted_timestamp = 100.0

        # 7 frames sem detecção não devem resetar
        for i in range(1, 8):
            self.assertIsNone(sm.update(is_positive=False, now_sec=100.0 + (i * 0.08)))
            self.assertEqual(sm.status, "Planted")

        # O 8º frame negativo consecutivo confirma que a Spike foi desarmada ou explodiu
        action = sm.update(is_positive=False, now_sec=100.0 + (8 * 0.08))
        self.assertEqual(action, "reset")
        self.assertEqual(sm.status, "Idle")

    def test_state_machine_timeout(self):
        """Valida que após 45 segundos decorridos ocorre timeout automático de segurança."""
        sm = PythonSpikeStateMachine()
        sm.status = "Planted"
        sm.planted_timestamp = 100.0

        # Mesmo com frames positivos residuais, após 45.1s reseta a máquina
        action = sm.update(is_positive=True, now_sec=145.1)
        self.assertEqual(action, "reset")
        self.assertEqual(sm.status, "Idle")

    def test_rust_spike_watcher_source_integrity(self):
        """Valida a presença dos arquivos e métodos críticos no Desktop Rust."""
        watcher_path = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "spike_watcher.rs")
        settings_path = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "settings.rs")
        pc_notif_path = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "pc_notifications.rs")
        deck_path = os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "deck.rs")

        self.assertTrue(os.path.exists(watcher_path), f"Arquivo não encontrado: {watcher_path}")

        with open(watcher_path, "r", encoding="utf-8") as f:
            watcher_content = f.read()
        with open(settings_path, "r", encoding="utf-8") as f:
            settings_content = f.read()
        with open(pc_notif_path, "r", encoding="utf-8") as f:
            pc_notif_content = f.read()
        with open(deck_path, "r", encoding="utf-8") as f:
            deck_content = f.read()

        # Checagens do Watcher
        self.assertIn("classify_pixel_is_spike_red", watcher_content)
        self.assertIn("is_spike_hud_active", watcher_content)
        self.assertIn("SpikeStateMachine", watcher_content)
        self.assertIn("start_watcher", watcher_content)

        # Checagens de Settings
        self.assertIn("valorant_spike_auto_detect", settings_content)
        self.assertIn("pub fn valorant_spike_auto_detect", settings_content)

        # Checagens de pc_notifications e deck
        self.assertIn("pub fn forward_to_phones_force", pc_notif_content)
        self.assertIn("forward_to_phones_force", deck_content)

    def test_android_kotlin_auto_listener_integrity(self):
        """Valida a presença dos receptores reativos no ecossistema Android Kotlin."""
        core_path = os.path.join(
            WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "core", "Core.kt"
        )
        deck_screen_path = os.path.join(
            WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "deck", "DeckScreen.kt"
        )
        main_activity_path = os.path.join(
            WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "MainActivity.kt"
        )

        with open(core_path, "r", encoding="utf-8") as f:
            core_content = f.read()
        with open(deck_screen_path, "r", encoding="utf-8") as f:
            deck_content = f.read()
        with open(main_activity_path, "r", encoding="utf-8") as f:
            main_content = f.read()

        # Core.kt
        self.assertIn("spikeAutoEvents", core_content)
        self.assertIn("SpikeAutoEvent", core_content)
        self.assertIn("spike:planted", core_content)
        self.assertIn("spike:defused", core_content)
        self.assertIn("spike:reset", core_content)

        # DeckScreen.kt
        self.assertIn("core.spikeAutoEvents.collect", deck_content)
        self.assertIn("SpikeAutoEvent.Planted", deck_content)

        # MainActivity.kt
        self.assertIn("core.spikeAutoEvents.collect", main_content)
        self.assertIn("FLAG_KEEP_SCREEN_ON", main_content)

    def test_zero_emojis_strict(self):
        """Garante que nenhum emoji foi inserido nos arquivos do sistema (Regra 3 mandatória)."""
        files_to_check = [
            os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "spike_watcher.rs"),
            os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "deck.rs"),
            os.path.join(WORKSPACE_ROOT, "desktop", "app", "src", "settings.rs"),
            os.path.join(WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "core", "Core.kt"),
            os.path.join(WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "deck", "DeckScreen.kt"),
            os.path.join(WORKSPACE_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android", "ui", "MainActivity.kt"),
        ]

        # Regex para faixas Unicode de emojis
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F]|"  # Emoticons
            r"[\U0001F300-\U0001F5FF]|"  # Símbolos e Pictogramas
            r"[\U0001F680-\U0001F6FF]|"  # Transporte e Mapas
            r"[\U0001F700-\U0001F77F]|"  # Símbolos Alquímicos
            r"[\U0001F780-\U0001F7FF]|"  # Geométricos estendidos
            r"[\U0001F800-\U0001F8FF]|"  # Setas suplementares
            r"[\U0001F900-\U0001F9FF]|"  # Pictogramas suplementares
            r"[\U0001FA00-\U0001FA6F]|"  # Xadrez e símbolos
            r"[\U0001FA70-\U0001FAFF]|"  # Símbolos estendidos-A
            r"[\U00002702-\U000027B0]|"  # Dingbats
            r"[\U000024C2-\U0001F251]"   # Enclosed caracteres
        )

        for file_path in files_to_check:
            self.assertTrue(os.path.exists(file_path), f"Arquivo não encontrado: {file_path}")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            matches = emoji_pattern.findall(content)
            self.assertEqual(
                len(matches),
                0,
                f"Emojis detectados no arquivo {os.path.basename(file_path)}: {matches}"
            )


if __name__ == "__main__":
    unittest.main()
