import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from router.policy import (  # noqa: E402
    Policy,
    RoutingError,
    anchor_message,
    classify_text,
    enforce_input_limit,
    resolve_candidates,
    resolve_route,
    strip_anchor_prefix,
    strip_prefix,
)


def load_policy() -> Policy:
    return Policy.load()


class StripPrefixTests(unittest.TestCase):
    def test_strips_known_prefix(self):
        route, rest = strip_prefix("/coding refactor this function")
        self.assertEqual(route, "coding")
        self.assertEqual(rest.strip(), "refactor this function")

    def test_no_prefix_returns_none(self):
        route, rest = strip_prefix("just a normal message")
        self.assertIsNone(route)
        self.assertEqual(rest, "just a normal message")

    def test_empty_string(self):
        self.assertEqual(strip_prefix(""), (None, ""))


class ClassifyTextTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()

    def test_coding_keyword(self):
        self.assertEqual(classify_text("Debug this MQL5 function.", self.policy), "coding")

    def test_research_keyword_indonesian(self):
        self.assertEqual(classify_text("Riset pasar Indonesia.", self.policy), "research")

    def test_cheap_default(self):
        self.assertEqual(classify_text("Summarize this paragraph.", self.policy), "cheap")

    def test_unmatched_falls_back_to_default_route(self):
        self.assertEqual(classify_text("hello there", self.policy), self.policy.default_route)

    def test_coding_precedes_research_when_both_could_match(self):
        # "compare" is a research keyword; "refactor" is a coding keyword.
        # Coding rules are listed first in routing-policy.json, so they win.
        text = "Please compare and refactor this function."
        self.assertEqual(classify_text(text, self.policy), "coding")


class AnchorTests(unittest.TestCase):
    def test_anchor_is_first_user_message(self):
        messages = [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "/coding fix this bug"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "continue"},
        ]
        self.assertEqual(anchor_message(messages)["content"], "/coding fix this bug")

    def test_no_user_message_returns_none(self):
        self.assertIsNone(anchor_message([{"role": "system", "content": "x"}]))


class ResolveRouteTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()
        self.known_routes = set(self.policy.routes)

    def test_follow_up_does_not_change_tier(self):
        messages = [
            {"role": "user", "content": "/coding fix this bug"},
            {"role": "assistant", "content": "done"},
            {"role": "user", "content": "continue"},
        ]
        self.assertEqual(resolve_route(messages, self.policy, self.known_routes), "coding")

    def test_classification_used_when_no_prefix(self):
        messages = [{"role": "user", "content": "Debug this Python script."}]
        self.assertEqual(resolve_route(messages, self.policy, self.known_routes), "coding")

    def test_unknown_prefix_falls_back_to_classification(self):
        messages = [{"role": "user", "content": "/notaroute Summarize this paragraph."}]
        self.assertEqual(resolve_route(messages, self.policy, self.known_routes), "cheap")

    def test_empty_conversation_returns_default(self):
        self.assertEqual(resolve_route([], self.policy, self.known_routes), self.policy.default_route)


class StripAnchorPrefixTests(unittest.TestCase):
    def test_removes_prefix_from_anchor_only(self):
        messages = [
            {"role": "user", "content": "/cheap rewrite this email"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "/cheap again"},
        ]
        out = strip_anchor_prefix(messages)
        self.assertEqual(out[0]["content"], "rewrite this email")
        self.assertEqual(out[2]["content"], "/cheap again")  # only the anchor is touched


class LimitsTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()

    def test_under_limit_ok(self):
        enforce_input_limit([{"role": "user", "content": "hello"}], self.policy)

    def test_over_limit_raises(self):
        huge = "x" * (self.policy.max_input_chars + 1)
        with self.assertRaises(RoutingError):
            enforce_input_limit([{"role": "user", "content": huge}], self.policy)


class ResolveCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.policy = load_policy()

    def test_filters_to_available(self):
        candidates = resolve_candidates("coding", self.policy, available={"openai-main"})
        self.assertEqual(candidates, ["openai-main"])

    def test_raises_when_nothing_available(self):
        with self.assertRaises(RoutingError):
            resolve_candidates("coding", self.policy, available=set())

    def test_preserves_policy_order(self):
        candidates = resolve_candidates(
            "coding", self.policy, available={"openai-main", "claude-code", "deepseek-fast"}
        )
        self.assertEqual(candidates, ["claude-code", "deepseek-fast", "openai-main"])


if __name__ == "__main__":
    unittest.main()
