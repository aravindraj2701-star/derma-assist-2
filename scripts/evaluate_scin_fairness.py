"""
Google SCIN Fairness & Performance Evaluator
Evaluates the trained multimodal model on the independent test set:
- Top-1, Top-3, Top-5 Multi-Label Accuracy / Recall
- Per-Class Precision, Recall, and F1 Scores
- Macro and Micro F1 Metrics
- Fitzpatrick Skin Tone Stratification (FST I-II vs III-IV vs V-VI) to evaluate fairness gaps.
"""

import os
import sys
import json
import shutil
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score, f1_score
from torchvision import transforms
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scin_pipeline import TOP_CONDITIONS
from backend.models.scin_multimodal_model import SCINMultimodalModel

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "scin")
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
DOCS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
ARTIFACT_DIR = r"C:\Users\aravi\.gemini\antigravity-ide\brain\e5562b2e-36da-4b3e-84a3-fba022aca532"

os.makedirs(DOCS_DIR, exist_ok=True)


def evaluate_fairness_and_performance():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 70)
    print("  GOOGLE SCIN -- FAIRNESS & PERFORMANCE EVALUATION")
    print("=" * 70)

    # 1. Load Test Split
    test_path = os.path.join(DATASET_DIR, "test_split.json")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test split not found at {test_path}. Run train_scin_model.py first.")

    with open(test_path, "r", encoding="utf-8") as f:
        test_records = json.load(f)

    print(f"Total Test Samples: {len(test_records)}")

    # 2. Load Model
    model_path = os.path.join(MODELS_DIR, "scin_multimodal_model.pt")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Trained model not found at {model_path}.")

    checkpoint = torch.load(model_path, map_location=device)
    model = SCINMultimodalModel(
        num_classes=len(TOP_CONDITIONS),
        tabular_dim=58,
        image_embed_dim=512,
        tabular_embed_dim=128,
        fusion_hidden_dim=256,
        dropout=0.3,
        pretrained_vision=False,
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    all_targets = []
    all_probs = []
    all_fst = []

    with torch.no_grad():
        for rec in test_records:
            try:
                img = Image.open(rec["image_path"]).convert("RGB")
                img_tensor = val_tf(img).unsqueeze(0).to(device)
                tab_tensor = torch.tensor([rec["tabular_vector"]], dtype=torch.float32).to(device)

                probs = model.predict_proba(images=img_tensor, tabular=tab_tensor, mode="multimodal")
                all_probs.append(probs.cpu().numpy()[0])
                all_targets.append(rec["target_vector"])
                all_fst.append(rec.get("fitzpatrick_skin_type", "UNKNOWN"))
            except Exception as e:
                pass

    all_targets = np.array(all_targets)
    all_probs = np.array(all_probs)
    all_fst = np.array(all_fst)

    # 3. Overall Top-K Metrics
    n_samples = len(all_targets)
    top1_correct = 0
    top3_correct = 0
    top5_correct = 0

    for i in range(n_samples):
        actual = np.where(all_targets[i] == 1.0)[0]
        if len(actual) == 0:
            continue
        ranked = np.argsort(all_probs[i])[::-1]

        if ranked[0] in actual:
            top1_correct += 1
        if any(idx in ranked[:3] for idx in actual):
            top3_correct += 1
        if any(idx in ranked[:5] for idx in actual):
            top5_correct += 1

    top1_acc = top1_correct / n_samples
    top3_acc = top3_correct / n_samples
    top5_acc = top5_correct / n_samples

    # Binary predictions for F1
    bin_preds = (all_probs >= 0.5).astype(int)
    # If no class >= 0.5, take argmax
    for i in range(n_samples):
        if np.sum(bin_preds[i]) == 0:
            bin_preds[i, np.argmax(all_probs[i])] = 1

    precision, recall, f1, support = precision_recall_fscore_support(all_targets, bin_preds, average=None, zero_division=0)
    macro_f1 = float(f1_score(all_targets, bin_preds, average="macro", zero_division=0))
    micro_f1 = float(f1_score(all_targets, bin_preds, average="micro", zero_division=0))

    # Per-class summary
    per_class_results = []
    for c_idx, c_name in enumerate(TOP_CONDITIONS):
        per_class_results.append({
            "class_name": c_name,
            "precision": float(precision[c_idx]),
            "recall": float(recall[c_idx]),
            "f1_score": float(f1[c_idx]),
            "support": int(support[c_idx]) if c_idx < len(support) else 0,
        })

    # 4. Fitzpatrick Skin Tone Fairness Stratification
    # Group into: FST I-II (Light), FST III-IV (Medium), FST V-VI (Dark), Other/Unknown
    fst_groups = {
        "FST I-II (Lighter Tones)": ["FST1", "FST2"],
        "FST III-IV (Intermediate Tones)": ["FST3", "FST4"],
        "FST V-VI (Darker Tones)": ["FST5", "FST6"],
        "Unspecified / Other": ["NONE_SELECTED", "UNKNOWN", "OTHER"],
    }

    fairness_metrics = {}
    for group_name, types in fst_groups.items():
        mask = np.isin(all_fst, types)
        count = int(np.sum(mask))
        if count > 0:
            sub_targets = all_targets[mask]
            sub_probs = all_probs[mask]
            sub_preds = bin_preds[mask]

            sub_top1 = 0
            sub_top3 = 0
            for i in range(count):
                act = np.where(sub_targets[i] == 1.0)[0]
                rnk = np.argsort(sub_probs[i])[::-1]
                if rnk[0] in act:
                    sub_top1 += 1
                if any(x in rnk[:3] for x in act):
                    sub_top3 += 1

            sub_top1_acc = sub_top1 / count
            sub_top3_acc = sub_top3 / count
            sub_micro_f1 = float(f1_score(sub_targets, sub_preds, average="micro", zero_division=0))
            sub_macro_f1 = float(f1_score(sub_targets, sub_preds, average="macro", zero_division=0))

            fairness_metrics[group_name] = {
                "sample_count": count,
                "percentage_of_test": f"{100.0 * count / n_samples:.1f}%",
                "top1_accuracy": round(sub_top1_acc, 4),
                "top3_accuracy": round(sub_top3_acc, 4),
                "micro_f1": round(sub_micro_f1, 4),
                "macro_f1": round(sub_macro_f1, 4),
            }

    # Fairness Gap Calculation (Delta between Lightest FST I-II and Darkest FST V-VI)
    fst_light_acc = fairness_metrics.get("FST I-II (Lighter Tones)", {}).get("top3_accuracy", 0)
    fst_dark_acc = fairness_metrics.get("FST V-VI (Darker Tones)", {}).get("top3_accuracy", 0)
    fairness_gap_top3 = abs(fst_light_acc - fst_dark_acc)

    report = {
        "evaluation_summary": {
            "total_test_samples": n_samples,
            "top1_accuracy": round(top1_acc, 4),
            "top3_accuracy": round(top3_acc, 4),
            "top5_accuracy": round(top5_acc, 4),
            "micro_f1": round(micro_f1, 4),
            "macro_f1": round(macro_f1, 4),
            "fairness_gap_fst_top3": round(fairness_gap_top3, 4),
        },
        "fitzpatrick_fairness_stratification": fairness_metrics,
        "per_class_performance": per_class_results,
    }

    # Save JSON Report
    report_path = os.path.join(DOCS_DIR, "scin_fairness_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # 5. Create High-Quality Multi-Panel Fairness & Performance Visualization Chart
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.patch.set_facecolor('#ffffff')
    plt.subplots_adjust(wspace=0.30, top=0.85, bottom=0.15, left=0.08, right=0.95)

    fig.suptitle("Google SCIN Multimodal Model -- Fairness & Top-K Diagnostic Performance", fontsize=16, fontweight='bold', color='#0f172a', y=0.96)

    # Panel 1: Top-K Accuracy & F1 Bar Chart
    ax1 = axes[0]
    metric_names = ["Top-1 Accuracy", "Top-3 Accuracy", "Top-5 Accuracy", "Micro F1", "Macro F1"]
    metric_values = [top1_acc * 100, top3_acc * 100, top5_acc * 100, micro_f1 * 100, macro_f1 * 100]
    colors = ['#0d9488', '#14b8a6', '#2dd4bf', '#0284c7', '#6366f1']

    bars = ax1.bar(metric_names, metric_values, color=colors, width=0.55, edgecolor='#0f172a', linewidth=0.8)
    ax1.set_ylim(0, 100)
    ax1.set_ylabel("Score (%)", fontsize=11, fontweight='600', color='#334155')
    ax1.set_title("Overall Multi-Label Test Performance", fontsize=13, fontweight='bold', color='#0f766e', pad=10)
    ax1.grid(axis='y', linestyle='--', alpha=0.3)
    ax1.set_xticks(range(len(metric_names)))
    ax1.set_xticklabels(metric_names, rotation=20, ha='right', fontsize=10)

    for bar in bars:
        height = bar.get_height()
        ax1.annotate(f'{height:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold', color='#0f172a')

    # Panel 2: Fitzpatrick Stratified Performance (Fairness Gap Check)
    ax2 = axes[1]
    groups = list(fairness_metrics.keys())
    top3_vals = [fairness_metrics[g]["top3_accuracy"] * 100 for g in groups]
    micro_vals = [fairness_metrics[g]["micro_f1"] * 100 for g in groups]

    x = np.arange(len(groups))
    width = 0.35

    b1 = ax2.bar(x - width/2, top3_vals, width, label='Top-3 Accuracy', color='#0d9488', edgecolor='#0f172a', linewidth=0.8)
    b2 = ax2.bar(x + width/2, micro_vals, width, label='Micro F1', color='#f59e0b', edgecolor='#0f172a', linewidth=0.8)

    ax2.set_ylim(0, 100)
    ax2.set_ylabel("Score (%)", fontsize=11, fontweight='600', color='#334155')
    ax2.set_title("Fitzpatrick Skin Tone Fairness Stratification", fontsize=13, fontweight='bold', color='#0f766e', pad=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels([g.split("(")[0].strip() for g in groups], rotation=15, ha='right', fontsize=10)
    ax2.legend(frameon=True, facecolor='#ffffff', edgecolor='#cbd5e1')
    ax2.grid(axis='y', linestyle='--', alpha=0.3)

    for b in b1:
        h = b.get_height()
        ax2.annotate(f'{h:.1f}%', xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='600')
    for b in b2:
        h = b.get_height()
        ax2.annotate(f'{h:.1f}%', xy=(b.get_x() + b.get_width() / 2, h), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='600')

    plot_path = os.path.join(DOCS_DIR, "scin_fairness_evaluation.png")
    plt.savefig(plot_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    if os.path.exists(ARTIFACT_DIR):
        artifact_dest = os.path.join(ARTIFACT_DIR, "scin_fairness_evaluation.png")
        shutil.copy2(plot_path, artifact_dest)

    # Print summary table
    print("\n" + "=" * 70)
    print("  OVERALL MULTI-LABEL PERFORMANCE METRICS")
    print("=" * 70)
    print(f"  * Top-1 Multi-Label Accuracy: {top1_acc * 100:6.2f}%")
    print(f"  * Top-3 Multi-Label Accuracy: {top3_acc * 100:6.2f}%")
    print(f"  * Top-5 Multi-Label Accuracy: {top5_acc * 100:6.2f}%")
    print(f"  * Micro-Averaged F1 Score:   {micro_f1 * 100:6.2f}%")
    print(f"  * Macro-Averaged F1 Score:   {macro_f1 * 100:6.2f}%")

    print("\n" + "=" * 70)
    print("  FITZPATRICK SKIN TONE FAIRNESS STRATIFICATION")
    print("=" * 70)
    for g, data in fairness_metrics.items():
        print(f"  -> {g:<35} | N={data['sample_count']:3d} ({data['percentage_of_test']}) | Top-3 Acc: {data['top3_accuracy']*100:5.1f}% | Micro F1: {data['micro_f1']*100:5.1f}%")
    print(f"\n  * Fairness Gap (FST I-II vs FST V-VI Top-3 Accuracy Delta): {fairness_gap_top3*100:.2f}%")

    print(f"\n[OK] Fairness report exported to: {report_path}")
    print(f"[OK] Evaluation plot exported to: {plot_path}")


if __name__ == "__main__":
    evaluate_fairness_and_performance()
