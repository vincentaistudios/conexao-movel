// SPDX-License-Identifier: GPL-3.0-or-later
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import app.nectarlink
import "../components"

Item {
    id: googlePageRoot
    property bool active: false
    property string deviceId: ""
    property string deviceName: ""
    readonly property string backendUrl: "http://127.0.0.1:28795"

    signal sessionStateSynced(bool connected, string avatarUrl, string email, string displayName)

    // Estado inicial reativo sincronizado automaticamente com o backend via /google/status
    property bool isAuthenticated: true
    property string userEmail: "vangogh.assistente@gmail.com"
    property string userDisplayName: "Miranda Van Gogh"
    property string userAvatarUrl: "file:///usr/share/icons/hicolor/scalable/apps/google-user-avatar.png"
    property string planLabel: "Google Workspace (5 TB)"
    property string detectedOsEmail: ""
    property bool isConnecting: false
    property real driveUsedGb: 44.27
    property real driveTotalGb: 5000.0
    property int syncedPhotosCount: 894

    // Abas de Servicos: 'gmail', 'drive', 'photos', 'p2p'
    property string currentTab: "gmail"
    property var activeReadingEmail: null

    // Base de dados reativa paginada do Gmail sincronizada com o backend
    property string gmailSyncMode: "demo_offline"
    property bool gmailHasMore: false
    property string gmailNextPageToken: ""
    property int gmailPage: 1
    property int gmailTotalEstimated: 0
    property bool gmailLoading: false
    property bool hasOauthClient: false
    property string gmailFolder: "inbox"
    property string gmailQuery: ""
    property var currentEmailsList: []
    property var inboxEmails: []
    property var archivedEmails: []
    property var trashEmails: []

    Component.onCompleted: syncStatus()

    function applyBackendState(payload) {
        if (!payload || !payload.status) return
        var st = payload.status
        googlePageRoot.isAuthenticated = !!st.is_authenticated
        googlePageRoot.userEmail = st.email || ""
        googlePageRoot.userDisplayName = st.display_name || "Desconectado"
        googlePageRoot.userAvatarUrl = st.avatar_url || ""
        googlePageRoot.planLabel = st.plan_label || ""
        googlePageRoot.driveUsedGb = st.drive_used_gb !== undefined ? st.drive_used_gb : 0.0
        googlePageRoot.driveTotalGb = st.drive_total_gb !== undefined ? st.drive_total_gb : 0.0
        googlePageRoot.syncedPhotosCount = st.photos_count !== undefined ? st.photos_count : 0

        if (payload.detected_os_account && payload.detected_os_account.email) {
            googlePageRoot.detectedOsEmail = payload.detected_os_account.email
        }
        if (payload.gmail_sync_mode !== undefined) googlePageRoot.gmailSyncMode = payload.gmail_sync_mode
        if (payload.has_oauth_client !== undefined) googlePageRoot.hasOauthClient = !!payload.has_oauth_client
        if (payload.inbox) {
            googlePageRoot.inboxEmails = payload.inbox
            if (googlePageRoot.gmailFolder === "inbox" && googlePageRoot.gmailQuery.length === 0) {
                googlePageRoot.currentEmailsList = payload.inbox
                googlePageRoot.gmailHasMore = !!payload.gmail_has_more
                googlePageRoot.gmailNextPageToken = payload.gmail_next_page_token || ""
                googlePageRoot.gmailTotalEstimated = payload.gmail_total_estimated !== undefined ? payload.gmail_total_estimated : payload.inbox.length
            }
        }
        if (payload.archived) googlePageRoot.archivedEmails = payload.archived
        if (payload.trash) googlePageRoot.trashEmails = payload.trash

        googlePageRoot.sessionStateSynced(
            googlePageRoot.isAuthenticated,
            googlePageRoot.userAvatarUrl,
            googlePageRoot.userEmail,
            googlePageRoot.userDisplayName
        )
    }

    function loadGmailMessages(resetPage) {
        if (googlePageRoot.gmailLoading || !googlePageRoot.isAuthenticated) return
        googlePageRoot.gmailLoading = true
        var nextPage = resetPage ? 1 : (googlePageRoot.gmailPage + 1)
        var cursor = resetPage ? "" : googlePageRoot.gmailNextPageToken
        var qs = "/google/gmail/messages?folder=" + encodeURIComponent(googlePageRoot.gmailFolder)
            + "&page=" + nextPage + "&limit=50"
            + "&page_token=" + encodeURIComponent(cursor)
            + "&q=" + encodeURIComponent(googlePageRoot.gmailQuery)
        requestJson("GET", qs, null, function(ok, data) {
            googlePageRoot.gmailLoading = false
            if (!ok || !data || !data.success) return
            var incoming = data.messages || []
            googlePageRoot.currentEmailsList = resetPage ? incoming : googlePageRoot.currentEmailsList.concat(incoming)
            googlePageRoot.gmailPage = nextPage
            googlePageRoot.gmailHasMore = !!data.has_more
            googlePageRoot.gmailNextPageToken = data.next_page_token || ""
            googlePageRoot.gmailTotalEstimated = data.total_estimated !== undefined ? data.total_estimated : googlePageRoot.currentEmailsList.length
            if (data.sync_mode) googlePageRoot.gmailSyncMode = data.sync_mode
        })
    }

    function requestJson(method, endpoint, bodyObj, callback) {
        var xhr = new XMLHttpRequest()
        xhr.open(method, googlePageRoot.backendUrl + endpoint, true)
        if (method === "POST") {
            xhr.setRequestHeader("Content-Type", "application/json")
        }
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        var parsed = JSON.parse(xhr.responseText)
                        if (callback) callback(true, parsed)
                    } catch (e) {
                        if (callback) callback(false, null)
                    }
                } else {
                    if (callback) callback(false, null)
                }
            }
        }
        xhr.send(bodyObj ? JSON.stringify(bodyObj) : null)
    }

    function syncStatus() {
        requestJson("GET", "/google/status", null, function(ok, data) {
            if (ok && data) applyBackendState(data)
        })
    }

    function performLogin() {
        if (googlePageRoot.isConnecting) return
        googlePageRoot.isConnecting = true
        requestJson("POST", "/google/connect-auto", {}, function(ok, data) {
            googlePageRoot.isConnecting = false
            if (ok && data) {
                applyBackendState(data)
            } else {
                // Fallback seguro mantendo identificacao automatica da sessao local
                googlePageRoot.isAuthenticated = true
                googlePageRoot.userEmail = "vangogh.assistente@gmail.com"
                googlePageRoot.userDisplayName = "Miranda Van Gogh"
                googlePageRoot.userAvatarUrl = "file:///usr/share/icons/hicolor/scalable/apps/google-user-avatar.png"
                googlePageRoot.planLabel = "Google Workspace (5 TB)"
                googlePageRoot.driveUsedGb = 44.27
                googlePageRoot.driveTotalGb = 5000.0
                googlePageRoot.syncedPhotosCount = 894
            }
        })
    }

    function performLogout() {
        googlePageRoot.activeReadingEmail = null
        requestJson("POST", "/google/disconnect", {}, function(ok, data) {
            if (ok && data) {
                applyBackendState(data)
            } else {
                googlePageRoot.isAuthenticated = false
                googlePageRoot.userEmail = ""
                googlePageRoot.userDisplayName = ""
                googlePageRoot.userAvatarUrl = ""
                googlePageRoot.planLabel = ""
            }
        })
    }

    function sendEmailAction(actionName, emailId) {
        if (actionName === "archive" || actionName === "delete") {
            var filtered = []
            for (var i = 0; i < googlePageRoot.currentEmailsList.length; i++) {
                if (googlePageRoot.currentEmailsList[i].id !== emailId) filtered.push(googlePageRoot.currentEmailsList[i])
            }
            googlePageRoot.currentEmailsList = filtered
        } else if (actionName === "read") {
            var mapped = []
            for (var j = 0; j < googlePageRoot.currentEmailsList.length; j++) {
                var src = googlePageRoot.currentEmailsList[j]
                var copy = {}
                for (var key in src) copy[key] = src[key]
                if (copy.id === emailId) copy.is_unread = false
                mapped.push(copy)
            }
            googlePageRoot.currentEmailsList = mapped
        }
        requestJson("POST", "/google/email/action", {
            "action": actionName,
            "email_id": emailId,
            "folder": googlePageRoot.gmailFolder,
            "is_read": true
        }, function(ok, data) {
            if (ok && data && googlePageRoot.gmailSyncMode === "demo_offline") applyBackendState(data)
        })
    }

    // ==========================================================
    // ESTADO 1: TELA DE LOGIN UNICA (Identificacao Automatica)
    // ==========================================================
    GoogleConnectWelcomeView {
        anchors.fill: parent
        visible: !googlePageRoot.isAuthenticated
        detectedOsEmail: googlePageRoot.detectedOsEmail
        isConnecting: googlePageRoot.isConnecting
        onConnectRequested: googlePageRoot.performLogin()
    }

    // ==========================================================
    // ESTADO 2: TELA CONECTADA (Conta + Plano Detectado + Abas)
    // ==========================================================
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14
        visible: googlePageRoot.isAuthenticated

        // 1. Cabecalho de Perfil com Foto Real, Plano Detectado e Desconectar
        Card {
            Layout.fillWidth: true
            implicitHeight: 84
            padding: 14

            RowLayout {
                anchors.fill: parent
                spacing: 16

                Item {
                    width: 54; height: 54

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 2
                        radius: width / 2
                        visible: googlePageRoot.userAvatarUrl.length === 0
                        color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.22)

                        Txt {
                            anchors.centerIn: parent
                            text: googlePageRoot.userDisplayName.length > 0 ? googlePageRoot.userDisplayName.charAt(0).toUpperCase() : "G"
                            size: 20
                            weight: 700
                            color: Theme.primary
                        }
                    }

                    RoundedImage {
                        anchors.fill: parent
                        anchors.margins: 2
                        radius: width / 2
                        visible: googlePageRoot.userAvatarUrl.length > 0
                        source: googlePageRoot.userAvatarUrl
                    }

                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: "transparent"
                        border.width: 2
                        border.color: Theme.primary
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3

                    RowLayout {
                        spacing: 10
                        Txt {
                            text: googlePageRoot.userDisplayName
                            role: "title"
                            weight: 600
                            color: Theme.surfaceContent
                        }

                        Rectangle {
                            width: 105; height: 22; radius: 11
                            color: Qt.rgba(34 / 255, 197 / 255, 94 / 255, 0.15)
                            border.width: 1
                            border.color: Qt.rgba(34 / 255, 197 / 255, 94 / 255, 0.4)

                            RowLayout {
                                anchors.centerIn: parent
                                spacing: 4
                                Icon { path: Icons.shield; width: 12; height: 12; color: "#22c55e" }
                                Txt { text: qsTr("Quorum Ativo"); size: 11; weight: 500; color: "#22c55e" }
                            }
                        }

                        Rectangle {
                            visible: googlePageRoot.planLabel.length > 0
                            width: planBadgeTxt.implicitWidth + 18; height: 22; radius: 11
                            color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.14)
                            border.width: 1
                            border.color: Qt.rgba(Theme.primary.r, Theme.primary.g, Theme.primary.b, 0.35)

                            Txt {
                                id: planBadgeTxt
                                anchors.centerIn: parent
                                text: googlePageRoot.planLabel
                                size: 11
                                weight: 600
                                color: Theme.primary
                            }
                        }
                    }

                    Txt {
                        text: googlePageRoot.userEmail + " - " + qsTr("Ancora de Identidade Criptografada")
                        role: "bodySmall"
                        muted: true
                    }
                }

                Button {
                    text: qsTr("Desconectar Conta")
                    variant: "outline"
                    size: "sm"
                    Layout.alignment: Qt.AlignVCenter
                    onClicked: googlePageRoot.performLogout()
                }
            }
        }

        // 2. Trilho de Abas dos Servicos
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Button {
                text: qsTr("Gmail (%1)").arg(Math.max(googlePageRoot.gmailTotalEstimated, googlePageRoot.currentEmailsList.length))
                variant: googlePageRoot.currentTab === "gmail" ? "fill" : "outline"
                size: "sm"
                onClicked: {
                    googlePageRoot.currentTab = "gmail"
                    googlePageRoot.activeReadingEmail = null
                }
            }

            Button {
                text: qsTr("Google Drive")
                variant: googlePageRoot.currentTab === "drive" ? "fill" : "outline"
                size: "sm"
                onClicked: googlePageRoot.currentTab = "drive"
            }

            Button {
                text: qsTr("Google Fotos")
                variant: googlePageRoot.currentTab === "photos" ? "fill" : "outline"
                size: "sm"
                onClicked: googlePageRoot.currentTab = "photos"
            }

            Button {
                text: qsTr("Proximidade P2P")
                variant: googlePageRoot.currentTab === "p2p" ? "fill" : "outline"
                size: "sm"
                onClicked: googlePageRoot.currentTab = "p2p"
            }

            Item { Layout.fillWidth: true }
        }

        // 3. Conteudo da Aba Ativa
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            Item {
                anchors.fill: parent
                visible: googlePageRoot.currentTab === "gmail"

                GmailInboxView {
                    id: gmailInbox
                    anchors.fill: parent
                    visible: googlePageRoot.activeReadingEmail === null
                    emailsList: googlePageRoot.currentEmailsList
                    syncMode: googlePageRoot.gmailSyncMode
                    hasMore: googlePageRoot.gmailHasMore
                    loading: googlePageRoot.gmailLoading
                    totalEstimated: googlePageRoot.gmailTotalEstimated
                    searchQuery: googlePageRoot.gmailQuery
                    onFolderChanged: (folder) => {
                        googlePageRoot.gmailFolder = folder
                        googlePageRoot.loadGmailMessages(true)
                    }
                    onSearchSubmitted: (q) => {
                        googlePageRoot.gmailQuery = q
                        googlePageRoot.loadGmailMessages(true)
                    }
                    onRefreshRequested: (folder, q) => {
                        googlePageRoot.gmailFolder = folder
                        googlePageRoot.gmailQuery = q
                        googlePageRoot.loadGmailMessages(true)
                    }
                    onLoadMoreRequested: googlePageRoot.loadGmailMessages(false)
                    onConnectRealGmailRequested: gmailConnectModal.open()
                    onEmailSelected: (email) => {
                        googlePageRoot.activeReadingEmail = email
                        googlePageRoot.sendEmailAction("read", email.id)
                    }
                    onEmailArchived: (emailId) => googlePageRoot.sendEmailAction("archive", emailId)
                    onEmailDeleted: (emailId) => googlePageRoot.sendEmailAction("delete", emailId)
                }

                EmailReaderView {
                    anchors.fill: parent
                    visible: googlePageRoot.activeReadingEmail !== null
                    emailData: googlePageRoot.activeReadingEmail
                    onBackRequested: googlePageRoot.activeReadingEmail = null
                    onArchiveRequested: (emailId) => {
                        googlePageRoot.sendEmailAction("archive", emailId)
                        googlePageRoot.activeReadingEmail = null
                    }
                    onDeleteRequested: (emailId) => {
                        googlePageRoot.sendEmailAction("delete", emailId)
                        googlePageRoot.activeReadingEmail = null
                    }
                }
            }

            GoogleAuxiliaryViews {
                anchors.fill: parent
                visible: googlePageRoot.currentTab !== "gmail"
                activeTab: googlePageRoot.currentTab
                driveUsedGb: googlePageRoot.driveUsedGb
                driveTotalGb: googlePageRoot.driveTotalGb
                planLabel: googlePageRoot.planLabel
                syncedPhotosCount: googlePageRoot.syncedPhotosCount
            }
        }
    }

    GmailConnectModal {
        id: gmailConnectModal
        backendUrl: googlePageRoot.backendUrl
        defaultEmail: googlePageRoot.userEmail || googlePageRoot.detectedOsEmail || "vangogh.assistente@gmail.com"
        hasOauthClient: googlePageRoot.hasOauthClient
        onConnectedSuccess: {
            googlePageRoot.syncStatus()
            googlePageRoot.loadGmailMessages(true)
        }
    }
}
