# Self-hosted multi-AI workspace

Start with **[docker-compose.yml](docker-compose.yml)** and **[librechat.yaml](librechat.yaml)**. The first defines the seven-service stack; the second defines the native and custom providers. Both are fully included in this package. Then follow the deployment procedure below.

Prepared for Ubuntu 24.04, a single VPS, and a private individual/small team. This is a production-oriented deployment baseline, not a claim that your server, credentials, OAuth, or provider integrations have already passed live acceptance.

This repository is the generic, reusable boilerplate: the compose stack, provider routing, and deployment scripts. It has no deployment-specific state in it. If you're tracking a real deployment (domain, provider accounts, acceptance checklist, agent handover notes), keep that in a separate private repository alongside this one — see `docs/OPERATIONS.md` for the split this project assumes.

## What you get

| Component | Purpose | Publicly exposed? |
|---|---|---|
| Caddy | HTTPS, automatic certificate renewal, streaming reverse proxy | TCP 80/443; UDP 443 |
| LibreChat | ChatGPT-style UI, saved conversations, authentication | Through Caddy only |
| MongoDB | Users, conversations, application records | No; authenticated, private network |
| Meilisearch | Conversation search | No; master key, private network |
| RAG API | Document parsing and local CPU embeddings | No; shared JWT verification |
| PostgreSQL + pgvector | RAG vectors | No; password, private network |
| LiteLLM, optional | Direct-provider model gateway, policy routing, fallbacks | No; private application key |

No Kubernetes, paid gateway, broker markup, hosted search subscription, or paid embedding service is required. Model requests go to official provider endpoints. The supplied chat platform does not train or host the large chat models.

**Three limitations must be understood before deployment:**

1. OpenAI API usage is separate from ChatGPT Plus/Pro, as is API access versus consumer subscriptions at other providers. Free chat websites do not establish free API access. Trials, quotas, and model availability depend on the account and region. VPS/domain/backup costs remain.
2. MongoDB Community is free to self-host but uses SSPL, which is not OSI-approved. Consequently **LibreChat + MongoDB cannot meet a literal “every component is OSI open source” requirement**. This bundle preserves your requested MongoDB stack and explicitly records that exception. Replacing it with an unverified compatibility layer is not presented as production-ready. If OSI-only licensing is mandatory, this architecture needs a database compatibility evaluation or a different chat platform. No commercial MongoDB or LiteLLM feature is required here.
3. `research` is a routing label, not an autonomous browsing or citation-verification agent. It selects Gemini for analysis. Live web search, provider research products, tools, image generation, and code execution are not enabled by this baseline.

## Project structure

```text
multi-ai-chat/
  docker-compose.yml          # Service definitions and network isolation
  librechat.yaml              # Editable provider/UI source template
  litellm_config.yaml         # Editable model inventory and fallback examples
  .env.example               # All deployment inputs and explanations
  .gitignore
  .gitattributes
  Caddyfile
  LICENSE
  README.md
  AGENTS.md                  # Shared coding-agent instructions
  SOURCE_FILES.txt           # Initial Git upload allowlist
  requirements-dev.txt       # Local validation dependencies
  mongo-init/01-user.js       # Least-privilege LibreChat database user
  router/
    __init__.py
    routing-policy.json      # Ordered preferences and editable classification rules
    policy.py                # Text-only, deterministic routing logic
    custom_router.py         # LiteLLM hook
  scripts/
    common.py
    init-env.py               # Generate unique secrets once
    configure.py              # Compile/prune active configs
    preflight.py
    pin-images.py             # Resolve image digests without starting services
    deploy.sh
    backup.py                 # Cold, consistent backup; encrypted with restic
    gateway-smoke.py           # Auth/models checks; optional billable inference
    check_source.py            # Source publication guard
  tests/
    test_policy.py
    test_config.py
    integration_gateway.py    # Actual LiteLLM process with local mock provider
  docs/
    OPERATIONS.md
    SOURCES.md
```

A deployment-specific private repo (your domain, provider accounts, agent
handover notes, acceptance evidence) is expected to sit alongside this one,
typically pulling it in as a git submodule. See `docs/OPERATIONS.md`.

Generated on your VPS, excluded from Git: `.env`, `runtime/`, `docker-compose.override.yml`, `image-lock.json`, and `backups/`. The generated YAML contains secret references; generated `.env` files contain real credentials and must remain private. Edit the source templates, not files in `runtime/`.

## 1. Prepare the VPS and domain

Use a dedicated Ubuntu 24.04 VPS or an existing host with sufficient **spare** capacity. Do not place this stack on a trading execution VPS without measuring isolation and resource headroom. You do not need a GPU or a home MiniPC.

