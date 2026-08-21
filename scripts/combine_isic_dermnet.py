"""
Combine ISIC & DermNet Datasets — Merges image paths, symptoms, body locations, and malignancy flags into combined_skin_disease_dataset.csv.
"""

import os
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
ISIC_META_FILE = DATASET_DIR / "isic_metadata.csv"
DERMNET_META_FILE = DATASET_DIR / "dermnet_metadata.csv"
LOOKUP_FILE = BASE_DIR / "scripts" / "dermnet_symptoms_lookup.csv"
OUTPUT_CSV_ROOT = BASE_DIR / "combined_skin_disease_dataset.csv"
OUTPUT_CSV_DATASET = DATASET_DIR / "combined_skin_disease_dataset.csv"


def combine_datasets():
    print(f"\n{'='*60}")
    print(f"  COMBINING ISIC & DERMNET DATASETS")
    print(f"{'='*60}\n")

    # Load symptoms lookup
    symptoms_lookup = {}
    if LOOKUP_FILE.exists():
        lookup_df = pd.read_csv(LOOKUP_FILE)
        for _, row in lookup_df.iterrows():
            symptoms_lookup[row["disease_name"].lower()] = row.to_dict()

    dfs = []

    # 1. Load DermNet metadata
    if DERMNET_META_FILE.exists():
        df_dermnet = pd.read_csv(DERMNET_META_FILE)
        print(f"[*] Loaded DermNet metadata: {len(df_dermnet)} records")
        dfs.append(df_dermnet)
    else:
        print("[!] No DermNet metadata found. Running prepare_dermnet_dataset first...")
        from scripts.download_and_prepare_dermnet import prepare_dermnet_dataset
        prepare_dermnet_dataset()
        if DERMNET_META_FILE.exists():
            dfs.append(pd.read_csv(DERMNET_META_FILE))

    # 2. Load ISIC metadata
    if ISIC_META_FILE.exists():
        df_isic = pd.read_csv(ISIC_META_FILE)
        print(f"[*] Loaded ISIC metadata: {len(df_isic)} records")
        # Enrich ISIC with symptoms lookup
        for idx, row in df_isic.iterrows():
            dis_name = str(row.get("disease_name", "")).lower()
            if dis_name in symptoms_lookup:
                info = symptoms_lookup[dis_name]
                df_isic.at[idx, "symptoms"] = info.get("symptoms", "Skin lesion, pigmented spot")
                df_isic.at[idx, "severity_level"] = info.get("severity_level", "moderate")
                df_isic.at[idx, "common_name"] = info.get("common_name", row["disease_name"])
            else:
                df_isic.at[idx, "symptoms"] = "Skin lesion, irregular pigmentation or growth"
                df_isic.at[idx, "severity_level"] = "severe" if row.get("is_malignant") == 1 else "mild"
                df_isic.at[idx, "common_name"] = row["disease_name"]
        dfs.append(df_isic)

    if not dfs:
        print("[ERROR] No dataset metadata files found to combine!")
        return

    # Combine all dataframes
    combined_df = pd.concat(dfs, ignore_index=True)

    # Fill missing values
    combined_df["body_location"] = combined_df["body_location"].fillna("Trunk / Limbs")
    combined_df["is_malignant"] = combined_df["is_malignant"].fillna(0).astype(int)
    combined_df["severity_level"] = combined_df["severity_level"].fillna("moderate")
    combined_df["dataset_source"] = combined_df["dataset_source"].fillna("DermNet")

    # Standard column ordering
    cols = [
        "image_path",
        "disease_name",
        "common_name",
        "symptoms",
        "body_location",
        "severity_level",
        "is_malignant",
        "dataset_source",
    ]
    existing_cols = [c for c in cols if c in combined_df.columns]
    combined_df = combined_df[existing_cols]

    # Save to root and dataset/
    combined_df.to_csv(OUTPUT_CSV_ROOT, index=False)
    combined_df.to_csv(OUTPUT_CSV_DATASET, index=False)

    print(f"\n{'='*60}")
    print(f"  🎉 COMBINED DATASET CREATED SUCCESSFULLY!")
    print(f"  Saved to: {OUTPUT_CSV_ROOT}")
    print(f"  Total Images: {len(combined_df)}")
    print(f"  Total Disease Classes: {combined_df['disease_name'].nunique()}")
    print(f"{'='*60}")

    print("\n📊 Class Distribution:")
    for cls, count in combined_df["disease_name"].value_counts().items():
        print(f"  • {cls:<25}: {count:>4} images")

    print("\n🔍 Malignancy Distribution:")
    for mal, count in combined_df["is_malignant"].value_counts().items():
        status = "Malignant" if mal == 1 else "Benign / Non-Cancerous"
        print(f"  • {status:<25}: {count:>4} images")


if __name__ == "__main__":
    combine_datasets()
