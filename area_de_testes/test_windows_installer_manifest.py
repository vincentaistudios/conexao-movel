# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de Testes de Validacao do Manifesto e Dependencias do Instalador Windows.
Inspeciona os manifestos AppxManifest.xml, nectarlink.nsi e o script package.ps1
garantindo que todas as dependencias, permissoes e arquivos obrigatorios estejam presentes.
"""

import os
import re
import unittest
import xml.etree.ElementTree as ET

REPO_ROOT = "/home/Vincent/.gemini/antigravity/scratch/nectarlink"
APPX_MANIFEST_PATH = os.path.join(REPO_ROOT, "desktop", "installer", "AppxManifest.xml")
NSIS_INSTALLER_PATH = os.path.join(REPO_ROOT, "desktop", "installer", "nectarlink.nsi")
PACKAGE_SCRIPT_PATH = os.path.join(REPO_ROOT, "scripts", "package.ps1")
WIN_DIST_DIR = "/home/Vincent/Downloads/Compartilhar-com-Amigos/2 - Computador (Windows)"


class TestWindowsInstallerManifest(unittest.TestCase):
    """Testes de integridade do manifesto do pacote Windows e dependencias requeridas."""

    def test_appx_manifest_file_exists(self):
        """Valida que o arquivo AppxManifest.xml existe e possui leitura habilitada."""
        self.assertTrue(os.path.isfile(APPX_MANIFEST_PATH), f"AppxManifest ausente: {APPX_MANIFEST_PATH}")
        self.assertGreater(os.path.getsize(APPX_MANIFEST_PATH), 500)

    def test_appx_manifest_xml_structure(self):
        """Valida que o arquivo XML e valido e contem elementos fundamentais de pacote."""
        tree = ET.parse(APPX_MANIFEST_PATH)
        root = tree.getroot()
        self.assertTrue(root.tag.endswith("Package"), "Raiz do manifesto deve ser <Package>")

        # Extrai namespace padrao
        ns = {"ns": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}

        # Identidade do pacote
        identity = root.find("ns:Identity", ns)
        self.assertIsNotNone(identity, "Elemento <Identity> ausente no manifesto")
        self.assertEqual(identity.get("Name"), "Nectarlink.Desktop")
        self.assertIn("CN=", identity.get("Publisher"))
        self.assertIn(identity.get("ProcessorArchitecture"), ["x64", "arm64"])

        # Propriedades
        properties = root.find("ns:Properties", ns)
        self.assertIsNotNone(properties, "Elemento <Properties> ausente")
        display_name = properties.find("ns:DisplayName", ns)
        self.assertEqual(display_name.text, "Nectarlink")
        logo = properties.find("ns:Logo", ns)
        self.assertIn("Assets", logo.text)

        # Dependencias de plataforma
        dependencies = root.find("ns:Dependencies", ns)
        self.assertIsNotNone(dependencies, "Elemento <Dependencies> ausente")
        target_device = dependencies.find("ns:TargetDeviceFamily", ns)
        self.assertIsNotNone(target_device)
        self.assertEqual(target_device.get("Name"), "Windows.Desktop")
        self.assertGreaterEqual(target_device.get("MinVersion"), "10.0.19041.0")

    def test_appx_manifest_applications_and_extensions(self):
        """Valida declaracao de executavel, recursos visuais e extensoes de integracao do Windows."""
        tree = ET.parse(APPX_MANIFEST_PATH)
        root = tree.getroot()
        ns = {
            "ns": "http://schemas.microsoft.com/appx/manifest/foundation/windows10",
            "uap": "http://schemas.microsoft.com/appx/manifest/uap/windows10",
            "uap10": "http://schemas.microsoft.com/appx/manifest/uap/windows10/10",
            "desktop": "http://schemas.microsoft.com/appx/manifest/desktop/windows10",
            "rescap": "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
        }

        app = root.find(".//ns:Application", ns)
        self.assertIsNotNone(app, "Elemento <Application> ausente")
        self.assertEqual(app.get("Executable"), "nectarlink-desktop.exe")

        # Extensao de Compartilhamento nativo (ShareTarget)
        share_target = app.find(".//uap:ShareTarget", ns)
        self.assertIsNotNone(share_target, "ShareTarget ausente nas extensoes")
        data_formats = [df.text for df in share_target.findall("uap:DataFormat", ns)]
        self.assertIn("StorageItems", data_formats)
        self.assertIn("WebLink", data_formats)
        self.assertIn("Text", data_formats)

        # Extensao de Notificacoes Toast
        toast_activation = app.find(".//desktop:ToastNotificationActivation", ns)
        self.assertIsNotNone(toast_activation, "ToastNotificationActivation ausente")
        self.assertTrue(len(toast_activation.get("ToastActivatorCLSID")) > 10)

        # Capacidades de seguranca
        capabilities = [c.get("Name") for c in root.findall(".//rescap:Capability", ns)]
        self.assertIn("runFullTrust", capabilities)
        self.assertIn("unvirtualizedResources", capabilities)

    def test_nsis_installer_definitions_and_rules(self):
        """Valida que o script NSIS contem todas as definicoes e arquivos requeridos para a instalacao."""
        self.assertTrue(os.path.isfile(NSIS_INSTALLER_PATH))
        with open(NSIS_INSTALLER_PATH, "r", encoding="utf-8", errors="ignore") as f:
            nsis_content = f.read()

        # Nomes canonicos
        self.assertIn('!define APP "Nectarlink"', nsis_content)
        self.assertIn('!define DISPLAY "Conexão Móvel"', nsis_content)
        self.assertIn('!define EXE "nectarlink-desktop.exe"', nsis_content)
        self.assertIn('!define SETUP_EXE "Conexao Movel Setup.exe"', nsis_content)

        # Regra de Firewall do Windows
        self.assertIn('!define FIREWALL_RULE "Nectarlink"', nsis_content)
        self.assertIn("netsh advfirewall firewall add rule", nsis_content)

        # Desinstalador seguro
        self.assertIn('WriteUninstaller "$INSTDIR\\uninstall.exe"', nsis_content)

        # DLLs e drivers de sistema
        self.assertIn("nectarlink_vcam.dll", nsis_content)
        self.assertIn("vcruntime140.dll", nsis_content)
        self.assertIn("msvcp140.dll", nsis_content)

        # Tarefa agendada para atualizacoes
        self.assertIn("Nectarlink Update", nsis_content)
        self.assertIn("schtasks /Create", nsis_content)

    def test_package_ps1_staging_manifest_requirements(self):
        """Valida que o script PowerShell de empacotamento lista todos os artefatos necessarios."""
        self.assertTrue(os.path.isfile(PACKAGE_SCRIPT_PATH))
        with open(PACKAGE_SCRIPT_PATH, "r", encoding="utf-8", errors="ignore") as f:
            ps_content = f.read()

        # Binarios principais
        self.assertIn("nectarlink-desktop.exe", ps_content)
        self.assertIn("nectarlink_vcam.dll", ps_content)

        # Manifestos e assets visuais
        self.assertIn("AppxManifest.xml", ps_content)
        self.assertIn("Square44x44Logo.png", ps_content)
        self.assertIn("Square150x150Logo.png", ps_content)

        # Licencas e avisos legais
        self.assertIn("LICENSE.txt", ps_content)
        self.assertIn("THIRD-PARTY-NOTICES.txt", ps_content)

        # Integracao com NSIS
        self.assertIn("nectarlink.nsi", ps_content)

    def test_windows_distribution_installer_binary_presence(self):
        """Valida presenca e integridade do executavel final do instalador para distribuicao."""
        self.assertTrue(os.path.isdir(WIN_DIST_DIR), f"Diretorio de distribuicao ausente: {WIN_DIST_DIR}")
        installer_exe = os.path.join(WIN_DIST_DIR, "Instalador-Windows.exe")
        self.assertTrue(os.path.isfile(installer_exe), f"Instalador ausente: {installer_exe}")
        # Executavel deve ter tamanho condizente com instalador completo (mais de 10 MB)
        file_size_mb = os.path.getsize(installer_exe) / (1024 * 1024)
        self.assertGreater(file_size_mb, 10.0, f"Instalador com tamanho inesperado: {file_size_mb:.2f} MB")

    def test_no_emojis_in_source_code(self):
        """Garante ausencia estrita de emojis no arquivo de testes segundo diretriz global."""
        current_file = os.path.abspath(__file__)
        with open(current_file, "r", encoding="utf-8") as f:
            content = f.read()

        for char in content:
            code_point = ord(char)
            is_emoji = (
                (0x1F600 <= code_point <= 0x1F64F)
                or (0x1F300 <= code_point <= 0x1F5FF)
                or (0x1F680 <= code_point <= 0x1F6FF)
                or (0x2600 <= code_point <= 0x26FF)
                or (0x2700 <= code_point <= 0x27BF)
                or (0x1F900 <= code_point <= 0x1F9FF)
            )
            self.assertFalse(is_emoji, f"Emoji detectado no codigo fonte: code point {code_point}")


if __name__ == "__main__":
    unittest.main()