These are engineering estimates for a few users, not measured load benchmarks:

| Deployment | CPU | RAM | SSD | Notes |
|---|---:|---:|---:|---|
| Light use, remote embeddings | 2 vCPU | 4 GB | 40–60 GB | Tight; avoid concurrent ingestion; remote embeddings are billable |
| Full supplied stack with CPU-local embeddings | 4 vCPU | 8 GB | 80 GB | Practical starting minimum |
| Comfortable small team / more documents | 4–8 vCPU | 16 GB | 120–160 GB | Recommended; tune after measuring |

Allow additional free disk for upgrades and one complete uncompressed logical data footprint during backup. Large Docker images, uploads, vectors, and the Hugging Face cache can grow substantially. Add a small emergency swap file if needed; swap is not a substitute for RAM. MongoDB's x86-64 image requires an AVX-capable CPU; choose a modern x86-64 VPS, or verify every image's ARM64 support before selecting ARM.

Create an `A` record, for example `chat.yourdomain.com`, pointing to the VPS. Add `AAAA` only if IPv6 is actually configured and reachable. Ensure ports 80 and 443 are unused and reachable. Use DNS-only mode initially if your DNS vendor offers a proxy/CDN; this Caddy configuration assumes it directly receives the client connection.

Use SSH keys. Before changing firewall/SSH settings, keep the current session open and test a second session. On a fresh server using SSH port 22:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git unzip python3 python3-yaml python3-dotenv ufw restic
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw enable
sudo ufw status
```

If SSH uses another port, allow that port **before** enabling UFW. Restrict SSH to your administrator IP using the VPS provider firewall when practical. Apply equivalent IPv6 firewall rules. Docker-published ports can bypass ordinary UFW rules; this project publishes only Caddy, and the provider firewall should also allow only SSH and web ports. Never add database or LiteLLM host ports as a troubleshooting shortcut.

## 2. Install Docker Engine and Compose

Use Docker's official Ubuntu repository. On a host with an existing container installation, check the official prerequisite/conflicting-package guidance before replacing packages.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

Require **Compose 2.30 or newer** for `env_file: format: raw`; newer compatible versions are fine. For the remaining commands, use a trusted operator account with Docker access, or a root administrative shell. Membership in the `docker` group is effectively root access. Do not grant it to ordinary chat users. This guide does not install Docker Desktop or require its subscription.

## 3. Install the project

Transfer the ZIP to the VPS and unpack it:

```bash
sudo install -d -m 0750 -o "$USER" -g "$(id -gn)" /opt/multi-ai-chat
unzip multi-ai-chat-claude-handover-2026-10-08.zip -d /tmp/multi-ai-chat-extract
cp -a /tmp/multi-ai-chat-extract/multi-ai-chat/. /opt/multi-ai-chat/
cd /opt/multi-ai-chat
chmod 750 scripts/deploy.sh
python3 scripts/init-env.py
```

Alternatively, commit the unpacked source files to your own **private** repository and clone it to `/opt/multi-ai-chat`. No repository has been created by this package. Review `.gitignore` before your first commit. Do not commit generated secrets, raw backups, or deployment credentials.

## 4. Configure your environment

Edit `.env` using an editor on the VPS:

```bash
nano .env
chmod 600 .env
```

Set `CHAT_DOMAIN`, `ACME_EMAIL`, and API keys for the providers you want. You may start with only one provider. Leave unavailable provider keys blank; configuration removes them automatically. Keep the generated database/JWT/encryption secrets. They are unique to your deployment.

| Provider | Key variable | Initial model IDs | Integration |
|---|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-6.1-sol`, `gpt-6-luna` | Native |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-5-5` | Native |
| Google Gemini | `GOOGLE_KEY` | `gemini-3.8-flash`, `gemini-3.5-flash-lite` | Native |
| DeepSeek | `DEEPSEEK_API_KEY` | `deepseek-flash`, `deepseek-v4-pro` | Official OpenAI-compatible API |
| Qwen | `DASHSCOPE_API_KEY` | `qwen-turbo`, `qwen-plus` | Official Model Studio endpoint |
| Z.ai | `ZAI_API_KEY` | `glm-5.3` | Official API, manual route by default |
| xAI | `XAI_API_KEY` | `grok-4.7` | Official OpenAI-compatible API |

Model IDs are configurable in `.env`; they are documentation-grounded examples, not a guarantee that your account has access. See [sources and version notes](docs/SOURCES.md). Avoid copying old `deepseek-chat`/`deepseek-reasoner` examples; their retirement is documented. Qwen keys and endpoints must match your region/workspace. Replace `YOUR_WORKSPACE_ID` in `DASHSCOPE_BASE_URL` using the URL shown in your Model Studio console. Do not mix a China-region key with a Singapore endpoint.

Z.ai uses the ordinary API endpoint here, not a coding-plan subscription endpoint. Grok is not assumed to be free or automatically cheaper. The current GLM flagship is registered but excluded from the budget pool until you choose and verify a suitable low-cost GLM model.

`COMPOSE_PROFILES=router` enables LiteLLM. Set it to an empty value for direct-provider-only mode. No LiteLLM service is required for the native/custom direct endpoints. Rerunning the deployment script removes the SmartRouter UI entry when disabled. If a previously running LiteLLM container remains after disabling the profile, explicitly stop it with `docker compose --profile router stop litellm`; this never deletes data.

RAG defaults to local `all-MiniLM-L6-v2` embeddings on CPU. The first startup must reach Hugging Face to download model files; subsequent starts reuse `hf_cache`. This compact embedding model is mainly suited to English; evaluate multilingual retrieval using your actual Indonesian documents before adopting it for those documents. Local embeddings avoid an embedding API fee, but retrieved document excerpts still go to the selected cloud chat provider and consume its input tokens.

For a smaller VPS, set `EMBEDDINGS_PROVIDER=openai`, `EMBEDDINGS_MODEL=text-embedding-3-small`, and `RAG_OPENAI_API_KEY`. You may switch `RAG_IMAGE` to the upstream `librechat-rag-api-dev-lite:latest` image **before pinning** when local embeddings are not needed. Remote embeddings incur API usage charges. Changing an embedding model on existing data requires a planned reindex; see operations.

## 5. Generate configuration, pin images, start

```bash
python3 scripts/preflight.py
python3 scripts/configure.py
python3 -m unittest discover -s tests -v
python3 scripts/pin-images.py
./scripts/deploy.sh
docker compose ps
```

`pin-images.py` pulls official candidate images and records immutable registry digests in a Compose override and `image-lock.json`. It includes LiteLLM even if its profile is disabled, so subsequent enabling is also pinned. It does not start containers. Upstream LibreChat's documented images are rolling development channels, not a certified stable suite. The lock makes the chosen artifacts reproducible; **you must still review release notes/security advisories and pass the acceptance checks**. Substitute an upstream supported release reference in `.env` if available to you, then resolve and test it.

The deployment script validates the Caddy config and waits for service health. First RAG startup can take several minutes. It recreates containers to ensure regenerated environment and mounted files are applied. `docker compose restart` alone does not reliably apply changed environment variables.

Only Caddy is reachable from the internet. It obtains and renews certificates automatically and redirects HTTP to HTTPS. No separate Certbot job is needed. Its certificate state is persistent. Check startup errors with:

```bash
docker compose logs --tail 100 caddy librechat rag_api
```

Do not paste logs publicly without checking for credentials, prompts, and personal information. Avoid `docker compose config` without `-q`: expanded output includes secrets.

## 6. Create the first account safely

Public email and social registration are disabled from the beginning. Create a verified local account with LibreChat's interactive maintenance command:

```bash
docker compose exec librechat npm run create-user
```

Enter your email, display name, username, and a strong unique password. Mark the account verified because you are provisioning it as the operator. Do not leave the password blank, and do not supply it as a command-line argument. Then open `https://YOUR_CHAT_DOMAIN` and sign in. The included platform does not expose a separate administration web service; maintenance uses SSH/CLI.

