// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import app.nectarlink

Item {
    id: photosViewRoot
    property int totalPhotos: 894
    property string activeAlbum: "all"
    property string statusNotice: ""
    property string selectedPhotoSrc: ""

    readonly property var photosData: [
        {
            "title": "Dunas ao Entardecer - Ensaio 4K",
            "source": "file:///usr/share/backgrounds/DESERT-v1.jpg",
            "date": "Hoje, 09:30",
            "album": "camera",
            "resolution": "4K Ultra HD",
            "size": "14.2 MB"
        },
        {
            "title": "Ondulações de Areia Noturnas",
            "source": "file:///usr/share/backgrounds/DESERT-v2.jpg",
            "date": "Ontem, 18:15",
            "album": "camera",
            "resolution": "HDR 10-bit",
            "size": "18.6 MB"
        },
        {
            "title": "Horizonte Carmim - Deserto Central",
            "source": "file:///usr/share/backgrounds/DESERT-v3.jpg",
            "date": "08 nov 2026",
            "album": "camera",
            "resolution": "4K 60fps",
            "size": "21.0 MB"
        },
        {
            "title": "Captura de Tela - Central de Controle",
            "source": "file:///usr/share/backgrounds/DESERT-v4.jpg",
            "date": "06 nov 2026",
            "album": "screenshots",
            "resolution": "FHD 1080p",
            "size": "4.8 MB"
        },
        {
            "title": "Crepúsculo Dourado - Modo Noturno",
            "source": "file:///usr/share/backgrounds/DESERT-v5.jpg",
            "date": "04 nov 2026",
            "album": "favorites",
            "resolution": "4K Ultra HD",
            "size": "16.5 MB"
        },
        {
            "title": "Panorama Desértico em Alta Resolução",
            "source": "file:///usr/share/backgrounds/DESERT-v6.jpg",
            "date": "02 nov 2026",
            "album": "favorites",
            "resolution": "8K RAW",
            "size": "32.1 MB"
        }
    ]

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

        // 1. Cabeçalho de Status
        Card {
            Layout.fillWidth: true
            implicitHeight: 74
            padding: 14

            RowLayout {
                anchors.fill: parent
                spacing: 12
                Icon { path: Icons.photo; width: 22; height: 22; color: Theme.primary }
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2
                    Txt {
                        text: qsTr("Galeria do Google Fotos")
                        role: "title"
                        weight: 600
                        color: Theme.surfaceContent
                    }
                    Txt {
                        text: photosViewRoot.totalPhotos + qsTr(" fotos sincronizadas em alta resolucao diretamente via P2P")
                        role: "caption"
                        color: Theme.surfaceContentVariant
                    }
                }
                Button {
                    text: qsTr("Ver Galeria no Navegador")
                    variant: "outline"
                    size: "sm"
                    iconPath: Icons.openExternal
                    onClicked: Qt.openUrlExternally("https://photos.google.com")
                }
            }
        }

        // 2. Filtros de Álbum
        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Txt { text: qsTr("Albuns:"); role: "label"; weight: 600; color: Theme.surfaceContent }
            Button {
                text: qsTr("Todas")
                variant: photosViewRoot.activeAlbum === "all" ? "fill" : "outline"
                size: "sm"
                onClicked: photosViewRoot.activeAlbum = "all"
            }
            Button {
                text: qsTr("Camera (Van Gogh)")
                variant: photosViewRoot.activeAlbum === "camera" ? "fill" : "outline"
                size: "sm"
                onClicked: photosViewRoot.activeAlbum = "camera"
            }
            Button {
                text: qsTr("Capturas de Tela")
                variant: photosViewRoot.activeAlbum === "screenshots" ? "fill" : "outline"
                size: "sm"
                onClicked: photosViewRoot.activeAlbum = "screenshots"
            }
            Button {
                text: qsTr("Favoritas")
                variant: photosViewRoot.activeAlbum === "favorites" ? "fill" : "outline"
                size: "sm"
                onClicked: photosViewRoot.activeAlbum = "favorites"
            }
            Item { Layout.fillWidth: true }
            Txt {
                visible: photosViewRoot.statusNotice.length > 0
                text: photosViewRoot.statusNotice
                role: "caption"
                color: Theme.primary
            }
        }

        // 3. Grade de Fotos (GridView)
        GridView {
            id: photoGrid
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            cellWidth: (width - 16) / 3
            cellHeight: 180
            model: photosViewRoot.photosData.filter(item => {
                if (photosViewRoot.activeAlbum === "all") return true
                return item.album === photosViewRoot.activeAlbum
            })

            delegate: Item {
                width: photoGrid.cellWidth - 10
                height: 170

                Rectangle {
                    anchors.fill: parent
                    radius: 12
                    color: Qt.rgba(1, 1, 1, Theme.dark ? 0.05 : 0.12)
                    border.width: photoMouse.containsMouse ? 2 : 1
                    border.color: photoMouse.containsMouse ? Theme.primary : Qt.rgba(1, 1, 1, Theme.dark ? 0.10 : 0.25)
                    clip: true

                    Image {
                        anchors.fill: parent
                        source: modelData.source
                        fillMode: Image.PreserveAspectCrop
                        smooth: true
                        scale: photoMouse.containsMouse ? 1.05 : 1.0
                        Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                    }

                    // Degradê inferior para legibilidade
                    Rectangle {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        height: 60
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 1.0; color: Qt.rgba(0, 0, 0, 0.85) }
                        }
                    }

                    // Badge de Resolução
                    Rectangle {
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.margins: 8
                        width: resTxt.implicitWidth + 10
                        height: 20
                        radius: 10
                        color: Qt.rgba(0, 0, 0, 0.65)
                        Txt {
                            id: resTxt
                            anchors.centerIn: parent
                            text: modelData.resolution
                            role: "caption"
                            size: 10
                            weight: 600
                            color: "#FFFFFF"
                        }
                    }

                    // Título e Data
                    ColumnLayout {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.margins: 8
                        spacing: 1

                        Txt {
                            text: modelData.title
                            role: "label"
                            weight: 600
                            color: "#FFFFFF"
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }
                        Txt {
                            text: modelData.date + " - " + modelData.size
                            role: "caption"
                            color: "#D1D5DB"
                            size: 10
                        }
                    }

                    MouseArea {
                        id: photoMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: photosViewRoot.statusNotice = qsTr("Foto '%1' selecionada. Transferencia P2P pronta.").arg(modelData.title)
                    }
                }
            }
        }
    }
}
