# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Rotas REST Locais para Integracao Google Suite (Identificacao Automatica, OAuth2 e Gmail).
Modulo desacoplado servido pela ponte HTTP local em 127.0.0.1:28795.
"""

from __future__ import annotations

import imaplib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

SYS_DEVICE_LINK_DIR = Path.home() / ".config" / "sys-device-link"
if str(SYS_DEVICE_LINK_DIR) not in sys.path:
    sys.path.insert(0, str(SYS_DEVICE_LINK_DIR))

from sys_google_oauth_flow import (  # noqa: E402
    exchange_code_for_tokens,
    save_oauth_client_config,
    start_oauth_pkce_flow,
)
from sys_google_suite import GoogleSuiteService  # noqa: E402


_google_service: GoogleSuiteService | None = None


def get_google_service() -> GoogleSuiteService:
    """Retorna instancia singleton de GoogleSuiteService."""
    global _google_service
    if _google_service is None:
        _google_service = GoogleSuiteService()
    return _google_service


def _send_json(handler: Any, status: int, payload: Dict[str, Any]) -> None:
    handler._set_cors_headers(status)
    handler.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _send_html(handler: Any, status: int, html_body: str) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(html_body.encode("utf-8"))


def handle_google_get(handler: Any, path: str, query: Dict[str, Any]) -> bool:
    """Despacha rotas GET /google/*. Retorna True se a rota foi tratada."""
    svc = get_google_service()

    if path == "/google/status":
        state = svc.export_state_dict()
        state["success"] = True
        _send_json(handler, 200, state)
        return True

    if path == "/google/gmail/messages":
        folder = str(query.get("folder", ["inbox"])[0] or "inbox")
        page_raw = str(query.get("page", ["1"])[0] or "1")
        limit_raw = str(query.get("limit", ["50"])[0] or "50")
        page_token = str(query.get("page_token", [""])[0] or "")
        query_text = str(query.get("q", [""])[0] or "")
        try:
            page = max(1, int(page_raw))
            limit = max(1, min(100, int(limit_raw)))
        except ValueError:
            page, limit = 1, 50

        try:
            res = svc.list_gmail_messages(
                folder=folder,
                page=page,
                limit=limit,
                page_token=page_token,
                query_text=query_text,
            )
            res["success"] = True
            _send_json(handler, 200, res)
        except Exception as exc:
            _send_json(handler, 502, {"success": False, "error": f"Falha ao sincronizar Gmail: {exc}"})
        return True

    if path == "/google/oauth/callback":
        code = str(query.get("code", [""])[0] or "")
        state = str(query.get("state", [""])[0] or "")
        err = str(query.get("error", [""])[0] or "")
        if err or not code:
            _send_html(
                handler,
                400,
                "<html><body style='font-family:sans-serif;background:#111;color:#eee;padding:40px'>"
                "<h2>Autorizacao nao concluida</h2><p>Voce pode fechar esta guia e tentar novamente no Conexao Movel.</p>"
                "</body></html>",
            )
            return True
        try:
            tokens = exchange_code_for_tokens(code, state)
            svc.connect_auto(
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token", ""),
                scope=tokens.get("scope", ""),
                expires_at=tokens.get("expires_at"),
            )
            _send_html(
                handler,
                200,
                "<html><body style='font-family:sans-serif;background:#111;color:#eee;padding:40px'>"
                "<h2>Conta Google autorizada com sucesso</h2>"
                "<p>Seus e-mails e cota do Drive foram sincronizados. Voce ja pode fechar esta aba e voltar ao Conexao Movel.</p>"
                "</body></html>",
            )
        except Exception as exc:
            _send_html(
                handler,
                500,
                f"<html><body style='font-family:sans-serif;background:#111;color:#eee;padding:40px'>"
                f"<h2>Erro ao concluir autenticacao</h2><p>{exc}</p></body></html>",
            )
        return True

    return False


def handle_google_post(handler: Any, path: str, data: Dict[str, Any]) -> bool:
    """Despacha rotas POST /google/*. Retorna True se a rota foi tratada."""
    svc = get_google_service()

    if path in ("/google/connect-auto", "/google/connect"):
        svc.connect_auto(
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            scope=str(data.get("scope", "")),
        )
        state = svc.export_state_dict()
        state["success"] = True
        _send_json(handler, 200, state)
        return True

    if path == "/google/disconnect":
        svc.disconnect_account()
        state = svc.export_state_dict()
        state["success"] = True
        _send_json(handler, 200, state)
        return True

    if path == "/google/gmail/connect-imap":
        email_addr = str(data.get("email", "")).strip()
        app_password = str(data.get("app_password", "")).strip()
        try:
            svc.connect_imap(email_addr, app_password)
            state = svc.export_state_dict()
            state["success"] = True
            _send_json(handler, 200, state)
        except (ValueError, imaplib.IMAP4.error) as exc:
            _send_json(handler, 401, {"success": False, "error": f"Falha na autenticacao IMAP do Gmail: {exc}"})
        except Exception as exc:
            _send_json(handler, 502, {"success": False, "error": f"Erro de conexao ao Gmail (imap.gmail.com): {exc}"})
        return True

    if path == "/google/gmail/sync":
        folder = str(data.get("folder", "inbox"))
        page = int(data.get("page", 1) or 1)
        limit = int(data.get("limit", 50) or 50)
        q = str(data.get("q", ""))
        try:
            res = svc.list_gmail_messages(folder=folder, page=page, limit=limit, query_text=q)
            res["success"] = True
            _send_json(handler, 200, res)
        except Exception as exc:
            _send_json(handler, 502, {"success": False, "error": f"Erro ao atualizar mensagens: {exc}"})
        return True

    if path == "/google/oauth/client":
        try:
            save_oauth_client_config(data.get("client_json", data))
            _send_json(handler, 200, {"success": True, "has_oauth_client": True})
        except Exception as exc:
            _send_json(handler, 400, {"success": False, "error": str(exc)})
        return True

    if path == "/google/oauth/start":
        try:
            auth_url, _ = start_oauth_pkce_flow()
            if data.get("open_browser", True):
                subprocess.Popen(["xdg-open", auth_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _send_json(handler, 200, {"success": True, "auth_url": auth_url})
        except Exception as exc:
            _send_json(handler, 400, {"success": False, "error": str(exc)})
        return True

    if path == "/google/email/action":
        action = str(data.get("action", "")).strip().lower()
        email_id = str(data.get("email_id", "")).strip()
        folder = str(data.get("folder", "inbox")).strip().lower()
        if not email_id or action not in ("read", "archive", "delete"):
            _send_json(handler, 400, {"success": False, "error": "Parametros invalidos para acao de e-mail."})
            return True

        ok = False
        if action == "read":
            ok = svc.mark_as_read(email_id, bool(data.get("is_read", True)), folder=folder)
        elif action == "archive":
            ok = svc.archive_email(email_id, folder=folder)
        elif action == "delete":
            ok = svc.delete_email(email_id, folder=folder)

        state = svc.export_state_dict()
        state["success"] = ok
        _send_json(handler, 200 if ok else 404, state)
        return True

    return False
