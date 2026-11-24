// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import app.nectarlink

// Windows 11 Fluent / macOS Sonoma styled automated phone setup card.
Card {
    id: setupCard
    width: parent ? parent.width : 560
    padding: 20

    property bool isBusy: false
    property string statusText: ""
    property string statusType: "info" // info, success, warning, error
    property var detectedDevices: []

    Component.onCompleted: {
        checkDevices()
    }

    function checkDevices() {
        try {
            let res = JSON.parse(AppController.listAdbDevices())
            detectedDevices = res || []
            if (detectedDevices.length > 0) {
                let first = detectedDevices[0]
                if (first.state === "device") {
                    statusText = qsTr("Smartphone conectado via USB (%1). Pronto para configuracao.").arg(first.serial)
                    statusType = "info"
                } else if (first.state === "unauthorized") {
                    statusText = qsTr("Aparelho conectado (%1), mas aguarda confirmacao de Depuracao USB na tela.").arg(first.serial)
                    statusType = "warning"
                } else {
                    statusText = qsTr("Aparelho detectado no estado: %1").arg(first.state)
                    statusType = "warning"
                }
            } else {
                statusText = qsTr("Nenhum smartphone detectado via USB. Conecte com cabo e ative a Depuracao USB.")
                statusType = "info"
            }
        } catch(e) {
            statusText = qsTr("Nenhum smartphone detectado via USB. Conecte com cabo e ative a Depuracao USB.")
            statusType = "info"
        }
    }

    function startAutoSetup() {
        isBusy = true
        statusText = qsTr("Concedendo permissoes e ativando Modo Elevado...")
        statusType = "info"
        setupTimer.start()
    }

    Timer {
        id: setupTimer
        interval: 100
        repeat: false
        onTriggered: {
            try {
                let target = detectedDevices.length > 0 ? detectedDevices[0].serial : ""
                let rawRes = AppController.runAdbAutoSetup(target)
                let res = JSON.parse(rawRes)
                isBusy = false
                if (res.success) {
                    statusText = qsTr("Sucesso! %1 permissoes concedidas e Modo Elevado ativo.").arg(res.permissions_granted)
                    statusType = "success"
                } else {
                    statusText = res.message || qsTr("Falha ao configurar permissoes.")
                    statusType = "error"
                }
            } catch(e) {
                isBusy = false
                statusText = qsTr("Erro ao executar configuracao automatica: %1").arg(e.toString())
                statusType = "error"
            }
        }
    }

    Column {
        width: parent.width
        spacing: 16

        RowLayout {
            width: parent.width
            spacing: 14

            Rectangle {
                Layout.preferredWidth: 38
                Layout.preferredHeight: 38
                radius: Theme.radiusMd
                color: Qt.alpha(Theme.primary, 0.14)
                border.width: 1
                border.color: Qt.alpha(Theme.primary, 0.28)

                Icon {
                    anchors.centerIn: parent
                    path: Icons.terminal
                    color: Theme.primary
                    width: 20
                    height: 20
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Txt {
                    Layout.fillWidth: true
                    text: qsTr("Assistente de Permissoes e Modo Elevado em 1 Clique")
                    role: "headline"
                    font.weight: Font.DemiBold
                }

                Txt {
                    Layout.fillWidth: true
                    text: qsTr("Conecte o smartphone via cabo USB com Depuracao USB para liberar todas as permissoes e ativar o Modo Elevado sem tocar no celular.")
                    role: "bodySmall"
                    color: Theme.onSurfaceVariant
                    wrapMode: Text.WordWrap
                }
            }
        }

        // Status Banner
        Rectangle {
            width: parent.width
            height: statusCol.implicitHeight + 20
            radius: Theme.radiusSm
            color: {
                if (statusType === "success") return Qt.alpha(Theme.primary, 0.12)
                if (statusType === "warning") return Qt.alpha("#EAB308", 0.12)
                if (statusType === "error") return Qt.alpha("#EF4444", 0.12)
                return Theme.surfaceContainerLow
            }
            border.width: 1
            border.color: {
                if (statusType === "success") return Qt.alpha(Theme.primary, 0.3)
                if (statusType === "warning") return Qt.alpha("#EAB308", 0.3)
                if (statusType === "error") return Qt.alpha("#EF4444", 0.3)
                return Theme.outlineVariant
            }

            ColumnLayout {
                id: statusCol
                anchors.fill: parent
                anchors.margins: 10
                spacing: 4

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Icon {
                        path: statusType === "success" ? Icons.check : (statusType === "error" ? Icons.bell : Icons.mirror)
                        width: 16
                        height: 16
                        color: {
                            if (statusType === "success") return Theme.primary
                            if (statusType === "warning") return "#EAB308"
                            if (statusType === "error") return "#EF4444"
                            return Theme.onSurfaceVariant
                        }
                    }

                    Txt {
                        Layout.fillWidth: true
                        text: statusText
                        role: "bodyMedium"
                        font.weight: statusType === "success" ? Font.Medium : Font.Normal
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        // Actions Bar
        RowLayout {
            width: parent.width
            spacing: 12

            Button {
                text: qsTr("Verificar Conexao USB")
                iconPath: Icons.refresh
                variant: "outlined"
                enabled: !isBusy
                onClicked: checkDevices()
            }

            Button {
                text: isBusy ? qsTr("Configurando...") : qsTr("Configurar Tudo em 1 Clique")
                iconPath: Icons.check
                variant: "filled"
                enabled: !isBusy
                onClicked: startAutoSetup()
            }

            Item { Layout.fillWidth: true }
        }
    }
}

