"""Tests for llm-prompt-compress.

Coverage is organized by feature:
  * LIGHT / MEDIUM / AGGRESSIVE produce expected output on known inputs
  * stats arithmetic is correct (chars, words, ratio)
  * empty + whitespace-only inputs are handled without error
  * code blocks are preserved by default and the opt-out works
  * custom rules append after built-ins
  * level monotonicity: AGGRESSIVE <= MEDIUM <= LIGHT in length
  * ratio is always in [0, 1]
  * Compressor batch reuse works
"""

from __future__ import annotations

import pytest

from llm_prompt_compress import (
    CompressionResult,
    CompressionStats,
    Compressor,
    Level,
    compress,
)

# ---------------------------- LIGHT level ----------------------------


def test_light_strips_leading_please():
    r = compress("Please help me debug this.", level=Level.LIGHT)
    assert r.text == "Help me debug this."


def test_light_strips_kindly_and_thanks():
    r = compress("Kindly review the patch, thanks!", level=Level.LIGHT)
    # politeness and trailing thanks both gone
    assert "kindly" not in r.text.lower()
    assert "thanks" not in r.text.lower()
    assert "review the patch" in r.text.lower()


def test_light_collapses_double_spaces_and_trims():
    r = compress("  hello    world  \n\n\n\n  next   line  ", level=Level.LIGHT)
    # single spaces, trimmed edges, no quadruple blank lines
    assert r.text == "Hello world\n\nnext line"


def test_light_does_not_remove_filler_verbs():
    # MEDIUM-only removal: "could you" should survive LIGHT
    r = compress("Could you summarize this paragraph?", level=Level.LIGHT)
    assert "could you" in r.text.lower()


# ---------------------------- MEDIUM level ---------------------------


def test_medium_strips_filler_verb_phrases():
    r = compress(
        "Could you please summarize the following text for me?",
        level=Level.MEDIUM,
    )
    text_lower = r.text.lower()
    assert "could you" not in text_lower
    assert "please" not in text_lower
    assert "summarize" in text_lower


def test_medium_removes_intensifiers():
    r = compress(
        "This is really very important and actually critical.",
        level=Level.MEDIUM,
    )
    text_lower = r.text.lower()
    for filler in ("really", "very", "actually"):
        assert filler not in text_lower
    assert "important" in text_lower
    assert "critical" in text_lower


def test_medium_handles_combined_request_from_spec():
    # spec example: "Could you please kindly help me with the following request?"
    r = compress(
        "Could you please kindly help me with the following request?",
        level=Level.MEDIUM,
    )
    text_lower = r.text.lower()
    for stripped in ("could you", "please", "kindly"):
        assert stripped not in text_lower
    assert "help me with the following request" in text_lower


# -------------------------- AGGRESSIVE level -------------------------


def test_aggressive_collapses_in_order_to():
    r = compress(
        "Run the script in order to generate the report.",
        level=Level.AGGRESSIVE,
    )
    assert "in order to" not in r.text.lower()
    assert " to generate" in r.text.lower()


def test_aggressive_collapses_due_to_the_fact_that():
    r = compress(
        "Skipping this case due to the fact that the API is down.",
        level=Level.AGGRESSIVE,
    )
    assert "due to the fact that" not in r.text.lower()
    assert "because" in r.text.lower()


def test_aggressive_strips_stopword_adjectives():
    r = compress(
        "Write a nice cool awesome wonderful summary of the docs.",
        level=Level.AGGRESSIVE,
    )
    text_lower = r.text.lower()
    for adj in ("nice", "cool", "awesome", "wonderful"):
        assert adj not in text_lower
    assert "summary of the docs" in text_lower


def test_aggressive_contracts_phrasing():
    r = compress("Do not panic, you are fine.", level=Level.AGGRESSIVE)
    text_lower = r.text.lower()
    assert "do not" not in text_lower
    assert "you are" not in text_lower
    assert "don't" in text_lower
    assert "you're" in text_lower


# ------------------------- code block preservation -------------------


def test_code_blocks_preserved_by_default():
    src = "Please run this:\n```python\nplease = 1  # keep this comment\nthanks\n```\nThanks!"
    r = compress(src, level=Level.AGGRESSIVE)
    # the code block body must be byte-identical to the original
    assert "please = 1  # keep this comment" in r.text
    assert "thanks\n```" in r.text
    # outside the block, "please" and "thanks" should be gone
    outside = r.text.split("```")[0]
    assert "please" not in outside.lower()


def test_code_blocks_opt_out():
    src = "```\nplease keep this\n```"
    r = compress(src, level=Level.LIGHT, preserve_code_blocks=False)
    # with preservation off, "please" inside the block IS removed
    assert "please" not in r.text.lower()


def test_multiple_code_blocks_preserved_in_order():
    src = "First:\n```\nblock one\n```\nThen:\n```\nblock two\n```\nThanks"
    r = compress(src, level=Level.LIGHT)
    # order matters - block one before block two
    pos_one = r.text.find("block one")
    pos_two = r.text.find("block two")
    assert pos_one != -1 and pos_two != -1
    assert pos_one < pos_two


