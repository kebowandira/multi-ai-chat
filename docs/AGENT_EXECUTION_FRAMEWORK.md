# Future agent execution and local inference framework

Recorded: 17 October 2026.
Source reviewed: owner's Drive handoff, Hermes-Ollama-Qwen-Multi-AI-Handoff-2026-10-17.md.
This is a curated architecture reference, not implemented capability.
Implementation remains paused for the owner's weekend. Current Jules router/
deployment integration assignment is unchanged.

## Relationship to the existing platform

| Layer | Role | Status |
| --- | --- | --- |
| LibreChat | Chat UI and provider selection | Existing source baseline; runtime validation separate |
| LiteLLM and deterministic router | Model access, task category selection and fallback | Reviewed source; combined integration pending |
| Hermes Agent | Optional bounded task execution and tool orchestration | Future integration proposal |
| Ollama | Optional local inference service | Future integration proposal |
| Small Qwen model | Limited offline/local fallback | Candidate, not benchmarked |
| Git and gh | Local checkout, verification and draft PR workflow | Proposed agent tools |
| GitHub MCP | Structured repository operations | Optional alternative/complement |
| Aider | Focused terminal code editing | Defer until core agent workflow works |
| Jules | Explicitly scoped implementation assignments | Existing owner-mediated workflow |

Installing an agent or model does not connect these layers automatically.
A model proxy endpoint is not a task execution service.
The current text-only router aliases and token caps must not silently be
reused for tool-using Hermes sessions; define and test a separate capable
route/endpoint contract before wiring them together.

## Useful principles incorporated

- Use capable cloud models for substantial coding and reasoning.
- Consider task capability AND availability when choosing fallback.
- An HTTP-success response is not evidence of correct task execution.
- Small local models may handle short summaries, extraction and bounded
  classification; do not assume reliable multi-file debugging or long tool loops.
- Start with read-only repository exercises, then established test commands,
  before allowing bounded edits and draft PRs.
- Keep Jules as the default coding delegate; coordinator supplies scope,
  evidence requirements and review.
- Aider is optional, not a prerequisite for Hermes or Ollama.
- One local inference request at a time is a starting proposal to measure,
  not a verified capacity setting.

## Candidate models from the handoff

qwen3:0.6b, qwen2.5-coder:0.5b and qwen2.5-coder:1.5b are evaluation candidates.
The handoff lists download sizes, not measured runtime RAM.
No head-to-head benchmark or successful Hermes tool-call trial is established.
Do not select a production default solely from parameter count or download size.
Recheck current model metadata, license and installed-version compatibility
before choosing. Generic claims about model-family tool support do not prove
the exact model/tag can execute this agent workflow reliably.

The handoff cites a 64,000-token Hermes context guideline. Treat this as an
unverified version-dependent upstream recommendation, not a deployment setting.
Measure actual prompt/tool-schema size, context memory and CPU latency first.

## Proposed task bridge contract

A future authenticated bridge could accept bounded tasks and return task IDs.
It needs explicit queued/running/succeeded/failed/cancelled states, execution
deadlines, cancellation, concurrency limits and durable results.
Display command exit codes, test counts, source revision and draft PR link.
Treat repository/log/tool content as untrusted data, not authorization.
Keep repository credentials outside model prompts, use least-privilege access,
and execute in isolated working copies with explicit command/repository scope.
No arbitrary shell execution should be exposed through an ordinary chat endpoint.
These are requirements to design/test, not claims of existing behavior.

## Local fallback evaluation

Use synthetic tasks before real repository writes:
1. Short log summary with known expected facts.
2. Structured extraction with schema validation.
3. Tool selection and exact argument formatting.
4. Interpretation of command exit status, including negative cases.
5. Honest failure/uncertainty reporting.
6. Timeout and unavailable-provider handling.
Measure peak resident memory, context size, CPU load, first-token latency,
total latency and result correctness. A successful model load alone is insufficient.
Keep tool execution disabled for an unvalidated local fallback.

## Relationship to monitoring reference

See AI_GATEWAY_REFERENCE.md.
A future operations view can show task status alongside provider/model,
latency, tokens, fallback events and estimated cost.
Separate subscription quota, token estimates and actual provider invoices.
Raw prompts, credentials and command output containing secrets should not
become default telemetry.

## Future sequence after current integration

1. Review and validate combined router/deployment source.
2. Inspect actual host resources and installed versions in the private ops workflow.
3. Verify one cloud-backed read-only agent task.
4. Verify GitHub access and established test execution.
5. Evaluate local inference in isolation within a measured resource budget.
6. Permit narrowly scoped draft PR work after execution checks pass.
7. Add a task bridge and operations view only after their interfaces are specified.

Host identity, sizing history, credentials and installation state remain
operational context outside this public framework. No new server purchase,
installation, authentication, model pull, task bridge, auto-delegation or
deployment is authorized or performed by this reference capture.

## Evidence and sources

The owner-supplied handoff was read in full on 17 October 2026.
Its capability assessments are engineering proposals, not new benchmark results.
Its listed external sources were not independently revalidated in this capture:
- https://hermes-agent.nousresearch.com/docs/guides/local-ollama-setup
- https://hermes-agent.nousresearch.com/docs/integrations
- https://ollama.com/library/qwen3:0.6b
- https://ollama.com/library/qwen2.5-coder:0.5b
- https://ollama.com/library/qwen2.5-coder:1.5b
- https://aider.chat/
- https://aider.chat/docs/llms/ollama.html
- https://cli.github.com/manual/gh_auth_login
- https://cli.github.com/manual/gh_repo_clone

Revalidate the relevant primary documentation before implementation.
