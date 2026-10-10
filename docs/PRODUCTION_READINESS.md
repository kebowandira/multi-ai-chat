# Production readiness and acceptance checklist

Reviewed: 10 October 2026. Scope: the reusable LibreChat + optional LiteLLM
deployment baseline for a private individual or small team.

This document defines work and acceptance criteria. An unchecked item is not
evidence of a defect, and a configured feature is not evidence of a successful
deployment. No live deployment, provider, OAuth, load, or restore result is
established by this checklist. Static and mocked tests cannot replace those checks.

Keep actual host details, account information, image locks, test evidence, and
operator handovers in the separate private operations repository described in
[OPERATIONS.md](OPERATIONS.md). Never copy credentials or real conversations into
this public template repository.

## Design boundaries

| Area | Baseline | Remaining decision or verification |
|---|---|---|
| Interface and providers | Native and OpenAI-compatible connections | Validate account access, streaming and required capabilities for every enabled model |
| Routing | Local keyword rules, explicit modes and ordered fallback | Evaluate representative tasks; this is not a proven quality or live price optimizer |
| Spending | Shared provider keys; request guards on route aliases | No durable per-user or global financial ceiling; direct endpoints bypass router guards |
| Privacy | Local application storage, cloud inference | Prompts and document excerpts leave the host; fallback can change their destination |
| Authentication | Closed registration; optional OAuth | Verify provisioning, denied access, recovery and session behavior on locked images |
| Documents | Local embeddings and vector storage | Verify ownership isolation, parsing safety, deletion and English/Indonesian retrieval |
| Recovery | Cold encrypted backup procedure | Demonstrate isolated restore and measure downtime/data loss |
| Operations | Compose restart and health checks | Install alerts and runbooks; unhealthy status alone does not restart a hung process |
| Capacity | Single VPS, estimated resource requirements | Measure concurrent chat/ingestion, disk growth and shared-host interference |
| Licensing | Documented MongoDB SSPL exception | Resolve the exception if strictly OSI-approved components are mandatory |

API access does not reproduce every feature of a provider's consumer application.
Live browsing, autonomous research, voice, image generation and code execution
are not enabled by this baseline. Record a capability matrix for the models
actually enabled; do not promise a feature based only on a model name.

## Gate 1: private pilot

Complete before relying on the platform for routine private use.

- [ ] Record source commit and deliberately reviewed image digests privately.
      Review upstream advisories and verify the actual LibreChat config schema.
- [ ] Start the complete locked stack on a disposable test host. Check volume
      ownership, model-cache downloads, startup dependencies and both router modes.
- [ ] Select standalone Caddy or the existing-host reverse proxy intentionally.
      In shared-host mode confirm the application binds to loopback, existing
      sites remain available, and trusted proxy/client-IP handling is correct.
- [ ] Verify HTTPS, HTTP redirects, browser streaming and large-request behavior.
      Scan externally over configured IPv4/IPv6: databases, RAG and LiteLLM must
      remain unreachable. Check certificate renewal monitoring.
- [ ] Create two test users. Confirm public signup is denied and neither user can
      obtain the other's conversations, uploads or retrieved document excerpts.
- [ ] Verify logout/session expiry and an operator account-recovery procedure.
      If OAuth is enabled, test allowed and unprovisioned users, verified identity
      handling, account linking and retention of a working local operator login.
- [ ] Send minimal real requests to each enabled provider. Record actual model,
      text/streaming behavior, account-region compatibility and billing evidence.
      These checks consume tokens; keep prompts synthetic and calls small.
- [ ] Exercise routing with a local mock: explicit mode, prefix, keyword,
      missing-key pruning, unavailable primary, exhausted fallback and partial
      stream failure. Confirm errors are visible and output is not duplicated.
- [ ] Test document retrieval using harmless English and Indonesian examples.
      Check citations/source relevance, unsupported files, upload limits and
      whether retrieved instructions can override the intended task.
