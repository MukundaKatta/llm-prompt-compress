"""Standard-library ``unittest`` suite for llm-prompt-compress.

The existing ``test_*.py`` modules use pytest's function/``assert`` style.
This module mirrors and extends that coverage using only the Python
standard library so the full suite can be run without any third-party
dependencies::

    python3 -m unittest discover -s tests

It is also collected by pytest, so it runs under both runners.

The package lives under ``src/`` (a src-layout project). To keep this
module runnable without an editable install, ``src/`` is added to
``sys.path`` at import time when the package is not already importable.
"""

from __future__ import annotations

import os
import sys
import unittest

# Make ``src/`` importable when the package has not been pip-installed.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from llm_prompt_compress import (  # noqa: E402
    CompressionResult,
    CompressionStats,
    CompressResult,
    Compressor,
    Level,
    compress,
    compress_messages,
    compress_prompt,
)


class LevelBasedCompressionTests(unittest.TestCase):
    """Tests for ``compress_prompt`` / ``Compressor`` / ``Level``."""

    def test_strips_leading_politeness(self) -> None:
        result = compress_prompt("Please help me.", level=Level.LIGHT)
        self.assertEqual(result.text, "Help me.")
        self.assertIsInstance(result, CompressionResult)
        self.assertIsInstance(result.stats, CompressionStats)

    def test_strips_trailing_thanks(self) -> None:
        result = compress_prompt("Summarize this. Thanks!", level=Level.LIGHT)
        self.assertNotIn("thanks", result.text.lower())
        self.assertTrue(result.text.startswith("Summarize"))

    def test_readme_aggressive_example(self) -> None:
        # The exact example advertised in the README must keep working.
        result = compress_prompt(
            "Please could you very kindly summarize this. Thanks!",
            level=Level.AGGRESSIVE,
        )
        self.assertEqual(result.text, "Summarize this.")
        self.assertLess(result.stats.ratio, 1.0)

    def test_levels_are_monotonic(self) -> None:
        text = "Please, can you really just in order to fix this. Thanks!"
        light = compress_prompt(text, level=Level.LIGHT)
        medium = compress_prompt(text, level=Level.MEDIUM)
        aggressive = compress_prompt(text, level=Level.AGGRESSIVE)
        # Higher levels are supersets of lower-level rules, so the output
        # length can only stay the same or shrink as the level increases.
        self.assertLessEqual(len(aggressive.text), len(medium.text))
        self.assertLessEqual(len(medium.text), len(light.text))

    def test_medium_removes_filler_verb_phrase(self) -> None:
        result = compress_prompt(
            "I would like you to write a poem.", level=Level.MEDIUM
        )
        self.assertNotIn("would like", result.text.lower())
        self.assertIn("poem", result.text)

    def test_aggressive_collapses_wordy_phrase(self) -> None:
        result = compress_prompt(
            "Run the script in order to deploy.", level=Level.AGGRESSIVE
        )
        self.assertNotIn("in order to", result.text.lower())
        self.assertIn("to deploy", result.text.lower())

    def test_code_blocks_preserved_by_default(self) -> None:
        src = "Please refactor:\n```python\n# keep please\nx = 1\n```\nThanks!"
        result = compress_prompt(src, level=Level.AGGRESSIVE)
        self.assertIn("# keep please", result.text)
        self.assertIn("x = 1", result.text)
        # Politeness outside the fenced block is still stripped.
        self.assertNotIn("thanks", result.text.lower())

    def test_preserve_code_blocks_false_processes_everything(self) -> None:
        src = "Please run:\n```\nplease note that x\n```"
        result = compress_prompt(
            src, level=Level.AGGRESSIVE, preserve_code_blocks=False
        )
        self.assertNotIn("please note that", result.text.lower())

    def test_multiple_code_blocks_keep_order(self) -> None:
        src = "Do ```first``` then ```second``` now."
        result = compress_prompt(src, level=Level.LIGHT)
        self.assertIn("```first```", result.text)
        self.assertIn("```second```", result.text)
        self.assertLess(
            result.text.index("```first```"), result.text.index("```second```")
        )

    def test_empty_input_has_unit_ratio(self) -> None:
        result = compress_prompt("", level=Level.AGGRESSIVE)
        self.assertEqual(result.text, "")
        self.assertEqual(result.stats.ratio, 1.0)
        self.assertEqual(result.stats.chars_before, 0)

    def test_whitespace_only_input_collapses_to_empty(self) -> None:
        result = compress_prompt("   \n\n  ", level=Level.LIGHT)
        self.assertEqual(result.text, "")

    def test_custom_rules_run_after_builtins(self) -> None:
        result = compress_prompt(
            "Foobar the widget.",
            level=Level.LIGHT,
            custom_rules=[(r"\bfoobar\b", "frobnicate")],
        )
        self.assertIn("frobnicate", result.text.lower())

    def test_stats_word_and_char_counts(self) -> None:
        result = compress_prompt("please help me now", level=Level.LIGHT)
        self.assertEqual(result.stats.words_before, 4)
        self.assertLessEqual(result.stats.words_after, result.stats.words_before)
        self.assertLessEqual(result.stats.chars_after, result.stats.chars_before)

    def test_first_char_recapitalized_after_leading_removal(self) -> None:
        result = compress_prompt("please summarize the document.", level=Level.LIGHT)
        self.assertTrue(result.text[0].isupper())

    def test_stray_comma_after_politeness_removed(self) -> None:
        result = compress_prompt("Please , help.", level=Level.LIGHT)
        self.assertEqual(result.text, "Help.")

    def test_default_level_is_light(self) -> None:
        self.assertEqual(Compressor().level, Level.LIGHT)
        self.assertEqual(Level.LIGHT, 1)
        self.assertLess(Level.LIGHT, Level.MEDIUM)
        self.assertLess(Level.MEDIUM, Level.AGGRESSIVE)

    def test_compressor_is_reusable(self) -> None:
        compressor = Compressor(level=Level.MEDIUM)
        first = compressor.compress("Can you please summarize this?")
        second = compressor.compress("I want to refactor this.")
        self.assertNotIn("please", first.text.lower())
        self.assertNotIn("i want to", second.text.lower())


