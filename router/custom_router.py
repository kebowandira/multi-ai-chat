"""LiteLLM proxy hook: rewrites the "auto" alias to a concrete route.

Registered in runtime/litellm_config.yaml as
    litellm_settings:
      callbacks: ["router.custom_router.router_logger"]

LiteLLM imports that dotted path and calls router_logger.async_pre_call_hook
on every proxy request (this is LiteLLM's documented CustomLogger plugin
interface). We only ever rewrite data["model"]; the actual fallback chain for
the resolved route is normal LiteLLM router_settings.fallbacks, compiled by
scripts/configure.py from router/routing-policy.json.
"""
from __future__ import annotations

from router.policy import (
    Policy,
    RoutingError,
    enforce_input_limit,
    resolve_route,
    strip_anchor_prefix,
)

try:
    from litellm.integrations.custom_logger import CustomLogger
except ImportError:  # pragma: no cover - exercised only inside the litellm image
    class CustomLogger:  # minimal stand-in so this module imports outside litellm
        async def async_pre_call_hook(self, *a, **k):
            raise NotImplementedError


ALIAS_ROUTES = {"auto", "coding", "research", "cheap"}


class ClassifyingRouter(CustomLogger):
    def __init__(self, policy: Policy | None = None):
        self.policy = policy or Policy.load()

    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        model = data.get("model")
        if model not in ALIAS_ROUTES:
            return data

        messages = data.get("messages", [])
        enforce_input_limit(messages, self.policy)
        data["messages"] = strip_anchor_prefix(messages)

        if model == "auto":
            data["model"] = resolve_route(messages, self.policy, known_routes=set(self.policy.routes))
        # "coding" / "research" / "cheap" selected explicitly in the UI pass through
        # unchanged; LiteLLM's own fallback chain for that model_name takes over.
        return data


router_logger = ClassifyingRouter()
