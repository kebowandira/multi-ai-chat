# Deployment Tooling Correctness & Validation Report

- **Assignment Date**: 16 October 2026 (WIB)
- **Base Commit SHA**: `7d8f2c44bf549e2e193a7b3b8bddd9d6c4e8ab09`
- **Tested Implementation SHA**: `cb5d5cf4d68ccfd1d65b01fdf1f361cebed6d587` (branch `jules/deploy-c1-20261016`)
- **Environment**: Python 3.12.13, Docker Compose 2.30.1

### Changed File SHA256 Manifest
- `scripts/deploy.sh`: `367d7499d162c99d4bd26e541d5beee79e1215eadfcce1b916d87f18d897909e`
- `scripts/preflight.py`: `91d261a1195fe09220d5a2b3ebd806e89a3afc8006ec770c37395117bb1abbbd`
- `scripts/pin-images.py`: `02aabcb03c0211ab0c6598e7e4e7db89b0328df212324471d0fb39fdf8338df2`
- `tests/test_deploy.py`: `57c5de0f7f659d1127766f9474a3cfd2f428891cf12de715cd5791afdb1b9dc8`
- `tests/test_preflight.py`: `404d442995e569ba3bf810a411fd8d38e5dbc1c952dc14c01ceb52ad1add9cb0`
- `tests/test_pin_images.py`: `05bd4fbf861f8c4706c5e399384f623994d9c10dba9bfec6d4bb32e34484db48`

---

## Baseline vs. Final Test Summary

| Check | Baseline Result | Final Result | Notes |
|---|---|---|---|
| `scripts/check_source.py` | PASS (34 files) | PASS (48 files) | Allowlist source publication guard |
| `unittest discover -s tests -v` | PASS (30/30 passed) | PASS (52/52 passed) | Unit & deployment test suites |
| `bash -n scripts/deploy.sh` | PASS | PASS | Shell syntax validation |
| `compileall scripts router tests` | PASS | PASS | Python bytecode compilation |
| `git diff --check` | PASS | PASS | Whitespace & diff safety |

---

## Verbatim Execution Outputs

### 1. Source Publication Allowlist Guard
```
$ .venv/bin/python scripts/check_source.py
ok: 48 allowlisted files, no forbidden paths, no credential patterns matched
```

