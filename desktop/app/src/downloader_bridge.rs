// SPDX-License-Identifier: GPL-3.0-or-later
//! Ponte HTTP local segura entre o canal P2P (`media.download_rpc`) e o
//! servidor Python de downloads em `127.0.0.1:28795`.

use std::{
    collections::HashSet,
    io::{Read, Write},
    net::{SocketAddr, TcpStream},
    path::PathBuf,
    sync::{Mutex, OnceLock},
    time::Duration,
};

use nectarlink_core::DeviceId;
use serde_json::{Map, Value};

const DOWNLOADER_PORT: u16 = 28795;
const UNAVAILABLE_MSG: &str = "Serviço local de downloads indisponível na porta 28795";
const CONNECT_TIMEOUT: Duration = Duration::from_secs(2);
const MAX_CONNECT_RETRIES: usize = 3;
const INITIAL_RETRY_BACKOFF: Duration = Duration::from_millis(50);
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(5);
const INSPECT_TIMEOUT: Duration = Duration::from_secs(30);
const MAX_HTTP_RESPONSE_BYTES: usize = 512 * 1024 + 16 * 1024;
const ALLOWED_OPS: &[&str] = &["health", "inspect", "start", "status", "history", "cancel"];

static DISPATCHED_TASKS: OnceLock<Mutex<HashSet<String>>> = OnceLock::new();

fn dispatched_tasks() -> &'static Mutex<HashSet<String>> {
    DISPATCHED_TASKS.get_or_init(|| Mutex::new(HashSet::new()))
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct PreparedRequest {
    method: &'static str,
    path: String,
    body: Option<String>,
    timeout: Duration,
}

/// Executa uma operacao RPC autenticada no servico local de downloads (`127.0.0.1:28795`).
pub fn handle_rpc(peer: &DeviceId, op: &str, payload_json: &str) -> Result<String, String> {
    let req = prepare_request(peer, op, payload_json)?;
    let addr = SocketAddr::from(([127, 0, 0, 1], DOWNLOADER_PORT));
    let response = execute_http(addr, &req)?;
    if op == "status" {
        maybe_dispatch_phone_files(peer, &response);
    }
    Ok(response)
}

fn validate_http_url(url: &str) -> Result<(), String> {
    if url.is_empty() || url.len() > 4096 || url.chars().any(|c| c.is_whitespace() || c.is_control()) {
        return Err("URL inválida: espaços e caracteres de controle não são permitidos".into());
    }
    let lower = url.get(..8).map(str::to_ascii_lowercase).unwrap_or_default();
    let after_scheme = if lower.starts_with("https://") {
        &url[8..]
    } else if lower.starts_with("http://") {
        &url[7..]
    } else {
        return Err("URL inválida: informe um endereço http:// ou https://".into());
    };
    let authority = after_scheme.split(['/', '?', '#']).next().unwrap_or("");
    if authority.is_empty() || authority.contains('@') {
        return Err("URL inválida: credenciais embutidas ou host ausente não são permitidos".into());
    }
    let host = authority.split(':').next().unwrap_or("").trim_matches(['[', ']']).to_ascii_lowercase();
    if matches!(host.as_str(), "" | "localhost" | "127.0.0.1" | "::1" | "0.0.0.0" | "169.254.169.254") {
        return Err("URL inválida: endereços locais internos não são permitidos".into());
    }
    Ok(())
}

fn sanitize_task_id(raw: &str) -> Result<String, String> {
    let id = raw.trim();
    let valid = !id.is_empty()
        && id.len() <= 64
        && id.bytes().all(|b| b.is_ascii_alphanumeric() || matches!(b, b'_' | b'-'));
    if !valid {
        return Err("Identificador task_id inválido".into());
    }
    Ok(id.to_owned())
}

fn parse_obj(payload_json: &str) -> Result<Map<String, Value>, String> {
    let parsed: Value = serde_json::from_str(payload_json).map_err(|_| "Payload JSON inválido".to_owned())?;
    parsed.as_object().cloned().ok_or_else(|| "Payload deve ser um objeto JSON".to_owned())
}

fn extract_str<'a>(obj: &'a Map<String, Value>, key: &str) -> &'a str {
    obj.get(key).and_then(Value::as_str).unwrap_or("")
}

