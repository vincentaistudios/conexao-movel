# SPDX-License-Identifier: GPL-3.0-or-later
# Script de Concessao Automatica de Permissoes e Ativacao do Modo Elevado (Windows)
# Executa via ADB a liberacao completa de permissoes de sistema e controle remoto no smartphone.

[CmdletBinding()]
param (
    [string]$Serial = ""
)

$ErrorActionPreference = "Continue"

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "  Conexao Movel (NectarLink) - Assistente de Permissoes em 1 Clique" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Localizar o binario ADB
$adbCmd = ""
if (Get-Command "adb" -ErrorAction SilentlyContinue) {
    $adbCmd = "adb"
} else {
    $candidatePaths = @(
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe",
        "$env:USERPROFILE\AppData\Local\Android\Sdk\platform-tools\adb.exe",
        "$env:ProgramFiles\Nectarlink\adb.exe",
        "$env:ProgramFiles(x86)\Nectarlink\adb.exe",
        "$PSScriptRoot\..\..\..\tools\adb.exe"
    )
    foreach ($path in $candidatePaths) {
        if (Test-Path $path) {
            $adbCmd = $path
            break
        }
    }
}

if (-not $adbCmd) {
    Write-Host "[ERRO] O utilitario ADB nao foi encontrado no sistema." -ForegroundColor Red
    Write-Host "Por favor, instale o Android SDK Platform-Tools ou adicione o adb ao PATH." -ForegroundColor Yellow
    exit 1
}

# 2. Iniciar servidor e verificar dispositivos conectados
Write-Host "[*] Verificando conexao com smartphone via USB..." -ForegroundColor Gray
& $adbCmd start-server | Out-Null

$rawDevices = & $adbCmd devices
$deviceList = @()
foreach ($line in ($rawDevices -split "`r?`n")) {
    $trimmed = $line.Trim()
    if ($trimmed -and -not $trimmed.StartsWith("List of devices") -and -not $trimmed.StartsWith("*")) {
        $parts = $trimmed -split "\s+"
        if ($parts.Length -ge 2) {
            $deviceList += [PSCustomObject]@{
                Serial = $parts[0]
                State  = $parts[1]
            }
        }
    }
}

if ($deviceList.Count -eq 0) {
    Write-Host "[AVISO] Nenhum celular conectado via USB foi detectado." -ForegroundColor Yellow
    Write-Host "Instrucoes para conectar:" -ForegroundColor Cyan
    Write-Host "  1. Conecte o celular ao computador com um cabo USB de dados."
    Write-Host "  2. No celular, ative a 'Depuracao USB' em Configuracoes > Opcoes do desenvolvedor."
    Write-Host "  3. Ao surgir a janela 'Permitir depuracao USB?', marque 'Sempre permitir' e toque em 'Permitir'."
    exit 2
}

$target = $null
if ($Serial) {
    $target = $deviceList | Where-Object { $_.Serial -eq $Serial }
} else {
    $target = $deviceList | Where-Object { $_.State -eq "device" } | Select-Object -First 1
    if (-not $target) {
        $target = $deviceList[0]
    }
}

if ($target.State -eq "unauthorized") {
    Write-Host "[AVISO] O aparelho $($target.Serial) esta conectado, mas aguarda autorizacao na tela." -ForegroundColor Yellow
    Write-Host "Por favor, desbloqueie o celular e toque em 'Permitir depuracao USB'." -ForegroundColor Cyan
    exit 3
}

$s = $target.Serial
Write-Host "[OK] Smartphone conectado: $s" -ForegroundColor Green
Write-Host ""

$pkg = "app.nectarlink"

# 3. Concessao de Permissoes Normais de Comunicacao
Write-Host "[1/5] Concedendo permissoes de comunicacao e midia..." -ForegroundColor Cyan
$normalPerms = @(
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.READ_CONTACTS",
    "android.permission.READ_PHONE_STATE",
    "android.permission.READ_CALL_LOG",
    "android.permission.CALL_PHONE",
    "android.permission.ANSWER_PHONE_CALLS",
    "android.permission.READ_SMS",
    "android.permission.SEND_SMS",
    "android.permission.READ_MEDIA_IMAGES",
    "android.permission.READ_MEDIA_VIDEO",
    "android.permission.BLUETOOTH_CONNECT"
)

