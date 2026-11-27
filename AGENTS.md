# Agent instructions — Multi-AI Chat (boilerplate)

Shared ground rules for any coding agent working in this repository. This
repo is the generic, reusable deployment baseline — Docker Compose +
LibreChat + MongoDB + Meilisearch + RAG/pgvector + optional LiteLLM. It has
no deployment-specific state (domain, provider accounts, agent handover
notes); that belongs in a separate private "ops" repo that pulls this one
in (typically as a git submodule).

## Hard rules

- Never commit `.env`, `runtime/`, `docker-compose.override.yml`,
  `image-lock.json`, or `backups/`. `scripts/check_source.py` enforces an
  allowlist (`SOURCE_FILES.txt`) — run it before every commit.
- Edit the source templates (`librechat.yaml`, `litellm_config.yaml`), never
  the generated files under `runtime/`. `scripts/configure.py` regenerates
  them from `.env` + the templates + `router/routing-policy.json`.
- Edit routing priority/regex only in `router/routing-policy.json`. Keep
  `coding` rules ahead of `research` rules (deliberate: see
  `tests/test_policy.py::test_coding_precedes_research_when_both_could_match`).
- No destructive git operations, no force-push, no unattended image
  updates. `scripts/pin-images.py` resolves digests but does not start
  containers; `scripts/deploy.sh` is the only script that does.
- Don't add a paid routing/classifier dependency to replace
  `router/policy.py`'s regex approach without discussing it first — the
  zero-cost deterministic router is a deliberate design choice, not a
  placeholder.
- This repo intentionally has no `github-bootstrap.py`-style identity-bound
  script and no hardcoded GitHub owner/repo — keep it that way so it stays
  reusable by anyone who forks it.

## Before changing router/ or scripts/configure.py

```bash
python3 -m unittest discover -s tests -v
```

`tests/test_policy.py` and `tests/test_config.py` are fast and dependency-light
(stdlib + PyYAML). `tests/integration_gateway.py` needs a separate
`.venv-gateway` with `litellm[proxy]` installed and is not part of the
default test run.

<!-- BEGIN bule-ai-os:save-claude-usage (source: kebowandira/bule-ai-os agy/AGENTS_BLOCK.md; do not edit here) -->
## Agent rules: save Claude usage (owner, 2026-11-27)

Applies to every agent working in this repository: Claude Code, agy, ask-gemini, Gemini, Jules and Colab
notebooks. Full text: the "Save Claude usage" host rule in `kebowandira/bule-ai-os` `agy/CLAUDE_HOST_RULES.md`.

1. Graphify first. Query the cross-repo graph (MCP `graphify-cross-repo` on DE1, backup on NL2, or
   `graphify query "<question>"`), then read only the files and lines it points to. No full-repository rereads.
2. Fresh graph. The graph is rebuilt after each merge to `main`. Run `graphify-fresh check` before starting;
   if it reports the graph stale, say so (until 2026-12-04 a warning, after that a stop).
3. Role split. agy (or Jules when the owner asks) builds from a spec made with
   `agy/templates/SPEC_TEMPLATE.md` in bule-ai-os: 1 to 3 files, tests written and committed first. Claude
   writes the spec and reviews only the diff and the test output.
4. Machines check first. Tests, lint and data checks run on the VPS (`scripts/agent-preflight.sh` where this
   repository has one). Claude reviews only work that shows `PREFLIGHT PASSED <sha>`.
5. Colab only for heavy CPU jobs (over about 30 minutes on one core); everything else runs on NL1, NL2 or DE1.
6. Model ladder. ask-gemini for the first-pass review, Claude Sonnet for the review, Claude Opus only for hard
   design calls.
7. Usage is logged per Claude session from 2026-11-28 to 2026-12-11 (`claude-usage-log`) to confirm the savings.

Live trading is read-only. Draft pull requests only. No secrets in any file.
<!-- END bule-ai-os:save-claude-usage -->
