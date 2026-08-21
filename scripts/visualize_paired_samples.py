"""
Google SCIN Paired Sample Visualizer
Displays actual images side-by-side with structured clinical symptoms,
demographic fields, and dermatologist labels to verify data linkage.
"""

import os
import sys
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scin_pipeline import load_and_merge_metadata, prepare_dataset_records, TOP_CONDITIONS

DATASET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset", "scin")
ARTIFACT_DIR = r"C:\Users\aravi\.gemini\antigravity-ide\brain\e5562b2e-36da-4b3e-84a3-fba022aca532"


def visualize_paired_examples(num_examples: int = 4):
    print("=" * 70)
    print("  GOOGLE SCIN — PAIRED EXAMPLES VISUALIZATION")
    print("=" * 70)

    df = load_and_merge_metadata()
    records, _, _ = prepare_dataset_records(df)

    if not records:
        print("No image records found yet. Wait for downloader.")
        return

    selected_records = records[:num_examples]

    # Create a multi-row visual figure
    fig, axes = plt.subplots(num_examples, 2, figsize=(16, 4.5 * num_examples), gridspec_kw={'width_ratios': [1, 2]})
    fig.patch.set_facecolor('#f8fafc')
    plt.subplots_adjust(wspace=0.15, hspace=0.40, top=0.94, bottom=0.04, left=0.05, right=0.95)

    fig.suptitle("Google SCIN Dataset — Paired Image & Clinical Metadata Verification", fontsize=18, fontweight='bold', color='#0f172a', y=0.98)

    for i, rec in enumerate(selected_records):
        ax_img = axes[i, 0] if num_examples > 1 else axes[0]
        ax_info = axes[i, 1] if num_examples > 1 else axes[1]

        # 1. Display Image
        img = Image.open(rec["image_path"]).convert("RGB")
        ax_img.imshow(img)
        ax_img.set_xticks([])
        ax_img.set_yticks([])
        ax_img.set_title(f"Case ID: {rec['case_id'][:16]} ({rec['filename']})", fontsize=11, fontweight='600', color='#0f766e', pad=6)

        # Border
        for spine in ax_img.spines.values():
            spine.set_edgecolor('#0d9488')
            spine.set_linewidth(2)

        # 2. Display Clinical Metadata & Dermatologist Labels
        ax_info.axis('off')

        # Find matching row for full details
        case_row = df[df["case_id"] == rec["case_id"]].iloc[0]

        # Extract active symptoms & body parts
        body_parts = [c.replace("body_parts_", "").replace("_", " ").title() for c in df.columns if c.startswith("body_parts_") and case_row.get(c) == "YES"]
        textures = [c.replace("textures_", "").replace("_", " ").title() for c in df.columns if c.startswith("textures_") and case_row.get(c) == "YES"]
        symptoms = [c.replace("condition_symptoms_", "").replace("_", " ").title() for c in df.columns if c.startswith("condition_symptoms_") and case_row.get(c) == "YES"]

        # Dermatologist annotations
        dermatologist_labels = rec["conditions"]
        conf_dict = rec["confidence_dict"]

        info_text = (
            f"Case ID: {rec['case_id']}\n"
            f"────────────────────────────────────────────────────────────\n"
            f"• Demographics:  Age: {rec['age_group']} | Sex: {rec['sex_at_birth']} | Skin Tone (FST): {rec['fitzpatrick_skin_type']}\n"
            f"• Body Location: {', '.join(body_parts) if body_parts else 'Unspecified'}\n"
            f"• Texture:       {', '.join(textures) if textures else 'Not specified'}\n"
            f"• Symptoms:      {', '.join(symptoms) if symptoms else 'None reported'} (Duration: {rec['duration']})\n"
            f"────────────────────────────────────────────────────────────\n"
            f"• Dermatologist Diagnosis Label(s):\n"
        )

        for cond in dermatologist_labels:
            conf_str = f" (Confidence weight: {conf_dict[cond]:.2f})" if cond in conf_dict else ""
            info_text += f"   ► {cond}{conf_str}\n"

        # Background box
        rect = patches.FancyBboxPatch((0.02, 0.05), 0.96, 0.90, boxstyle="round,pad=0.03",
                                      facecolor="#ffffff", edgecolor="#cbd5e1", linewidth=1.5,
                                      transform=ax_info.transAxes)
        ax_info.add_patch(rect)

        ax_info.text(0.06, 0.88, info_text, transform=ax_info.transAxes,
                     fontsize=10.5, fontfamily='sans-serif', verticalalignment='top',
                     color='#1e293b', linespacing=1.4)

    output_path = os.path.join(DATASET_DIR, "paired_samples_visualization.png")
    plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()

    print(f"[OK] Paired samples visualization saved to: {output_path}")

    # Copy to artifacts directory
    if os.path.exists(ARTIFACT_DIR):
        artifact_dest = os.path.join(ARTIFACT_DIR, "paired_samples_visualization.png")
        shutil.copy2(output_path, artifact_dest)
        print(f"[OK] Paired samples figure copied to artifacts: {artifact_dest}")


if __name__ == "__main__":
    visualize_paired_examples(num_examples=4)