fn prepare_request(peer: &DeviceId, op: &str, payload_json: &str) -> Result<PreparedRequest, String> {
    if !ALLOWED_OPS.contains(&op) {
        return Err(format!("Operação não permitida: {op}"));
    }
    match op {
        "health" => Ok(PreparedRequest { method: "GET", path: "/health".into(), body: None, timeout: DEFAULT_TIMEOUT }),
        "history" => Ok(PreparedRequest { method: "GET", path: "/history".into(), body: None, timeout: DEFAULT_TIMEOUT }),
        "status" => {
            let task_id = sanitize_task_id(extract_str(&parse_obj(payload_json)?, "task_id"))?;
            Ok(PreparedRequest { method: "GET", path: format!("/status?task_id={task_id}"), body: None, timeout: DEFAULT_TIMEOUT })
        }
        "inspect" => {
            let obj = parse_obj(payload_json)?;
            let url = extract_str(&obj, "url").trim();
            validate_http_url(url)?;
            Ok(PreparedRequest {
                method: "POST",
                path: "/inspect".into(),
                body: Some(serde_json::json!({ "url": url }).to_string()),
                timeout: INSPECT_TIMEOUT,
            })
        }
        "start" => {
            let obj = parse_obj(payload_json)?;
            let url = extract_str(&obj, "url").trim();
            validate_http_url(url)?;
            let format = match extract_str(&obj, "format").to_ascii_lowercase().as_str() {
                "audio" => "audio",
                "both" => "both",
                _ => "video",
            };
            let destination = match extract_str(&obj, "destination").to_ascii_lowercase().as_str() {
                "pc" => "pc",
                "both" => "both",
                _ => "phone",
            };
            let body = serde_json::json!({
                "url": url,
                "format": format,
                "destination": destination,
                "device_id": peer.to_string(),
            });
            Ok(PreparedRequest { method: "POST", path: "/download".into(), body: Some(body.to_string()), timeout: DEFAULT_TIMEOUT })
        }
        "cancel" => {
            let task_id = sanitize_task_id(extract_str(&parse_obj(payload_json)?, "task_id"))?;
            Ok(PreparedRequest { method: "POST", path: "/cancel".into(), body: Some(serde_json::json!({ "task_id": task_id }).to_string()), timeout: DEFAULT_TIMEOUT })
        }
        _ => Err(format!("Operação não permitida: {op}")),
    }
}

/// Estabelece conexao TCP com o servico local realizando retentativas com backoff
/// rapido caso o servidor na porta 28795 esteja em processo de inicializacao.
fn connect_with_retry(addr: &SocketAddr) -> Result<TcpStream, String> {
    let mut backoff = INITIAL_RETRY_BACKOFF;
    for attempt in 0..=MAX_CONNECT_RETRIES {
        match TcpStream::connect_timeout(addr, CONNECT_TIMEOUT) {
            Ok(stream) => return Ok(stream),
            Err(_) => {
                if attempt < MAX_CONNECT_RETRIES {
                    std::thread::sleep(backoff);
                    backoff = (backoff * 2).min(Duration::from_millis(200));
                }
            }
        }
    }
    Err(UNAVAILABLE_MSG.to_owned())
}

fn execute_http(addr: SocketAddr, req: &PreparedRequest) -> Result<String, String> {
    let mut stream = connect_with_retry(&addr)?;
    let _ = stream.set_read_timeout(Some(req.timeout));
    let _ = stream.set_write_timeout(Some(DEFAULT_TIMEOUT));
    let raw_req = match req.body.as_deref() {
        Some(body) => format!(
            "{} {} HTTP/1.1\r\nHost: 127.0.0.1:{DOWNLOADER_PORT}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{body}",
            req.method, req.path, body.len()
        ),
        None => format!(
            "{} {} HTTP/1.1\r\nHost: 127.0.0.1:{DOWNLOADER_PORT}\r\nConnection: close\r\n\r\n",
            req.method, req.path
        ),
    };
    stream
        .write_all(raw_req.as_bytes())
        .and_then(|_| stream.flush())
        .map_err(|e| format!("Falha ao enviar requisição local de download: {e}"))?;
    let mut raw_resp = Vec::new();
    stream
        .take((MAX_HTTP_RESPONSE_BYTES + 1) as u64)
        .read_to_end(&mut raw_resp)
        .map_err(|e| format!("Falha ao ler resposta do serviço de downloads: {e}"))?;
    if raw_resp.len() > MAX_HTTP_RESPONSE_BYTES {
        return Err("Resposta do serviço de downloads excedeu o limite permitido".into());
    }
    let split_pos = raw_resp.windows(4).position(|w| w == b"\r\n\r\n").ok_or_else(|| "Resposta HTTP inválida".to_owned())?;
    let head = std::str::from_utf8(&raw_resp[..split_pos]).map_err(|_| "Cabeçalho HTTP inválido".to_owned())?;
    let status = head
        .lines()
        .next()
        .and_then(|l| l.split_whitespace().nth(1))
        .and_then(|c| c.parse::<u16>().ok())
        .ok_or_else(|| "Status HTTP inválido".to_owned())?;
    let body = std::str::from_utf8(&raw_resp[split_pos + 4..]).map_err(|_| "Corpo não é UTF-8".to_owned())?;
    if status >= 500 {
        return Err(format!("Erro interno ({status}) no serviço local de downloads"));
    }
    Ok(body.to_owned())
}

