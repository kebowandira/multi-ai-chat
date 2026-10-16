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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, die  # noqa: E402

COMPOSE_PATH = ROOT / "docker-compose.yml"
OVERRIDE_PATH = ROOT / "docker-compose.override.yml"
LOCK_PATH = ROOT / "image-lock.json"


def resolve_digest(image: str) -> str:
    print(f"pulling {image} ...")
    pull = subprocess.run(["docker", "pull", "--quiet", image], capture_output=True, text=True)
    if pull.returncode != 0:
        die(f"docker pull failed for {image}:\n{pull.stderr}")
    inspect = subprocess.run(
        ["docker", "image", "inspect", image, "--format", "{{join .RepoDigests \",\"}}"],
        capture_output=True, text=True,
    )
    if inspect.returncode != 0 or not inspect.stdout.strip():
        die(f"could not read RepoDigests for {image}; is it a registry image?")
    digests = inspect.stdout.strip().split(",")
    # Prefer a digest reference matching this image's own repository.
    repo = image.split(":")[0]
    for d in digests:
        if d.startswith(repo + "@"):
            return d
    return digests[0]


def main() -> None:
    doc = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    services = doc.get("services", {})

    lock: dict[str, str] = {}
    override_services: dict[str, dict] = {}

    for name, spec in services.items():
        image = spec.get("image")
        if not image:
            continue
        digest_ref = resolve_digest(image)
        lock[name] = digest_ref
        override_services[name] = {"image": digest_ref}

    OVERRIDE_PATH.write_text(
        yaml.safe_dump({"services": override_services}, sort_keys=False), encoding="utf-8"
    )
    LOCK_PATH.write_text(
        json.dumps(
            {"resolved_at": datetime.now(timezone.utc).isoformat(), "images": lock},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OVERRIDE_PATH}")
    print(f"wrote {LOCK_PATH}")
    print("review each image's release notes/advisories before relying on this lock in production")


if __name__ == "__main__":
    main()
