# Fresh Jules task: deployment corrections

Repository: kebowandira/multi-ai-chat
Select start branch: deployfix (9 characters).
Snapshot: 5c0e552d873bef4597ddafaa61d00690345163dc.
That snapshot has the SAME tree as rejected 3059504 and 1b6c725.
No R1–R5 fixes are present. Do not reuse the completed old Jules session.

Read AGENTS.md, docs/JULES_DEPLOY_ASSIGNMENT.md and
docs/JULES_DEPLOY_REVIEW_HANDOFF.md. This document supplies the current
branch workflow. Work from deployfix; if a child branch is required, target
deployfix in a new draft PR. Leave PRs #1–#4 and router branches untouched.
Do not merge, deploy or force-push. No routine reconfirmation needed within scope.

## Required actual changes

1. scripts/pin-images.py: canonicalize image repositories precisely.
Docker Hub shortnames must never suffix-match unrelated registries.
Reject malformed algorithm/hash digests, use full valid sha256 fixtures.
An input already pinned to a digest must not silently resolve to a different
digest. Test Docker Hub aliases, host:port, unrelated same-basename registry,
malformed digests, and requested digest mismatch.

2. tests/test_pin_images.py currently invokes real Docker in its alleged
rollback test. Mock load_compose_services and resolve_digest. Inject each
temporary write failure and each rename failure, especially second replacement
after the first succeeds. Verify original bytes and cleanup for preexisting
and absent outputs. Fix implementation as necessary. Two renames do not
provide crash-atomic pair replacement: document actual limits, including
rollback failure, and do not claim untested atomicity.

3. scripts/preflight.py: audit actual mandatory enabled-service inputs.
Current list omits JWT_REFRESH_SECRET, CREDS_KEY, CREDS_IV and router
LITELLM_SALT_KEY. Test each mandatory blank field and required constraints
without logging secret values. Preserve shell profile precedence.

4. scripts/deploy.sh: resolve and validate expected services BEFORE Caddy
run, pull or up. Do not suppress discovery errors with || true. Test
empty/error discovery prevents these mutations. Test empty ps. Verify every
returned replica or explicitly enforce/document single-container support.
Retain all four profile modes and missing/exited/restarting/starting/health tests.

5. Replace stale validation report claims with literal actual test output.
Baseline's unmocked Docker test failed here: 61/62 final tests passed, one
FileNotFoundError. Do not claim Docker Compose 2.30.1 is installed just because
a fake returns it. Record fresh SHA256 for all changed implementation/test
files, tested published identity (or stable hashes across publication),
skipped scenarios and limitations.

## Allowed scope and verification

Only deployment/preflight/pin-images scripts, minimal common helper if needed,
their focused tests/fixtures and deployment validation report/evidence.
No router, configure.py, backup.py, Compose, provider/image inventory,
.env.example, AGENTS changes.

Use isolated synthetic fixtures and mocked/fake Docker ONLY. No live Docker,
registry pulls, providers, real credentials, SSH, DNS or deployment.
Run python3 -m unittest discover -s tests -v, scripts/check_source.py,
bash -n scripts/deploy.sh and git diff --check. Preserve a nonempty
implementation/test diff before publication. Return PR URL, base/head,
literal tests, hashes and unresolved limitations.
If editing/publishing is unavailable, report the blocker instead of
recommitting identical files.

Original detailed review:
https://github.com/kebowandira/multi-ai-chat/pull/4#issuecomment-6208285353
