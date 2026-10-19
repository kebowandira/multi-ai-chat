# C1 deployment correction handoff — 16 October 2026

Start branch: jules/deploy-c1-20261016
Target: main
Do not use jules/router-validation-2026-10-15-12658344165251581824.
The coordinator copied the C1 submission unchanged onto this branch, based on
main, to separate it from the accepted router work. Existing PR #1 is historical
mixed work. No code fix was made by this separation.

Read AGENTS.md and docs/JULES_DEPLOY_ASSIGNMENT.md. That assignment's scope and
execution authority apply. Continue on a new child branch from this branch if
Jules requires it, and submit a PR targeting jules/deploy-c1-20261016 in that case;
otherwise update this branch's draft C1 PR targeting main. Do not merge/force-push.
If the correct base is unavailable, report that and do not substitute main or
the router branch.

Required corrections from C1 review R1-R5:
1. Branch separation is now supplied. Leave accepted router work and PR alone.
2. Verify Compose failures stop image pinning, unmatched/malformed digests fail,
   canonical repository matching handles host:port and existing digests, and
   optional profiles are deliberately included. No manual interpolation fallback.
3. Test empty expected services, empty/error ps, missing/exited/restarting/
   starting states, no-healthcheck running service and all four profile modes.
   Use Compose's effective environment consistently; .env grep alone cannot
   establish enabled profiles when shell variables override it.
4. Preflight must validate all actual enabled-service required inputs, address
   application-port conflicts with same-project distinction, and avoid incorrect
   shared-host web-port warnings. Verify lock output consistency on failures
   during writing and at each rename; implement recovery or report the actual
   pair-consistency limitation honestly.
5. Cover these with meaningful fake-Docker tests. Report skipped scenarios
   explicitly. A fixture returning Compose 2.30.1 is not proof of a real CLI.
   Record literal test output and SHA256 for every changed implementation/test
   file. Reference retrievable published code identity, not a branch name under
   a heading called SHA.

Read the full original review at:
https://github.com/kebowandira/multi-ai-chat/pull/1#issuecomment-6205979730

Use isolated synthetic fixtures and fake Docker only. No actual container
startup, registry pull, host access, credentials, providers, DNS or deployment.
Proceed within scope without routine reconfirmation. Return the exact PR URL,
base/head, tests, evidence and blockers. The coordinator reviews integration.
