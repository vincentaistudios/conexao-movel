#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validação da Segunda Tela acionável pelo PC, persistência de tema e verificação anti-emojis.
Localizado em: area_de_testes/test_second_screen_pc_trigger.py
"""

import unittest
import os
import re

SCRATCH_DIR = "/home/Vincent/.gemini/antigravity/scratch/nectarlink"

class TestSecondScreenPcTrigger(unittest.TestCase):

    def test_hive_invite_dismissed_not_reset_on_update(self):
        """Verifica que a flag hive_invite_dismissed não é mais zerada no main.rs."""
        main_rs = os.path.join(SCRATCH_DIR, "desktop/app/src/main.rs")
        with open(main_rs, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("std::mem::take(&mut saved.hive_invite_dismissed)", content,
                         "hive_invite_dismissed ainda está sendo resetado em main.rs")

    def test_pc_mirror_is_second_screen_active_exists(self):
        """Verifica se is_second_screen_active está declarado e exposto em pc_mirror.rs."""
        pc_mirror_rs = os.path.join(SCRATCH_DIR, "desktop/app/src/pc_mirror.rs")
        with open(pc_mirror_rs, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("pub fn is_second_screen_active() -> bool", content)
        self.assertIn("second_screen: options.second_screen", content)

    def test_bridge_app_toggle_second_screen_exposed(self):
        """Verifica se toggle_second_screen e second_screen_active estão expostos ao QML."""
        app_rs = os.path.join(SCRATCH_DIR, "desktop/app/src/bridge/app.rs")
        with open(app_rs, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("fn toggle_second_screen(self: Pin<&mut AppController>, device: &QString);", content)
        self.assertIn("#[qproperty(bool, second_screen_active)]", content)
        self.assertIn("pub fn toggle_second_screen(mut self: Pin<&mut Self>, device: &QString)", content)
        self.assertIn("second_screen: true", content)

    def test_homepage_qml_action_tile_second_screen(self):
        """Verifica se o botão ActionTile de Segunda Tela está presente no HomePage.qml."""
        home_qml = os.path.join(SCRATCH_DIR, "desktop/app/qml/pages/HomePage.qml")
        with open(home_qml, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('title: qsTr("Segunda tela")', content)
        self.assertIn("AppController.toggleSecondScreen(home.deviceId)", content)
        self.assertIn("AppController.secondScreenActive", content)

    def test_no_emojis_in_new_code(self):
        """Regra 3: Proibição absoluta de emojis em código e strings de interface."""
        files_to_check = [
            os.path.join(SCRATCH_DIR, "desktop/app/src/main.rs"),
            os.path.join(SCRATCH_DIR, "desktop/app/src/pc_mirror.rs"),
            os.path.join(SCRATCH_DIR, "desktop/app/src/bridge/app.rs"),
            os.path.join(SCRATCH_DIR, "desktop/app/qml/pages/HomePage.qml")
        ]
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F700-\U0001F77F"
            "\U0001F780-\U0001F7FF"
            "\U0001F800-\U0001F8FF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA00-\U0001FA6F"
            "\U0001FA70-\U0001FAFF"
            "\U00002702-\U000027B0]"
        )
        for filepath in files_to_check:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                matches = emoji_pattern.findall(content)
                self.assertEqual(len(matches), 0, f"Emojis proibidos encontrados em {filepath}: {matches}")

if __name__ == "__main__":
    unittest.main()
