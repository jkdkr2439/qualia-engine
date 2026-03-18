"""I/P/normalize.py — NFC normalization and tokenization."""
import unicodedata, re

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return text.strip()

def tokenize(text: str) -> list[str]:
    text = normalize(text).lower()
    tokens = re.findall(r'\b\w{2,}\b', text)
    return tokens

def context_pairs(tokens: list[str], window: int = 3) -> list[tuple[str, str]]:
    pairs = []
    for i, center in enumerate(tokens):
        for j in range(max(0, i-window), min(len(tokens), i+window+1)):
            if j != i:
                pairs.append((center, tokens[j]))
    return pairs