Create further accounts with the same command. Keep registration closed. Password reset by email is disabled until a real SMTP service has been configured and tested; an operator can use the installed LibreChat password-reset maintenance command (`npm run reset-password`) after checking its prompts. Preserve operator access and backups.

## 7. Optional Google / GitHub sign-in

OAuth signs users into LibreChat. It does not authorize model API billing and does not connect consumer ChatGPT/Claude subscriptions.

For Google, create a project and OAuth web application in Google Cloud Console. Configure the consent screen and the permitted/test users or your Workspace audience. Set the authorized JavaScript origin to `https://YOUR_CHAT_DOMAIN` and redirect URI to:

```text
https://YOUR_CHAT_DOMAIN/oauth/google/callback
```

Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `ALLOW_SOCIAL_LOGIN=true` in `.env`. Callback path variables are already generated for you.

For GitHub, follow LibreChat's current GitHub App instructions: create the app under Developer Settings, set the homepage to your chat URL, set the callback below, disable webhooks, and grant read-only email-address access. Generate a client secret and set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`:

```text
https://YOUR_CHAT_DOMAIN/oauth/github/callback
```

Keep `ALLOW_SOCIAL_REGISTRATION=false`. Provision an account specifically for the selected provider using the operator CLI, for example:

```bash
docker compose exec librechat npm run create-user -- --provider=google
# OR for GitHub:
docker compose exec librechat npm run create-user -- --provider=github
./scripts/deploy.sh
```

