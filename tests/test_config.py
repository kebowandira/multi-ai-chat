import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import configure  # noqa: E402


ENV = {
    "ANTHROPIC_MODELS": "claude-sonnet-5-5",
    "OPENAI_MODELS": "gpt-6.1-sol",
    "GOOGLE_MODELS": "gemini-3.8-flash",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com/v1",
    "DEEPSEEK_FAST_MODEL": "deepseek-flash",
    "DEEPSEEK_PRO_MODEL": "deepseek-v4-pro",
    "DASHSCOPE_BASE_URL": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/ws",
    "QWEN_TURBO_MODEL": "qwen-turbo",
    "QWEN_PLUS_MODEL": "qwen-plus",
    "ZAI_BASE_URL": "https://api.z.ai/api/paas/v4",
    "ZAI_MODEL": "glm-5.3",
    "XAI_BASE_URL": "https://api.x.ai/v1",
    "XAI_MODEL": "grok-4.7",
}


class SubstituteTests(unittest.TestCase):
    def test_substitutes_nested_structures(self):
        doc = {"a": "${DEEPSEEK_BASE_URL}", "b": ["${ZAI_MODEL}", "literal"]}
        out = configure.substitute(doc, ENV)
        self.assertEqual(out["a"], "https://api.deepseek.com/v1")
        self.assertEqual(out["b"], ["glm-5.3", "literal"])

    def test_missing_var_becomes_empty_string(self):
        self.assertEqual(configure.substitute("${NOT_SET}", ENV), "")


class CompileLibrechatTests(unittest.TestCase):
    def test_only_deepseek_kept(self):
        doc = configure.compile_librechat(ENV, providers={"deepseek"}, router_enabled=False)
        names = {e["name"] for e in doc["endpoints"]["custom"]}
        self.assertEqual(names, {"DeepSeek"})

    def test_smartrouter_requires_router_enabled(self):
        doc = configure.compile_librechat(ENV, providers={"deepseek", "qwen", "zai", "xai"}, router_enabled=False)
        names = {e["name"] for e in doc["endpoints"]["custom"]}
        self.assertNotIn("SmartRouter", names)

        doc2 = configure.compile_librechat(ENV, providers={"deepseek", "qwen", "zai", "xai"}, router_enabled=True)
        names2 = {e["name"] for e in doc2["endpoints"]["custom"]}
        self.assertIn("SmartRouter", names2)

    def test_no_providers_leaves_only_smartrouter_when_router_enabled(self):
        doc = configure.compile_librechat(ENV, providers=set(), router_enabled=True)
        names = {e["name"] for e in doc["endpoints"]["custom"]}
        self.assertEqual(names, {"SmartRouter"})

    def test_api_keys_substituted(self):
        env = {**ENV, "DEEPSEEK_API_KEY": "dummy-key"}
        doc = configure.compile_librechat(env, providers={"deepseek"}, router_enabled=False)
        entry = doc["endpoints"]["custom"][0]
        self.assertEqual(entry["apiKey"], "dummy-key")


class CompileLitellmTests(unittest.TestCase):
    def test_prunes_unavailable_models(self):
        doc = configure.compile_litellm(ENV, providers={"anthropic", "deepseek"})
        names = {e["model_name"] for e in doc["model_list"]}
        self.assertIn("claude-code", names)
        self.assertIn("deepseek-fast", names)
        self.assertIn("deepseek-pro", names)
        self.assertNotIn("openai-main", names)
        self.assertNotIn("qwen-turbo", names)

    def test_coding_alias_and_fallback_built(self):
        doc = configure.compile_litellm(ENV, providers={"anthropic", "deepseek"})
        names = {e["model_name"] for e in doc["model_list"]}
        self.assertIn("coding", names)
        fallback_map = {k: v for d in doc["router_settings"]["fallbacks"] for k, v in d.items()}
        self.assertEqual(fallback_map["coding"], ["deepseek-fast"])

    def test_single_candidate_route_has_no_fallback_entry(self):
        doc = configure.compile_litellm(ENV, providers={"google"})
        fallback_map = {k: v for d in doc["router_settings"]["fallbacks"] for k, v in d.items()}
        # research = [gemini-flash, openai-main]; only gemini-flash is available.
        self.assertNotIn("research", fallback_map)
        names = {e["model_name"] for e in doc["model_list"]}
        self.assertIn("research", names)  # alias still created, pointed at gemini-flash

    def test_no_providers_yields_no_aliases(self):
        doc = configure.compile_litellm(ENV, providers=set())
        self.assertEqual(doc["model_list"], [])
        self.assertEqual(doc["router_settings"]["fallbacks"], [])


if __name__ == "__main__":
    unittest.main()
