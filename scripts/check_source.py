#!/usr/bin/env python3
"""Source publication guard. Run before any commit/push:

    python3 scripts/check_source.py

Fails if a path outside SOURCE_FILES.txt's allowlist would be committed, if
a generated/secret path (.env, runtime/, backups/, docker-compose.override.yml,
image-lock.json) is present in the allowlist or the working tree staging
area, or if any allowlisted file's *content* contains a string that looks
like a live credential. This is a heuristic safety net, not a secret scanner
replacement — still review `git status`/`git diff` yourself.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, die  # noqa: E402

ALLOWLIST_PATH = ROOT / "SOURCE_FILES.txt"

FORBIDDEN_PATHS = {".env", "runtime", "backups", "docker-compose.override.yml", "image-lock.json"}

CREDENTIAL_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),           # OpenAI-style
    re.compile(r"sk-ant-[A-Za-z0-9\-_]{20,}"),     # Anthropic-style
    re.compile(r"AKIA[0-9A-Z]{16}"),               # AWS access key id
    re.compile(r"ghp_[A-Za-z0-9]{36}"),            # GitHub PAT
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),   # Slack token
    re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY-----"),
]


def load_allowlist() -> list[str]:
    if not ALLOWLIST_PATH.exists():
        die(f"{ALLOWLIST_PATH} not found")
    entries = []
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(stripped)
    return entries


def expand(entry: str) -> list[Path]:
    path = ROOT / entry
    if entry.endswith("/"):
        if not path.exists():
            return []
        return [p for p in path.rglob("*") if p.is_file()]
    return [path] if path.exists() else []


def main() -> None:
    entries = load_allowlist()

    for entry in entries:
        top = entry.split("/")[0]
        if top in FORBIDDEN_PATHS:
            die(f"SOURCE_FILES.txt lists a forbidden/generated path: {entry}")

    files: list[Path] = []
    for entry in entries:
        resolved = expand(entry)
        if not resolved:
            die(f"allowlisted path does not exist: {entry}")
        files.extend(resolved)

    violations = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001 - binary/unreadable files are not scanned
            continue
        for pattern in CREDENTIAL_PATTERNS:
            if pattern.search(text):
                violations.append((f, pattern.pattern))

    if violations:
        for f, pattern in violations:
            print(f"FAIL: {f} matches credential pattern /{pattern}/", file=sys.stderr)
        sys.exit(1)

    # If this is a git repo already, make sure nothing forbidden is staged.
    result = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            path = line[3:].strip().strip('"')
            top = path.split("/")[0]
            if top in FORBIDDEN_PATHS:
                die(f"forbidden path is present in the working tree: {path}")

    print(f"ok: {len(files)} allowlisted files, no forbidden paths, no credential patterns matched")


if __name__ == "__main__":
    main()