Use the provider's verified email. Set a strong random password when the CLI prompts even for provider accounts. The exact provider-account/linking behavior must be verified on the locked LibreChat image before relying on OAuth. Do not assume that a local account with a matching email will auto-link. If your image rejects a pre-provisioned social account, inspect its current account-linking documentation; do not solve the issue by enabling unrestricted public social registration. Use a separate browser session to test permitted and unprovisioned users, while retaining a working local operator account.

`registration.allowedDomains` in `librechat.yaml` can further restrict corporate accounts. Allowing `gmail.com` does not restrict access to *your* Gmail account. OAuth provider MFA is strongly recommended.

## 8. Routing behavior and examples

Choose **SmartRouter** in LibreChat. All configured gateway provider aliases plus the available routing modes appear. A route disappears if none of its candidate keys are configured; `auto` appears only when the default budget route is available.

| Selection | First choice when configured | Ordered fallback |
|---|---|---|
| `coding` | Claude | DeepSeek Flash → OpenAI main |
| `research` | Gemini Flash | OpenAI main |
| `cheap` | Qwen Turbo | DeepSeek Flash → OpenAI low-cost → Gemini Flash-Lite |
| `auto` | Rule applied to the first user message | Fallback list for the selected route |
| Direct alias, e.g. `glm-manual` | Exactly that model | None configured |

Absent API keys are removed **before** routing, so the first configured candidate becomes primary. Changing the task/model can change answer quality, context behavior, and destination provider. Fallback sends the conversation to another provider; use a direct endpoint when the data must stay with one provider.

Examples for `auto`:

```text
/coding Refactor this Python function and explain the changes.
/research Compare the arguments in these two supplied documents.
/cheap Rewrite this sales email professionally.
Debug this MQL5 function.          # coding keyword rule
Riset pasar Indonesia.            # research keyword rule
Summarize this paragraph.         # cheap default
```

The first user message anchors classification, so a routine follow-up such as “continue” does not unexpectedly change the tier. Prefixes are removed before sending the first message upstream. Explicit UI route selection takes priority over a prompt prefix. Start a new conversation or select a different route to change the tier. If earlier history is removed/truncated, the earliest remaining user message becomes the anchor; this is not server-side durable conversation state.

Edit `router/routing-policy.json` to change priorities or regular expressions. Order matters. Coding rules currently precede research rules. Indonesian phrases can be added to the regex. This heuristic does not understand semantic quality and is not a security boundary. It is a clear, zero-classifier-cost starting policy.

To use DeepSeek before Claude for coding:

```json
"coding": ["deepseek-fast", "claude-code", "openai-main"]
```

To add GLM to a budget fallback, first choose a GLM model you have verified for current price, availability, and compatible text output, set `ZAI_MODEL`, then include `glm-manual` at the desired position in `cheap`. Do not label an expensive flagship “cheap” solely because of its provider name.

To route based on actual cost, calculate a workload-specific estimate:

```text
estimated request cost = input_tokens × input_price_per_million / 1,000,000
                       + output_tokens × output_price_per_million / 1,000,000
```

Account for cached tokens, reasoning tokens, discounts, and extra tools separately. Reorder `cheap` using current provider pricing and your observed input/output mix. This package intentionally does not ship stale prices or pretend that ordered preference is a live price optimizer. LiteLLM's cost-based strategies require trustworthy price metadata and a deliberate same-group deployment setup; adopt those only after testing your workload.

Route aliases accept **plain text only** and enforce 48,000 input characters and up to 4,096 output tokens. These are conservative limits, not an exact tokenization guarantee. They reject images, files, tool histories, and structured-output requests instead of forwarding them to incompatible fallback models. Use native/direct endpoints for those capabilities. Direct provider aliases are not subject to these router caps; set provider budgets and UI limits accordingly.

LiteLLM retries a failed call once, then uses the configured ordered fallback chain. Some errors (especially context-window/content-policy failures) have separate handling and intentionally have no configured fallback here. A failure after streaming has begun cannot generally be transparently recovered without duplicating or corrupting output; retry it as a new request. Failed/retried requests may still be billed. Selecting `research` does not enable live browsing.

## 9. Add another OpenAI-compatible provider

