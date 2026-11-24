# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Suite de Testes de Seguranca e Hardening do Downloader Conexao Movel.
Valida prevencao contra DNS Rebinding, Zero-Trust CORS Bypass,
injecao de opcoes/comandos no yt-dlp, Path Traversal, SSRF e Rate Limiting.
"""

import json
import os
import sys
import unittest
import urllib.error
import urllib.request

SERVER_BASE_URL = "http://127.0.0.1:28795"


class TestDownloaderSecurityHardening(unittest.TestCase):
    """Testes de seguranca ofensiva e defensiva para o downloader local."""

    def setUp(self):
        self._request("/test/reset_limiters", method="POST")

    def tearDown(self):
        self._request("/test/reset_limiters", method="POST")

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict = None,
        headers: dict = None,
        timeout: float = 3.0,
    ):
        url = f"{SERVER_BASE_URL}{endpoint}"
        req_headers = headers.copy() if headers else {}
        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            req_headers["Content-Type"] = "application/json; charset=utf-8"

        req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8", errors="replace")
                parsed = json.loads(raw) if raw else {}
                return status, parsed, dict(resp.headers)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            parsed = json.loads(raw) if raw else {}
            return exc.code, parsed, dict(exc.headers)

    def test_dns_rebinding_rejection(self):
        """Requisicoes com cabecalho Host externo devem ser sumariamente rejeitadas com 403."""
        status, data, _ = self._request(
            "/health",
            method="GET",
            headers={"Host": "attacker-rebinding.com:28795"},
        )
        self.assertEqual(status, 403)
        self.assertIn("anti-DNS Rebinding", data.get("error", ""))

    def test_cors_zero_trust_subdomain_bypass_prevention(self):
        """Valida que subdominios artificiais de localhost e 127.0.0.1 sao bloqueados."""
        for malicious_origin in (
            "http://localhost.evil.com",
            "http://127.0.0.1.attacker.org",
            "https://evil-site.com",
            "http://sub.localhost.mycorp.com",
        ):
            status, data, headers = self._request(
                "/health",
                method="GET",
                headers={"Origin": malicious_origin},
            )
            self.assertEqual(status, 403, f"Origem maliciosa nao foi bloqueada: {malicious_origin}")
            self.assertIn("Zero-Trust", data.get("error", ""))
            self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_allowed_loopback_origins(self):
        """Origens legitimas de loopback sao aceitas com cabecalho CORS adequado."""
        for safe_origin in ("http://127.0.0.1", "http://localhost", "http://127.0.0.1:28795"):
            status, _, headers = self._request(
                "/health",
                method="GET",
                headers={"Origin": safe_origin},
            )
            self.assertEqual(status, 200)
            self.assertEqual(headers.get("Access-Control-Allow-Origin"), safe_origin)

    def test_ssrf_internal_ips_rejected(self):
        """Tentativas de SSRF em metadados de nuvem e loopback via /inspect sao rejeitadas."""
        for blocked_url in (
            "http://169.254.169.254/latest/meta-data/",
            "http://127.0.0.1:28795/health",
            "http://localhost:8080/secret",
            "http://0.0.0.0/",
            "http://router.local/",
        ):
            status, data, _ = self._request(
                "/inspect",
                method="POST",
                data={"url": blocked_url},
            )
            self.assertEqual(status, 400)
            self.assertFalse(data.get("success", False))
            self.assertIn("bloqueados", data.get("error", ""))

    def test_option_injection_and_control_chars_rejected(self):
        """URLs com caracteres de espaco ou quebras de linha sao rejeitadas para evitar injecoes."""
        for malformed_url in (
            "https://example.com/video --exec rm -rf /",
            "https://example.com/video\n--config-location /etc/passwd",
            "https://user:pass@example.com/video",
            "ftp://example.com/video.mp4",
        ):
            status, data, _ = self._request(
                "/inspect",
                method="POST",
                data={"url": malformed_url},
            )
            self.assertEqual(status, 400)
            self.assertFalse(data.get("success", False))

    def test_path_traversal_task_id_rejected(self):
        """Identificadores task_id com Path Traversal ou caracteres invalidos sao rejeitados."""
        status, data, _ = self._request(
            "/status?task_id=../../../../etc/shadow",
            method="GET",
        )
        self.assertEqual(status, 404)
        self.assertEqual(data.get("error"), "Tarefa nao encontrada.")

    def test_z_rate_limiting_protection(self):
        """Disparo consecutivo de requisicoes em massa ativa o limitador de taxa (HTTP 429)."""
        hit_rate_limit = False
        for _ in range(35):
            status, data, _ = self._request(
                "/inspect",
                method="POST",
                data={"url": "http://127.0.0.1/rapid-probe"},
            )
            if status == 429:
                hit_rate_limit = True
                self.assertIn("Limite", data.get("error", ""))
                break
        self.assertTrue(hit_rate_limit, "Limitador de taxa (Rate Limiter) deveria ter disparado HTTP 429.")

    def test_no_emojis_in_code_or_documentation(self):
        """Garante ausencia absoluta de emojis neste arquivo de teste."""
        with open(__file__, "r", encoding="utf-8") as f:
            content = f.read()
        for char in content:
            cp = ord(char)
            is_emoji = (
                (0x1F600 <= cp <= 0x1F64F)
                or (0x1F300 <= cp <= 0x1F5FF)
                or (0x1F680 <= cp <= 0x1F6FF)
                or (0x2600 <= cp <= 0x26FF)
                or (0x2700 <= cp <= 0x27BF)
                or (0x1F900 <= cp <= 0x1F9FF)
            )
            self.assertFalse(is_emoji, f"Emoji detectado: code point {cp}")


if __name__ == "__main__":
    unittest.main()
