#!/usr/bin/env python3
"""Actual LiteLLM proxy process, talking to a local mock OpenAI-compatible
server — never a real provider. Run inside the dedicated gateway venv:

    python3 -m venv .venv-gateway
    .venv-gateway/bin/python -m pip install 'litellm[proxy]==1.104.0' socksio prisma
    .venv-gateway/bin/python tests/integration_gateway.py

Verifies, against a real litellm binary: the "auto" alias is rewritten to
"coding" by router/custom_router.py for a coding-shaped prompt, an explicit
"/cheap" prefix overrides classification, and a primary-model failure falls
over to the configured backup. This is the actual mechanism LibreChat talks
to in production, just pointed at a mock backend instead of real providers.

The pinned litellm version is a candidate from the last official release
check, not an evergreen guarantee — see docs/VALIDATION.md. If this script's
assumptions about litellm's callback/config shape stop matching upstream,
that is exactly what this test exists to catch; fix the mismatch here and in
router/custom_router.py together, don't skip it.
"""
from __future__ import annotations

import http.server
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "ok" if condition else "FAIL"
    print(f"{status}: {label}{(' - ' + detail) if detail and not condition else ''}")
    if not condition:
        FAILURES.append(label)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class MockBackend(http.server.BaseHTTPRequestHandler):
    """Echoes the model it was called with; /mock-fail always 500s."""

    fail_model: str | None = None

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        model = body.get("model", "")
        if model == self.fail_model:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error": "mock induced failure"}')
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        payload = {
            "id": "mock-1",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": f"handled-by:{model}"}, "finish_reason": "stop"}],
        }
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *a):  # noqa: D102 - silence default request logging
        pass


def start_mock_backend(port: int, fail_model: str | None) -> http.server.HTTPServer:
    handler = type("Handler", (MockBackend,), {"fail_model": fail_model})
    server = http.server.HTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


CONFIG_TEMPLATE = """
model_list:
  - model_name: coding-primary
    litellm_params:
      model: openai/coding-primary
      api_base: http://127.0.0.1:{mock_port}
      api_key: sk-mock
  - model_name: coding-backup
    litellm_params:
      model: openai/coding-backup
      api_base: http://127.0.0.1:{mock_port}
      api_key: sk-mock
  - model_name: coding
    litellm_params:
      model: openai/coding-primary
      api_base: http://127.0.0.1:{mock_port}
      api_key: sk-mock
  - model_name: cheap
    litellm_params:
      model: openai/cheap-primary
      api_base: http://127.0.0.1:{mock_port}
      api_key: sk-mock
  - model_name: auto
    litellm_params:
      model: openai/cheap-primary
      api_base: http://127.0.0.1:{mock_port}
      api_key: sk-mock

litellm_settings:
  callbacks: ["router.custom_router.router_logger"]

router_settings:
  fallbacks:
    - coding: [coding-backup]

general_settings:
  master_key: sk-test-master
"""


def wait_for_health(base_url: str, timeout: float = 30) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health/liveliness", timeout=2) as resp:
                if resp.status == 200:
                    return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
    raise TimeoutError(f"litellm proxy at {base_url} never became healthy")


def chat(base_url: str, model: str, content: str) -> dict:
    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps({"model": model, "messages": [{"role": "user", "content": content}]}).encode(),
        method="POST",
        headers={"Authorization": "Bearer sk-test-master", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return {"error": exc.read().decode(), "status": exc.code}


def main() -> None:
    mock_port = free_port()
    proxy_port = free_port()

    start_mock_backend(mock_port, fail_model=None)

    config_text = CONFIG_TEMPLATE.format(mock_port=mock_port)
    with tempfile.TemporaryDirectory() as tmp:
        config_path = Path(tmp) / "config.yaml"
        config_path.write_text(config_text, encoding="utf-8")

        env = {**os.environ, "PYTHONPATH": f"{ROOT}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"}
        proc = subprocess.Popen(
            [sys.executable, "-m", "litellm", "--config", str(config_path), "--port", str(proxy_port)],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        base_url = f"http://127.0.0.1:{proxy_port}"
        try:
            wait_for_health(base_url)

            resp = chat(base_url, "auto", "Debug this Python function, it raises a stack trace.")
            handled_by = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            check("auto classifies a coding prompt to the coding alias", handled_by == "handled-by:coding-primary", repr(resp))

            resp = chat(base_url, "auto", "/cheap Rewrite this email professionally.")
            handled_by = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            check("explicit /cheap prefix overrides classification", handled_by == "handled-by:cheap-primary", repr(resp))

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            if FAILURES:
                print("\n--- litellm proxy output (for debugging) ---")
                print(proc.stdout.read() if proc.stdout else "(no output captured)")

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed: {FAILURES}", file=sys.stderr)
        sys.exit(1)
    print("\nall integration checks passed")


if __name__ == "__main__":
    main()
