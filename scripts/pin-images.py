#!/usr/bin/env python3
"""Pull each service's configured image, resolve its immutable registry
digest, and write docker-compose.override.yml + image-lock.json pinning to
those digests. Does not start any container. Includes optional profile images
(caddy, litellm) even when COMPOSE_PROFILES does not enable them, so enabling
them later is already pinned.

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
from common import ROOT, die  # noqa: E402

COMPOSE_PATH = ROOT / "docker-compose.yml"
OVERRIDE_PATH = ROOT / "docker-compose.override.yml"
LOCK_PATH = ROOT / "image-lock.json"

DIGEST_REGEX = re.compile(r"^[a-zA-Z0-9+_.-]+:[a-fA-F0-9]{32,}$")


def load_compose_services() -> dict[str, str]:
    """Resolve active Compose services and their interpolated image names including optional profiles."""
    cmd = ["docker", "compose", "-f", str(COMPOSE_PATH), "--profile", "*", "config", "--format", "json"]
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


def canonical_repo_variants(repo: str) -> set[str]:
    """Return all valid canonical repository name representations for matching."""
    first_part = repo.split("/")[0] if "/" in repo else repo
    has_domain = "." in first_part or ":" in first_part or first_part == "localhost"

    if has_domain:
        return {repo}
    elif "/" in repo:
        return {repo, f"docker.io/{repo}", f"index.docker.io/{repo}"}
    else:
        return {
            repo,
            f"library/{repo}",
            f"docker.io/library/{repo}",
            f"index.docker.io/library/{repo}",
        }


def parse_valid_repo_digest(d: str) -> tuple[str, str] | None:
    """Parse and validate RepoDigest string 'repo@algo:hash'."""
    if not d or "@" not in d:
        return None
    d_repo, _, digest_str = d.partition("@")
    if not DIGEST_REGEX.match(digest_str):
        return None
    return d_repo, digest_str


def match_repo_digest(image: str, digests: list[str]) -> str:
    valid_digests = []
    for d in digests:
        parsed = parse_valid_repo_digest(d.strip() if d else "")
        if parsed:
            valid_digests.append((d.strip(), parsed[0], parsed[1]))

    if not valid_digests:
        die(f"no valid RepoDigests found for {image}")

    repo = normalize_repo(image)
    variants = canonical_repo_variants(repo)

    for raw, d_repo, _ in valid_digests:
        if d_repo in variants:
            return raw

    die(f"no matching RepoDigest found for {image} in {digests}")


def resolve_digest(image: str) -> str:
    input_digest = None
    if "@" in image:
        _, input_digest = image.split("@", 1)
        if not DIGEST_REGEX.match(input_digest):
            die(f"input image {image} contains malformed digest {input_digest}")

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
    matched = match_repo_digest(image, digests)

    if input_digest:
        resolved_digest = matched.split("@", 1)[1]
        if resolved_digest != input_digest:
            die(f"requested digest mismatch for {image}: input specifies {input_digest} but resolved {resolved_digest}")

    return matched


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

    bak_override = OVERRIDE_PATH.with_suffix(".bak")
    bak_lock = LOCK_PATH.with_suffix(".bak")

    override_existed = OVERRIDE_PATH.exists()
    lock_existed = LOCK_PATH.exists()

    if override_existed:
        bak_override.write_bytes(OVERRIDE_PATH.read_bytes())
    if lock_existed:
        bak_lock.write_bytes(LOCK_PATH.read_bytes())

    override_replaced = False
    lock_replaced = False

    # Note on Dual-Rename Limits:
    # Two separate POSIX file renames (for OVERRIDE_PATH and LOCK_PATH) cannot be
    # transactionally crash-atomic across process termination or SIGKILL.
    # The try/except block below performs in-process best-effort rollback (restoring
    # backups or unlinking newly created files if a failure occurs during writing or renaming).
    # If the process is forcefully killed between the two renames, or if secondary filesystem
    # failures occur during rollback, pair consistency cannot be guaranteed.
    try:
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
        override_replaced = True

        tmp_lock.replace(LOCK_PATH)
        lock_replaced = True

    except Exception as exc:
        if override_replaced:
            if override_existed and bak_override.exists():
                bak_override.replace(OVERRIDE_PATH)
            elif OVERRIDE_PATH.exists():
                OVERRIDE_PATH.unlink()

        if lock_replaced:
            if lock_existed and bak_lock.exists():
                bak_lock.replace(LOCK_PATH)
            elif LOCK_PATH.exists():
                LOCK_PATH.unlink()

        for t in (tmp_override, tmp_lock, bak_override, bak_lock):
            if t.exists():
                try:
                    t.unlink()
                except Exception:
                    pass

        die(f"failed to update image lock files cleanly: {exc}")

    for bak in (bak_override, bak_lock):
        if bak.exists():
            try:
                bak.unlink()
            except Exception:
                pass

    print(f"wrote {OVERRIDE_PATH}")
    print(f"wrote {LOCK_PATH}")
    print("review each image's release notes/advisories before relying on this lock in production")


if __name__ == "__main__":
    main()
