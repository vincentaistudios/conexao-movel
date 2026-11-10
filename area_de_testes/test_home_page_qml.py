"""
Testes de validacao da interface grafica QML (HomePage.qml) para os
paineis expansiveis de Wi-Fi e Bluetooth nos Controles do Celular.
"""

import unittest
import os
import unicodedata

class TestHomePageQml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.qml_path = os.path.join(base_dir, "desktop", "app", "qml", "pages", "HomePage.qml")
        with open(cls.qml_path, "r", encoding="utf-8") as f:
            cls.content = f.read()

    def test_file_exists(self):
        self.assertTrue(os.path.isfile(self.qml_path))

    def test_zero_emojis(self):
        """Verifica conformidade estrita com a regra mandatoria de ZERO emojis."""
        emojis = []
        for line_no, line in enumerate(self.content.splitlines(), 1):
            for ch in line:
                code = ord(ch)
                if (0x1F300 <= code <= 0x1FAFF) or (0x2600 <= code <= 0x27BF) or (0xFE00 <= code <= 0xFE0F) or (0x1F900 <= code <= 0x1F9FF):
                    emojis.append((line_no, ch, f"U+{code:04X}"))
        self.assertEqual(len(emojis), 0, f"Emojis encontrados: {emojis}")

    def test_quick_toggle_button_enhancements(self):
        """Verifica se o QuickToggleButton suporta subtitle, expandable, expanded e expandClicked."""
        self.assertIn("property string subtitle:", self.content)
        self.assertIn("property bool expandable: false", self.content)
        self.assertIn("property bool expanded: false", self.content)
        self.assertIn("signal expandClicked", self.content)
        self.assertIn("id: qexpandArea", self.content)

    def test_wifi_toggle_button_features(self):
        """Verifica aprimoramentos no botao de Wi-Fi: sub-rotulo e expansibilidade."""
        self.assertIn("shortTitle: qsTr(\"Wi‑Fi\")", self.content)
        self.assertIn("phoneControls.wifiPanelExpanded", self.content)
        self.assertIn("phoneControls.currentWifiSsid", self.content)

    def test_bluetooth_toggle_button_features(self):
        """Verifica aprimoramentos no botao de Bluetooth: sub-rotulo e expansibilidade."""
        self.assertIn("shortTitle: qsTr(\"BT\")", self.content)
        self.assertIn("phoneControls.btPanelExpanded", self.content)
        self.assertIn("phoneControls.connectedBtDeviceName", self.content)

    def test_wifi_panel_presence_and_actions(self):
        """Verifica painel expansivel de Wi-Fi, busca de redes e sinal."""
        self.assertIn("id: wifiPanel", self.content)
        self.assertIn("AppController.setPhoneToggle(home.deviceId, \"wifi_scan\", \"true\")", self.content)
        self.assertIn("phoneControls.wifiNetworksList", self.content)
        self.assertIn("wifi_connect", self.content)

    def test_bluetooth_panel_presence_and_actions(self):
        """Verifica painel expansivel de Bluetooth, chave de ligar/desligar e conexao."""
        self.assertIn("id: btPanel", self.content)
        self.assertIn("phoneControls.btDevicesList", self.content)
        self.assertIn("bt_connect", self.content)
        self.assertIn("bt_disconnect", self.content)
        self.assertIn("btCategoryIcon", self.content)

    def test_preventive_wifi_dialog_preserved(self):
        """Verifica se o dialogo preventivo de desligamento de Wi-Fi foi preservado."""
        self.assertIn("confirmWifiOff", self.content)
        self.assertIn("Turning off Wi‑Fi may disconnect %1.", self.content)

if __name__ == "__main__":
    unittest.main()
