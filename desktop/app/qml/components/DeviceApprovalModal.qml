// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import app.nectarlink

Item {
    id: modalRoot
    anchors.fill: parent
    z: 9999
    visible: pendingDeviceName !== ""

    property string pendingRequestId: ""
    property string pendingDeviceName: ""
    property string pendingDeviceModel: ""
    property string pendingSasCode: "000000"
    property int pendingRssi: -50
    property string pendingTransport: "Wi-Fi Direct P2P"

    signal deviceApproved(string requestId)
    signal deviceRejected(string requestId)

    // Fundo escurecido translúcido
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0, 0, 0, 0.65)
        Behavior on opacity { NumberAnimation { duration: 200 } }

        MouseArea {
            anchors.fill: parent
        }
    }

    // Caixa de Diálogo Centralizada (Padrão Fluent / macOS)
    Card {
        id: dialogCard
        width: Math.min(480, modalRoot.width - 48)
        anchors.centerIn: parent
        padding: 24

        ColumnLayout {
            anchors.fill: parent
            spacing: 16

            // Cabeçalho com Ícone de Segurança
            RowLayout {
                Layout.fillWidth: true
                spacing: 14

                Rectangle {
                    width: 44
                    height: 44
                    radius: 22
                    color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.15)
                    border.width: 1
                    border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.3)

                    Icon {
                        anchors.centerIn: parent
                        path: Icons.shield
                        color: Theme.primary
                        width: 24
                        height: 24
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Txt {
                        text: "Solicitação de Acesso por Proximidade"
                        role: "title"
                        weight: 600
                        color: Theme.surfaceContent
                    }

                    Txt {
                        text: "Segurança Zero-Trust: Quórum de Aprovação"
                        role: "caption"
                        muted: true
                    }
                }
            }

            Divider {
                Layout.fillWidth: true
            }

            // Informações do Dispositivo Requisitante
            Rectangle {
                Layout.fillWidth: true
                implicitHeight: deviceCol.height + 20
                radius: Theme.radiusMd
                color: Theme.cardColor
                border.width: 1
                border.color: Theme.cardBorder

                ColumnLayout {
                    id: deviceCol
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8

                    RowLayout {
                        Layout.fillWidth: true
                        Txt {
                            text: "Dispositivo:"
                            role: "bodySmall"
                            muted: true
                            Layout.preferredWidth: 100
                        }
                        Txt {
                            text: modalRoot.pendingDeviceName + " (" + modalRoot.pendingDeviceModel + ")"
                            role: "bodySmall"
                            weight: 500
                            color: Theme.surfaceContent
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Txt {
                            text: "Conexão:"
                            role: "bodySmall"
                            muted: true
                            Layout.preferredWidth: 100
                        }
                        Txt {
                            text: modalRoot.pendingTransport + " (Sem Roteador)"
                            role: "bodySmall"
                            color: Theme.surfaceContent
                            Layout.fillWidth: true
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Txt {
                            text: "Sinal de Rádio:"
                            role: "bodySmall"
                            muted: true
                            Layout.preferredWidth: 100
                        }
                        Txt {
                            text: modalRoot.pendingRssi + " dBm (Proximidade Direta)"
                            role: "bodySmall"
                            color: Theme.primary
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            // Bloco do Código SAS de 6 dígitos
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6

                Txt {
                    text: "Confirme se o código abaixo é idêntico no novo dispositivo:"
                    role: "caption"
                    muted: true
                    Layout.alignment: Qt.AlignHCenter
                }

                Rectangle {
                    Layout.alignment: Qt.AlignHCenter
                    width: 220
                    height: 52
                    radius: Theme.radiusMd
                    color: Qt.rgba(Theme.surfaceContent.r, Theme.surfaceContent.g, Theme.surfaceContent.b, 0.08)
                    border.width: 1
                    border.color: Theme.primary

                    Txt {
                        anchors.centerIn: parent
                        text: modalRoot.pendingSasCode
                        size: 26
                        weight: 700
                        font.letterSpacing: 6
                        color: Theme.primary
                    }
                }
            }

            // Botões de Ação
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 8
                spacing: 12

                Button {
                    Layout.fillWidth: true
                    text: "Rejeitar e Bloquear"
                    variant: "outline"
                    onClicked: {
                        var req = modalRoot.pendingRequestId;
                        modalRoot.pendingDeviceName = "";
                        modalRoot.deviceRejected(req);
                    }
                }

                Button {
                    Layout.fillWidth: true
                    text: "Autorizar Acesso"
                    variant: "fill"
                    onClicked: {
                        var req = modalRoot.pendingRequestId;
                        modalRoot.pendingDeviceName = "";
                        modalRoot.deviceApproved(req);
                    }
                }
            }
        }
    }
}
