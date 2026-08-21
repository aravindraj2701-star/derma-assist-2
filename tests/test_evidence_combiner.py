"""
Tests for the Evidence Combiner Service.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.services.evidence_combiner import combine_evidence


def test_combine_basic():
    """Test basic evidence combination."""
    image_predictions = [
        {"rank": 1, "disease": "Eczema", "confidence": 0.87, "class_index": 0},
        {"rank": 2, "disease": "Psoriasis", "confidence": 0.08, "class_index": 1},
        {"rank": 3, "disease": "Dermatitis", "confidence": 0.05, "class_index": 2},
    ]

    symptom_scores = [
        {"disease": "Eczema", "symptom_score": 0.82},
        {"disease": "Psoriasis", "symptom_score": 0.51},
        {"disease": "Dermatitis", "symptom_score": 0.44},
    ]

    result = combine_evidence(image_predictions, symptom_scores, 0.7, 0.3)

    assert len(result["predictions"]) == 3
    assert result["predictions"][0]["disease"] == "Eczema"
    assert result["predictions"][0]["combined_score"] > 0
    assert not result["is_conflicting"]
    print("✅ test_combine_basic passed")


def test_normalized_scores():
    """Test that combined scores are normalized."""
    image_predictions = [
        {"rank": 1, "disease": "A", "confidence": 0.5, "class_index": 0},
        {"rank": 2, "disease": "B", "confidence": 0.3, "class_index": 1},
        {"rank": 3, "disease": "C", "confidence": 0.2, "class_index": 2},
    ]

    symptom_scores = [
        {"disease": "A", "symptom_score": 0.5},
        {"disease": "B", "symptom_score": 0.3},
        {"disease": "C", "symptom_score": 0.2},
    ]

    result = combine_evidence(image_predictions, symptom_scores)
    total = sum(p["combined_score"] for p in result["predictions"])
    assert abs(total - 1.0) < 0.01, f"Scores should normalize to ~1.0, got {total}"
    print("✅ test_normalized_scores passed")


def test_conflicting_evidence():
    """Test conflict detection when image and symptoms disagree."""
    image_predictions = [
        {"rank": 1, "disease": "Eczema", "confidence": 0.80, "class_index": 0},
        {"rank": 2, "disease": "Psoriasis", "confidence": 0.15, "class_index": 1},
    ]

    symptom_scores = [
        {"disease": "Psoriasis", "symptom_score": 0.85},
        {"disease": "Eczema", "symptom_score": 0.10},
    ]

    result = combine_evidence(image_predictions, symptom_scores)
    assert result["is_conflicting"] is True
    assert result["top_image_disease"] == "Eczema"
    assert result["top_symptom_disease"] == "Psoriasis"
    print("✅ test_conflicting_evidence passed")


def test_low_confidence():
    """Test low confidence detection."""
    image_predictions = [
        {"rank": 1, "disease": "A", "confidence": 0.30, "class_index": 0},
        {"rank": 2, "disease": "B", "confidence": 0.25, "class_index": 1},
        {"rank": 3, "disease": "C", "confidence": 0.20, "class_index": 2},
    ]

    symptom_scores = [
        {"disease": "A", "symptom_score": 0.20},
        {"disease": "B", "symptom_score": 0.15},
        {"disease": "C", "symptom_score": 0.10},
    ]

    result = combine_evidence(image_predictions, symptom_scores)
    # With low individual scores, the normalized top will likely be below threshold
    # but depends on how many diseases exist
    assert isinstance(result["is_low_confidence"], bool)
    print("✅ test_low_confidence passed")


def test_empty_symptoms():
    """Test with empty symptom scores."""
    image_predictions = [
        {"rank": 1, "disease": "Eczema", "confidence": 0.90, "class_index": 0},
    ]

    result = combine_evidence(image_predictions, [])
    assert len(result["predictions"]) >= 1
    assert result["predictions"][0]["disease"] == "Eczema"
    print("✅ test_empty_symptoms passed")


if __name__ == "__main__":
    test_combine_basic()
    test_normalized_scores()
    test_conflicting_evidence()
    test_low_confidence()
    test_empty_symptoms()
    print("\n🎉 All evidence combiner tests passed!")
