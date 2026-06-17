# llm-prompt-compress

Heuristic prompt compression for LLM context budgeting.

Zero runtime dependencies. Python 3.10+.

## Usage

### Level-based prompt compression

Strip politeness, filler, and wordy phrases while preserving fenced code blocks:

```python
from llm_prompt_compress import compress_prompt, Level

result = compress_prompt(
    "Please could you very kindly summarize this. Thanks!",
    level=Level.AGGRESSIVE,
)
print(result.text)         # "Summarize this."
print(result.stats.ratio)  # chars_after / chars_before
```

Levels are cumulative: `Level.LIGHT` < `Level.MEDIUM` < `Level.AGGRESSIVE`.
Use the `Compressor` class to compile the rules once and reuse it in a loop:

```python
from llm_prompt_compress import Compressor, Level

compressor = Compressor(level=Level.MEDIUM)
for prompt in prompts:
    print(compressor.compress(prompt).text)
```

Fenced code blocks are preserved by default. Pass `preserve_code_blocks=False`
to compress inside them too, or supply `custom_rules` (a list of
`(pattern, replacement)` regex tuples applied after the built-ins) to extend
the ruleset:

```python
compress_prompt(
    "Frobnicate the widget.",
    level=Level.LIGHT,
    custom_rules=[(r"\bfrobnicate\b", "fix")],
)
```

### Strategy-based cleanup

Trim transcripts to a character budget:

```python
from llm_prompt_compress import compress, compress_messages

compress("text   with   noise\n\n\n", strategies=["whitespace"]).text
compress_messages(messages, max_chars_per_message=2000, strategies=["whitespace"])
```

Available strategies (applied in the order you list them): `whitespace`
(collapse blank lines and trailing spaces), `comments` (drop `#` and `//`
single-line comments), `fences` (strip markdown code-fence markers), and
`truncate` (cut to `max_chars` at a sentence boundary). When `max_chars` is
set it is always enforced as a final hard cap, regardless of strategy.

## API

| Symbol | Summary |
| --- | --- |
| `compress_prompt(text, level=Level.LIGHT, *, custom_rules=None, preserve_code_blocks=True)` | Level-based heuristic rewrite. Returns a `CompressionResult`. |
| `Compressor(level=Level.LIGHT, *, custom_rules=None, preserve_code_blocks=True)` | Reusable compressor; compiles rule regexes once. `.compress(text)` returns a `CompressionResult`. |
| `Level` | `IntEnum` with `LIGHT < MEDIUM < AGGRESSIVE`. |
| `CompressionResult` | `text: str` plus `stats: CompressionStats`. |
| `CompressionStats` | `chars_before`, `chars_after`, `words_before`, `words_after`, `ratio` (`chars_after / chars_before`; `1.0` for empty input). |
| `compress(text, max_chars=None, strategies=None)` | Strategy-based cleanup (default `["whitespace"]`). Returns a `CompressResult`. |
| `compress_messages(messages, max_chars_per_message=None, strategies=None, skip_roles=None)` | Compress each message's `content`; `skip_roles` defaults to `["system"]`. Returns `(messages, total_chars_saved)`. |
| `CompressResult` | `text`, `original_chars`, `compressed_chars`, `strategy`, plus `ratio` and `saved_chars` properties. |

The package ships a `py.typed` marker, so type checkers see its annotations.

## Development

```bash
pip install -e ".[dev]"
ruff check src/ tests/
pytest
```

The test suite has no third-party dependencies, so it also runs with the
standard library alone:

```bash
python -m unittest discover -s tests
```
