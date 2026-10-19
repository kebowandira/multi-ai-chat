# MultiChat completion roadmap and Gemini monitor guide

Owner direction: 19 October 2026. Jules is the default worker for bounded
coding, tests, docs and refactors; coordinator retains architecture, review,
security-policy decisions, secrets, authentication, infrastructure and merge authority.
This is the project's staged queue, not a claim that automation is installed.

## Release definitions

V1 private pilot: one HTTPS chat UI, authenticated trusted users, selected
official provider endpoints, optional deterministic routing, tested isolation,
bounded synthetic and minimal operator-authorized live verification.
V1 operational: demonstrated backup/restore, monitoring, maintenance and recovery.
V2 optional: provider-neutral agent task execution and usage dashboard.
Subscription-account connectors, local inference and Aider are research options,
not V1 requirements. Do not promise all models or capabilities without account tests.
MongoDB SSPL vs strictly OSI-only licensing remains an owner decision.

## Verified inventory (19 October)

All nine public branches were listed through API; pagination exhausted.
main 7d8f2c44bf549e2e193a7b3b8bddd9d6c4e8ab09 lacks reviewed combined work.
PR2 b599ad357175b5df9082cc8ae8755712c75ad160 preserves reviewed router.
PR5 cd701216c14182f7f9febb71db5b332e1af1e715 now contains combined router/deployment
and a contributor report claiming 97 passes; coordinator has not independently
accepted that combined revision. A manifest entry for tests/test_config.py is
suspect and must be recalculated. Previous deployment-only 81 passes were reviewed.
PR1 and PR3 are older overlapping submissions; do not restart their tasks.
PR4 is absent from the current open-PR list.
PR6 feat/agent-runs-20261018 at ee625065827c5b7b89ba332696f0fa9041b5c018
owns additive protocol planning; its adapter has no verified launch.
Issue7 has no label or comments at inspection and proposes overlapping deployment
work; do not launch it in parallel with reconciliation.
chatmerge 6d8d14b36457cdab991611f8c5ca2f9e9fceda2e preserves separate framework
references, not combined router code. Preserve these docs during later integration.
No observed evidence establishes production deployment or continuous Gemini monitoring.

## Ordered batches

Each row becomes a fresh complete work order/issue only when its prerequisites
are reviewed and the exact execution base has been verified. Never label every
row jules at once. Future rows are backlog specifications, not runnable tasks.

