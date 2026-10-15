# Jules assignment: router and mock integration validation

Assignment date: 15 October 2026. Status: ready for owner submission; no Jules
session has been launched by publishing this file.

## Objective and ownership

Validate the actual router/configuration path in this public reusable stack.
Find reproducible defects, fix them narrowly, and open a pull request with
evidence. Use synthetic prompts, dummy keys and a local mock provider only.

Jules owns this task's router/configuration tests and minimal related fixes.
The coordinating assistant owns integration review and deployment-script work.
Host, DNS, TLS, credentials, live provider calls, backup execution and private
operations state are outside this assignment.

## Start here

Read AGENTS.md, README.md, docs/OPERATIONS.md, docs/PRODUCTION_READINESS.md,
docs/SOURCES.md, requirements-dev.txt, router/, scripts/configure.py,
scripts/common.py, scripts/gateway-smoke.py, tests/test_policy.py,
tests/test_config.py and tests/integration_gateway.py.

Record the current remote main SHA. Initial assignment baseline is
30c87f06aefaf930b6d0bda2405a17187bab9bbf; use the current main containing this
assignment, rather than checking out that older commit blindly.
Inspect branches and existing PRs for duplicate work before changing files.
Use a dedicated branch such as jules/router-validation-2026-10-15.
Do not push code changes directly to main and do not auto-merge.

## Allowed changes

- tests/test_policy.py, tests/test_config.py, tests/integration_gateway.py.
- New focused tests under tests/ and a report under docs/reviews/.
- Minimal evidence-backed fixes in router/, scripts/configure.py and
  scripts/common.py; avoid unrelated changes to common helpers.
- Small necessary fixes to scripts/gateway-smoke.py.
- Related explanations in this assignment's report.

Do not edit deployment/backup/pinning scripts, Compose, image versions,
provider/model inventory, README.md or AGENTS.md in this first task. Report
findings outside scope with paths/reproduction and let the coordinator handle
them. Do not alter routing preference order or replace the deterministic
classifier. Keep source publication rules and existing capabilities intact.

## Required baseline checks

Run from the repository root, using isolated virtual environments:

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/check_source.py
.venv/bin/python -m unittest discover -s tests -v
bash -n scripts/deploy.sh
.venv/bin/python -m compileall -q scripts router tests

python3 -m venv .venv-gateway
.venv-gateway/bin/python -m pip install 'litellm[proxy]==1.104.0' socksio prisma
.venv-gateway/bin/python tests/integration_gateway.py
~~~

The LiteLLM version matches the existing test example. Inspect the configured
image/version and official documentation before interpreting compatibility.
If dependencies are unavailable, report the exact failure; do not silently
substitute a different version or claim a skipped check passed. Capture version
information and commands. Do not run model health probes against real providers.

## Work in order

1. Run and record the baseline before editing. Distinguish failures in product
   behavior from limitations in the test harness/environment.
2. Trace configuration generation through the actual CustomLogger callback and
   LiteLLM fallback. Verify the hook is registered and invoked, rather than
   merely asserting a pure policy function returns the right value.
3. Strengthen the real local-proxy integration test where necessary:
   - missing and invalid gateway keys fail without reaching the mock backend;
   - ordinary auto classification, explicit UI route precedence, prefix
     precedence/removal and follow-up conversation behavior;
   - missing-key pruning does not advertise unusable route aliases;
   - failed primary reaches the intended fallback; exhausted fallback returns
     an error and does not loop indefinitely;
   - streaming produces valid SSE framing and completion termination; a
     failure after partial output is surfaced without duplicating output;
   - documented text-only route guards, input limits and output limits are
     enforced before an incompatible upstream request reaches the mock.
   Verify these claims against code. If a documented guard is missing, add a
   minimal compatible fix or report an unresolved design choice explicitly.
4. Add focused regression tests for each concrete fix. Test useful behavior,
   including upstream call counts/model IDs, rather than mirroring internals.
   Avoid broad refactors or tests that only assert the implementation's shape.
5. Ensure test servers/processes stop on failure, ports are local/ephemeral,
   timeouts are bounded and no real provider host can receive fixture calls.
   Use a temporary directory for generated .env/runtime fixtures.
6. Run the baseline checks again after changes. Record exact totals, failures
   and skipped checks. Inspect the full diff and run the source guard before
   committing. Do not add environments, logs, credentials or generated runtime.

## Deliverables and acceptance

Open one focused PR targeting main. Add
docs/reviews/JULES_ROUTER_VALIDATION_2026-10-15.md containing:

- source/base SHA, tested implementation SHA, Python/LiteLLM versions;
- baseline and final commands/results;
- findings with severity, affected path, reproduction, expected/actual behavior;
- minimal fix rationale and regression evidence;
- a coverage table for each required scenario above;
- remaining risks, blocked/skipped checks and recommended follow-up.

The PR must explain the concrete problem, resulting behavior and validation.
List any unresolved finding instead of hiding it behind a green unit suite.
The coordinator will review and merge; do not update a private deployment's
submodule pointer or claim that this public test proves production readiness.

## Boundaries

No SSH or production host access. No DNS, firewall, OAuth application, account
or repository-visibility changes. No API billing, real keys, cloud deployment
or destructive volume operations. No new paid service or classifier. Keep this
report generic and public-safe. If private material appears, do not reproduce
it in a public issue/PR; tell the owner privately.
