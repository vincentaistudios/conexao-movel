// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import app.nectarlink
import "../components"

Item {
    id: page
    property bool active: false
    property string deviceId: ""
    property string deviceName: ""

    property string currentUrl: ""
    property var inspectedMedia: null
    property string selectedFormat: "both" // "audio", "video", "both"
    property string selectedDestination: "both" // "pc", "phone", "both"
    property string currentTaskId: ""
    property string downloadStatus: "idle" // "idle", "inspecting", "downloading", "completed", "error"
    property real downloadProgress: 0.0
    property string downloadSpeed: ""
    property string downloadEta: ""
    property string statusMessage: ""
    property var lastFiles: []
    property var recentHistory: []

    readonly property string backendUrl: "http://127.0.0.1:28795"

    function inspectLink(urlText) {
        let u = (urlText || currentUrl || "").trim()
        if (!u.startsWith("http://") && !u.startsWith("https://")) {
            if (u.includes("youtube.com") || u.includes("youtu.be") ||
                u.includes("instagram.com") || u.includes("tiktok.com") ||
                u.includes("x.com") || u.includes("twitter.com")) {
                u = "https://" + u
            } else {
                statusMessage = qsTr("Insira um link valido (YouTube, Instagram, TikTok, etc.)")
                downloadStatus = "error"
                return
            }
        }
        currentUrl = u
        urlInput.text = u
        downloadStatus = "inspecting"
        statusMessage = qsTr("Inspecionando metadados da midia...")

        let xhr = new XMLHttpRequest()
        xhr.open("POST", backendUrl + "/inspect", true)
        xhr.setRequestHeader("Content-Type", "application/json")
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    try {
                        let res = JSON.parse(xhr.responseText)
                        if (res.success) {
                            inspectedMedia = res
                            downloadStatus = "ready"
                            statusMessage = qsTr("Midia identificada com sucesso!")
                        } else {
                            downloadStatus = "error"
                            statusMessage = res.error || qsTr("Falha ao inspecionar midia.")
                        }
                    } catch (e) {
                        downloadStatus = "error"
                        statusMessage = qsTr("Erro de comunicacao com o servico.")
                    }
                } else {
                    downloadStatus = "error"
                    statusMessage = qsTr("Falha ao consultar servico local.")
                }
            }
        }
        xhr.send(JSON.stringify({ "url": u }))
    }

    function triggerDownload() {
        if (!currentUrl) return
        downloadStatus = "downloading"
        downloadProgress = 0.0
        downloadSpeed = qsTr("Iniciando download...")
        downloadEta = "--:--"
        statusMessage = qsTr("Baixando e processando midia...")

        let xhr = new XMLHttpRequest()
        xhr.open("POST", backendUrl + "/download", true)
        xhr.setRequestHeader("Content-Type", "application/json")
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    try {
                        let res = JSON.parse(xhr.responseText)
                        if (res.success) {
                            currentTaskId = res.task_id
                            pollTimer.restart()
                        } else {
                            downloadStatus = "error"
                            statusMessage = res.error || qsTr("Nao foi possivel iniciar o download.")
                        }
                    } catch (e) {
                        downloadStatus = "error"
                        statusMessage = qsTr("Erro ao processar resposta do servico.")
                    }
                } else {
                    downloadStatus = "error"
                    statusMessage = qsTr("Erro ao conectar ao servico local.")
                }
            }
        }
        xhr.send(JSON.stringify({
            "url": currentUrl,
            "format": selectedFormat,
            "destination": selectedDestination,
            "device_id": page.deviceId
        }))
    }

    function pollStatus() {
        if (!currentTaskId || downloadStatus !== "downloading") return

        let xhr = new XMLHttpRequest()
        xhr.open("GET", backendUrl + "/status?task_id=" + encodeURIComponent(currentTaskId), true)
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                try {
                    let res = JSON.parse(xhr.responseText)
                    if (res.success && res.task) {
                        let t = res.task
                        downloadProgress = t.progress || 0.0
                        downloadSpeed = t.speed || ""
                        downloadEta = t.eta || ""

                        if (t.status === "completed") {
                            pollTimer.stop()
                            downloadStatus = "completed"
                            lastFiles = t.generated_files || []
                            statusMessage = qsTr("Download concluido com sucesso na pasta Downloads!")

                            // Encaminha para o celular se a opcao selecionada for celular ou ambos
                            if ((selectedDestination === "phone" || selectedDestination === "both") && lastFiles.length > 0 && page.deviceId.length > 0) {
                                let urlsToSend = []
                                for (let i = 0; i < lastFiles.length; i++) {
                                    urlsToSend.push("file://" + lastFiles[i])
                                }
                                TransferList.send(page.deviceId, urlsToSend)
                                statusMessage += qsTr(" Arquivo(s) enviado(s) para o celular.")
                            }
                            fetchHistory()
                        } else if (t.status === "failed") {
                            pollTimer.stop()
                            downloadStatus = "error"
                            statusMessage = t.error || qsTr("Falha durante o download.")
                        }
                    }
                } catch (e) {}
            }
        }
        xhr.send()
    }

    function cancelCurrentDownload() {
        if (!currentTaskId) return
        let xhr = new XMLHttpRequest()
        xhr.open("POST", backendUrl + "/cancel", true)
        xhr.setRequestHeader("Content-Type", "application/json")
        xhr.send(JSON.stringify({ "task_id": currentTaskId }))
        pollTimer.stop()
        downloadStatus = "idle"
        statusMessage = qsTr("Download cancelado pelo usuario.")
    }

    function fetchHistory() {
        let xhr = new XMLHttpRequest()
        xhr.open("GET", backendUrl + "/history", true)
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                try {
                    let res = JSON.parse(xhr.responseText)
                    if (res.success) {
                        recentHistory = res.history || []
                    }
                } catch (e) {}
            }
        }
        xhr.send()
    }

    Timer {
        id: pollTimer
        interval: 600
        repeat: true
        running: false
        onTriggered: page.pollStatus()
    }

    Component.onCompleted: {
        page.fetchHistory()
    }

    onActiveChanged: {
        if (active) page.fetchHistory()
    }

    Flickable {
        anchors.fill: parent
        anchors.margins: Theme.contentPadding
        contentWidth: width
        contentHeight: contentCol.height + 40
        clip: true

        Column {
            id: contentCol
            width: parent.width
            spacing: 20

            // Cabecalho
            Column {
                width: parent.width
                spacing: 6
                Txt {
                    role: "headline"
                    text: qsTr("Downloads Multimidia")
                    size: 24
                }
                Txt {
                    role: "body"
                    muted: true
                    text: qsTr("Baixe videos e audios do YouTube, Instagram, TikTok e envie diretamente ao computador ou smartphone.")
                }
            }

            // Card de Entrada da URL
            Card {
                width: parent.width
                padding: 18

                Column {
                    width: parent.width
                    spacing: 14

                    Txt {
                        role: "title"
                        text: qsTr("Link do Conteudo")
                        size: 16
                    }

                    Row {
                        width: parent.width
                        spacing: 10

                        Rectangle {
                            height: 42
                            width: parent.width - btnPaste.width - btnInspect.width - 20
                            radius: Theme.radiusSm
                            color: Theme.graphite ? "#14161D" : Theme.surfaceContainerHighest
                            border.width: 1
                            border.color: urlInput.activeFocus ? Theme.primary : Theme.outlineVariant

                            TextInput {
                                id: urlInput
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                verticalAlignment: TextInput.AlignVCenter
                                color: Theme.surfaceContent
                                font.pixelSize: 14
                                selectByMouse: true
                                clip: true
                                text: page.currentUrl
                                onTextChanged: page.currentUrl = text
                                onAccepted: page.inspectLink(text)

                                Text {
                                    anchors.fill: parent
                                    verticalAlignment: Text.AlignVCenter
                                    visible: !urlInput.text && !urlInput.activeFocus
                                    text: qsTr("Cole o link aqui (ex: https://youtube.com/watch?v=...)")
                                    color: Theme.surfaceContentVariant
                                    font.pixelSize: 14
                                }
                            }
                        }

                        Button {
                            id: btnPaste
                            text: qsTr("Colar")
                            iconPath: Icons.clipboard
                            variant: "tonal"
                            onClicked: {
                                // 1. Tenta colar nativamente no TextInput
                                urlInput.forceActiveFocus()
                                urlInput.selectAll()
                                urlInput.paste()
                                let nativeText = (urlInput.text || "").trim()

                                if (nativeText.length > 0 && (nativeText.startsWith("http://") || nativeText.startsWith("https://") || nativeText.includes("youtu"))) {
                                    page.inspectLink(nativeText)
                                    return
                                }

                                // 2. Fallback resiliente via servico local (suporta clipboard e primary selection X11)
                                let xhr = new XMLHttpRequest()
                                xhr.open("GET", backendUrl + "/clipboard", true)
                                xhr.onreadystatechange = function() {
                                    if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                                        try {
                                            let res = JSON.parse(xhr.responseText)
                                            if (res.success && res.text) {
                                                let clipText = res.text.trim()
                                                if (clipText.length > 0) {
                                                    urlInput.text = clipText
                                                    page.inspectLink(clipText)
                                                }
                                            }
                                        } catch (e) {}
                                    }
                                }
                                xhr.send()
                            }
                        }

                        Button {
                            id: btnInspect
                            text: qsTr("Analisar")
                            iconPath: Icons.search
                            variant: "fill"
                            busy: page.downloadStatus === "inspecting"
                            onClicked: page.inspectLink(urlInput.text)
                        }
                    }

                    // Mensagem de Status / Alerta
                    Txt {
                        visible: page.statusMessage.length > 0
                        role: "bodySmall"
                        color: page.downloadStatus === "error" ? Theme.error : Theme.primary
                        text: page.statusMessage
                    }
                }
            }

            // Card de Metadados e Configuracoes de Download
            Card {
                width: parent.width
                padding: 18
                visible: page.inspectedMedia !== null || page.downloadStatus === "downloading" || page.downloadStatus === "completed"

                Column {
                    width: parent.width
                    spacing: 16

                    // Miniatura e Informacoes da Midia
                    Row {
                        width: parent.width
                        spacing: 16

                        Rectangle {
                            width: 140
                            height: 84
                            radius: Theme.radiusSm
                            color: "#0F172A"
                            clip: true

                            Image {
                                anchors.fill: parent
                                fillMode: Image.PreserveAspectCrop
                                source: page.inspectedMedia ? page.inspectedMedia.thumbnail : ""
                            }
                        }

                        Column {
                            width: parent.width - 156
                            spacing: 6

                            Txt {
                                width: parent.width
                                role: "title"
                                text: page.inspectedMedia ? page.inspectedMedia.title : qsTr("Processando midia...")
                                elide: Text.ElideRight
                                maximumLineCount: 2
                            }

                            Txt {
                                role: "bodySmall"
                                muted: true
                                text: page.inspectedMedia
                                    ? (page.inspectedMedia.uploader + " · " + Math.floor(page.inspectedMedia.duration / 60) + "m " + (page.inspectedMedia.duration % 60) + "s")
                                    : ""
                            }
                        }
                    }

                    Divider { width: parent.width }

                    // Escolha de Formato
                    Column {
                        width: parent.width
                        spacing: 8
                        Txt {
                            role: "label"
                            text: qsTr("Formato Desejado")
                        }
                        Segmented {
                            width: Math.min(parent.width, 520)
                            options: [
                                { value: "audio", label: qsTr("Opcao 1: Audio (MP3 320k)") },
                                { value: "video", label: qsTr("Opcao 2: Video (MP4)") },
                                { value: "both", label: qsTr("Opcao 3: Ambos (Video + Audio)") }
                            ]
                            value: page.selectedFormat
                            onPicked: v => page.selectedFormat = v
                        }
                    }

                    // Escolha de Destino
                    Column {
                        width: parent.width
                        spacing: 8
                        Txt {
                            role: "label"
                            text: qsTr("Destino do Arquivo")
                        }
                        Segmented {
                            width: Math.min(parent.width, 560)
                            options: [
                                { value: "pc", label: qsTr("Salvar no Computador") },
                                { value: "phone", label: qsTr("Enviar ao Celular (%1)").arg(page.deviceName || qsTr("Pareado")) },
                                { value: "both", label: qsTr("Salvar em Ambos") }
                            ]
                            value: page.selectedDestination
                            onPicked: v => page.selectedDestination = v
                        }
                    }

                    // Barra de Progresso durante Download
                    Column {
                        width: parent.width
                        spacing: 6
                        visible: page.downloadStatus === "downloading"

                        Row {
                            width: parent.width
                            Txt {
                                role: "bodySmall"
                                text: qsTr("Progresso: %1% · Velocidade: %2 · Restante: %3").arg(page.downloadProgress.toFixed(1)).arg(page.downloadSpeed).arg(page.downloadEta)
                            }
                        }

                        Rectangle {
                            width: parent.width
                            height: 8
                            radius: 4
                            color: Theme.graphite ? "#22242C" : Theme.surfaceContainerHighest
                            clip: true

                            Rectangle {
                                height: parent.height
                                width: parent.width * (page.downloadProgress / 100.0)
                                radius: 4
                                color: Theme.primary
                                Behavior on width { NumberAnimation { duration: 200 } }
                            }
                        }
                    }

                    // Botoes de Acao de Download
                    Row {
                        spacing: 12
                        visible: page.downloadStatus !== "downloading"

                        Button {
                            text: qsTr("Baixar Agora")
                            iconPath: Icons.download
                            variant: "fill"
                            onClicked: page.triggerDownload()
                        }

                        Button {
                            text: qsTr("Abrir Pasta Downloads")
                            iconPath: Icons.folder
                            variant: "tonal"
                            onClicked: Qt.openUrlExternally("file:///home/Vincent/Downloads")
                        }

                        Button {
                            text: qsTr("Reenviar ao Celular")
                            iconPath: Icons.send
                            variant: "outline"
                            visible: page.downloadStatus === "completed" && page.lastFiles.length > 0 && page.deviceId.length > 0
                            onClicked: {
                                let urls = []
                                for (let i = 0; i < page.lastFiles.length; i++) {
                                    urls.push("file://" + page.lastFiles[i])
                                }
                                TransferList.send(page.deviceId, urls)
                            }
                        }
                    }

                    // Botao de Cancelar durante Download
                    Row {
                        visible: page.downloadStatus === "downloading"
                        Button {
                            text: qsTr("Cancelar Download")
                            iconPath: Icons.close || Icons.cross
                            variant: "tonal"
                            onClicked: page.cancelCurrentDownload()
                        }
                    }
                }
            }

            // Historico de Downloads Recentes
            Card {
                width: parent.width
                padding: 18
                visible: page.recentHistory.length > 0

                Column {
                    width: parent.width
                    spacing: 12

                    Txt {
                        role: "title"
                        text: qsTr("Downloads Recentes")
                        size: 16
                    }

                    Repeater {
                        model: page.recentHistory
                        delegate: Rectangle {
                            width: contentCol.width - 36
                            height: 48
                            radius: Theme.radiusSm
                            color: Theme.graphite ? "#14161D" : Theme.surfaceContainerHighest

                            Row {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 12

                                Icon {
                                    anchors.verticalCenter: parent.verticalCenter
                                    path: modelData.format === "audio" ? Icons.music : Icons.video
                                    color: Theme.primary
                                }

                                Column {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - 240
                                    Txt {
                                        width: parent.width
                                        text: modelData.title || qsTr("Midia baixada")
                                        elide: Text.ElideRight
                                        role: "bodySmall"
                                    }
                                }

                                Row {
                                    anchors.verticalCenter: parent.verticalCenter
                                    spacing: 8

                                    Txt {
                                        anchors.verticalCenter: parent.verticalCenter
                                        role: "caption"
                                        muted: true
                                        text: modelData.status === "completed" ? qsTr("Concluido") : qsTr("Falhou")
                                    }

                                    IconButton {
                                        iconPath: Icons.folder
                                        iconSize: 14
                                        label: qsTr("Abrir pasta")
                                        onClicked: Qt.openUrlExternally("file:///home/Vincent/Downloads")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
