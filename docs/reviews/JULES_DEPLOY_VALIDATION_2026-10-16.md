# Deployment Tooling Correctness & Validation Report

- **Assignment Date**: 16 October 2026 (WIB)
- **Branch**: `deployfix`
- **Reviewed Revision SHA**: `90d1712feeeebf338a631da5bfad18834757d49f`
- **Baseline Snapshot SHA**: `5c0e552d873bef4597ddafaa61d00690345163dc`
- **Environment**: Python 3.12.13, Simulated Docker Harness

### Changed File SHA256 Manifest
- `scripts/deploy.sh`: `d6ad80c459d2b9675a6b7398b730415ea27749778230bec637d145685a655436`
- `scripts/preflight.py`: `e3c580d59759ed1784bcde7d00e93ba033d10cdcb8bdc9315f4cdd30681e7a49`
- `scripts/pin-images.py`: `cfaaf4e179d20fee9afb8daf75e36106e073b0bc226cc427e3daa724d80347ff`
- `tests/test_deploy.py`: `5afaa5f2fbd30a1a2d34fb02a600b00f600d2c48f81dbb87ad9c7a5cca67e5c1`
- `tests/test_preflight.py`: `bc4a57607dc6befb7769c4b24e13961d14352a4b9626fca52bdf051a80ebc50b`
- `tests/test_pin_images.py`: `18914ad6091b2373b6dc9a388bcefb4fcf9fbeb7a7db1f6a7933f1bdf9fca299`

---

## Baseline vs. Final Test Summary

| Check | Baseline Result | Final Result | Notes |
|---|---|---|---|
| `scripts/check_source.py` | PASS (48 files) | PASS (57 files) | Allowlist source publication guard |
| `unittest discover -s tests -v` | FAIL (12 failures, 2 errors / PyYAML missing) | PASS (81/81 passed) | Full test suite across preflight, deploy, pin-images & policy |
| `bash -n scripts/deploy.sh` | PASS | PASS | Shell syntax validation |
| `compileall scripts router tests` | PASS | PASS | Python bytecode compilation |
| `git diff --check` | PASS | PASS | Whitespace & diff safety |

---

## Literal Test Execution Output

```
Ran 81 tests in 8.033s

OK
```

---

## Summary of Corrections Implemented (Including Follow-up Findings F1–F3)

### 1. `scripts/pin-images.py` & `tests/test_pin_images.py`
- **F1 (Strict SHA256 Regex & Pre-Subprocess Validation)**: Updated `DIGEST_REGEX` to enforce exact 64-character SHA256 hex strings (`^sha256:[0-9a-fA-F]{64}$`) with `fullmatch` to reject bogus algorithms or invalid hex lengths. In `resolve_digest`, malformed input images (e.g. `mongo@sha256:invalid`) are validated and rejected BEFORE `subprocess.run` calls, verified via `test_resolve_digest_malformed_input_fails_before_subprocess`.
- **F2 (Injected Rollback Failure Verification)**: Refactored `_run_pin_main_with_injected_error` in `tests/test_pin_images.py` to use `autospec=True` on `Path.write_text` and `Path.replace`. Explicitly asserted that injected callbacks fire, that `stderr` reports the exact injected `OSError` string (and not an unrelated `TypeError`), and that for second-rename failures, the first rename replacement actually succeeded before the second rename raised `OSError`.
- **F3 (Symmetric Repository Canonicalization)**: Updated `canonical_repo_variants` in `scripts/pin-images.py` so repository normalization is completely symmetric. Qualified inputs like `docker.io/library/mongo:7` match short RepoDigests (`mongo@sha256:...`), and short inputs like `mongo:latest` match qualified RepoDigests (`docker.io/library/mongo@sha256:...`). Symmetric matching also covers user/repo images (`docker.io/litellm/litellm:v1` and `litellm/litellm:latest`), while preserving strict rejection of unrelated registries and host:port repositories.