class StrategyBasedCompressionTests(unittest.TestCase):
    """Tests for ``compress`` / ``compress_messages`` / ``CompressResult``."""

    def test_whitespace_collapses_blank_lines(self) -> None:
        result = compress("Line 1\n\n\n\nLine 2", strategies=["whitespace"])
        self.assertEqual(result.text, "Line 1\n\nLine 2")
        self.assertEqual(result.strategy, "whitespace")

    def test_whitespace_trims_trailing_spaces(self) -> None:
        result = compress("hello   \nworld   \n", strategies=["whitespace"])
        self.assertNotIn("   ", result.text)

    def test_fences_strips_code_markers(self) -> None:
        result = compress("```python\nprint('hello')\n```", strategies=["fences"])
        self.assertNotIn("```", result.text)
        self.assertIn("print", result.text)

    def test_comments_removes_hash_lines(self) -> None:
        result = compress("x = 1\n# a comment\ny = 2\n", strategies=["comments"])
        self.assertNotIn("# a comment", result.text)
        self.assertIn("y = 2", result.text)

    def test_comments_removes_slash_lines(self) -> None:
        result = compress(
            "int x = 1;\n// comment here\nint y = 2;\n", strategies=["comments"]
        )
        self.assertNotIn("// comment", result.text)
        self.assertIn("int y", result.text)

    def test_truncate_respects_max_chars(self) -> None:
        result = compress(
            "Hello world. This is a long sentence. More text here.",
            max_chars=20,
            strategies=["truncate"],
        )
        self.assertLessEqual(len(result.text), 20)

    def test_truncate_prefers_sentence_boundary(self) -> None:
        result = compress(
            "First sentence. Second sentence. Third sentence.",
            max_chars=30,
            strategies=["truncate"],
        )
        self.assertTrue(result.text.endswith(".") or len(result.text) <= 30)

    def test_hard_truncate_applies_without_truncate_strategy(self) -> None:
        # ``max_chars`` is enforced as a final hard cap even when the
        # ``truncate`` strategy is not requested.
        result = compress(
            "Hello world this is long", max_chars=5, strategies=["whitespace"]
        )
        self.assertLessEqual(len(result.text), 5)

    def test_unknown_strategy_is_ignored(self) -> None:
        result = compress("hello", strategies=["bogus"])
        self.assertEqual(result.text, "hello")
        self.assertEqual(result.strategy, "none")

    def test_default_strategy_is_whitespace(self) -> None:
        result = compress("a\n\n\n\nb")
        self.assertEqual(result.strategy, "whitespace")

    def test_short_text_unchanged(self) -> None:
        result = compress("Short.", max_chars=100, strategies=["whitespace"])
        self.assertEqual(result.text, "Short.")

    def test_ratio_and_saved_chars(self) -> None:
        result = compress("Hello   \n\n\n\nWorld", strategies=["whitespace"])
        self.assertGreaterEqual(result.saved_chars, 0)
        self.assertLessEqual(result.ratio, 1.0)
        self.assertEqual(
            result.saved_chars, result.original_chars - result.compressed_chars
        )

    def test_original_char_count(self) -> None:
        result = compress("Hello", strategies=["whitespace"])
        self.assertEqual(result.original_chars, 5)

    def test_empty_input_unit_ratio(self) -> None:
        result = compress("", strategies=["whitespace"])
        self.assertEqual(result.text, "")
        self.assertEqual(result.ratio, 1.0)

    def test_result_type(self) -> None:
        self.assertIsInstance(compress("hello"), CompressResult)


