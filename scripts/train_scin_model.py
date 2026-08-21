"""
Google SCIN Multimodal Model Training Script
Trains the joint Vision Backbone + Tabular Symptom MLP with positive class weighting
for multi-label skin condition classification.
"""

import os
import sys
import json
import time
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scin_pipeline import (
    load_and_merge_metadata,
    prepare_dataset_records,
    split_records_stratified,
    compute_pos_weights,
    SCINMultimodalDataset,
    get_data_transforms,
    TOP_CONDITIONS,
    BODY_PART_COLUMNS,
    TEXTURE_COLUMNS,
    SYMPTOM_COLUMNS,
    SYSTEMIC_SYMPTOM_COLUMNS,
    AGE_GROUPS,
    SEX_AT_BIRTH,
    FITZPATRICK_TYPES,
    DURATION_CATEGORIES,
)
from backend.models.scin_multimodal_model import SCINMultimodalModel

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "scin")
os.makedirs(MODELS_DIR, exist_ok=True)


def train_model(epochs: int = 10, batch_size: int = 16, lr: float = 1e-4):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 70)
    print(f"  TRAINING SCIN MULTIMODAL MODEL (Device: {device})")
    print("=" * 70)

    # 1. Load dataset records
    df = load_and_merge_metadata()
    records, condition_to_idx, idx_to_condition = prepare_dataset_records(df)
    print(f"Total verified paired records: {len(records)}")

    # 2. Stratified Split (70% Train, 15% Val, 15% Test)
    train_recs, val_recs, test_recs = split_records_stratified(records, val_size=0.15, test_size=0.15, random_state=42)
    print(f"Split sizes — Train: {len(train_recs)}, Val: {len(val_recs)}, Test: {len(test_recs)}")

    # Save test records for independent fairness evaluation
    test_export = [{
        "case_id": r["case_id"],
        "image_path": r["image_path"],
        "conditions": r["conditions"],
        "target_vector": r["target_vector"].tolist(),
        "tabular_vector": r["tabular_vector"].tolist(),
        "fitzpatrick_skin_type": r["fitzpatrick_skin_type"],
        "age_group": r["age_group"],
        "sex_at_birth": r["sex_at_birth"],
    } for r in test_recs]

    with open(os.path.join(DATASET_DIR, "test_split.json"), "w") as f:
        json.dump(test_export, f, indent=2)

    # 3. Transforms and Datasets
    train_tf, val_tf = get_data_transforms()
    train_ds = SCINMultimodalDataset(train_recs, transform=train_tf)
    val_ds = SCINMultimodalDataset(val_recs, transform=val_tf)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    # 4. Model & Loss Setup
    num_classes = len(TOP_CONDITIONS)
    tabular_dim = 58
    pos_weights = compute_pos_weights(train_recs, num_classes).to(device)

    model = SCINMultimodalModel(
        num_classes=num_classes,
        tabular_dim=tabular_dim,
        image_embed_dim=512,
        tabular_embed_dim=128,
        fusion_hidden_dim=256,
        dropout=0.3,
        pretrained_vision=True,
    ).to(device)

    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_loss = float("inf")
    best_model_path = os.path.join(MODELS_DIR, "scin_multimodal_model.pt")

    # 5. Training Loop
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        start_time = time.time()

        for batch in tqdm(train_loader, desc=f"Epoch {epoch}/{epochs} [Train]"):
            images = batch["image"].to(device)
            tabular = batch["tabular"].to(device)
            targets = batch["target"].to(device)

            optimizer.zero_grad()
            logits = model(images=images, tabular=tabular, mode="multimodal")
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * images.size(0)

        scheduler.step()
        train_loss = train_loss / len(train_ds)

        # Validation
        model.eval()
        val_loss = 0.0
        val_preds = []
        val_targets = []

        with torch.no_grad():
            for batch in val_loader:
                images = batch["image"].to(device)
                tabular = batch["tabular"].to(device)
                targets = batch["target"].to(device)

                logits = model(images=images, tabular=tabular, mode="multimodal")
                loss = criterion(logits, targets)
                val_loss += loss.item() * images.size(0)

                probs = torch.sigmoid(logits)
                val_preds.append(probs.cpu().numpy())
                val_targets.append(targets.cpu().numpy())

        val_loss = val_loss / len(val_ds)
        val_preds = np.vstack(val_preds)
        val_targets = np.vstack(val_targets)

        # Top-3 Accuracy on Val
        top3_correct = 0
        total_eval = len(val_targets)
        for i in range(total_eval):
            top3_idx = np.argsort(val_preds[i])[-3:]
            actual_idx = np.where(val_targets[i] == 1.0)[0]
            if any(idx in top3_idx for idx in actual_idx):
                top3_correct += 1
        val_top3_acc = top3_correct / total_eval

        elapsed = time.time() - start_time
        print(f"Epoch {epoch:02d}/{epochs:02d} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Val Top-3 Acc: {val_top3_acc*100:.1f}% | Time: {elapsed:.1f}s")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": val_loss,
                "val_top3_acc": val_top3_acc,
                "num_classes": num_classes,
                "top_conditions": TOP_CONDITIONS,
            }, best_model_path)
            print(f"  [+] Saved new best model checkpoint to {best_model_path}")

    # 6. Export Model Metadata for API
    meta = {
        "num_classes": len(TOP_CONDITIONS),
        "conditions": TOP_CONDITIONS,
        "body_parts": BODY_PART_COLUMNS,
        "textures": TEXTURE_COLUMNS,
        "symptoms": SYMPTOM_COLUMNS,
        "systemic_symptoms": SYSTEMIC_SYMPTOM_COLUMNS,
        "age_groups": AGE_GROUPS,
        "sex_at_birth": SEX_AT_BIRTH,
        "fitzpatrick_types": FITZPATRICK_TYPES,
        "duration_categories": DURATION_CATEGORIES,
        "best_val_loss": float(best_val_loss),
    }
    with open(os.path.join(MODELS_DIR, "scin_model_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n[OK] Model training complete. Checkpoint saved to: {best_model_path}")
    return best_model_path


if __name__ == "__main__":
    train_model(epochs=6, batch_size=16, lr=1e-4)
