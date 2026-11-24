# SPDX-License-Identifier: GPL-3.0-or-later
"""
Testes unitarios e estaticos para validacao das permissoes de Bluetooth
e tratamento de Modo Elevado no Conexao Movel (NectarLink).
"""

import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANDROID_DIR = os.path.join(REPO_ROOT, "android", "app", "src", "main")
DESKTOP_DIR = os.path.join(REPO_ROOT, "desktop", "app", "src")


class TestBluetoothTogglePermissions(unittest.TestCase):
    """Bateria de testes para as politicas de permissao e alternancia de Bluetooth."""

    def test_android_manifest_contains_bluetooth_permissions(self):
        """Verifica se o manifesto Android declara BLUETOOTH_CONNECT e legadas."""
        manifest_path = os.path.join(ANDROID_DIR, "AndroidManifest.xml")
        self.assertTrue(os.path.exists(manifest_path), f"Manifesto nao encontrado: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("android.permission.BLUETOOTH_CONNECT", content,
                      "AndroidManifest.xml deve declarar android.permission.BLUETOOTH_CONNECT para Android 12+")
        self.assertIn("android.permission.BLUETOOTH", content,
                      "AndroidManifest.xml deve declarar android.permission.BLUETOOTH para compatibilidade legada")
        self.assertIn("android.permission.BLUETOOTH_ADMIN", content,
                      "AndroidManifest.xml deve declarar android.permission.BLUETOOTH_ADMIN para compatibilidade legada")

    def test_phone_toggles_can_change_bluetooth_requires_elevated_on_q_plus(self):
        """Verifica se canChangeBluetooth() exige Modo Elevado a partir do Android 10 (Q)."""
        toggles_path = os.path.join(ANDROID_DIR, "kotlin", "app", "nectarlink", "android", "toggles", "PhoneToggles.kt")
        self.assertTrue(os.path.exists(toggles_path), f"PhoneToggles.kt nao encontrado: {toggles_path}")

        with open(toggles_path, "r", encoding="utf-8") as f:
            content = f.read()

        match = re.search(r"fun canChangeBluetooth\(\):\s*Boolean\s*=\s*([^;\n]+)", content)
        self.assertIsNotNone(match, "Funcao canChangeBluetooth() nao encontrada em PhoneToggles.kt")
        expr = match.group(1).strip()
        self.assertIn("Elevated.running", expr,
                      "canChangeBluetooth() deve verificar se Elevated.running esta ativo")
        self.assertIn("Build.VERSION_CODES.Q", expr,
                      "canChangeBluetooth() deve checar a versao minima do Android (Build.VERSION_CODES.Q)")

    def test_bluetooth_toggles_helper_guards_silent_toggle(self):
        """Verifica se setBluetooth() em BluetoothTogglesHelper.kt protege contra falhas no Android 10+."""
        helper_path = os.path.join(ANDROID_DIR, "kotlin", "app", "nectarlink", "android", "toggles", "BluetoothTogglesHelper.kt")
        self.assertTrue(os.path.exists(helper_path), f"BluetoothTogglesHelper.kt nao encontrado: {helper_path}")

        with open(helper_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Elevated.running", content, "setBluetooth deve usar Elevated.running quando disponivel")
        self.assertIn("Build.VERSION_CODES.Q", content,
                      "setBluetooth deve bloquear tentativa silenciosa no Android 10+ sem Modo Elevado")

    def test_desktop_bridge_provides_friendly_error_for_bluetooth(self):
        """Verifica se o desktop exibe mensagem amigavel em caso de falha de alternancia sem Modo Elevado."""
        bridge_path = os.path.join(DESKTOP_DIR, "bridge", "app.rs")
        self.assertTrue(os.path.exists(bridge_path), f"bridge/app.rs nao encontrado: {bridge_path}")

        with open(bridge_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('failed_id == "bluetooth"', content,
                      "set_phone_toggle no bridge Rust deve capturar falha no toggle de bluetooth")
        self.assertIn("Settings › Elevated", content,
                      "Mensagem de erro deve orientar o usuario a ativar o Modo Elevado")


if __name__ == "__main__":
    unittest.main()

