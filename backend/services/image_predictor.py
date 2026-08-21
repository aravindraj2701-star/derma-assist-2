"""
Image Predictor Service — EfficientNetB0 inference for skin disease classification.
Loads model and class names dynamically from configured paths.
"""

import json
import os
import numpy as np
from pathlib import Path
from backend.config import settings

# Lazy-loaded globals
_model = None
_class_names = None
_model_config = None


def _load_model():
    """Load the trained EfficientNetB0 model (lazy initialization)."""
    global _model
    if _model is not None:
        return _model

    model_path = settings.MODEL_PATH
    if not os.path.exists(model_path):
        print(f"[WARN] Model file not found at {model_path}. Predictions will use mock mode.")
        return None

    try:
        import tensorflow as tf
        _model = tf.keras.models.load_model(model_path)
        print(f"[MODEL] Loaded model from {model_path}")
        return _model
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        return None


def _load_class_names():
    """Load class names from class_names.json."""
    global _class_names
    if _class_names is not None:
        return _class_names

    class_path = settings.CLASS_NAMES_PATH
    if not os.path.exists(class_path):
        print(f"[WARN] class_names.json not found at {class_path}. Using defaults.")
        # Fallback to disease names from database CSVs
        _class_names = _load_fallback_class_names()
        return _class_names

    with open(class_path, "r") as f:
        data = json.load(f)
        _class_names = data.get("classes", [])
        print(f"[MODEL] Loaded {len(_class_names)} class names")
        return _class_names


def _load_fallback_class_names():
    """Load disease names from CSV as fallback class names."""
    import csv
    csv_path = settings.DISEASES_CSV
    if not os.path.exists(csv_path):
        return ["Unknown"]
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row["disease_name"].strip() for row in reader if row.get("disease_name")]


def _load_model_config():
    """Load model configuration."""
    global _model_config
    if _model_config is not None:
        return _model_config

    config_path = settings.MODEL_CONFIG_PATH
    if not os.path.exists(config_path):
        _model_config = {"image_size": 224, "model": "EfficientNetB0"}
        return _model_config

    with open(config_path, "r") as f:
        _model_config = json.load(f)
        return _model_config


def get_image_size() -> int:
    """Get the configured image size for preprocessing."""
    config = _load_model_config()
    return config.get("image_size", 224)


def get_model():
    """Get the loaded model (or None if not available)."""
    return _load_model()


def get_class_names() -> list[str]:
    """Get the list of class names."""
    return _load_class_names()


def predict_image(img_array: np.ndarray) -> list[dict]:
    """
    Run inference on a preprocessed image.

    Args:
        img_array: Preprocessed image array of shape (1, H, W, 3)

    Returns:
        List of top-3 predictions with disease name and confidence score,
        sorted by confidence descending.
    """
    model = _load_model()
    class_names = _load_class_names()

    if model is None:
        # Mock mode — return placeholder predictions
        return _mock_predictions(class_names)

    try:
        import tensorflow as tf

        # Apply EfficientNet preprocessing
        processed = tf.keras.applications.efficientnet.preprocess_input(img_array.copy())

        # Run inference
        predictions = model.predict(processed, verbose=0)

        # Softmax probabilities
        if predictions.shape[-1] > 1:
            probs = predictions[0]
        else:
            probs = predictions[0]

        # Sort by probability (descending)
        sorted_indices = np.argsort(probs)[::-1]

        # Top-3 predictions
        top_3 = []
        for i, idx in enumerate(sorted_indices[:3]):
            disease_name = class_names[idx] if idx < len(class_names) else f"Class_{idx}"
            top_3.append({
                "rank": i + 1,
                "disease": disease_name,
                "confidence": float(probs[idx]),
                "class_index": int(idx),
            })

        return top_3

    except Exception as e:
        print(f"[ERROR] Prediction failed: {e}")
        return _mock_predictions(class_names)


def _mock_predictions(class_names: list[str]) -> list[dict]:
    """
    Generate mock predictions when no model is available.
    Clearly marked as mock — not real predictions.
    """
    import random
    # Use available class names but generate random scores
    # This is ONLY for development/testing without a trained model
    available = class_names[:] if class_names else ["Unknown"]
    random.shuffle(available)

    mock = []
    remaining = 1.0
    for i, name in enumerate(available[:3]):
        if i == 2:
            conf = remaining
        else:
            conf = remaining * random.uniform(0.4, 0.8)
            remaining -= conf
        mock.append({
            "rank": i + 1,
            "disease": name,
            "confidence": round(conf, 4),
            "class_index": i,
            "_mock": True,  # Flag indicating this is not a real prediction
        })

    # Sort by confidence
    mock.sort(key=lambda x: x["confidence"], reverse=True)
    for i, m in enumerate(mock):
        m["rank"] = i + 1

    return mock


def reload_model():
    """Force reload the model and class names (e.g., after retraining)."""
    global _model, _class_names, _model_config
    _model = None
    _class_names = None
    _model_config = None
    _load_model()
    _load_class_names()
    _load_model_config()
    print("[MODEL] Model and configuration reloaded.")
