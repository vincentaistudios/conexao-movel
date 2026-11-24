#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validação de integridade do README.md e assets gráficos de branding.
Verifica:
1. Sintaxe XML dos arquivos SVG criados.
2. Existência de todos os assets locais referenciados no README.
3. Coerência dos links e menção à versão v0.1.8 e repositório vincentaistudios/conexao-movel.
4. Ausência estrita de emojis em conformidade com a Regra 3 do sistema.
"""

import os
import re
import unittest
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.expanduser("~/.gemini/antigravity/scratch/nectarlink")
README_PATH = os.path.join(REPO_ROOT, "README.md")

EXPECTED_SVGS = [
    os.path.join(REPO_ROOT, "assets/brand/banner-hero-animated.svg"),
    os.path.join(REPO_ROOT, "docs/assets/mockup-spike-companion.svg"),
    os.path.join(REPO_ROOT, "docs/assets/mockup-stream-deck.svg"),
    os.path.join(REPO_ROOT, "docs/assets/mockup-ecosystem-sync.svg"),
    os.path.join(REPO_ROOT, "assets/badges/badge-version.svg"),
    os.path.join(REPO_ROOT, "assets/badges/badge-download.svg"),
    os.path.join(REPO_ROOT, "assets/badges/badge-android.svg"),
    os.path.join(REPO_ROOT, "assets/badges/badge-windows.svg"),
    os.path.join(REPO_ROOT, "assets/badges/badge-linux.svg"),
    os.path.join(REPO_ROOT, "assets/badges/badge-localfirst.svg"),
    os.path.join(REPO_ROOT, "assets/badges/badge-license.svg"),
]

EMOJI_PATTERN = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]"
)


class TestReadmeAndBrandingAssets(unittest.TestCase):

    def test_svg_xml_syntax(self):
        """Valida que todos os SVGs são documentos XML bem formados e válidos."""
        for svg_file in EXPECTED_SVGS:
            self.assertTrue(os.path.isfile(svg_file), f"Arquivo não encontrado: {svg_file}")
            try:
                tree = ET.parse(svg_file)
                root = tree.getroot()
                self.assertTrue(root.tag.endswith("svg"), f"Tag raiz não é svg em: {svg_file}")
            except Exception as e:
                self.fail(f"Erro ao analisar XML de {svg_file}: {e}")

    def test_readme_referenced_local_assets_exist(self):
        """Valida que todas as imagens locais referenciadas no README.md realmente existem."""
        self.assertTrue(os.path.isfile(README_PATH), "README.md não encontrado")
        with open(README_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Busca por tags <img src="..."> e ![...](...)
        img_src_matches = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        md_img_matches = re.findall(r'!\[.*?\]\((.*?)\)', content)
        all_imgs = img_src_matches + md_img_matches

        local_imgs = [img for img in all_imgs if not img.startswith("http")]
        self.assertGreater(len(local_imgs), 0, "Nenhuma imagem local encontrada no README.md")

        for img_rel in local_imgs:
            abs_path = os.path.join(REPO_ROOT, img_rel)
            self.assertTrue(
                os.path.isfile(abs_path),
                f"Imagem local referenciada no README não existe: {img_rel} (esperado em {abs_path})"
            )

    def test_readme_branding_and_links(self):
        """Valida que o README possui os links corretos da organização e menção à v0.1.8."""
        with open(README_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("vincentaistudios/conexao-movel", content)
        self.assertIn("v0.1.8", content)
        self.assertIn("Spike Companion", content)
        self.assertIn("Snap Layout", content)
        self.assertIn("GPL-3.0", content)

    def test_no_emojis_in_readme_and_assets(self):
        """Valida a ausência estrita de emojis no README e nos assets SVG (Regra 3)."""
        targets = [README_PATH] + EXPECTED_SVGS
        for t in targets:
            with open(t, "r", encoding="utf-8") as f:
                text = f.read()
            emojis = EMOJI_PATTERN.findall(text)
            self.assertEqual(
                len(emojis), 0,
                f"Emojis proibidos encontrados em {os.path.basename(t)}: {emojis}"
            )


    def test_stream_deck_mockup_responsive_and_no_overflow(self):
        """Valida que o mockup do stream deck não possui nomes rígidos e expandiu os contêineres contra overflow."""
        mockup_path = os.path.join(REPO_ROOT, "docs/assets/mockup-stream-deck.svg")
        with open(mockup_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Garante que nomes rígidos específicos não estão presentes
        self.assertNotIn("PC VINCENT", content)
        self.assertIn("COMPUTADOR CONECTADO", content)
        self.assertIn("REDE LOCAL", content)

        # Garante que os contêineres do painel direito foram expandidos para evitar overflow
        self.assertIn('width="450"', content)
        self.assertIn('width="402"', content)
        self.assertIn("Maximizar aplicativo no monitor principal", content)


if __name__ == "__main__":
    unittest.main()