class MessageCompressionTests(unittest.TestCase):
    """Tests for ``compress_messages``."""

    def test_system_messages_skipped_by_default(self) -> None:
        messages = [
            {"role": "system", "content": "You are helpful.\n\n\n"},
            {"role": "user", "content": "Hello.\n\n\n\nWorld."},
        ]
        compressed, saved = compress_messages(messages, strategies=["whitespace"])
        # System content is left untouched.
        self.assertEqual(compressed[0]["content"], "You are helpful.\n\n\n")
        # User content is compressed and reported as savings.
        self.assertGreaterEqual(saved, 0)
        self.assertNotEqual(compressed[1]["content"], messages[1]["content"])

    def test_total_saved_is_non_negative(self) -> None:
        messages = [{"role": "user", "content": "A\n\n\n\nB"}]
        _, saved = compress_messages(messages, strategies=["whitespace"])
        self.assertGreaterEqual(saved, 0)

    def test_non_string_content_passed_through(self) -> None:
        messages = [
            {"role": "user", "content": [{"type": "text", "text": "hello"}]},
        ]
        result, saved = compress_messages(messages, strategies=["whitespace"])
        self.assertEqual(result[0]["content"], messages[0]["content"])
        self.assertEqual(saved, 0)

    def test_custom_skip_roles(self) -> None:
        messages = [
            {"role": "assistant", "content": "Sure.\n\n\n\nHere."},
            {"role": "user", "content": "Hi.\n\n\n\nThere."},
        ]
        compressed, _ = compress_messages(
            messages, strategies=["whitespace"], skip_roles=["assistant"]
        )
        # Assistant skipped, user compressed.
        self.assertEqual(compressed[0]["content"], messages[0]["content"])
        self.assertNotEqual(compressed[1]["content"], messages[1]["content"])

    def test_original_messages_not_mutated(self) -> None:
        messages = [{"role": "user", "content": "Hi.\n\n\n\nThere."}]
        original_content = messages[0]["content"]
        compress_messages(messages, strategies=["whitespace"])
        self.assertEqual(messages[0]["content"], original_content)


if __name__ == "__main__":
    unittest.main()
