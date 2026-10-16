# Deployment Tooling Correctness & Validation Report

- **Assignment Date**: 16 October 2026 (WIB)
- **Branch**: `deployfix`
- **Snapshot SHA**: `5c0e552d873bef4597ddafaa61d00690345163dc`
- **Environment**: Python 3.12.13, Simulated Docker Harness

### Changed File SHA256 Manifest
- `scripts/deploy.sh`: `d6ad80c459d2b9675a6b7398b730415ea27749778230bec637d145685a655436`
- `scripts/preflight.py`: `e3c580d59759ed1784bcde7d00e93ba033d10cdcb8bdc9315f4cdd30681e7a49`
- `scripts/pin-images.py`: `2ebb5b9fc57a1d4e98ead6d3e60c930901585ddb839cdaa8f517af30eb817d71`
- `tests/test_deploy.py`: `5afaa5f2fbd30a1a2d34fb02a600b00f600d2c48f81dbb87ad9c7a5cca67e5c1`
- `tests/test_preflight.py`: `bc4a57607dc6befb7769c4b24e13961d14352a4b9626fca52bdf051a80ebc50b`
- `tests/test_pin_images.py`: `99a52ae6e59599dcbbf986af6ea93337bc966591670017bda344c3e0fc11d9e6`

---

## Baseline vs. Final Test Summary

| Check | Baseline Result | Final Result | Notes |
|---|---|---|---|
| `scripts/check_source.py` | PASS (48 files) | PASS (51 files) | Allowlist source publication guard |
| `unittest discover -s tests -v` | FAIL (12 failures, 2 errors / PyYAML missing) | PASS (80/80 passed) | Full test suite across preflight, deploy, pin-images & policy |
| `bash -n scripts/deploy.sh` | PASS | PASS | Shell syntax validation |
| `compileall scripts router tests` | PASS | PASS | Python bytecode compilation |
| `git diff --check` | PASS | PASS | Whitespace & diff safety |

---

## Literal Test Execution Output

```
Ran 80 tests in 8.602s

OK
```

---

## Summary of Corrections Implemented

### 1. `scripts/pin-images.py`
- **Canonical Repository Matching**: Updated `match_repo_digest` to construct exact canonical repository variants (`repo`, `library/repo`, `docker.io/library/repo`, `index.docker.io/library/repo`, `docker.io/user/repo`, `host:port/repo`). Shortnames no longer suffix-match unrelated registries (e.g. `evil.com/mongo` will not match `mongo`).
- **Digest Format Validation**: Added `DIGEST_REGEX` validation (`^[a-zA-Z0-9+_.-]+:[a-fA-F0-9]{32,}$`) to reject malformed RepoDigests or missing `@` delimiters.
- **Requested Digest Mismatch Enforced**: If the input image is already pinned to a digest, `resolve_digest` verifies that the resolved digest matches the input digest and exits with an error on mismatch.
- **Mocked Unit Tests & Failure Injections**: Rewrote `tests/test_pin_images.py` to use 100% mocked Docker calls (`load_compose_services` and `resolve_digest`), testing Docker Hub aliases, host:port repositories, unrelated registry prevention, malformed digests, digest mismatches, and injected write/rename failures for both preexisting and absent files.
- **Documented Dual-Rename Limitations**: Clearly documented in code comments and unit tests that two separate file renames (`docker-compose.override.yml` and `image-lock.json`) do not provide crash-atomic pair replacement across process SIGKILL or secondary filesystem errors.

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
| **Pin Images Repos, Digests & Rollback** | COVERED | `test_pin_images.py`: Verified repository canonicalization, malformed digest rejection, requested digest mismatch checks, and write/rename failure injected rollbacks. |

---

## Testing Method & Explicit Limitations

- **Simulated / Mocked Docker Environment**: All unit tests in `tests/test_deploy.py`, `tests/test_preflight.py`, and `tests/test_pin_images.py` execute using synthetic test fixtures and mocked subprocess/Docker responses in Python.
- **No Production Host / Daemon Claim**: Passing tests verify script control flow, argument passing, output parsing, secret constraint checking, and error handling. They do NOT constitute full-stack live VPS execution, live container startup, or real registry pulls.
- **Dual-Rename Limitation**: Two separate POSIX file renames (`docker-compose.override.yml` and `image-lock.json`) in `scripts/pin-images.py` do not guarantee crash-atomic pair replacement if the process is killed via SIGKILL between renames.
