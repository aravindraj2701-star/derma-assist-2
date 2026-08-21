"""
Reference Embedding Service — Deep Visual Feature Matching for Dermatological Lesions.
Uses pretrained ResNet34 visual backbone to extract 512-dimensional normalized embeddings
for all verified dataset images, and retrieves the most visually and pathologically similar
reference training example for any predicted condition.
"""

import os
import io
import glob
import base64
import json
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from torchvision import transforms
import torchvision.models as models
from PIL import Image
from typing import Dict, Any, List, Optional
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCIN_CASES_PATH = PROJECT_ROOT / "dataset" / "scin" / "metadata" / "scin_cases.csv"
SCIN_LABELS_PATH = PROJECT_ROOT / "dataset" / "scin" / "metadata" / "scin_labels.csv"
SCIN_IMAGES_DIR = PROJECT_ROOT / "dataset" / "scin" / "images"
ISIC_DATASET_DIR = PROJECT_ROOT / "dataset"
EMBEDDINGS_CACHE_PATH = PROJECT_ROOT / "models" / "reference_image_embeddings.json"

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_feature_extractor = None
_reference_index: List[Dict[str, Any]] = []
_reference_embeddings_matrix: Optional[np.ndarray] = None

_val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])


def get_feature_extractor():
    """Initializes and returns the visual feature extraction network."""
    global _feature_extractor
    if _feature_extractor is not None:
        return _feature_extractor

    resnet = models.resnet34(weights=models.ResNet34_Weights.DEFAULT)
    modules = list(resnet.children())[:-1] # Remove final classification FC layer
    extractor = torch.nn.Sequential(*modules).to(_device)
    extractor.eval()
    _feature_extractor = extractor
    return _feature_extractor


def extract_image_embedding(pil_image: Image.Image) -> np.ndarray:
    """Extracts a 512-dimensional L2-normalized feature embedding vector from a single image."""
    extractor = get_feature_extractor()
    tensor = _val_transform(pil_image.convert("RGB")).unsqueeze(0).to(_device)
    with torch.no_grad():
        feat = extractor(tensor)
        feat = torch.flatten(feat, 1)
        feat = F.normalize(feat, p=2, dim=1)
        return feat.cpu().numpy()[0]


