"""
Tests for the Symptom Matcher Service.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.utils.text_utils import clean_symptom_text, extract_keywords


def test_clean_symptom_text():
    """Test text cleaning."""
    result = clean_symptom_text("I have ITCHY red DRY patches on my hand!")
    assert result == "i have itchy red dry patches on my hand"
    print("✅ test_clean_symptom_text passed")


def test_clean_empty():
    """Test cleaning empty string."""
    assert clean_symptom_text("") == ""
    assert clean_symptom_text(None) == ""
    print("✅ test_clean_empty passed")


def test_extract_keywords():
    """Test keyword extraction with stop word removal."""
    keywords = extract_keywords("I have itchy red dry patches on my hand for five days")
    assert "itchy" in keywords
    assert "red" in keywords
    assert "dry" in keywords
    assert "patches" in keywords
    assert "hand" in keywords
    # Stop words should be removed
    assert "have" not in keywords
    assert "for" not in keywords
    assert "five" not in keywords
    print("✅ test_extract_keywords passed")


def test_extract_empty():
    """Test keyword extraction from empty string."""
    keywords = extract_keywords("")
    assert keywords == []
    print("✅ test_extract_empty passed")


def test_special_characters():
    """Test cleaning of special characters."""
    result = clean_symptom_text("rash@#$%^& on my skin!!!")
    assert "@" not in result
    assert "rash" in result
    assert "skin" in result
    print("✅ test_special_characters passed")


if __name__ == "__main__":
    test_clean_symptom_text()
    test_clean_empty()
    test_extract_keywords()
    test_extract_empty()
    test_special_characters()
    print("\n🎉 All symptom matcher tests passed!")
