// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import app.nectarlink

Card {
    id: itemCard
    property var itemData: null

    signal starToggled(var item)
    signal previewRequested(var item)
    signal downloadRequested(var item)
    signal p2pSendRequested(var item)
    signal trashRequested(var item)

    implicitHeight: 56
    padding: 10

    RowLayout {
        anchors.fill: parent
        spacing: 12

        Rectangle {
            width: 36; height: 36; radius: 8
            color: Qt.rgba(itemData && itemData.color ? Qt.color(itemData.color).r : Theme.primary.r,
                           itemData && itemData.color ? Qt.color(itemData.color).g : Theme.primary.g,
                           itemData && itemData.color ? Qt.color(itemData.color).b : Theme.primary.b, 0.14)
            Icon {
                anchors.centerIn: parent
                path: itemData ? itemData.iconPath : Icons.fileText
                width: 18; height: 18
                color: itemData && itemData.color ? itemData.color : Theme.primary
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            RowLayout {
                spacing: 6
                Txt {
                    text: itemData ? itemData.name : ""
                    role: "body"
                    weight: 600
                    color: Theme.surfaceContent
                    elide: Text.ElideMiddle
                }
                Icon {
                    visible: itemData && itemData.isStarred
                    path: Icons.star
                    width: 14; height: 14
                    color: "#f9ab00"
                }
            }
            Txt {
                text: itemData ? qsTr("%1 • %2 • %3").arg(itemData.size).arg(itemData.owner).arg(itemData.date) : ""
                role: "caption"
                color: Theme.surfaceContentVariant
            }
        }

        Button {
            iconPath: Icons.star
            variant: itemData && itemData.isStarred ? "fill" : "outline"
            size: "sm"
            onClicked: itemCard.starToggled(itemData)
        }

        Button {
            text: qsTr("Visualizar")
            variant: "outline"
            size: "sm"
            iconPath: Icons.window
            onClicked: itemCard.previewRequested(itemData)
        }

        Button {
            text: qsTr("Baixar")
            variant: "outline"
            size: "sm"
            iconPath: Icons.download
            onClicked: itemCard.downloadRequested(itemData)
        }

        Button {
            text: qsTr("Celular (P2P)")
            variant: "tonal"
            size: "sm"
            iconPath: Icons.send
            onClicked: itemCard.p2pSendRequested(itemData)
        }

        Button {
            iconPath: Icons.trash
            variant: "ghost"
            size: "sm"
            onClicked: itemCard.trashRequested(itemData)
        }
    }
}
