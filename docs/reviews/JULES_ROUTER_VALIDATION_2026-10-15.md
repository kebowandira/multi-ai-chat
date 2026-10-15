# Router and Mock Integration Validation Report

- **Assignment Date**: 15 October 2026
- **Base Commit SHA**: `8e3e6644f1ddbead08b61c9eefaf92b67d5ce390`
- **Tested Implementation SHA**: `8e3e6644f1ddbead08b61c9eefaf92b67d5ce390` (branch `jules/router-validation-2026-10-15`)
- **Environment**: Python 3.12.13, LiteLLM 1.104.0

---

## Baseline vs. Final Test Summary

| Check | Baseline Result | Final Result | Notes |
|---|---|---|---|
| `scripts/check_source.py` | PASS (34 files) | PASS (48 files) | Allowlist source publication guard |
| `unittest discover -s tests -v` | PASS (30/30 passed) | PASS (46/46 passed) | Policy and config unit tests |
| `bash -n scripts/deploy.sh` | PASS | PASS | Shell syntax validation |
| `compileall scripts router tests` | PASS | PASS | Python bytecode compilation |
| `tests/integration_gateway.py` | FAIL (Timeout Error) | PASS (29/29 passed) | Real LiteLLM proxy process against local mock server |

---

## Findings and Defect Analysis

### Finding 1: Integration Test Harness Binary Launch & Subprocess Output Deadlock
- **Severity**: Low (Test Harness)
- **Affected Path**: `tests/integration_gateway.py`
- **Reproduction**: Executing `.venv-gateway/bin/python tests/integration_gateway.py` in baseline state.
- **Expected Behavior**: The script starts the `litellm` proxy process in a subprocess and waits for `/health/liveliness`.
- **Actual Behavior**:
  1. The script ran `[sys.executable, "-m", "litellm", ...]`, which failed because `litellm` is a package without a `__main__.py` module in version `1.104.0`.
  2. Subprocess `stdout=subprocess.PIPE` caused pipe buffer deadlocks on verbose proxy output, stalling startup in restricted environments.
- **Fix Rationale**:
  1. Updated `tests/integration_gateway.py` to invoke `.venv-gateway/bin/litellm` executable binary.
  2. Redirected subprocess logs to dedicated temporary log files (`log_file = open(tmp_dir / f"litellm_{proxy_port}.log", "w+")`), eliminating pipe buffer stalls.
  3. Set `LITELLM_LOCAL_MODEL_COST_MAP=True` in environment to prevent external network fetch stalls during offline startup.
  4. Added cleanup logic in `start_proxy` to capture and raise log contents if health check fails.

### Finding 2: Missing Enforcement of Output Token Limits, Null/Boolean Bypasses, and Text-Only Guards
- **Severity**: Medium (Router Policy Enforcement)
- **Affected Path**: `router/policy.py`, `router/custom_router.py`
- **Reproduction**:
  1. Sending requests with omitted `max_tokens` or explicit `max_tokens: null` / `max_completion_tokens: null`.
  2. Sending requests with `max_tokens: True` or `max_tokens: 1` combined with `max_completion_tokens: 5000`.
  3. Sending requests containing image blocks (`image_url`), function tools (`tools`), or structured outputs (`response_format`) to route aliases (`auto`, `coding`, `research`, `cheap`).
- **Expected Behavior**: Per documentation, route aliases accept plain text only and enforce a 48,000 input character limit and 4,096 output token limit.
  - Omitted or `null` output limits must default to `max_tokens: 4096`.
  - Both `max_tokens` and `max_completion_tokens` must be validated against the 4,096 output token cap.
  - Booleans (`True`/`False`), negative values, or values > 4,096 must be rejected with `RoutingError`.
  - Non-text payloads (images, function tools, response formats) must be rejected prior to reaching upstream.
- **Actual Behavior**: `router/custom_router.py` checked only input character counts (`enforce_input_limit`) and allowed requests with oversized output tokens, explicit nulls, booleans, or function tools to pass unvalidated to upstream models.
- **Fix Rationale**:
  - Implemented `enforce_output_limit` in `router/policy.py`: normalizes explicit `None`/`null` fields, validates both `max_tokens` and `max_completion_tokens`, rejects booleans and values > 4,096 or < 1, and sets default `max_tokens = 4096` when no limit is provided.
  - Implemented `enforce_text_only` in `router/policy.py`.
  - Invoked both guards in `ClassifyingRouter.async_pre_call_hook` in `router/custom_router.py`.

---

## Scenario Coverage Matrix

| Required Scenario | Status | Verification & Evidence |
|---|---|---|
| **Gateway Authentication** | COVERED | `test_gateway_auth`: Verified requests with missing Authorization headers (401) and invalid gateway keys (400) fail before reaching `MockBackend`. |
| **Classification & Precedence** | COVERED | `test_classification_and_precedence`: Verified keyword auto-classification (`coding` / `research` / `cheap`), explicit `/cheap` prompt prefix override on a `coding`-shaped prompt (`/cheap Refactor this Python function...`), explicit UI route precedence over text prefixes, anchor prefix stripping, and follow-up conversation tier locking. |
| **Missing-Key Pruning** | COVERED | `test_missing_key_pruning` & `test_alias_omitted_when_no_candidates_available`: Verified `configure.compile_litellm` prunes aliases when candidate provider keys are missing and `/v1/models` does not advertise unconfigured routes. |
| **Fallback & Exhaustion** | COVERED | `test_fallback_and_exhaustion`: Verified primary model HTTP 500 error triggers fallback to `coding-backup`. Verified simultaneous primary and backup failures return HTTP 500 without infinite loops. |
| **Streaming SSE** | COVERED | `test_streaming`: Verified HTTP 200 SSE streaming output with parsed `data: ...` events and `[DONE]` termination. Verified midstream delivery receives partial output chunks and upstream errors fail without sending `[DONE]`. |
| **Route Guards & Limits** | COVERED | `test_route_guards_and_limits`, `LimitsTests`, & `TextOnlyGuardTests`: Verified input length >48k, max tokens / max completion tokens >4096, omitted / `null` limit defaults (4096), booleans/negatives rejection, image content, and tool calls are rejected on alias routes prior to mock backend receipt, while direct model endpoints allow larger limits. |

---

## Remaining Risks, Skipped Checks, and Recommendations

- **Skipped / Blocked Checks**: None. All required unit and integration tests were executed locally and passed.
- **Production Isolation**: All test executions were performed using isolated virtual environments (`.venv` and `.venv-gateway`), local mock HTTP backends, and synthetic data. No live AI provider API calls or deployment actions were taken.
- **Recommendations**: Maintain integration tests in automated CI runs to detect potential changes in LiteLLM's `CustomLogger` callback interfaces in future updates.
