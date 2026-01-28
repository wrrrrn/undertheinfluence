"""
Entity normalization utilities for UnderTheInfluence.

This module provides functions for normalizing actor names to enable
entity resolution while avoiding false positives.

Phase 3.1 Implementation - Weighted Alias System
"""

import re
from typing import Tuple

# Common titles/honorifics to strip during weak normalization
TITLES = [
    'lord', 'baroness', 'sir', 'dame', 'dr', 'prof', 'mr', 'mrs', 'ms', 'cllr',
    'rt', 'hon', 'rev', 'viscount', 'earl', 'countess', 'duke', 'duchess'
]

def normalize_actor_name(name: str, strength: str = 'weak') -> str:
    """
    Normalize an actor name for entity resolution.

    Applies different normalization levels based on the desired alias strength:

    - **Strong**: Conservative normalization (case, whitespace, basic punctuation)
      Preserves enough structure to avoid false positives.
      Example: "Unite the Union" → "Unite the Union"

    - **Weak**: Aggressive normalization (lowercase, remove all punctuation)
      Useful for fuzzy matching but higher false positive rate.
      Example: "Unite the Union" → "unite union"

    Args:
        name: The actor name to normalize
        strength: Either 'strong' or 'weak' (default: 'weak')

    Returns:
        Normalized name string

    Examples:
        >>> normalize_actor_name("Unite the Union", strength='strong')
        "Unite the Union"

        >>> normalize_actor_name("Unite the Union", strength='weak')
        "unite union"

        >>> normalize_actor_name("St. John's College, Oxford", strength='weak')
        "st johns college oxford"

    See Also:
        - OtherName.alias_type field
        - build_search_key() for additional search optimization
    """
    if not name:
        return ""

    # Start with basic cleanup - applies to all strengths
    normalized = name.strip()

    # Quality fixes (applied before normalization):
    # 1. Convert long whitespace runs to semicolons (tabular data)
    #    "Company                    Person" -> "Company; Person"
    normalized = re.sub(r'\s{6,}', '; ', normalized)

    # 2. Remove trailing punctuation (commas, semicolons, colons)
    normalized = re.sub(r'[,;:]+$', '', normalized)

    # 3. Remove leading punctuation
    normalized = re.sub(r'^[,;:\-]+\s*', '', normalized)

    if strength == 'strong':
        # Conservative normalization - preserve structure
        # Collapse remaining multiple spaces to single space
        normalized = re.sub(r'  +', ' ', normalized)
        # Remove trailing periods from abbreviations but keep apostrophes
        normalized = re.sub(r'\.$', '', normalized)
        return normalized.strip()

    elif strength == 'weak':
        # Aggressive normalization - fuzzy matching
        # Convert to lowercase
        normalized = normalized.lower()

        # Remove punctuation (except spaces initially)
        normalized = re.sub(r'[^\w\s]', '', normalized)

        # Remove leading "THE " - very common variant
        # "THE TRUSSELL TRUST" -> "TRUSSELL TRUST"
        normalized = re.sub(r'^the\s+', '', normalized)

        # Remove common legal suffixes (expanded list matching CH matcher)
        legal_suffixes = [
            r'\b(limited|ltd)\b',
            r'\b(public limited company|plc)\b',
            r'\b(llp)\b',
            r'\b(llc)\b',
            r'\b(incorporated|inc)\b',
            r'\b(corporation|corp)\b',
            r'\b(company|co)\b',
            r'\b(uk|gb)\b',  # Geographic suffixes
            r'\b(holdings?)\b',
            r'\b(group)\b',
            r'\b(international|intl)\b',
            r'\b(services?)\b',
            r'\b(solutions?)\b',
            r'\b(partners?|partnership)\b',
        ]
        for suffix in legal_suffixes:
            normalized = re.sub(suffix, '', normalized)

        # Remove common words that add no meaning
        normalized = re.sub(r'\b(the|and|of|for)\b', '', normalized)

        # Remove titles/honorifics
        titles_pattern = r'\b(' + '|'.join(TITLES) + r')\b'
        normalized = re.sub(titles_pattern, '', normalized)

        # Collapse whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        # Final trim
        normalized = normalized.strip()
        return normalized

    else:
        raise ValueError(f"Invalid strength: {strength}. Must be 'strong' or 'weak'.")


