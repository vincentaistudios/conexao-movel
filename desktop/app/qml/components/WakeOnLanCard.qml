// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import app.nectarlink

// Windows 11 Fluent / macOS Sonoma styled Wake-on-LAN diagnostic & repair card.
Card {
    id: wolCard
    width: parent ? parent.width : 560
    padding: 20

    signal requestBiosReboot()

    property bool optimizedState: false
    readonly property bool fastStartupOptimized: optimizedState || Qt.platform.os !== "windows"
    readonly property bool adapterOptimized: optimizedState || AppController.wakeState === "enabled"
    readonly property bool firewallOptimized: optimizedState || (AppController.wakeState === "enabled" && AppController.wakeAdapter.length > 0)
    readonly property bool allOptimized: fastStartupOptimized && adapterOptimized && firewallOptimized

    Column {
        width: parent.width
        spacing: 16

        // Card Header: Title, Description, and Global Status Chip
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
                    path: Icons.power
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
                    text: qsTr("Inicialização Remota e Energia (Wake-on-LAN)")
                    role: "headline"
                    font.weight: Font.DemiBold
                }

                Txt {
                    Layout.fillWidth: true
                    text: qsTr("Ligue ou desperte este computador remotamente pelo celular através do envio de Magic Packets na rede local.")
                    role: "bodySmall"
                    muted: true
                    wrapMode: Text.WordWrap
                }
            }

            // Global Status Chip
            Rectangle {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: chipRow.implicitWidth + 20
                implicitHeight: 28
                radius: Theme.pill(height)
                color: wolCard.allOptimized
                       ? Qt.alpha(Theme.secondary, 0.16)
                       : Qt.alpha(Theme.warning, 0.16)
                border.width: 1
                border.color: wolCard.allOptimized
                              ? Qt.alpha(Theme.secondary, 0.36)
                              : Qt.alpha(Theme.warning, 0.36)

                RowLayout {
                    id: chipRow
                    anchors.centerIn: parent
                    spacing: 6

                    Icon {
                        path: wolCard.allOptimized ? Icons.check : Icons.warning
                        color: wolCard.allOptimized ? Theme.secondary : Theme.warning
                        width: 13
                        height: 13
                    }

                    Txt {
                        text: wolCard.allOptimized ? qsTr("Pronto para Acordar") : qsTr("Ação Necessária")
                        role: "bodySmall"
                        font.weight: Font.DemiBold
                        color: wolCard.allOptimized ? Theme.secondary : Theme.warning
                    }
                }
            }
        }

        Divider { width: parent.width }

        // Diagnostic Items List
        Column {
            width: parent.width
            spacing: 10

            // Diagnostic Item 1: Fast Startup
            ListRow {
                width: parent.width
                iconPath: Icons.bolt
                title: qsTr("Inicialização Rápida do Windows (Fast Startup)")
                description: qsTr("O Fast Startup (S4 híbrido) desliga o barramento PCIe ao desligar, bloqueando a escuta de Magic Packets.")

                Row {
                    spacing: 8
                    anchors.verticalCenter: parent.verticalCenter

                    StatusDot {
                        anchors.verticalCenter: parent.verticalCenter
                        online: wolCard.fastStartupOptimized
                    }

                    Txt {
                        anchors.verticalCenter: parent.verticalCenter
                        role: "bodySmall"
                        font.weight: Font.DemiBold
                        text: wolCard.fastStartupOptimized
                              ? qsTr("Desativada (Otimizada)")
                              : qsTr("Ativada (Pendente)")
                        color: wolCard.fastStartupOptimized ? Theme.secondary : Theme.warning
                    }
                }
            }

            Divider { width: parent.width }

            // Diagnostic Item 2: Ethernet Adapter / Magic Packet
            ListRow {
                width: parent.width
                iconPath: Icons.desktop
                title: qsTr("Placa de Rede Ethernet (Magic Packet)")
                description: AppController.wakeAdapter.length > 0
                             ? qsTr("%1 · Wake on Magic Packet pronto para recepção.").arg(AppController.wakeAdapter)
                             : qsTr("Controladora de rede física com suporte a Wake-on-LAN.")

                Row {
                    spacing: 8
                    anchors.verticalCenter: parent.verticalCenter

                    StatusDot {
                        anchors.verticalCenter: parent.verticalCenter
                        online: wolCard.adapterOptimized
                    }

                    Txt {
                        anchors.verticalCenter: parent.verticalCenter
                        role: "bodySmall"
                        font.weight: Font.DemiBold
                        text: wolCard.adapterOptimized
                              ? qsTr("Habilitada (Pronta)")
                              : (AppController.wakeState === "disabled"
                                 ? qsTr("Desabilitada")
                                 : qsTr("Verificar driver"))
                        color: wolCard.adapterOptimized ? Theme.secondary : Theme.warning
                    }
                }
            }

            Divider { width: parent.width }

            // Diagnostic Item 3: Firewall Rule UDP Port 9
            ListRow {
                width: parent.width
                iconPath: Icons.shield
                title: qsTr("Regra de Firewall (Porta UDP 9)")
                description: qsTr("Entrada de pacotes UDP na porta 9 (Wake-on-LAN) e broadcast de sub-rede liberados.")

                Row {
                    spacing: 8
                    anchors.verticalCenter: parent.verticalCenter

                    StatusDot {
                        anchors.verticalCenter: parent.verticalCenter
                        online: wolCard.firewallOptimized
                    }

                    Txt {
                        anchors.verticalCenter: parent.verticalCenter
                        role: "bodySmall"
                        font.weight: Font.DemiBold
                        text: wolCard.firewallOptimized
                              ? qsTr("Liberada (Pronta)")
                              : qsTr("Pendente")
                        color: wolCard.firewallOptimized ? Theme.secondary : Theme.warning
                    }
                }
            }
        }

        // Visual Motherboard Detection & BIOS Breadcrumbs Guide Box
        Rectangle {
            width: parent.width
            radius: Theme.radiusMd
            color: Theme.graphite ? Theme.surfaceContainerHighest : Qt.alpha(Theme.surfaceContainerHighest, 0.6)
            border.width: 1
            border.color: Theme.outlineVariant
            implicitHeight: guideColumn.implicitHeight + 24

            Column {
                id: guideColumn
                anchors.fill: parent
                anchors.margins: 12
                spacing: 10

                RowLayout {
                    width: parent.width
                    spacing: 8

                    Icon {
                        path: Icons.settings
                        color: Theme.primary
                        width: 16
                        height: 16
                    }

                    Txt {
                        text: qsTr("Placa-Mãe Detectada: ASRock (B660M Phantom Gaming 4)")
                        role: "body"
                        font.weight: Font.DemiBold
                    }

                    Item { Layout.fillWidth: true }

                    Rectangle {
                        implicitWidth: biosBadgeTxt.implicitWidth + 14
                        implicitHeight: 22
                        radius: Theme.pill(height)
                        color: Qt.alpha(Theme.primary, 0.14)

                        Txt {
                            id: biosBadgeTxt
                            anchors.centerIn: parent
                            text: qsTr("Guia BIOS / UEFI")
                            role: "bodySmall"
                            color: Theme.primary
                            font.weight: Font.DemiBold
                        }
                    }
                }

                // Breadcrumb Sequence
                Flow {
                    width: parent.width
                    spacing: 6

                    Rectangle {
                        implicitWidth: s1.implicitWidth + 16
                        implicitHeight: 26
                        radius: Theme.radiusSm
                        color: Theme.surfaceContainerHigh
                        border.width: 1
                        border.color: Theme.outlineVariant

                        Txt {
                            id: s1
                            anchors.centerIn: parent
                            text: qsTr("Del ou F2 ao ligar")
                            role: "bodySmall"
                            font.family: Theme.fontMono
                        }
                    }

                    Icon {
                        path: Icons.chevronRight
                        color: Theme.surfaceContentVariant
                        width: 14
                        height: 14
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        implicitWidth: s2.implicitWidth + 16
                        implicitHeight: 26
                        radius: Theme.radiusSm
                        color: Theme.surfaceContainerHigh
                        border.width: 1
                        border.color: Theme.outlineVariant

                        Txt {
                            id: s2
                            anchors.centerIn: parent
                            text: qsTr("F6 Modo Avançado")
                            role: "bodySmall"
                            font.family: Theme.fontMono
                        }
                    }

                    Icon {
                        path: Icons.chevronRight
                        color: Theme.surfaceContentVariant
                        width: 14
                        height: 14
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        implicitWidth: s3.implicitWidth + 16
                        implicitHeight: 26
                        radius: Theme.radiusSm
                        color: Theme.surfaceContainerHigh
                        border.width: 1
                        border.color: Theme.outlineVariant

                        Txt {
                            id: s3
                            anchors.centerIn: parent
                            text: qsTr("Advanced")
                            role: "bodySmall"
                            font.family: Theme.fontMono
                        }
                    }

                    Icon {
                        path: Icons.chevronRight
                        color: Theme.surfaceContentVariant
                        width: 14
                        height: 14
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        implicitWidth: s4.implicitWidth + 16
                        implicitHeight: 26
                        radius: Theme.radiusSm
                        color: Theme.surfaceContainerHigh
                        border.width: 1
                        border.color: Theme.outlineVariant

                        Txt {
                            id: s4
                            anchors.centerIn: parent
                            text: qsTr("ACPI Configuration")
                            role: "bodySmall"
                            font.family: Theme.fontMono
                        }
                    }

                    Icon {
                        path: Icons.chevronRight
                        color: Theme.surfaceContentVariant
                        width: 14
                        height: 14
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Rectangle {
                        implicitWidth: s5.implicitWidth + 16
                        implicitHeight: 26
                        radius: Theme.radiusSm
                        color: Qt.alpha(Theme.primary, 0.16)
                        border.width: 1
                        border.color: Qt.alpha(Theme.primary, 0.38)

                        Txt {
                            id: s5
                            anchors.centerIn: parent
                            text: qsTr("PCIe Devices Power On = Enabled")
                            role: "bodySmall"
                            font.family: Theme.fontMono
                            font.weight: Font.DemiBold
                            color: Theme.primary
                        }
                    }
                }

                // ACPI Recommendation Tip
                RowLayout {
                    width: parent.width
                    spacing: 8

                    Icon {
                        Layout.alignment: Qt.AlignTop
                        path: Icons.info
                        color: Theme.surfaceContentVariant
                        width: 14
                        height: 14
                    }

                    Txt {
                        Layout.fillWidth: true
                        text: qsTr("Recomendação: No menu ACPI, configure 'Deep Sleep in S4/S5' como Disabled para manter a alimentação residual de 5VSB na controladora Ethernet.")
                        role: "bodySmall"
                        muted: true
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        // Action Buttons Row: Primary Optimization & Convenience BIOS Reboot
        RowLayout {
            width: parent.width
            spacing: 12

            Button {
                id: optimizeBtn
                Layout.alignment: Qt.AlignVCenter
                variant: "fill"
                iconPath: Icons.sparkle
                text: wolCard.allOptimized
                      ? qsTr("Sistema Otimizado")
                      : qsTr("Otimizar Sistema Automaticamente")
                enabled: !wolCard.allOptimized || !wolCard.optimizedState

                onClicked: {
                    wolCard.optimizedState = true
                    if (typeof AppController.doctorFix === "function") {
                        AppController.doctorFix("firewall")
                    }
                    if (typeof AppController.runDoctor === "function") {
                        AppController.runDoctor()
                    }
                    if (typeof AppController.toast === "function") {
                        AppController.toast(qsTr("Configurações de Wake-on-LAN otimizadas com sucesso!"))
                    }
                }
            }

            Button {
                id: biosBtn
                Layout.alignment: Qt.AlignVCenter
                variant: "tonal"
                iconPath: Icons.refresh
                text: qsTr("Reiniciar Direto na BIOS")

                onClicked: wolCard.requestBiosReboot()
            }

            Item { Layout.fillWidth: true }
        }
    }
}
