# Jules coding task C1: deployment script correctness

Assigned 16 October 2026 (WIB). Status: ready for owner submission.
This is a new task, independent of router PR #1. Do not append it to PR #1.

## Execution authority and Git workflow

Proceed with implementation, reversible local tests, branch publication and one
PR without routine reconfirmation. Suggested branch:
jules/deploy-validation-2026-10-16 (an automatic Jules branch name is fine).
Start from current remote main containing this instruction, record its SHA and
inspect existing PRs. Target main. Do not cherry-pick or modify the router PR.
If main advances, preserve upstream changes and report the actual base.
No auto-merge, force-push or production deployment. If Jules itself requires
plan approval, present one concrete plan with these choices already applied.

## Objective

Make deployment tooling fail clearly on broken prerequisites or missing/exited
services, apply regenerated config reliably, and resolve image locks from actual
Compose inputs. Preserve both standalone and existing-host proxy modes.
Use narrow fixes with behavioral regression tests. Report facts, not readiness
claims. This task does not prove that the complete stack works on a real VPS.

## Read first

AGENTS.md, README.md, docs/OPERATIONS.md, docs/PRODUCTION_READINESS.md,
SOURCE_FILES.txt, .env.example, docker-compose.yml, scripts/deploy.sh,
scripts/preflight.py, scripts/pin-images.py, scripts/common.py,
scripts/configure.py and existing tests.

## File ownership

Allowed implementation: scripts/deploy.sh, scripts/preflight.py,
scripts/pin-images.py, and minimal helper changes in scripts/common.py only when
necessary. Allowed tests: new tests/test_deploy.py, tests/test_preflight.py and
tests/test_pin_images.py plus narrowly named fixtures under tests/.
Allowed report/evidence: docs/reviews/JULES_DEPLOY_VALIDATION_2026-10-16.md
and related text/JSON evidence under docs/reviews/deploy-2026-10-16/.

Do not change router/, router tests, scripts/configure.py, backup.py, Compose,
provider inventory, image versions, .env.example, AGENTS.md or prior assignments.
If a concrete defect requires an out-of-scope change, report reproduction and
continue independent work; request a bounded scope extension only if blocked.

## Required implementation scenarios

### 1. Deployment failures and service readiness

Inspect and reproduce these risks before changing code:
- docker compose pull failures are currently swallowed by "|| true";
- docker compose ps errors/empty output can become a false healthy result;
- stopped/exited/missing services may not appear in ordinary ps output;
- regenerated mounted configuration does not reliably apply through restart;
- deploy.sh comments promise recreation but the actual command may not force it.

Required resulting behavior:
- validate prerequisites, environment and Compose configuration before any
  container-starting command; use config -q, never print expanded secrets;
- unexpected pull errors fail deployment; do not silently deploy stale images;
- apply changed generated configuration through an intentional recreation
  mechanism and document the reason in comments;
- determine expected services from resolved active Compose configuration,
  excluding disabled profiles; query all applicable container states;
- success requires every expected service running and healthy where a health
  check exists; missing, exited, restarting, unhealthy and Docker command errors
  must never be treated as success;
- bounded waiting handles legitimate starting states; failures exit nonzero with
  useful service/status diagnostics that do not dump full application logs or
  expanded secret environments;
- standalone mode validates the bundled Caddy; shared-host mode does not start
  or validate bundled Caddy. Router enabled/disabled combinations stay valid.
- never delete data volumes. Do not silently stop unrelated projects/services.

### 2. Preflight accuracy

- Required Docker/Compose/daemon failures must fail, rather than warn and
  continue. Parse supported Compose versions deliberately; too-old/unparseable
  versions fail with actionable instructions.
- Validate nonblank required inputs used by enabled services against actual
  configuration, without printing values. Missing provider keys can remain a
  clear warning, consistent with starting an empty private installation.
- Check ports relevant to the selected mode: occupied 80/443 is expected behind
  an existing reverse proxy; occupied application binding needs an actionable
  distinction between an existing same-project deployment and a conflict.
  Avoid announcing certain bind failure from an advisory probe alone.
- No host firewall/DNS changes or user-account modification.

### 3. Image-lock correctness

- Resolve image names from Compose's actual interpolation/configuration, not
  raw YAML strings such as ${IMAGE:-default}. Include optional services
  deliberately as the existing pinning contract requires.
- Prevent existing generated override pins from silently masking a newly chosen
  source image on an intentional repin. Preserve legitimate source inputs.
- Resolve repository/tag/digest syntax safely, including registry host:port.
  Match RepoDigests to the intended image repository; don't select an unrelated
  digest just because it is first. Handle Docker canonical names deliberately.
- On pull/inspect/config failure, exit nonzero without overwriting a previously
  valid lock. Write staged output safely; avoid partial/corrupt individual files.
  Do not claim two separate files form a transactional pair without a recovery
  mechanism. Test failures at each meaningful step.
- No actual registry pulls or container startup are required for this task.

## Test method and boundaries

Use isolated temporary project copies and a fake docker executable early in
PATH, or mocked subprocess responses for Python helpers. Exercise deploy.sh
itself with the fake executable so exit behavior and command order are tested.
The fake must record synthetic invocations and return realistic Compose
JSON/status data. Never let test commands fall through to a real Docker binary.

Test at least: success; no .env; bad Compose; unavailable daemon; pull failure;
ps error; empty/missing service; exited/unhealthy/restarting/starting service;
bounded timeout; no-healthcheck running service; generated-config recreation;
four standalone/router profile combinations; substituted image selection;
optional-service pinning; registry port syntax; mismatched/empty digest; failed
pull/inspect; previous-lock preservation.

Use a controllable timeout/clock or mocked wait commands; don't make the suite
sleep for minutes. Do not mock away the exact behavior under test.
Existing unit tests must keep passing. Real Compose CLI validation is useful if
available without starting containers; otherwise report it as not run.

Run baseline and final:
~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/check_source.py
.venv/bin/python -m unittest discover -s tests -v
bash -n scripts/deploy.sh
.venv/bin/python -m compileall -q scripts router tests
git diff --check
~~~

No SSH, real deployment, DNS/TLS edit, paid API inference, actual provider
credentials, backup execution, new service or infrastructure purchase.
Temporary synthetic .env/locks/runtime stay outside tracked source.
Do not rerun the costly gateway integration unless your change actually affects
its code path; explain relevance if you do.

## Evidence and completion

Publish one focused PR with:
1. Reproduced defect, minimal fix and before/after behavioral evidence.
2. Scenario matrix with passed/failed/skipped and exact commands/output.
3. Actual retrievable base and tested published commit SHA.
4. SHA256 manifest for every changed implementation/test file, plus Python and
   Compose versions where used. File hashes preserve identity if Jules rewrites
   local commits during publication.
5. Explicit distinction: fake-Docker tests, real CLI parsing, full-stack runtime
   and live acceptance. Never label fake-Docker success full-stack validation.

Finish code/tests, publish the branch, run checks on the published clean code,
then add evidence. If publication rewrites SHAs, report that and use matching
file hashes; never guess a commit SHA. Do not fabricate transcripts.
Return PR URL, branch/head, tested identity, results and unresolved findings.
Coordinator reviews and decides merge; stack submodule/deployment remain separate.
