import os
import subprocess
import unittest

class TestMobileConnectNativeIntegration(unittest.TestCase):
    def test_binaries_installed(self):
        self.assertTrue(os.path.exists("/usr/bin/nectarlink-desktop"), "Binario oficial deve existir")
        self.assertTrue(os.path.islink("/usr/local/bin/sys-device-link"), "Symlink de compatibilidade deve existir")
        target = os.readlink("/usr/local/bin/sys-device-link")
        self.assertEqual(target, "/usr/bin/nectarlink-desktop")

    def test_desktop_file_and_icon(self):
        desktop_path = "/usr/share/applications/sys-device-link.desktop"
        self.assertTrue(os.path.exists(desktop_path), "Atalho desktop deve existir")
        with open(desktop_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Name=Conexão Móvel", content)
        self.assertIn("Icon=sys-device-link", content)

    def test_flaticon_icons_installed(self):
        for name in ["sys-device-link.svg", "nectarlink.svg", "nectarlink-desktop.svg"]:
            path = f"/usr/share/icons/hicolor/scalable/apps/{name}"
            self.assertTrue(os.path.exists(path), f"Icone {name} deve existir no tema de icones")
        for size in ["512x512", "256x256", "48x48"]:
            path = f"/usr/share/icons/hicolor/{size}/apps/sys-device-link.png"
            self.assertTrue(os.path.exists(path), f"PNG {size} de sys-device-link deve existir")

    def test_apk_available(self):
        apk_path = "/home/Vincent/Downloads/Compartilhar-com-Amigos/1 - Celular (Android)/ConexaoMovel.apk"
        self.assertTrue(os.path.exists(apk_path), "APK para instalacao no smartphone deve estar na pasta de distribuicao")
        self.assertGreater(os.path.getsize(apk_path), 40 * 1024 * 1024)

    def test_distribution_package_structure(self):
        base_dir = "/home/Vincent/Downloads/Compartilhar-com-Amigos"
        self.assertTrue(os.path.isdir(base_dir), "Pasta de compartilhamento deve existir")
        self.assertTrue(os.path.isfile(os.path.join(base_dir, "COMO-INSTALAR.txt")), "Guia de instalacao deve existir")
        self.assertTrue(os.path.isfile(os.path.join(base_dir, "2 - Computador (Windows)/Instalador-Windows.exe")), "Instalador Windows deve existir")
        self.assertTrue(os.path.isfile(os.path.join(base_dir, "3 - Computador (Linux)/Instalador-Linux-Ubuntu-Debian.deb")), "Instalador Linux deb deve existir")

    def test_legacy_daemon_stopped(self):
        cmd = ["pgrep", "-f", "sys-device-link-daemon"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE)
        self.assertNotEqual(res.returncode, 0, "O daemon Python legado nao deve estar em execucao")

    def test_flaticon_mark_and_qml_branding(self):
        main_qml = "/usr/lib/nectarlink/qml/MainWindow.qml"
        with open(main_qml, "r", encoding="utf-8") as f:
            qml = f.read()
        self.assertIn('title: "Conexão Móvel"', qml, "O titulo da janela principal deve ser Conexao Movel")
        self.assertTrue(
            'file:///usr/share/icons/hicolor/scalable/apps/sys-device-link.svg' in qml or
            'file:///usr/share/icons/hicolor/scalable/apps/nectarlink.svg' in qml,
            "O icone SVG oficial deve ser referenciado em MainWindow.qml"
        )

        icons_qml = "/usr/lib/nectarlink/qml/Icons.qml"
        with open(icons_qml, "r", encoding="utf-8") as f:
            icons = f.read()
        self.assertNotIn("M9.39 11.23C4.14", icons, "O caminho waggle dance antigo nao deve mais existir em Icons.qml")

if __name__ == "__main__":
    unittest.main()
