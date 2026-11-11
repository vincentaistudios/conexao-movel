#!/usr/bin/env python3
"""
test_skills_registration.py
Valida a presenca, integridade e conformidade das skills do Antigravity e OpenCode.
"""

import os
import stat
import unittest
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


if __name__ == "__main__":
    unittest.main()
