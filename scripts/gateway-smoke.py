#!/usr/bin/env python3
"""Run inside the litellm container:

    docker compose --profile router exec -T litellm python - < scripts/gateway-smoke.py

With no flags: checks the proxy is reachable, the master key authenticates,
and the model catalog matches what configure.py compiled in — no billable
inference. Pass --call <alias> --prompt '...' to make one real (billable)
request through an alias, optionally --stream.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("GATEWAY_SMOKE_BASE_URL", "http://localhost:4000")


def request(method: str, path: str, body: dict | None = None):
    master_key = os.environ.get("LITELLM_MASTER_KEY")
    if not master_key:
        print("FAIL: LITELLM_MASTER_KEY is not set in this container's environment", file=sys.stderr)
        sys.exit(1)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {master_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def check_liveness() -> None:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health/liveliness", timeout=10) as resp:
            if resp.status != 200:
                print(f"FAIL: liveness returned {resp.status}", file=sys.stderr)
                sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: proxy unreachable at {BASE_URL}: {exc}", file=sys.stderr)
        sys.exit(1)
    print("ok: proxy is alive")


def check_models() -> list[str]:
    status, body = request("GET", "/v1/models")
    if status != 200:
        print(f"FAIL: /v1/models returned {status}: {body}", file=sys.stderr)
        sys.exit(1)
    names = sorted(m["id"] for m in body.get("data", []))
    print(f"ok: authenticated; {len(names)} models in catalog: {', '.join(names)}")
    return names


def billable_call(alias: str, prompt: str, stream: bool) -> None:
    print(f"making a BILLABLE request through alias '{alias}' (stream={stream})...")
    status, body = request(
        "POST", "/v1/chat/completions",
        {"model": alias, "messages": [{"role": "user", "content": prompt}], "stream": stream, "max_tokens": 64},
    )
    if status != 200:
        print(f"FAIL: chat completion returned {status}: {body}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(body, indent=2)[:2000])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--call", help="alias to call with one real (billable) request")
    parser.add_argument("--prompt", default="Reply OK.")
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()

    check_liveness()
    names = check_models()

    if args.call:
        if args.call not in names and args.call != "auto":
            print(f"FAIL: alias '{args.call}' is not in the compiled catalog: {names}", file=sys.stderr)
            sys.exit(1)
        billable_call(args.call, args.prompt, args.stream)


if __name__ == "__main__":
    main()
