import re
from typing import List, Tuple
from rapidfuzz import fuzz, process

def find_similar_merchants(target: str, existing_merchants: List[str], threshold: int = 70) -> List[Tuple[str, float]]:
    """
    Finds merchants in the existing list that are similar to the target string.
    Returns a list of tuples (merchant_name, score) sorted by score descending.
    """
    if not target or not existing_merchants:
        return []
    
    # Use token_sort_ratio to be robust against word order (e.g. "WALMART CASHI" vs "CASHI WALMART")
    matches = process.extract(
        target, 
        existing_merchants, 
        scorer=fuzz.token_sort_ratio, 
        limit=5
    )
    
    return [(m, score) for m, score, _ in matches if score >= threshold]

def normalize_for_matching(text: str) -> str:
    """
    Cleans a description or merchant name for more robust matching.
    Removes numbers, extra spaces, and common noise.
    """
    if not text:
        return ""
    # Lowercase
    s = text.lower()
    # Remove numbers
    s = re.sub(r"\d+", "", s)
    # Remove extra whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s
