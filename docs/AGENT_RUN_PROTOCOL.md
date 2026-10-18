# Agent run protocol v1

18 October 2026. Additive integration contract; existing LibreChat/LiteLLM
routing and deployment behavior are unchanged.

## Responsibilities

The chat stack is the interface and provider gateway. A separate run ledger
owns workflow state, checkpoints and cost reservations. A project dashboard
imports a small status snapshot. Keep each authority independent; chat text
alone cannot mark a run complete or authorize production changes.

The first transport is a manually exported/imported JSON file. No service,
worker, automatic endpoint, live model adapter or Jules connection is enabled
by this document. Existing deployment/router PRs remain separate.

## Snapshot

See `agent-runs/example.json`: entirely synthetic, no deployment information.

| Field | Contract |
|---|---|
| schemaVersion | Integer 1 |
| runId | Stable 8–64 character identifier: letters, numbers, underscore, hyphen |
| revision | Positive monotonic integer; identical revision must have identical canonical content |
| repository | owner/repository, explicitly bound to the receiving project |
| title / agent / phase | Bounded plain text: 200 / 80 / 80 characters |
| state | planned, running, blocked, paused, completed, failed, killed |
| updatedAt | ISO UTC timestamp with milliseconds; source observation time |
| nextAction | At most 500 characters, handover next action |
| budget | capMicrousd, spentMicrousd, reservedMicrousd; nonnegative safe integers ≤ 10^12 |
| evidence | At most 30 items: label (≤160), sha256 (64 lowercase hex), passed (boolean), exitCode (0–255) |

One USD is 1,000,000 micro-USD. Never use floating point for accounting.
A completed snapshot requires nonempty passing evidence, no outstanding
reservations and spent ≤ cap. Dashboard display says *source-reported checks*;
it does not independently establish correctness. Hashes identify artifacts,
not the truth of their contents. Runtime imports must reject unsupported keys,
cross-owner/project access, stale revisions and same-revision conflicts.

Snapshots contain no raw prompts, conversation messages, tool commands,
provider credentials or raw logs. Strict field validation does not detect a
secret pasted inside an allowed title; review before sharing. Original full
evidence remains in access-controlled storage; links/transport are future work.

## Provider adapter contract — next implementation batch

Adapters must declare capabilities (text, tools, streaming) and configured
provider/model IDs. Existing deterministic routing remains the authority for
provider selection. Do not add a paid classifier or change routing priorities.

1. Load current run/revision and task requirements.
2. Reject unsupported capabilities or a terminal/paused/blocked run.
3. Reserve the conservatively bounded maximum cost atomically before a call.
4. A dry-run decision is a distinct enum and never sends a request.
5. Issue at most one request per recorded attempt. Preserve uncertain requests
   for reconciliation; do not automatically retry writes/tool actions.
6. Settle actual usage; retain raw receipts privately. Cost above reservation
   blocks the run. Missing pricing or usage fails closed for paid calls.
7. Store a checkpoint and next action; export a sanitized snapshot.

Per-run accounting cannot constrain unrelated API-key usage. A future trusted
adapter needs provider-side limits, account-wide controls and conservative
pricing. Availability failover is different from task-quality verification.

## Reuse from the reviewed reference

SYADAGENTIC supplied workflow ideas: on-demand skills, staged execution,
checkpoints, budgets, kill switch and evidence before completion. The reviewed
source was Sekolah76/syadagentic at 87be42724260d61f32e9dced2b2703df748a150e.
No source, jailbreak prompts, account-farming automation, global instruction
installer or skill collection is imported. No comparative performance claim.
