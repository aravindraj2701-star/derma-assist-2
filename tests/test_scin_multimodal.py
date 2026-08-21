"""
Unit and Integration Tests for Google SCIN Multimodal System
"""

import os
import sys
import numpy as np
import torch
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.scin_predictor import (
    get_scin_model,
    encode_structured_symptoms,
    predict_scin_multimodal,
    DEFAULT_CONDITIONS,
)


def test_tabular_encoding():
    print("Testing tabular symptom encoding...")
    symptom_payload = {
        "body_part": "arm",
        "condition_duration": "ONE_TO_FOUR_WEEKS",
        "textures": ["rough_or_flaky", "raised_or_bumpy"],
        "itching": True,
        "burning": False,
        "pain": False,
        "bleeding": False,
        "increasing_size": False,
        "darkening": False,
        "age_group": "AGE_30_TO_39",
        "sex_at_birth": "FEMALE",
        "fitzpatrick_skin_type": "FST3",
    }

    vec = encode_structured_symptoms(symptom_payload)
    assert isinstance(vec, np.ndarray), "Encoded vector must be numpy array"
    assert vec.shape == (58,), f"Expected shape (58,), got {vec.shape}"
    assert vec[1] == 1.0, "Body part 'arm' should be encoded as 1.0"
    print("  [OK] Tabular symptom encoding verified (shape: 58).")


def test_model_inference():
    print("Testing multimodal model loading and inference...")
    model, meta = get_scin_model()
    assert model is not None, "Model failed to load"
    assert len(meta["conditions"]) == 20, f"Expected 20 conditions, got {len(meta['conditions'])}"

    # Create synthetic test image
    test_img = Image.new("RGB", (224, 224), color=(180, 120, 100))

    symptom_payload = {
        "body_part": "leg",
        "condition_duration": "ONE_TO_SIX_MONTHS",
        "textures": ["raised_or_bumpy"],
        "itching": True,
        "burning": False,
        "pain": False,
        "bleeding": False,
        "increasing_size": True,
        "darkening": True,
        "age_group": "AGE_40_TO_49",
        "sex_at_birth": "MALE",
        "fitzpatrick_skin_type": "FST4",
    }

    result = predict_scin_multimodal(test_img, symptom_payload)
    assert "primary_prediction" in result, "Missing primary_prediction"
    assert "differential_diagnoses" in result, "Missing differential_diagnoses"
    assert "all_predictions" in result, "Missing all_predictions"
    assert len(result["all_predictions"]) == 5, "Expected top-5 predictions"
    assert "fairness_context" in result, "Missing fairness_context"

    primary = result["primary_prediction"]
    print(f"  [OK] Multimodal Prediction: {primary['condition']} (Confidence: {primary['confidence_pct']}%)")
    print(f"  [OK] Differential diagnoses: {[d['condition'] for d in result['differential_diagnoses']]}")
    print(f"  [OK] Fairness context: {result['fairness_context']['fitzpatrick_group']}")


if __name__ == "__main__":
    test_tabular_encoding()
    test_model_inference()
    print("\n[OK] All SCIN Multimodal unit tests passed successfully!")
