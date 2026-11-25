// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import app.nectarlink

Card {
    id: sidebarRoot
    property string currentSection: "meu_drive"
    property real driveUsedGb: 44.27
    property real driveTotalGb: 5000.0
    property string formattedStorage: ""

    signal sectionSelected(string sectionKey)
    signal newFolderRequested()

    Layout.preferredWidth: 210
    Layout.fillHeight: true
    padding: 10

    ColumnLayout {
        anchors.fill: parent
        spacing: 6

        Button {
            Layout.fillWidth: true
            text: qsTr("+ Novo")
            variant: "fill"
            size: "md"
            iconPath: Icons.plus
            onClicked: sidebarRoot.newFolderRequested()
        }

        Item { height: 6 }

        Component {
            id: navItemComp
            Rectangle {
                required property string sectionKey
                required property string label
                required property string icon

                Layout.fillWidth: true
                height: 38
                radius: 19
                color: sidebarRoot.currentSection === sectionKey ? Qt.rgba(0.102, 0.451, 0.910, 0.14) : (navMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.05) : "transparent")

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    Icon {
                        path: icon
                        width: 18; height: 18
                        color: sidebarRoot.currentSection === sectionKey ? "#1a73e8" : Theme.surfaceContentVariant
                    }
                    Txt {
                        Layout.fillWidth: true
                        text: label
                        role: "bodySmall"
                        weight: sidebarRoot.currentSection === sectionKey ? 600 : 400
                        color: sidebarRoot.currentSection === sectionKey ? "#1a73e8" : Theme.surfaceContent
                    }
                }

                MouseArea {
                    id: navMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: sidebarRoot.sectionSelected(sectionKey)
                }
            }
        }

        Loader {
            Layout.fillWidth: true
            sourceComponent: navItemComp
            property string sectionKey: "meu_drive"
            property string label: qsTr("Meu Drive")
            property string icon: Icons.drive
        }
        Loader {
            Layout.fillWidth: true
            sourceComponent: navItemComp
            property string sectionKey: "compartilhados"
            property string label: qsTr("Compartilhados")
            property string icon: Icons.share
        }
        Loader {
            Layout.fillWidth: true
            sourceComponent: navItemComp
            property string sectionKey: "recentes"
            property string label: qsTr("Recentes")
            property string icon: Icons.history
        }
        Loader {
            Layout.fillWidth: true
            sourceComponent: navItemComp
            property string sectionKey: "com_estrela"
            property string label: qsTr("Com estrela")
            property string icon: Icons.star
        }
        Loader {
            Layout.fillWidth: true
            sourceComponent: navItemComp
            property string sectionKey: "lixeira"
            property string label: qsTr("Lixeira")
            property string icon: Icons.trash
        }

        Item { Layout.fillHeight: true }

        Divider { Layout.fillWidth: true }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            RowLayout {
                Layout.fillWidth: true
                Icon { path: Icons.drive; width: 14; height: 14; color: Theme.primary }
                Txt { text: qsTr("Armazenamento"); role: "caption"; weight: 600; color: Theme.surfaceContent }
            }
            Rectangle {
                Layout.fillWidth: true
                height: 6
                radius: 3
                color: Qt.rgba(Theme.surfaceContent.r, Theme.surfaceContent.g, Theme.surfaceContent.b, 0.1)
                Rectangle {
                    width: Math.max(6, parent.width * Math.min(1.0, (sidebarRoot.driveUsedGb / sidebarRoot.driveTotalGb)))
                    height: parent.height
                    radius: 3
                    color: "#1a73e8"
                }
            }
            Txt {
                text: sidebarRoot.formattedStorage
                role: "caption"
                color: Theme.surfaceContentVariant
            }
        }
    }
}
