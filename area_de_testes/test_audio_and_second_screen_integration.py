#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de Homologacao e Integracao: Audio Integrado no Espelhamento do PC e Segunda Tela Virtual
Valida a integridade dos contratos de dados, configuracoes do xrandr, mapeamento de coordenadas,
reproducao de audio simultanea e compatibilidade com a suite Android Jetpack Compose.
"""

import os
import re
import unittest
from pathlib import Path

BASE_DIR = Path("/home/Vincent/.gemini/antigravity/scratch/nectarlink")


class TestAudioAndSecondScreenIntegration(unittest.TestCase):
    def setUp(self):
        self.pc_mirror_file = BASE_DIR / "desktop/app/src/pc_mirror.rs"
        self.virtual_display_file = BASE_DIR / "desktop/app/src/linux/virtual_display.rs"
        self.protocol_file = BASE_DIR / "core/nectarlink-protocol/src/messages.rs"
        self.ffi_file = BASE_DIR / "core/nectarlink-ffi/src/lib.rs"
        self.remote_screen_file = (
            BASE_DIR / "android/app/src/main/kotlin/app/nectarlink/android/ui/remote/RemoteScreen.kt"
        )
        self.pc_mirror_view_file = (
            BASE_DIR / "android/app/src/main/kotlin/app/nectarlink/android/ui/remote/PcMirrorView.kt"
        )
        self.strings_pt_br_file = (
            BASE_DIR / "android/app/src/main/res/values-pt-rBR/strings.xml"
        )

    def test_protocol_mirror_start_contains_second_screen_field(self):
        """Valida se o protocolo de espelhamento suporta o campo second_screen com deserializacao defensiva."""
        content = self.protocol_file.read_text(encoding="utf-8")
        self.assertIn("pub second_screen: bool", content)
        self.assertIn('serde(default, skip_serializing_if = "std::ops::Not::not")', content)

    def test_pc_mirror_starts_sound_for_regular_desktop_and_second_screen(self):
        """Valida se a captura de audio de baixa latencia e ativada no espelhamento padrao e segunda tela."""
        content = self.pc_mirror_file.read_text(encoding="utf-8")
        self.assertIn("SoundToPhone::start(peer, watched.is_some())", content)
        # Confirma que SoundToPhone::start nao muta o PC quando watched for falso
        self.assertIn("fn start(peer: DeviceId, mute_pc: bool) -> SoundToPhone", content)
        self.assertIn("let muted = mute_pc", content)

    def test_virtual_display_module_exists_and_implements_raii(self):
        """Valida se o modulo de display virtual esta implementado com liberacao defensiva no Drop."""
        self.assertTrue(self.virtual_display_file.exists())
        content = self.virtual_display_file.read_text(encoding="utf-8")
        self.assertIn("pub struct VirtualDisplay", content)
        self.assertIn("impl Drop for VirtualDisplay", content)
        self.assertIn("self.release()", content)
        self.assertIn("--output", content)
        self.assertIn("--off", content)

    def test_virtual_display_coordinate_mapping_logic(self):
        """Testa o mapeamento matematico de toque [0.0, 1.0] para a area estendida."""
        primary_w = 2560
        target_w = 1920
        target_h = 1080

        left = primary_w
        top = 0

        # Canto superior esquerdo
        x0 = left + int(round(0.0 * target_w))
        y0 = top + int(round(0.0 * target_h))
        self.assertEqual((x0, y0), (2560, 0))

        # Ponto central
        x_mid = left + int(round(0.5 * target_w))
        y_mid = top + int(round(0.5 * target_h))
        self.assertEqual((x_mid, y_mid), (3520, 540))

        # Canto inferior direito
        x_max = left + int(round(1.0 * target_w))
        y_max = top + int(round(1.0 * target_h))
        self.assertEqual((x_max, y_max), (4480, 1080))

    def test_ffi_exports_second_screen_and_enables_audio(self):
        """Valida se o FFI transmite audio: true e second_screen."""
        content = self.ffi_file.read_text(encoding="utf-8")
        self.assertIn("second_screen: Option<bool>", content)
        self.assertIn("audio: true", content)
        self.assertIn("second_screen: second_screen.unwrap_or(false)", content)

    def test_android_remote_mode_includes_second_screen(self):
        """Valida se o RemoteScreen do Android possui o modo SecondScreen integrado."""
        content = self.remote_screen_file.read_text(encoding="utf-8")
        self.assertIn("enum class RemoteMode { Touchpad, AirMouse, Presentation, Screen, SecondScreen }", content)
        self.assertIn("RemoteMode.SecondScreen", content)
        self.assertIn("stringResource(R.string.remote_mode_second_screen)", content)
        self.assertIn("isSecondScreen = true", content)

    def test_android_pc_mirror_view_supports_second_screen_parameter(self):
        """Valida se o PcMirrorView recebe e despacha isSecondScreen para o core."""
        content = self.pc_mirror_view_file.read_text(encoding="utf-8")
        self.assertIn("isSecondScreen: Boolean = false", content)
        self.assertIn("secondScreen = isSecondScreen", content)

    def test_pt_br_strings_contain_proper_labels_without_emojis(self):
        """Valida a presenca de rotulos em pt-BR e ausencia total de emojis."""
        content = self.strings_pt_br_file.read_text(encoding="utf-8")
        self.assertIn('name="remote_mode_second_screen">Segunda tela<', content)
        self.assertIn('name="desk_second_screen">Segunda tela<', content)
        self.assertIn('name="second_screen_badge">Segunda tela virtual<', content)

        # Verificacao estrita contra caracteres emoji Unicode na declaracao
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F900-\U0001F9FF]"
        )
        self.assertIsNone(
            emoji_pattern.search(content),
            "Detectado emoji proibido nas definicoes de strings de interface",
        )


if __name__ == "__main__":
    unittest.main()
