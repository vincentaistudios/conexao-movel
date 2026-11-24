#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Script de Concessao Automatica de Permissoes e Ativacao do Modo Elevado (Linux)
# Executa via ADB a liberacao completa de permissoes de sistema e controle remoto no smartphone.

set -euo pipefail

PKG="app.nectarlink"

echo "===================================================================="
echo "  Conexao Movel (NectarLink) - Assistente de Permissoes em 1 Clique"
echo "===================================================================="
echo ""

# 1. Localizar binario adb
ADB_CMD=""
if command -v adb >/dev/null 2>&1; then
    ADB_CMD="adb"
elif [ -x "$HOME/Android/Sdk/platform-tools/adb" ]; then
    ADB_CMD="$HOME/Android/Sdk/platform-tools/adb"
elif [ -x "/usr/lib/android-sdk/platform-tools/adb" ]; then
    ADB_CMD="/usr/lib/android-sdk/platform-tools/adb"
fi

if [ -z "$ADB_CMD" ]; then
    echo "[ERRO] O utilitario ADB nao foi encontrado no sistema."
    echo "Instale o pacote com: sudo apt install adb (Debian/Ubuntu) ou consulte a documentacao."
    exit 1
fi

# 2. Iniciar servidor e verificar dispositivos
echo "[*] Verificando conexao com smartphone via USB..."
"$ADB_CMD" start-server >/dev/null 2>&1 || true

DEVICES_RAW=$("$ADB_CMD" devices | grep -v "^List of devices" | grep -v "^\*" | grep -v "^$" || true)

if [ -z "$DEVICES_RAW" ]; then
    echo "[AVISO] Nenhum celular conectado via USB foi detectado."
    echo "Instrucoes para conectar:"
    echo "  1. Conecte o celular ao computador com um cabo USB de dados."
    echo "  2. No celular, ative a 'Depuracao USB' em Configuracoes > Opcoes do desenvolvedor."
    echo "  3. Ao surgir a janela 'Permitir depuracao USB?', marque 'Sempre permitir' e toque em 'Permitir'."
    exit 2
fi

SERIAL=$(echo "$DEVICES_RAW" | head -n1 | awk '{print $1}')
STATE=$(echo "$DEVICES_RAW" | head -n1 | awk '{print $2}')

if [ "$STATE" = "unauthorized" ]; then
    echo "[AVISO] O aparelho $SERIAL esta conectado, mas aguarda autorizacao na tela."
    echo "Por favor, desbloqueie o celular e toque em 'Permitir depuracao USB'."
    exit 3
fi

echo "[OK] Smartphone conectado: $SERIAL"
echo ""

# 3. Permissoes normais de comunicacao e midia
echo "[1/5] Concedendo permissoes de comunicacao e midia..."
NORMAL_PERMS=(
    "android.permission.POST_NOTIFICATIONS"
    "android.permission.READ_CONTACTS"
    "android.permission.READ_PHONE_STATE"
    "android.permission.READ_CALL_LOG"
    "android.permission.CALL_PHONE"
    "android.permission.ANSWER_PHONE_CALLS"
    "android.permission.READ_SMS"
    "android.permission.SEND_SMS"
    "android.permission.READ_MEDIA_IMAGES"
    "android.permission.READ_MEDIA_VIDEO"
    "android.permission.BLUETOOTH_CONNECT"
)

for perm in "${NORMAL_PERMS[@]}"; do
    "$ADB_CMD" -s "$SERIAL" shell pm grant "$PKG" "$perm" >/dev/null 2>&1 || true
done
echo "  -> Permissoes de contatos, chamadas, SMS, midia e Bluetooth concedidas."

# 4. Permissoes avancadas de sistema
echo "[2/5] Concedendo permissoes avancadas de configuracao do sistema..."
"$ADB_CMD" -s "$SERIAL" shell pm grant "$PKG" android.permission.WRITE_SECURE_SETTINGS >/dev/null 2>&1 || true
"$ADB_CMD" -s "$SERIAL" shell appops set "$PKG" WRITE_SETTINGS allow >/dev/null 2>&1 || true
"$ADB_CMD" -s "$SERIAL" shell appops set "$PKG" SYSTEM_ALERT_WINDOW allow >/dev/null 2>&1 || true
"$ADB_CMD" -s "$SERIAL" shell appops set "$PKG" GET_USAGE_STATS allow >/dev/null 2>&1 || true
echo "  -> Permissoes WRITE_SECURE_SETTINGS e WRITE_SETTINGS concedidas."

# 5. Acesso especial a notificacoes e Nao Perturbe
echo "[3/5] Habilitando acesso a notificacoes e modo Nao Perturbe..."
"$ADB_CMD" -s "$SERIAL" shell cmd notification allow_listener "$PKG/app.nectarlink.android.notifications.NotificationListener" >/dev/null 2>&1 || true
"$ADB_CMD" -s "$SERIAL" shell cmd notification allow_dnd "$PKG" >/dev/null 2>&1 || true
echo "  -> Acesso a notificacoes e controle de Nao Perturbe liberados."

# 6. Ativacao do Servico de Acessibilidade (Controle)
echo "[4/5] Habilitando servico de acessibilidade para controle por toque..."
SERVICE_NAME="$PKG/app.nectarlink.android.accessibility.InputService"
CURRENT_SERVICES=$("$ADB_CMD" -s "$SERIAL" shell settings get secure enabled_accessibility_services || true)

if ! echo "$CURRENT_SERVICES" | grep -q "$PKG"; then
    if [ -n "$CURRENT_SERVICES" ] && [ "$CURRENT_SERVICES" != "null" ]; then
        NEW_SERVICES="${CURRENT_SERVICES}:${SERVICE_NAME}"
    else
        NEW_SERVICES="$SERVICE_NAME"
    fi
    "$ADB_CMD" -s "$SERIAL" shell settings put secure enabled_accessibility_services "$NEW_SERVICES" >/dev/null 2>&1 || true
fi
"$ADB_CMD" -s "$SERIAL" shell settings put secure accessibility_enabled 1 >/dev/null 2>&1 || true
echo "  -> Servico de acessibilidade ativado para controle remoto da tela."

# 7. Inicializacao do Modo Elevado (Area de Transferencia em Segundo Plano e Hardware)
echo "[5/5] Inicializando servico do Modo Elevado..."
APK_PATH=$("$ADB_CMD" -s "$SERIAL" shell pm path "$PKG" 2>/dev/null | grep -E "base\.apk" | head -n1 | cut -d: -f2 || true)
if [ -z "$APK_PATH" ]; then
    APK_PATH=$("$ADB_CMD" -s "$SERIAL" shell pm path "$PKG" 2>/dev/null | head -n1 | cut -d: -f2 || true)
fi

if [ -n "$APK_PATH" ]; then
    TOKEN=$(od -vN 24 -An -tx1 /dev/urandom | tr -d ' \n')
    CMD="CLASSPATH=$APK_PATH app_process /system/bin app.nectarlink.android.elevated.InputServer $TOKEN"
    "$ADB_CMD" -s "$SERIAL" shell "nohup $CMD >/dev/null 2>&1 &" || true
    echo "  -> Modo Elevado inicializado com sucesso (Area de transferencia e Bluetooth ativos)."
else
    echo "  -> O aplicativo $PKG ainda nao esta instalado. Instale o APK primeiro."
fi

echo ""
echo "===================================================================="
echo "  Sucesso: Todas as permissoes foram concedidas ao smartphone!"
echo "  O celular esta pronto para uso completo pelo computador."
echo "===================================================================="

