# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Servidor REST Local para Integracao do Downloader com a Interface QML.
Opera de forma assincrona e nao-bloqueante em 127.0.0.1:28795.
"""

import sys
import os
import json
import uuid
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Garante importacao do modulo downloader_service
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from downloader_service import MediaDownloader, DOWNLOADS_DIR

HOST = "127.0.0.1"
PORT = 28795

downloader = MediaDownloader(output_dir=DOWNLOADS_DIR)

class DownloaderHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(200)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/health":
            self._set_cors_headers(200)
            payload = {
                "status": "ok",
                "downloads_dir": DOWNLOADS_DIR,
                "server": "ConexaoMovel-Downloader/1.0"
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        elif path == "/status":
            task_id = query.get("task_id", [""])[0]
            if not task_id:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({"error": "Parametro task_id ausente."}).encode("utf-8"))
                return

            task = downloader.get_task_status(task_id)
            if not task:
                self._set_cors_headers(404)
                self.wfile.write(json.dumps({"error": "Tarefa nao encontrada."}).encode("utf-8"))
                return

            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"success": True, "task": task}).encode("utf-8"))

        elif path == "/history":
            history = downloader.get_recent_history(limit=20)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"success": True, "history": history}).encode("utf-8"))

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
                            text = candidate
                            break
                except Exception:
                    pass
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"success": True, "text": text}).encode("utf-8"))

        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Rota nao encontrada."}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length).decode("utf-8", errors="ignore")
        
        try:
            data = json.loads(raw_body) if raw_body else {}
        except Exception:
            data = {}

        if path == "/inspect":
            url = data.get("url", "")
            result = downloader.inspect_url(url)
            status_code = 200 if result.get("success") else 400
            self._set_cors_headers(status_code)
            self.wfile.write(json.dumps(result).encode("utf-8"))

        elif path == "/download":
            url = data.get("url", "")
            media_format = data.get("format", "video") # "audio", "video", "both"
            destination = data.get("destination", "pc") # "pc", "phone", "both"
            device_id = data.get("device_id", "")
            task_id = "dl_" + uuid.uuid4().hex[:8]

            res = downloader.start_download(
                task_id=task_id,
                url=url,
                media_format=media_format,
                destination=destination,
                device_id=device_id
            )

            status_code = 200 if res.get("success") else 400
            self._set_cors_headers(status_code)
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif path == "/cancel":
            task_id = data.get("task_id", "")
            ok = downloader.cancel_download(task_id)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({"success": ok}).encode("utf-8"))

        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Rota POST nao encontrada."}).encode("utf-8"))

    def log_message(self, format, *args):
        # Desativa logs poluidos de acesso HTTP no terminal padrao
        pass

def run_server():
    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, DownloaderHandler)
    print(f"Servidor Conexao Movel Downloader rodando em http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()

if __name__ == "__main__":
    run_server()

