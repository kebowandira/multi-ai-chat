"""Shared helpers for the scripts/ CLI tools. No third-party dependencies
beyond PyYAML and python-dotenv so these run with the system python3 on a
bare VPS (requirements-dev.txt is only for the local validation venv)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
RUNTIME_DIR = ROOT / "runtime"


def die(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def read_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file (no quoting/interpolation)."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            die(f"{path}:{lineno}: expected KEY=VALUE, got: {stripped!r}")
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


def write_env_file(path: Path, values: dict[str, str], template: Path) -> None:
    """Rewrite ``path`` preserving the comments/ordering of ``template``."""
    lines = []
    seen = set()
    for line in template.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        lines.append(f"{key}={values.get(key, '')}")
        seen.add(key)
    extra = {k: v for k, v in values.items() if k not in seen}
    for key, value in extra.items():
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def require_env(values: dict[str, str], *keys: str) -> None:
    missing = [k for k in keys if not values.get(k)]
    if missing:
        die(f"missing required .env values: {', '.join(missing)}")


# (provider_env_var, model_name) pairs used by configure.py to decide which
# custom endpoints / LiteLLM model_list entries to keep.
PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "zai": "ZAI_API_KEY",
    "xai": "XAI_API_KEY",
}


def active_providers(values: dict[str, str]) -> set[str]:
    return {name for name, env_key in PROVIDER_KEYS.items() if values.get(env_key)}
