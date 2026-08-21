"""
Dataset Loader — Scan, validate, and prepare skin disease image datasets.

Generates:
- class_names.json
- Dataset statistics report
"""

import os
import sys
import json
from pathlib import Path
from collections import Counter
from PIL import Image

# Configuration
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
DEFAULT_DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "dataset")
OUTPUT_DIR = os.path.dirname(__file__)


def scan_dataset(dataset_path: str = None) -> dict:
    """
    Scan a dataset directory and detect disease classes.

    Expected structure:
    dataset_path/
    ├── train/
    │   ├── Disease1/
    │   ├── Disease2/
    ├── validation/
    ├── test/

    OR:
    dataset_path/
    ├── Disease1/
    ├── Disease2/
    (flat structure — needs splitting)

    Returns a dict with dataset statistics.
    """
    if dataset_path is None:
        dataset_path = DEFAULT_DATASET_PATH

    dataset_path = os.path.abspath(dataset_path)

    if not os.path.exists(dataset_path):
        print(f"[ERROR] Dataset path does not exist: {dataset_path}")
        return {"error": "Dataset path not found", "path": dataset_path}

    print(f"\n{'='*60}")
    print(f"  DATASET SCANNER")
    print(f"  Path: {dataset_path}")
    print(f"{'='*60}")

    # Check for train/validation/test structure
    splits = ["train", "validation", "test"]
    has_splits = any(
        os.path.isdir(os.path.join(dataset_path, s)) for s in splits
    )

    stats = {
        "path": dataset_path,
        "has_splits": has_splits,
        "splits": {},
        "all_classes": set(),
        "total_images": 0,
        "corrupted_images": [],
        "unsupported_files": [],
        "class_distribution": Counter(),
    }

    if has_splits:
        for split in splits:
            split_path = os.path.join(dataset_path, split)
            if os.path.isdir(split_path):
                split_stats = _scan_split(split_path, split)
                stats["splits"][split] = split_stats
                stats["all_classes"].update(split_stats["classes"])
                stats["total_images"] += split_stats["total_images"]
                stats["corrupted_images"].extend(split_stats["corrupted"])
                stats["unsupported_files"].extend(split_stats["unsupported"])
                for cls, count in split_stats["class_counts"].items():
                    stats["class_distribution"][cls] += count
    else:
        # Flat structure — treat the entire directory as one split
        split_stats = _scan_split(dataset_path, "all")
        stats["splits"]["all"] = split_stats
        stats["all_classes"] = set(split_stats["classes"])
        stats["total_images"] = split_stats["total_images"]
        stats["corrupted_images"] = split_stats["corrupted"]
        stats["unsupported_files"] = split_stats["unsupported"]
        stats["class_distribution"] = Counter(split_stats["class_counts"])

    stats["all_classes"] = sorted(stats["all_classes"])
    stats["num_classes"] = len(stats["all_classes"])

    return stats


def _scan_split(split_path: str, split_name: str) -> dict:
    """Scan a single split directory (train/validation/test)."""
    split_stats = {
        "name": split_name,
        "path": split_path,
        "classes": [],
        "class_counts": {},
        "total_images": 0,
        "corrupted": [],
        "unsupported": [],
    }

    # Each subdirectory is a class
    for item in sorted(os.listdir(split_path)):
        class_path = os.path.join(split_path, item)
        if not os.path.isdir(class_path):
            continue

        class_name = item
        split_stats["classes"].append(class_name)

        # Count and validate images
        image_count = 0
        for filename in os.listdir(class_path):
            filepath = os.path.join(class_path, filename)
            if not os.path.isfile(filepath):
                continue

            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                split_stats["unsupported"].append(filepath)
                continue

            # Validate image
            if _is_corrupted(filepath):
                split_stats["corrupted"].append(filepath)
            else:
                image_count += 1

        split_stats["class_counts"][class_name] = image_count
        split_stats["total_images"] += image_count

    return split_stats


