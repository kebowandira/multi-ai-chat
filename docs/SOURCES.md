# Sources and version notes

Model IDs and endpoints in this package were carried over from the original
handover package (prepared 7–8 October 2026) as documentation-grounded
placeholders. They are not a guarantee of availability on your account or
region. Recheck each before deployment:

| Provider | Variable(s) | Placeholder value(s) | Recheck against |
|---|---|---|---|
| OpenAI | `OPENAI_MODELS` | `gpt-6.1-sol`, `gpt-6-luna` | OpenAI's model list for your account/API tier |
| Anthropic | `ANTHROPIC_MODELS` | `claude-sonnet-5-5` | Anthropic's current model catalog |
| Google | `GOOGLE_MODELS` | `gemini-3.8-flash`, `gemini-3.5-flash-lite` | Google AI Studio / Vertex model list |
| DeepSeek | `DEEPSEEK_FAST_MODEL`, `DEEPSEEK_PRO_MODEL` | `deepseek-flash`, `deepseek-v4-pro` | DeepSeek API docs — avoid the retired `deepseek-chat`/`deepseek-reasoner` names |
| Qwen | `QWEN_TURBO_MODEL`, `QWEN_PLUS_MODEL` | `qwen-turbo`, `qwen-plus` | Alibaba Model Studio, your workspace region |
| Z.ai | `ZAI_MODEL` | `glm-5.3` | Z.ai API pricing/availability page before adding to the `cheap` pool |
| xAI | `XAI_MODEL` | `grok-4.7` | xAI API docs |

## Image versions

`docker-compose.yml` pins images by tag, not digest. `scripts/pin-images.py`
resolves and locks digests into `image-lock.json` /
`docker-compose.override.yml` — run it, then separately check each
upstream project's release notes/security advisories before trusting the
lock in production:

- LibreChat: https://github.com/danny-avila/LibreChat (dev-channel image)
- LiteLLM: https://github.com/BerriAI/litellm
- Caddy: https://github.com/caddyserver/caddy
- MongoDB: https://www.mongodb.com/docs/manual/release-notes/
- Meilisearch: https://github.com/meilisearch/meilisearch
- pgvector (ankane/pgvector image): https://github.com/pgvector/pgvector

## LiteLLM package pin used by tests/integration_gateway.py

`litellm[proxy]==1.104.0` — a candidate from the last official release
check at package-prep time, not an evergreen recommendation. If it's
unavailable or superseded, check PyPI/GitHub releases and choose a
supported replacement deliberately, then update this file and
`CLAUDE_CODE_HANDOVER.md` together.
