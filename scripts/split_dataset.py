"""
Dataset Splitter — Stratified splitting into train/validation/test sets.

Usage:
  python scripts/split_dataset.py --input dataset/all --output dataset/ --train 0.70 --val 0.15 --test 0.15

Splits a flat dataset (one folder per class) into train/validation/test
with stratified sampling to ensure every class is represented in all splits.
"""

import os
import sys
import shutil
import random
import argparse
from collections import defaultdict


def split_dataset(
    input_dir: str,
    output_dir: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
):
    """
    Split a flat dataset into train/validation/test with stratified sampling.

    Args:
        input_dir: Path to the flat dataset (one subfolder per class)
        output_dir: Where to create train/, validation/, test/ folders
        train_ratio: Fraction for training set
        val_ratio: Fraction for validation set
        test_ratio: Fraction for test set
        seed: Random seed for reproducibility
    """
    # Validate ratios
    total = train_ratio + val_ratio + test_ratio
    if abs(total - 1.0) > 0.01:
        print(f"[ERROR] Ratios must sum to 1.0 (got {total:.2f})")
        sys.exit(1)

    if not os.path.isdir(input_dir):
        print(f"[ERROR] Input directory not found: {input_dir}")
        sys.exit(1)

    random.seed(seed)

    SUPPORTED = {".jpg", ".jpeg", ".png"}

    # Discover classes and images
    class_images = defaultdict(list)
    for class_name in sorted(os.listdir(input_dir)):
        class_path = os.path.join(input_dir, class_name)
        if not os.path.isdir(class_path):
            continue

        for filename in os.listdir(class_path):
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED:
                class_images[class_name].append(
                    os.path.join(class_path, filename)
                )

    if not class_images:
        print("[ERROR] No image classes found in input directory.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  DATASET SPLITTER")
    print(f"{'='*60}")
    print(f"  Input: {input_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Ratios: train={train_ratio}, val={val_ratio}, test={test_ratio}")
    print(f"  Classes: {len(class_images)}")
    print(f"{'='*60}")

    # Create output directories
    splits = {"train": train_ratio, "validation": val_ratio, "test": test_ratio}
    for split in splits:
        for class_name in class_images:
            os.makedirs(os.path.join(output_dir, split, class_name), exist_ok=True)

    # Stratified split per class
    total_stats = {"train": 0, "validation": 0, "test": 0}

    for class_name, images in sorted(class_images.items()):
        random.shuffle(images)
        n = len(images)

        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        n_test = n - n_train - n_val  # Remainder goes to test

        # Ensure at least 1 image per split if possible
        if n >= 3:
            n_train = max(n_train, 1)
            n_val = max(n_val, 1)
            n_test = max(n_test, 1)
            # Recalculate to not exceed total
            excess = (n_train + n_val + n_test) - n
            if excess > 0:
                n_train -= excess

        split_assignments = {
            "train": images[:n_train],
            "validation": images[n_train : n_train + n_val],
            "test": images[n_train + n_val :],
        }

        print(f"\n  {class_name}:")
        for split_name, split_images in split_assignments.items():
            for src_path in split_images:
                filename = os.path.basename(src_path)
                dst_path = os.path.join(output_dir, split_name, class_name, filename)
                shutil.copy2(src_path, dst_path)

            count = len(split_images)
            total_stats[split_name] += count
            print(f"    {split_name:<12} {count:>5} images")

    # Final summary
    print(f"\n{'='*60}")
    print(f"  SPLIT COMPLETE!")
    print(f"{'='*60}")
    for split_name, count in total_stats.items():
        print(f"  {split_name:<12} {count:>6} images")
    print(f"  {'TOTAL':<12} {sum(total_stats.values()):>6} images")
    print(f"{'='*60}\n")

    # Check for duplicates
    all_files = set()
    duplicates = 0
    for split in ["train", "validation", "test"]:
        split_dir = os.path.join(output_dir, split)
        for root, dirs, files in os.walk(split_dir):
            for f in files:
                full_path = os.path.join(root, f)
                # Use relative path + filename as identifier
                rel = os.path.relpath(full_path, output_dir)
                if f in all_files:
                    duplicates += 1
                all_files.add(f)

    if duplicates > 0:
        print(f"  ⚠️  Found {duplicates} potential duplicate filenames across splits")
    else:
        print(f"  ✅ No duplicate images across splits")


def main():
    parser = argparse.ArgumentParser(
        description="Split a flat dataset into train/validation/test"
    )
    parser.add_argument("--input", required=True, help="Input dataset directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--train", type=float, default=0.70, help="Train ratio (default: 0.70)")
    parser.add_argument("--val", type=float, default=0.15, help="Validation ratio (default: 0.15)")
    parser.add_argument("--test", type=float, default=0.15, help="Test ratio (default: 0.15)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    split_dataset(
        input_dir=args.input,
        output_dir=args.output,
        train_ratio=args.train,
        val_ratio=args.val,
        test_ratio=args.test,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