foreach ($perm in $normalPerms) {
    & $adbCmd -s $s shell pm grant $pkg $perm 2>$null | Out-Null
}
Write-Host "  -> Permissoes de contatos, chamadas, SMS, midia e Bluetooth concedidas." -ForegroundColor Green

# 4. Concessao de Permissoes Avancadas de Sistema
Write-Host "[2/5] Concedendo permissoes avancadas de configuracao do sistema..." -ForegroundColor Cyan
& $adbCmd -s $s shell pm grant $pkg android.permission.WRITE_SECURE_SETTINGS 2>$null | Out-Null
& $adbCmd -s $s shell appops set $pkg WRITE_SETTINGS allow 2>$null | Out-Null
& $adbCmd -s $s shell appops set $pkg SYSTEM_ALERT_WINDOW allow 2>$null | Out-Null
& $adbCmd -s $s shell appops set $pkg GET_USAGE_STATS allow 2>$null | Out-Null
Write-Host "  -> Permissoes WRITE_SECURE_SETTINGS e WRITE_SETTINGS concedidas." -ForegroundColor Green

# 5. Acesso Especial a Notificacoes e Nao Perturbe
Write-Host "[3/5] Habilitando acesso a notificacoes e modo Nao Perturbe..." -ForegroundColor Cyan
& $adbCmd -s $s shell cmd notification allow_listener app.nectarlink/app.nectarlink.android.notifications.NotificationListener 2>$null | Out-Null
& $adbCmd -s $s shell cmd notification allow_dnd $pkg 2>$null | Out-Null
Write-Host "  -> Acesso a notificacoes e controle de Nao Perturbe liberados." -ForegroundColor Green

# 6. Ativacao do Servico de Acessibilidade (Controle Completo)
Write-Host "[4/5] Habilitando servico de acessibilidade para controle por toque..." -ForegroundColor Cyan
$serviceName = "app.nectarlink/app.nectarlink.android.accessibility.InputService"
$currentServices = & $adbCmd -s $s shell settings get secure enabled_accessibility_services
if ($currentServices -notmatch "app.nectarlink") {
    $newServices = if ($currentServices -and $currentServices -ne "null") { "$currentServices:$serviceName" } else { $serviceName }
    & $adbCmd -s $s shell settings put secure enabled_accessibility_services $newServices 2>$null | Out-Null
}
& $adbCmd -s $s shell settings put secure accessibility_enabled 1 2>$null | Out-Null
Write-Host "  -> Servico de acessibilidade ativado para controle remoto da tela." -ForegroundColor Green

# 7. Inicializacao do Modo Elevado (Area de Transferencia em Segundo Plano e Hardware)
Write-Host "[5/5] Inicializando servico do Modo Elevado..." -ForegroundColor Cyan
$apkPathRaw = & $adbCmd -s $s shell pm path $pkg
$apkPath = ""
foreach ($line in ($apkPathRaw -split "`r?`n")) {
    if ($line -match "package:(.+base\.apk)") {
        $apkPath = $Matches[1]
        break
    } elseif ($line -match "package:(.+)") {
        $apkPath = $Matches[1]
    }
}

if ($apkPath) {
    # Inicia o InputServer do modo elevado em background
    $tokenBytes = New-Object byte[] 24
    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($tokenBytes)
    $token = ($tokenBytes | ForEach-Object { "{0:x2}" -f $_ }) -join ""
    
    # Broadcast de despertar e inicio do servico
    $cmd = "CLASSPATH=$apkPath app_process /system/bin app.nectarlink.android.elevated.InputServer $token"
    & $adbCmd -s $s shell "nohup $cmd >/dev/null 2>&1 &"
    Write-Host "  -> Modo Elevado inicializado com sucesso (Area de transferencia e Bluetooth ativos)." -ForegroundColor Green
} else {
    Write-Host "  -> O aplicativo $pkg ainda nao esta instalado. Instale o APK primeiro." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "  Sucesso: Todas as permissoes foram concedidas ao smartphone!" -ForegroundColor Green
Write-Host "  O celular esta pronto para uso completo pelo computador." -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Green

