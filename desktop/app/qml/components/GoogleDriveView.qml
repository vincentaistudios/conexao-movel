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
    property string currentSection: "meu_drive"
    property string searchQuery: ""
    property string activeTypeFilter: "all"
    property string statusNotice: ""
    property var selectedItemForAction: null
    property bool showNewFolderModal: false
    property bool showPreviewModal: false
    property string newFolderInputName: ""

    function formattedStorage() {
        var usedStr = driveViewRoot.driveUsedGb.toFixed(2).replace(".", ",") + " GB";
        if (driveViewRoot.driveTotalGb <= 0) return usedStr;
        var totalStr = driveViewRoot.driveTotalGb >= 1000 ? (driveViewRoot.driveTotalGb / 1000).toFixed(0) + " TB" : driveViewRoot.driveTotalGb.toFixed(0) + " GB";
        var pct = (driveViewRoot.driveUsedGb / driveViewRoot.driveTotalGb * 100).toFixed(1).replace(".", ",");
        return usedStr + " de " + totalStr + " (" + pct + "%)";
    }

    property var filesData: [
        {
            "id": "file_1",
            "name": "Dossiê Clínico - Sincronização e Quórum.pdf",
            "type": "pdf",
            "size": "2.4 MB",
            "date": "Hoje, 10:45",
            "owner": "Vincent",
            "isStarred": true,
            "section": "meu_drive",
            "color": "#ea4335",
            "iconPath": Icons.fileText
        },
        {
            "id": "file_2",
            "name": "Planejamento Arquitetural Conexão Móvel.docx",
            "type": "doc",
            "size": "1.1 MB",
            "date": "Ontem, 16:20",
            "owner": "Vincent",
            "isStarred": false,
            "section": "meu_drive",
            "color": "#4285f4",
            "iconPath": Icons.fileText
        },
        {
            "id": "file_3",
            "name": "Orçamento de Recursos e Serviços 2026.xlsx",
            "type": "sheet",
            "size": "540 KB",
            "date": "07 nov 2026",
            "owner": "Vincent",
            "isStarred": true,
            "section": "meu_drive",
            "color": "#0f9d58",
            "iconPath": Icons.spreadsheet
        },
        {
            "id": "file_4",
            "name": "Apresentação Executiva do Ecossistema.pptx",
            "type": "deck",
            "size": "8.2 MB",
            "date": "05 nov 2026",
            "owner": "Vincent",
            "isStarred": false,
            "section": "meu_drive",
            "color": "#f4b400",
            "iconPath": Icons.deck
        },
        {
            "id": "file_5",
            "name": "Backup P2P - Van Gogh Android 16.tar.gz",
            "type": "archive",
            "size": "1.8 GB",
            "date": "02 nov 2026",
            "owner": "Vincent",
            "isStarred": false,
            "section": "meu_drive",
            "color": "#70757a",
            "iconPath": Icons.folder
        },
        {
            "id": "file_6",
            "name": "Manual de Integração Google Workspace.pdf",
            "type": "pdf",
            "size": "3.5 MB",
            "date": "28 out 2026",
            "owner": "Equipe de Engenharia",
            "isStarred": true,
            "section": "compartilhados",
            "color": "#ea4335",
            "iconPath": Icons.fileText
        },
        {
            "id": "file_7",
            "name": "Rascunho Antigo de Testes.txt",
            "type": "doc",
            "size": "12 KB",
            "date": "15 out 2026",
            "owner": "Vincent",
            "isStarred": false,
            "section": "lixeira",
            "color": "#d93025",
            "iconPath": Icons.trash
        }
    ]

    function getFilteredFiles() {
        return driveViewRoot.filesData.filter(function(item) {
            if (driveViewRoot.currentSection === "com_estrela") {
                if (!item.isStarred || item.section === "lixeira") return false;
            } else if (driveViewRoot.currentSection === "recentes") {
                if (item.section === "lixeira") return false;
            } else {
                if (item.section !== driveViewRoot.currentSection) return false;
            }

            if (driveViewRoot.activeTypeFilter !== "all" && item.type !== driveViewRoot.activeTypeFilter) {
                return false;
            }

            if (driveViewRoot.searchQuery.trim().length > 0) {
                var q = driveViewRoot.searchQuery.toLowerCase();
                return item.name.toLowerCase().indexOf(q) !== -1;
            }

            return true;
        });
    }

    function toggleStar(item) {
        var updated = [];
        for (var i = 0; i < driveViewRoot.filesData.length; i++) {
            var cur = driveViewRoot.filesData[i];
            if (cur.id === item.id) {
                cur.isStarred = !cur.isStarred;
                driveViewRoot.statusNotice = cur.isStarred ? qsTr("'%1' marcado como favorito.").arg(cur.name) : qsTr("'%1' desmarcado.").arg(cur.name);
            }
            updated.push(cur);
        }
        driveViewRoot.filesData = updated;
    }

    function moveToTrash(item) {
        var updated = [];
        for (var i = 0; i < driveViewRoot.filesData.length; i++) {
            var cur = driveViewRoot.filesData[i];
            if (cur.id === item.id) {
                cur.section = "lixeira";
                driveViewRoot.statusNotice = qsTr("'%1' movido para a Lixeira.").arg(cur.name);
            }
            updated.push(cur);
        }
        driveViewRoot.filesData = updated;
    }

    function confirmNewFolder() {
        if (driveViewRoot.newFolderInputName.trim().length === 0) return;
        driveViewRoot.statusNotice = qsTr("Pasta '%1' criada com sucesso.").arg(driveViewRoot.newFolderInputName.trim());
        driveViewRoot.newFolderInputName = "";
        driveViewRoot.showNewFolderModal = false;
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        // Barra Superior de Contexto e Busca
        Card {
            Layout.fillWidth: true
            implicitHeight: 52
            padding: 8

            RowLayout {
                anchors.fill: parent
                spacing: 12

                RowLayout {
                    spacing: 8
                    Icon { path: Icons.drive; width: 22; height: 22; color: "#1a73e8" }
                    Txt {
                        text: qsTr("Google Drive")
                        role: "title"
                        weight: 600
                        color: Theme.surfaceContent
                    }
                    Txt { text: "/"; color: Theme.surfaceContentVariant }
                    Txt {
                        text: driveViewRoot.currentSection === "meu_drive" ? qsTr("Meu Drive") :
                              driveViewRoot.currentSection === "compartilhados" ? qsTr("Compartilhados comigo") :
                              driveViewRoot.currentSection === "recentes" ? qsTr("Recentes") :
                              driveViewRoot.currentSection === "com_estrela" ? qsTr("Com estrela") : qsTr("Lixeira")
                        role: "body"
                        weight: 500
                        color: Theme.primary
                    }
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    width: 280
                    height: 36
                    radius: 18
                    color: Qt.rgba(Theme.surfaceContent.r, Theme.surfaceContent.g, Theme.surfaceContent.b, Theme.dark ? 0.08 : 0.05)
                    border.color: searchInput.activeFocus ? Theme.primary : Qt.rgba(Theme.surfaceContent.r, Theme.surfaceContent.g, Theme.surfaceContent.b, 0.15)
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 6

                        Icon { path: Icons.search; width: 16; height: 16; color: Theme.surfaceContentVariant }
                        TextInput {
                            id: searchInput
                            Layout.fillWidth: true
                            text: driveViewRoot.searchQuery
                            color: Theme.surfaceContent
                            font.pixelSize: 13
                            selectByMouse: true
                            onTextChanged: driveViewRoot.searchQuery = text
                        }
                        Txt {
                            visible: driveViewRoot.searchQuery.length === 0 && !searchInput.activeFocus
                            text: qsTr("Pesquisar no Drive...")
                            role: "caption"
                            color: Theme.surfaceContentVariant
                        }
                    }
                }

                Button {
                    text: qsTr("Abrir no Navegador")
                    variant: "outline"
                    size: "sm"
                    iconPath: Icons.openExternal
                    onClicked: Qt.openUrlExternally("https://drive.google.com")
                }
            }
        }

        // Corpo: Sidebar + Conteúdo
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            GoogleDriveSidebar {
                currentSection: driveViewRoot.currentSection
                driveUsedGb: driveViewRoot.driveUsedGb
                driveTotalGb: driveViewRoot.driveTotalGb
                formattedStorage: driveViewRoot.formattedStorage()
                onSectionSelected: sectionKey => driveViewRoot.currentSection = sectionKey
                onNewFolderRequested: driveViewRoot.showNewFolderModal = true
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Txt { text: qsTr("Filtros:"); role: "caption"; weight: 600; color: Theme.surfaceContentVariant }

                    Button {
                        text: qsTr("Todos")
                        variant: driveViewRoot.activeTypeFilter === "all" ? "fill" : "outline"
                        size: "sm"
                        onClicked: driveViewRoot.activeTypeFilter = "all"
                    }
                    Button {
                        text: qsTr("Documentos")
                        variant: driveViewRoot.activeTypeFilter === "doc" ? "fill" : "outline"
                        size: "sm"
                        onClicked: driveViewRoot.activeTypeFilter = "doc"
                    }
                    Button {
                        text: qsTr("Planilhas")
                        variant: driveViewRoot.activeTypeFilter === "sheet" ? "fill" : "outline"
                        size: "sm"
                        onClicked: driveViewRoot.activeTypeFilter = "sheet"
                    }
                    Button {
                        text: qsTr("PDFs")
                        variant: driveViewRoot.activeTypeFilter === "pdf" ? "fill" : "outline"
                        size: "sm"
                        onClicked: driveViewRoot.activeTypeFilter = "pdf"
                    }
                    Button {
                        text: qsTr("Apresentações")
                        variant: driveViewRoot.activeTypeFilter === "deck" ? "fill" : "outline"
                        size: "sm"
                        onClicked: driveViewRoot.activeTypeFilter = "deck"
                    }

                    Item { Layout.fillWidth: true }

                    Txt {
                        visible: driveViewRoot.statusNotice.length > 0
                        text: driveViewRoot.statusNotice
                        role: "caption"
                        color: Theme.primary
                    }
                }

                ListView {
                    id: mainListView
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 8
                    model: driveViewRoot.getFilteredFiles()

                    delegate: GoogleDriveItemDelegate {
                        width: mainListView.width
                        itemData: modelData
                        onStarToggled: item => driveViewRoot.toggleStar(item)
                        onPreviewRequested: item => {
                            driveViewRoot.selectedItemForAction = item
                            driveViewRoot.showPreviewModal = true
                        }
                        onDownloadRequested: item => driveViewRoot.statusNotice = qsTr("Download de '%1' salvo em Downloads.").arg(item.name)
                        onP2pSendRequested: item => driveViewRoot.statusNotice = qsTr("Enviando '%1' via P2P para o celular.").arg(item.name)
                        onTrashRequested: item => driveViewRoot.moveToTrash(item)
                    }
                }
            }
        }
    }

    Dialog {
        id: newFolderDialog
        visible: driveViewRoot.showNewFolderModal
        title: qsTr("Nova Pasta")
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        modal: true

        ColumnLayout {
            spacing: 10
            Txt { text: qsTr("Nome da nova pasta:"); role: "bodySmall" }
            TextField {
                Layout.fillWidth: true
                placeholderText: qsTr("Ex.: Documentos 2026")
                onTextChanged: driveViewRoot.newFolderInputName = text
            }
        }
        onAccepted: driveViewRoot.confirmNewFolder()
        onRejected: driveViewRoot.showNewFolderModal = false
    }

    Dialog {
        id: previewDialog
        visible: driveViewRoot.showPreviewModal
        title: driveViewRoot.selectedItemForAction ? driveViewRoot.selectedItemForAction.name : qsTr("Visualizador")
        standardButtons: Dialog.Close
        anchors.centerIn: parent
        modal: true

        ColumnLayout {
            spacing: 12
            Rectangle {
                Layout.preferredWidth: 360
                Layout.preferredHeight: 180
                radius: 12
                color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.08)
                ColumnLayout {
                    anchors.centerIn: parent
                    spacing: 8
                    Icon {
                        path: driveViewRoot.selectedItemForAction ? driveViewRoot.selectedItemForAction.iconPath : Icons.fileText
                        width: 48; height: 48
                        color: driveViewRoot.selectedItemForAction ? (driveViewRoot.selectedItemForAction.color || Theme.primary) : Theme.primary
                    }
                    Txt {
                        text: driveViewRoot.selectedItemForAction ? driveViewRoot.selectedItemForAction.name : ""
                        role: "body"
                        weight: 600
                        color: Theme.surfaceContent
                    }
                    Txt {
                        text: driveViewRoot.selectedItemForAction ? qsTr("Tamanho: %1 • %2").arg(driveViewRoot.selectedItemForAction.size).arg(driveViewRoot.selectedItemForAction.date) : ""
                        role: "caption"
                        color: Theme.surfaceContentVariant
                    }
                }
            }
        }
        onClosed: driveViewRoot.showPreviewModal = false
    }
}
