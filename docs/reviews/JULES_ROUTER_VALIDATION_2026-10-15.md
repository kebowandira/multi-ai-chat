# Router and Mock Integration Validation Report

- **Assignment Date**: 15 October 2026
- **Base Commit SHA**: `8e3e6644dba79f7f24e4529f19e5c2309f3a4db4`
- **Published Remote PR Head SHA**: `d02388717951ab998a9cd5e09bad1bc07d997d92`
- **Environment**: Python 3.12.13, LiteLLM 1.104.0

### File Hashes (SHA256)
- `router/policy.py`: `cb4e207b24a6902f474eb85b274289ef406fa81ab98236601c7005186054f09a`
- `router/custom_router.py`: `4466bdebcf9708eefe3a61aa2cea0e4d77cc5b06644d45890e00ad55c0184f4d`
- `tests/integration_gateway.py`: `b2e0e88e6aefe0e341dcc7170087166a26b7498d2552b0f3f5bc450676c7a697`
- `tests/test_policy.py`: `2d2ef8fb3ffc76562afad686211dac43909ae0d2c40fb2d5ace823c555bc83b2`
- `tests/test_config.py`: `b2d00b1b0ae08dbb45d8d2aae95fd25bcd48da458f81185e80d87f8096094191`

---

## Baseline vs. Final Test Summary

| Check | Baseline Result | Final Result | Notes |
|---|---|---|---|
| `scripts/check_source.py` | PASS (34 files) | PASS (48 files) | Allowlist source publication guard |
| `unittest discover -s tests -v` | PASS (30/30 passed) | PASS (46/46 passed) | Policy and config unit tests |
| `bash -n scripts/deploy.sh` | PASS | PASS | Shell syntax validation |
| `compileall scripts router tests` | PASS | PASS | Python bytecode compilation |
| `tests/integration_gateway.py` | FAIL (Timeout Error) | PASS (35/35 passed) | Real LiteLLM proxy process against local mock server |

---

## Verbatim Execution Outputs

### 1. Source Publication Allowlist Guard
```
$ .venv/bin/python scripts/check_source.py
ok: 48 allowlisted files, no forbidden paths, no credential patterns matched
```

