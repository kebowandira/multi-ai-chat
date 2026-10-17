# AI gateway design reference

Recorded: 17 October 2026, Asia/Jakarta.
Source: owner-supplied screenshots of a Threads discussion by adit4rt.
Status: reference only; implementation paused for owner's weekend.
No change to current Jules integration scope.

## Owner direction

Retain the pictured gateway dashboard as a framework/design reference.
Also retain multi-account Gemini access without provider API keys as a
possible approach to investigate, not an approved or validated implementation.

## Visible dashboard ideas

- Requests, input/output tokens, cached tokens and estimated cost.
- Date filters, recent-request table, model and request timestamps.
- Visual connection/routing flow between coding clients, gateway and backends.
- Distinguish estimated cost from actual billing; screenshot explicitly
  labels its cost estimate as not actual billing.

## Mapping to our architecture

LibreChat is the user-facing chat interface.
Optional LiteLLM plus our deterministic policy is the routing layer.
A separate operations view could show usage, latency, errors, fallback events
and model/provider routing. This dashboard is not currently implemented.
Keep monitoring distinct from chat and avoid recording raw prompts by default.

## Account-based Gemini access: research track

Screenshots contain claims about connecting multiple Google accounts to
9Router, using subscription quotas rather than conventional API keys,
token-refresh issues and possible account restrictions.
The owner described the reference as user/password access without API.
The screenshots do not establish whether actual authentication uses passwords,
OAuth, browser cookies, session tokens or another mechanism.
Do not equate a Google account login with official Gemini API entitlement.

Before proposing implementation, verify the exact upstream repository,
license, authentication flow, documented provider support, applicable access
terms, quota handling, credential storage and maintenance requirements.
Research supported sign-in integration first. Never commit credentials,
cookies, refresh/access tokens or actual account identities to this public repo.
No credential entry, account acquisition, quota-circumvention implementation,
installation or account connection is authorized by this reference note.

## Evidence limits

9Router/Antigravity/OpenCode labels, model names and commenter statements are
observations from screenshots, not independently verified technical facts.
Account longevity, free access, claimed savings, model identity and safety
are not established. Do not use screenshot token totals or estimated costs
as verified billing evidence.

## Future decision

After current reviewed router/deployment integration, assess:
1. Minimal private usage/health dashboard.
2. API-based providers and any separately verified supported account connectors.
3. Clear separation of actual billed cost, estimates and subscription quotas.

No new Jules assignment or implementation is started by this document.
