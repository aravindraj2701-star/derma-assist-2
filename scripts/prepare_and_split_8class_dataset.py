"""
Prepare and Split 8-Class Skin Lesion Dataset
--------------------------------------------
Classes:
1. Actinic Keratosis
2. Basal Cell Carcinoma
3. Dermatofibroma
4. Melanoma
5. Nevus
6. Pigmented Benign Keratosis
7. Seborrheic Keratosis
8. Squamous Cell Carcinoma

Steps:
- Scan raw source directory
- Verify each image (integrity & corruption test)
- Stratified Train (70%) / Val (15%) / Test (15%) split with random seed
- Save into dataset/train, dataset/validation, dataset/test
- Export combined_skin_disease_dataset.csv with clinical metadata
"""

import os
import shutil
import random
from pathlib import Path
from PIL import Image
import pandas as pd
from collections import Counter
from tqdm import tqdm

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = BASE_DIR / "data" / "skin_dataset" / "Skin Cancer Dataset"
DATASET_DIR = BASE_DIR / "dataset"
LOOKUP_FILE = BASE_DIR / "scripts" / "dermnet_symptoms_lookup.csv"
OUTPUT_CSV = BASE_DIR / "combined_skin_disease_dataset.csv"
OUTPUT_CSV_DATASET = DATASET_DIR / "combined_skin_disease_dataset.csv"

# 8 Target Classes Mapping (Handle folder spelling variants)
CLASS_MAPPING = {
    "acitinic keratosis": "Actinic Keratosis",
    "actinic keratosis": "Actinic Keratosis",
    "basal cell carcinoma": "Basal Cell Carcinoma",
    "dermatofibroma": "Dermatofibroma",
    "melanoma": "Melanoma",
    "nevus": "Nevus",
    "pigmented benign keratosis": "Pigmented Benign Keratosis",
    "seborrheic keratosis": "Seborrheic Keratosis",
    "squamous cell carcinoma": "Squamous Cell Carcinoma",
}

MALIGNANT_CLASSES = {
    "Melanoma",
    "Basal Cell Carcinoma",
    "Squamous Cell Carcinoma"
}

CATEGORY_MAPPING = {
    "Melanoma": "Malignant Skin Cancer",
    "Basal Cell Carcinoma": "Non-Melanoma Skin Cancer (Malignant)",
    "Squamous Cell Carcinoma": "Non-Melanoma Skin Cancer (Malignant)",
    "Actinic Keratosis": "Pre-cancerous Lesion",
    "Pigmented Benign Keratosis": "Benign Skin Lesion",
    "Seborrheic Keratosis": "Benign Skin Lesion",
    "Nevus": "Benign Melanocytic Lesion",
    "Dermatofibroma": "Benign Fibrous Nodule",
}

SYMPTOMS_LOOKUP = {
    "Actinic Keratosis": "Rough, scaly, gritty erythematous patch, sandpapery texture on chronically sun-exposed skin.",
    "Basal Cell Carcinoma": "Pearly translucent papule or nodule, rolled borders, telangiectasia, non-healing ulcer.",
    "Dermatofibroma": "Firm, solitary, hyperpigmented button-like nodule that dimples downward with lateral pinching.",
    "Melanoma": "Asymmetrical, irregular borders, variegated color (brown/black/red/blue), diameter >6mm, evolving lesion.",
    "Nevus": "Symmetrical, uniform brown/tan pigmented macule or papule with well-defined borders.",
    "Pigmented Benign Keratosis": "Well-demarcated stuck-on pigmented plaque, verrucous or waxy surface, follicular plugging.",
    "Seborrheic Keratosis": "Waxy, stuck-on hyperkeratotic plaque, brown to black, dull surface with horn pseudocysts.",
    "Squamous Cell Carcinoma": "Hyperkeratotic, crusted, firm erythematous plaque or nodule, may ulcerate or bleed easily.",
}

BODY_LOCATIONS = {
    "Actinic Keratosis": "Face, Scalp, Ears, Forearms, Hands",
    "Basal Cell Carcinoma": "Face, Nose, Scalp, Neck, Shoulders",
    "Dermatofibroma": "Lower extremities, Arms, Trunk",
    "Melanoma": "Trunk, Back (men), Lower legs (women), Face",
    "Nevus": "Trunk, Neck, Extremities, Face",
    "Pigmented Benign Keratosis": "Trunk, Face, Back, Neck",
    "Seborrheic Keratosis": "Chest, Back, Shoulders, Face",
    "Squamous Cell Carcinoma": "Lower lip, Ears, Face, Scalp, Dorsal hands",
}


