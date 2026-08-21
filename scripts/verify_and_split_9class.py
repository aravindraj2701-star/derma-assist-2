"""
verify_and_split_9class.py
--------------------------
Step 1: Locate the 9 disease class folders in C:\\Users\\aravi\\OneDrive\\Desktop\\derma assist 2\\data\\multiple_skin_disease
Step 2: Verify the number of images in each class, screening out corrupted images.
Step 3: Perform stratified 80/10/10 train/validation/test split, copying files to dataset/train, dataset/validation, and dataset/test.
Step 4: Output validation reports and class-wise distribution.
"""

import os
import sys
import shutil
import random
from pathlib import Path
from collections import Counter
from PIL import Image

BASE_DIR = Path(r"C:\Users\aravi\OneDrive\Desktop\derma assist 2")
DATA_DIR = BASE_DIR / "data" / "multiple_skin_disease"
OUTPUT_DIR = BASE_DIR / "dataset"

# 9 target classes mapping
CLASS_MAP = {
    "acitinic keratosis": "Actinic Keratosis",
    "actinic keratosis": "Actinic Keratosis",
    "basal cell carcinoma": "Basal Cell Carcinoma",
    "dermatofibroma": "Dermatofibroma",
    "melanoma": "Melanoma",
    "nevus": "Nevus",
    "pigmented benign keratosis": "Pigmented Benign Keratosis",
    "seborrheic keratosis": "Seborrheic Keratosis",
    "squamous cell carcinoma": "Squamous Cell Carcinoma",
    "vascular lesion": "Vascular Lesion",
}


def find_dataset_root(search_dir: Path) -> Path:
    """Recursively search for a directory containing the majority of target class subfolders."""
    best_dir = None
    max_matches = 0

    for root, dirs, _ in os.walk(search_dir):
        current_dir = Path(root)
        matched_classes = 0
        for d in dirs:
            if d.strip().lower() in CLASS_MAP:
                matched_classes += 1

        if matched_classes > max_matches:
            max_matches = matched_classes
            best_dir = current_dir

    if best_dir and max_matches >= 7:  # Expect at least 7 of 9 classes to match
        return best_dir
    return None


def verify_and_split(train_ratio=0.80, val_ratio=0.10, test_ratio=0.10, seed=42):
    random.seed(seed)

    print("=" * 80)
    print("  STEP 1 & 2: SCANNING AND VERIFYING 9-CLASS DATASET")
    print("=" * 80)
    print(f"Searching under base directory: {DATA_DIR}")

    dataset_root = find_dataset_root(DATA_DIR)
    if not dataset_root:
        print("[ERROR] Could not automatically locate the folder containing the disease class subfolders.")
        sys.exit(1)

    print(f"[FOUND] Class folders located in: {dataset_root}")

    # Gather and verify image files
    class_images = {cls: [] for cls in set(CLASS_MAP.values())}
    corrupted_count = 0

    for sub_dir in dataset_root.iterdir():
        if not sub_dir.is_dir():
            continue
        folder_lower = sub_dir.name.strip().lower()
        if folder_lower not in CLASS_MAP:
            continue

        canonical_name = CLASS_MAP[folder_lower]
        all_files = list(sub_dir.glob("*.*"))

        for file_path in all_files:
            if file_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                continue
            # Try loading image to check for corruption
            try:
                with Image.open(file_path) as img:
                    img.verify()
                # Verify we can fully load it
                with Image.open(file_path) as img:
                    img = img.convert("RGB")
                    _ = img.size
                class_images[canonical_name].append(file_path)
            except Exception as e:
                print(f"  [CORRUPTED] Skipping {file_path.name}: {e}")
                corrupted_count += 1

    print("\n" + "-" * 80)
    print("  VERIFIED IMAGE COUNTS (Clean Images)")
    print("-" * 80)
    total_images = 0
    for cls_name, files in sorted(class_images.items()):
        print(f"  • {cls_name:<30}: {len(files):>5} images")
        total_images += len(files)
    print(f"  Total Clean Images across 9 classes: {total_images}")
    print(f"  Corrupted files removed/skipped: {corrupted_count}")
    print("-" * 80)

    if total_images == 0:
        print("[ERROR] No images found. Please check your dataset path.")
        sys.exit(1)

    # Clean previous splits to avoid leftovers
    if OUTPUT_DIR.exists():
        print(f"[*] Clearing existing split directory at {OUTPUT_DIR}...")
        import stat
        def make_writable_and_remove(path):
            try:
                os.chmod(path, stat.S_IWRITE)
            except Exception:
                pass
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
            except Exception:
                pass

        # Try to delete subdirectories individually
        for item in OUTPUT_DIR.glob("**/*"):
            if item.is_file():
                make_writable_and_remove(item)
        for item in OUTPUT_DIR.glob("*"):
            if item.is_dir():
                make_writable_and_remove(item)
        try:
            shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
        except Exception:
            pass

    # Create new directories
    for split in ["train", "validation", "test"]:
        for cls_name in class_images.keys():
            (OUTPUT_DIR / split / cls_name).mkdir(parents=True, exist_ok=True)

    # Perform stratified split
    split_counts = {"train": Counter(), "validation": Counter(), "test": Counter()}

    print("\n[*] Splitting and copying files into 80% Train / 10% Val / 10% Test...")
    for cls_name, files in class_images.items():
        shuffled = files.copy()
        random.shuffle(shuffled)
        n = len(shuffled)

        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        n_test = n - n_train - n_val

        splits = {
            "train": shuffled[:n_train],
            "validation": shuffled[n_train:n_train + n_val],
            "test": shuffled[n_train + n_val:],
        }

        for split_name, split_files in splits.items():
            target_dir = OUTPUT_DIR / split_name / cls_name
            for src_file in split_files:
                dest_file = target_dir / src_file.name
                shutil.copy2(src_file, dest_file)
                split_counts[split_name][cls_name] += 1

    print("\n" + "=" * 80)
    print("  DATASET SPLIT COMPLETE")
    print("=" * 80)
    summary_list = []
    for cls_name in sorted(class_images.keys()):
        tr = split_counts["train"][cls_name]
        va = split_counts["validation"][cls_name]
        te = split_counts["test"][cls_name]
        tot = tr + va + te
        summary_list.append({
            "Class": cls_name,
            "Train": tr,
            "Val": va,
            "Test": te,
            "Total": tot,
        })
        print(f"  {cls_name:<30} | Train: {tr:>4} | Val: {va:>3} | Test: {te:>3} | Total: {tot:>4}")

    print("-" * 80)
    print(f"  Total Dataset Images: {total_images}")
    print("=" * 80)


if __name__ == "__main__":
    verify_and_split()
