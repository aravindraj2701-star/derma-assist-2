"""
Text Utilities — Cleaning and normalization for symptom text.
"""

import re
import string


def clean_symptom_text(text: str) -> str:
    """
    Clean and normalize user-entered symptom text.
    - Lowercase
    - Remove special characters (keep spaces and basic punctuation)
    - Collapse multiple spaces
    - Strip leading/trailing whitespace
    """
    if not text:
        return ""

    text = text.lower().strip()

    # Remove non-alpha characters except spaces, hyphens, and periods
    text = re.sub(r"[^a-z\s\-.]", " ", text)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_keywords(text: str) -> list[str]:
    """
    Extract meaningful keywords from symptom text.
    Removes common stop words.
    """
    stop_words = {
        "i", "me", "my", "have", "has", "had", "am", "is", "are", "was",
        "were", "be", "been", "being", "a", "an", "the", "and", "but",
        "or", "for", "nor", "on", "at", "to", "from", "by", "in", "of",
        "with", "as", "it", "its", "this", "that", "these", "those",
        "do", "does", "did", "will", "would", "shall", "should", "may",
        "might", "can", "could", "there", "here", "where", "when",
        "what", "which", "who", "whom", "how", "very", "really",
        "just", "about", "also", "some", "any", "all", "each", "every",
        "both", "few", "more", "most", "other", "into", "over", "after",
        "before", "between", "under", "again", "then", "once", "so",
        "than", "too", "not", "no", "up", "out", "off", "down",
        "since", "days", "day", "week", "weeks", "month", "months",
        "ago", "recently", "now", "five", "three", "two", "one", "four",
        "six", "seven", "eight", "nine", "ten", "many", "much", "lot",
        "started", "noticed", "getting", "got", "feel", "feeling",
    }

    cleaned = clean_symptom_text(text)
    words = cleaned.split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    return keywords