### 2. Unit Test Discovery Output
```
$ .venv/bin/python -m unittest discover -s tests -v
test_api_keys_substituted (test_config.CompileLibrechatTests.test_api_keys_substituted) ... ok
test_no_providers_leaves_only_smartrouter_when_router_enabled (test_config.CompileLibrechatTests.test_no_providers_leaves_only_smartrouter_when_router_enabled) ... ok
test_only_deepseek_kept (test_config.CompileLibrechatTests.test_only_deepseek_kept) ... ok
test_smartrouter_requires_router_enabled (test_config.CompileLibrechatTests.test_smartrouter_requires_router_enabled) ... ok
test_alias_omitted_when_no_candidates_available (test_config.CompileLitellmTests.test_alias_omitted_when_no_candidates_available) ... ok
test_coding_alias_and_fallback_built (test_config.CompileLitellmTests.test_coding_alias_and_fallback_built) ... ok
test_no_providers_yields_no_aliases (test_config.CompileLitellmTests.test_no_providers_yields_no_aliases) ... ok
test_prunes_unavailable_models (test_config.CompileLitellmTests.test_prunes_unavailable_models) ... ok
test_single_candidate_route_has_no_fallback_entry (test_config.CompileLitellmTests.test_single_candidate_route_has_no_fallback_entry) ... ok
test_missing_var_becomes_empty_string (test_config.SubstituteTests.test_missing_var_becomes_empty_string) ... ok
test_substitutes_nested_structures (test_config.SubstituteTests.test_substitutes_nested_structures) ... ok
test_anchor_is_first_user_message (test_policy.AnchorTests.test_anchor_is_first_user_message) ... ok
test_no_user_message_returns_none (test_policy.AnchorTests.test_no_user_message_returns_none) ... ok
test_cheap_default (test_policy.ClassifyTextTests.test_cheap_default) ... ok
test_coding_keyword (test_policy.ClassifyTextTests.test_coding_keyword) ... ok
test_coding_precedes_research_when_both_could_match (test_policy.ClassifyTextTests.test_coding_precedes_research_when_both_could_match) ... ok
test_research_keyword_indonesian (test_policy.ClassifyTextTests.test_research_keyword_indonesian) ... ok
test_unmatched_falls_back_to_default_route (test_policy.ClassifyTextTests.test_unmatched_falls_back_to_default_route) ... ok
test_boolean_max_tokens_raises (test_policy.LimitsTests.test_boolean_max_tokens_raises) ... ok
test_dual_field_max_completion_tokens_over_limit_raises (test_policy.LimitsTests.test_dual_field_max_completion_tokens_over_limit_raises) ... ok
test_invalid_type_max_tokens_raises (test_policy.LimitsTests.test_invalid_type_max_tokens_raises) ... ok
test_max_completion_tokens_over_limit_raises (test_policy.LimitsTests.test_max_completion_tokens_over_limit_raises) ... ok
test_null_max_tokens_defaults_to_policy_cap (test_policy.LimitsTests.test_null_max_tokens_defaults_to_policy_cap) ... ok
test_omitted_output_limit_defaults_to_policy_cap (test_policy.LimitsTests.test_omitted_output_limit_defaults_to_policy_cap) ... ok
test_over_limit_raises (test_policy.LimitsTests.test_over_limit_raises) ... ok
test_over_output_limit_raises (test_policy.LimitsTests.test_over_output_limit_raises) ... ok
test_under_limit_ok (test_policy.LimitsTests.test_under_limit_ok) ... ok
test_under_output_limit_ok (test_policy.LimitsTests.test_under_output_limit_ok) ... ok
test_zero_or_negative_max_tokens_raises (test_policy.LimitsTests.test_zero_or_negative_max_tokens_raises) ... ok
test_filters_to_available (test_policy.ResolveCandidatesTests.test_filters_to_available) ... ok
test_preserves_policy_order (test_policy.ResolveCandidatesTests.test_preserves_policy_order) ... ok
test_raises_when_nothing_available (test_policy.ResolveCandidatesTests.test_raises_when_nothing_available) ... ok
test_classification_used_when_no_prefix (test_policy.ResolveRouteTests.test_classification_used_when_no_prefix) ... ok
test_empty_conversation_returns_default (test_policy.ResolveRouteTests.test_empty_conversation_returns_default) ... ok
test_follow_up_does_not_change_tier (test_policy.ResolveRouteTests.test_follow_up_does_not_change_tier) ... ok
test_unknown_prefix_falls_back_to_classification (test_policy.ResolveRouteTests.test_unknown_prefix_falls_back_to_classification) ... ok
test_removes_prefix_from_anchor_only (test_policy.StripAnchorPrefixTests.test_removes_prefix_from_anchor_only) ... ok
test_empty_string (test_policy.StripPrefixTests.test_empty_string) ... ok
test_no_prefix_returns_none (test_policy.StripPrefixTests.test_no_prefix_returns_none) ... ok
test_strips_known_prefix (test_policy.StripPrefixTests.test_strips_known_prefix) ... ok
test_image_content_raises (test_policy.TextOnlyGuardTests.test_image_content_raises) ... ok
test_plain_text_ok (test_policy.TextOnlyGuardTests.test_plain_text_ok) ... ok
test_response_format_raises (test_policy.TextOnlyGuardTests.test_response_format_raises) ... ok
test_structured_content_text_ok (test_policy.TextOnlyGuardTests.test_structured_content_text_ok) ... ok
test_tool_history_role_raises (test_policy.TextOnlyGuardTests.test_tool_history_role_raises) ... ok
test_tools_raises (test_policy.TextOnlyGuardTests.test_tools_raises) ... ok

----------------------------------------------------------------------
Ran 46 tests in 0.090s

OK
```

