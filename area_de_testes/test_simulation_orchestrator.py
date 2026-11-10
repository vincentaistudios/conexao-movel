# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de Testes da Infraestrutura de Simulacao Docker/KVM.
Garante prontidao do ambiente virtualizado para testes de mobile e Windows.
"""

import os
import sys
import unittest

sim_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "simulacao")
if sim_dir not in sys.path:
    sys.path.insert(0, sim_dir)

from run_simulation import check_kvm_support, check_docker_support, COMPOSE_FILE, PRESETS

class TestSimulationOrchestrator(unittest.TestCase):
    def test_compose_file_exists_and_configured(self):
        """Valida que o arquivo docker-compose.yml de simulacao existe e esta estruturado"""
        self.assertTrue(os.path.isfile(COMPOSE_FILE), "docker-compose.yml de simulacao deve existir")
        with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("mobile-android:", content)
        self.assertIn("desktop-windows:", content)
        self.assertIn("/dev/kvm", content)
        self.assertIn("sim_bridge", content)

    def test_kvm_and_docker_readiness(self):
        """Valida prontidao da virtualizacao KVM e do daemon Docker"""
        self.assertTrue(check_kvm_support(), "/dev/kvm deve estar acessivel e com permissao de escrita")
        self.assertTrue(check_docker_support(), "Daemon Docker deve estar ativo e respondendo")

    def test_presets_coverage(self):
        """Garante cobertura minima de smartphone e tablet nos presets"""
        self.assertIn("phone", PRESETS)
        self.assertIn("tablet", PRESETS)

if __name__ == "__main__":
    unittest.main()
