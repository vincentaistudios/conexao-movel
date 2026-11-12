#!/usr/bin/env python3
"""
test_opencode_rotator_hybrid.py
Testes unitarios e de integracao do gateway hibrido Groq-first -> NIM/Cerebras/OpenRouter 1M -> Gemini.
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
    """Valida pools multi-provedor, estimativa de tokens e cascata de failover."""

    def test_env_pool_loading_all_providers_and_cooldown(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write(
                "GROQ_API_KEYS=gsk_test_key_0000000001,gsk_test_key_0000000002\n"
                "GEMINI_API_KEYS=AIzaTestKey0000000001,AQ.Ab8RNTestKey000002\n"
                "OPENROUTER_API_KEYS=sk-or-v1-test0000000000000001\n"
                "NVIDIA_API_KEYS=nvapi-test000000000000000001\n"
                "CEREBRAS_API_KEYS=csk-test0000000000000000001\n"
            )
            tmp_path = tmp.name

        try:
            script = f"""
            import {{ createPoolManager }} from '{(LIB_DIR / "pools.mjs").as_uri()}';
            const mgr = createPoolManager({json.dumps(tmp_path)});
            const k1 = mgr.groq.nextKey();
            mgr.groq.cooldown(k1, 60000);
            const k2 = mgr.groq.nextKey();
            console.log(JSON.stringify({{ k1, k2, stats: mgr.stats() }}));
            """
            res = run_node_eval(script)
            self.assertEqual(res["k1"], "gsk_test_key_0000000001")
            self.assertEqual(res["k2"], "gsk_test_key_0000000002")
            self.assertEqual(res["stats"]["groq"]["cooldown"], 1)
            self.assertEqual(res["stats"]["gemini"]["total"], 2)
            self.assertEqual(res["stats"]["openrouter"]["total"], 1)
            self.assertEqual(res["stats"]["nvidia"]["total"], 1)
            self.assertEqual(res["stats"]["cerebras"]["total"], 1)
        finally:
            os.unlink(tmp_path)

    def test_auto_plan_cascades_groq_openrouter_1m_and_gemini(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write(
                "GROQ_API_KEYS=gsk_a00000000000000001,gsk_b00000000000000002\n"
                "OPENROUTER_API_KEYS=sk-or-v1-test0000000000000001\n"
                "GEMINI_API_KEYS=AIzaGem000000000000001\n"
            )
            tmp_path = tmp.name

        try:
            script = f"""
            import {{ createPoolManager }} from '{(LIB_DIR / "pools.mjs").as_uri()}';
            import {{ buildAutoCandidates, buildDirectTarget, estimateRequestTokens }} from '{(LIB_DIR / "router.mjs").as_uri()}';
            const mgr = createPoolManager({json.dumps(tmp_path)});
            const shortPlan = buildAutoCandidates(3500, mgr, false).map(c => ({{ p: c.provider, m: c.model }}));
            const longPlan = buildAutoCandidates(50000, mgr, false).map(c => ({{ p: c.provider, m: c.model }}));
            const orTarget = buildDirectTarget('/openrouter/v1/chat/completions');
            const nimTarget = buildDirectTarget('/nvidia/v1/chat/completions');
            const cerTarget = buildDirectTarget('/cerebras/v1/chat/completions');
            const est = estimateRequestTokens(Buffer.alloc(14000, 'a'));
            console.log(JSON.stringify({{ shortPlan, longPlan, orTarget, nimTarget, cerTarget, est }}));
            """
            res = run_node_eval(script)
            self.assertEqual(res["est"], 4000)
            self.assertEqual([x["p"] for x in res["shortPlan"][:2]], ["groq", "groq"])
            self.assertEqual(res["shortPlan"][2]["p"], "openrouter")
            self.assertEqual(res["shortPlan"][2]["m"], "nvidia/nemotron-3.5-super-vl:free")
            self.assertEqual(res["longPlan"][0]["p"], "openrouter")
            self.assertEqual(res["longPlan"][0]["m"], "nvidia/nemotron-3.5-super-vl:free")
            self.assertTrue(any(x["p"] == "gemini" for x in res["longPlan"]))
            self.assertFalse(any(x["p"] == "groq" for x in res["longPlan"]))
            self.assertEqual(res["orTarget"]["hostname"], "openrouter.ai")
            self.assertEqual(res["orTarget"]["path"], "/api/v1/chat/completions")
            self.assertEqual(res["nimTarget"]["hostname"], "integrate.api.nvidia.com")
            self.assertEqual(res["cerTarget"]["hostname"], "api.cerebras.ai")
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
