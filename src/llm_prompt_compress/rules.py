"""Built-in compression rules grouped by level.

Each rule is a `(pattern, replacement)` pair. Patterns are compiled with
`re.IGNORECASE` so authors can write them lowercase. Order matters: rules
run top to bottom, so longer phrases must come before their substrings.

The lists are intentionally short and conservative. They strip the most
common low-value tokens that show up in LLM prompts without changing the
intent of the request. Callers that want more aggressive shaping can pass
`custom_rules` to `compress()`.
"""

from __future__ import annotations

# Rules applied at LIGHT level. Strips whitespace noise, politeness
# tokens, and trailing thanks. Word boundaries (`\b`) keep "please" out
# of words like "pleasure".
LIGHT_RULES: list[tuple[str, str]] = [
    # leading politeness
    (r"\b(please|kindly)\b[\s,]*", ""),
    # trailing thanks (with optional punctuation)
    (r"[\s,]*\b(thanks|thank you|thx|thanks in advance|ty)\b[\s.!]*$", ""),
    # inline thanks / appreciation
    (r"\b(thanks|thank you)\b[\s,]*", ""),
    # "I appreciate it" tail
    (r"\b(i (would |really )?appreciate (it|your help))\b[\s.!]*", ""),
]

# Extra rules added at MEDIUM level. Filler verb phrases that don't
# carry meaning and redundant intensifiers.
MEDIUM_EXTRA: list[tuple[str, str]] = [
    # filler verb phrases at the start of a request
    (r"\bi would like (you )?to\b", ""),
    (r"\bi want (you )?to\b", ""),
    (r"\bi need (you )?to\b", ""),
    (r"\bcan you (please )?\b", ""),
    (r"\bcould you (please )?\b", ""),
    (r"\bwould you (please )?\b", ""),
    (r"\bwill you (please )?\b", ""),
    (r"\bdo you (think you )?(can|could) (please )?\b", ""),
    # redundant intensifiers
    (r"\b(very|really|actually|basically|literally|just|simply)\b\s*", ""),
]

# Extra rules added at AGGRESSIVE level. Stopword adjectives, common
# wordy phrases collapsed to a shorter equivalent.
AGGRESSIVE_EXTRA: list[tuple[str, str]] = [
    # wordy phrase collapses
    (r"\bin order to\b", "to"),
    (r"\bdue to the fact that\b", "because"),
    (r"\bin spite of the fact that\b", "although"),
    (r"\bat this point in time\b", "now"),
    (r"\ba large number of\b", "many"),
    (r"\bthe majority of\b", "most"),
    (r"\bfor the purpose of\b", "to"),
    (r"\bwith regard to\b", "about"),
    (r"\bin the event that\b", "if"),
    (r"\bas a matter of fact\b", ""),
    (r"\bit is important to note that\b", ""),
    (r"\bplease note that\b", ""),
    # filler adjectives (stopwords that rarely change request intent)
    (r"\b(nice|good|great|cool|awesome|amazing|wonderful|fantastic)\b\s*", ""),
    # quick contractions
    (r"\bdo not\b", "don't"),
    (r"\bcan not\b", "can't"),
    (r"\bwill not\b", "won't"),
    (r"\bit is\b", "it's"),
    (r"\byou are\b", "you're"),
    (r"\bthat is\b", "that's"),
]


def rules_for_level(level_value: int) -> list[tuple[str, str]]:
    """Return the ordered rule list that applies at `level_value`.

    Level values are the integer values of the `Level` enum. Higher
    levels include all rules from lower levels. Whitespace normalization
    is applied separately by the compressor.
    """
    if level_value <= 1:
        return list(LIGHT_RULES)
    if level_value == 2:
        return LIGHT_RULES + MEDIUM_EXTRA
    return LIGHT_RULES + MEDIUM_EXTRA + AGGRESSIVE_EXTRA
