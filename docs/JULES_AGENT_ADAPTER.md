# Jules A1 — mocked provider adapter for the run protocol

Status: ready for owner submission; no Jules session launched.
Start from `feat/agent-runs-20261018`, record the fetched SHA, and create a new
branch. Target that branch in one draft PR. Inspect open PRs first; router and
deployment work are owned separately. Do not merge or deploy.

## Read first

AGENTS.md, docs/AGENT_RUN_PROTOCOL.md, router/policy.py, router/custom_router.py,
router/routing-policy.json, SOURCE_FILES.txt and existing tests. Run baseline
source guard and unit tests. Do not assume the public main branch contains the
accepted router PR; preserve the selected base.

## Scope

Implement `router/agent_adapter.py` and `tests/test_agent_adapter.py` only,
plus `docs/reviews/AGENT_ADAPTER_A1.md`. Use an injected ledger interface
and an injected fake provider transport. Private core source is not required;
the protocol is public and sufficient for a test double.

Ledger methods: get current status/revision; reserve(attempt, cost, revision,
dry_run) returning RESERVED or DRY_RUN; settle(attempt, observed_cost, revision);
record checkpoint. Final interface details must be documented in the report.
The adapter must reload revision after each ledger mutation.

Deliver a library component, not a callback installation. No changes to the
existing callback, routing priorities, LiteLLM config, Compose, providers,
requirements, deployment scripts, global agent files or production services.

## Required behavior and tests

- Explicit capability match before selecting a provider; no invented model IDs.
- A separate DRY_RUN result never calls transport or settles a paid request.
- Reserve cost before every call; reject missing prices or insufficient budget.
- Record one stable attempt; an already reserved/settled attempt cannot replay.
- Known successful response settles observed cost and records a checkpoint.
- Timeout/connection loss leaves the reservation for reconciliation. Do not
  blindly release and retry an uncertain request or external write.
- Failed/partial stream cannot be reported complete. No automatic retry of
  tool actions. Unsupported tools/streaming return an explicit error.
- A provider cost above the reserved amount stops additional work and is
  reported for review. No claim to undo already spent money.
- Logs/reports redact payloads, secrets, authorization headers and raw outputs.
- Concurrent revision conflict makes no provider call.

Use only local mocks, no network and no paid inference. Cover each behavior
with regression tests and assert provider call counts and ordering. Keep
runtime payloads out of fixture files. Run existing unit tests, new tests,
source guard and diff whitespace checks. Report base/tested SHA, file hashes,
commands, exact results and unverified integration boundaries.

Coordinator reviews the PR, then a later batch connects a trusted runner.
Publishing this instruction does not run Jules or enable the adapter.
