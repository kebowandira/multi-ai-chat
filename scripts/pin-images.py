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


def load_compose_services() -> dict[str, str]:
    """Resolve active Compose services and their interpolated image names without loading docker-compose.override.yml."""
    cmd = ["docker", "compose", "-f", str(COMPOSE_PATH), "config", "--format", "json"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        die(f"docker compose config failed:\n{res.stderr.strip()}")
    try:
        doc = json.loads(res.stdout)
    except Exception as exc:
        die(f"failed to parse docker compose config JSON output: {exc}")

    services = doc.get("services", {})
    images = {}
    for name, spec in services.items():
        img = spec.get("image")
        if img:
            images[name] = img
    return images


def normalize_repo(image: str) -> str:
    """Extract repository string without tag or digest."""
    if "@" in image:
        image = image.split("@", 1)[0]
    if ":" in image and "/" in image:
        last_slash = image.rfind("/")
        last_colon = image.rfind(":")
        if last_colon > last_slash:
            return image[:last_colon]
        return image
    elif ":" in image:
        return image.split(":", 1)[0]
    return image


def match_repo_digest(image: str, digests: list[str]) -> str:
    if not digests:
        die(f"no RepoDigests found for {image}")

    repo = normalize_repo(image)

    # Exact match on repo + "@"
    for d in digests:
        if d.startswith(repo + "@"):
            return d

    # Canonical Docker Hub library expansion
    if "/" not in repo:
        canonical_docker_repo = f"docker.io/library/{repo}"
        for d in digests:
            if d.startswith(canonical_docker_repo + "@"):
                return d

    # Exact repository match without registry domain prefix if single-part repo
    for d in digests:
        d_repo = d.split("@")[0]
        if d_repo == repo or (d_repo.endswith("/" + repo) and "/" not in repo):
            return d

    die(f"no matching RepoDigest found for {image} in {digests}")


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
