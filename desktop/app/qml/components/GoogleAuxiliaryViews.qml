// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import app.nectarlink

Item {
    id: rootAux
    property string activeTab: "drive"
    property real driveUsedGb: 44.27
    property real driveTotalGb: 5000.0
    property string planLabel: "Google Workspace (5 TB)"
    property int syncedPhotosCount: 894

    // ABA GOOGLE DRIVE
    GoogleDriveView {
        anchors.fill: parent
        visible: rootAux.activeTab === "drive"
        driveUsedGb: rootAux.driveUsedGb
        driveTotalGb: rootAux.driveTotalGb
        planLabel: rootAux.planLabel
    }

    // ABA GOOGLE FOTOS
    GooglePhotosView {
        anchors.fill: parent
        visible: rootAux.activeTab === "photos"
        totalPhotos: rootAux.syncedPhotosCount
    }

    // ABA PROXIMIDADE P2P
    Card {
        anchors.fill: parent
        visible: rootAux.activeTab === "p2p"
        padding: 24

        ColumnLayout {
            anchors.fill: parent
            spacing: 16

            RowLayout {
                Layout.fillWidth: true
                Icon { path: Icons.proximityP2P; width: 28; height: 28; color: Theme.primary }
                Txt { text: qsTr("Enlace por Proximidade P2P (Sem Roteador Wi-Fi)"); role: "headline"; weight: 600; color: Theme.surfaceContent }
            }

            Txt {
                text: "Canal direto Wi-Fi Direct P2P ativo com criptografia militar AES-256-GCM.
Latencia medida: 3ms - Taxa de transferencia: 433 Mbps
Frequencia: 5GHz P2P Group Owner.
Dispositivo de confianca conectado: Van Gogh (Android 16)."
                role: "body"
                color: Theme.surfaceContentVariant
                wrapMode: Text.WordWrap
            }

            Item { Layout.fillHeight: true }
        }
    }
}
