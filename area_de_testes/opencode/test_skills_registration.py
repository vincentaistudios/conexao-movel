#!/usr/bin/env python3
"""
test_skills_registration.py
Valida a presenca, integridade e conformidade das skills do Antigravity e OpenCode.
"""

import json
import os
import shutil
import stat
import subprocess
import unittest
import urllib.request
from pathlib import Path

REQUIRED_SKILLS = [
    "ponytail",
    "security-audit",
    "cloudflare-patterns",
    "playwright-cli",
    "taste-skill",
    "impeccable",
    "awesome-design-md",
]


class TestSkillsRegistration(unittest.TestCase):
    """Testes de integridade das skills em Antigravity e OpenCode."""

    def setUp(self):
        self.antigravity_skills = Path.home() / ".gemini" / "config" / "skills"
        self.opencode_dir = Path.home() / ".config" / "opencode"
        self.opencode_instructions = self.opencode_dir / "instructions"
        self.opencode_skills = self.opencode_dir / "skills"

    def test_antigravity_skills_exist_and_have_skill_md(self):
        for skill_name in REQUIRED_SKILLS:
            skill_path = self.antigravity_skills / skill_name
            self.assertTrue(
                skill_path.exists(),
                f"Skill '{skill_name}' nao encontrada em {self.antigravity_skills}",
            )
            skill_md = skill_path / "SKILL.md"
            self.assertTrue(
                skill_md.exists(),
                f"Arquivo SKILL.md ausente na skill '{skill_name}' ({skill_md})",
            )
            content = skill_md.read_text(encoding="utf-8")
            self.assertGreater(len(content), 50, f"SKILL.md muito curto em '{skill_name}'")
            self.assertIn("name:", content, f"Cabecalho YAML 'name:' ausente em '{skill_name}'")
            self.assertIn("description:", content, f"Cabecalho YAML 'description:' ausente em '{skill_name}'")

    def test_opencode_instructions_exist(self):
        for skill_name in REQUIRED_SKILLS:
            instruction_file = self.opencode_instructions / f"{skill_name}.md"
            self.assertTrue(
                instruction_file.exists(),
                f"Instrucao OpenCode ausente: {instruction_file}",
            )
            content = instruction_file.read_text(encoding="utf-8")
            self.assertGreater(len(content), 50, f"Instrucao vazia ou muito curta: {instruction_file}")

    def test_opencode_skills_symlinks_exist(self):
        for skill_name in REQUIRED_SKILLS:
            skill_link = self.opencode_skills / skill_name
            self.assertTrue(
                skill_link.exists(),
                f"Link de skill OpenCode ausente: {skill_link}",
            )

    def test_opencode_env_file_security_permissions(self):
        env_file = self.opencode_dir / ".env"
        self.assertTrue(env_file.exists(), f"Arquivo .env ausente em {self.opencode_dir}")
        mode = env_file.stat().st_mode
        # Deve ter permissao 0600 (apenas leitura e escrita pelo dono)
        self.assertEqual(
            oct(stat.S_IMODE(mode)),
            "0o600",
            f"Permissoes inseguras no .env ({oct(stat.S_IMODE(mode))}), esperado 0o600",
        )

    def test_opencode_binary_executable(self):
        bin_path = Path("/usr/local/bin/opencode")
        self.assertTrue(bin_path.exists(), "Binario /usr/local/bin/opencode ausente")
        self.assertTrue(os.access(bin_path, os.X_OK), "Binario nao executavel")

    def test_opencode_desktop_shortcut_and_icons(self):
        desktop_file = Path.home() / ".local" / "share" / "applications" / "opencode.desktop"
        self.assertTrue(desktop_file.exists(), f"Atalho .desktop ausente: {desktop_file}")
        content = desktop_file.read_text(encoding="utf-8")
        self.assertIn("Name=OpenCode", content)
        self.assertIn("Icon=opencode", content)
        self.assertIn("sys-opencode", content)
        self.assertIn("open code", content.lower())

        launcher = Path("/usr/local/bin/sys-opencode")
        self.assertTrue(launcher.exists() and os.access(launcher, os.X_OK))

        icons_base = Path.home() / ".local" / "share" / "icons" / "hicolor"
        for rel in ("scalable/apps/opencode.svg", "48x48/apps/opencode.png", "256x256/apps/opencode.png"):
            self.assertTrue((icons_base / rel).exists(), f"Icone ausente: {icons_base / rel}")

        if shutil.which("desktop-file-validate"):
            proc = subprocess.run(["desktop-file-validate", str(desktop_file)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"desktop-file-validate falhou: {proc.stdout} {proc.stderr}")

    def test_opencode_global_rules_and_config_schema(self):
        agents_md = self.opencode_dir / "AGENTS.md"
        self.assertTrue(agents_md.exists(), f"Arquivo global AGENTS.md ausente: {agents_md}")
        agents_text = agents_md.read_text(encoding="utf-8")
        self.assertIn("GEMINI.md", agents_text)
        self.assertIn("pt-BR", agents_text)
        self.assertIn("area_de_testes", agents_text)

        config_json = json.loads((self.opencode_dir / "opencode.json").read_text(encoding="utf-8"))
        self.assertEqual(config_json.get("model"), "google/gemini-3.5-flash")
        self.assertIn("groq", config_json.get("providers", {}))
        self.assertIn("google", config_json.get("providers", {}))
        agents = config_json.get("agents", {})
        for expected_agent in ("groq-fast", "arquiteto", "desenvolvedor", "qa-tester", "auditor-seguranca", "ux-especialista"):
            self.assertIn(expected_agent, agents)
        self.assertIn(
            str(Path.home() / ".gemini" / "config" / "plugins" / "agent-orchestrator" / "rules" / "AGENTS.md"),
            config_json.get("instructions", []),
        )
        groq_settings = config_json["providers"]["groq"].get("settings", {})
        self.assertEqual(groq_settings.get("baseURL"), "http://127.0.0.1:4041/openai/v1")

    def test_opencode_rotator_gateway_and_key_pool(self):
        rotator = Path("/usr/local/bin/sys-opencode-rotator")
        self.assertTrue(rotator.exists() and os.access(rotator, os.X_OK))
        with urllib.request.urlopen("http://127.0.0.1:4041/health", timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            health = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(health.get("status"), "ok")
        self.assertEqual(health.get("groq", {}).get("total"), 9)
        self.assertGreaterEqual(health.get("groq", {}).get("active", 0), 1)


if __name__ == "__main__":
    unittest.main()

