import re


def clean_text(text: str) -> str:
    """Return normalized text for indexing."""
    text = text.strip().lower()
    return re.sub(r"\s+", " ", text)


def remove_stopwords(text: str, stopwords: list) -> str:
    """Remove stop words from the provided text."""
    words = [w for w in text.split() if w not in stopwords]
    return " ".join(words)