fn extract_completed_phone_files(body: &str) -> Option<(String, Vec<PathBuf>)> {
    let val: Value = serde_json::from_str(body).ok()?;
    let task = val.get("task").unwrap_or(&val);
    if task.get("status").and_then(Value::as_str) != Some("completed") {
        return None;
    }
    if !matches!(task.get("destination").and_then(Value::as_str), Some("phone" | "both")) {
        return None;
    }
    let task_id = task.get("id").and_then(Value::as_str)?.trim();
    if task_id.is_empty() {
        return None;
    }
    let files: Vec<PathBuf> = task
        .get("generated_files")?
        .as_array()?
        .iter()
        .filter_map(Value::as_str)
        .filter(|s| !s.trim().is_empty())
        .map(PathBuf::from)
        .collect();
    (!files.is_empty()).then(|| (task_id.to_owned(), files))
}

fn maybe_dispatch_phone_files(peer: &DeviceId, response_json: &str) {
    let Some((task_id, paths)) = extract_completed_phone_files(response_json) else { return };
    let existing: Vec<PathBuf> = paths.into_iter().filter(|p| p.is_file()).collect();
    if existing.is_empty() {
        return;
    }
    let mut sent = dispatched_tasks().lock().unwrap_or_else(|e| e.into_inner());
    if sent.len() >= 256 {
        sent.clear();
    }
    if sent.insert(task_id) {
        crate::transfers::send(*peer, existing);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn validates_ops_urls_and_injects_device_id() {
        let peer = DeviceId([7u8; 32]);
        assert!(prepare_request(&peer, "exec", "{}").is_err());
        assert!(prepare_request(&peer, "inspect", r#"{"url":"file:///etc/passwd"}"#).is_err());
        assert!(prepare_request(&peer, "inspect", r#"{"url":"http://127.0.0.1:28795/health"}"#).is_err());
        assert!(prepare_request(&peer, "inspect", r#"{"url":"https://user@example.com/v"}"#).is_err());
        assert!(prepare_request(&peer, "start", r#"{"url":"https://example.com/v with space"}"#).is_err());
        assert!(prepare_request(&peer, "status", r#"{"task_id":"../secret"}"#).is_err());

        let start = prepare_request(&peer, "start", r#"{"url":"https://example.com/watch?v=1","format":"audio","device_id":"forged","extra":"drop"}"#).unwrap();
        assert_eq!((start.method, start.path.as_str(), start.timeout), ("POST", "/download", DEFAULT_TIMEOUT));
        let body: Value = serde_json::from_str(start.body.as_deref().unwrap()).unwrap();
        assert_eq!(body.get("device_id").and_then(Value::as_str), Some(peer.to_string().as_str()));
        assert!(body.get("extra").is_none());

        let inspect = prepare_request(&peer, "inspect", r#"{"url":"https://example.com/v"}"#).unwrap();
        assert_eq!(inspect.timeout, INSPECT_TIMEOUT);
    }

    #[test]
    fn http_roundtrip_and_unavailable_error() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        let closed_port = {
            let l = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
            l.local_addr().unwrap().port()
        };
        std::thread::spawn(move || {
            if let Ok((mut s, _)) = listener.accept() {
                let mut buf = [0u8; 512];
                let _ = s.read(&mut buf);
                let _ = s.write_all(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"ok\"}");
            }
        });
        let req = PreparedRequest { method: "GET", path: "/health".into(), body: None, timeout: DEFAULT_TIMEOUT };
        assert_eq!(execute_http(addr, &req).unwrap(), r#"{"status":"ok"}"#);
        let err = execute_http(SocketAddr::from(([127, 0, 0, 1], closed_port)), &req).unwrap_err();
        assert_eq!(err, UNAVAILABLE_MSG);
    }

    #[test]
    fn extracts_completed_phone_files_only_for_phone_or_both() {
        let pc_only = r#"{"success":true,"task":{"id":"dl_1","status":"completed","destination":"pc","generated_files":["/tmp/a.mp4"]}}"#;
        assert!(extract_completed_phone_files(pc_only).is_none());

        let both = r#"{"success":true,"task":{"id":"dl_3","status":"completed","destination":"both","generated_files":["/tmp/a.mp4","/tmp/a.mp3"]}}"#;
        let (id, files) = extract_completed_phone_files(both).unwrap();
        assert_eq!(id, "dl_3");
        assert_eq!(files.len(), 2);
    }

    #[test]
    fn connects_resiliently_with_retry_on_delayed_server_startup() {
        let listener = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap();
        drop(listener);

        let (tx, rx) = std::sync::mpsc::channel();
        std::thread::spawn(move || {
            std::thread::sleep(Duration::from_millis(60));
            if let Ok(l) = std::net::TcpListener::bind(addr) {
                let _ = tx.send(());
                let _ = l.accept();
            }
        });

        let _ = rx.recv_timeout(Duration::from_secs(1));
        let stream = connect_with_retry(&addr);
        assert!(stream.is_ok());
    }
}