def build_search_key(name: str) -> str:
    """
    Build a search key for fast entity lookup.

    Creates a simplified, sortable key for indexing actors. This is useful
    for building lookup tables and search indexes.

    Implementation:
    - Lowercase
    - Remove all punctuation and special characters
    - Remove whitespace
    - Sort words alphabetically (handles word order variations)

    Args:
        name: The actor name

    Returns:
        Search key string (alphanumeric, sorted words)

    Examples:
        >>> build_search_key("Unite the Union")
        "theuniounite"

        >>> build_search_key("Union, the Unite")  # Same key despite word order
        "theuniounite"

        >>> build_search_key("St. John's College")
        "collegejonesst"

    Use Cases:
        - Building actor lookup tables by normalized name
        - Deduplication during data import
        - Search autocomplete indexing
    """
    if not name:
        return ""

    # Normalize first (weak mode strips titles/punctuation)
    clean = normalize_actor_name(name, strength='weak')

    # Remove all non-alphanumeric characters (just in case normalize left any, though it shouldn't)
    clean = re.sub(r'[^\w\s]', '', clean)

    # Split into words and sort alphabetically
    words = sorted(clean.split())

    # Join without spaces
    return ''.join(words)


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculate similarity score between two actor names.

    Uses a combination of:
    1. Exact match on strong normalization (weight: 0.5)
    2. Weak normalization Levenshtein distance (weight: 0.5)

    Args:
        name1: First actor name
        name2: Second actor name

    Returns:
        Similarity score from 0.0 (completely different) to 1.0 (identical)

    Examples:
        >>> calculate_name_similarity("Unite the Union", "Unite")
        0.75  # High similarity

        >>> calculate_name_similarity("Unite the Union", "UNISON")
        0.2   # Low similarity

    Note:
        This is a simple implementation. For production, consider using
        more sophisticated algorithms like:
        - Jaro-Winkler distance
        - Cosine similarity on character n-grams
        - phonetic algorithms (Metaphone, Soundex)
    """
    if not name1 or not name2:
        return 0.0

    # Exact match after strong normalization
    strong1 = normalize_actor_name(name1, strength='strong')
    strong2 = normalize_actor_name(name2, strength='strong')

    if strong1 == strong2:
        return 1.0

    # Weak normalization match
    weak1 = normalize_actor_name(name1, strength='weak')
    weak2 = normalize_actor_name(name2, strength='weak')

    if weak1 == weak2:
        return 0.85

    # Calculate Levenshtein distance for partial similarity
    distance = levenshtein_distance(weak1, weak2)
    max_len = max(len(weak1), len(weak2))

    if max_len == 0:
        return 0.0

    # Convert distance to similarity (0-1 range)
    similarity = 1.0 - (distance / max_len)

    return max(0.0, similarity)


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein (edit) distance between two strings.

    The Levenshtein distance is the minimum number of single-character
    edits (insertions, deletions, or substitutions) required to change
    one string into the other.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Edit distance (integer >= 0)

    Example:
        >>> levenshtein_distance("kitten", "sitting")
        3

    Reference:
        https://en.wikipedia.org/wiki/Levenshtein_distance
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)

    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def get_confidence_level(similarity: float, has_identifier_match: bool = False,
                        has_strong_alias: bool = False) -> Tuple[float, str]:
    """
    Determine entity resolution confidence level.

    Confidence Levels (from Backend Architecture Strategy):
    1. 1.0 - Identifier Match: External ID match (EC donor ID, ParlParse person ID)
    2. 0.90 - Strong Alias Match: High-confidence name variant
    3. 0.85 - Exact Strong Normalization: Exact match after conservative normalization
    4. 0.70 - Weak Alias Match: Match on aggressive normalization
    5. 0.40 - Fuzzy Match: Levenshtein distance suggests similarity

    Args:
        similarity: Similarity score from calculate_name_similarity()
        has_identifier_match: True if external identifiers match
        has_strong_alias: True if match via strong alias

    Returns:
        Tuple of (confidence_score, decision)
        decision is one of: 'auto_merge', 'review', 'suggest', 'ignore'

    Examples:
        >>> get_confidence_level(1.0, has_identifier_match=True)
        (1.0, 'auto_merge')

        >>> get_confidence_level(0.85, has_strong_alias=True)
        (0.90, 'review')

        >>> get_confidence_level(0.75, has_strong_alias=False)
        (0.70, 'suggest')

    Decision Logic:
        - auto_merge: >= 1.0 (identifier match only)
        - review: >= 0.85 (strong alias, requires manual approval)
        - suggest: >= 0.70 (weak alias, show to user but don't auto-apply)
        - ignore: < 0.70 (too uncertain, don't show)
    """
    if has_identifier_match:
        return (1.0, 'auto_merge')

    if has_strong_alias and similarity >= 0.85:
        return (0.90, 'review')

    if similarity >= 0.85:
        return (0.85, 'review')

    if similarity >= 0.70:
        return (0.70, 'suggest')

    if similarity >= 0.40:
        return (0.40, 'ignore')

    return (0.0, 'ignore')
