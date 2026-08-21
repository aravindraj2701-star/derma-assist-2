"""
Google SCIN Dataset Downloader
Downloads metadata CSVs and images from public GCS bucket gs://dx-scin-public-data
(via https://storage.googleapis.com/dx-scin-public-data/)
No GCP auth or billing required.
"""

import os
import io
import time
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from PIL import Image

BASE_GCS_URL = "https://storage.googleapis.com/dx-scin-public-data"
DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "scin")
METADATA_DIR = os.path.join(DATASET_DIR, "metadata")
IMAGES_DIR = os.path.join(DATASET_DIR, "images")

os.makedirs(METADATA_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)


def download_file(url: str, dest_path: str, overwrite: bool = False) -> bool:
    """Downloads a single file from a public URL with retry."""
    if os.path.exists(dest_path) and not overwrite:
        if os.path.getsize(dest_path) > 0:
            return True

    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                with open(dest_path, "wb") as f:
                    f.write(resp.content)
                return True
            else:
                time.sleep(1)
        except Exception as e:
            time.sleep(1)
    return False


def download_metadata():
    """Downloads scin_cases.csv and scin_labels.csv."""
    print("=" * 60)
    print("  Downloading SCIN Metadata CSVs...")
    print("=" * 60)

    cases_url = f"{BASE_GCS_URL}/dataset/scin_cases.csv"
    labels_url = f"{BASE_GCS_URL}/dataset/scin_labels.csv"

    cases_path = os.path.join(METADATA_DIR, "scin_cases.csv")
    labels_path = os.path.join(METADATA_DIR, "scin_labels.csv")

    success_cases = download_file(cases_url, cases_path, overwrite=False)
    success_labels = download_file(labels_url, labels_path, overwrite=False)

    if success_cases and success_labels:
        df_cases = pd.read_csv(cases_path, dtype={"case_id": str})
        df_labels = pd.read_csv(labels_path, dtype={"case_id": str})
        print(f"[OK] Downloaded scin_cases.csv: {len(df_cases)} cases ({os.path.getsize(cases_path)/1024:.1f} KB)")
        print(f"[OK] Downloaded scin_labels.csv: {len(df_labels)} label records ({os.path.getsize(labels_path)/1024:.1f} KB)")
        return df_cases, df_labels
    else:
        raise RuntimeError("Failed to download SCIN metadata CSVs from GCS.")


def download_images(df_cases: pd.DataFrame, max_images: int = 1500, max_workers: int = 16):
    """
    Downloads images listed in df_cases.
    Downloads primary image_1_path and secondary image_2_path / image_3_path.
    """
    print("=" * 60)
    print(f"  Downloading SCIN Images (target: up to {max_images} images)...")
    print("=" * 60)

    # Collect all image paths
    image_tasks = []
    for _, row in df_cases.iterrows():
        for col in ["image_1_path", "image_2_path", "image_3_path"]:
            rel_path = row.get(col)
            if pd.notna(rel_path) and isinstance(rel_path, str) and rel_path.strip():
                filename = os.path.basename(rel_path)
                dest_path = os.path.join(IMAGES_DIR, filename)
                url = f"{BASE_GCS_URL}/{rel_path}"
                image_tasks.append((url, dest_path, filename))

    # Remove duplicates while preserving order
    seen = set()
    unique_tasks = []
    for url, dest, fname in image_tasks:
        if fname not in seen:
            seen.add(fname)
            unique_tasks.append((url, dest, fname))

    if max_images and max_images < len(unique_tasks):
        unique_tasks = unique_tasks[:max_images]

    print(f"  Total unique images to download: {len(unique_tasks)}")

    # Check already existing valid images
    to_download = []
    existing_count = 0
    for url, dest, fname in unique_tasks:
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            existing_count += 1
        else:
            to_download.append((url, dest, fname))

    print(f"  Already downloaded and verified: {existing_count}")
    print(f"  Remaining to download: {len(to_download)}")

    if not to_download:
        print("[OK] All target images already downloaded.")
        return

    success_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_file, url, dest): fname for url, dest, fname in to_download}
        with tqdm(total=len(to_download), desc="Downloading images") as pbar:
            for future in as_completed(futures):
                fname = futures[future]
                try:
                    res = future.result()
                    if res:
                        success_count += 1
                except Exception as e:
                    pass
                pbar.update(1)

    print(f"[OK] Successfully downloaded {success_count} new images. Total available: {existing_count + success_count}")


if __name__ == "__main__":
    cases_df, labels_df = download_metadata()
    download_images(cases_df, max_images=1200, max_workers=16)
