# C0 — combined source evidence reconciliation

Repository: kebowandira/multi-ai-chat.
Starting branch: chatplan. Exact execution SHA will be pinned in the GitHub issue
after this work order is committed. Target draft PR: chatplan.
Implementation snapshot: cd701216c14182f7f9febb71db5b332e1af1e715.
Read AGENTS.md, docs/PROJECT_STATE.md, docs/COMPLETION_ROADMAP.md and all three
existing validation reports in full. Existing JULES_INTEGRATION.md is historical;
combined code is already present. DO NOT repeat integration or deployment fixes.

## Ownership / allowed modifications

Only:
- docs/reviews/JULES_COMBINED_VALIDATION_2026-10-16.md
- docs/reviews/C0_EVIDENCE_2026-10-19.md (new)

No implementation/test changes. Execute tests but do not edit them. No changes
to PR6 protocol, agent adapter, reference docs, global instructions, source guards,
CI, Compose, requirements, models, routing policy or private ops.
No other observed branch owns the new C0 evidence path. Existing older PRs
retain their history and must not be rewritten or merged.

## Required work

1. Verify exact starting SHA from issue. Run baseline unittest discovery,
   source guard, bash -n and diff --check; record commands/exit codes/output.
2. Compare SIX router files byte-for-byte to
   b599ad357175b5df9082cc8ae8755712c75ad160:
   router/policy.py, router/custom_router.py, tests/test_policy.py,
   tests/test_config.py, tests/integration_gateway.py,
   docs/reviews/JULES_ROUTER_VALIDATION_2026-10-15.md.
3. Compare SEVEN deployment files to
   b2c0dfd5d78b0fc410b68ae2ea0f4dd33926ba2d:
   scripts/deploy.sh, scripts/preflight.py, scripts/pin-images.py,
   tests/test_deploy.py, tests/test_preflight.py, tests/test_pin_images.py,
   docs/reviews/JULES_DEPLOY_VALIDATION_2026-10-16.md.
4. Recompute actual SHA256 of all 13 files; repair stale combined manifest,
   especially tests/test_config.py. Never copy a hash from another report.
5. Correct actual baseline branch/revision; record that historical chatmerge
   was not the branch where the published combined commit appeared.
6. Unit nominal count is97, but report actual discovery truthfully.
   No gateway installation/run required in C0; explicitly mark runtime
   integration NOT RUN and preserve previous reviewer startup timeout and
   truncated-stream-detection limitation. Do not claim full-stack readiness.
7. Preserve best-effort/non-crash-atomic dual-file lock limitation.
8. Record source guard count as observed, with scope, not proof of runtime security.
9. Verify diff is confined to two allowed report files; source guard before
   commit, publish draft PR, return issue/task/PR URLs and exact published SHA.

## Acceptance / stop

Acceptance: all source identities match or discrepancies are precisely reported;
literal reproducible unit/static checks; correct manifest; honest runtime limits;
no source/test change and no new integration claim from green unit tests.
If a baseline fails, source is unavailable, an overlap appears, or code correction
is needed, stop and report it with evidence; do not expand scope.
No Docker daemon/container startup/pull, billable inference, provider auth,
credentials, SSH/VPS, production data, financial/security-policy decisions,
permission changes, destructive git, merge or deployment.
Only local synthetic test harness commands are permitted.
This issue launches C0 only; never auto-start later roadmap tasks.
