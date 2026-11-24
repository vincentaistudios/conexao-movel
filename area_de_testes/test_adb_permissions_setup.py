# SPDX-License-Identifier: GPL-3.0-or-later
"""
Testes unitarios e de integracao para validacao do Assistente de Permissoes
e Modo Elevado em 1 Clique (via ADB) para Windows e Linux.
"""

import os
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WINDOWS_PKG = os.path.join(REPO_ROOT, "desktop", "packaging", "windows")
LINUX_PKG = os.path.join(REPO_ROOT, "desktop", "packaging", "linux")
SRC_DIR = os.path.join(REPO_ROOT, "desktop", "app", "src")
QML_COMPONENTS = os.path.join(REPO_ROOT, "desktop", "app", "qml", "components")


class TestAdbPermissionsSetup(unittest.TestCase):
    """Bateria de testes para os scripts e modulo Rust do assistente ADB."""

    def test_windows_powershell_script_exists_and_covers_all_grants(self):
        """Verifica se o script PowerShell do Windows cobre todas as permissoes e servicos."""
        ps_path = os.path.join(WINDOWS_PKG, "auto_setup_phone_permissions.ps1")
        self.assertTrue(os.path.exists(ps_path), f"Arquivo nao encontrado: {ps_path}")

        with open(ps_path, "r", encoding="utf-8") as f:
            content = f.read()

        expected_perms = [
            "android.permission.POST_NOTIFICATIONS",
            "android.permission.READ_CONTACTS",
            "android.permission.READ_PHONE_STATE",
            "android.permission.READ_CALL_LOG",
            "android.permission.CALL_PHONE",
            "android.permission.ANSWER_PHONE_CALLS",
            "android.permission.READ_SMS",
            "android.permission.SEND_SMS",
            "android.permission.READ_MEDIA_IMAGES",
            "android.permission.READ_MEDIA_VIDEO",
            "android.permission.BLUETOOTH_CONNECT",
            "android.permission.WRITE_SECURE_SETTINGS",
            "WRITE_SETTINGS",
            "SYSTEM_ALERT_WINDOW",
            "GET_USAGE_STATS",
            "NotificationListener",
            "allow_dnd",
            "InputService",
            "InputServer",
        ]
        for term in expected_perms:
            self.assertIn(term, content, f"Script PowerShell deve conceder ou gerenciar: {term}")

    def test_windows_bat_wrapper_exists(self):
        """Verifica se o wrapper executavel .bat para Windows existe e executa o PowerShell."""
        bat_path = os.path.join(WINDOWS_PKG, "auto_setup_phone_permissions.bat")
        self.assertTrue(os.path.exists(bat_path), f"Arquivo .bat nao encontrado: {bat_path}")

        with open(bat_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("auto_setup_phone_permissions.ps1", content)

    def test_linux_bash_script_exists_and_is_executable(self):
        """Verifica se o script bash para Linux existe, e executavel e possui todas as concessões."""
        sh_path = os.path.join(LINUX_PKG, "auto_setup_phone_permissions.sh")
        self.assertTrue(os.path.exists(sh_path), f"Arquivo .sh nao encontrado: {sh_path}")
        self.assertTrue(os.access(sh_path, os.X_OK), f"Script {sh_path} deve possuir permissao de execucao (+x)")

        with open(sh_path, "r", encoding="utf-8") as f:
            content = f.read()

        expected_tokens = [
            "android.permission.POST_NOTIFICATIONS",
            "android.permission.READ_CONTACTS",
            "android.permission.BLUETOOTH_CONNECT",
            "android.permission.WRITE_SECURE_SETTINGS",
            "WRITE_SETTINGS",
            "NotificationListener",
            "allow_dnd",
            "InputService",
            "InputServer",
        ]
        for tok in expected_tokens:
            self.assertIn(tok, content, f"Script Linux deve conter concessao para: {tok}")

    def test_rust_adb_setup_module_implements_safe_execution(self):
        """Verifica se desktop/app/src/adb_setup.rs implementa protecoes de seguranca."""
        rs_path = os.path.join(SRC_DIR, "adb_setup.rs")
        self.assertTrue(os.path.exists(rs_path), f"Arquivo adb_setup.rs nao encontrado: {rs_path}")

        with open(rs_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("is_serial_allowed", content,
                      "adb_setup.rs deve validar serial com is_serial_allowed antes de comandos")
        self.assertIn("run_auto_setup", content,
                      "adb_setup.rs deve conter a funcao de esteira run_auto_setup")
        self.assertIn("InputServer", content,
                      "adb_setup.rs deve inicializar o InputServer para ativacao do Modo Elevado")

    def test_phone_setup_card_qml_exists(self):
        """Verifica se o componente visual PhoneSetupCard.qml foi criado e contem as acoes necessarias."""
        qml_path = os.path.join(QML_COMPONENTS, "PhoneSetupCard.qml")
        self.assertTrue(os.path.exists(qml_path), f"PhoneSetupCard.qml nao encontrado: {qml_path}")

        with open(qml_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("AppController.listAdbDevices", content,
                      "PhoneSetupCard.qml deve chamar AppController.listAdbDevices")
        self.assertIn("AppController.runAdbAutoSetup", content,
                      "PhoneSetupCard.qml deve chamar AppController.runAdbAutoSetup")


if __name__ == "__main__":
    unittest.main()

