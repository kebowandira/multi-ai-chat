#!/usr/bin/env python3
"""Pull each service's configured image, resolve its immutable registry
digest, and write docker-compose.override.yml + image-lock.json pinning to
those digests. Does not start any container. Includes the litellm image even
when COMPOSE_PROFILES does not enable the router profile, so enabling it
later is already pinned.

This makes the *chosen* artifacts reproducible. It does not substitute for
reading upstream release notes/security advisories before trusting them —
see README.md section 5.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, die, read_env_file  # noqa: E402

COMPOSE_PATH = ROOT / "docker-compose.yml"
OVERRIDE_PATH = ROOT / "docker-compose.override.yml"
LOCK_PATH = ROOT / "image-lock.json"

_VAR_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def interpolate_image_var(val: str, env: dict[str, str]) -> str:
    def _sub(m: re.Match) -> str:
        var_name = m.group(1)
        default_val = m.group(2) if m.group(2) is not None else ""
        return env.get(var_name) or default_val

    return _VAR_ENV_RE.sub(_sub, val)


def load_compose_services() -> dict[str, str]:
    """Resolve active Compose services and their interpolated image names without loading docker-compose.override.yml."""
    cmd = ["docker", "compose", "-f", str(COMPOSE_PATH), "config", "--format", "json"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        doc = json.loads(res.stdout)
        services = doc.get("services", {})
        images = {}
        for name, spec in services.items():
            img = spec.get("image")
            if img:
                images[name] = img
        return images
    except Exception:
        # Fallback to PyYAML with env substitution if docker compose CLI fails
        raw = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
        env = read_env_file(ROOT / ".env") if (ROOT / ".env").exists() else {}
        images = {}
        for name, spec in (raw.get("services") or {}).items():
            img = spec.get("image")
            if img:
                images[name] = interpolate_image_var(img, env)
        return images


def match_repo_digest(image: str, digests: list[str]) -> str:
    if not digests:
        die(f"no RepoDigests found for {image}")

    if ":" in image and "/" in image:
        last_slash = image.rfind("/")
        last_colon = image.rfind(":")
        if last_colon > last_slash:
            repo = image[:last_colon]
        else:
            repo = image
    elif ":" in image:
        repo = image.split(":", 1)[0]
    else:
        repo = image

    for d in digests:
        if d.startswith(repo + "@"):
            return d

    repo_name = repo.split("/")[-1]
    for d in digests:
        d_repo = d.split("@")[0]
        if d_repo.endswith("/" + repo_name) or d_repo == repo_name:
            return d

    return digests[0]


def resolve_digest(image: str) -> str:
    print(f"pulling {image} ...")
    pull = subprocess.run(["docker", "pull", "--quiet", image], capture_output=True, text=True)
    if pull.returncode != 0:
        die(f"docker pull failed for {image}:\n{pull.stderr.strip()}")

    inspect = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{join .RepoDigests \",\"}}"],
        capture_output=True, text=True,
    )
    if inspect.returncode != 0 or not inspect.stdout.strip():
        die(f"could not read RepoDigests for {image}; is it a registry image?")

    digests = [d.strip() for d in inspect.stdout.strip().split(",") if d.strip()]
    return match_repo_digest(image, digests)


def main() -> None:
    service_images = load_compose_services()
    if not service_images:
        die("no service images found to pin")

    lock: dict[str, str] = {}
    override_services: dict[str, dict] = {}

    for name, image in service_images.items():
        digest_ref = resolve_digest(image)
        lock[name] = digest_ref
        override_services[name] = {"image": digest_ref}

    tmp_override = OVERRIDE_PATH.with_suffix(".tmp")
    tmp_lock = LOCK_PATH.with_suffix(".tmp")

    tmp_override.write_text(
        yaml.safe_dump({"services": override_services}, sort_keys=False), encoding="utf-8"
    )
    tmp_lock.write_text(
        json.dumps(
            {"resolved_at": datetime.now(timezone.utc).isoformat(), "images": lock},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    tmp_override.replace(OVERRIDE_PATH)
    tmp_lock.replace(LOCK_PATH)

    print(f"wrote {OVERRIDE_PATH}")
    print(f"wrote {LOCK_PATH}")
    print("review each image's release notes/advisories before relying on this lock in production")


if __name__ == "__main__":
    main()
