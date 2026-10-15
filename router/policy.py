"""Deterministic, text-only routing policy.

No model call, no embedding, no external classifier: a regex pass over the
anchor message plus an explicit-prefix override. Loaded both by the LiteLLM
hook (router/custom_router.py) and by tests/test_policy.py.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

POLICY_PATH = Path(__file__).parent / "routing-policy.json"

_PREFIX_RE = re.compile(r"^\s*/(?P<route>[a-zA-Z][\w-]*)\b\s*")


class RoutingError(ValueError):
    pass


@dataclass(frozen=True)
class Policy:
    routes: dict
    default_route: str
    max_input_chars: int
    max_output_tokens: int
    rules: list  # list of (route, compiled_pattern)

    @classmethod
    def load(cls, path: Path = POLICY_PATH) -> "Policy":
        raw = json.loads(path.read_text(encoding="utf-8"))
        rules = [
            (r["route"], re.compile(r["pattern"]))
            for r in raw["classification_rules"]
        ]
        return cls(
            routes=raw["routes"],
            default_route=raw["default_route"],
            max_input_chars=raw["limits"]["max_input_chars"],
            max_output_tokens=raw["limits"]["max_output_tokens"],
            rules=rules,
        )


def strip_prefix(text: str) -> tuple[Optional[str], str]:
    """Split a leading ``/route`` token off a message, if present."""
    if not text:
        return None, text
    match = _PREFIX_RE.match(text)
    if not match:
        return None, text
    return match.group("route").lower(), text[match.end():]


def classify_text(text: str, policy: Policy) -> str:
    """Apply classification rules in file order; fall back to default_route."""
    for route, pattern in policy.rules:
        if pattern.search(text or ""):
            return route
    return policy.default_route


def anchor_message(messages: list[dict]) -> Optional[dict]:
    """The earliest user message in the conversation.

    Anchoring on the earliest (not latest) user message is what keeps a
    follow-up like "continue" from silently changing the selected tier.
    """
    for message in messages:
        if message.get("role") == "user":
            return message
    return None


def _as_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
        return "\n".join(parts)
    return ""


def resolve_route(messages: list[dict], policy: Policy, known_routes: set[str]) -> str:
    """Resolve the alias a conversation should use.

    An explicit ``/route`` prefix on the anchor message always wins, provided
    it names a real configured route; otherwise the message is classified.
    """
    anchor = anchor_message(messages)
    if anchor is None:
        return policy.default_route
    text = _as_text(anchor.get("content"))
    prefix_route, _ = strip_prefix(text)
    if prefix_route and prefix_route in known_routes:
        return prefix_route
    return classify_text(text, policy)


def strip_anchor_prefix(messages: list[dict]) -> list[dict]:
    """Return a shallow copy of ``messages`` with the anchor's ``/route`` prefix removed."""
    out = list(messages)
    for i, message in enumerate(out):
        if message.get("role") == "user":
            text = _as_text(message.get("content"))
            route, rest = strip_prefix(text)
            if route:
                out[i] = {**message, "content": rest.lstrip()}
            break
    return out


def enforce_input_limit(messages: list[dict], policy: Policy) -> None:
    total = sum(len(_as_text(m.get("content"))) for m in messages)
    if total > policy.max_input_chars:
        raise RoutingError(
            f"input is {total} characters, over the {policy.max_input_chars}-character router limit; "
            "use a direct provider endpoint for long-context requests"
        )


def enforce_output_limit(data: dict, policy: Policy) -> None:
    max_tokens = data.get("max_tokens")
    if max_tokens is None:
        max_tokens = data.get("max_completion_tokens")
    if max_tokens is not None and isinstance(max_tokens, int) and max_tokens > policy.max_output_tokens:
        raise RoutingError(
            f"requested max output tokens ({max_tokens}) exceeds the {policy.max_output_tokens}-token router limit; "
            "use a direct provider endpoint for larger generation limits"
        )


def enforce_text_only(data: dict) -> None:
    if data.get("tools") or data.get("tool_choice") or data.get("functions") or data.get("function_call"):
        raise RoutingError(
            "route aliases support plain text only; tool/function calling is not permitted on router aliases, use a direct endpoint"
        )
    if data.get("response_format"):
        raise RoutingError(
            "route aliases support plain text only; structured outputs (response_format) are not permitted on router aliases, use a direct endpoint"
        )
    messages = data.get("messages", [])
    for m in messages:
        if not isinstance(m, dict):
            continue
        if m.get("role") in ("tool", "function") or m.get("tool_calls") or m.get("function_call") or m.get("tool_call_id"):
            raise RoutingError(
                "route aliases support plain text only; tool history is not permitted on router aliases, use a direct endpoint"
            )
        content = m.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type")
                    if item_type and item_type != "text":
                        raise RoutingError(
                            f"route aliases support plain text only; content type '{item_type}' is not permitted on router aliases, use a direct endpoint"
                        )


def resolve_candidates(route: str, policy: Policy, available: set[str]) -> list[str]:
    """Ordered candidate model names for ``route``, filtered to configured providers."""
    candidates = policy.routes.get(route, [])
    filtered = [m for m in candidates if m in available]
    if not filtered:
        raise RoutingError(f"no configured provider is available for route '{route}'")
    return filtered
