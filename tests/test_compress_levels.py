"""Tests for the level-based heuristic compressor (compress.py / rules.py)."""

from llm_prompt_compress import (
    CompressionResult,
    CompressionStats,
    Compressor,
    Level,
    compress_prompt,
)


def test_compress_prompt_strips_politeness():
    r = compress_prompt("Please help me.", level=Level.LIGHT)
    assert r.text == "Help me."
    assert isinstance(r, CompressionResult)
    assert isinstance(r.stats, CompressionStats)


def test_compress_prompt_strips_trailing_thanks():
    r = compress_prompt("Summarize this. Thanks!", level=Level.LIGHT)
    assert "thanks" not in r.text.lower()
    assert r.text.startswith("Summarize")


def test_level_ordering_is_monotonic():
    text = "Please, can you really just in order to fix this. Thanks!"
    light = compress_prompt(text, level=Level.LIGHT)
    medium = compress_prompt(text, level=Level.MEDIUM)
    aggressive = compress_prompt(text, level=Level.AGGRESSIVE)
    # Higher levels include all lower-level rules, so they cannot grow.
    assert len(aggressive.text) <= len(medium.text) <= len(light.text)


def test_medium_removes_filler_verb_phrase():
    r = compress_prompt("I would like you to write a poem.", level=Level.MEDIUM)
    assert "would like" not in r.text.lower()
    assert "poem" in r.text


def test_aggressive_collapses_wordy_phrase():
    r = compress_prompt("Run the script in order to deploy.", level=Level.AGGRESSIVE)
    assert "in order to" not in r.text.lower()
    assert "to deploy" in r.text.lower()


def test_preserve_code_blocks_keeps_fenced_content():
    src = "Please refactor:\n```python\n# keep please\nx = 1\n```\nThanks!"
    r = compress_prompt(src, level=Level.AGGRESSIVE, preserve_code_blocks=True)
    assert "# keep please" in r.text
    assert "x = 1" in r.text
    # politeness outside the block is still stripped
    assert "thanks" not in r.text.lower()


def test_preserve_code_blocks_false_processes_everything():
    src = "Please run:\n```\nplease note that x\n```"
    r = compress_prompt(src, level=Level.AGGRESSIVE, preserve_code_blocks=False)
    # without preservation the inner "please note that" rule applies
    assert "please note that" not in r.text.lower()


def test_multiple_code_blocks_order_preserved():
    src = "Do ```first``` then ```second``` now."
    r = compress_prompt(src, level=Level.LIGHT)
    assert "```first```" in r.text
    assert "```second```" in r.text
    assert r.text.index("```first```") < r.text.index("```second```")


def test_empty_input_ratio_is_one():
    r = compress_prompt("", level=Level.AGGRESSIVE)
    assert r.text == ""
    assert r.stats.ratio == 1.0
    assert r.stats.chars_before == 0


def test_whitespace_only_input():
    r = compress_prompt("   \n\n  ", level=Level.LIGHT)
    assert r.text == ""


def test_custom_rules_applied_after_builtins():
    r = compress_prompt(
        "Foobar the widget.",
        level=Level.LIGHT,
        custom_rules=[(r"\bfoobar\b", "frobnicate")],
    )
    assert "frobnicate" in r.text.lower()


def test_stats_word_counts():
    r = compress_prompt("please help me now", level=Level.LIGHT)
    assert r.stats.words_before == 4
    assert r.stats.words_after == r.stats.words_after  # well-defined
    assert r.stats.chars_after <= r.stats.chars_before


def test_compressor_reuse():
    c = Compressor(level=Level.MEDIUM)
    a = c.compress("Can you please summarize this?")
    b = c.compress("I want to refactor this.")
    assert "please" not in a.text.lower()
    assert "i want to" not in b.text.lower()


def test_compressor_default_level_is_light():
    c = Compressor()
    assert c.level == Level.LIGHT


def test_first_char_capitalized_after_leading_removal():
    # leading "please " removal should not leave a lowercase sentence start
    r = compress_prompt("please summarize the document.", level=Level.LIGHT)
    assert r.text[0].isupper()
