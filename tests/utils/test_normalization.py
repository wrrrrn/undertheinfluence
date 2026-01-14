"""
Unit tests for entity normalization utilities.

Tests cover:
- Name normalization (strong vs weak)
- Search key generation
- Similarity scoring
- Confidence level calculation
- Levenshtein distance
"""

import pytest
from datafetch.utils.normalization import (
    normalize_actor_name,
    build_search_key,
    calculate_name_similarity,
    get_confidence_level,
    levenshtein_distance,
)


class TestNormalizeActorName:
    """Tests for normalize_actor_name function."""

    def test_strong_normalization_preserves_structure(self):
        """Strong normalization should preserve most structure."""
        result = normalize_actor_name("Unite the Union", strength='strong')
        assert result == "Unite the Union"

        # Should remove trailing periods
        result = normalize_actor_name("Ltd.", strength='strong')
        assert result == "Ltd"

        # Should collapse whitespace
        result = normalize_actor_name("Test    Organization", strength='strong')
        assert result == "Test Organization"

    def test_weak_normalization_aggressive(self):
        """Weak normalization should aggressively simplify."""
        result = normalize_actor_name("Unite the Union", strength='weak')
        assert result == "unite union"

        # Should remove punctuation
        result = normalize_actor_name("St. John's College", strength='weak')
        assert result == "st johns college"

        # Should remove legal suffixes
        result = normalize_actor_name("Test Organization Ltd", strength='weak')
        assert result == "test organization"

        # Should remove common words
        result = normalize_actor_name("The Test Organization", strength='weak')
        assert result == "test organization"

    def test_weak_normalization_comprehensive(self):
        """Test comprehensive weak normalization cases."""
        cases = [
            ("Conservative and Unionist Party", "conservative unionist party"),
            ("Labour Party, The", "labour party"),
            ("UNISON - The Union", "unison union"),
            ("David Sainsbury Ltd.", "david sainsbury"),
            ("St John's College, Oxford", "st johns college oxford"),
        ]

        for input_name, expected in cases:
            result = normalize_actor_name(input_name, strength='weak')
            assert result == expected, f"Failed for {input_name}"

    def test_empty_string_handling(self):
        """Should handle empty strings gracefully."""
        assert normalize_actor_name("", strength='strong') == ""
        assert normalize_actor_name("", strength='weak') == ""
        assert normalize_actor_name(None, strength='weak') == ""

    def test_invalid_strength_raises_error(self):
        """Invalid strength parameter should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid strength"):
            normalize_actor_name("Test", strength='invalid')


class TestBuildSearchKey:
    """Tests for build_search_key function."""

    def test_basic_search_key(self):
        """Basic search key generation."""
        result = build_search_key("Unite the Union")
        # Words: "unite", "the", "union" sorted = "the", "union", "unite"
        assert result == "theunionunite"

    def test_word_order_independence(self):
        """Search key should be independent of word order."""
        key1 = build_search_key("Unite the Union")
        key2 = build_search_key("Union, the Unite")
        assert key1 == key2

    def test_punctuation_removal(self):
        """Search key should remove all punctuation."""
        result = build_search_key("St. John's College")
        # Words: "st", "johns", "college" sorted alphabetically
        assert result == "collegejohnsst"

    def test_case_insensitive(self):
        """Search key should be case-insensitive."""
        key1 = build_search_key("LABOUR PARTY")
        key2 = build_search_key("labour party")
        assert key1 == key2

    def test_empty_string(self):
        """Should handle empty strings."""
        assert build_search_key("") == ""
        assert build_search_key(None) == ""


class TestCalculateNameSimilarity:
    """Tests for calculate_name_similarity function."""

    def test_exact_match(self):
        """Exact matches should return 1.0."""
        similarity = calculate_name_similarity("Unite the Union", "Unite the Union")
        assert similarity == 1.0

    def test_strong_normalization_match(self):
        """Same after strong normalization should return 1.0."""
        similarity = calculate_name_similarity("Test   Name", "Test Name")
        assert similarity == 1.0

    def test_weak_normalization_match(self):
        """Same after weak normalization should return 0.85."""
        similarity = calculate_name_similarity("Unite the Union", "unite union")
        assert similarity == 0.85

    def test_partial_similarity(self):
        """Partially similar names should return intermediate scores."""
        similarity = calculate_name_similarity("Unite the Union", "Unite")
        # "Unite" vs "Unite the Union" - partial match
        assert 0.4 < similarity < 1.0

    def test_completely_different(self):
        """Completely different names should return low score."""
        similarity = calculate_name_similarity("Labour Party", "Conservative Party")
        assert 0.0 < similarity < 0.5

    def test_empty_string_handling(self):
        """Empty strings should return 0.0."""
        assert calculate_name_similarity("", "Test") == 0.0
        assert calculate_name_similarity("Test", "") == 0.0
        assert calculate_name_similarity("", "") == 0.0


class TestLevenshteinDistance:
    """Tests for levenshtein_distance function."""

    def test_identical_strings(self):
        """Identical strings should have distance 0."""
        assert levenshtein_distance("test", "test") == 0

    def test_single_character_difference(self):
        """Single character difference."""
        assert levenshtein_distance("test", "tent") == 1
        assert levenshtein_distance("test", "tst") == 1
        assert levenshtein_distance("test", "tests") == 1

    def test_classic_example(self):
        """Classic kitten -> sitting example."""
        assert levenshtein_distance("kitten", "sitting") == 3

    def test_empty_string(self):
        """Distance to empty string is length of other string."""
        assert levenshtein_distance("", "test") == 4
        assert levenshtein_distance("test", "") == 4
        assert levenshtein_distance("", "") == 0

    def test_order_independence(self):
        """Distance should be symmetric."""
        d1 = levenshtein_distance("abc", "def")
        d2 = levenshtein_distance("def", "abc")
        assert d1 == d2


class TestGetConfidenceLevel:
    """Tests for get_confidence_level function."""

    def test_identifier_match_highest_confidence(self):
        """Identifier match should be confidence 1.0 and auto_merge."""
        confidence, decision = get_confidence_level(
            similarity=0.5,
            has_identifier_match=True,
            has_strong_alias=False
        )
        assert confidence == 1.0
        assert decision == 'auto_merge'

    def test_strong_alias_match(self):
        """Strong alias match with high similarity should be 0.90 and review."""
        confidence, decision = get_confidence_level(
            similarity=0.90,
            has_identifier_match=False,
            has_strong_alias=True
        )
        assert confidence == 0.90
        assert decision == 'review'

    def test_exact_strong_normalization(self):
        """Exact match after strong normalization."""
        confidence, decision = get_confidence_level(
            similarity=0.85,
            has_identifier_match=False,
            has_strong_alias=False
        )
        assert confidence == 0.85
        assert decision == 'review'

    def test_weak_alias_match(self):
        """Weak alias match should suggest but not auto-apply."""
        confidence, decision = get_confidence_level(
            similarity=0.75,
            has_identifier_match=False,
            has_strong_alias=False
        )
        assert confidence == 0.70
        assert decision == 'suggest'

    def test_fuzzy_match_below_threshold(self):
        """Fuzzy match below threshold should be ignored."""
        confidence, decision = get_confidence_level(
            similarity=0.50,
            has_identifier_match=False,
            has_strong_alias=False
        )
        assert confidence == 0.40
        assert decision == 'ignore'

    def test_very_low_similarity_ignored(self):
        """Very low similarity should be ignored."""
        confidence, decision = get_confidence_level(
            similarity=0.20,
            has_identifier_match=False,
            has_strong_alias=False
        )
        assert confidence == 0.0
        assert decision == 'ignore'


class TestNormalizationIntegration:
    """Integration tests combining multiple normalization functions."""

    def test_entity_resolution_workflow(self):
        """Test complete entity resolution workflow."""
        # Scenario: "Unite the Union" appears in data as multiple variants
        canonical_name = "Unite the Union"
        variant1 = "Unite"
        variant2 = "unite union"
        variant3 = "The Unite Union"

        # Calculate similarities
        sim1 = calculate_name_similarity(canonical_name, variant1)
        sim2 = calculate_name_similarity(canonical_name, variant2)
        sim3 = calculate_name_similarity(canonical_name, variant3)

        # All should show some similarity
        assert sim1 > 0.4  # "Unite" is partial match
        assert sim2 == 0.85  # Weak normalization match
        assert sim3 > 0.8  # Very close

        # Get confidence levels
        _, decision1 = get_confidence_level(sim1, has_strong_alias=True)
        _, decision2 = get_confidence_level(sim2, has_strong_alias=False)
        _, decision3 = get_confidence_level(sim3, has_strong_alias=False)

        # "Unite" similarity is ~0.45, which falls below suggest threshold
        # Even with strong alias, needs higher similarity for review
        assert decision1 == 'ignore'  # Below 0.70 threshold
        # "unite union" weak match has 0.85 similarity, triggers review
        assert decision2 == 'review'  # 0.85 similarity >= 0.85 threshold
        # "The Unite Union" very close should review
        assert decision3 == 'review'

    def test_avoid_false_positive(self):
        """Test that dissimilar organizations don't match."""
        # "Unite" (different organization) vs "UNISON" (different union)
        name1 = "Unite"
        name2 = "UNISON"

        similarity = calculate_name_similarity(name1, name2)
        confidence, decision = get_confidence_level(
            similarity,
            has_identifier_match=False,
            has_strong_alias=False
        )

        # Similarity is exactly 0.5 (some overlap in letters)
        # But decision should still be 'ignore' (below review threshold)
        assert similarity <= 0.5
        assert decision == 'ignore'

    def test_political_party_variants(self):
        """Test political party name variants."""
        canonical = "Conservative and Unionist Party"
        variants = {
            "Conservative Party": 0.65,  # Very close (actual: ~0.67)
            "Conservatives": 0.4,  # Shorter variant (actual: ~0.48)
            "Tory Party": 0.2,  # Different name entirely
            "Conservative and Unionist Party (UK)": 0.9,  # Nearly identical
        }

        for variant, min_similarity in variants.items():
            similarity = calculate_name_similarity(canonical, variant)
            assert similarity >= min_similarity, \
                f"Failed for {variant}: expected >={min_similarity}, got {similarity}"