1. Confirm the vendor's official HTTPS base URL, model ID, and API key type. OpenAI-compatible chat completion APIs commonly end their base URL in `/v1`; avoid duplicating `/chat/completions`.
2. Add literal variables to `.env`, for example `NEWAI_API_KEY`, `NEWAI_BASE_URL`, and `NEWAI_MODEL`. Include empty/example equivalents in `.env.example` for future deployments; keep real keys out of Git.
3. Append this under `endpoints.custom` in `librechat.yaml`:

```yaml
- name: NewAI
  apiKey: "${NEWAI_API_KEY}"
  baseURL: "${NEWAI_BASE_URL}"
  models:
    default: ["${NEWAI_MODEL}"]
    fetch: false
  titleConvo: false
  modelDisplayLabel: New AI
```

4. Optionally register it under `model_list` in `litellm_config.yaml`:

```yaml
- model_name: newai-chat
  litellm_params:
    model: openai/${NEWAI_MODEL}
    api_base: ${NEWAI_BASE_URL}
    api_key: os.environ/NEWAI_API_KEY
```

5. Optionally add `newai-chat` to a routing preference list. The generator discovers key references and passes only needed keys to the relevant containers.
6. Run `./scripts/deploy.sh`, then test direct text, streaming, error handling, and any required capabilities before adding real workloads. Use `fetch: true` only after confirming that provider's `/models` implementation.

For a non-OpenAI-compatible protocol, use a supported native provider/SDK adapter rather than merely changing `baseURL`.

## 10. Acceptance before normal use

Complete all of these on your actual VPS:

- `docker compose ps`: all enabled services are up and healthy. Reboot the VPS and confirm automatic recovery. `unless-stopped` respects an explicit administrator stop; health status alone does not cause Docker to restart a hung process.
- HTTPS works with a valid certificate; HTTP redirects. A scan from another machine shows no 3080, 4000, 7700, 8000, 27017, or 5432 listener accessible from the internet.
- The operator can log in; public email/social signup is denied. Unauthorized users cannot retrieve another user's files or conversations. Verify OAuth acceptance/rejection if enabled.
- Send one short request through each enabled direct endpoint. Check the actual provider billing console and returned model. Test streaming in the browser.
- Upload a harmless sample document through a direct RAG-capable endpoint, ask a factual question about it, and verify the answer. Check that a second user cannot retrieve the document.
- Test the gateway auth and model catalog without billable inference:

```bash
docker compose --profile router exec -T litellm python - < scripts/gateway-smoke.py
```

- Optional real inference tests **consume API tokens**:

```bash
docker compose --profile router exec -T litellm python - --call auto --prompt '/cheap Reply OK.' < scripts/gateway-smoke.py
docker compose --profile router exec -T litellm python - --call coding --stream < scripts/gateway-smoke.py
```

- On a separate staging deployment, deliberately point a route's primary `api_base` to an unreachable **local** endpoint or use a mock server, while preserving a valid fallback. Verify the next configured model succeeds. Do not intentionally break production credentials. Test a failure after streaming starts and confirm that the UI reports an error.
- Complete a backup and restore drill using [OPERATIONS.md](docs/OPERATIONS.md).

No provider test is run automatically on startup. Liveness checks do not call billable `/health` model probes.

## Security and maintenance essentials

Keep `.env` and `runtime/*.env` mode 600 and the project operator-controlled. Docker administrators can read container environment variables; `.env` is not a secret vault. Use dedicated provider project keys, least available scope, spending caps where supported, and billing alerts. An alert is not a guaranteed hard spending stop.

Keep signup closed and users trusted. A shared server-side API key means approved users spend from your account, including direct endpoints that bypass router policy. This baseline is not a metered public API business. Durable per-user budgets/keys require an expanded gateway design with a database and, for multiple workers, shared state; no such guarantee is implied here.

Application message/login/upload limits are configured. They are single-replica controls, not DDoS protection or a monetary quota. Caddy's standard build has no rate-limit plugin in this package. Use the VPS provider firewall and upstream network protection where needed. Do not enable arbitrary tools/MCP, code execution, public sharing, or remote URL fetch features without reviewing their access and network implications.

Chats and documents are stored on your VPS, but cloud providers receive their prompts and any included excerpts. No end-to-end encryption from the server operator is claimed. Use encrypted off-host backups, review data retention and provider policies, and avoid verbose request logging. Do not mount the Docker socket or your host home directory into LibreChat.

Check OS security updates routinely. Review upstream releases, back up, test image updates on staging, then intentionally regenerate the image lock. Never use an unattended image-updater against this database-backed stack. See operations for backups, restore, monitoring, upgrades, and rollback.
