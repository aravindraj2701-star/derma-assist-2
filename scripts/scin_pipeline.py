"""
Google SCIN Multimodal Data Pipeline & Preprocessing
Handles dataset parsing, multi-label condition extraction, structured symptom encoding,
train/val/test stratified splitting, and PyTorch Dataset creation.
"""

import os
import ast
import json
import glob
from collections import Counter
import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from sklearn.model_selection import train_test_split

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "scin")
METADATA_DIR = os.path.join(DATASET_DIR, "metadata")
IMAGES_DIR = os.path.join(DATASET_DIR, "images")

# Top condition categories selected from SCIN dataset
TOP_CONDITIONS = [
    "Eczema",
    "Allergic Contact Dermatitis",
    "Psoriasis",
    "Insect Bite",
    "Urticaria",
    "Folliculitis",
    "Irritant Contact Dermatitis",
    "Tinea",
    "Herpes Zoster",
    "Drug Rash",
    "Herpes Simplex",
    "Impetigo",
    "Acute dermatitis, NOS",
    "Hypersensitivity",
    "Acne",
    "Pigmented purpuric eruption",
    "Leukocytoclastic Vasculitis",
    "Lichen planus/lichenoid eruption",
    "Pityriasis rosea",
    "Viral Exanthem",
]

# Structured Tabular Feature Definitions
BODY_PART_COLUMNS = [
    "body_parts_head_or_neck",
    "body_parts_arm",
    "body_parts_palm",
    "body_parts_back_of_hand",
    "body_parts_torso_front",
    "body_parts_torso_back",
    "body_parts_genitalia_or_groin",
    "body_parts_buttocks",
    "body_parts_leg",
    "body_parts_foot_top_or_side",
    "body_parts_foot_sole",
    "body_parts_other",
]

TEXTURE_COLUMNS = [
    "textures_raised_or_bumpy",
    "textures_flat",
    "textures_rough_or_flaky",
    "textures_fluid_filled",
]

SYMPTOM_COLUMNS = [
    "condition_symptoms_bothersome_appearance",
    "condition_symptoms_bleeding",
    "condition_symptoms_increasing_size",
    "condition_symptoms_darkening",
    "condition_symptoms_itching",
    "condition_symptoms_burning",
    "condition_symptoms_pain",
    "condition_symptoms_no_relevant_experience",
]

SYSTEMIC_SYMPTOM_COLUMNS = [
    "other_symptoms_fever",
    "other_symptoms_chills",
    "other_symptoms_fatigue",
    "other_symptoms_joint_pain",
    "other_symptoms_mouth_sores",
    "other_symptoms_shortness_of_breath",
    "other_symptoms_no_relevant_symptoms",
]

AGE_GROUPS = [
    "AGE_18_TO_29",
    "AGE_30_TO_39",
    "AGE_40_TO_49",
    "AGE_50_TO_59",
    "AGE_60_TO_69",
    "AGE_70_TO_79",
    "AGE_80_OR_ABOVE",
    "AGE_UNKNOWN",
]

SEX_AT_BIRTH = ["FEMALE", "MALE", "OTHER_OR_UNSPECIFIED"]

FITZPATRICK_TYPES = ["FST1", "FST2", "FST3", "FST4", "FST5", "FST6", "NONE_SELECTED", "UNKNOWN"]

DURATION_CATEGORIES = [
    "LESS_THAN_A_WEEK",
    "ONE_TO_FOUR_WEEKS",
    "ONE_TO_SIX_MONTHS",
    "SEVEN_TO_TWELVE_MONTHS",
    "ONE_TO_TWO_YEARS",
    "THREE_TO_FIVE_YEARS",
    "MORE_THAN_FIVE_YEARS",
    "UNKNOWN",
]


def load_and_merge_metadata():
    """Loads scin_cases.csv and scin_labels.csv and merges on case_id."""
    cases_path = os.path.join(METADATA_DIR, "scin_cases.csv")
    labels_path = os.path.join(METADATA_DIR, "scin_labels.csv")

    if not os.path.exists(cases_path) or not os.path.exists(labels_path):
        raise FileNotFoundError("Metadata CSVs not found. Please run scin_downloader.py first.")

    cases_df = pd.read_csv(cases_path, dtype={"case_id": str})
    labels_df = pd.read_csv(labels_path, dtype={"case_id": str})

    merged_df = pd.merge(cases_df, labels_df, on="case_id", how="inner")
    return merged_df


