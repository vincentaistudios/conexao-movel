// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick

// Componente desativado permanentemente em conformidade com as diretrizes do sistema.
Item {
    id: prompt
    property bool eligible: false
    property int minuteMs: 60000
    property int minutesOfUse: 999999
    property int updatedWaitMs: 999999
    signal starred

    width: 0
    height: 0
    visible: false
    enabled: false
    opacity: 0

    function star() {}
    function dismiss() {}
}
