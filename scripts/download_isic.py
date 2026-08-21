"""
ISIC Dataset Downloader — Downloads curated skin lesion images and metadata from ISIC Archive API.
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from pathlib import Path
from tqdm import tqdm

ISIC_API_BASE = "https://api.isic-archive.com/api/v2"
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "dataset" / "isic"
METADATA_FILE = BASE_DIR / "dataset" / "isic_metadata.csv"

# Target diagnostic classes
TARGET_DIAGNOSES = [
    "melanoma",
    "basal cell carcinoma",
    "squamous cell carcinoma",
    "nevus",
    "seborrheic keratosis",
    "dermatofibroma",
    "vascular lesion",
    "actinic keratosis",
]

DIAGNOSIS_MAPPING = {
    "melanoma": "Melanoma",
    "basal cell carcinoma": "Basal Cell Carcinoma",
    "squamous cell carcinoma": "Squamous Cell Carcinoma",
    "nevus": "Nevus",
    "seborrheic keratosis": "Benign Keratosis",
    "dermatofibroma": "Dermatofibroma",
    "vascular lesion": "Vascular Lesion",
    "actinic keratosis": "Actinic Keratosis",
}


def download_isic_images(limit_per_class: int = 50):
    """
    Download skin lesion images and metadata from ISIC Archive API.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    print(f"\n{'='*60}")
    print(f"  ISIC ARCHIVE DOWNLOADER")
    print(f"  Target Classes: {len(TARGET_DIAGNOSES)}")
    print(f"  Limit Per Class: {limit_per_class}")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    for diagnosis in TARGET_DIAGNOSES:
        canonical_name = DIAGNOSIS_MAPPING.get(diagnosis, diagnosis.title())
        class_dir = OUTPUT_DIR / canonical_name
        class_dir.mkdir(parents=True, exist_ok=True)

        print(f"[*] Querying ISIC for diagnosis: '{diagnosis}' ({canonical_name})...")
        try:
            # Query ISIC API
            params = {
                "query": f'diagnosis:"{diagnosis}"',
                "limit": limit_per_class,
            }
            res = requests.get(f"{ISIC_API_BASE}/images/search/", params=params, timeout=30)
            
            if res.status_code != 200:
                print(f"  [!] ISIC search API returned status {res.status_code}, falling back to general search...")
                res = requests.get(f"{ISIC_API_BASE}/images/", params={"limit": limit_per_class}, timeout=30)

            data = res.json()
            results = data.get("results", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

            print(f"  Found {len(results)} images for {canonical_name}")

            download_count = 0
            for item in tqdm(results, desc=f"  Downloading {canonical_name}"):
                isic_id = item.get("isic_id")
                if not isic_id:
                    continue

                # Fetch image download URL
                img_url = item.get("files", {}).get("full", {}).get("url")
                if not img_url:
                    img_url = f"{ISIC_API_BASE}/images/{isic_id}/download/"

                img_path = class_dir / f"{isic_id}.jpg"

                # Download image if not exists
                if not img_path.exists():
                    try:
                        img_res = requests.get(img_url, timeout=30, stream=True)
                        if img_res.status_code == 200:
                            with open(img_path, "wb") as f:
                                for chunk in img_res.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            download_count += 1
                        else:
                            continue
                    except Exception as err:
                        continue
                else:
                    download_count += 1

                # Extract metadata
                meta = item.get("metadata", {})
                clinical = meta.get("clinical", {})
                
                records.append({
                    "isic_id": isic_id,
                    "image_path": str(img_path.relative_to(BASE_DIR)),
                    "disease_name": canonical_name,
                    "body_location": clinical.get("anatom_site_general", "Trunk / Limbs"),
                    "is_malignant": 1 if "carcinoma" in diagnosis or "melanoma" in diagnosis else 0,
                    "dataset_source": "ISIC_Archive",
                })

        except Exception as e:
            print(f"  [ERROR] Failed querying ISIC for {diagnosis}: {e}")

    # If API had low count or network error, check if existing local ISIC images exist
    if not records:
        print("\n[*] Checking for existing downloaded ISIC images...")
        for cls_dir in OUTPUT_DIR.iterdir():
            if cls_dir.is_dir():
                for img_file in cls_dir.glob("*.jpg"):
                    records.append({
                        "isic_id": img_file.stem,
                        "image_path": str(img_file.relative_to(BASE_DIR)),
                        "disease_name": cls_dir.name,
                        "body_location": "Skin lesion",
                        "is_malignant": 1 if cls_dir.name in ["Melanoma", "Basal Cell Carcinoma", "Squamous Cell Carcinoma"] else 0,
                        "dataset_source": "ISIC_Archive",
                    })

    # Save metadata
    if records:
        df = pd.DataFrame(records)
        df.to_csv(METADATA_FILE, index=False)
        print(f"\n✅ ISIC Metadata saved to: {METADATA_FILE} ({len(records)} records)")
    else:
        print("\n[!] No ISIC images downloaded. (You can place ISIC images in dataset/isic/)")


if __name__ == "__main__":
    limit = 20
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    download_isic_images(limit_per_class=limit)
