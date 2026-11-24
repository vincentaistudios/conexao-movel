// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import app.nectarlink

Sheet {
    id: modalRoot
    cardWidth: 560
    property string backendUrl: "http://127.0.0.1:28795"
    property string defaultEmail: "vangogh.assistente@gmail.com"
    property bool hasOauthClient: false
    property bool busy: false
    property bool showPassword: false
    property string errorText: ""

    signal connectedSuccess()

    onOpenedChanged: {
        if (opened) {
            errorText = ""
            busy = false
            emailField.text = defaultEmail
            appPassField.text = ""
        }
    }

    function submitImap() {
        var em = (emailField.text || "").trim()
        var pw = (appPassField.text || "").trim()
        if (em.length === 0 || pw.length === 0) {
            errorText = qsTr("Informe o e-mail e a Senha de App Google.")
            return
        }
        busy = true
        errorText = ""
        var xhr = new XMLHttpRequest()
        xhr.open("POST", modalRoot.backendUrl + "/google/gmail/connect-imap", true)
        xhr.setRequestHeader("Content-Type", "application/json")
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                busy = false
                try {
                    var resp = JSON.parse(xhr.responseText)
                    if (xhr.status >= 200 && xhr.status < 300 && resp.success) {
                        modalRoot.close()
                        modalRoot.connectedSuccess()
                    } else {
                        errorText = resp.error || qsTr("Nao foi possivel autenticar no Gmail IMAP.")
                    }
                } catch (e) {
                    errorText = qsTr("Erro de comunicacao com o servico local.")
                }
            }
        }
        xhr.send(JSON.stringify({"email": em, "app_password": pw}))
    }

    function startOauthBrowser() {
        busy = true
        errorText = ""
        var xhr = new XMLHttpRequest()
        xhr.open("POST", modalRoot.backendUrl + "/google/oauth/start", true)
        xhr.setRequestHeader("Content-Type", "application/json")
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                busy = false
                try {
                    var resp = JSON.parse(xhr.responseText)
                    if (xhr.status >= 200 && xhr.status < 300 && resp.success) {
                        errorText = qsTr("Navegador aberto para autorizacao. Conclua o acesso e clique em Atualizar no Gmail.")
                    } else {
                        errorText = resp.error || qsTr("Configure a credencial OAuth Desktop primeiro.")
                    }
                } catch (e) {
                    errorText = qsTr("Falha ao iniciar fluxo OAuth.")
                }
            }
        }
        xhr.send(JSON.stringify({"open_browser": true}))
    }

    Column {
        width: parent.width
        spacing: 14

        RowLayout {
            width: parent.width
            spacing: 12

            Rectangle {
                width: 40; height: 40; radius: 20
                color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.14)
                Icon { anchors.centerIn: parent; path: Icons.messages; width: 20; height: 20; color: Theme.primary }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Txt { Layout.fillWidth: true; text: qsTr("Conectar Caixa Real do Gmail"); role: "title"; weight: 600; color: Theme.surfaceContent }
                Txt { Layout.fillWidth: true; text: qsTr("Sincroniza todos os seus e-mails com criptografia AES-256-GCM local."); role: "caption"; muted: true; wrapMode: Text.WordWrap }
            }
        }

        Divider { width: parent.width }

        Txt {
            width: parent.width
            text: qsTr("Conta Google (IMAP SSL - imap.gmail.com)")
            role: "label"
            color: Theme.surfaceContent
        }

        Rectangle {
            width: parent.width
            height: 40
            radius: Theme.radiusSm
            color: Theme.graphite ? "#14161D" : Theme.surfaceContainerHighest
            border.width: 1
            border.color: emailField.activeFocus ? Theme.primary : Theme.outlineVariant

            TextInput {
                id: emailField
                anchors.fill: parent
                anchors.margins: 10
                verticalAlignment: TextInput.AlignVCenter
                color: Theme.surfaceContent
                font.pixelSize: 13
                selectByMouse: true
                clip: true
                text: modalRoot.defaultEmail
            }
        }

        RowLayout {
            width: parent.width
            Txt { text: qsTr("Senha de App Google (16 digitos)"); role: "label"; color: Theme.surfaceContent; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            Button {
                text: qsTr("Gerar Senha de App")
                variant: "text"
                size: "sm"
                iconPath: Icons.openExternal
                onClicked: Qt.openUrlExternally("https://myaccount.google.com/apppasswords")
            }
        }

        Rectangle {
            width: parent.width
            height: 40
            radius: Theme.radiusSm
            color: Theme.graphite ? "#14161D" : Theme.surfaceContainerHighest
            border.width: 1
            border.color: appPassField.activeFocus ? Theme.primary : Theme.outlineVariant

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 6
                spacing: 6

                TextInput {
                    id: appPassField
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    verticalAlignment: TextInput.AlignVCenter
                    color: Theme.surfaceContent
                    font.pixelSize: 13
                    echoMode: modalRoot.showPassword ? TextInput.Normal : TextInput.Password
                    selectByMouse: true
                    clip: true
                    onAccepted: modalRoot.submitImap()

                    Txt {
                        anchors.fill: parent
                        verticalAlignment: Text.AlignVCenter
                        visible: !appPassField.text && !appPassField.activeFocus
                        text: qsTr("xxxx xxxx xxxx xxxx")
                        muted: true
                        size: 13
                    }
                }

                Button {
                    text: modalRoot.showPassword ? qsTr("Ocultar") : qsTr("Ver")
                    variant: "text"
                    size: "sm"
                    onClicked: modalRoot.showPassword = !modalRoot.showPassword
                }
            }
        }

        Txt {
            visible: modalRoot.errorText.length > 0
            width: parent.width
            text: modalRoot.errorText
            role: "bodySmall"
            color: Theme.error
            wrapMode: Text.WordWrap
        }

        RowLayout {
            width: parent.width
            spacing: 10

            Button {
                text: qsTr("Cancelar")
                variant: "outline"
                size: "sm"
                enabled: !modalRoot.busy
                onClicked: modalRoot.close()
            }

            Item { Layout.fillWidth: true }

            Button {
                text: modalRoot.hasOauthClient ? qsTr("OAuth Navegador") : qsTr("Usar OAuth Desktop")
                variant: "tonal"
                size: "sm"
                visible: modalRoot.hasOauthClient
                enabled: !modalRoot.busy
                onClicked: modalRoot.startOauthBrowser()
            }

            Button {
                text: modalRoot.busy ? qsTr("Conectando...") : qsTr("Sincronizar E-mails")
                variant: "fill"
                size: "sm"
                enabled: !modalRoot.busy
                onClicked: modalRoot.submitImap()
            }
        }
    }
}
