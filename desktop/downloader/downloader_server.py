# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Servidor REST Local para Integracao do Downloader com a Interface QML e RPC.
Opera de forma assincrona e nao-bloqueante em 127.0.0.1:28795.
Possui protecao estrita anti-DNS Rebinding, validacao Zero-Trust de CORS,
e limitacao de taxa (Rate Limiting) defensiva.
"""

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from downloader_service import DOWNLOADS_DIR, MediaDownloader
from google_bridge_routes import handle_google_get, handle_google_post

HOST = "127.0.0.1"
PORT = 28795
MAX_CONCURRENT_DOWNLOADS = 3

downloader = MediaDownloader(output_dir=DOWNLOADS_DIR)


class RateLimiter:
    """Limitador de taxa com janela deslizante em memoria."""

    def __init__(self, max_requests: int = 60, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps: List[float] = []
        self._lock = threading.Lock()

    def allow(self) -> bool:
        now = time.time()
        with self._lock:
            cutoff = now - self.window_seconds
            self.timestamps = [t for t in self.timestamps if t > cutoff]
            if len(self.timestamps) >= self.max_requests:
                return False
            self.timestamps.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self.timestamps.clear()


global_limiter = RateLimiter(max_requests=120, window_seconds=60.0)
inspect_limiter = RateLimiter(max_requests=30, window_seconds=60.0)
download_limiter = RateLimiter(max_requests=15, window_seconds=60.0)


def is_allowed_origin(origin: Optional[str]) -> bool:
    """Valida estritamente se a origem HTTP pertence ao loopback local."""
    if not origin:
        return True
    try:
        parsed = urlparse(origin)
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower().strip("[]")
        return hostname in ("127.0.0.1", "localhost")
    except Exception:
        return False


def is_allowed_host(host_header: Optional[str]) -> bool:
    """Valida se o cabecalho Host pertence ao loopback local (anti-DNS Rebinding)."""
    if not host_header:
        return True
    try:
        host = host_header.split(":")[0].strip().lower().strip("[]")
        return host in ("127.0.0.1", "localhost")
    except Exception:
        return False


class DownloaderHandler(BaseHTTPRequestHandler):
    """Manipulador de requisicoes HTTP do servico de download."""

    def _send_json_response(self, status: int, payload: Dict[str, Any]):
        """Serializa e envia resposta JSON com Content-Length e cabecalhos defensivos."""
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Connection", "close")
        origin = self.headers.get("Origin")
        if origin and is_allowed_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(body_bytes)

    def _set_cors_headers(self, status: int = 200):
        """Metodo de retrocompatibilidade com modulos auxiliares."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Connection", "close")
        origin = self.headers.get("Origin")
        if origin and is_allowed_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def _validate_request(self) -> bool:
        """Aplica verificacoes de seguranca Zero-Trust, Host e Rate Limiting."""
        if not is_allowed_host(self.headers.get("Host")):
            self._send_json_response(403, {
                "error": "Acesso bloqueado: cabecalho Host invalido (anti-DNS Rebinding)."
            })
            return False

        if not is_allowed_origin(self.headers.get("Origin")):
            self._send_json_response(403, {
                "error": "Acesso cross-origin bloqueado por politica Zero-Trust."
            })
            return False

        if not global_limiter.allow():
            self._send_json_response(429, {
                "error": "Taxa limite de requisicoes excedida (Rate Limit). Aguarde."
            })
            return False

        return True

    def do_OPTIONS(self):
        if not self._validate_request():
            return
        self._set_cors_headers(200)

    def do_GET(self):
        if not self._validate_request():
            return

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path.startswith("/google/") and handle_google_get(self, path, query):
            return

        if path == "/health":
            self._send_json_response(200, {
                "status": "ok",
                "downloads_dir": DOWNLOADS_DIR,
                "server": "ConexaoMovel-Downloader/1.0",
                "active_downloads": downloader.get_active_downloads_count(),
            })

        elif path == "/status":
            task_id = query.get("task_id", [""])[0]
            if not task_id:
                self._send_json_response(400, {"error": "Parametro task_id ausente."})
                return

            task = downloader.get_task_status(task_id)
            if not task:
                self._send_json_response(404, {"error": "Tarefa nao encontrada."})
                return

            self._send_json_response(200, {"success": True, "task": task})

        elif path == "/history":
            history = downloader.get_recent_history(limit=20)
            self._send_json_response(200, {"success": True, "history": history})

        elif path == "/clipboard":
            text = ""
            env = dict(os.environ)
            if "DISPLAY" not in env:
                env["DISPLAY"] = ":0"
            if "XAUTHORITY" not in env:
                env["XAUTHORITY"] = os.path.expanduser("~/.Xauthority")
            for sel in ["clipboard", "primary"]:
                try:
                    res = subprocess.run(
                        ["xclip", "-selection", sel, "-o"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=1,
                        env=env,
                    )
                    if res.returncode == 0:
                        candidate = res.stdout.decode("utf-8", errors="ignore").strip()
                        if candidate:
                            text = candidate[:65536]
                            break
                except Exception:
                    pass
            self._send_json_response(200, {"success": True, "text": text})

        else:
            self._send_json_response(404, {"error": "Rota nao encontrada."})

    def do_POST(self):
        if not self._validate_request():
            return

        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 1048576:
            self._send_json_response(413, {"error": "Corpo da requisicao excede 1MB."})
            return

        raw_body = self.rfile.read(content_length).decode("utf-8", errors="ignore")
        try:
            data = json.loads(raw_body) if raw_body else {}
        except Exception:
            data = {}

        if path.startswith("/google/") and handle_google_post(self, path, data):
            return

        if path == "/test/reset_limiters":
            global_limiter.reset()
            inspect_limiter.reset()
            download_limiter.reset()
            self._send_json_response(200, {"success": True})
            return

        if path == "/inspect":
            if not inspect_limiter.allow():
                self._send_json_response(429, {"error": "Limite de inspecoes por minuto excedido."})
                return

            url = data.get("url", "")
            result = downloader.inspect_url(url)
            status_code = 200 if result.get("success") else 400
            self._send_json_response(status_code, result)

        elif path == "/download":
            if not download_limiter.allow():
                self._send_json_response(429, {"error": "Limite de downloads por minuto excedido."})
                return

            if downloader.get_active_downloads_count() >= MAX_CONCURRENT_DOWNLOADS:
                self._send_json_response(429, {
                    "error": f"Limite de downloads simultaneos atingido (maximo {MAX_CONCURRENT_DOWNLOADS}). Aguarde."
                })
                return

            url = data.get("url", "")
            media_format = data.get("format", "video")
            destination = data.get("destination", "pc")
            device_id = data.get("device_id", "")
            task_id = "dl_" + uuid.uuid4().hex[:8]

            res = downloader.start_download(
                task_id=task_id,
                url=url,
                media_format=media_format,
                destination=destination,
                device_id=device_id,
            )

            status_code = 200 if res.get("success") else 400
            self._send_json_response(status_code, res)

        elif path == "/cancel":
            task_id = data.get("task_id", "")
            ok = downloader.cancel_download(task_id)
            self._send_json_response(200, {"success": ok})

        else:
            self._send_json_response(404, {"error": "Rota POST nao encontrada."})

    def log_message(self, format, *args):
        pass


def run_server():
    server_address = (HOST, PORT)
    httpd = ThreadingHTTPServer(server_address, DownloaderHandler)
    print(f"Servidor Conexao Movel Downloader rodando em http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
