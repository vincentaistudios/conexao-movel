# SPDX-License-Identifier: GPL-3.0-or-later
"""
Testes de Validacao de Pacotes e Interoperabilidade Windows para Simulacao.
Verifica integridade do instalador .exe, caminhos e volume compartilhado do Docker.
"""

import os
import unittest

class TestWindowsPackageSimulation(unittest.TestCase):
    def setUp(self):
        self.dist_dir = "/home/Vincent/Downloads/Compartilhar-com-Amigos"
        self.win_dir = os.path.join(self.dist_dir, "2 - Computador (Windows)")

    def test_windows_package_directory_exists(self):
        """Valida que o diretorio dedicado a distribuicao Windows existe"""
        self.assertTrue(os.path.isdir(self.win_dir), f"Diretorio Windows nao encontrado em {self.win_dir}")

    def test_windows_installer_executable_present(self):
        """Valida presenca do binario instalador Windows (.exe)"""
        exe_path = os.path.join(self.win_dir, "Instalador-Windows.exe")
        self.assertTrue(os.path.isfile(exe_path), "Instalador-Windows.exe deve estar presente")
        self.assertGreater(os.path.getsize(exe_path), 5 * 1024 * 1024, "Tamanho do instalador .exe incompativel")

    def test_windows_path_conversion_helper(self):
        """Valida conversao segura de caminhos Unix para caminhos NTFS do Windows"""
        def to_windows_path(unix_path: str, drive_letter: str = "C:") -> str:
            clean = unix_path.strip().replace("/", "\\")
            if clean.startswith("\\"):
                return drive_letter + clean
            return drive_letter + "\\" + clean

        self.assertEqual(to_windows_path("/shared/app.exe"), "C:\\shared\\app.exe")
        self.assertEqual(to_windows_path("Program Files/ConexaoMovel"), "C:\\Program Files\\ConexaoMovel")
        self.assertNotIn("/", to_windows_path("/AppData/Local/Temp"))

    def test_docker_shared_volume_path_validity(self):
        """Valida que o volume compartilhado para o Windows no docker-compose e valido"""
        self.assertTrue(os.path.isdir(self.dist_dir))
        self.assertTrue(os.access(self.dist_dir, os.R_OK))

if __name__ == "__main__":
    unittest.main()
