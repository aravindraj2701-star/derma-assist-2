"""
predict_skin_disease.py
-----------------------
Inference/Prediction script for the 9-class skin disease classifier.
Accepts an image path, runs inference, and returns predicted classes with confidence.

Usage:
  python scripts/predict_skin_disease.py --image path/to/image.jpg
"""

import os
import argparse
import json
import numpy as np
import tensorflow as tf
from PIL import Image

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, "models", "skin_disease_model.keras")
DEFAULT_CLASSES_PATH = os.path.join(BASE_DIR, "models", "class_names.json")


def load_class_names(path):
    if not os.path.exists(path):
        # Fallback list of 9 classes
        return [
            "Actinic Keratosis",
            "Basal Cell Carcinoma",
            "Dermatofibroma",
            "Melanoma",
            "Nevus",
            "Pigmented Benign Keratosis",
            "Seborrheic Keratosis",
            "Squamous Cell Carcinoma",
            "Vascular Lesion"
        ]
    with open(path, "r") as f:
        data = json.load(f)
        return data.get("classes", [])


def preprocess_image(image_path, target_size=(224, 224)):
    """Load and preprocess the image to match training defaults."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Load with PIL
    img = Image.open(image_path).convert("RGB")
    # Resize
    img = img.resize(target_size)
    # Convert to numpy array in [0, 255]
    img_array = np.array(img, dtype=np.float32)
    # Add batch dimension (1, 224, 224, 3)
    img_array = np.expand_dims(img_array, axis=0)
    return img_array


def predict(image_path, model_path=DEFAULT_MODEL_PATH, classes_path=DEFAULT_CLASSES_PATH):
    print("=" * 60)
    print("  DERMA ASSIST — Skin Disease Inference Tool")
    print("=" * 60)

    # 1. Load model
    if not os.path.exists(model_path):
        print(f"[ERROR] Trained model file not found at: {model_path}")
        print("Please train the model first by running scripts/train_9class_model.py")
        return

    print(f"[*] Loading model from: {model_path} ...")
    model = tf.keras.models.load_model(model_path)
    class_names = load_class_names(classes_path)

    # 2. Preprocess image
    print(f"[*] Loading and preprocessing image: {image_path} ...")
    img_array = preprocess_image(image_path)

    # 3. Predict
    print("[*] Running inference...")
    preds = model.predict(img_array, verbose=0)[0]

    # Get top-3
    top_indices = np.argsort(preds)[::-1]

    # Metadata lookup
    DISEASE_METADATA_LOOKUP = {
        "Melanoma": {
            "symptoms": "Asymmetrical, irregular borders, variegated color (brown/black/red/blue), diameter >6mm, evolving lesion.",
            "location": "Trunk, Back (men), Lower legs (women), Face"
        },
        "Basal Cell Carcinoma": {
            "symptoms": "Pearly translucent papule or nodule, rolled borders, telangiectasia, non-healing ulcer.",
            "location": "Face, Nose, Scalp, Neck, Shoulders"
        },
        "Squamous Cell Carcinoma": {
            "symptoms": "Hyperkeratotic, crusted, firm erythematous plaque or nodule, may ulcerate or bleed easily.",
            "location": "Lower lip, Ears, Face, Scalp, Dorsal hands"
        },
        "Actinic Keratosis": {
            "symptoms": "Rough, scaly, gritty erythematous patch, sandpapery texture on chronically sun-exposed skin.",
            "location": "Face, Scalp, Ears, Forearms, Hands"
        },
        "Nevus": {
            "symptoms": "Symmetrical, uniform brown/tan pigmented macule or papule with well-defined borders.",
            "location": "Trunk, Neck, Extremities, Face"
        },
        "Pigmented Benign Keratosis": {
            "symptoms": "Well-demarcated stuck-on pigmented plaque, verrucous or waxy surface, follicular plugging.",
            "location": "Trunk, Face, Back, Neck"
        },
        "Seborrheic Keratosis": {
            "symptoms": "Waxy, stuck-on hyperkeratotic plaque, brown to black, dull surface with horn pseudocysts.",
            "location": "Chest, Back, Shoulders, Face"
        },
        "Dermatofibroma": {
            "symptoms": "Firm, solitary, hyperpigmented button-like nodule that dimples downward with lateral pinching.",
            "location": "Lower extremities, Arms, Trunk"
        },
        "Vascular Lesion": {
            "symptoms": "Bright red or purple spot, smooth dome-shaped papule, small dilated blood vessels, blenches slightly",
            "location": "Trunk, Face, Neck, Limbs, Lips"
        }
    }

    print("\n" + "-" * 50)
    print("  ANALYSIS RESULTS (Top Predictions)")
    print("-" * 50)
    for i, idx in enumerate(top_indices[:3]):
        label = class_names[idx] if idx < len(class_names) else f"Class {idx}"
        confidence = preds[idx] * 100
        print(f"  {i+1}. {label:<30} : {confidence:.2f}% confidence")
    print("-" * 50)

    # Output detailed symptom and location mapping for the top prediction
    top_label = class_names[top_indices[0]] if top_indices[0] < len(class_names) else "Unknown"
    metadata = DISEASE_METADATA_LOOKUP.get(top_label)
    if metadata:
        print("\n" + "=" * 60)
        print(f"  DETAILED INFORMATION FOR TOP PREDICTION: {top_label}")
        print("=" * 60)
        print(f"  • Mapped Symptoms     : {metadata['symptoms']}")
        print(f"  • Mapped Body Location: {metadata['location']}")
        print("=" * 60 + "\n")

    # 4. Medical Disclaimer
    print("\n" + "!" * 60)
    print("  IMPORTANT RESEARCH & EDUCATIONAL DISCLAIMER:")
    print("  This classifier is developed solely for educational and research")
    print("  purposes. It does NOT provide medical advice, diagnosis, or")
    print("  professional clinical screening. Please consult a qualified")
    print("  dermatologist or doctor for any health or medical concern.")
    print("!" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run inference on a single skin image")
    parser.add_argument("--image", required=True, help="Path to the input skin lesion image")
    parser.add_argument("--model", default=DEFAULT_MODEL_PATH, help="Path to the .keras model file")
    parser.add_argument("--classes", default=DEFAULT_CLASSES_PATH, help="Path to class_names.json")
    args = parser.parse_args()

    try:
        predict(args.image, args.model, args.classes)
    except Exception as e:
        print(f"[ERROR] Inference failed: {e}")
