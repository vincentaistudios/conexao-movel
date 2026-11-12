#!/usr/bin/env python3
"""
test_opencode_model_selector.py
Suite de testes unitarios para validacao do seletor inteligente de modelos e resiliencia anti-429.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Adiciona o diretorio de scripts do orchestrator ao path
ORCHESTRATOR_SCRIPTS = Path.home() / ".gemini" / "config" / "plugins" / "agent-orchestrator" / "skills" / "agent-routing" / "scripts"
sys.path.insert(0, str(ORCHESTRATOR_SCRIPTS))

import importlib.util

spec = importlib.util.spec_from_file_location("route_to_opencode", str(ORCHESTRATOR_SCRIPTS / "route-to-opencode.py"))
route_to_opencode = importlib.util.module_from_spec(spec)
spec.loader.exec_module(route_to_opencode)


class TestOpenCodeModelSelector(unittest.TestCase):
    """Testes unitarios para classificacao de missao e filas de modelos."""

    def test_classify_mission_syntax_lint(self):
        profile, queue = route_to_opencode.classify_mission("Executar linter e corrigir formatacao", 0)
        self.assertEqual(profile, "syntax_lint")
        self.assertEqual(queue[0], "groq/llama-3.1-8b-instant")
        self.assertIn("groq/llama-3.3-70b-versatile", queue)

    def test_classify_mission_tdd_tests(self):
        profile, queue = route_to_opencode.classify_mission("Rodar suite de testes com pytest e aplicar tdd", 1)
        self.assertEqual(profile, "tdd_tests")
        self.assertEqual(queue[0], "groq/llama-3.3-70b-versatile")
        self.assertIn("google/gemini-2.5-flash", queue)

    def test_classify_mission_reasoning_security(self):
        profile, queue = route_to_opencode.classify_mission("Auditoria de seguranca contra vulnerabilidade CVE", 2)
        self.assertEqual(profile, "reasoning_security")
        self.assertEqual(queue[0], "groq/deepseek-r1-distill-llama-70b")
        self.assertIn("groq/llama-3.3-70b-versatile", queue)

    def test_classify_mission_wide_context_ui(self):
        profile, queue = route_to_opencode.classify_mission("Ajustar layout responsivo QML", 0)
        self.assertEqual(profile, "wide_context_ui")
        self.assertEqual(queue[0], "google/gemini-2.5-flash")

    def test_classify_mission_many_files_fallback_to_wide_context(self):
        profile, queue = route_to_opencode.classify_mission("Verificar alteracao em modulo", 6)
        self.assertEqual(profile, "wide_context_ui")
        self.assertEqual(queue[0], "google/gemini-2.5-flash")

    def test_rate_limit_detection(self):
        self.assertTrue(route_to_opencode.is_rate_limit_error("Error: 429 Too Many Requests"))
        self.assertTrue(route_to_opencode.is_rate_limit_error("Rate limit reached for requests_per_minute"))
        self.assertTrue(route_to_opencode.is_rate_limit_error("tokens_per_minute limit exceeded"))
        self.assertTrue(route_to_opencode.is_rate_limit_error("quota_exceeded on provider"))
        self.assertFalse(route_to_opencode.is_rate_limit_error("SyntaxError: invalid syntax"))
        self.assertFalse(route_to_opencode.is_rate_limit_error("Compilation error: exit code 1"))

    @patch("subprocess.run")
    def test_headless_execution_success(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Task completed successfully"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        code, output = route_to_opencode.run_opencode_headless("Prompt teste", "/tmp", "groq/llama-3.1-8b-instant", [])
        self.assertEqual(code, 0)
        self.assertIn("Task completed successfully", output)


if __name__ == "__main__":
    unittest.main()

