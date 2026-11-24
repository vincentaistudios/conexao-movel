#!/usr/bin/env python3
"""
Modulo de testes unitarios para validacao da matriz de icones e identidade visual
do aplicativo Conexao Movel (Logotipo V oficial do sistema operacional).
"""

import os
import unittest
from PIL import Image


class TestIconAssets(unittest.TestCase):
    """Bateria de testes para assegurar presenca e conformidade dos icones visuais."""

    RESOLUTIONS = [16, 24, 32, 48, 64, 96, 128, 256, 512]
    ICON_NAMES = ["sys-device-link", "nectarlink", "nectarlink-desktop"]

    def test_system_png_icons_exist_and_valid(self):
        """Valida que todos os icones PNG do sistema existem nas dimensoes exatas."""
        base_dir = "/usr/share/icons/hicolor"
        for size in self.RESOLUTIONS:
            size_dir = os.path.join(base_dir, f"{size}x{size}", "apps")
            self.assertTrue(
                os.path.isdir(size_dir),
                f"Diretorio de resolucao {size}x{size} ausente: {size_dir}"
            )
            for name in self.ICON_NAMES:
                icon_path = os.path.join(size_dir, f"{name}.png")
                self.assertTrue(
                    os.path.isfile(icon_path),
                    f"Icone ausente no sistema: {icon_path}"
                )
                with Image.open(icon_path) as img:
                    self.assertEqual(
                        img.size, (size, size),
                        f"Dimensoes incorretas em {icon_path}: esperava {(size, size)}, obteve {img.size}"
                    )
                    self.assertIn(
                        img.mode, ["RGBA", "RGB"],
                        f"Modo de cor invalido em {icon_path}: {img.mode}"
                    )

    def test_local_user_png_icons_exist(self):
        """Valida que os icones de usuario existem no diretorio ~/.local/share/icons."""
        home = os.path.expanduser("~")
        base_dir = os.path.join(home, ".local", "share", "icons", "hicolor")
        for size in self.RESOLUTIONS:
            for name in self.ICON_NAMES:
                icon_path = os.path.join(base_dir, f"{size}x{size}", "apps", f"{name}.png")
                self.assertTrue(
                    os.path.isfile(icon_path),
                    f"Icone de usuario ausente: {icon_path}"
                )

    def test_scalable_svg_icons_exist(self):
        """Valida a presenca dos vetores SVG escalaveis no sistema e no usuario."""
        sys_svg = "/usr/share/icons/hicolor/scalable/apps/sys-device-link.svg"
        usr_svg = os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps/sys-device-link.svg")
        self.assertTrue(os.path.isfile(sys_svg), f"Vetor SVG do sistema ausente: {sys_svg}")
        self.assertTrue(os.path.isfile(usr_svg), f"Vetor SVG de usuario ausente: {usr_svg}")

        with open(sys_svg, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("<svg", content, "Conteudo de sys-device-link.svg nao e um SVG valido")
            self.assertIn("vLeftGrad", content, "sys-device-link.svg nao contem o gradiente do monograma V")

    def test_tray_icon_locked_and_32px(self):
        """Valida que o icone de bandeja em /run/user/1000 existe e esta blindado (444)."""
        uid = os.getuid()
        tray_icon = f"/run/user/{uid}/nectarlink/tray-icon.png"
        self.assertTrue(
            os.path.isfile(tray_icon),
            f"Icone de bandeja ausente em {tray_icon}"
        )
        with Image.open(tray_icon) as img:
            self.assertEqual(img.size, (32, 32), "Icone de bandeja deve ter 32x32 pixels")

        # Verificar permissao 444
        mode = oct(os.stat(tray_icon).st_mode)[-3:]
        self.assertEqual(
            mode, "444",
            f"Permissoes de {tray_icon} devem ser estritamente 444 (somente leitura), obteve {mode}"
        )

    def test_local_cache_icon_updated(self):
        """Valida que o arquivo de cache da aplicacao foi devidamente atualizado com o logotipo V."""
        cache_icon = os.path.expanduser("~/.local/share/nectarlink/cache/nectarlink.png")
        self.assertTrue(os.path.isfile(cache_icon), f"Cache de icone ausente: {cache_icon}")
        with Image.open(cache_icon) as img:
            self.assertEqual(img.size, (256, 256), "Cache de icone deve ter 256x256 pixels")

    def test_tray_icon_palette_matches_v_monogram(self):
        """Valida os pixels reais de tray-icon.png contra a nova paleta do monograma V."""
        uid = os.getuid()
        tray_icon = f"/run/user/{uid}/nectarlink/tray-icon.png"
        if not os.path.isfile(tray_icon):
            self.skipTest(f"Icone de bandeja ausente no runtime: {tray_icon}")

        with Image.open(tray_icon) as img:
            rgba = img.convert("RGBA")
            w, h = rgba.size
            cx, cy = w // 2, h // 2
            cr, cg, cb, ca = rgba.getpixel((cx, cy))

            self.assertGreater(ca, 0, f"Pixel central de {tray_icon} nao pode ser totalmente transparente")
            self.assertFalse(
                cr > 230 and 155 <= cg <= 215 and cb < 120,
                f"Pixel central de {tray_icon} usa dourado antigo: {(cr, cg, cb)}",
            )
            self.assertFalse(
                abs(cr - 44) <= 4 and abs(cg - 22) <= 4 and cb <= 8,
                f"Pixel central de {tray_icon} usa tile marrom antigo (44, 22, 0): {(cr, cg, cb)}",
            )

            palette_targets = (
                (15, 23, 42),     # #0F172A
                (3, 7, 18),       # #030712
                (56, 189, 248),   # #38BDF8
                (255, 255, 255),  # #FFFFFF
            )
            has_new_palette = False
            for y in range(h):
                for x in range(w):
                    r, g, b, a = rgba.getpixel((x, y))
                    if a < 128:
                        continue
                    for tr, tg, tb in palette_targets:
                        if abs(r - tr) <= 40 and abs(g - tg) <= 40 and abs(b - tb) <= 40:
                            has_new_palette = True
                            break
                    if has_new_palette:
                        break
                if has_new_palette:
                    break

            self.assertTrue(
                has_new_palette,
                f"Nenhum pixel de {tray_icon} corresponde a nova paleta (#0F172A/#030712/#38BDF8/#FFFFFF); centro={(cr, cg, cb, ca)}",
            )


if __name__ == "__main__":
    unittest.main()

