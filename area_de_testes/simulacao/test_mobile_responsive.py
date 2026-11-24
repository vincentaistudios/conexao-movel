# SPDX-License-Identifier: GPL-3.0-or-later
"""
Testes de Responsividade, Viewport e Densidade de Tela Mobile para Simulacao.
Valida conformidade com perfis de Smartphone e Tablet sob o Android CDD.
"""

import unittest
from run_simulation import PRESETS

class TestMobileResponsiveSimulation(unittest.TestCase):
    def test_presets_completeness_and_aspect_ratios(self):
        """Valida se os perfis de simulacao contem metricas de tela validas e suportadas"""
        self.assertIn("phone", PRESETS)
        self.assertIn("tablet", PRESETS)
        self.assertIn("compact", PRESETS)

        for name, p in PRESETS.items():
            self.assertGreater(p["width"], 0, f"Largura invalida no perfil {name}")
            self.assertGreater(p["height"], 0, f"Altura invalida no perfil {name}")
            self.assertGreater(p["dpi"], 120, f"DPI muito baixo no perfil {name}")
            self.assertLessEqual(p["dpi"], 640, f"DPI excessivo no perfil {name}")

            # Razao de aspecto (altura / largura em modo retrato)
            aspect_ratio = p["height"] / p["width"]
            if name == "tablet":
                # Tablets tipicamente possuem aspecto 16:10 (1.6) ou 4:3 (1.33)
                self.assertAlmostEqual(aspect_ratio, 1.6, delta=0.15)
            else:
                # Smartphones modernos variam entre 19:9 e 21:9 (2.0 a 2.33)
                self.assertGreaterEqual(aspect_ratio, 1.9)
                self.assertLessEqual(aspect_ratio, 2.4)

    def test_dp_density_buckets_calculation(self):
        """Valida conversao de pixels fisicos para densidade dp (Density-Independent Pixels)"""
        # dp = px / (dpi / 160)
        phone = PRESETS["phone"]
        phone_width_dp = phone["width"] / (phone["dpi"] / 160.0)
        
        tablet = PRESETS["tablet"]
        tablet_width_dp = tablet["width"] / (tablet["dpi"] / 160.0)

        # Smartphones devem se enquadrar na categoria < 600dp (layout vertical/compacto)
        self.assertLess(phone_width_dp, 600.0, "Smartphone nao deve ser classificado como tela larga (sw600dp)")

        # Tablets devem atender ao limiar sw600dp ou superior (habilita modo split/duas colunas)
        self.assertGreaterEqual(tablet_width_dp, 600.0, "Tablet deve atingir o limiar sw600dp para layouts expandidos")

    def test_adb_window_manager_commands_format(self):
        """Valida que comandos de ajuste dinamico de resolucao ADB estejam no formato correto"""
        for name, p in PRESETS.items():
            wm_size_cmd = f"wm size {p['width']}x{p['height']}"
            wm_density_cmd = f"wm density {p['dpi']}"
            
            self.assertTrue(wm_size_cmd.startswith("wm size "))
            self.assertIn("x", wm_size_cmd.split(" ")[2])
            self.assertTrue(wm_density_cmd.startswith("wm density "))
            self.assertTrue(wm_density_cmd.split(" ")[2].isdigit())

if __name__ == "__main__":
    unittest.main()

