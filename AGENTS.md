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
