"""Heuristic prompt compression.

The `compress()` function and `Compressor` class strip low-value tokens
from a prompt without changing its intent. Three levels are exposed:

  * `Level.LIGHT` - whitespace normalization and politeness removal.
  * `Level.MEDIUM` - LIGHT plus filler verb phrases and intensifiers.
  * `Level.AGGRESSIVE` - MEDIUM plus wordy-phrase collapses and
    stopword adjectives.

The output is reported as a `CompressionResult` with a `CompressionStats`
block so callers can decide whether the savings were worth keeping.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum

from llm_prompt_compress.rules import rules_for_level

# matches a fenced code block: ``` optional language ``` ... ```
# DOTALL so the body can contain newlines.
_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)

# placeholder format used to swap code blocks out before compression.
# the index keeps blocks distinct so order is preserved on restore.
_PLACEHOLDER_FMT = "\x00LPC_CODE_{i}\x00"
_PLACEHOLDER_RE = re.compile(r"\x00LPC_CODE_(\d+)\x00")


class Level(IntEnum):
    """Compression aggressiveness. Higher includes everything below."""

    LIGHT = 1
    MEDIUM = 2
    AGGRESSIVE = 3


@dataclass(frozen=True)
class CompressionStats:
    """Before/after sizes for one `compress()` call.

    `ratio` is `chars_after / chars_before`. Lower is more savings. When
    the input is empty, `ratio` is `1.0` so callers can compare safely.
    """

    chars_before: int
    chars_after: int
    words_before: int
    words_after: int
    ratio: float


@dataclass(frozen=True)
class CompressionResult:
    """Compressed text plus the stats describing the change."""

    text: str
    stats: CompressionStats


def _count_words(text: str) -> int:
    """Whitespace-split word count, robust to empty / whitespace-only."""
    return len(text.split())


def _build_stats(before: str, after: str) -> CompressionStats:
    chars_before = len(before)
    chars_after = len(after)
    ratio = 1.0 if chars_before == 0 else chars_after / chars_before
    return CompressionStats(
        chars_before=chars_before,
        chars_after=chars_after,
        words_before=_count_words(before),
        words_after=_count_words(after),
        ratio=ratio,
    )


def _extract_code_blocks(text: str) -> tuple[str, list[str]]:
    """Replace ``` blocks with placeholders. Returns (masked_text, blocks)."""
    blocks: list[str] = []

    def _swap(match: re.Match[str]) -> str:
        blocks.append(match.group(0))
        return _PLACEHOLDER_FMT.format(i=len(blocks) - 1)

    masked = _CODE_BLOCK_RE.sub(_swap, text)
    return masked, blocks


def _restore_code_blocks(text: str, blocks: list[str]) -> str:
    """Swap placeholders back to their original code blocks."""
    if not blocks:
        return text

    def _swap(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return blocks[idx]

    return _PLACEHOLDER_RE.sub(_swap, text)


def _normalize_whitespace(text: str) -> str:
    """Collapse runs of spaces/tabs and trim each line.

    Keeps newlines intact so multi-paragraph prompts stay readable.
    Strips leading/trailing whitespace on the whole string.
    """
    # collapse runs of horizontal whitespace
    text = re.sub(r"[ \t]+", " ", text)
    # trim each line
    text = "\n".join(line.strip() for line in text.split("\n"))
    # collapse 3+ blank lines down to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class Compressor:
    """Reusable compressor that compiles its rule regexes once.

    Use this when compressing many prompts in a loop. For one-shot calls,
    the module-level `compress()` helper is simpler.
    """

    def __init__(
        self,
        level: Level = Level.LIGHT,
        *,
        custom_rules: list[tuple[str, str]] | None = None,
        preserve_code_blocks: bool = True,
    ) -> None:
        self.level = level
        self.preserve_code_blocks = preserve_code_blocks
        # built-in rules first, then any caller-supplied rules
        built_in = rules_for_level(int(level))
        all_rules = built_in + list(custom_rules or [])
        # pre-compile every pattern; flags=IGNORECASE so authors can
        # write "please" instead of "[Pp]lease".
        self._compiled: list[tuple[re.Pattern[str], str]] = [
            (re.compile(pat, flags=re.IGNORECASE), repl) for pat, repl in all_rules
        ]

    def compress(self, text: str) -> CompressionResult:
        original = text
        if not text:
            return CompressionResult(text=text, stats=_build_stats(original, text))

        if self.preserve_code_blocks:
            working, blocks = _extract_code_blocks(text)
        else:
            working, blocks = text, []

        for pattern, replacement in self._compiled:
            working = pattern.sub(replacement, working)

        # whitespace normalization runs after substitutions because the
        # substitutions themselves leave double spaces and stray commas.
        working = _normalize_whitespace(working)
        # strip leftover commas/semicolons that were stranded by removed
        # politeness tokens (for example "please, help" -> ", help").
        working = re.sub(r"^[\s,;]+", "", working)
        working = re.sub(r"\s+([,.;:!?])", r"\1", working)
        # capitalize the first character if we lowercased it by accident
        # via a leading-word removal. only the very first char.
        if working and working[0].islower():
            working = working[0].upper() + working[1:]

        if blocks:
            working = _restore_code_blocks(working, blocks)

        return CompressionResult(text=working, stats=_build_stats(original, working))


def compress(
    text: str,
    level: Level = Level.LIGHT,
    *,
    custom_rules: list[tuple[str, str]] | None = None,
    preserve_code_blocks: bool = True,
) -> CompressionResult:
    """Compress `text` at the given `level`.

    `custom_rules` is an optional list of `(pattern, replacement)` tuples
    applied after the built-in rules. Patterns are full Python regex
    strings; `re.IGNORECASE` is applied automatically.

    When `preserve_code_blocks` is True (default), the contents of
    triple-backtick fenced blocks are passed through untouched.
    """
    compressor = Compressor(
        level=level,
        custom_rules=custom_rules,
        preserve_code_blocks=preserve_code_blocks,
    )
    return compressor.compress(text)
