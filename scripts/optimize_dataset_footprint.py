"""
Dataset and Symptom Footprint Optimization Script
Target: 50MB - 60MB total footprint.
- Scales 9-class ISIC dataset to 80 images/class (60 train, 10 val, 10 test) @ 300px JPEG
- Scales SCIN dataset to 35 images/condition @ 300px JPEG
- Prunes duplicate multi-gigabyte data/ folders
- Compresses symptom dataset to ~625 rich balanced profiles
- Retains all required clinical features and metadata
"""

import os
import shutil
import glob
import json
from PIL import Image
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(PROJECT_ROOT, "dataset")
SCIN_DIR = os.path.join(DATASET_DIR, "scin")
SCIN_IMAGES_DIR = os.path.join(SCIN_DIR, "images")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

TARGET_MAX_PX = 300
JPEG_QUALITY = 80


def optimize_and_save_image(src_path, dst_path, max_dim=TARGET_MAX_PX, quality=JPEG_QUALITY):
    try:
        with Image.open(src_path) as img:
            img = img.convert("RGB")
            # Downscale proportionally if larger than max_dim
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            img.save(dst_path, "JPEG", quality=quality, optimize=True)
            return True
    except Exception as e:
        print(f"Error processing {src_path}: {e}")
        return False


def optimize_isic_dataset():
    print("\n--- 1. Optimizing 9-Class ISIC Dataset (80 images/class: 60 train, 10 val, 10 test) ---")
    splits_target = {
        "train": 60,
        "validation": 10,
        "test": 10
    }
    
    for split, target_count in splits_target.items():
        split_dir = os.path.join(DATASET_DIR, split)
        if not os.path.exists(split_dir):
            continue
            
        for category in sorted(os.listdir(split_dir)):
            cat_dir = os.path.join(split_dir, category)
            if not os.path.isdir(cat_dir):
                continue
                
            files = [f for f in sorted(os.listdir(cat_dir)) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            keep_files = files[:target_count]
            remove_files = files[target_count:]
            
            # Downscale kept files in place
            for f in keep_files:
                fpath = os.path.join(cat_dir, f)
                optimize_and_save_image(fpath, fpath)
                
            # Remove surplus files
            for f in remove_files:
                fpath = os.path.join(cat_dir, f)
                try:
                    os.remove(fpath)
                except Exception:
                    pass
            print(f"  [{split}] {category}: Kept & optimized {len(keep_files)} images (removed {len(remove_files)})")


def optimize_scin_dataset():
    print("\n--- 2. Optimizing Google SCIN Images (Max 35 images per condition) ---")
    if not os.path.exists(SCIN_IMAGES_DIR):
        print("  SCIN images directory not found, skipping.")
        return

    # Load SCIN metadata to group images by condition
    cases_csv = os.path.join(SCIN_DIR, "metadata", "scin_cases.csv")
    labels_csv = os.path.join(SCIN_DIR, "metadata", "scin_labels.csv")
    
    selected_image_files = set()
    
    if os.path.exists(cases_csv) and os.path.exists(labels_csv):
        df_cases = pd.read_csv(cases_csv)
        df_labels = pd.read_csv(labels_csv)
        
        # Merge on case_id
        df_merged = pd.merge(df_cases, df_labels, on="case_id", how="inner")
        condition_col = "weighted_skin_condition_label" if "weighted_skin_condition_label" in df_merged.columns else "condition"
        
        # Sample up to 35 images per condition
        if condition_col in df_merged.columns:
            for cond, group in df_merged.groupby(condition_col):
                sample_rows = group.head(35)
                for _, row in sample_rows.iterrows():
                    for col in ["image_1_path", "image_2_path", "image_3_path"]:
                        if col in row and pd.notna(row[col]):
                            fname = os.path.basename(str(row[col]))
                            selected_image_files.add(fname)
                            
    all_files = [f for f in os.listdir(SCIN_IMAGES_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if not selected_image_files:
        # Fallback: keep first 700 images
        selected_image_files = set(all_files[:700])
        
    kept_count = 0
    removed_count = 0
    
    for f in all_files:
        fpath = os.path.join(SCIN_IMAGES_DIR, f)
        if f in selected_image_files:
            optimize_and_save_image(fpath, fpath)
            kept_count += 1
        else:
            try:
                os.remove(fpath)
                removed_count += 1
            except Exception:
                pass
                
    print(f"  SCIN Images: Kept & optimized {kept_count} images (removed {removed_count})")


def prune_duplicate_data_dirs():
    print("\n--- 3. Pruning Multi-Gigabyte Duplicate data/ Folders ---")
    duplicate_dirs = [
        os.path.join(DATA_DIR, "multiple_skin_disease"),
        os.path.join(DATA_DIR, "skin_dataset"),
    ]
    for d in duplicate_dirs:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
            print(f"  Removed redundant duplicate folder: {d}")


def optimize_symptom_dataset():
    print("\n--- 4. Optimizing Symptom Dataset to ~625 Compact Profiles ---")
    symptom_csv = os.path.join(PROJECT_ROOT, "combined_skin_disease_dataset_v2.csv")
    if os.path.exists(symptom_csv):
        df = pd.read_csv(symptom_csv)
        col = "label" if "label" in df.columns else ("disease" if "disease" in df.columns else None)
        if col:
            # Sample up to 25 representative rows per disease
            df_sampled = df.groupby(col, group_keys=False).apply(lambda g: g.head(25))
            df_sampled.to_csv(symptom_csv, index=False)
            print(f"  Saved {len(df_sampled)} compact symptom rows across {df_sampled[col].nunique()} conditions to {symptom_csv}")


def cleanup_large_model_caches():
    print("\n--- 5. Cleaning Heavy JSON Cache Files ---")
    large_json = os.path.join(MODELS_DIR, "reference_image_embeddings.json")
    if os.path.exists(large_json):
        # We rely on reference_embeddings_matrix.npz and canonical_references.json for instant <10ms lookup
        try:
            os.remove(large_json)
            print(f"  Removed uncompressed 50MB JSON cache ({large_json}) - using fast .npz matrix instead.")
        except Exception as e:
            print(f"  Notice removing JSON: {e}")


def main():
    print("Starting Dataset & Symptom Footprint Optimization (Target: ~50MB - 60MB)...")
    optimize_isic_dataset()
    optimize_scin_dataset()
    prune_duplicate_data_dirs()
    optimize_symptom_dataset()
    cleanup_large_model_caches()
    print("\nOptimization Complete!")


if __name__ == "__main__":
    main()
