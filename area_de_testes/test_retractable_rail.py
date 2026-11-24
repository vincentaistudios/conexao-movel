#!/usr/bin/env python3
"""
Modulo de testes unitarios para validacao do menu lateral retratil
e do botao de avatar Google na barra superior em MainWindow.qml.
"""

import os
import unittest


class TestRetractableRailAndTopAvatar(unittest.TestCase):
    """Bateria de testes para assegurar mecanica do menu retratil e avatar superior."""

    MAIN_WINDOW = "/usr/lib/nectarlink/qml/MainWindow.qml"

    def test_rail_collapsed_property_declared(self):
        """Valida que MainWindow.qml declara a propriedade booleana railCollapsed."""
        with open(self.MAIN_WINDOW, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("property bool railCollapsed: false", content, "Propriedade railCollapsed ausente")

    def test_toggle_rail_button_present(self):
        """Valida a presenca do botao toggleRailBtn na barra superior."""
        with open(self.MAIN_WINDOW, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("id: toggleRailBtn", content, "Botao toggleRailBtn ausente")
        self.assertIn("Icons.menu", content, "Icone Icons.menu ausente")
        self.assertIn("Icons.sidebar", content, "Icone Icons.sidebar ausente")
        self.assertIn("window.railCollapsed = !window.railCollapsed", content, "Acao de alternar rail ausente")

    def test_rail_width_animation_configured(self):
        """Valida que o rail possui animacao de transicao de largura e opacidade."""
        with open(self.MAIN_WINDOW, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("width: window.railCollapsed ? 0 : Theme.railWidth", content, "Largura dinamica ausente")
        self.assertIn("opacity: window.railCollapsed ? 0 : 1", content, "Opacidade dinamica ausente")

    def test_google_avatar_top_button_present(self):
        """Valida a presenca do botao circular com foto do Google na barra superior sem efeito online."""
        with open(self.MAIN_WINDOW, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("id: googleAvatarTopBtn", content, "Botao googleAvatarTopBtn ausente")
        self.assertIn("google-user-avatar.png", content, "Foto de avatar ausente no botao do topo")
        self.assertIn("window.page = \"google\"", content, "Clique para abrir aba google ausente")
        self.assertIn("RoundedImage", content, "Componente RoundedImage ausente no avatar do topo")
        # Garante que o indicador verde de online foi totalmente removido
        btn_block = content[content.find("googleAvatarTopBtn"):content.find("googleAvatarTopBtn") + 800]
        self.assertNotIn("#22c55e", btn_block, "Indicador verde de online deve ser removido")

    def test_page_title_google_services_mapping(self):
        """Valida que o titulo exibe 'Servicos Google' quando a aba google estiver ativa."""
        with open(self.MAIN_WINDOW, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("window.page === \"google\" ? qsTr(\"Serviços Google\")", content, "Mapeamento de titulo ausente")

    def test_no_emojis_in_main_window(self):
        """Garante conformidade com a regra de zero emojis em MainWindow.qml."""
        with open(self.MAIN_WINDOW, "r", encoding="utf-8") as f:
            content = f.read()
        for char in content:
            code = ord(char)
            self.assertFalse(
                (0x1F600 <= code <= 0x1F64F) or (0x1F300 <= code <= 0x1F5FF) or
                (0x1F680 <= code <= 0x1F6FF) or (0x1F900 <= code <= 0x1F9FF) or
                (0x2600 <= code <= 0x26FF) or (0x2700 <= code <= 0x27BF),
                f"Emoji detectado em MainWindow.qml: char {char} (U+{code:04X})"
            )


if __name__ == "__main__":
    unittest.main()