### 2. Unit & Deployment Test Discovery Output
```
$ .venv/bin/python -m unittest discover -s tests -v
test_api_keys_substituted (test_config.CompileLibrechatTests.test_api_keys_substituted) ... ok
test_no_providers_leaves_only_smartrouter_when_router_enabled (test_config.CompileLibrechatTests.test_no_providers_leaves_only_smartrouter_when_router_enabled) ... ok
test_only_deepseek_kept (test_config.CompileLibrechatTests.test_only_deepseek_kept) ... ok
test_smartrouter_requires_router_enabled (test_config.CompileLibrechatTests.test_smartrouter_requires_router_enabled) ... ok
test_coding_alias_and_fallback_built (test_config.CompileLitellmTests.test_coding_alias_and_fallback_built) ... ok
test_no_providers_yields_no_aliases (test_config.CompileLitellmTests.test_no_providers_yields_no_aliases) ... ok
test_prunes_unavailable_models (test_config.CompileLitellmTests.test_prunes_unavailable_models) ... ok
test_single_candidate_route_has_no_fallback_entry (test_config.CompileLitellmTests.test_single_candidate_route_has_no_fallback_entry) ... ok
test_missing_var_becomes_empty_string (test_config.SubstituteTests.test_missing_var_becomes_empty_string) ... ok
test_substitutes_nested_structures (test_config.SubstituteTests.test_substitutes_nested_structures) ... ok
test_bad_compose_config_fails (test_deploy.DeployScriptTests.test_bad_compose_config_fails) ... ok
test_empty_expected_services_fails (test_deploy.DeployScriptTests.test_empty_expected_services_fails) ... ok
test_missing_env_fails (test_deploy.DeployScriptTests.test_missing_env_fails) ... ok
test_missing_service_causes_deploy_failure (test_deploy.DeployScriptTests.test_missing_service_causes_deploy_failure) ... ok
test_profile_combination_standalone_and_router (test_deploy.DeployScriptTests.test_profile_combination_standalone_and_router) ... ok
test_pull_failure_causes_deploy_failure (test_deploy.DeployScriptTests.test_pull_failure_causes_deploy_failure) ... ok
test_standalone_profile_disabled_skips_caddy_validation (test_deploy.DeployScriptTests.test_standalone_profile_disabled_skips_caddy_validation) ... ok
test_successful_deployment (test_deploy.DeployScriptTests.test_successful_deployment) ... ok
test_unhealthy_service_causes_deploy_failure (test_deploy.DeployScriptTests.test_unhealthy_service_causes_deploy_failure) ... ok
test_atomic_file_preservation_on_failure (test_pin_images.PinImagesTests.test_atomic_file_preservation_on_failure) ... ok
test_load_compose_services_config_failure_dies (test_pin_images.PinImagesTests.test_load_compose_services_config_failure_dies) ... error: docker compose config failed:
Compose config error
ok
test_match_repo_digest_registry_with_port (test_pin_images.PinImagesTests.test_match_repo_digest_registry_with_port) ... ok
test_match_repo_digest_simple (test_pin_images.PinImagesTests.test_match_repo_digest_simple) ... ok
test_match_repo_digest_unrelated_repo_fails (test_pin_images.PinImagesTests.test_match_repo_digest_unrelated_repo_fails) ... error: no matching RepoDigest found for trusted.example/team/app:v1 in ['other.example/evil@sha256:abc']
ok
test_anchor_is_first_user_message (test_policy.AnchorTests.test_anchor_is_first_user_message) ... ok
test_no_user_message_returns_none (test_policy.AnchorTests.test_no_user_message_returns_none) ... ok
test_cheap_default (test_policy.ClassifyTextTests.test_cheap_default) ... ok
test_coding_keyword (test_policy.ClassifyTextTests.test_coding_keyword) ... ok
test_coding_precedes_research_when_both_could_match (test_policy.ClassifyTextTests.test_coding_precedes_research_when_both_could_match) ... ok
test_research_keyword_indonesian (test_policy.ClassifyTextTests.test_research_keyword_indonesian) ... ok
test_unmatched_falls_back_to_default_route (test_policy.ClassifyTextTests.test_unmatched_falls_back_to_default_route) ... ok
test_over_limit_raises (test_policy.LimitsTests.test_over_limit_raises) ... ok
test_under_limit_ok (test_policy.LimitsTests.test_under_limit_ok) ... ok
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
test_check_compose_version_cmd_error_fails (test_preflight.PreflightTests.test_check_compose_version_cmd_error_fails) ... FAIL: docker compose command failed: plugin missing
ok
test_check_compose_version_too_old_fails (test_preflight.PreflightTests.test_check_compose_version_too_old_fails) ... FAIL: docker compose v2.29.0 is older than required 2.30.0 (env_file format: raw)
ok
test_check_compose_version_valid (test_preflight.PreflightTests.test_check_compose_version_valid) ... ok
test_check_docker_daemon_unreachable_fails (test_preflight.PreflightTests.test_check_docker_daemon_unreachable_fails) ... FAIL: docker daemon is not running or unreachable: Is the docker daemon running?
ok
test_check_env_missing_secret_fails (test_preflight.PreflightTests.test_check_env_missing_secret_fails) ... FAIL: .env variable JWT_SECRET is missing or blank; run: python3 scripts/init-env.py
ok
test_check_env_router_missing_master_key_fails (test_preflight.PreflightTests.test_check_env_router_missing_master_key_fails) ... FAIL: .env variable LITELLM_MASTER_KEY is missing or blank; run: python3 scripts/init-env.py
ok
test_check_tool_missing_optional_warns (test_preflight.PreflightTests.test_check_tool_missing_optional_warns) ... ok
test_check_tool_missing_required_raises (test_preflight.PreflightTests.test_check_tool_missing_required_raises) ... FAIL: 'docker' not found on PATH
ok

----------------------------------------------------------------------
Ran 52 tests in 5.364s

OK
```

---

## Reproduced Defects & Behavioral Corrections

### Defect 1: Deployment Script Swallowed Pull Errors and Ignored Exited/Missing Services
- **Severity**: High (Deployment Safety)
- **Affected Path**: `scripts/deploy.sh`
- **Reproduction**:
  1. Image pull errors during `docker compose pull --quiet` were suppressed by `|| true`, proceeding to start containers even on pull failure.
  2. `docker compose up -d` without `--force-recreate` did not reliably apply updated environment variables or mounted files.
  3. `docker compose ps` checked only healthy flags on active containers, ignoring missing or exited containers. Empty service outputs were treated as success.
  4. `preflight.py` and `docker compose config -q` were not executed prior to starting containers.
- **Fix Rationale**:
  - Added `python3 scripts/preflight.py` and `docker compose config -q` at the top of `deploy.sh`.
  - Removed `|| true` from `docker compose pull --quiet` so pull errors halt deployment immediately.
  - Added `--force-recreate` to `docker compose up -d`.
  - Parsed expected active services via `docker compose config --services`. If empty, halts immediately with error. Verified every expected service has state `running` and health status `healthy` (or no health check). Any missing, exited, or unhealthy service causes a non-zero exit with explicit diagnostics.

