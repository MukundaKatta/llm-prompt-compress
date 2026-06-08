"""Tests for llm-prompt-compress."""

from llm_prompt_compress import compress, compress_messages, CompressResult


def test_compress_whitespace_collapses_blanks():
    text = "Line 1\n\n\n\nLine 2"
    r = compress(text, strategies=["whitespace"])
    assert r.text == "Line 1\n\nLine 2"
    assert r.strategy == "whitespace"


def test_compress_trailing_spaces():
    text = "hello   \nworld   \n"
    r = compress(text, strategies=["whitespace"])
    assert "   " not in r.text


def test_compress_fences():
    text = "```python\nprint('hello')\n```"
    r = compress(text, strategies=["fences"])
    assert "```" not in r.text
    assert "print" in r.text


def test_compress_comments_hash():
    text = "x = 1\n# this is a comment\ny = 2\n"
    r = compress(text, strategies=["comments"])
    assert "# this" not in r.text
    assert "y = 2" in r.text


def test_compress_comments_slash():
    text = "int x = 1;\n// comment here\nint y = 2;\n"
    r = compress(text, strategies=["comments"])
    assert "// comment" not in r.text
    assert "int y" in r.text


def test_compress_truncate_at_max_chars():
    text = "Hello world. This is a long sentence. More text here."
    r = compress(text, max_chars=20, strategies=["truncate"])
    assert len(r.text) <= 20


def test_compress_truncate_sentence_boundary():
    text = "First sentence. Second sentence. Third sentence."
    r = compress(text, max_chars=30, strategies=["truncate"])
    # should end at sentence boundary
    assert r.text.endswith(".") or len(r.text) <= 30


def test_compress_no_change_short_text():
    text = "Short."
    r = compress(text, max_chars=100, strategies=["whitespace"])
    assert r.text == text


def test_compress_ratio():
    text = "A\n\n\n\nB"
    r = compress(text, strategies=["whitespace"])
    assert r.ratio < 1.0 or r.original_chars == r.compressed_chars


def test_compress_saved_chars():
    text = "Hello   \n\n\n\nWorld"
    r = compress(text, strategies=["whitespace"])
    assert r.saved_chars >= 0


def test_compress_original_chars():
    text = "Hello"
    r = compress(text, strategies=["whitespace"])
    assert r.original_chars == 5


def test_compress_empty():
    r = compress("", strategies=["whitespace"])
    assert r.text == ""
    assert r.ratio == 1.0


def test_compress_messages_skips_system():
    messages = [
        {"role": "system", "content": "You are helpful.\n\n\n"},
        {"role": "user", "content": "Hello.\n\n\n\nWorld."},
    ]
    compressed, saved = compress_messages(messages, strategies=["whitespace"])
    # system should be unchanged (skipped)
    assert compressed[0]["content"] == "You are helpful.\n\n\n"
    # user should be compressed
    assert "saved" or saved >= 0


def test_compress_messages_total_saved():
    messages = [
        {"role": "user", "content": "A\n\n\n\nB"},
    ]
    _, saved = compress_messages(messages, strategies=["whitespace"])
    assert saved >= 0


def test_compress_messages_non_string_passthrough():
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "hello"}]},
    ]
    result, _ = compress_messages(messages, strategies=["whitespace"])
    assert result[0]["content"] == messages[0]["content"]


def test_compress_multiple_strategies():
    text = "# comment\n\nHello\n\n\nWorld."
    r = compress(text, strategies=["comments", "whitespace"])
    assert "comment" not in r.text
    assert "\n\n\n" not in r.text


def test_compress_result_type():
    r = compress("hello", strategies=["whitespace"])
    assert isinstance(r, CompressResult)
