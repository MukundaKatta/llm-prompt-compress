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
Use the `Compressor` class to compile the rules once and reuse it in a loop.

### Strategy-based cleanup

Trim transcripts to a character budget:

```python
from llm_prompt_compress import compress, compress_messages

compress("text   with   noise\n\n\n", strategies=["whitespace"]).text
compress_messages(messages, max_chars_per_message=2000, strategies=["whitespace"])
```

## Development

```bash
pip install -e ".[dev]"
ruff check src/ tests/
pytest
```
