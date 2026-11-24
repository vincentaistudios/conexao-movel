<#
.SYNOPSIS
  Configura Wake-on-LAN (WoL), gerenciamento de energia e regras de rede no Windows.

.DESCRIPTION
  Este script e executado durante a instalacao do Conexao Movel (NectarLink)
  para preparar o sistema operacional para acordar via pacotes magicos (Magic Packet):
  1. Desativa a Inicializacao Rapida (Fast Startup / HiberbootEnabled = 0).
  2. Habilita Wake-on-LAN nos adaptadores fisicos de rede Ethernet.
  3. Desativa o desligamento do adaptador em desconexao.
  4. Configura as chaves de registro do driver de rede (*WakeOnMagicPacket e PnPCapabilities).
  5. Adiciona a regra no Firewall do Windows para a porta UDP 9 (Wake-on-LAN).

.NOTES
  Licenca: GPL-3.0-or-later
  Padrão: Conexao Movel / NectarLink
  Requisito: Privilegios de Administrador
#>

[CmdletBinding()]
param(
    [switch]$Quiet
)

$ErrorActionPreference = 'SilentlyContinue'

function Write-LogMessage {
    param([string]$Message)
    if (-not $Quiet) {
        Write-Host "[Conexao Movel] $Message"
    }
}

Write-LogMessage "Iniciando configuracao de Wake-on-LAN e gerenciamento de energia..."

# 1. Desativar Inicializacao Rapida (Fast Startup)
# A inicializacao rapida mantem o computador em estado hibrido que impede placas de rede
# de responder a Magic Packets no estado de energia S5 (desligado).
try {
    $powerRegPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power'
    if (Test-Path $powerRegPath) {
        Set-ItemProperty -Path $powerRegPath -Name 'HiberbootEnabled' -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue
        Write-LogMessage "Inicializacao rapida (Fast Startup) desativada no registro com sucesso."
    }
} catch {
    Write-LogMessage "Aviso: Falha ao atualizar configuracao de inicializacao rapida: $_"
}

# 2. Identificar adaptadores fisicos de rede reais
# Filtra placas virtuais, VPNs, emuladores e pontes de conteineres
$adapters = @()
try {
    $adapters = Get-NetAdapter -Physical -ErrorAction SilentlyContinue | Where-Object {
        $_.Status -ne 'Disabled' -and
        $_.InterfaceDescription -notmatch 'Virtual|VPN|Hamachi|Radmin|Hyper-V|Docker|Podman'
    }
} catch {
    Write-LogMessage "Aviso: Nao foi possivel consultar adaptadores de rede fisicos: $_"
}

if ($adapters.Count -gt 0) {
    Write-LogMessage ("Foram encontrados {0} adaptadores fisicos elegiveis." -f $adapters.Count)

    foreach ($adapter in $adapters) {
        $adapterName = $adapter.Name
        Write-LogMessage ("Configurando adaptador: {0} ({1})" -f $adapterName, $adapter.InterfaceDescription)

        # Habilitar Wake on Magic Packet e manter adaptador alimentado
        Set-NetAdapterPowerManagement -Name $adapterName -WakeOnMagicPacket Enabled -DeviceSleepOnDisconnect Disabled -ErrorAction SilentlyContinue

        # Definir propriedades avancadas do driver de rede
        Set-NetAdapterAdvancedProperty -Name $adapterName -DisplayName 'Wake on Magic Packet' -DisplayValue 'Enabled' -ErrorAction SilentlyContinue
        Set-NetAdapterAdvancedProperty -Name $adapterName -DisplayName 'Wake on pattern match' -DisplayValue 'Enabled' -ErrorAction SilentlyContinue
        Set-NetAdapterAdvancedProperty -Name $adapterName -RegistryKeyword '*WakeOnMagicPacket' -RegistryValue '1' -ErrorAction SilentlyContinue
    }

    # 3. Atualizar chaves de registro da classe de adaptadores de rede
    # HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}
    $netClassPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}'
    if (Test-Path $netClassPath) {
        Get-ChildItem -Path $netClassPath -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match '^\d{4}$' } | ForEach-Object {
            $subKeyPath = $_.PSPath
            $props = Get-ItemProperty -Path $subKeyPath -ErrorAction SilentlyContinue
            $desc = $props.DriverDesc
            $guid = $props.NetCfgInstanceId

            $isTarget = $adapters | Where-Object {
                ($guid -and $_.InterfaceGuid -and ($guid -eq $_.InterfaceGuid)) -or
                ($desc -and $_.InterfaceDescription -and ($desc -eq $_.InterfaceDescription))
            }

            if ($isTarget) {
                Set-ItemProperty -Path $subKeyPath -Name '*WakeOnMagicPacket' -Value '1' -Type String -Force -ErrorAction SilentlyContinue
                Set-ItemProperty -Path $subKeyPath -Name 'PnPCapabilities' -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue
                Write-LogMessage ("Registro atualizado para a subchave: {0} ({1})" -f $_.PSChildName, $desc)
            }
        }
    }
} else {
    Write-LogMessage "Nenhum adaptador fisico Ethernet/Wi-Fi requereu ajustes adicionais."
}

# 4. Configurar regra no Firewall do Windows para UDP 9 (Wake-on-LAN)
try {
    $ruleName = 'Nectarlink Wake-on-LAN'
    # Remover regra legada ou duplicada se existente
    & netsh.exe advfirewall firewall delete rule name=$ruleName 2>$null | Out-Null

    # Adicionar regra permitindo pacotes UDP 9 nos perfis Private e Domain
    & netsh.exe advfirewall firewall add rule name=$ruleName `
        dir=in `
        action=allow `
        protocol=UDP `
        localport=9 `
        enable=yes `
        profile=private,domain `
        description='Permite acordar este PC via rede local pelo Conexao Movel' 2>$null | Out-Null

    Write-LogMessage "Regra de Firewall adicionada para a porta UDP 9 (Wake-on-LAN)."
} catch {
    Write-LogMessage "Aviso: Falha ao configurar regra de Firewall: $_"
}

Write-LogMessage "Configuracao de Wake-on-LAN e gerenciamento de energia concluida com sucesso."
exit 0