def parse_labels(label_str, weighted_str=None):
    """
    Parses dermatologist condition names list / weighted dictionary.
    Returns list of condition names and dict of condition: confidence.
    """
    conditions = []
    confidence_dict = {}

    if pd.notna(weighted_str) and isinstance(weighted_str, str) and weighted_str.strip():
        try:
            w_dict = ast.literal_eval(weighted_str)
            if isinstance(w_dict, dict):
                confidence_dict = w_dict
                conditions = list(w_dict.keys())
        except Exception:
            pass

    if not conditions and pd.notna(label_str) and isinstance(label_str, str) and label_str.strip():
        try:
            l_list = ast.literal_eval(label_str)
            if isinstance(l_list, (list, tuple)):
                conditions = [str(c).strip() for c in l_list]
        except Exception:
            conditions = [label_str.strip()]

    return conditions, confidence_dict


def build_tabular_feature_vector(row):
    """
    Converts structured symptom/demographic fields in a dataframe row
    into a continuous/binary numerical feature vector.
    """
    features = []

    # 1. Body Parts (12 features, binary 1.0 or 0.0)
    for col in BODY_PART_COLUMNS:
        val = 1.0 if row.get(col) == "YES" else 0.0
        features.append(val)

    # 2. Textures (4 features)
    for col in TEXTURE_COLUMNS:
        val = 1.0 if row.get(col) == "YES" else 0.0
        features.append(val)

    # 3. Cutaneous Symptoms (8 features)
    for col in SYMPTOM_COLUMNS:
        val = 1.0 if row.get(col) == "YES" else 0.0
        features.append(val)

    # 4. Systemic Symptoms (7 features)
    for col in SYSTEMIC_SYMPTOM_COLUMNS:
        val = 1.0 if row.get(col) == "YES" else 0.0
        features.append(val)

    # 5. Age Group One-Hot (8 features)
    age = str(row.get("age_group", "AGE_UNKNOWN"))
    for ag in AGE_GROUPS:
        features.append(1.0 if age == ag else 0.0)

    # 6. Sex at Birth One-Hot (3 features)
    sex = str(row.get("sex_at_birth", "OTHER_OR_UNSPECIFIED"))
    for s in SEX_AT_BIRTH:
        features.append(1.0 if sex == s else 0.0)

    # 7. Fitzpatrick Skin Type One-Hot (8 features)
    fst = str(row.get("fitzpatrick_skin_type", "UNKNOWN"))
    if pd.isna(fst) or not fst:
        fst = "UNKNOWN"
    for f in FITZPATRICK_TYPES:
        features.append(1.0 if fst == f else 0.0)

    # 8. Duration Category One-Hot (8 features)
    dur = str(row.get("condition_duration", "UNKNOWN"))
    if pd.isna(dur) or not dur:
        dur = "UNKNOWN"
    for d in DURATION_CATEGORIES:
        features.append(1.0 if dur == d else 0.0)

    return np.array(features, dtype=np.float32)


def extract_multilabel_vector(conditions, condition_to_idx):
    """Encodes list of conditions to multi-hot binary vector of shape (K,)."""
    target = np.zeros(len(condition_to_idx), dtype=np.float32)
    for cond in conditions:
        if cond in condition_to_idx:
            target[condition_to_idx[cond]] = 1.0
    return target


