// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import app.nectarlink

Item {
    id: readerRoot
    property var emailData: null

    signal backRequested()
    signal archiveRequested(string emailId)
    signal deleteRequested(string emailId)
    signal toggleUnreadRequested(string emailId)

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        // Barra Superior de Navegação e Ações
        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Button {
                text: "Voltar para Lista"
                iconPath: Icons.back
                variant: "outline"
                size: "sm"
                onClicked: readerRoot.backRequested()
            }

            Item { Layout.fillWidth: true }

            Button {
                text: "Arquivar"
                iconPath: Icons.folder
                variant: "tonal"
                size: "sm"
                onClicked: {
                    if (readerRoot.emailData)
                        readerRoot.archiveRequested(readerRoot.emailData.id)
                }
            }

            Button {
                text: "Excluir"
                iconPath: Icons.trash
                variant: "outline"
                size: "sm"
                onClicked: {
                    if (readerRoot.emailData)
                        readerRoot.deleteRequested(readerRoot.emailData.id)
                }
            }
        }

        // Card com Conteúdo da Mensagem
        Card {
            Layout.fillWidth: true
            Layout.fillHeight: true
            padding: 24

            ColumnLayout {
                anchors.fill: parent
                spacing: 16

                // Assunto
                Txt {
                    Layout.fillWidth: true
                    text: readerRoot.emailData ? readerRoot.emailData.subject : ""
                    role: "headline"
                    weight: 700
                    color: Theme.surfaceContent
                    wrapMode: Text.WordWrap
                }

                // Metadados do Remetente
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Avatar {
                        width: 40
                        height: 40
                        name: readerRoot.emailData ? readerRoot.emailData.sender : ""
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        RowLayout {
                            spacing: 8
                            Txt {
                                text: readerRoot.emailData ? readerRoot.emailData.sender : ""
                                role: "body"
                                weight: 600
                                color: Theme.surfaceContent
                            }
                            Txt {
                                text: "<" + (readerRoot.emailData ? readerRoot.emailData.sender_email : "") + ">"
                                role: "bodySmall"
                                muted: true
                            }
                        }

                        Txt {
                            text: "Enviado em: " + (readerRoot.emailData ? readerRoot.emailData.date : "")
                            role: "caption"
                            muted: true
                        }
                    }
                }

                Divider {
                    Layout.fillWidth: true
                }

                // Corpo do E-mail com Rolagem Suave
                Flickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: bodyText.implicitHeight + 20
                    clip: true

                    Txt {
                        id: bodyText
                        width: parent.width
                        text: readerRoot.emailData ? readerRoot.emailData.body : ""
                        role: "body"
                        color: Theme.surfaceContent
                        wrapMode: Text.WordWrap
                        lineHeightMode: Text.ProportionalHeight
                        lineHeight: 1.4
                    }
                }
            }
        }
    }
}