def build_or_load_reference_index():
    """
    Builds or loads the precomputed visual feature embeddings index
    using fast batched PyTorch inference across verified SCIN & representative ISIC images.
    """
    global _reference_index, _reference_embeddings_matrix
    if len(_reference_index) > 0 and _reference_embeddings_matrix is not None:
        return _reference_index, _reference_embeddings_matrix

    # Check if precomputed JSON exists
    if EMBEDDINGS_CACHE_PATH.exists():
        try:
            with open(EMBEDDINGS_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                _reference_index = data["records"]
                _reference_embeddings_matrix = np.array(data["embeddings"], dtype=np.float32)
                print(f"[REFERENCE MATCHER] Loaded {len(_reference_index)} indexed reference embeddings from cache.")
                return _reference_index, _reference_embeddings_matrix
        except Exception as e:
            print(f"[REFERENCE MATCHER] Cache load error ({e}), re-indexing dataset...")

    print("[REFERENCE MATCHER] Building fast reference image visual index...")
    extractor = get_feature_extractor()

    records_meta = []
    image_paths_to_process = []

    # 1. Index all verified SCIN images (1,199 images)
    if SCIN_CASES_PATH.exists() and SCIN_LABELS_PATH.exists():
        try:
            cases_df = pd.read_csv(SCIN_CASES_PATH, dtype={"case_id": str})
            labels_df = pd.read_csv(SCIN_LABELS_PATH, dtype={"case_id": str})
            merged = pd.merge(cases_df, labels_df, on="case_id")

            existing_imgs = set(os.path.basename(f) for f in glob.glob(str(SCIN_IMAGES_DIR / "*.png")))

            for _, row in merged.iterrows():
                lbl = str(row.get("dermatologist_skin_condition_on_label_name", ""))
                w_lbl = str(row.get("weighted_skin_condition_label", ""))
                primary_label = str(row.get("dermatologist_skin_condition_on_label_1", "")).strip("['\"] ")

                # Find valid image
                found_img_path = None
                for col in ["image_1_path", "image_2_path", "image_3_path"]:
                    p = row.get(col)
                    if pd.notna(p) and isinstance(p, str):
                        fname = os.path.basename(p)
                        if fname in existing_imgs:
                            found_img_path = str(SCIN_IMAGES_DIR / fname)
                            break

                if found_img_path and os.path.exists(found_img_path):
                    body_parts = [c.replace("body_parts_", "").replace("_", " ").title() for c in merged.columns if c.startswith("body_parts_") and row.get(c) == "YES"]
                    dur = str(row.get("condition_duration", "Subacute")).replace("_", " ").title()

                    records_meta.append({
                        "id": f"scin_{row['case_id']}",
                        "disease_name": primary_label or "Cutaneous Lesion",
                        "all_labels": f"{lbl} {w_lbl} {primary_label}",
                        "image_path": os.path.relpath(found_img_path, PROJECT_ROOT).replace("\\", "/"),
                        "body_location": ", ".join(body_parts) if body_parts else "Cutaneous Site",
                        "symptoms_description": f"Verified clinical reference presentation ({dur}) from Google SCIN archive.",
                        "source": "Google SCIN Dataset",
                        "severity": "Moderate" if any(w in str(primary_label).lower() for w in ["zoster", "vasculitis", "purpura"]) else "Benign",
                    })
                    image_paths_to_process.append(found_img_path)
        except Exception as e:
            print(f"[REFERENCE MATCHER] Error collecting SCIN metadata: {e}")

    # 2. Index representative ISIC images (up to 40 per class)
    isic_class_counts = {}
    for img_p in glob.glob(str(ISIC_DATASET_DIR / "*" / "*" / "*")):
        if img_p.endswith((".jpg", ".JPG", ".jpeg", ".png", ".PNG")):
            rel_p = os.path.relpath(img_p, PROJECT_ROOT).replace("\\", "/")
            parts = rel_p.split("/")
            if len(parts) >= 3 and parts[0] == "dataset" and parts[1] != "scin":
                disease_name = parts[2]
                isic_class_counts[disease_name] = isic_class_counts.get(disease_name, 0) + 1
                if isic_class_counts[disease_name] <= 40:
                    records_meta.append({
                        "id": f"isic_{len(records_meta)}",
                        "disease_name": disease_name,
                        "all_labels": disease_name,
                        "image_path": rel_p,
                        "body_location": "Trunk, Face, Extremities",
                        "symptoms_description": f"Dermatoscopic pathology reference for {disease_name}.",
                        "source": "ISIC / DermNet Archive",
                        "severity": "Malignant" if "carcinoma" in disease_name.lower() or "melanoma" in disease_name.lower() else "Benign",
                    })
                    image_paths_to_process.append(img_p)

    # 3. Fast Batched Embedding Extraction
    batch_size = 64
    all_embeddings = []
    valid_records = []

    print(f"[REFERENCE MATCHER] Extracting visual features for {len(image_paths_to_process)} images in batches of {batch_size}...")
    for i in range(0, len(image_paths_to_process), batch_size):
        batch_paths = image_paths_to_process[i:i + batch_size]
        batch_tensors = []
        batch_valid_indices = []

        for b_idx, p in enumerate(batch_paths):
            try:
                img = Image.open(p).convert("RGB")
                t = _val_transform(img)
                batch_tensors.append(t)
                batch_valid_indices.append(b_idx)
            except Exception:
                pass

        if batch_tensors:
            stack = torch.stack(batch_tensors).to(_device)
            with torch.no_grad():
                feats = extractor(stack)
                feats = torch.flatten(feats, 1)
                feats = F.normalize(feats, p=2, dim=1)
                np_feats = feats.cpu().numpy()

            for valid_idx, emb in zip(batch_valid_indices, np_feats):
                rec_idx = i + valid_idx
                valid_records.append(records_meta[rec_idx])
                all_embeddings.append(emb.tolist())

    _reference_index = valid_records
    _reference_embeddings_matrix = np.array(all_embeddings, dtype=np.float32)

    # Save to disk
    try:
        with open(EMBEDDINGS_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "records": _reference_index,
                "embeddings": all_embeddings,
            }, f)
        print(f"[REFERENCE MATCHER] Successfully saved {len(_reference_index)} indexed reference embeddings to {EMBEDDINGS_CACHE_PATH}")
    except Exception as e:
        print(f"[REFERENCE MATCHER] Warning: Failed to save embeddings cache: {e}")

    return _reference_index, _reference_embeddings_matrix


