import re

WORD = re.compile(r"\w+", re.U)
MIN_STEM = 4
MIN_WORD = 3


def stems(text):
    words = WORD.findall((text or "").lower().replace("ё", "е"))
    return [word if len(word) <= MIN_STEM else word[:max(MIN_STEM, len(word) - 2)] for word in words
            if len(word) >= MIN_WORD]


def score(query, phrases):
    wanted = set(stems(query))
    total = 0
    for phrase in phrases:
        parts = stems(phrase)
        hits = sum(1 for part in parts if any(item.startswith(part) or part.startswith(item) for item in wanted))
        if parts and hits == len(parts):
            total += 3 * len(parts)
        elif parts:
            total += float(hits) / len(parts)
    return total
