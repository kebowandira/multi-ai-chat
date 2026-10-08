#!/usr/bin/env python3
"""Compile the source templates (librechat.yaml, litellm_config.yaml) into
runtime/, substituting ${VAR} from .env and pruning anything whose provider
key is blank. Idempotent; safe to rerun after editing .env or either
template. Never edit files under runtime/ by hand — they are regenerated.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, RUNTIME_DIR, active_providers, die, read_env_file  # noqa: E402

LIBRECHAT_SRC = ROOT / "librechat.yaml"
LITELLM_SRC = ROOT / "litellm_config.yaml"
POLICY_PATH = ROOT / "router" / "routing-policy.json"

_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

# model_name -> provider key in common.PROVIDER_KEYS, for pruning model_list.
MODEL_PROVIDER = {
    "claude-code": "anthropic",
    "openai-main": "openai",
    "openai-low-cost": "openai",
    "gemini-flash": "google",
    "gemini-flash-lite": "google",
    "deepseek-fast": "deepseek",
    "deepseek-pro": "deepseek",
    "qwen-turbo": "qwen",
    "qwen-plus": "qwen",
    "glm-manual": "zai",
    "grok-manual": "xai",
}


def substitute(value, env: dict[str, str]):
    if isinstance(value, str):
        return _VAR_RE.sub(lambda m: env.get(m.group(1), ""), value)
    if isinstance(value, list):
        return [substitute(v, env) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, env) for k, v in value.items()}
    return value


def compile_librechat(env: dict[str, str], providers: set[str], router_enabled: bool) -> dict:
    doc = yaml.safe_load(LIBRECHAT_SRC.read_text(encoding="utf-8"))
    custom = doc.get("endpoints", {}).get("custom", [])
    kept = []
    name_to_provider = {
        "DeepSeek": "deepseek",
        "Qwen": "qwen",
        "Z.ai": "zai",
        "xAI": "xai",
        "SmartRouter": None,  # gated on router_enabled, not a provider key
    }
    for entry in custom:
        provider = name_to_provider.get(entry.get("name"))
        if entry.get("name") == "SmartRouter":
            if not router_enabled:
                continue
        elif provider not in providers:
            continue
        kept.append(substitute(entry, env))
    doc["endpoints"]["custom"] = kept
    return doc


def compile_litellm(env: dict[str, str], providers: set[str]) -> dict:
    doc = yaml.safe_load(LITELLM_SRC.read_text(encoding="utf-8"))
    policy = _load_policy()

    model_list = []
    for entry in doc.get("model_list", []):
        name = entry["model_name"]
        provider = MODEL_PROVIDER.get(name)
        if provider is not None and provider not in providers:
            continue
        model_list.append(substitute(entry, env))

    available_names = {e["model_name"] for e in model_list}
    fallbacks = []
    for route, candidates in policy["routes"].items():
        filtered = [m for m in candidates if m in available_names]
        if not filtered:
            continue
        primary = next(e for e in model_list if e["model_name"] == filtered[0])
        model_list.append({"model_name": route, "litellm_params": copy.deepcopy(primary["litellm_params"])})
        if len(filtered) > 1:
            fallbacks.append({route: filtered[1:]})

    default_route = policy["default_route"]
    if default_route in {e["model_name"] for e in model_list} and "auto" not in {e["model_name"] for e in model_list}:
        primary = next(e for e in model_list if e["model_name"] == default_route)
        model_list.append({"model_name": "auto", "litellm_params": copy.deepcopy(primary["litellm_params"])})

    doc["model_list"] = model_list
    doc.setdefault("router_settings", {})["fallbacks"] = fallbacks
    return doc


def _load_policy() -> dict:
    import json

    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def main() -> None:
    if not ROOT.joinpath(".env").exists():
        die(".env not found; run scripts/init-env.py first")
    env = read_env_file(ROOT / ".env")
    providers = active_providers(env)
    router_enabled = "router" in (env.get("COMPOSE_PROFILES") or "").split(",")

    RUNTIME_DIR.mkdir(exist_ok=True)

    librechat_doc = compile_librechat(env, providers, router_enabled)
    (RUNTIME_DIR / "librechat.yaml").write_text(
        yaml.safe_dump(librechat_doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    if router_enabled:
        litellm_doc = compile_litellm(env, providers)
        (RUNTIME_DIR / "litellm_config.yaml").write_text(
            yaml.safe_dump(litellm_doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )
    else:
        stale = RUNTIME_DIR / "litellm_config.yaml"
        if stale.exists():
            stale.unlink()

    print(f"providers active: {', '.join(sorted(providers)) or '(none)'}")
    print(f"router (LiteLLM): {'enabled' if router_enabled else 'disabled'}")
    print(f"wrote {RUNTIME_DIR / 'librechat.yaml'}")
    if router_enabled:
        print(f"wrote {RUNTIME_DIR / 'litellm_config.yaml'}")


if __name__ == "__main__":
    main()
