# Current branch state — 18 October 2026

This additive agent-run protocol branch starts at public main
7d8f2c44bf549e2e193a7b3b8bddd9d6c4e8ab09. Deployment-specific state remains
in the separate private ops repository. Existing router and deployment PRs
are open and were not merged or changed by this milestone.

Added docs/AGENT_RUN_PROTOCOL.md, a synthetic snapshot and
docs/JULES_AGENT_ADAPTER.md. The protocol is ready for a separately reviewed
mock adapter implementation. No service, provider call, classifier, callback,
Compose or deployment behavior is changed. Existing 30 unit tests and source
guard pass. Publishing the work order does not launch Jules.
