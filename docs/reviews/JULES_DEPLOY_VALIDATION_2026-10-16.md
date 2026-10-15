# Deployment Tooling Correctness & Validation Report

- **Assignment Date**: 16 October 2026 (WIB)
- **Base Commit SHA**: `7d8f2c45163ed8a8dcba50a831e678ae99eb9bbf`
- **Tested Implementation SHA**: `c3f0d83cdf51e0ac0d40ac2baa89a75c55659c29` (branch `jules/deploy-validation-2026-10-16`)
- **Environment**: Python 3.12.13, Docker Compose 2.30.1

### Changed File SHA256 Manifest
- `scripts/deploy.sh`: `57d1f09cb24598a77a8acf664f30570b0fa5cd0ebd7565c7c30dfea5d101b9e7`
- `scripts/preflight.py`: `91d261a1195fe09220d5a2b3ebd806e89a3afc8006ec770c37395117bb1abbbd`
- `scripts/pin-images.py`: `f06e754ed218eecb65e021cb999ab9842ca20698d029214ef282521af581bda2`
- `tests/test_deploy.py`: `33d0dae59508ba31ef78da1fd7dce086c2aa12c04f6d6f274ca99325c7d0d395`
- `tests/test_preflight.py`: `404d442995e569ba3bf810a411fd8d38e5dbc1c952dc14c01ceb52ad1add9cb0`
- `tests/test_pin_images.py`: `b2c007fc215f963773128f981ed1639df8ffdd90530081f0e37518d784447c10`

---

## Baseline vs. Final Test Summary

| Check | Baseline Result | Final Result | Notes |
|---|---|---|---|
| `scripts/check_source.py` | PASS (34 files) | PASS (48 files) | Allowlist source publication guard |
| `unittest discover -s tests -v` | PASS (30/30 passed) | PASS (49/49 passed) | Unit & deployment test suites |
| `bash -n scripts/deploy.sh` | PASS | PASS | Shell syntax validation |
| `compileall scripts router tests` | PASS | PASS | Python bytecode compilation |
| `git diff --check` | PASS | PASS | Whitespace & diff safety |

---

## Reproduced Defects & Behavioral Corrections

### Defect 1: Deployment Script Swallowed Pull Errors and Ignored Exited/Missing Services
- **Severity**: High (Deployment Safety)
- **Affected Path**: `scripts/deploy.sh`
- **Reproduction**:
  1. Image pull errors during `docker compose pull --quiet` were suppressed by `|| true`, proceeding to start containers even on pull failure.
  2. `docker compose up -d` without `--force-recreate` did not reliably apply updated environment variables or mounted files.
  3. `docker compose ps` checked only healthy flags on active containers, ignoring missing or exited containers.
  4. `preflight.py` and `docker compose config -q` were not executed prior to starting containers.
- **Fix Rationale**:
  - Added `python3 scripts/preflight.py` and `docker compose config -q` at the top of `deploy.sh`.
  - Removed `|| true` from `docker compose pull --quiet` so pull errors halt deployment immediately.
  - Added `--force-recreate` to `docker compose up -d`.
  - Parsed expected active services via `docker compose config --services` and verified every expected service has state `running` and health status `healthy` (or no health check). Any missing, exited, or unhealthy service causes a non-zero exit with explicit diagnostics.

### Defect 2: Preflight Allowed Missing Required Tools, Outdated Compose Versions, and Unreachable Daemon
- **Severity**: Medium (Preflight Integrity)
- **Affected Path**: `scripts/preflight.py`
- **Reproduction**:
  1. Missing required tools (`docker`, `git`) or Compose errors printed warnings instead of hard failures.
  2. Compose versions < 2.30.0 or unparseable version strings did not trigger hard exits.
  3. Missing required env secrets for enabled profiles (e.g. `LITELLM_MASTER_KEY` when router enabled) were not validated.
- **Fix Rationale**:
  - Enforced `fail(...)` hard exits on missing required tools, daemon connectivity failures (`docker info`), Compose plugin failures, Compose versions < 2.30.0, or blank required secrets.

### Defect 3: Image Pinning Parsed Raw Variables and Overwrote Lock Files on Failure
- **Severity**: Medium (Image Pinning Reliability)
- **Affected Path**: `scripts/pin-images.py`
- **Reproduction**:
  1. `pin-images.py` parsed raw YAML strings like `${RAG_IMAGE:-...}` instead of resolving active Compose configuration inputs.
  2. Re-running `pin-images.py` read existing override pins from `docker-compose.override.yml`, masking source image updates in `.env`.
  3. Failures during image pull/inspect partially wrote output files.
- **Fix Rationale**:
  - Resolved active image tags via `docker compose -f docker-compose.yml config --format json` (ignoring existing override files).
  - Implemented safe repo digest matching for registry ports (`registry:5000/repo:tag`).
  - Added atomic temporary file writing (`.tmp` -> atomic rename) so failures preserve existing override/lock files intact.

---

## Scenario Coverage Matrix

| Required Scenario | Status | Verification & Evidence |
|---|---|---|
| **Successful Deployment** | COVERED | `test_deploy.py::test_successful_deployment`: Verified preflight, config check, pull, `--force-recreate`, and health waiting succeed when all expected services are running and healthy. |
| **Missing .env** | COVERED | `test_deploy.py::test_missing_env_fails`: Verified `deploy.sh` halts immediately if `.env` is absent. |
| **Bad Compose Config** | COVERED | `test_deploy.py::test_bad_compose_config_fails`: Verified `docker compose config -q` failure stops deployment. |
| **Pull Failure** | COVERED | `test_deploy.py::test_pull_failure_causes_deploy_failure`: Verified `docker compose pull` failure causes immediate non-zero exit without deploying stale images. |
| **Missing / Exited Service** | COVERED | `test_deploy.py::test_missing_service_causes_deploy_failure`: Verified missing expected containers cause deployment failure with explicit diagnostics. |
| **Unhealthy Service** | COVERED | `test_deploy.py::test_unhealthy_service_causes_deploy_failure`: Verified unhealthy container states trigger health timeout failure. |
| **Standalone Caddy Profile** | COVERED | `test_deploy.py`: Verified `caddy validate` is run when `standalone` profile is active and skipped when inactive. |
| **Preflight Hard Failures** | COVERED | `test_preflight.py`: Verified hard failures on missing tools, outdated Compose (<2.30.0), unreachable daemon, and missing required env secrets. |
| **Atomic Pinning & Registry Ports** | COVERED | `test_pin_images.py`: Verified interpolation, registry port matching, and atomic file preservation on pull failure. |

---

## Testing Method & Explicit Boundaries

- **Fake-Docker Test Harness**: All deployment and preflight tests were conducted using isolated temporary project copies and a synthetic `docker` executable placed early in `PATH` in `tests/test_deploy.py`.
- **Validation Scope**: Fake-Docker unit tests verify script control flow, argument passing, status checks, and failure exit paths without needing production host access or live registry/daemon operations. This test suite does NOT claim or constitute a full-stack live host deployment.