### 2. `scripts/preflight.py`
- **Mandatory Secrets Audit**: Updated `check_env()` to enforce required secrets for base services (`JWT_SECRET`, `JWT_REFRESH_SECRET`, `CREDS_KEY`, `CREDS_IV`, `MEILI_MASTER_KEY`, `MONGO_ROOT_PASSWORD`, `MONGO_APP_PASSWORD`, `POSTGRES_PASSWORD`) and router profile (`LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`).
- **Cryptographic Key Constraints**: Added strict hex format and length checks for `CREDS_KEY` (64-character hex / 32 bytes) and `CREDS_IV` (32-character hex / 16 bytes) without logging secret values.
- **Shell Profile Precedence**: Ensured `COMPOSE_PROFILES` from `os.environ` overrides `.env` consistently across `check_env()` and `check_ports()`.
- **Port Conflict Distinction**: Updated port checks to distinguish existing same-project containers from external listener conflicts and skip web port (80/443) checks when `standalone` profile is inactive.

### 3. `scripts/deploy.sh`
- **Pre-Mutation Service Resolution**: Resolved active Compose services (`expected_services=$(docker compose config --services)`) before running Caddy validation, pulling images, or starting containers. Errors are no longer suppressed with `|| true`.
- **Pre-Mutation Error Halt**: Halts deployment immediately if service discovery fails or yields no expected services, preventing accidental image pulls or container updates.
- **Multi-Replica Container Validation**: In the health wait loop, queries `docker compose ps` and evaluates state and health for every returned line/replica per service.
- **State & Health Enforcement**: Enforces `running` state and `healthy` status (or running with no healthcheck) across all four profile modes (`standalone`, shared-host, `router`, `standalone,router`). Missing, exited, restarting, starting, unhealthy, or empty `ps` outputs trigger explicit diagnostics.

---

## Scenario Matrix

| Required Scenario | Status | Verification & Evidence |
|---|---|---|
| **Successful Deployment (4 Profiles)** | COVERED | `test_deploy.py`: Verified standalone, shared-host, router, and standalone+router profile combinations. |
| **Discovery Failure Before Mutations** | COVERED | `test_deploy.py::test_config_services_discovery_failure_halts_before_mutations`: Verified discovery errors stop deploy before Caddy/pull/up. |
| **Empty Expected Services** | COVERED | `test_deploy.py::test_empty_expected_services_halts_before_mutations`: Verified empty service list stops deploy before mutations. |
| **Pull Failure** | COVERED | `test_deploy.py::test_pull_failure_causes_deploy_failure`: Verified pull failure halts deployment immediately. |
| **Empty PS / Missing / Exited / Restarting / Starting / Unhealthy** | COVERED | `test_deploy.py`: Verified empty ps, missing, exited, restarting, starting, and unhealthy container states fail deploy cleanly. |
| **Multi-Replica Container Checks** | COVERED | `test_deploy.py::test_multi_replica_fail` & `test_multi_replica_ok`: Verified multi-replica line evaluation. |
| **No-Healthcheck Running Service** | COVERED | `test_deploy.py::test_no_healthcheck_running_service_succeeds`: Verified running services without healthchecks succeed. |
| **Preflight Secret Audit & Constraints** | COVERED | `test_preflight.py`: Verified mandatory secrets, length/hex constraints, and shell profile precedence without leaking secret values. |
| **Pin Images Repos, Digests & Rollback** | COVERED | `test_pin_images.py`: Verified symmetric repository canonicalization, malformed digest rejection, requested digest mismatch checks, pre-subprocess malformed input checks, and write/rename failure injected rollbacks. |

---

## Testing Method & Explicit Limitations

- **Simulated / Mocked Docker Environment**: All unit tests in `tests/test_deploy.py`, `tests/test_preflight.py`, and `tests/test_pin_images.py` execute using synthetic test fixtures and mocked subprocess/Docker responses in Python.
- **No Production Host / Daemon Claim**: Passing tests verify script control flow, argument passing, output parsing, secret constraint checking, and error handling. They do NOT constitute full-stack live VPS execution, live container startup, or real registry pulls.
- **Dual-Rename Limitation**: Two separate POSIX file renames (`docker-compose.override.yml` and `image-lock.json`) in `scripts/pin-images.py` do not guarantee crash-atomic pair replacement if the process is killed via SIGKILL between renames.