def prepare_dataset(train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42):
    random.seed(seed)

    print("=" * 70)
    print("  8-CLASS SKIN DISEASE DATASET PREPARATION & INTEGRITY VERIFICATION")
    print("=" * 70)
    print(f"Source Directory: {SOURCE_DIR}")
    print(f"Target Directory: {DATASET_DIR}")
    print(f"Ratios: Train={train_ratio*100:.0f}%, Val={val_ratio*100:.0f}%, Test={test_ratio*100:.0f}%")
    print("-" * 70)

    # 1. Discover and validate images
    valid_images = {cls: [] for cls in set(CLASS_MAPPING.values())}
    corrupted_count = 0

    for sub_dir in SOURCE_DIR.iterdir():
        if not sub_dir.is_dir():
            continue
        folder_lower = sub_dir.name.strip().lower()
        if folder_lower not in CLASS_MAPPING:
            print(f"  [SKIPPING] Unmapped directory: {sub_dir.name}")
            continue

        canonical_class = CLASS_MAPPING[folder_lower]
        all_files = list(sub_dir.glob("*.*"))

        for file_path in all_files:
            if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                continue
            # Integrity check
            try:
                with Image.open(file_path) as img:
                    img.verify()
                # Secondary check: ensure image can be decoded and converted to RGB
                with Image.open(file_path) as img:
                    img = img.convert("RGB")
                    _ = img.size
                valid_images[canonical_class].append(file_path)
            except Exception as e:
                print(f"  [CORRUPTED] Removed/Skipped {file_path.name}: {e}")
                corrupted_count += 1

    print(f"\n[*] Total corrupted/unreadable images removed: {corrupted_count}")
    print(f"[*] Verified valid images per class:")
    total_valid = 0
    for cls_name, files in sorted(valid_images.items()):
        print(f"    • {cls_name:<30}: {len(files):>5} images")
        total_valid += len(files)
    print(f"    Total clean images across 8 classes: {total_valid}")

    # 2. Reset and create output train/val/test folders
    for split_name in ["train", "validation", "test"]:
        for cls_name in valid_images.keys():
            split_cls_dir = DATASET_DIR / split_name / cls_name
            split_cls_dir.mkdir(parents=True, exist_ok=True)

    # 3. Perform stratified split and copy files
    metadata_records = []
    split_counts = {"train": Counter(), "validation": Counter(), "test": Counter()}

    print("\n[*] Splitting and organizing images into Train / Val / Test sets...")
    for cls_name, files in valid_images.items():
        shuffled = files.copy()
        random.shuffle(shuffled)
        n = len(shuffled)

        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        n_test = n - n_train - n_val

        train_files = shuffled[:n_train]
        val_files = shuffled[n_train:n_train + n_val]
        test_files = shuffled[n_train + n_val:]

        splits = {
            "train": train_files,
            "validation": val_files,
            "test": test_files,
        }

        for split_name, split_files in splits.items():
            target_dir = DATASET_DIR / split_name / cls_name
            for src_file in split_files:
                dest_file = target_dir / src_file.name
                if not dest_file.exists():
                    shutil.copy2(src_file, dest_file)

                split_counts[split_name][cls_name] += 1
                rel_path = str(dest_file.relative_to(BASE_DIR)).replace("\\", "/")

                metadata_records.append({
                    "image_path": rel_path,
                    "source": "ISIC_HAM10000",
                    "unified_disease_label": cls_name,
                    "category": CATEGORY_MAPPING.get(cls_name, "Dermatological Lesion"),
                    "body_location": BODY_LOCATIONS.get(cls_name, "Trunk / Limbs / Face"),
                    "symptoms_description": SYMPTOMS_LOOKUP.get(cls_name, "Visible cutaneous lesion"),
                    "malignant": 1 if cls_name in MALIGNANT_CLASSES else 0,
                    "split": split_name,
                })

    # 4. Save metadata DataFrame
    df = pd.DataFrame(metadata_records)
    df.to_csv(OUTPUT_CSV, index=False)
    df.to_csv(OUTPUT_CSV_DATASET, index=False)

    print("\n" + "=" * 70)
    print("  SPLIT DISTRIBUTION SUMMARY")
    print("=" * 70)
    summary_data = []
    for cls_name in sorted(valid_images.keys()):
        tr = split_counts["train"][cls_name]
        va = split_counts["validation"][cls_name]
        te = split_counts["test"][cls_name]
        tot = tr + va + te
        summary_data.append({
            "Disease Class": cls_name,
            "Train": tr,
            "Validation": va,
            "Test": te,
            "Total": tot,
            "Malignant": "Yes" if cls_name in MALIGNANT_CLASSES else "No",
        })

    summary_df = pd.DataFrame(summary_data)
    print(summary_df.to_string(index=False))
    print("-" * 70)
    print(f"Total Dataset Images: {len(df)}")
    print(f"Dataset CSV saved: {OUTPUT_CSV}")
    print("=" * 70)


if __name__ == "__main__":
    prepare_dataset()
