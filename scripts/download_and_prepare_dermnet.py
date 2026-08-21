"""
DermNet Dataset Preparer — Organizes DermNet images and maps clinical symptoms.
"""

import os
import shutil
import pandas as pd
from pathlib import Path
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
DERMNET_DIR = DATASET_DIR / "dermnet"
METADATA_FILE = DATASET_DIR / "dermnet_metadata.csv"
LOOKUP_FILE = BASE_DIR / "scripts" / "dermnet_symptoms_lookup.csv"

# Pre-existing dataset location on machine if available
EXTERNAL_DATASET_PATH = Path(r"C:\Users\aravi\OneDrive\Desktop\derma assist\dataset")

DERMNET_CLASSES = [
    "Acne",
    "Eczema",
    "Psoriasis",
    "Rosacea",
    "Melanoma",
    "Dermatitis",
    "Ringworm",
    "Vitiligo",
    "Impetigo",
    "Urticaria",
]


def prepare_dermnet_dataset():
    """
    Scan existing DermNet / local skin disease images, organize into dataset/dermnet,
    and generate structured metadata linked to symptoms lookup.
    """
    DERMNET_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    # Load symptoms lookup if present
    symptoms_lookup = {}
    if LOOKUP_FILE.exists():
        lookup_df = pd.read_csv(LOOKUP_FILE)
        for _, row in lookup_df.iterrows():
            symptoms_lookup[row["disease_name"].lower()] = row.to_dict()

    print(f"\n{'='*60}")
    print(f"  DERMNET DATASET PREPARATION")
    print(f"  Target Classes: {len(DERMNET_CLASSES)}")
    print(f"  Output Dir: {DERMNET_DIR}")
    print(f"{'='*60}\n")

    # 1. Check if external dataset exists and copy/link images
    if EXTERNAL_DATASET_PATH.exists():
        print(f"[*] Found local dataset at: {EXTERNAL_DATASET_PATH}")
        for split_dir in EXTERNAL_DATASET_PATH.iterdir():
            if split_dir.is_dir():
                for cls_dir in split_dir.iterdir():
                    if cls_dir.is_dir():
                        cls_name = cls_dir.name
                        if cls_name == "Atopic Dermatitis":
                            cls_name = "Eczema"

                        target_cls_dir = DERMNET_DIR / cls_name
                        target_cls_dir.mkdir(parents=True, exist_ok=True)

                        for img_file in cls_dir.glob("*.*"):
                            if img_file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                                dest_file = target_cls_dir / f"{split_dir.name}_{img_file.name}"
                                if not dest_file.exists():
                                    shutil.copy2(img_file, dest_file)

    # 2. Also check if dataset/train, validation, test exist inside the current project
    for split_name in ["train", "validation", "test"]:
        split_dir = DATASET_DIR / split_name
        if split_dir.exists() and split_dir.is_dir():
            for cls_dir in split_dir.iterdir():
                if cls_dir.is_dir() and cls_dir.name not in ["isic", "dermnet"]:
                    cls_name = cls_dir.name
                    target_cls_dir = DERMNET_DIR / cls_name
                    target_cls_dir.mkdir(parents=True, exist_ok=True)
                    for img_file in cls_dir.glob("*.*"):
                        if img_file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                            dest_file = target_cls_dir / f"{split_name}_{img_file.name}"
                            if not dest_file.exists():
                                shutil.copy2(img_file, dest_file)

    # 3. Scan all images in dataset/dermnet and build metadata
    print("[*] Building metadata for DermNet images...")
    for cls_dir in DERMNET_DIR.iterdir():
        if cls_dir.is_dir():
            cls_name = cls_dir.name
            lookup_data = symptoms_lookup.get(cls_name.lower(), {})

            for img_file in cls_dir.glob("*.*"):
                if img_file.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    records.append({
                        "image_path": str(img_file.relative_to(BASE_DIR)),
                        "disease_name": cls_name,
                        "common_name": lookup_data.get("common_name", cls_name),
                        "symptoms": lookup_data.get("symptoms", "Skin irritation, visible lesion, redness"),
                        "body_location": lookup_data.get("body_location", "Face, Trunk, Limbs"),
                        "severity_level": lookup_data.get("severity_level", "moderate"),
                        "is_malignant": lookup_data.get("is_malignant", 1 if cls_name == "Melanoma" else 0),
                        "dataset_source": "DermNet",
                    })

    if records:
        df = pd.DataFrame(records)
        df.to_csv(METADATA_FILE, index=False)
        print(f"\n✅ DermNet Metadata saved to: {METADATA_FILE} ({len(records)} images mapped to symptoms)")
    else:
        print(f"\n[!] No DermNet images found. Place disease image folders in dataset/dermnet/<DiseaseName>/")


if __name__ == "__main__":
    prepare_dermnet_dataset()
