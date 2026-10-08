#!/usr/bin/env python3
"""Create .env from .env.example and fill in unique secrets.

Idempotent: existing non-blank values (including provider keys you already
set) are never overwritten. Safe to rerun after editing .env.example.
"""
from __future__ import annotations

import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ENV_EXAMPLE_PATH, ENV_PATH, die, read_env_file, write_env_file  # noqa: E402

# Fields this script is responsible for generating when blank.
GENERATED_HEX32 = [
    "JWT_SECRET",
    "JWT_REFRESH_SECRET",
    "SESSION_SECRET",
    "MEILI_MASTER_KEY",
    "LITELLM_MASTER_KEY",
    "LITELLM_SALT_KEY",
]
GENERATED_URLSAFE = [
    "MONGO_ROOT_PASSWORD",
    "MONGO_APP_PASSWORD",
    "POSTGRES_PASSWORD",
]
# CREDS_KEY/CREDS_IV are LibreChat's credential-encryption key/IV and must be
# exact hex lengths (32 bytes / 16 bytes) per LibreChat's documented format.
GENERATED_FIXED_HEX = {
    "CREDS_KEY": 32,
    "CREDS_IV": 16,
}


def main() -> None:
    if not ENV_EXAMPLE_PATH.exists():
        die(f"{ENV_EXAMPLE_PATH} not found")

    values = read_env_file(ENV_PATH) if ENV_PATH.exists() else read_env_file(ENV_EXAMPLE_PATH)

    changed = []
    for key in GENERATED_HEX32:
        if not values.get(key):
            values[key] = secrets.token_hex(32)
            changed.append(key)
    for key in GENERATED_URLSAFE:
        if not values.get(key):
            values[key] = secrets.token_urlsafe(24)
            changed.append(key)
    for key, nbytes in GENERATED_FIXED_HEX.items():
        if not values.get(key):
            values[key] = secrets.token_hex(nbytes)
            changed.append(key)

    write_env_file(ENV_PATH, values, template=ENV_EXAMPLE_PATH)
    ENV_PATH.chmod(0o600)

    if changed:
        print(f"generated: {', '.join(changed)}")
    else:
        print("no secrets were blank; .env left as-is")
    print(f"wrote {ENV_PATH}")
    print("next: edit CHAT_DOMAIN, ACME_EMAIL, and provider API keys in .env")


if __name__ == "__main__":
    main()