### Defect 2: Preflight Allowed Missing Required Tools, Outdated Compose Versions, and Unreachable Daemon
- **Severity**: Medium (Preflight Integrity)
- **Affected Path**: `scripts/preflight.py`
- **Reproduction**:
  1. Missing required tools (`docker`, `git`) or Compose errors printed warnings instead of hard failures.
  2. Compose versions < 2.30.0 or unparseable version strings did not trigger hard exits.
  3. Missing required env secrets for enabled profiles (e.g. `LITELLM_MASTER_KEY` when router enabled) were not validated.
  4. Web port warnings (80/443) were printed even in shared-proxy mode where standalone Caddy is not bound.
- **Fix Rationale**:
  - Enforced `fail(...)` hard exits on missing required tools, daemon connectivity failures (`docker info`), Compose plugin failures, Compose versions < 2.30.0, or blank required secrets.
  - Restricted web port checks strictly to when `standalone` profile is active.
  - Respected `COMPOSE_PROFILES` from environment variables as well as `.env`.

### Defect 3: Image Pinning Parsed Raw Variables, Allowed Unrelated Repo Digests, and Overwrote Lock Files
- **Severity**: Medium (Image Pinning Reliability)
- **Affected Path**: `scripts/pin-images.py`
- **Reproduction**:
  1. `pin-images.py` parsed raw YAML strings like `${RAG_IMAGE:-...}` instead of resolving active Compose configuration inputs.
  2. `load_compose_services()` fell back to handwritten YAML parsing on Compose errors instead of stopping.
  3. `match_repo_digest('trusted.example/team/app:v1', ['other.example/evil@sha256:abc'])` returned an unrelated digest instead of failing.
  4. Failures during image pull/inspect partially wrote output files.
- **Fix Rationale**:
  - Resolved active image tags via `docker compose -f docker-compose.yml config --format json` (ignoring existing override files). Removed handwritten fallback so Compose errors fail immediately.
  - Strict repository matching: normalized registry host/port tags (`registry:5000/repo:tag`) and canonical docker names. Unmatched repositories trigger `die(...)` instead of returning `digests[0]`.
  - Added atomic temporary file writing (`.tmp` -> atomic rename) so failures preserve existing override/lock files intact.

---

## Scenario Coverage Matrix

| Required Scenario | Status | Verification & Evidence |
|---|---|---|
| **Successful Deployment** | COVERED | `test_deploy.py::test_successful_deployment`: Verified preflight, config check, pull, `--force-recreate`, and health waiting succeed when all expected services are running and healthy. |
| **Missing .env** | COVERED | `test_deploy.py::test_missing_env_fails`: Verified `deploy.sh` halts immediately if `.env` is absent. |
| **Bad Compose Config** | COVERED | `test_deploy.py::test_bad_compose_config_fails`: Verified `docker compose config -q` failure stops deployment. |
| **Pull Failure** | COVERED | `test_deploy.py::test_pull_failure_causes_deploy_failure`: Verified `docker compose pull` failure causes immediate non-zero exit without deploying stale images. |
| **Empty Expected Services** | COVERED | `test_deploy.py::test_empty_expected_services_fails`: Verified empty `config --services` output triggers immediate non-zero exit. |
| **Missing / Exited Service** | COVERED | `test_deploy.py::test_missing_service_causes_deploy_failure`: Verified missing expected containers cause deployment failure with explicit diagnostics. |
| **Unhealthy Service** | COVERED | `test_deploy.py::test_unhealthy_service_causes_deploy_failure`: Verified unhealthy container states trigger health timeout failure. |
| **Standalone Caddy Profile** | COVERED | `test_deploy.py`: Verified `caddy validate` is run when `standalone` profile is active and skipped when inactive. |
| **Preflight Hard Failures** | COVERED | `test_preflight.py`: Verified hard failures on missing tools, outdated Compose (<2.30.0), unreachable daemon, and missing required env secrets. |
| **Strict Repo Matching & Atomic Pinning** | COVERED | `test_pin_images.py`: Verified strict repository matching (rejects unrelated digests), registry port parsing, Compose error halting, and atomic file preservation on failure. |

---

## Testing Method & Explicit Boundaries

- **Fake-Docker Test Harness**: All deployment and preflight tests were conducted using isolated temporary project copies and a synthetic `docker` executable placed early in `PATH` in `tests/test_deploy.py`.
- **Validation Scope**: Fake-Docker unit tests verify script control flow, argument passing, status checks, and failure exit paths without needing production host access or live registry/daemon operations. This test suite does NOT claim or constitute a full-stack live host deployment.
