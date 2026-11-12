#!/usr/bin/env python3
"""
test_opencode_rotator_hybrid.py
Testes unitarios e de integracao do gateway hibrido Groq-first -> Gemini OpenAI-compat.
"""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

LIB_DIR = Path.home() / ".local" / "lib" / "opencode-rotator"


def run_node_eval(js_code: str, env_extra: dict | None = None) -> dict:
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", js_code],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip())


class TestOpenCodeRotatorHybrid(unittest.TestCase):
    """Valida pools de chaves, estimativa de tokens e failover Groq -> Gemini."""

    def test_env_pool_loading_and_round_robin_cooldown(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write(
                "GROQ_API_KEYS=gsk_test_key_0000000001,gsk_test_key_0000000002\n"
                "GEMINI_API_KEYS=AIzaTestKey0000000001,AQ.Ab8RNTestKey000002\n"
            )
            tmp_path = tmp.name

        try:
            script = f"""
            import {{ createPoolManager }} from '{(LIB_DIR / "pools.mjs").as_uri()}';
            const mgr = createPoolManager({json.dumps(tmp_path)});
            const k1 = mgr.groq.nextKey();
            mgr.groq.cooldown(k1, 60000);
            const k2 = mgr.groq.nextKey();
            const g1 = mgr.gemini.nextKey();
            const g2 = mgr.gemini.nextKey();
            console.log(JSON.stringify({{ k1, k2, g1, g2, stats: mgr.stats() }}));
            """
            res = run_node_eval(script)
            self.assertEqual(res["k1"], "gsk_test_key_0000000001")
            self.assertEqual(res["k2"], "gsk_test_key_0000000002")
            self.assertEqual(res["g1"], "AIzaTestKey0000000001")
            self.assertEqual(res["g2"], "AQ.Ab8RNTestKey000002")
            self.assertEqual(res["stats"]["groq"]["cooldown"], 1)
            self.assertEqual(res["stats"]["groq"]["active"], 1)
            self.assertEqual(res["stats"]["gemini"]["total"], 2)
        finally:
            os.unlink(tmp_path)

    def test_auto_plan_prioritizes_groq_under_threshold_and_skips_above(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write(
                "GROQ_API_KEYS=gsk_a00000000000000001,gsk_b00000000000000002,gsk_c00000000000000003\n"
                "GEMINI_API_KEYS=AIzaGem000000000000001\n"
            )
            tmp_path = tmp.name

        try:
            script = f"""
            import {{ createPoolManager }} from '{(LIB_DIR / "pools.mjs").as_uri()}';
            import {{ buildAutoCandidates, estimateRequestTokens }} from '{(LIB_DIR / "router.mjs").as_uri()}';
            const mgr = createPoolManager({json.dumps(tmp_path)});
            const shortPlan = buildAutoCandidates(3500, mgr, false).map(c => ({{ p: c.provider, m: c.model }}));
            const longPlan = buildAutoCandidates(12000, mgr, false).map(c => ({{ p: c.provider, m: c.model }}));
            const ollamaPlan = buildAutoCandidates(12000, mgr, true).map(c => ({{ p: c.provider, m: c.model }}));
            const est = estimateRequestTokens(Buffer.alloc(14000, 'a'));
            console.log(JSON.stringify({{ shortPlan, longPlan, ollamaPlan, est }}));
            """
            res = run_node_eval(script)
            self.assertEqual(res["est"], 4000)
            self.assertEqual([x["p"] for x in res["shortPlan"][:3]], ["groq", "groq", "groq"])
            self.assertEqual(res["shortPlan"][0]["m"], "openai/gpt-oss-120b")
            self.assertEqual(res["shortPlan"][1]["m"], "qwen/qwen3.8-27b")
            self.assertEqual(res["shortPlan"][2]["m"], "openai/gpt-oss-20b")
            self.assertEqual(res["shortPlan"][3]["p"], "gemini")
            self.assertTrue(all(x["p"] == "gemini" for x in res["longPlan"]))
            self.assertEqual(res["ollamaPlan"][-1]["p"], "ollama")
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
