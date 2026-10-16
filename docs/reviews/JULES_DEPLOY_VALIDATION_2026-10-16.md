# Deployment Tooling Correctness & Validation Report

- **Assignment Date**: 16 October 2026 (WIB)
- **Base Commit SHA**: `cb5d5cf4d68ccfd1d65b01fdf1f361cebed6d587` (branch: `jules/deploy-c1-20261016`)
- **Environment**: Python 3.12.13, Docker Compose 2.30.1

### Changed File SHA256 Manifest
- `scripts/deploy.sh`: `89b0a1f215876b864637d4cbc12c42af0abf25597441f70b022b2bc8d3cbbeb0`
- `scripts/preflight.py`: `2b82759238873661d0d655ad68ef4a383d550748606e624d44f0e3fb2f811c97`
- `scripts/pin-images.py`: `19c6cb51a03cf49cc4e256f9bfb00d0daf18ddd807cfcc99ca2bfc6771659632`
- `tests/test_deploy.py`: `f34aaeffa973bcb73e6d115f6e0634533523c5aba27dada514a9c741fdac6546`
- `tests/test_preflight.py`: `fcfa0a7fce1cb7d91dae864f4a7f67e5335369847edd225a9524337111795cc6`
- `tests/test_pin_images.py`: `1b89a9f9659b87f806aeb2b443dee0807ec1cf94a385b28937b1af08a9576040`

---

## Baseline vs. Final Test Summary

| Check | Baseline Result | Final Result | Notes |
|---|---|---|---|
| `scripts/check_source.py` | PASS (48 files) | PASS (50 files) | Allowlist source publication guard |
| `unittest discover -s tests -v` | PASS (51/51 passed) | PASS (62/62 passed) | Unit & deployment test suites |
| `bash -n scripts/deploy.sh` | PASS | PASS | Shell syntax validation |
| `compileall scripts router tests` | PASS | PASS | Python bytecode compilation |
| `git diff --check` | PASS | PASS | Whitespace & diff safety |

---

## Reproduced Defects & Behavioral Corrections

### Defect 1: Profile Detection and Container State/Health Validation in Deploy Script
- **Severity**: High (Deployment Safety)
- **Affected Path**: `scripts/deploy.sh`
- **Reproduction**:
  1. `deploy.sh` previously relied on `grep` against `.env` to determine active profiles, ignoring shell environment variable overrides or Compose effective settings.
  2. Missing, exited, restarting, or starting containers could produce incomplete readiness reports or be missed if `docker compose ps` failed or returned empty output.
- **Fix Rationale**:
  - Replaced `.env` grep with `docker compose config --services` to evaluate effective active services and profile status (e.g. bundled Caddy when `caddy` service is present).
  - Explicit error handling for empty service lists and `docker compose ps` command errors.
  - Checked each expected active service for exact `running` state and `healthy` status (or running with no healthcheck). Exited, missing, restarting, or starting states fail deployment cleanly with actionable diagnostics.

### Defect 2: Preflight Secret Checks, Environment Overrides, and Port Conflict Distinction
- **Severity**: Medium (Preflight Integrity)
- **Affected Path**: `scripts/preflight.py`
- **Reproduction**:
  1. Preflight did not check all required secrets across enabled default/profile services (`MONGO_APP_PASSWORD`, `POSTGRES_PASSWORD`).
  2. Environment variable overrides for `COMPOSE_PROFILES` in shell were not prioritized over `.env`.
  3. Port probes failed to distinguish between existing same-project containers and external listener conflicts, and warned about web ports 80/443 even in shared-host mode.
- **Fix Rationale**:
  - Enforced secret validation for `JWT_SECRET`, `MEILI_MASTER_KEY`, `MONGO_ROOT_PASSWORD`, `MONGO_APP_PASSWORD`, `POSTGRES_PASSWORD`, and `LITELLM_MASTER_KEY` (when router profile enabled).
  - Evaluated `os.environ["COMPOSE_PROFILES"]` over `.env`.
  - Added `is_project_container_running()` helper to distinguish port bindings owned by existing project containers vs external conflicts. Skipped 80/443 probes when standalone profile is disabled (shared-host mode).

### Defect 3: Image Pinning Profile Resolution, Digest Match Validation, and Transactional Rollback
- **Severity**: Medium (Image Pinning Reliability)
- **Affected Path**: `scripts/pin-images.py`
- **Reproduction**:
  1. `pin-images.py` previously evaluated `docker compose config` without `--profile "*"` causing optional services (`caddy`, `litellm`) to be omitted when their profiles were inactive.
  2. Malformed digests or unmatched repositories could lead to invalid lock entries.
  3. Failures during writing or file replacing could leave `docker-compose.override.yml` and `image-lock.json` out of sync.
- **Fix Rationale**:
  - Executed `docker compose config --profile "*"` so all profiled services (`caddy`, `litellm`) are resolved and pinned.
  - Added strict digest format validation (`valid_digests = [d for d in digests if d and "@" in d]`).
  - Implemented transactional pair-writing with `.bak` backups and rollback cleanup on failure so override and lock files are updated atomically together or preserved intact.

---

## Scenario Coverage Matrix

| Required Scenario | Status | Verification & Evidence |
|---|---|---|
| **Successful Deployment (4 Profiles)** | COVERED | `test_deploy.py`: Verified deployment success across standalone, shared-host, router, and standalone+router profile combinations. |
| **Missing .env** | COVERED | `test_deploy.py::test_missing_env_fails`: Verified `deploy.sh` halts immediately if `.env` is absent. |
| **Bad Compose Config** | COVERED | `test_deploy.py::test_bad_compose_config_fails`: Verified `docker compose config -q` failure stops deployment. |
| **Pull Failure** | COVERED | `test_deploy.py::test_pull_failure_causes_deploy_failure`: Verified `docker compose pull` failure causes immediate non-zero exit without deploying stale images. |
| **Empty Expected Services** | COVERED | `test_deploy.py::test_empty_expected_services_fails`: Verified empty `config --services` output triggers immediate non-zero exit. |
| **Compose PS Error** | COVERED | `test_deploy.py::test_ps_failure_causes_deploy_failure`: Verified `docker compose ps` command errors fail deployment. |
| **Missing / Exited / Restarting / Starting Service** | COVERED | `test_deploy.py`: Verified missing, exited, restarting, or starting container states trigger explicit failure diagnostics. |
| **No-Healthcheck Running Service** | COVERED | `test_deploy.py::test_no_healthcheck_running_service_succeeds`: Verified services with state `running` and no healthcheck are accepted as ready. |
| **Preflight Secret & Shell Profile Overrides** | COVERED | `test_preflight.py`: Verified hard failures on missing required secrets and shell `COMPOSE_PROFILES` override handling. |
| **Preflight Port Distinction** | COVERED | `test_preflight.py::test_check_ports_same_project_vs_conflict`: Verified same-project container distinction and web port probe skipping in shared-host mode. |
| **Image Pinning Profiles & Transactional Rollback** | COVERED | `test_pin_images.py`: Verified `--profile "*"` inclusion, digest format validation, and atomic backup/rollback preservation on failure. |

---

## Testing Method & Explicit Boundaries

- **Fake-Docker Test Harness**: All deployment, preflight, and image pinning tests were conducted using simulated Docker fixtures and isolated temporary project copies in `tests/`.
- **Validation Scope**: Simulated Docker unit tests verify script control flow, argument passing, status checks, profile modes, and failure exit paths without requiring production host access or live registry/daemon operations. This test suite does NOT claim or constitute a full-stack live host deployment.