def prepare_dataset_records(df):
    """
    Pairs downloaded images with tabular symptoms and condition labels.
    """
    records = []
    condition_to_idx = {c: i for i, c in enumerate(TOP_CONDITIONS)}
    idx_to_condition = {i: c for i, c in enumerate(TOP_CONDITIONS)}

    for _, row in df.iterrows():
        case_id = str(row["case_id"])
        conditions, conf_dict = parse_labels(
            row.get("dermatologist_skin_condition_on_label_name"),
            row.get("weighted_skin_condition_label")
        )

        # Check if at least one condition is in top conditions
        has_top_condition = any(c in condition_to_idx for c in conditions)
        if not has_top_condition:
            continue

        target_vector = extract_multilabel_vector(conditions, condition_to_idx)
        tabular_vector = build_tabular_feature_vector(row)

        # Fitzpatrick skin type (self-reported or dermatologist-assigned for fairness evaluation)
        fst = row.get("fitzpatrick_skin_type")
        if pd.isna(fst) or not fst:
            fst = row.get("dermatologist_fitzpatrick_skin_type_label_1")
        if pd.isna(fst) or not fst:
            fst = "UNKNOWN"

        # Check existing images for this case
        for col in ["image_1_path", "image_2_path", "image_3_path"]:
            rel_path = row.get(col)
            if pd.notna(rel_path) and isinstance(rel_path, str):
                fname = os.path.basename(rel_path)
                local_path = os.path.join(IMAGES_DIR, fname)
                if os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
                    records.append({
                        "case_id": case_id,
                        "image_path": local_path,
                        "filename": fname,
                        "conditions": conditions,
                        "confidence_dict": conf_dict,
                        "target_vector": target_vector,
                        "tabular_vector": tabular_vector,
                        "fitzpatrick_skin_type": str(fst),
                        "age_group": str(row.get("age_group", "AGE_UNKNOWN")),
                        "sex_at_birth": str(row.get("sex_at_birth", "OTHER_OR_UNSPECIFIED")),
                        "duration": str(row.get("condition_duration", "UNKNOWN")),
                    })

    return records, condition_to_idx, idx_to_condition


class SCINMultimodalDataset(Dataset):
    """PyTorch Multimodal Dataset for SCIN (Image + Tabular Symptoms)."""

    def __init__(self, records, transform=None):
        self.records = records
        self.transform = transform

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        rec = self.records[idx]

        # Load image
        img = Image.open(rec["image_path"]).convert("RGB")
        if self.transform:
            img_tensor = self.transform(img)
        else:
            default_tf = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            img_tensor = default_tf(img)

        tab_tensor = torch.tensor(rec["tabular_vector"], dtype=torch.float32)
        target_tensor = torch.tensor(rec["target_vector"], dtype=torch.float32)

        return {
            "image": img_tensor,
            "tabular": tab_tensor,
            "target": target_tensor,
            "case_id": rec["case_id"],
            "fst": rec["fitzpatrick_skin_type"]
        }


def get_data_transforms():
    """Standard image transforms and augmentations."""
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.2),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    return train_transform, val_transform


def split_records_stratified(records, val_size=0.15, test_size=0.15, random_state=42):
    """
    Stratified split by primary condition label with robust grouping for rare classes.
    """
    primary_labels = []
    for r in records:
        primary_idx = int(np.argmax(r["target_vector"])) if np.sum(r["target_vector"]) > 0 else 0
        primary_labels.append(primary_idx)

    # Group rare classes (count < 4) into a common bin (-1) for stratification
    label_counts = Counter(primary_labels)
    binned_labels = [lbl if label_counts[lbl] >= 4 else -1 for lbl in primary_labels]

    total_val_test = val_size + test_size
    train_recs, val_test_recs, _, val_test_binned = train_test_split(
        records,
        binned_labels,
        test_size=total_val_test,
        stratify=binned_labels if len(set(binned_labels)) > 1 else None,
        random_state=random_state
    )

    # Second split: val and test
    val_test_counts = Counter(val_test_binned)
    val_test_sub_binned = [lbl if val_test_counts[lbl] >= 2 else -1 for lbl in val_test_binned]
    relative_test_size = test_size / total_val_test

    val_recs, test_recs = train_test_split(
        val_test_recs,
        test_size=relative_test_size,
        stratify=val_test_sub_binned if len(set(val_test_sub_binned)) > 1 else None,
        random_state=random_state
    )

    return train_recs, val_recs, test_recs


def compute_pos_weights(train_records, num_classes):
    """Computes pos_weight for BCEWithLogitsLoss to handle class imbalance."""
    all_targets = np.array([r["target_vector"] for r in train_records])
    pos_counts = np.sum(all_targets, axis=0)
    total_samples = len(train_records)

    pos_weights = np.zeros(num_classes, dtype=np.float32)
    for c in range(num_classes):
        p = max(pos_counts[c], 1.0)
        neg = total_samples - p
        pos_weights[c] = np.clip(neg / p, 1.0, 50.0)

    return torch.tensor(pos_weights, dtype=torch.float32)
