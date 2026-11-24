# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de Testes de Integracao RPC: Servidor de Downloads Conexao Movel.
Valida o servidor downloader_server.py ativo na porta 28795
atendendo requisicoes para /health, /status, /inspect e /history.
Tambem valida politicas de seguranca Zero-Trust de CORS e tratamento de erros.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import unittest

SERVER_BASE_URL = "http://127.0.0.1:28795"


class TestDownloaderRpcEndpoints(unittest.TestCase):
    """Testes de integracao dos endpoints REST/RPC do sys-downloader-bridge."""

    def setUp(self):
        self._http_request("/test/reset_limiters", method="POST")

    def tearDown(self):
        self._http_request("/test/reset_limiters", method="POST")

    def _http_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict = None,
        origin: str = None,
        timeout: float = 5.0
    ):
        """Utilitario para despachar requisicoes HTTP com controle de cabecalhos e fechamento seguro."""
        url = f"{SERVER_BASE_URL}{endpoint}"
        body_bytes = None
        headers = {}

        if data is not None:
            body_bytes = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"

        if origin:
            headers["Origin"] = origin

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status_code = resp.status
                resp_headers = dict(resp.headers)
                resp_body = resp.read().decode("utf-8", errors="replace")
                parsed_json = json.loads(resp_body) if resp_body else {}
                return status_code, parsed_json, resp_headers
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
                parsed_json = json.loads(err_body) if err_body else {}
                return exc.code, parsed_json, dict(exc.headers)
            finally:
                exc.close()

    def test_health_endpoint_success(self):
        """Valida que o endpoint /health retorna status ok, identificacao do servidor e pasta de downloads."""
        status, data, _ = self._http_request("/health")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("server"), "ConexaoMovel-Downloader/1.0")
        self.assertIn("downloads_dir", data)
        self.assertTrue(os.path.isdir(data["downloads_dir"]))

    def test_status_endpoint_missing_task_id(self):
        """Valida que /status sem parametro task_id retorna erro 400."""
        status, data, _ = self._http_request("/status")
        self.assertEqual(status, 400)
        self.assertIn("error", data)
        self.assertEqual(data.get("error"), "Parametro task_id ausente.")

    def test_status_endpoint_not_found(self):
        """Valida que /status com task_id inexistente retorna 404."""
        status, data, _ = self._http_request("/status?task_id=dl_tarefa_inexistente_999")
        self.assertEqual(status, 404)
        self.assertIn("error", data)
        self.assertEqual(data.get("error"), "Tarefa nao encontrada.")

    def test_history_endpoint_structure(self):
        """Valida que /history retorna status 200 e lista valida de historico."""
        status, data, _ = self._http_request("/history")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertIsInstance(data.get("history"), list)

    def test_inspect_endpoint_invalid_url(self):
        """Valida que /inspect rejeita URLs invalidas com status 400 e mensagem descritiva imediata."""
        payload = {"url": "invalid-url-schema"}
        status, data, _ = self._http_request("/inspect", method="POST", data=payload)
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success"))
        self.assertIn("error", data)

    def test_inspect_endpoint_empty_payload(self):
        """Valida que /inspect com payload vazio retorna erro 400."""
        status, data, _ = self._http_request("/inspect", method="POST", data={})
        self.assertEqual(status, 400)
        self.assertFalse(data.get("success"))
        self.assertIn("error", data)

    def test_clipboard_endpoint_availability(self):
        """Valida que /clipboard responde com sucesso e campo text."""
        status, data, _ = self._http_request("/clipboard")
        self.assertEqual(status, 200)
        self.assertTrue(data.get("success"))
        self.assertIn("text", data)

    def test_zero_trust_origin_rejection(self):
        """Valida politica Zero-Trust: requisicao com Origin externo deve ser rejeitada com 403."""
        status, data, _ = self._http_request(
            "/health",
            method="GET",
            origin="http://site-externo-malicioso.com"
        )
        self.assertEqual(status, 403)
        self.assertIn("error", data)
        self.assertIn("Zero-Trust", data.get("error", ""))

    def test_zero_trust_origin_allow_local(self):
        """Valida que Origin local (127.0.0.1 ou localhost) e aceito com cabecalho CORS adequado."""
        status, _, headers = self._http_request(
            "/health",
            method="GET",
            origin="http://127.0.0.1"
        )
        self.assertEqual(status, 200)
        allow_origin = headers.get("Access-Control-Allow-Origin") or headers.get("access-control-allow-origin")
        self.assertEqual(allow_origin, "http://127.0.0.1")

    def test_cors_options_preflight(self):
        """Valida resposta do metodo OPTIONS com metodos permitidos."""
        status, _, headers = self._http_request(
            "/inspect",
            method="OPTIONS",
            origin="http://127.0.0.1"
        )
        self.assertEqual(status, 200)
        allow_methods = headers.get("Access-Control-Allow-Methods") or headers.get("access-control-allow-methods")
        self.assertIn("GET", allow_methods)
        self.assertIn("POST", allow_methods)
        self.assertIn("OPTIONS", allow_methods)

    def test_unknown_get_route_returns_404(self):
        """Valida que rotas GET nao cadastradas retornam 404."""
        status, data, _ = self._http_request("/rota_inexistente_12345")
        self.assertEqual(status, 404)
        self.assertEqual(data.get("error"), "Rota nao encontrada.")

    def test_unknown_post_route_returns_404(self):
        """Valida que rotas POST nao cadastradas retornam 404."""
        status, data, _ = self._http_request("/rota_post_inexistente_12345", method="POST", data={})
        self.assertEqual(status, 404)
        self.assertEqual(data.get("error"), "Rota POST nao encontrada.")

    def test_no_emojis_in_source_code(self):
        """Garante ausencia estrita de emojis no arquivo de testes segundo diretriz global."""
        current_file = os.path.abspath(__file__)
        with open(current_file, "r", encoding="utf-8") as f:
            content = f.read()

        for char in content:
            code_point = ord(char)
            is_emoji = (
                (0x1F600 <= code_point <= 0x1F64F)
                or (0x1F300 <= code_point <= 0x1F5FF)
                or (0x1F680 <= code_point <= 0x1F6FF)
                or (0x2600 <= code_point <= 0x26FF)
                or (0x2700 <= code_point <= 0x27BF)
                or (0x1F900 <= code_point <= 0x1F9FF)
            )
            self.assertFalse(is_emoji, f"Emoji detectado no codigo fonte: code point {code_point}")


if __name__ == "__main__":
    unittest.main()
