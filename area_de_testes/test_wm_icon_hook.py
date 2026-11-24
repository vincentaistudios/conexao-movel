#!/usr/bin/env python3
"""
Modulo de testes unitarios e de integracao para o hook C libsysiconhook.so
e os scripts executaveis responsaveis pela injecao do logotipo V em runtime.
"""

import os
import subprocess
import unittest


class TestWmIconHook(unittest.TestCase):
    """Bateria de testes para validacao da biblioteca de interceptacao e wrappers."""

    HOOK_LIB = "/usr/lib/nectarlink/libsysiconhook.so"
    WRAPPER_SCRIPT = "/usr/lib/nectarlink/nectarlink-desktop"
    REAL_BINARY = "/usr/lib/nectarlink/nectarlink-desktop.real"

    def test_hook_shared_library_exists(self):
        """Valida a presenca da biblioteca compartilhada compilada."""
        self.assertTrue(
            os.path.isfile(self.HOOK_LIB),
            f"Biblioteca de hook ausente: {self.HOOK_LIB}"
        )

    def test_hook_exports_required_symbols(self):
        """Valida que a biblioteca intercepta os simbolos necessarios de XCB e X11."""
        res = subprocess.run(
            ["nm", "-D", self.HOOK_LIB],
            capture_output=True,
            text=True,
            check=True
        )
        symbols = res.stdout
        self.assertIn("xcb_change_property", symbols, "Simbolo xcb_change_property ausente no hook")
        self.assertIn("xcb_change_property_checked", symbols, "Simbolo xcb_change_property_checked ausente")
        self.assertIn("XChangeProperty", symbols, "Simbolo XChangeProperty ausente no hook")

    def test_wrapper_script_configured_properly(self):
        """Valida que o wrapper script executa com permissao adequada e injeta LD_PRELOAD."""
        self.assertTrue(os.path.isfile(self.WRAPPER_SCRIPT), "Wrapper script ausente")
        self.assertTrue(os.access(self.WRAPPER_SCRIPT, os.X_OK), "Wrapper script deve ser executavel")

        with open(self.WRAPPER_SCRIPT, "r", encoding="utf-8") as f:
            script_text = f.read()

        self.assertIn("libsysiconhook.so", script_text, "LD_PRELOAD do hook ausente no wrapper")
        self.assertIn("nectarlink-desktop.real", script_text, "Execucao do binario real ausente no wrapper")
        self.assertIn("tray-icon.png", script_text, "Garantia de bloqueio da bandeja ausente no wrapper")

    def test_real_binary_present_and_executable(self):
        """Valida a presenca e permissoes de execucao do binario real."""
        self.assertTrue(os.path.isfile(self.REAL_BINARY), "Binario real ausente")
        self.assertTrue(os.access(self.REAL_BINARY, os.X_OK), "Binario real deve ser executavel")


if __name__ == "__main__":
    unittest.main()

