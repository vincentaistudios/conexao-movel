// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import app.nectarlink

Item {
    id: welcomeRoot
    property string detectedOsEmail: ""
    property bool isConnecting: false
    signal connectRequested()

    Card {
        width: Math.min(520, parent.width - 48)
        height: 390
        anchors.centerIn: parent
        padding: 32

        ColumnLayout {
            anchors.fill: parent
            spacing: 16

            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                width: 64; height: 64; radius: 32
                color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.14)
                border.width: 1
                border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.32)

                Icon {
                    anchors.centerIn: parent
                    path: Icons.globe
                    color: Theme.primary
                    width: 30; height: 30
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                Txt {
                    Layout.fillWidth: true
                    text: qsTr("Conectar Conta Google")
                    role: "headline"
                    weight: 700
                    color: Theme.surfaceContent
                    horizontalAlignment: Text.AlignHCenter
                }
                Txt {
                    Layout.fillWidth: true
                    text: qsTr("Acesse seus e-mails do Gmail, arquivos do Google Drive e fotos diretamente pelo Conexao Movel. Sua conta e plano sao identificados automaticamente.")
                    role: "body"
                    color: Theme.surfaceContentVariant
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            Rectangle {
                visible: welcomeRoot.detectedOsEmail.length > 0
                Layout.alignment: Qt.AlignHCenter
                width: Math.min(parent.width, detectedRow.implicitWidth + 24)
                height: 30
                radius: 15
                color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.10)
                border.width: 1
                border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.25)

                RowLayout {
                    id: detectedRow
                    anchors.centerIn: parent
                    spacing: 6
                    Icon { path: Icons.shield; width: 13; height: 13; color: Theme.primary }
                    Txt {
                        text: qsTr("Sessao detectada: %1").arg(welcomeRoot.detectedOsEmail)
                        size: 12
                        weight: 500
                        color: Theme.surfaceContent
                    }
                }
            }

            Divider { Layout.fillWidth: true }

            Button {
                Layout.alignment: Qt.AlignHCenter
                width: 280
                text: welcomeRoot.isConnecting ? qsTr("Identificando conta e plano...") : qsTr("Conectar Conta Google")
                variant: "fill"
                size: "md"
                enabled: !welcomeRoot.isConnecting
                onClicked: welcomeRoot.connectRequested()
            }

            Txt {
                Layout.fillWidth: true
                text: qsTr("Nenhuma credencial e compartilhada externamente. Criptografia AES-256-GCM local.")
                role: "caption"
                muted: true
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }
}

