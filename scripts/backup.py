#!/usr/bin/env python3
"""Cold, consistent backup: stop the stack, dump Mongo/Postgres, tar the
upload volume, start the stack again, then push everything to the restic
repository configured via RESTIC_REPOSITORY/RESTIC_PASSWORD in .env.

This implies a maintenance window — see docs/OPERATIONS.md. Run a restore
drill before relying on this in production.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, die, read_env_file, require_env  # noqa: E402


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, **kw)


def compose(*args: str) -> None:
    run(["docker", "compose", *args], cwd=ROOT)


def main() -> None:
    env = read_env_file(ROOT / ".env")
    require_env(env, "RESTIC_REPOSITORY", "RESTIC_PASSWORD", "MONGO_ROOT_PASSWORD", "POSTGRES_PASSWORD")

    restic_env = {
        "RESTIC_REPOSITORY": env["RESTIC_REPOSITORY"],
        "RESTIC_PASSWORD": env["RESTIC_PASSWORD"],
    }
    import os

    full_env = {**os.environ, **restic_env}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.TemporaryDirectory(prefix="multi-ai-chat-backup-") as tmp:
        tmp_path = Path(tmp)
        mongo_dump = tmp_path / "mongodump"
        pg_dump = tmp_path / "pg.dump"

        print("stopping application services for a consistent snapshot...")
        compose("stop", "librechat", "rag_api")

        run([
            "docker", "compose", "exec", "-T", "mongodb",
            "mongodump", "--username", "root", "--password", env["MONGO_ROOT_PASSWORD"],
            "--authenticationDatabase", "admin", "--archive",
        ], cwd=ROOT, stdout=open(mongo_dump, "wb"))

        run([
            "docker", "compose", "exec", "-T", "vectordb",
            "pg_dump", "-U", "rag", "-d", "rag", "-F", "c",
        ], cwd=ROOT, stdout=open(pg_dump, "wb"), env={**__import__("os").environ, "PGPASSWORD": env["POSTGRES_PASSWORD"]})

        print("restarting application services...")
        compose("start", "librechat", "rag_api")

        run([
            "docker", "run", "--rm",
            "-v", "multi-ai-chat_librechat_uploads:/data:ro",
            "-v", f"{tmp_path}:/backup",
            "alpine", "tar", "czf", f"/backup/uploads-{stamp}.tar.gz", "-C", "/data", ".",
        ])

        print("pushing snapshot to restic repository...")
        run(["restic", "snapshots"], env=full_env)  # fails fast if repo is unreachable/not initialized
        run(["restic", "backup", str(tmp_path), "--tag", f"multi-ai-chat-{stamp}"], env=full_env)

    print(f"backup {stamp} complete")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        die(f"command failed: {exc}")