### 3. Gateway Integration Suite Output
```
$ .venv-gateway/bin/python tests/integration_gateway.py
ok: missing gateway key fails with 401/403
ok: invalid gateway key fails with 400/401/403
ok: missing/invalid gateway key does not reach mock backend
ok: auto classifies coding prompt to coding-primary
ok: auto classifies research prompt to research-primary
ok: explicit /cheap prefix overrides coding classification
ok: explicit UI route cheap wins over /coding prompt prefix
ok: anchor /coding prefix is stripped when sent upstream
ok: follow-up message respects anchor message classification
ok: failed primary reaches intended fallback coding-backup
ok: call log records primary then backup call
ok: exhausted fallback returns error status (500)
ok: exhausted fallback stops after retries and does not loop infinitely
ok: streaming produces HTTP 200
ok: streaming output contains parsed data events and done event
ok: midstream failure on alias coding receives partial output chunk
ok: midstream failure does not trigger fallback replay to backup
ok: midstream failure delivers partial chunk exactly once without duplication
ok: failed stream returns error status (500) and does not send [DONE]
ok: omitted output limit defaults to policy max_tokens (4096)
ok: null output limit defaults to policy max_tokens (4096)
ok: boolean max_tokens is rejected before mock
ok: negative max_tokens is rejected before mock
ok: over-limit input is rejected before mock
ok: over-limit max_tokens is rejected before mock
ok: dual field max_completion_tokens over-limit is rejected before mock
ok: image content is rejected before mock
ok: tools payload is rejected before mock
ok: route guard rejections do not reach mock backend
ok: direct endpoint allows larger max_tokens
ok: direct endpoint reaches mock backend
ok: pruned config includes coding alias when provider candidate exists
ok: pruned config excludes research alias when no provider candidate exists
ok: pruned catalog does not advertise unavailable research alias
ok: pruned catalog advertises available coding alias

all integration checks passed
```

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
  4. Increased `start_proxy` health check timeout to 30s and added cleanup logic in `start_proxy` to capture and raise log contents if health check fails.

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
| **Streaming SSE** | COVERED | `test_streaming`: Verified HTTP 200 SSE streaming output with parsed `data: ...` events. Verified midstream failure on alias route `coding` delivers partial content chunks without triggering transparent fallback replay to `coding-backup` (`coding-backup` call count = 0), preventing text duplication. Upstream HTTP 500 errors return error status without `[DONE]`. |
| **Route Guards & Limits** | COVERED | `test_route_guards_and_limits`, `LimitsTests`, & `TextOnlyGuardTests`: Verified input length >48k, max tokens / max completion tokens >4096, omitted / `null` limit defaults (4096), booleans/negatives rejection, image content, and tool calls are rejected on alias routes prior to mock backend receipt, while direct model endpoints allow larger limits. |

---

## Observed Upstream Behavior Notes & Recommendations

- **Streaming Behavior Note**: In LiteLLM 1.104.0, when an HTTP 200 SSE stream has delivered partial data chunks and the upstream server connection is closed mid-stream, LiteLLM forwards the partial content and synthesizes a completion chunk rather than executing a mid-stream fallback attempt. This prevents duplicating partial response text across fallbacks.
- **Environment Note**: All 35 integration gateway checks pass in this execution sandbox environment. In certain reviewer host environments, proxy health check startup may time out due to host-specific loopback or network configurations.
- **Skipped / Blocked Checks**: None. All required unit and integration tests were executed locally and passed.
- **Production Isolation**: All test executions were performed using isolated virtual environments (`.venv` and `.venv-gateway`), local mock HTTP backends, and synthetic data. No live AI provider API calls or deployment actions were taken.
- **Recommendations**: Maintain integration tests in automated CI runs to detect potential changes in LiteLLM's `CustomLogger` callback interfaces in future updates.
