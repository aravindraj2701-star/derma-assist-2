"""
update_dataset_v2.py
--------------------
1. Load combined_skin_disease_dataset.csv.
2. Verify symptoms_description and body_location against the reference mapping.
3. Add a severity_flag column: "Malignant", "Pre-cancerous", "Benign".
4. Export the modified dataset to combined_skin_disease_dataset_v2.csv.
5. Print a diff summary of the modifications.
"""

import pandas as pd
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_CSV = BASE_DIR / "combined_skin_disease_dataset.csv"
OUTPUT_CSV = BASE_DIR / "combined_skin_disease_dataset_v2.csv"

# Reference symptom mapping from the HTML
REFERENCE_MAPPING = {
    "Melanoma": {
        "category": "Malignant Skin Cancer",
        "location": "Trunk, Back (men), Lower legs (women), Face",
        "symptoms": "Asymmetrical, irregular borders, variegated color (brown/black/red/blue), diameter >6mm, evolving lesion.",
        "severity_flag": "Malignant"
    },
    "Basal Cell Carcinoma": {
        "category": "Non-Melanoma Skin Cancer (Malignant)",
        "location": "Face, Nose, Scalp, Neck, Shoulders",
        "symptoms": "Pearly translucent papule or nodule, rolled borders, telangiectasia, non-healing ulcer.",
        "severity_flag": "Malignant"
    },
    "Squamous Cell Carcinoma": {
        "category": "Non-Melanoma Skin Cancer (Malignant)",
        "location": "Lower lip, Ears, Face, Scalp, Dorsal hands",
        "symptoms": "Hyperkeratotic, crusted, firm erythematous plaque or nodule, may ulcerate or bleed easily.",
        "severity_flag": "Malignant"
    },
    "Actinic Keratosis": {
        "category": "Pre-cancerous Lesion",
        "location": "Face, Scalp, Ears, Forearms, Hands",
        "symptoms": "Rough, scaly, gritty erythematous patch, sandpapery texture on chronically sun-exposed skin.",
        "severity_flag": "Pre-cancerous"
    },
    "Nevus": {
        "category": "Benign Melanocytic Lesion",
        "location": "Trunk, Neck, Extremities, Face",
        "symptoms": "Symmetrical, uniform brown/tan pigmented macule or papule with well-defined borders.",
        "severity_flag": "Benign"
    },
    "Pigmented Benign Keratosis": {
        "category": "Benign Skin Lesion",
        "location": "Trunk, Face, Back, Neck",
        "symptoms": "Well-demarcated stuck-on pigmented plaque, verrucous or waxy surface, follicular plugging.",
        "severity_flag": "Benign"
    },
    "Seborrheic Keratosis": {
        "category": "Benign Skin Lesion",
        "location": "Chest, Back, Shoulders, Face",
        "symptoms": "Waxy, stuck-on hyperkeratotic plaque, brown to black, dull surface with horn pseudocysts.",
        "severity_flag": "Benign"
    },
    "Dermatofibroma": {
        "category": "Benign Fibrous Nodule",
        "location": "Lower extremities, Arms, Trunk",
        "symptoms": "Firm, solitary, hyperpigmented button-like nodule that dimples downward with lateral pinching.",
        "severity_flag": "Benign"
    }
}


def update_dataset():
    if not INPUT_CSV.exists():
        print(f"[ERROR] Input dataset file not found: {INPUT_CSV}")
        return

    # Load dataset
    df = pd.read_csv(INPUT_CSV)
    print(f"[*] Loaded dataset: {INPUT_CSV} ({len(df)} rows)")

    mismatches_symptoms = 0
    mismatches_category = 0
    mismatches_location = 0

    updated_records = []

    # Verification and Enrichment loop
    for idx, row in df.iterrows():
        disease = row["unified_disease_label"]
        current_symptoms = row.get("symptoms_description", "")
        current_category = row.get("category", "")
        current_location = row.get("body_location", "")

        ref = REFERENCE_MAPPING.get(disease)
        if not ref:
            # If disease is not in our 8 target classes (e.g. Vascular Lesion in some datasets)
            # determine severity based on malignant column
            severity = "Malignant" if row.get("malignant") == 1 else "Benign"
            updated_records.append({
                **row.to_dict(),
                "severity_flag": severity
            })
            continue

        # Check symptoms
        if str(current_symptoms).strip() != ref["symptoms"]:
            mismatches_symptoms += 1

        # Check category
        if str(current_category).strip() != ref["category"]:
            mismatches_category += 1

        # Check location
        if str(current_location).strip() != ref["location"]:
            mismatches_location += 1

        # Update columns based on reference mapping
        updated_row = row.to_dict()
        updated_row["symptoms_description"] = ref["symptoms"]
        updated_row["category"] = ref["category"]
        updated_row["body_location"] = ref["location"]
        updated_row["severity_flag"] = ref["severity_flag"]

        updated_records.append(updated_row)

    # Save to v2 CSV
    df_v2 = pd.DataFrame(updated_records)
    
    # Save both in project root and dataset folder for safety
    df_v2.to_csv(OUTPUT_CSV, index=False)
    df_v2.to_csv(BASE_DIR / "dataset" / "combined_skin_disease_dataset_v2.csv", index=False)

    print("\n" + "=" * 60)
    print("  VERIFICATION & UPDATE SUMMARY")
    print("=" * 60)
    print(f"  • Symptoms Mismatches Fixed  : {mismatches_symptoms}")
    print(f"  • Category Mismatches Fixed  : {mismatches_category}")
    print(f"  • Location Mismatches Fixed  : {mismatches_location}")
    print("-" * 60)
    print(f"  • New Column Added           : `severity_flag`")
    print("    Value Distribution:")
    for val, count in df_v2["severity_flag"].value_counts().items():
        print(f"      - {val:<15} : {count:>4} rows")
    print("-" * 60)
    print(f"  • Saved Updated Dataset to   : {OUTPUT_CSV}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    update_dataset()
