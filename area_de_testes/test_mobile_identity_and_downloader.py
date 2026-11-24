#!/usr/bin/env python3
"""
Suite de validacao da identidade visual (monograma V), nacionalizacao pt-BR,
versionamento Cargo e conformidade modular (limite de linhas e zero emojis)
dos componentes moveis e da ponte de downloads do Conexao Movel.
"""

import glob
import os
import re
import tomllib
import unittest
import xml.etree.ElementTree as ET
from PIL import Image


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANDROID_RES = os.path.join(REPO_ROOT, "android", "app", "src", "main", "res")
ANDROID_KOTLIN = os.path.join(
    REPO_ROOT, "android", "app", "src", "main", "kotlin", "app", "nectarlink", "android"
)

EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002300-\U000023FF"
    r"\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF\uFE0F\u200D]"
)


class TestMobileIdentityAndDownloader(unittest.TestCase):
    """Testes de integridade visual, localizacao, versao e modularidade."""

    LEGACY_MARKERS = ("M41.5,42.5C", "#2C1600")

    V_LAUNCHER_PATHS = (
        "M31.92,32.88 L43.44,32.88 L54,65.04 L49.2,72.72 Z",
        "M76.08,32.88 L64.56,32.88 L54,65.04 L58.8,72.72 Z",
        "M54,65.04 L49.2,72.72 L54,75.12 L58.8,72.72 Z",
        "M54,35.76 L57.36,42.36 L54,48.96 L50.64,42.36 Z",
    )

    V_BACKGROUND_MARKERS = (
        "M0,0h108v108h-108z",
        "M54,18.25a34,34",
        "M54,32a22,22",
        "#FF0F172A",
        "#2638BDF8",
    )

    V_NOTIFICATION_PATHS = (
        "M2.8,3.2 L7.6,3.2 L12,16.6 L10,19.8 Z",
        "M21.2,3.2 L16.4,3.2 L12,16.6 L14,19.8 Z",
        "M12,16.6 L10,19.8 L12,20.8 L14,19.8 Z",
        "M12,4.4 L13.4,7.15 L12,9.9 L10.6,7.15 Z",
    )

    def _read_text(self, rel_path: str) -> str:
        full_path = os.path.join(REPO_ROOT, rel_path)
        self.assertTrue(os.path.isfile(full_path), f"Arquivo ausente: {full_path}")
        with open(full_path, "r", encoding="utf-8") as fh:
            return fh.read()

    def test_android_drawables_use_v_monogram_without_legacy_infinity(self):
        """Valida que todos os drawables de icone usam o monograma V e nao o infinito antigo."""
        drawable_expectations = {
            "android/app/src/main/res/drawable/ic_launcher_foreground.xml": self.V_LAUNCHER_PATHS,
            "android/app/src/main/res/drawable/ic_launcher_monochrome.xml": self.V_LAUNCHER_PATHS,
            "android/app/src/main/res/drawable/ic_launcher_background.xml": self.V_BACKGROUND_MARKERS,
            "android/app/src/main/res/drawable/ic_notification.xml": self.V_NOTIFICATION_PATHS,
        }

        for rel_path, expected_markers in drawable_expectations.items():
            content = self._read_text(rel_path)
            ET.fromstring(content)
            for legacy in self.LEGACY_MARKERS:
                self.assertNotIn(
                    legacy,
                    content,
                    f"Marcador legado '{legacy}' ainda presente em {rel_path}",
                )
            for marker in expected_markers:
                self.assertIn(
                    marker,
                    content,
                    f"Path/marcador oficial do monograma V ausente em {rel_path}: {marker}",
                )

    def test_all_strings_xml_use_conexao_movel_and_zero_nectarlink(self):
        """Valida app_name == 'Conexão Móvel' e zero 'NectarLink' em todos values*/strings.xml."""
        pattern = os.path.join(ANDROID_RES, "values*", "strings.xml")
        files = sorted(glob.glob(pattern))
        self.assertGreaterEqual(len(files), 1, f"Nenhum strings.xml encontrado em {pattern}")

        for xml_path in files:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            app_name_nodes = [
                el for el in root.findall("string") if el.get("name") == "app_name"
            ]
            self.assertEqual(
                len(app_name_nodes),
                1,
                f"Esperado exatamente 1 <string name='app_name'> em {xml_path}",
            )
            self.assertEqual(
                app_name_nodes[0].text,
                "Conexão Móvel",
                f"app_name divergente em {xml_path}: {app_name_nodes[0].text!r}",
            )

            for el in root.findall("string"):
                text = "".join(el.itertext())
                self.assertNotIn(
                    "NectarLink",
                    text,
                    f"Marca legada 'NectarLink' encontrada em {xml_path} [{el.get('name')}]: {text}",
                )

    def test_cargo_workspace_version_at_least_0_1_7(self):
        """Valida que Cargo.toml possui versao >= 0.1.7."""
        cargo_path = os.path.join(REPO_ROOT, "Cargo.toml")
        with open(cargo_path, "rb") as fh:
            data = tomllib.load(fh)

        version_str = data["workspace"]["package"]["version"]
        parts = tuple(int(p) for p in version_str.split("."))
        self.assertGreaterEqual(
            parts,
            (0, 1, 7),
            f"Versao de workspace em Cargo.toml deve ser >= 0.1.7, obteve {version_str}",
        )

        deps = data["workspace"]["dependencies"]
        for crate_name in ("nectarlink-adb", "nectarlink-protocol", "nectarlink-core", "nectarlink-vcam"):
            dep_ver = deps[crate_name]["version"]
            dep_parts = tuple(int(p) for p in dep_ver.split("."))
            self.assertGreaterEqual(
                dep_parts,
                (0, 1, 7),
                f"Versao de {crate_name} em Cargo.toml deve ser >= 0.1.7, obteve {dep_ver}",
            )

        desktop_cargo_path = os.path.join(REPO_ROOT, "desktop", "app", "Cargo.toml")
        with open(desktop_cargo_path, "rb") as fh:
            desktop_data = tomllib.load(fh)
        self.assertTrue(
            desktop_data["package"]["version"].get("workspace") is True,
            "desktop/app/Cargo.toml deve herdar version.workspace = true",
        )

    def test_android_mipmap_launcher_and_round_icons(self):
        """Valida os 10 PNGs mipmap, ic_launcher_round.xml e android:roundIcon no Manifest."""
        density_sizes = {
            "mipmap-mdpi": 48,
            "mipmap-hdpi": 72,
            "mipmap-xhdpi": 96,
            "mipmap-xxhdpi": 144,
            "mipmap-xxxhdpi": 192,
        }
        for folder, expected_px in density_sizes.items():
            for filename in ("ic_launcher.png", "ic_launcher_round.png"):
                png_path = os.path.join(ANDROID_RES, folder, filename)
                self.assertTrue(os.path.isfile(png_path), f"Mipmap ausente: {png_path}")
                with Image.open(png_path) as img:
                    self.assertEqual(
                        img.size,
                        (expected_px, expected_px),
                        f"Dimensao invalida em {png_path}: esperava {(expected_px, expected_px)}, obteve {img.size}",
                    )

        round_xml = self._read_text("android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml")
        round_root = ET.fromstring(round_xml)
        self.assertEqual(round_root.tag, "adaptive-icon")
        self.assertIn("@drawable/ic_launcher_background", round_xml)
        self.assertIn("@drawable/ic_launcher_foreground", round_xml)

        manifest_src = self._read_text("android/app/src/main/AndroidManifest.xml")
        self.assertIn('android:roundIcon="@mipmap/ic_launcher_round"', manifest_src)

    def test_brand_assets_use_v_monogram_without_legacy_honey(self):
        """Valida assets/brand/icon.svg e assets/brand/icon-512.png com o monograma V."""
        svg_src = self._read_text("assets/brand/icon.svg")
        ET.fromstring(svg_src)
        svg_lower = svg_src.lower()
        for legacy_hex in ("#2c1600", "#ffb95f", "m41.5,42.5"):
            self.assertNotIn(legacy_hex, svg_lower, f"Marcador legado '{legacy_hex}' em assets/brand/icon.svg")
        self.assertTrue(
            any(color in svg_lower for color in ("#0f172a", "#030712", "#38bdf8")),
            "assets/brand/icon.svg deve conter a paleta oficial do monograma V (#0F172A/#030712/#38BDF8)",
        )

        png_path = os.path.join(REPO_ROOT, "assets", "brand", "icon-512.png")
        self.assertTrue(os.path.isfile(png_path), f"Asset ausente: {png_path}")
        with Image.open(png_path) as img:
            self.assertEqual(img.size, (512, 512), f"icon-512.png deve ser 512x512, obteve {img.size}")
            rgba = img.convert("RGBA")
            r, g, b, _ = rgba.getpixel((256, 256))
            self.assertFalse(
                r > 230 and 155 <= g <= 215 and b < 120,
                f"Pixel central de icon-512.png parece dourado antigo: {(r, g, b)}",
            )
            self.assertNotEqual((r, g, b), (44, 22, 0), "Pixel central de icon-512.png nao pode ser marrom #2C1600")

    def test_desktop_mark_rs_uses_v_monogram_without_legacy_honey(self):
        """Valida ausencia da paleta antiga no codigo de producao de desktop/app/src/mark.rs."""
        mark_src = self._read_text("desktop/app/src/mark.rs")
        mark_prod = mark_src.split("#[cfg(test)]", 1)[0].lower()
        for legacy in ("#2c1600", "#ffb95f", "0x2c, 0x16, 0x00", "0xff, 0xb9, 0x5f"):
            self.assertNotIn(
                legacy,
                mark_prod,
                f"Paleta antiga '{legacy}' ainda presente em desktop/app/src/mark.rs",
            )
        self.assertIn("0x38, 0xbd, 0xf8", mark_prod, "Cor ciano do monograma V ausente em mark.rs")

    def test_downloader_and_quick_power_files_under_500_lines_and_no_emojis(self):
        """Valida limite de < 500 linhas e ausencia total de emojis Unicode."""
        target_files = [
            "android/app/src/main/kotlin/app/nectarlink/android/ui/downloader/MediaDownloaderSheet.kt",
            "android/app/src/main/kotlin/app/nectarlink/android/ui/downloader/MediaDownloaderComponents.kt",
            "android/app/src/main/kotlin/app/nectarlink/android/ui/downloader/MediaDownloaderModels.kt",
            "android/app/src/main/kotlin/app/nectarlink/android/ui/home/HomeQuickPowerBar.kt",
            "desktop/app/src/downloader_bridge.rs",
        ]

        for rel_path in target_files:
            content = self._read_text(rel_path)
            lines = content.splitlines()
            self.assertLess(
                len(lines),
                500,
                f"Arquivo {rel_path} excedeu o teto de 500 linhas ({len(lines)} linhas)",
            )
            emojis = [
                (idx + 1, EMOJI_PATTERN.findall(line))
                for idx, line in enumerate(lines)
                if EMOJI_PATTERN.search(line)
            ]
            self.assertEqual(
                emojis,
                [],
                f"Emojis Unicode detectados em {rel_path}: {emojis}",
            )

    def test_app_language_supports_pt_br_without_english_fallback(self):
        """Valida que AppLanguage.kt e locales_config.xml suportam pt-BR sem forcar ingles."""
        app_lang_src = self._read_text(
            "android/app/src/main/kotlin/app/nectarlink/android/ui/AppLanguage.kt"
        )
        self.assertIn('"pt-BR" to "Português (Brasil)"', app_lang_src)
        self.assertIn(
            'lower == "pt" || (lower.startsWith("pt-") && lower.endsWith("-br")) -> "pt-BR"',
            app_lang_src,
        )
        self.assertNotRegex(
            app_lang_src,
            re.compile(r'else\s*->\s*"en"'),
            "AppLanguage.normalize nao pode ter fallback forcando 'en'",
        )

        locales_xml = self._read_text("android/app/src/main/res/xml/locales_config.xml")
        self.assertIn('<locale android:name="pt-BR" />', locales_xml)


if __name__ == "__main__":
    unittest.main()
