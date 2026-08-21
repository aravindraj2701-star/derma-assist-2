"""
Builds and saves precomputed visual embeddings index using our domain-trained
ResNet34 vision backbone from models/scin_multimodal_model.pt.
"""

import os
import sys
import json
import glob
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "scin_multimodal_model.pt")
OUTPUT_JSON = os.path.join(MODELS_DIR, "reference_image_embeddings.json")

sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))
sys.path.insert(0, PROJECT_ROOT)

from scin_pipeline import TOP_CONDITIONS
from backend.models.scin_multimodal_model import SCINMultimodalModel

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# Load trained multimodal model
checkpoint = torch.load(MODEL_PATH, map_location=device)
model = SCINMultimodalModel(
    num_classes=len(TOP_CONDITIONS),
    tabular_dim=58,
    image_embed_dim=512,
    tabular_embed_dim=128,
    fusion_hidden_dim=256,
    dropout=0.3,
    pretrained_vision=False
).to(device)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()
print("[OK] Domain-trained vision backbone loaded from checkpoint.")

val_tf = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

cases_df = pd.read_csv(os.path.join(PROJECT_ROOT, "dataset", "scin", "metadata", "scin_cases.csv"), dtype={"case_id": str})
labels_df = pd.read_csv(os.path.join(PROJECT_ROOT, "dataset", "scin", "metadata", "scin_labels.csv"), dtype={"case_id": str})
merged = pd.merge(cases_df, labels_df, on="case_id")
existing_imgs = set(os.path.basename(f) for f in glob.glob(os.path.join(PROJECT_ROOT, "dataset", "scin", "images", "*.png")))

records = []
images = []

for _, row in merged.iterrows():
    primary_label = str(row.get("dermatologist_skin_condition_on_label_1", "")).strip("['\"] ")
    lbl = str(row.get("dermatologist_skin_condition_on_label_name", ""))
    w_lbl = str(row.get("weighted_skin_condition_label", ""))
    
    for col in ["image_1_path", "image_2_path", "image_3_path"]:
        p = row.get(col)
        if pd.notna(p) and isinstance(p, str):
            fname = os.path.basename(p)
            if fname in existing_imgs:
                rel_path = f"dataset/scin/images/{fname}"
                dur = str(row.get("condition_duration", "Subacute")).replace("_", " ").title()
                
                records.append({
                    "id": f"scin_{row['case_id']}",
                    "disease_name": primary_label or "Cutaneous Lesion",
                    "all_labels": f"{lbl} {w_lbl} {primary_label}",
                    "image_path": rel_path,
                    "symptoms_description": f"Verified clinical reference presentation ({dur}) from Google SCIN archive.",
                    "source": "Google SCIN Dataset",
                    "severity": "Moderate" if any(w in str(primary_label).lower() for w in ["zoster", "vasculitis", "purpura"]) else "Benign",
                })
                images.append(os.path.join(PROJECT_ROOT, rel_path))
                break

print(f"Total SCIN reference images to index: {len(images)}")

embeddings = []
batch_size = 64

for i in range(0, len(images), batch_size):
    batch_paths = images[i:i + batch_size]
    tensors = []
    for p in batch_paths:
        try:
            img = Image.open(p).convert("RGB")
            tensors.append(val_tf(img))
        except Exception:
            pass

    if tensors:
        stack = torch.stack(tensors).to(device)
        with torch.no_grad():
            feat = model.image_encoder(stack) # Shape: [B, 512]
            feat = F.normalize(feat, p=2, dim=1)
            embeddings.extend(feat.cpu().numpy().tolist())
    print(f"  Processed {len(embeddings)}/{len(images)} images...")

with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump({"records": records, "embeddings": embeddings}, f)

print(f"\n[OK] Reference visual embeddings index saved successfully to: {OUTPUT_JSON}")
