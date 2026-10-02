"""
Language detection for memories — rule-based and predictable.

Labels text as "en", "te", "hi" or "mixed" from the writing system it
uses, plus common romanised Telugu/Hindi words for text typed in
English letters ("Nenu K9s open chesi pod logs check chesanu").
"""

import re

TELUGU = (0x0C00, 0x0C7F)
DEVANAGARI = (0x0900, 0x097F)

# Frequent romanised words. Two or more in one text → mixed language.
ROMANISED_TELUGU = {
    "nenu", "naku", "nannu", "chesanu", "chesa", "chesi", "chesindi", "chesina",
    "emi", "enti", "ivvala", "ninna", "repu", "undi", "ledu", "kani", "inka",
    "ayindi", "chusanu", "chusa", "chusi", "cheppanu", "cheppadu", "vachindi",
    "pani", "lo", "ki", "ga",
}
ROMANISED_HINDI = {
    "maine", "mujhe", "mera", "meri", "kiya", "kiye", "hai", "hain", "tha",
    "thi", "nahi", "nahin", "kya", "aaj", "kal", "raha", "rahi", "gaya",
    "diya", "liya", "karna", "kar", "ko", "ka", "ke",
}


def _count(text: str, block: tuple[int, int]) -> int:
    lo, hi = block
    return sum(1 for ch in text if lo <= ord(ch) <= hi)


def detect_language(text: str) -> str:
    """Return "en", "te", "hi" or "mixed"."""
    te = _count(text, TELUGU)
    hi = _count(text, DEVANAGARI)
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    indic = te + hi

    if indic:
        main = "te" if te >= hi else "hi"
        # Indian script plus a fair amount of English (tech terms,
        # commands) counts as mixed.
        return "mixed" if latin >= 0.25 * (indic + latin) else main

    words = set(re.findall(r"[a-z]+", text.lower()))
    if len(words & ROMANISED_TELUGU) >= 2 or len(words & ROMANISED_HINDI) >= 2:
        return "mixed"

    return "en"