def _is_corrupted(filepath: str) -> bool:
    """Check if an image file is corrupted."""
    try:
        with Image.open(filepath) as img:
            img.verify()
        return False
    except Exception:
        return True


def generate_class_names(stats: dict, output_path: str = None) -> str:
    """Generate class_names.json from dataset statistics."""
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "class_names.json")

    classes = stats.get("all_classes", [])
    if not classes:
        print("[WARN] No classes found. Cannot generate class_names.json.")
        return output_path

    data = {"classes": classes}

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n[OUTPUT] class_names.json saved to: {output_path}")
    print(f"  Classes ({len(classes)}): {', '.join(classes)}")
    return output_path


def generate_model_config(stats: dict, output_path: str = None, image_size: int = 224) -> str:
    """Generate model_config.json."""
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "model_config.json")

    config = {
        "image_size": image_size,
        "num_classes": stats.get("num_classes", 0),
        "model": "EfficientNetB0",
        "classes": stats.get("all_classes", []),
    }

    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"[OUTPUT] model_config.json saved to: {output_path}")
    return output_path


def print_report(stats: dict):
    """Print a formatted dataset report."""
    print(f"\n{'='*60}")
    print(f"  DATASET STATISTICS REPORT")
    print(f"{'='*60}")
    print(f"  Total Classes: {stats.get('num_classes', 0)}")
    print(f"  Total Images: {stats.get('total_images', 0)}")
    print(f"  Has Train/Val/Test Splits: {stats.get('has_splits', False)}")

    # Per-split statistics
    for split_name, split_data in stats.get("splits", {}).items():
        print(f"\n  --- {split_name.upper()} ---")
        print(f"  Images: {split_data['total_images']}")
        print(f"  Classes: {len(split_data['classes'])}")

    # Class distribution
    print(f"\n  --- CLASS DISTRIBUTION ---")
    distribution = stats.get("class_distribution", {})
    if distribution:
        max_name_len = max(len(name) for name in distribution.keys())
        for name, count in sorted(distribution.items(), key=lambda x: -x[1]):
            bar = "█" * min(count // 10, 50)
            print(f"  {name:<{max_name_len}}  {count:>6}  {bar}")

    # Imbalance check
    if distribution:
        counts = list(distribution.values())
        max_count = max(counts)
        min_count = min(counts)
        ratio = max_count / min_count if min_count > 0 else float("inf")
        if ratio > 3:
            print(f"\n  ⚠️  CLASS IMBALANCE DETECTED (max/min ratio: {ratio:.1f}x)")
            print(f"      Consider using class weights during training.")
        else:
            print(f"\n  ✅ Class balance is acceptable (max/min ratio: {ratio:.1f}x)")

    # Corrupted images
    corrupted = stats.get("corrupted_images", [])
    if corrupted:
        print(f"\n  ⚠️  CORRUPTED IMAGES: {len(corrupted)}")
        for path in corrupted[:10]:
            print(f"      {path}")
        if len(corrupted) > 10:
            print(f"      ... and {len(corrupted) - 10} more")

    # Unsupported files
    unsupported = stats.get("unsupported_files", [])
    if unsupported:
        print(f"\n  ⚠️  UNSUPPORTED FILES: {len(unsupported)}")
        for path in unsupported[:5]:
            print(f"      {path}")

    print(f"\n{'='*60}\n")


def main():
    """Run the dataset loader as a standalone script."""
    dataset_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATASET_PATH

    stats = scan_dataset(dataset_path)

    if "error" in stats:
        print(f"\n[ERROR] {stats['error']}")
        print(f"Please place your dataset in: {dataset_path}")
        print(f"\nExpected structure:")
        print(f"  {dataset_path}/")
        print(f"  ├── train/")
        print(f"  │   ├── Disease1/")
        print(f"  │   │   ├── image001.jpg")
        print(f"  │   ├── Disease2/")
        print(f"  ├── validation/")
        print(f"  └── test/")
        return

    print_report(stats)
    generate_class_names(stats)
    generate_model_config(stats)


if __name__ == "__main__":
    main()
