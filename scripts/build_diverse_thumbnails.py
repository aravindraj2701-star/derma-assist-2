"""
Build diverse condition thumbnails catalog.
Extracts up to 6 distinct clinical photos per condition to ensure
that multiple dataset cards of the same condition never look identical on Render.
"""

import os
import glob
import io
import base64
import json
from pathlib import Path
from PIL import Image
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "models" / "diverse_condition_thumbnails.json"

output = {}

# 1. Load existing or initialize
if OUTPUT_FILE.exists():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            output = json.load(f)
    except Exception:
        output = {}

# 2. Extract from dataset/train
train_dir = PROJECT_ROOT / "dataset" / "train"
if train_dir.exists():
    for d in sorted(os.listdir(train_dir)):
        p = train_dir / d
        if p.is_dir():
            imgs = list(p.glob("*.*"))
            samples = []
            for img_path in imgs[:8]:
                try:
                    with Image.open(img_path) as im:
                        im = im.convert("RGB")
                        im.thumbnail((240, 240), Image.Resampling.LANCZOS)
                        buf = io.BytesIO()
                        im.save(buf, format="JPEG", quality=80)
                        samples.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
                except Exception:
                    pass
            if samples:
                output[d] = samples
                print(f"ISIC condition {d}: {len(samples)} images")

# 3. Extract from dataset/scin
scin_cases = PROJECT_ROOT / "dataset" / "scin" / "metadata" / "scin_cases.csv"
scin_labels = PROJECT_ROOT / "dataset" / "scin" / "metadata" / "scin_labels.csv"
scin_img_dir = PROJECT_ROOT / "dataset" / "scin" / "images"

if scin_cases.exists() and scin_labels.exists() and scin_img_dir.exists():
    cases_df = pd.read_csv(scin_cases, dtype={"case_id": str})
    labels_df = pd.read_csv(scin_labels, dtype={"case_id": str})
    merged = pd.merge(cases_df, labels_df, on="case_id")
    for label, group in merged.groupby("dermatologist_skin_condition_on_label_name"):
        clean_label = str(label).strip("[]'\" ")
        if not clean_label or clean_label == "nan" or len(clean_label) < 3:
            continue
        if clean_label not in output:
            output[clean_label] = []
        for _, row in group.iterrows():
            if len(output[clean_label]) >= 6:
                break
            for col in ["image_1_path", "image_2_path", "image_3_path"]:
                p = row.get(col)
                if pd.notna(p):
                    fname = os.path.basename(str(p))
                    fpath = scin_img_dir / fname
                    if fpath.exists():
                        try:
                            with Image.open(fpath) as im:
                                im = im.convert("RGB")
                                im.thumbnail((240, 240), Image.Resampling.LANCZOS)
                                buf = io.BytesIO()
                                im.save(buf, format="JPEG", quality=80)
                                output[clean_label].append(base64.b64encode(buf.getvalue()).decode("utf-8"))
                                break
                        except Exception:
                            pass
        if clean_label in output and output[clean_label]:
            print(f"SCIN condition {clean_label}: {len(output[clean_label])} images")

# 4. Save to models/diverse_condition_thumbnails.json
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f)

print(f"\nSaved {len(output)} condition sets to {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size / 1024:.1f} KB)")
