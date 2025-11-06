"""Utilities to estimate Malay syllable counts and approximate duration."""

from typing import Dict, List

VOWELS = set("aeiouAEIOU")


def estimate_syllables_ms(text: str) -> int:
    """Very rough syllable estimate for Malay: count vowel groups.

    This is intentionally simple and fast; good enough for batch gating.
    """
    if not text:
        return 0
    count = 0
    prev_is_vowel = False
    for ch in text:
        is_vowel = ch in VOWELS
        if is_vowel and not prev_is_vowel:
            count += 1
        prev_is_vowel = is_vowel
    return max(1, count)


def estimate_dialogue_syllables(dialogue: List[Dict]) -> int:
    total = 0
    for turn in dialogue:
        total += estimate_syllables_ms(turn.get("text", ""))
    return total


def estimate_minutes_from_syllables(syllables: int) -> float:
    # Client proxy: 300–350 syllables / minute → use 325 midpoint
    return syllables / 325.0


