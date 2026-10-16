# Jules: combine reviewed router and deployment sources

Repository: kebowandira/multi-ai-chat
Start branch: chatmerge (9 characters). Start a FRESH Jules task.
Deployment snapshot: e14c0b3e11ccd8b6c720663262175e85c88dff84.
Its complete tree equals accepted b2c0dfd5d78b0fc410b68ae2ea0f4dd33926ba2d.
Router source: b599ad357175b5df9082cc8ae8755712c75ad160
on review/router-accepted-20261016 (PR #2).
Read AGENTS.md and this document first. Historical assignments do not
override this integration scope.

## Goal and scope

Prepare ONE combined draft integration PR, without merging existing PRs.
Keep accepted deployment implementation/tests unchanged unless a reproduced
interaction defect requires a minimal fix, reported explicitly.

Bring EXACTLY these SIX files from router source b599ad3 into this branch:
- router/policy.py
- router/custom_router.py
- tests/test_policy.py
- tests/test_config.py
- tests/integration_gateway.py
- docs/reviews/JULES_ROUTER_VALIDATION_2026-10-15.md

Do NOT copy the router snapshot's older docs/JULES_DEPLOY_ASSIGNMENT.md;
it differs from current main and would regress task instructions.
Do not replace the deployment files with baseline versions.
Use git fetch of the named router branch then restore the six paths from
the exact SHA. If remote retrieval is blocked, report the blocker; do not
fabricate files or silently substitute another revision.

Run baseline tests first, integrate the six files, then run the combined suite.
Expected nominal count: 97 (81 deployment snapshot +16 router additions);
discover actual count and explain differences rather than forcing a number.

## Verification and evidence

1. python3 -m unittest discover -s tests -v
2. python3 scripts/check_source.py
3. bash -n scripts/deploy.sh
4. git diff --check
5. Verify all six restored files byte-for-byte against b599ad3.
6. Verify deployment scripts and focused tests byte-for-byte against e14c0b3,
   except explicitly justified interaction fixes.
7. If possible run tests/integration_gateway.py using isolated dependencies,
   LiteLLM 1.104.0 and local mock endpoints/dummy keys only. Read its harness
   before running; never send provider calls. This is NOT required to label
   all integration accepted if runtime cannot initialize: report timeout,
   failed, skipped and unavailable scenarios honestly.
8. Add docs/reviews/JULES_COMBINED_VALIDATION_2026-10-16.md with source SHAs,
   actual commands/literal results, SHA256 manifest, differences, and blockers.
   Keep isolated virtualenvs/generated configs/secrets/logs out of Git.

Known limits to preserve: coordinator independently validated router unit
tests but could not reproduce gateway initialization in its environment.
Upstream truncated streams may appear successful; no reliable truncation
detection guarantee. Image lock pair is not crash-atomic; rollback best effort.
Passing fake-Docker tests is not real Compose/VPS validation.

## Publication

Commit and push nonempty integration changes. If Jules creates a child branch,
open a draft PR targeting chatmerge. Do not merge any PR or modify existing
PR branches. The coordinator will prepare final main integration after review.
Return PR URL, exact published head/base, test counts, hashes and limitations.

No live Docker/container deployment, registry pulls, provider billing, SSH,
DNS, real keys, production data, force-push or private ops edits.
No feature expansion, model upgrades, dependency upgrades or broad refactoring.
Proceed autonomously within this scope; ask only for a concrete blocker.
