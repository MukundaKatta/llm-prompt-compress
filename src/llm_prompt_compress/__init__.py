"""llm-prompt-compress - heuristic prompt compression for LLM calls.

Reduces token count by removing low-value tokens (politeness, filler
verbs, redundant intensifiers, wordy phrases) rather than truncating.
The intent of the request is preserved; only weight is shed.

    from llm_prompt_compress import compress, Level

    result = compress(
        "Could you please kindly help me with the following request?",
        level=Level.MEDIUM,
    )
    print(result.text)         # "Help me with the following request"
    print(result.stats.ratio)  # 0.55

Three levels are exposed:

  * `Level.LIGHT` - whitespace + politeness only.
  * `Level.MEDIUM` - LIGHT plus filler verb phrases and intensifiers.
  * `Level.AGGRESSIVE` - MEDIUM plus wordy-phrase collapses and
    stopword adjectives.

Code blocks (triple-backtick fences) are preserved by default. Custom
rules can be appended via the `custom_rules` keyword.

Sibling to `agentfit` (strict truncation to fit a budget) and
`tool-output-truncate-py` (tool output truncation).
"""

from llm_prompt_compress.compress import (
    CompressionResult,
    CompressionStats,
    Compressor,
    Level,
    compress,
)

__version__ = "0.1.0"

__all__ = [
    "Compressor",
    "CompressionResult",
    "CompressionStats",
    "Level",
    "__version__",
    "compress",
]
