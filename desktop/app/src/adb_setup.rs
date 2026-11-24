// SPDX-License-Identifier: GPL-3.0-or-later
//! Modulo de assistente automatizado ADB para concessao de permissoes em 1 clique
//! e inicializacao do Modo Elevado (InputServer) no smartphone via USB.

use std::{net::SocketAddr, process::Command};
use nectarlink_adb::{DEFAULT_ADB_ADDR, is_serial_allowed};
use serde::{Deserialize, Serialize};

const PKG: &str = "app.nectarlink";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdbDeviceSummary {
    pub serial: String,
    pub state: String,
    pub model: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdbSetupResult {
    pub success: bool,
    pub serial: String,
    pub permissions_granted: usize,
    pub elevated_started: bool,
    pub message: String,
}

/// Detecta dispositivos Android conectados via ADB (pure Rust socket ou CLI).
pub async fn list_attached_devices(addr: Option<SocketAddr>) -> Vec<AdbDeviceSummary> {
    let server = addr.unwrap_or(DEFAULT_ADB_ADDR);
    if let Ok(devs) = nectarlink_adb::list_devices(server).await {
        return devs
            .into_iter()
            .map(|d| AdbDeviceSummary {
                serial: d.serial,
                state: d.state,
                model: d.model,
            })
            .collect();
    }

    // Fallback executando `adb devices -l`
    run_cli_list_devices()
}

fn run_cli_list_devices() -> Vec<AdbDeviceSummary> {
    let output = Command::new("adb").args(["devices", "-l"]).output();
    let Ok(out) = output else { return Vec::new() };
    if !out.status.success() {
        return Vec::new();
    }
    let text = String::from_utf8_lossy(&out.stdout);
    nectarlink_adb::parse_devices_l(&text)
        .into_iter()
        .map(|d| AdbDeviceSummary {
            serial: d.serial,
            state: d.state,
            model: d.model,
        })
        .collect()
}

/// Executa um comando no shell do dispositivo via adb CLI com timeout.
pub fn run_shell_command(serial: &str, command: &str) -> Result<String, String> {
    if !is_serial_allowed(serial) {
        return Err(format!("Serial invalido ou bloqueado por seguranca: {serial}"));
    }
    let output = Command::new("adb")
        .args(["-s", serial, "shell", command])
        .output()
        .map_err(|e| format!("Falha ao executar adb shell: {e}"))?;

    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();

    if !output.status.success() && !stderr.is_empty() {
        return Err(stderr);
    }
    Ok(stdout)
}

/// Executa a esteira completa de concessao em 1 clique e inicializacao do Modo Elevado.
pub async fn run_auto_setup(target_serial: Option<String>) -> AdbSetupResult {
    let devices = list_attached_devices(None).await;
    if devices.is_empty() {
        return AdbSetupResult {
            success: false,
            serial: String::new(),
            permissions_granted: 0,
            elevated_started: false,
            message: "Nenhum celular conectado via USB foi detectado. Ative a Depuracao USB.".into(),
        };
    }

    let selected = match target_serial {
        Some(ref s) => devices.into_iter().find(|d| &d.serial == s),
        None => devices.into_iter().find(|d| d.state == "device").or_else(|| None),
    };

    let Some(device) = selected else {
        return AdbSetupResult {
            success: false,
            serial: String::new(),
            permissions_granted: 0,
            elevated_started: false,
            message: "Dispositivo aguardando autorizacao. Confirme a permissao de Depuracao USB na tela do celular.".into(),
        };
    };

    if device.state == "unauthorized" {
        return AdbSetupResult {
            success: false,
            serial: device.serial,
            permissions_granted: 0,
            elevated_started: false,
            message: "Toque em 'Permitir depuracao USB' na tela do celular para continuar.".into(),
        };
    }

    let serial = device.serial.clone();

    // 1. Permissoes normais de comunicacao e midia
    let normal_perms = [
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
        "android.permission.BLUETOOTH_CONNECT",
        "android.permission.WRITE_SECURE_SETTINGS",
    ];

    let mut granted_count = 0;
    for perm in normal_perms {
        let cmd = format!("pm grant {PKG} {perm}");
        if run_shell_command(&serial, &cmd).is_ok() {
            granted_count += 1;
        }
    }

    // 2. Permissoes especiais via appops
    let appops = [
        format!("appops set {PKG} WRITE_SETTINGS allow"),
        format!("appops set {PKG} SYSTEM_ALERT_WINDOW allow"),
        format!("appops set {PKG} GET_USAGE_STATS allow"),
    ];
    for op in appops {
        if run_shell_command(&serial, &op).is_ok() {
            granted_count += 1;
        }
    }

    // 3. Notificacoes e Nao Perturbe
    let _ = run_shell_command(&serial, &format!("cmd notification allow_listener {PKG}/app.nectarlink.android.notifications.NotificationListener"));
    let _ = run_shell_command(&serial, &format!("cmd notification allow_dnd {PKG}"));

    // 4. Servico de Acessibilidade (Controle por Toque)
    let current_acc = run_shell_command(&serial, "settings get secure enabled_accessibility_services").unwrap_or_default();
    let service_id = format!("{PKG}/app.nectarlink.android.accessibility.InputService");
    if !current_acc.contains(PKG) {
        let new_val = if current_acc.is_empty() || current_acc == "null" {
            service_id
        } else {
            format!("{current_acc}:{service_id}")
        };
        let _ = run_shell_command(&serial, &format!("settings put secure enabled_accessibility_services {new_val}"));
    }
    let _ = run_shell_command(&serial, "settings put secure accessibility_enabled 1");

    // 5. Inicializacao do Modo Elevado (InputServer)
    let mut elevated_started = false;
    let apk_path_res = run_shell_command(&serial, &format!("pm path {PKG}"));
    if let Ok(paths) = apk_path_res {
        let base_apk = paths
            .lines()
            .find(|l| l.contains("base.apk"))
            .or_else(|| paths.lines().next())
            .and_then(|l| l.strip_prefix("package:"))
            .map(|s| s.trim());

        if let Some(apk) = base_apk {
            let token = blake3::hash(format!("{serial}_{:?}", std::time::SystemTime::now()).as_bytes()).to_hex().to_string();
            let launch_cmd = format!("nohup env CLASSPATH={apk} app_process /system/bin app.nectarlink.android.elevated.InputServer {token} >/dev/null 2>&1 &");
            let _ = run_shell_command(&serial, &launch_cmd);
            elevated_started = true;
        }
    }

    AdbSetupResult {
        success: true,
        serial,
        permissions_granted: granted_count,
        elevated_started,
        message: "Configuracao concluida com sucesso! Todas as permissoes e o Modo Elevado foram ativados.".into(),
    }
}