- [ ] Set initial provider budget controls where supported and billing alerts.
      Document exposure through direct endpoints, retries and premium fallbacks.
      Restrict the pilot to trusted users while financial enforcement is absent.

## Gate 2: operational readiness

Complete before describing an actual deployment as production-ready for its
stated private-use scope.

- [ ] Define maximum acceptable data loss (RPO) and recovery time (RTO).
      Choose backup frequency, retention and a maintenance window accordingly.
- [ ] Schedule encrypted off-host backups; alert on failure and stale backups.
      Keep recovery credentials independently accessible. Restore into an
      isolated host and verify accounts, conversations, documents and retrieval.
      Record measured RPO/RTO; a successful archive upload is insufficient.
- [ ] Reboot the host and simulate service failure safely in staging. Verify
      recovery, alerts and operator actions for a hung container/provider outage.
- [ ] Monitor external HTTPS availability, service health, disk/inodes, memory,
      CPU, backup age, certificate expiry and provider errors. Test delivery of
      each critical alert. Probes must not make billable inference calls.
- [ ] Define retention for chats, uploads, vectors, search indexes and logs.
      Test deletion across active stores. Explain that retained backups preserve
      older data until expiry and prevent unintended resurrection after restore.
- [ ] Document permitted data categories and destination providers. For sensitive
      conversations use a single approved provider or a tested fallback allowlist.
      Make model/provider changes visible; avoid prompt content in routine logs.
- [ ] Review database service-account privileges, filesystem permissions, secret
      scope and host administration access. Test key rotation without destroying
      access to existing encrypted application data. Require MFA for operator
      infrastructure/provider accounts where available.
- [ ] Rehearse a staged upgrade and rollback with a backup. Include database
      migration compatibility; reverting an image does not undo a data migration.
- [ ] Establish an incident runbook: stop billable traffic, revoke exposed keys,
      preserve appropriate evidence, restore service and notify affected users.
- [ ] Resolve or explicitly accept the documented licensing boundary. Keep the
      stack's licensing description accurate.

## Gate 3: controlled expansion

Complete before admitting more users or promising predictable usage budgets.

- [ ] Measure concurrent chats plus document ingestion, response latency, error
      rates, resource peaks and disk growth. Set supported concurrency, upload
      size and storage limits from those measurements.
- [ ] Define per-user and overall daily/monthly budgets, currency, reset timezone
      and price-metadata update rules. Account for cached/reasoning tokens and
      retries; unknown prices must not silently count as zero.
- [ ] Design durable usage attribution and enforcement for every billable path,
      including native/direct endpoints, title generation and remote embeddings
      if enabled. Gateway-only quotas cannot cover traffic bypassing the gateway.
- [ ] Test financial limits across concurrent requests, restarts and fallback.
      Reserve estimated spend before admission and reconcile actual usage.
      Document remaining in-flight overshoot and unavailable usage reports;
      rate limits and billing alerts are not equivalent to a hard financial cap.
- [ ] Set a cost ceiling or approval policy for premium fallbacks. Validate
      context/capability compatibility and reject unsupported requests early.
- [ ] Evaluate routing on a fixed set of representative coding, research and
      writing tasks. Record quality, latency and measured cost before changing
      preferences. Keep deterministic routing unless a deliberate replacement
      is agreed; no paid classifier is required.
- [ ] Reassess host separation and recovery targets as usage grows. High
      availability is optional unless the required uptime justifies its cost.

## Evidence and completion record

Maintain this record privately for each gate/item:

| Field | Required content |
|---|---|
| Item and status | Pending, passed, failed or explicitly deferred with reason |
| Scope | Source commit, image digests, tested mode and synthetic workload |
| Evidence | Dated command/result or redacted screenshots and measurements |
| Owner | Person responsible for resolving or accepting the item |
| Limitation | Untested behavior, residual exposure and follow-up deadline |

Do not mark a live acceptance item passed from a unit test or mock result.
Any deployment-readiness statement must name the completed gates, intended user
scope and accepted limitations. Keep deployment-specific evidence out of this
generic repository.
