#!/usr/bin/env python3
"""Actual LiteLLM proxy process, talking to a local mock OpenAI-compatible
server — never a real provider. Run inside the dedicated gateway venv:

    python3 -m venv .venv-gateway
    .venv-gateway/bin/python -m pip install 'litellm[proxy]==1.104.0' socksio prisma
    .venv-gateway/bin/python tests/integration_gateway.py

Verifies against a real litellm binary:
  - Missing and invalid gateway keys fail without reaching the mock backend
  - Auto classification, explicit UI route precedence, prefix precedence/removal, and follow-up behavior
  - Missing-key pruning does not advertise unusable route aliases
  - Primary model fallback and fallback exhaustion behavior without infinite loops
  - Streaming SSE framing and completion termination; mid-stream failure surfacing
  - Text-only route guards, input limits, and output limits enforced before reaching mock
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

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import configure  # noqa: E402

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
    """Echoes the model it was called with; supports failure modes and call tracking."""

    fail_models: set[str] = set()
    call_log: list[dict] = []
    lock = threading.Lock()

    @classmethod
    def reset(cls):
        with cls.lock:
            cls.fail_models = set()
            cls.call_log = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw_body or b"{}")
        except Exception:
            body = {}
        model = body.get("model", "")
        stream = body.get("stream", False)

        with self.lock:
            self.call_log.append({
                "model": model,
                "body": body,
                "headers": dict(self.headers),
            })

        if model in self.fail_models:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "mock induced failure"}')
            return

        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            chunk1 = {
                "id": "mock-stream-1",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": f"handled-by:{model}"}, "finish_reason": None}],
            }
            chunk2 = {
                "id": "mock-stream-2",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            self.wfile.write(f"data: {json.dumps(chunk1)}\n\n".encode())
            self.wfile.write(f"data: {json.dumps(chunk2)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
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

    def log_message(self, *a):
        pass


def start_mock_backend(port: int) -> http.server.HTTPServer:
    MockBackend.reset()
    server = http.server.HTTPServer(("127.0.0.1", port), MockBackend)
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
  - model_name: research-primary
    litellm_params:
      model: openai/research-primary
      api_base: http://127.0.0.1:{mock_port}
      api_key: sk-mock
  - model_name: cheap-primary
    litellm_params:
      model: openai/cheap-primary
      api_base: http://127.0.0.1:{mock_port}
      api_key: sk-mock
  - model_name: coding
    litellm_params:
      model: openai/coding-primary
      api_base: http://127.0.0.1:{mock_port}
      api_key: sk-mock
  - model_name: research
    litellm_params:
      model: openai/research-primary
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


def chat(
    base_url: str,
    model: str,
    messages_or_content,
    api_key: str | None = "sk-test-master",
    stream: bool = False,
    extra_payload: dict | None = None,
) -> tuple[int, dict | str]:
    if isinstance(messages_or_content, str):
        messages = [{"role": "user", "content": messages_or_content}]
    else:
        messages = messages_or_content

    payload = {"model": model, "messages": messages, "stream": stream}
    if extra_payload:
        payload.update(extra_payload)

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        f"{base_url}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode()
            if stream:
                return resp.status, raw
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw_err = exc.read().decode()
        try:
            return exc.code, json.loads(raw_err)
        except Exception:
            return exc.code, raw_err


def start_proxy(config_text: str, proxy_port: int, tmp_dir: Path) -> subprocess.Popen:
    config_path = tmp_dir / f"config_{proxy_port}.yaml"
    config_path.write_text(config_text, encoding="utf-8")

    env = {**os.environ, "PYTHONPATH": f"{ROOT}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"}
    litellm_bin = Path(sys.executable).parent / "litellm"
    cmd = [str(litellm_bin)] if litellm_bin.exists() else [sys.executable, "-m", "litellm.proxy.proxy_cli"]
    proc = subprocess.Popen(
        [*cmd, "--config", str(config_path), "--port", str(proxy_port)],
        cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    wait_for_health(f"http://127.0.0.1:{proxy_port}")
    return proc


def test_gateway_auth(base_url: str):
    MockBackend.reset()
    status, resp = chat(base_url, "auto", "hello", api_key=None)
    check("missing gateway key fails with 401/403", status in (401, 403), f"status={status}, resp={resp}")

    status, resp = chat(base_url, "auto", "hello", api_key="sk-invalid-key")
    check("invalid gateway key fails with 400/401/403", status in (400, 401, 403), f"status={status}, resp={resp}")

    check("missing/invalid gateway key does not reach mock backend", len(MockBackend.call_log) == 0, f"calls={len(MockBackend.call_log)}")


def test_classification_and_precedence(base_url: str):
    MockBackend.reset()
    status, resp = chat(base_url, "auto", "Debug this Python function, it raises a stack trace.")
    handled_by = resp.get("choices", [{}])[0].get("message", {}).get("content", "") if isinstance(resp, dict) else ""
    check("auto classifies coding prompt to coding-primary", handled_by == "handled-by:coding-primary", f"status={status}, resp={resp}")

    status, resp = chat(base_url, "auto", "Riset pasar Indonesia.")
    handled_by = resp.get("choices", [{}])[0].get("message", {}).get("content", "") if isinstance(resp, dict) else ""
    check("auto classifies research prompt to research-primary", handled_by == "handled-by:research-primary", f"status={status}, resp={resp}")

    status, resp = chat(base_url, "auto", "/cheap Rewrite this email professionally.")
    handled_by = resp.get("choices", [{}])[0].get("message", {}).get("content", "") if isinstance(resp, dict) else ""
    check("explicit /cheap prefix overrides classification", handled_by == "handled-by:cheap-primary", f"status={status}, resp={resp}")

    status, resp = chat(base_url, "cheap", "/coding Refactor this Python function.")
    handled_by = resp.get("choices", [{}])[0].get("message", {}).get("content", "") if isinstance(resp, dict) else ""
    check("explicit UI route cheap wins over /coding prompt prefix", handled_by == "handled-by:cheap-primary", f"status={status}, resp={resp}")

    last_body = MockBackend.call_log[-1]["body"]
    upstream_content = last_body["messages"][0]["content"]
    check("anchor /coding prefix is stripped when sent upstream", upstream_content.strip() == "Refactor this Python function.", f"content={upstream_content!r}")

    messages = [
        {"role": "user", "content": "/coding Fix bug"},
        {"role": "assistant", "content": "Fixed"},
        {"role": "user", "content": "continue"},
    ]
    status, resp = chat(base_url, "auto", messages)
    handled_by = resp.get("choices", [{}])[0].get("message", {}).get("content", "") if isinstance(resp, dict) else ""
    check("follow-up message respects anchor message classification", handled_by == "handled-by:coding-primary", f"status={status}, resp={resp}")


def test_fallback_and_exhaustion(base_url: str):
    MockBackend.reset()
    MockBackend.fail_models = {"coding-primary"}

    status, resp = chat(base_url, "coding", "Fix this bug")
    handled_by = resp.get("choices", [{}])[0].get("message", {}).get("content", "") if isinstance(resp, dict) else ""
    check("failed primary reaches intended fallback coding-backup", handled_by == "handled-by:coding-backup", f"status={status}, resp={resp}")
    models_called = [c["model"] for c in MockBackend.call_log]
    check("call log records primary then backup call", models_called[0] == "coding-primary" and models_called[-1] == "coding-backup" and "coding-backup" in models_called, f"called={models_called}")

    MockBackend.reset()
    MockBackend.fail_models = {"coding-primary", "coding-backup"}
    status, resp = chat(base_url, "coding", "Fix this bug")
    check("exhausted fallback returns error status (500)", status == 500, f"status={status}, resp={resp}")
    total_calls = len(MockBackend.call_log)
    check("exhausted fallback stops after retries and does not loop infinitely", 1 <= total_calls <= 10, f"total_calls={total_calls}")


def test_streaming(base_url: str):
    MockBackend.reset()
    MockBackend.fail_models = set()

    status, raw_sse = chat(base_url, "coding", "Fix this bug", stream=True)
    check("streaming produces HTTP 200", status == 200, f"status={status}")
    check("streaming output contains data chunks and [DONE]", "data: " in raw_sse and "[DONE]" in raw_sse, f"raw={raw_sse}")

    MockBackend.reset()
    MockBackend.fail_models = {"coding-primary"}
    status, raw_sse = chat(base_url, "coding-primary", "Fix this bug", stream=True)
    check("failed stream surfaces error without [DONE]", status in (400, 500) and "[DONE]" not in raw_sse, f"status={status}, raw={raw_sse}")


def test_route_guards_and_limits(base_url: str):
    MockBackend.reset()

    huge_text = "x" * 50000
    status, resp = chat(base_url, "auto", huge_text)
    check("over-limit input is rejected before mock", status in (400, 500), f"status={status}, resp={resp}")

    status, resp = chat(base_url, "auto", "hello", extra_payload={"max_tokens": 5000})
    check("over-limit max_tokens is rejected before mock", status in (400, 500), f"status={status}, resp={resp}")

    img_msg = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "http://example.com/img.png"}}]}]
    status, resp = chat(base_url, "auto", img_msg)
    check("image content is rejected before mock", status in (400, 500), f"status={status}, resp={resp}")

    status, resp = chat(base_url, "auto", "hello", extra_payload={"tools": [{"type": "function", "function": {"name": "test"}}]})
    check("tools payload is rejected before mock", status in (400, 500), f"status={status}, resp={resp}")

    check("route guard rejections do not reach mock backend", len(MockBackend.call_log) == 0, f"calls={len(MockBackend.call_log)}")

    status, resp = chat(base_url, "coding-primary", "hello", extra_payload={"max_tokens": 5000})
    check("direct endpoint allows larger max_tokens", status == 200, f"status={status}, resp={resp}")
    check("direct endpoint reaches mock backend", len(MockBackend.call_log) == 1, f"calls={len(MockBackend.call_log)}")


def test_missing_key_pruning(tmp_dir: Path, mock_port: int):
    env = {
        "ANTHROPIC_MODELS": "claude-sonnet-5-5",
        "DEEPSEEK_BASE_URL": f"http://127.0.0.1:{mock_port}",
        "DEEPSEEK_FAST_MODEL": "coding-primary",
        "DEEPSEEK_PRO_MODEL": "coding-backup",
    }
    litellm_doc = configure.compile_litellm(env, providers={"anthropic", "deepseek"})

    names = {e["model_name"] for e in litellm_doc["model_list"]}
    check("pruned config includes coding alias when provider candidate exists", "coding" in names, f"names={names}")
    check("pruned config excludes research alias when no provider candidate exists", "research" not in names, f"names={names}")

    pruned_port = free_port()
    litellm_doc["general_settings"] = {"master_key": "sk-test-master"}
    for entry in litellm_doc["model_list"]:
        if "litellm_params" in entry:
            entry["litellm_params"]["api_base"] = f"http://127.0.0.1:{mock_port}"
            entry["litellm_params"]["api_key"] = "sk-mock"

    config_text = yaml.safe_dump(litellm_doc)
    proc = start_proxy(config_text, pruned_port, tmp_dir)
    try:
        base_url = f"http://127.0.0.1:{pruned_port}"
        req = urllib.request.Request(f"{base_url}/v1/models", headers={"Authorization": "Bearer sk-test-master"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            catalog = json.loads(resp.read().decode())
            model_ids = {m["id"] for m in catalog.get("data", [])}
            check("pruned catalog does not advertise unavailable research alias", "research" not in model_ids, f"catalog={model_ids}")
            check("pruned catalog advertises available coding alias", "coding" in model_ids, f"catalog={model_ids}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> None:
    mock_port = free_port()
    proxy_port = free_port()

    start_mock_backend(mock_port)

    config_text = CONFIG_TEMPLATE.format(mock_port=mock_port)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        proc = start_proxy(config_text, proxy_port, tmp_dir)
        base_url = f"http://127.0.0.1:{proxy_port}"
        try:
            test_gateway_auth(base_url)
            test_classification_and_precedence(base_url)
            test_fallback_and_exhaustion(base_url)
            test_streaming(base_url)
            test_route_guards_and_limits(base_url)
            test_missing_key_pruning(tmp_dir, mock_port)

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed: {FAILURES}", file=sys.stderr)
        sys.exit(1)
    print("\nall integration checks passed")


if __name__ == "__main__":
    main()
