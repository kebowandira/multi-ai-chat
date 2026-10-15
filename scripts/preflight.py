#!/usr/bin/env python3
"""Sanity checks before scripts/configure.py / deploy.sh. Exits non-zero on
the first hard failure; prints warnings for soft issues and keeps going."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ENV_EXAMPLE_PATH, ENV_PATH, ROOT, active_providers, read_env_file  # noqa: E402

MIN_COMPOSE = (2, 30, 0)


def warn(msg: str) -> None:
    print(f"warning: {msg}")


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def check_tool(name: str, required: bool = True) -> None:
    if shutil.which(name) is None:
        (fail if required else warn)(f"'{name}' not found on PATH")
    else:
        print(f"ok: {name} found")


def check_compose_version() -> None:
    try:
        res = subprocess.run(["docker", "compose", "version", "--short"], capture_output=True, text=True)
        if res.returncode != 0:
            fail(f"docker compose command failed: {res.stderr.strip() or 'docker compose plugin not available'}")
        out = res.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        fail(f"could not determine docker compose version: {exc}")

    parts = out.lstrip("v").split(".")
    try:
        version = tuple(int(p) for p in parts[:3])
    except ValueError:
        fail(f"unrecognized docker compose version string: '{out}'; require >= {'.'.join(map(str, MIN_COMPOSE))}")

    if version < MIN_COMPOSE:
        fail(f"docker compose {out} is older than required {'.'.join(map(str, MIN_COMPOSE))} (env_file format: raw)")
    print(f"ok: docker compose {out}")


def check_docker_daemon() -> None:
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if res.returncode != 0:
            fail(f"docker daemon is not running or unreachable: {res.stderr.strip() or 'check docker service/permissions'}")
    except Exception as exc:  # noqa: BLE001
        fail(f"docker daemon check failed: {exc}")
    print("ok: docker daemon is reachable")


def check_env() -> None:
    if not ENV_PATH.exists():
        fail(f"{ENV_PATH} missing; run: python3 scripts/init-env.py")
    values = read_env_file(ENV_PATH)
    example = read_env_file(ENV_EXAMPLE_PATH)
    missing_keys = set(example) - set(values)
    if missing_keys:
        warn(f".env is missing keys present in .env.example: {', '.join(sorted(missing_keys))}")

    profiles = set(p.strip() for p in (values.get("COMPOSE_PROFILES") or "").split(",") if p.strip())

    if "standalone" in profiles:
        chat_domain = values.get("CHAT_DOMAIN", "chat.example.com")
        if not chat_domain or chat_domain == "chat.example.com":
            warn("CHAT_DOMAIN is still unset or placeholder 'chat.example.com'")

    providers = active_providers(values)
    if not providers:
        warn("no provider API keys are set; LibreChat will start with no usable endpoint")
    else:
        print(f"ok: active providers: {', '.join(sorted(providers))}")

    required_secrets = ["JWT_SECRET", "MEILI_MASTER_KEY", "MONGO_ROOT_PASSWORD"]
    if "router" in profiles:
        required_secrets.append("LITELLM_MASTER_KEY")

    for secret in required_secrets:
        if not values.get(secret):
            fail(f".env variable {secret} is missing or blank; run: python3 scripts/init-env.py")


def check_ports() -> None:
    import socket

    if not ENV_PATH.exists():
        return
    values = read_env_file(ENV_PATH)
    profiles = set(p.strip() for p in (values.get("COMPOSE_PROFILES") or "").split(",") if p.strip())

    if "standalone" in profiles:
        for port in (80, 443):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    warn(f"port {port} already has a listener; standalone Caddy will fail to bind if not already running")


def main() -> None:
    print(f"project root: {ROOT}")
    check_tool("docker", required=True)
    check_tool("git", required=True)
    check_tool("gh", required=False)
    check_compose_version()
    check_docker_daemon()
    check_env()
    check_ports()
    print("preflight complete")


if __name__ == "__main__":
    main()
