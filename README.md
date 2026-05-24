# llm-prompt-compress

[![PyPI](https://img.shields.io/pypi/v/llm-prompt-compress.svg)](https://pypi.org/project/llm-prompt-compress/)
[![Python](https://img.shields.io/pypi/pyversions/llm-prompt-compress.svg)](https://pypi.org/project/llm-prompt-compress/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Heuristic prompt compression for LLM calls.**

Reduce token count by removing low-value tokens (politeness, filler verbs,
redundant intensifiers, wordy phrases) rather than truncating. The intent
of the request is preserved; only weight is shed.

Three aggressiveness levels. Pure regex and word lists. No model
dependency. Code blocks are preserved by default.

Sibling to [`agentfit`](https://pypi.org/project/agentfit/) (strict
truncation to fit a budget) and
[`tool-output-truncate-py`](https://pypi.org/project/tool-output-truncate-py/)
(tool output truncation).

## Install

```bash
pip install llm-prompt-compress
```

## Use

```python
from llm_prompt_compress import compress, Level

result = compress(
    "Could you please kindly help me with the following request?",
    level=Level.MEDIUM,
)
print(result.text)           # "Help me with the following request"
print(result.stats.ratio)    # ~0.55
print(result.stats.chars_before, result.stats.chars_after)
```

## Levels

Each level includes everything from the levels below it.

### LIGHT

Whitespace normalization plus politeness removal.

```python
compress("Please review the patch, thanks!", level=Level.LIGHT).text
# "Review the patch"
```

Strips: `please`, `kindly`, leading and trailing `thanks` / `thank you`,
duplicate spaces, redundant blank lines.

### MEDIUM

LIGHT plus filler verb phrases and intensifiers.

```python
compress(
    "Could you please summarize the following text for me?",
    level=Level.MEDIUM,
).text
# "Summarize the following text for me?"
```

Strips: `could you`, `would you`, `can you`, `I would like you to`,
`I want you to`, `very`, `really`, `actually`, `basically`.

### AGGRESSIVE

MEDIUM plus wordy-phrase collapses and stopword adjectives.

```python
compress(
    "Run the script in order to generate the report, "
    "due to the fact that the deploy was delayed.",
    level=Level.AGGRESSIVE,
).text
# "Run the script to generate the report, because the deploy was delayed."
```

Collapses: `in order to` -> `to`, `due to the fact that` -> `because`,
`at this point in time` -> `now`, `the majority of` -> `most`, plus
contractions like `do not` -> `don't`. Strips filler adjectives
(`nice`, `cool`, `awesome`, `wonderful`).

## Code blocks are preserved

Triple-backtick blocks are masked before compression and restored after,
so code inside the prompt is never touched.

```python
src = """
Please run this snippet:
```python
please = 1  # this stays
thanks
```
Thanks!
"""
result = compress(src, level=Level.AGGRESSIVE)
# Outside the fence: "please" and "thanks" are gone.
# Inside the fence: every character is preserved byte-for-byte.
```

Opt out with `preserve_code_blocks=False` if you actually want the
inside of the block compressed too.

## Custom rules

Append your own `(pattern, replacement)` tuples. They run after the
built-ins, case-insensitive.

```python
result = compress(
    "Please summarize the FooBar release notes.",
    level=Level.LIGHT,
    custom_rules=[(r"\bfoobar\b", "FB")],
)
print(result.text)  # "Summarize the FB release notes."
```

## Batch reuse

The `Compressor` class compiles its rule regexes once. Use this when
compressing many prompts in a loop.

```python
from llm_prompt_compress import Compressor, Level

compressor = Compressor(level=Level.MEDIUM)
for prompt in many_prompts:
    cleaned = compressor.compress(prompt)
    ...
```

## What it does NOT do

- No tokenizer. Reports characters and words; pair with your provider's
  tokenizer if you need exact token counts.
- No model in the loop. Pure regex and word lists. If you want
  semantic compression, run the output through an LLM yourself.
- No truncation. If you need strict byte budgets, use
  [`agentfit`](https://pypi.org/project/agentfit/) instead.
- No JSON or structured-output handling. Strings only.

## License

MIT