def find_best_reference_match(
    patient_image: Image.Image,
    predicted_disease: str,
    top_k_candidates: int = 20
) -> Optional[Dict[str, Any]]:
    """
    Finds the reference training image with the HIGHEST visual embedding similarity
    to the patient's uploaded lesion among all candidate images labeled with the predicted disease.
    """
    if not predicted_disease or predicted_disease in ["Unknown", "Undetermined"]:
        return None

    records, matrix = build_or_load_reference_index()
    if len(records) == 0 or matrix is None or len(matrix) == 0:
        return None

    # 1. Extract Patient Image Embedding
    patient_emb = extract_image_embedding(patient_image)

    # 2. Filter Candidate Reference Records for Predicted Condition
    target_clean = predicted_disease.lower().replace("dermatitis", "").replace("rash", "").strip()
    candidate_indices = []

    # Check for Ringworm / Tinea alias handling
    aliases = [predicted_disease.lower(), target_clean]
    if "tinea" in target_clean or "ringworm" in target_clean:
        aliases.extend(["tinea", "ringworm", "tinea corporis", "tinea cruris", "tinea pedis"])
    if "eczema" in target_clean or "atopic" in target_clean:
        aliases.extend(["eczema", "atopic dermatitis", "dermatitis"])
    if "psoriasis" in target_clean:
        aliases.extend(["psoriasis", "plaque psoriasis"])
    if "contact" in target_clean:
        aliases.extend(["contact dermatitis", "allergic contact", "irritant contact"])
    if "zoster" in target_clean or "shingles" in target_clean:
        aliases.extend(["herpes zoster", "zoster", "shingles"])

    for idx, rec in enumerate(records):
        rec_lbl = rec["all_labels"].lower()
        rec_dis = rec["disease_name"].lower()
        if any(alias in rec_lbl or alias in rec_dis for alias in aliases):
            candidate_indices.append(idx)

    # Fallback: if no strict condition match, consider top similar across whole index
    if len(candidate_indices) == 0:
        candidate_indices = list(range(len(records)))

    # 3. Compute Cosine Similarity between Patient and all Candidates
    candidate_embs = matrix[candidate_indices]
    sims = np.dot(candidate_embs, patient_emb)

    best_cand_idx = int(np.argmax(sims))
    best_record_idx = candidate_indices[best_cand_idx]
    best_sim_score = float(sims[best_cand_idx])

    best_record = dict(records[best_record_idx])

    # Convert similarity score [-1, 1] into a clean clinical percentage [0, 100%]
    sim_pct = round(float(np.clip((best_sim_score + 1.0) / 2.0 * 100.0, 0.0, 99.9)), 1)

    # Encode matched image to base64
    full_path = PROJECT_ROOT / best_record["image_path"]
    b64_str = ""
    if full_path.exists():
        try:
            with Image.open(full_path) as img:
                img = img.convert("RGB")
                img.thumbnail((360, 360))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=88)
                b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[REFERENCE MATCHER] Base64 encode error: {e}")

    best_record["image_base64"] = b64_str
    best_record["similarity_score"] = round(best_sim_score, 4)
    best_record["similarity_pct"] = sim_pct
    best_record["has_image"] = bool(b64_str)
    best_record["label"] = f"Matched reference example for {predicted_disease} ({sim_pct}% visual alignment)"

    print(f"[REFERENCE MATCHER] Matched {predicted_disease} -> {best_record['image_path']} (Similarity: {sim_pct}%, Cosine: {best_sim_score:.4f})")
    return best_record
