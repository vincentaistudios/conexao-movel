// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import app.nectarlink

Item {
    id: inboxViewRoot
    property var emailsList: []
    property string activeFolder: "inbox" // 'inbox', 'sent', 'archived', 'trash'
    property string syncMode: "demo_offline"
    property bool hasMore: false
    property bool loading: false
    property int totalEstimated: 0
    property string searchQuery: ""

    signal emailSelected(var email)
    signal emailArchived(string emailId)
    signal emailDeleted(string emailId)
    signal folderChanged(string folder)
    signal refreshRequested(string folder, string query)
    signal loadMoreRequested()
    signal searchSubmitted(string query)
    signal connectRealGmailRequested()

    function switchFolder(folderKey) {
        inboxViewRoot.activeFolder = folderKey
        inboxViewRoot.folderChanged(folderKey)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 12

        // Faixa informativa transparente quando operando com mensagens locais
        Card {
            Layout.fillWidth: true
            implicitHeight: 54
            padding: 12
            visible: inboxViewRoot.syncMode === "demo_offline"

            RowLayout {
                anchors.fill: parent
                spacing: 10

                Icon { path: Icons.messages; width: 18; height: 18; color: Theme.warning }

                Txt {
                    Layout.fillWidth: true
                    text: qsTr("Modo demonstracao offline (apenas 3 mensagens de exemplo). Conecte sua caixa real para carregar todos os e-mails.")
                    role: "bodySmall"
                    color: Theme.surfaceContent
                    elide: Text.ElideRight
                }

                Button {
                    text: qsTr("Conectar Gmail Real")
                    variant: "fill"
                    size: "sm"
                    onClicked: inboxViewRoot.connectRealGmailRequested()
                }

                Button {
                    text: qsTr("Abrir no Navegador")
                    iconPath: Icons.openExternal
                    variant: "outline"
                    size: "sm"
                    onClicked: Qt.openUrlExternally("https://mail.google.com")
                }
            }
        }

        // Barra de pastas, busca e atualizacao
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Button {
                text: qsTr("Caixa de Entrada")
                variant: inboxViewRoot.activeFolder === "inbox" ? "fill" : "outline"
                size: "sm"
                onClicked: inboxViewRoot.switchFolder("inbox")
            }

            Button {
                text: qsTr("Enviados")
                variant: inboxViewRoot.activeFolder === "sent" ? "fill" : "outline"
                size: "sm"
                onClicked: inboxViewRoot.switchFolder("sent")
            }

            Button {
                text: qsTr("Arquivados")
                variant: inboxViewRoot.activeFolder === "archived" ? "fill" : "outline"
                size: "sm"
                onClicked: inboxViewRoot.switchFolder("archived")
            }

            Button {
                text: qsTr("Lixeira")
                variant: inboxViewRoot.activeFolder === "trash" ? "fill" : "outline"
                size: "sm"
                onClicked: inboxViewRoot.switchFolder("trash")
            }

            Item { Layout.fillWidth: true }

            // Campo de busca de mensagens
            Rectangle {
                Layout.preferredWidth: Math.min(260, Math.max(150, inboxViewRoot.width * 0.24))
                height: 32
                radius: Theme.radiusSm
                color: Theme.graphite ? "#14161D" : Theme.surfaceContainerHighest
                border.width: 1
                border.color: searchField.activeFocus ? Theme.primary : Theme.outlineVariant

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 6
                    spacing: 6

                    Icon { path: Icons.search; width: 14; height: 14; color: Theme.surfaceContentVariant }

                    TextInput {
                        id: searchField
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        verticalAlignment: TextInput.AlignVCenter
                        color: Theme.surfaceContent
                        font.pixelSize: 12
                        selectByMouse: true
                        clip: true
                        onAccepted: inboxViewRoot.searchSubmitted(text.trim())

                        Txt {
                            anchors.fill: parent
                            verticalAlignment: Text.AlignVCenter
                            visible: !searchField.text && !searchField.activeFocus
                            text: qsTr("Buscar e-mails...")
                            muted: true
                            size: 12
                        }
                    }

                    MouseArea {
                        width: 16; height: 16
                        visible: searchField.text.length > 0
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            searchField.text = ""
                            inboxViewRoot.searchSubmitted("")
                        }
                        Txt { anchors.centerIn: parent; text: "x"; size: 12; muted: true }
                    }
                }
            }

            Button {
                text: inboxViewRoot.loading ? qsTr("Sincronizando...") : qsTr("Atualizar")
                iconPath: Icons.refresh
                variant: "tonal"
                size: "sm"
                enabled: !inboxViewRoot.loading
                onClicked: inboxViewRoot.refreshRequested(inboxViewRoot.activeFolder, searchField.text.trim())
            }
        }

        // Indicador discreto de contagem real quando sincronizado via API/IMAP
        RowLayout {
            Layout.fillWidth: true
            visible: inboxViewRoot.syncMode !== "demo_offline"
            spacing: 8

            Txt {
                text: qsTr("Exibindo %1 de %2 e-mails nesta pasta").arg(inboxViewRoot.emailsList.length).arg(Math.max(inboxViewRoot.totalEstimated, inboxViewRoot.emailsList.length))
                role: "caption"
                muted: true
            }
            Item { Layout.fillWidth: true }
            Txt {
                text: inboxViewRoot.syncMode === "gmail_api" ? qsTr("Sincronizado via Gmail API v1") : qsTr("Sincronizado via IMAP SSL")
                role: "caption"
                color: Theme.primary
            }
        }

        // Estado vazio
        Card {
            Layout.fillWidth: true
            implicitHeight: 120
            visible: !inboxViewRoot.loading && (!inboxViewRoot.emailsList || inboxViewRoot.emailsList.length === 0)
            padding: 24

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 8
                Txt {
                    text: qsTr("Nenhuma mensagem encontrada nesta pasta.")
                    role: "body"
                    color: Theme.surfaceContent
                    Layout.alignment: Qt.AlignHCenter
                }
                Txt {
                    text: qsTr("Use a pesquisa ou clique em Atualizar para verificar novas mensagens.")
                    role: "caption"
                    muted: true
                    Layout.alignment: Qt.AlignHCenter
                }
            }
        }

        // Lista virtualizada (suporta milhares de e-mails sem saturar memoria)
        ListView {
            id: mailListView
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: inboxViewRoot.emailsList && inboxViewRoot.emailsList.length > 0
            clip: true
            spacing: 8
            model: inboxViewRoot.emailsList

            delegate: Card {
                id: emailCard
                width: mailListView.width
                implicitHeight: 86
                padding: 14

                readonly property var emailItem: modelData
                readonly property bool unread: !!emailItem.is_unread

                Rectangle {
                    anchors.fill: parent
                    color: emailMouse.containsMouse
                        ? Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.08)
                        : "transparent"
                    radius: Theme.radiusLg
                    Behavior on color { ColorAnimation { duration: 150 } }
                }

                RowLayout {
                    anchors.fill: parent
                    spacing: 14

                    Rectangle {
                        width: 8; height: 8; radius: 4
                        color: Theme.primary
                        visible: emailCard.unread
                    }

                    Avatar {
                        width: 36; height: 36
                        name: emailCard.emailItem.sender || "G"
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        RowLayout {
                            Layout.fillWidth: true
                            Txt {
                                text: emailCard.emailItem.sender || ""
                                role: "body"
                                weight: emailCard.unread ? 700 : 500
                                color: Theme.surfaceContent
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Txt {
                                text: emailCard.emailItem.date || ""
                                role: "caption"
                                muted: true
                            }
                        }

                        Txt {
                            text: emailCard.emailItem.subject || ""
                            role: "bodySmall"
                            weight: emailCard.unread ? 600 : 400
                            color: Theme.surfaceContent
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }

                        Txt {
                            text: emailCard.emailItem.snippet || ""
                            role: "caption"
                            muted: true
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }

                    RowLayout {
                        spacing: 6
                        visible: emailMouse.containsMouse

                        Button {
                            iconPath: Icons.folder
                            variant: "tonal"
                            size: "sm"
                            onClicked: inboxViewRoot.emailArchived(emailCard.emailItem.id)
                        }

                        Button {
                            iconPath: Icons.trash
                            variant: "outline"
                            size: "sm"
                            onClicked: inboxViewRoot.emailDeleted(emailCard.emailItem.id)
                        }
                    }
                }

                MouseArea {
                    id: emailMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: inboxViewRoot.emailSelected(emailCard.emailItem)
                }
            }

            footer: Item {
                width: mailListView.width
                height: inboxViewRoot.hasMore ? 56 : 8

                Button {
                    anchors.centerIn: parent
                    visible: inboxViewRoot.hasMore
                    text: inboxViewRoot.loading ? qsTr("Carregando mais...") : qsTr("Carregar mais e-mails")
                    variant: "outline"
                    size: "sm"
                    enabled: !inboxViewRoot.loading
                    onClicked: inboxViewRoot.loadMoreRequested()
                }
            }
        }
    }
}
