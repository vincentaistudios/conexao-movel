// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import app.nectarlink

Item {
    id: driveViewRoot
    property real driveUsedGb: 44.27
    property real driveTotalGb: 5000.0
    property string planLabel: "Google Workspace (5 TB)"
    property string activeFilter: "all"
    property string statusNotice: ""

    function formattedStorage() {
        var usedStr = driveViewRoot.driveUsedGb.toFixed(2).replace(".", ",") + " GB";
        if (driveViewRoot.driveTotalGb <= 0) return usedStr;
        var totalStr = driveViewRoot.driveTotalGb >= 1000 ? (driveViewRoot.driveTotalGb / 1000).toFixed(0) + " TB" : driveViewRoot.driveTotalGb.toFixed(0) + " GB";
        var pct = (driveViewRoot.driveUsedGb / driveViewRoot.driveTotalGb * 100).toFixed(1).replace(".", ",");
        return usedStr + " de " + totalStr + " em uso (" + pct + "%)";
    }

    readonly property var filesData: [
        {
            "name": "Dossie Clinico - Sincronizacao e Quorum.pdf",
            "type": "pdf",
            "size": "2.4 MB",
            "date": "Hoje, 10:45",
            "iconPath": Icons.fileText
        },
        {
            "name": "Planejamento Arquitetural Conexao Movel.docx",
            "type": "doc",
            "size": "1.1 MB",
            "date": "Ontem, 16:20",
            "iconPath": Icons.fileText
        },
        {
            "name": "Orcamento de Recursos e Servicos 2026.xlsx",
            "type": "sheet",
            "size": "540 KB",
            "date": "07 nov 2026",
            "iconPath": Icons.spreadsheet
        },
        {
            "name": "Apresentacao Executiva do Sistema.pptx",
            "type": "doc",
            "size": "8.2 MB",
            "date": "05 nov 2026",
            "iconPath": Icons.deck
        },
        {
            "name": "Backup P2P - Van Gogh Android 16.tar.gz",
            "type": "archive",
            "size": "1.8 GB",
            "date": "02 nov 2026",
            "iconPath": Icons.folder
        }
    ]

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

        // 1. Card de Armazenamento e Ações Globais
        Card {
            Layout.fillWidth: true
            implicitHeight: 124
            padding: 16

            ColumnLayout {
                anchors.fill: parent
                spacing: 8

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Icon { path: Icons.drive; width: 22; height: 22; color: Theme.primary }
                    ColumnLayout {
                        spacing: 2
                        Txt {
                            text: qsTr("Armazenamento da Conta Google")
                            role: "title"
                            weight: 600
                            color: Theme.surfaceContent
                        }
                        Txt {
                            text: driveViewRoot.planLabel.length > 0
                                ? qsTr("%1 - Espaco compartilhado entre Drive, Gmail e Fotos").arg(driveViewRoot.planLabel)
                                : qsTr("Espaço compartilhado entre Google Drive, Gmail e Google Fotos")
                            role: "bodySmall"
                            muted: true
                        }
                    }
                    Item { Layout.fillWidth: true }
                    Txt {
                        text: driveViewRoot.formattedStorage()
                        role: "label"
                        weight: 600
                        color: Theme.surfaceContent
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 8
                    radius: 4
                    color: Qt.rgba(1, 1, 1, Theme.dark ? 0.08 : 0.14)

                    Rectangle {
                        width: driveViewRoot.driveTotalGb > 0
                            ? Math.max(8, parent.width * Math.min(1.0, (driveViewRoot.driveUsedGb / driveViewRoot.driveTotalGb)))
                            : 8
                        height: parent.height
                        radius: 4
                        color: Theme.primary
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Button {
                        text: qsTr("Sincronizar Celular (P2P)")
                        variant: "fill"
                        size: "sm"
                        iconPath: Icons.refresh
                        onClicked: driveViewRoot.statusNotice = qsTr("Sincronizacao P2P concluida com sucesso.")
                    }
                    Button {
                        text: qsTr("Abrir Google Drive no Navegador")
                        variant: "outline"
                        size: "sm"
                        iconPath: Icons.openExternal
                        onClicked: Qt.openUrlExternally("https://drive.google.com")
                    }
                    Item { Layout.fillWidth: true }
                    Txt {
                        visible: driveViewRoot.statusNotice.length > 0
                        text: driveViewRoot.statusNotice
                        role: "caption"
                        color: Theme.primary
                    }
                }
            }
        }

        // 2. Barra de Filtros de Arquivos
        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Txt {
                text: qsTr("Arquivos Recentes:")
                role: "label"
                weight: 600
                color: Theme.surfaceContent
            }

            Button {
                text: qsTr("Todos")
                variant: driveViewRoot.activeFilter === "all" ? "fill" : "outline"
                size: "sm"
                onClicked: driveViewRoot.activeFilter = "all"
            }
            Button {
                text: qsTr("Documentos")
                variant: driveViewRoot.activeFilter === "doc" ? "fill" : "outline"
                size: "sm"
                onClicked: driveViewRoot.activeFilter = "doc"
            }
            Button {
                text: qsTr("Planilhas")
                variant: driveViewRoot.activeFilter === "sheet" ? "fill" : "outline"
                size: "sm"
                onClicked: driveViewRoot.activeFilter = "sheet"
            }
            Button {
                text: qsTr("PDFs")
                variant: driveViewRoot.activeFilter === "pdf" ? "fill" : "outline"
                size: "sm"
                onClicked: driveViewRoot.activeFilter = "pdf"
            }
            Item { Layout.fillWidth: true }
        }

        // 3. Lista Rolável de Arquivos
        ListView {
            id: fileList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 8
            model: driveViewRoot.filesData.filter(item => {
                if (driveViewRoot.activeFilter === "all") return true
                return item.type === driveViewRoot.activeFilter
            })

            delegate: Card {
                width: fileList.width
                implicitHeight: 58
                padding: 10

                RowLayout {
                    anchors.fill: parent
                    spacing: 12

                    Rectangle {
                        width: 36; height: 36; radius: 8
                        color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.12)
                        Icon {
                            anchors.centerIn: parent
                            path: modelData.iconPath
                            width: 18; height: 18
                            color: Theme.primary
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Txt {
                            text: modelData.name
                            role: "body"
                            weight: 600
                            color: Theme.surfaceContent
                            elide: Text.ElideMiddle
                        }
                        Txt {
                            text: modelData.size + " - Modificado em " + modelData.date
                            role: "caption"
                            color: Theme.surfaceContentVariant
                        }
                    }

                    Button {
                        text: qsTr("Baixar no PC")
                        variant: "outline"
                        size: "sm"
                        iconPath: Icons.download
                        onClicked: driveViewRoot.statusNotice = qsTr("Download de '%1' salvo na pasta Downloads.").arg(modelData.name)
                    }

                    Button {
                        text: qsTr("Enviar para Celular")
                        variant: "tonal"
                        size: "sm"
                        iconPath: Icons.send
                        onClicked: driveViewRoot.statusNotice = qsTr("Enviando '%1' para Van Gogh via P2P.").arg(modelData.name)
                    }
                }
            }
        }
    }
}
