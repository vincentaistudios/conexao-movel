#!/usr/bin/env python3
"""
Modulo de testes unitarios para a aba de Servicos Google (Gmail, Drive, Fotos, P2P)
e integracao da identidade visual do usuario Van Gogh no Conexao Movel.
"""

import os
import unittest


class TestGoogleServicesPage(unittest.TestCase):
    """Bateria de testes para assegurar integridade dos componentes Google."""

    QML_DIR = "/usr/lib/nectarlink/qml"
    AVATAR_PATH = "/usr/share/icons/hicolor/scalable/apps/google-user-avatar.png"

    def test_avatar_asset_exists(self):
        """Valida que o asset de foto oficial do Van Gogh existe e tem dados."""
        self.assertTrue(os.path.isfile(self.AVATAR_PATH), "Avatar oficial Van Gogh ausente")
        self.assertGreater(os.path.getsize(self.AVATAR_PATH), 1024, "Arquivo de avatar corrompido ou vazio")

    def test_google_services_page_structure(self):
        """Valida o componente principal GoogleServicesPage.qml."""
        page_path = os.path.join(self.QML_DIR, "pages", "GoogleServicesPage.qml")
        self.assertTrue(os.path.isfile(page_path), "GoogleServicesPage.qml ausente")

        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("userAvatarUrl", content, "Propriedade userAvatarUrl ausente")
        self.assertIn("google-user-avatar.png", content, "Referencia ao avatar local ausente")
        self.assertIn("isAuthenticated: true", content, "Estado padrao autenticado ausente")
        self.assertIn("vangogh.assistente@gmail.com", content, "Identificador da conta Google autenticada ausente")
        self.assertIn("RoundedImage", content, "Componente RoundedImage ausente no cabecalho Google")
        self.assertIn("GoogleAuxiliaryViews", content, "Integracao de abas auxiliares ausente")
        self.assertIn("/google/connect-auto", content, "Chamada automatica /google/connect-auto ausente")
        self.assertIn("/google/status", content, "Sincronizacao HTTP /google/status ausente")
        self.assertIn("planLabel", content, "Propriedade automatica planLabel ausente")

    def test_no_manual_plan_selection_choices(self):
        """Garante que nao ha escolha manual de plano (5 TB vs 15 GB) nem perfis ficticios no QML."""
        page_path = os.path.join(self.QML_DIR, "pages", "GoogleServicesPage.qml")
        with open(page_path, "r", encoding="utf-8") as f:
            content = f.read()

        forbidden_strings = [
            "Conectar Conta Corporativa",
            "Conectar Conta Pessoal",
            "usuario.pessoal@gmail.com",
            "Alternar Conta",
        ]
        for forbidden in forbidden_strings:
            self.assertNotIn(
                forbidden,
                content,
                f"Escolha manual de plano ou perfil ficticio nao deve existir: '{forbidden}'",
            )

    def test_google_drive_view_component(self):
        """Valida o componente GoogleDriveView.qml e sua lista de arquivos."""
        drive_path = os.path.join(self.QML_DIR, "components", "GoogleDriveView.qml")
        self.assertTrue(os.path.isfile(drive_path), "GoogleDriveView.qml ausente")

        with open(drive_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("filesData", content, "Modelo de arquivos do Drive ausente")
        self.assertIn("Dossie Clinico", content, "Documento de teste ausente no Drive")
        self.assertIn("activeFilter", content, "Filtro de tipos de arquivo ausente")
        self.assertIn("driveUsedGb", content, "Medidor de armazenamento ausente")

    def test_google_photos_view_component(self):
        """Valida o componente GooglePhotosView.qml e o grid de fotografias."""
        photos_path = os.path.join(self.QML_DIR, "components", "GooglePhotosView.qml")
        self.assertTrue(os.path.isfile(photos_path), "GooglePhotosView.qml ausente")

        with open(photos_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("photosData", content, "Modelo de fotografias ausente")
        self.assertIn("/usr/share/backgrounds/DESERT-v1.jpg", content, "Foto de alta definicao ausente")
        self.assertIn("activeAlbum", content, "Filtro de albuns ausente")
        self.assertIn("GridView", content, "Grade de miniaturas ausente")

    def test_gmail_inbox_virtualized_and_connect_modal(self):
        """Valida lista virtualizada ListView, paginacao, busca e modal de conexao real."""
        inbox_path = os.path.join(self.QML_DIR, "components", "GmailInboxView.qml")
        modal_path = os.path.join(self.QML_DIR, "components", "GmailConnectModal.qml")
        welcome_path = os.path.join(self.QML_DIR, "components", "GoogleConnectWelcomeView.qml")
        for p in (inbox_path, modal_path, welcome_path):
            self.assertTrue(os.path.isfile(p), f"Componente ausente: {p}")

        inbox_src = open(inbox_path, "r", encoding="utf-8").read()
        self.assertIn("ListView", inbox_src, "ListView virtualizada ausente em GmailInboxView.qml")
        self.assertIn("Carregar mais e-mails", inbox_src, "Botao de paginacao ausente")
        self.assertIn("Enviados", inbox_src, "Pasta Enviados ausente")
        self.assertIn("Conectar Gmail Real", inbox_src, "Acao de autorizacao real ausente")

        modal_src = open(modal_path, "r", encoding="utf-8").read()
        self.assertIn("/google/gmail/connect-imap", modal_src, "Rota IMAP ausente no modal")
        self.assertIn("/google/oauth/start", modal_src, "Rota OAuth ausente no modal")

    def test_no_emojis_in_google_qml(self):
        """Garante conformidade com a diretriz mandatoria de zero emojis."""
        files = [
            os.path.join(self.QML_DIR, "pages", "GoogleServicesPage.qml"),
            os.path.join(self.QML_DIR, "components", "GoogleDriveView.qml"),
            os.path.join(self.QML_DIR, "components", "GooglePhotosView.qml"),
            os.path.join(self.QML_DIR, "components", "GoogleAuxiliaryViews.qml"),
            os.path.join(self.QML_DIR, "components", "GmailInboxView.qml"),
            os.path.join(self.QML_DIR, "components", "GmailConnectModal.qml"),
            os.path.join(self.QML_DIR, "components", "GoogleConnectWelcomeView.qml"),
        ]
        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            for char in content:
                code = ord(char)
                self.assertFalse(
                    (0x1F600 <= code <= 0x1F64F) or (0x1F300 <= code <= 0x1F5FF) or
                    (0x1F680 <= code <= 0x1F6FF) or (0x1F900 <= code <= 0x1F9FF) or
                    (0x2600 <= code <= 0x26FF) or (0x2700 <= code <= 0x27BF),
                    f"Emoji detectado no arquivo {fpath}: char {char} (U+{code:04X})"
                )


if __name__ == "__main__":
    unittest.main()

