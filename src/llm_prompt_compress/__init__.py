"""
llm-prompt-compress: Heuristic prompt compression — shrink context to fit a token budget.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CompressResult:
    text: str
    original_chars: int
    compressed_chars: int
    strategy: str

    @property
    def ratio(self) -> float:
        if self.original_chars == 0:
            return 1.0
        return self.compressed_chars / self.original_chars

    @property
    def saved_chars(self) -> int:
        return self.original_chars - self.compressed_chars


def _strip_markdown_fences(text: str) -> str:
    """Remove code fence markers (``` lines) but keep the code content."""
    return re.sub(r"^```[a-zA-Z0-9]*\n?|^```$", "", text, flags=re.MULTILINE).strip()


def _collapse_whitespace(text: str) -> str:
    """Collapse multiple blank lines into one, strip trailing spaces."""
    text = re.sub(r" +$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _remove_comments(text: str) -> str:
    """Remove single-line comments (# and //) from code-like content."""
    text = re.sub(r"^\s*#[^\n]*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*//[^\n]*\n", "", text, flags=re.MULTILINE)
    return text


def _truncate_sentences(text: str, max_chars: int) -> str:
    """Truncate to the last complete sentence boundary within max_chars."""
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    # find last sentence-ending punctuation
    for end_char in (".", "!", "?", "\n"):
        pos = chunk.rfind(end_char)
        if pos > max_chars // 2:
            return chunk[: pos + 1].strip()
    return chunk.strip()


def compress(
    text: str,
    max_chars: Optional[int] = None,
    strategies: Optional[list[str]] = None,
) -> CompressResult:
    """
    Compress ``text`` using heuristic strategies.

    Strategies (applied in order):
    - ``whitespace``:  collapse redundant blank lines and trailing spaces.
    - ``comments``:    remove ``#`` and ``//`` single-line comments.
    - ``fences``:      strip markdown code fence markers.
    - ``truncate``:    hard truncate to ``max_chars`` at sentence boundary.

    Parameters
    ----------
    text:
        Input text to compress.
    max_chars:
        Hard character limit (applied last via truncation).
    strategies:
        List of strategy names to apply. Default: ``["whitespace"]``.
    """
    if strategies is None:
        strategies = ["whitespace"]

    original = text
    applied: list[str] = []

    for strategy in strategies:
        if strategy == "whitespace":
            text = _collapse_whitespace(text)
            applied.append("whitespace")
        elif strategy == "comments":
            text = _remove_comments(text)
            applied.append("comments")
        elif strategy == "fences":
            text = _strip_markdown_fences(text)
            applied.append("fences")
        elif strategy == "truncate":
            if max_chars is not None:
                text = _truncate_sentences(text, max_chars)
            applied.append("truncate")

    if max_chars is not None and len(text) > max_chars:
        text = text[:max_chars].strip()

    return CompressResult(
        text=text,
        original_chars=len(original),
        compressed_chars=len(text),
        strategy="+".join(applied) if applied else "none",
    )


def compress_messages(
    messages: list[dict[str, Any]],
    max_chars_per_message: Optional[int] = None,
    strategies: Optional[list[str]] = None,
    skip_roles: Optional[list[str]] = None,
) -> tuple[list[dict[str, Any]], int]:
    """
    Compress the ``content`` field of each message.

    Returns ``(compressed_messages, total_chars_saved)``.
    """
    skip = set(skip_roles or ["system"])
    total_saved = 0
    result: list[dict[str, Any]] = []
    for msg in messages:
        if msg.get("role") in skip or not isinstance(msg.get("content"), str):
            result.append(msg)
            continue
        r = compress(msg["content"], max_chars=max_chars_per_message, strategies=strategies)
        total_saved += r.saved_chars
        result.append({**msg, "content": r.text})
    return result, total_saved


__all__ = ["compress", "compress_messages", "CompressResult"]