| ID | Work and allowed scope | Acceptance | Dependency / owner |
| --- | --- | --- | --- |
| C0 | Verify combined source identities and repair report only | Literal unit output, all 13 hashes, upstream comparisons, truthful skipped runtime evidence | First eligible Jules task; docs-only ownership |
| G0 | Independently review combined full diff and C0 evidence | Scope, hashes, tests, CI status checked; explicit accepted/blocked result | Coordinator; no automatic merge |
| C1 | Portable unit-test CI using approved dependency policy, no credentials | Clean checkout runs suite/guard/shell check; deliberate failure blocks check; no live providers | G0 + coordinator-approved CI design; Jules |
| C2 | Synthetic configure/profile/provider matrix tests | Native/custom enabled/disabled, missing key pruning, all four profiles, generated output excludes absent providers | G0; tests only first, minimal reproduced fixes separately authorized |
| G1 | Review source integration candidate | C1/C2 evidence, complete diff, no lost reference/protocol docs; main merge separately decided | Coordinator |
| O1 | Schema/image/license and host resource review | Exact versions, advisories, resource headroom and license decision documented privately | G1; coordinator, not Jules |
| C3 | Operator quickstart and adding-provider documentation reconciled to accepted source | Commands/variables trace to code; native vs API subscription distinction; no invented runtime success | G1; Jules docs-only, technical facts verified |
| O2 | Staging/pilot installation and access verification | HTTPS, signup restrictions, two-user isolation, streaming, loopback/database exposure checks | O1; coordinator only |
| O3 | Selected live provider checks | Minimal authorized calls; actual model/account/capability/billing evidence | O2; coordinator only |
| C4 | Offline backup/restore test fixtures and runbook corrections | Synthetic failure propagation and data manifest checks; no real databases/keys/backups | O2 defines requirements; Jules bounded fixtures/docs |
| O4 | Restore, reboot, alert, upgrade/rollback rehearsal | Measured RPO/RTO, working alert path and verified recovery | C4; coordinator only |
| G2 | Private operational release review | Gate1/Gate2 PRODUCTION_READINESS evidence; explicit residual risks | Independent reviewer + owner deployment decision |
| A0 | Reconcile PR6 protocol with accepted core interfaces | Versioned contract review; no tools on text-only routing aliases | G1; coordinator interface decision |
| A1 | Mock provider adapter library only | See existing PR6 work order; fake ledger/provider, no financial authority changes | A0 + financial-contract approval; Jules code/tests only |
| G3 | Independent agent-adapter review | No replay of uncertain actions; state transitions, redaction, evidence checked | Coordinator |
| A2 | Read-only agent-run status view using synthetic contract | Pending/running/failed/cancelled/completed render accurately; no secret payloads | G3; Jules bounded UI/tests |
| A3 | Idempotent task transport with mocked Jules/GitHub API | Duplicate events do not duplicate tasks; bounded poll/cancel/retry; no auto-merge | Approved interface/auth policy; Jules mocked implementation |
| O5 | Authenticate and connect real agent tools | Credentials scoped, read-only task verified before writes | Coordinator only; no credentials delegated |
| G4 | Agent workflow acceptance | One task from instruction through reviewed draft PR with auditable status | Independent reviewer |
| R1 | Local Ollama/Qwen evaluation | Measured memory/latency/correctness and short-task capability | Optional; coordinator host work |
| R2 | Account-based Gemini connector assessment | Verify license/auth/provider-supported use/quotas; no passwords in Git | Optional; coordinator research decision |

C1-C4/A1-A3 require detailed file ownership, tests, evidence and stop conditions
before labeling; this roadmap alone is insufficient implementation authorization.
Security-policy, budget-authority or permission changes are never Jules scope.

## Gemini monitoring procedure

Gemini reads GitHub state; it must not infer completion from a summary.
For every task record issue URL, start/target SHA, owned paths, dependencies,
Jules bot acknowledgement/task URL, PR/head SHA, CI conclusion, reviewer identity
and integration/deployment evidence. State vocabulary:
planned -> prepared -> trigger_requested -> launched -> PR_opened -> CI_passed
-> reviewed -> merged -> deployed, with blocked/failed/cancelled alternatives.
CI_passed is not reviewed. Reviewed is not merged. Merged is not deployed.

Only apply exact jules label after issue body/work order/base/ownership are complete.
Record launched only after google-labs-jules[bot] explicitly acknowledges working
and provides a verifiable task URL. If absent, report trigger_requested/unconfirmed.
Do not repeatedly relabel or submit duplicate sessions.
When a PR lands, Gemini assembles a compact reviewer packet, not approval:
diff scope, commands/exit codes, failed/skipped tests, SHA256, CI links,
limitations and next eligible task. Changed head invalidates prior head-specific approval.
One active implementation per repo by default; no overlapping path ownership.
Do not edit Jules-owned files while its task runs.

Continuous monitoring/automatic progression requires a separately configured
runner and authentication. Neither this document nor a Gemini browser chat
creates that runner. No schedule or deployment is claimed here.

## Stop conditions and review triggers

Stop on unavailable exact source, conflicting ownership, failing baseline,
scope expansion, unknown prices/financial authority, secrets, auth/SSH needs,
security-policy decisions or production access. Report blocker with evidence.
Ask coordinator to resolve; never silently use main or replace source.
Fresh branch names created by coordinator must be <=10 characters.
Final release/merge approval remains with coordinator/owner.