# ----------------------------- custom rules --------------------------


def test_custom_rules_append_after_builtins():
    # built-ins strip "please"; custom rule swaps "foo" -> "bar"
    r = compress(
        "please replace foo here",
        level=Level.LIGHT,
        custom_rules=[(r"\bfoo\b", "bar")],
    )
    text_lower = r.text.lower()
    assert "please" not in text_lower
    assert "foo" not in text_lower
    assert "bar" in text_lower


def test_custom_rule_is_case_insensitive():
    r = compress(
        "Replace FOO with something",
        level=Level.LIGHT,
        custom_rules=[(r"\bfoo\b", "baz")],
    )
    assert "FOO" not in r.text
    assert "baz" in r.text


# ----------------------------- stats fields --------------------------


def test_stats_chars_and_words_counts():
    src = "Please help me out"
    r = compress(src, level=Level.LIGHT)
    assert r.stats.chars_before == len(src)
    assert r.stats.chars_after == len(r.text)
    assert r.stats.words_before == 4
    # "Help me out" -> 3 words
    assert r.stats.words_after == 3


def test_stats_ratio_arithmetic():
    src = "please please please go"  # heavy politeness, will shrink a lot
    r = compress(src, level=Level.LIGHT)
    expected = r.stats.chars_after / r.stats.chars_before
    assert r.stats.ratio == pytest.approx(expected)
    assert 0.0 <= r.stats.ratio <= 1.0


def test_stats_ratio_for_empty_input_is_one():
    r = compress("", level=Level.LIGHT)
    assert r.stats.ratio == 1.0
    assert r.stats.chars_before == 0
    assert r.stats.chars_after == 0


def test_stats_ratio_for_text_without_matches_is_one():
    src = "go"  # nothing to strip
    r = compress(src, level=Level.LIGHT)
    assert r.stats.ratio == 1.0
    assert r.text == "Go"


# --------------------------- edge case inputs ------------------------


def test_empty_string_handled():
    r = compress("", level=Level.AGGRESSIVE)
    assert isinstance(r, CompressionResult)
    assert r.text == ""
    assert isinstance(r.stats, CompressionStats)


def test_whitespace_only_handled():
    r = compress("    \n  \n   ", level=Level.AGGRESSIVE)
    # everything trimmed away
    assert r.text == ""
    assert r.stats.chars_after == 0


def test_no_match_input_only_capitalizes_and_trims():
    r = compress("Already short.", level=Level.AGGRESSIVE)
    assert r.text == "Already short."


# -------------------------- level monotonicity -----------------------


def test_aggressive_is_at_most_as_long_as_medium_as_long_as_light():
    src = (
        "Could you please kindly help me with this request, in order to "
        "complete the task due to the fact that we are very behind, thanks!"
    )
    r_light = compress(src, level=Level.LIGHT)
    r_medium = compress(src, level=Level.MEDIUM)
    r_aggressive = compress(src, level=Level.AGGRESSIVE)
    assert len(r_light.text) >= len(r_medium.text) >= len(r_aggressive.text)
    # on this input, each step should strictly shrink
    assert len(r_light.text) > len(r_medium.text) > len(r_aggressive.text)


def test_ratios_in_unit_interval_for_each_level():
    src = "Please kindly help me with this request, thanks!"
    for level in (Level.LIGHT, Level.MEDIUM, Level.AGGRESSIVE):
        r = compress(src, level=level)
        assert 0.0 <= r.stats.ratio <= 1.0


# --------------------------- Compressor reuse ------------------------


def test_compressor_class_reuses_compiled_rules():
    c = Compressor(level=Level.MEDIUM)
    a = c.compress("Could you please summarize this?")
    b = c.compress("Could you please summarize that?")
    assert "could you" not in a.text.lower()
    assert "could you" not in b.text.lower()
    assert "summarize this" in a.text.lower()
    assert "summarize that" in b.text.lower()


def test_compressor_class_accepts_custom_rules_once():
    c = Compressor(
        level=Level.LIGHT,
        custom_rules=[(r"\bfoo\b", "FOO")],
    )
    r1 = c.compress("please change foo here")
    r2 = c.compress("foo is the target")
    assert "FOO" in r1.text and "FOO" in r2.text
    assert "please" not in r1.text.lower()


# -------------------- preserve code-blocks edge cases ----------------


def test_code_block_with_language_tag_preserved():
    src = "```js\nconst please = 'keep';\n```"
    r = compress(src, level=Level.AGGRESSIVE)
    assert "const please = 'keep';" in r.text


def test_dataclasses_are_frozen():
    # `frozen=True` raises `dataclasses.FrozenInstanceError` (a subclass
    # of `AttributeError`) on assignment to a field.
    from dataclasses import FrozenInstanceError

    r = compress("please go", level=Level.LIGHT)
    with pytest.raises(FrozenInstanceError):
        r.text = "mutated"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        r.stats.chars_before = 0  # type: ignore[misc]
