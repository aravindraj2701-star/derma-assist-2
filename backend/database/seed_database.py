"""
Database Seeder — Import diseases.csv and disease_symptoms.csv into the database.
Prevents duplicate records on re-runs.
"""

import csv
import os

from backend.config import settings
from backend.database.connection import SessionLocal
from backend.database.models import Disease, DiseaseSymptom
from backend.database.init_db import init_database


def load_csv(filepath: str) -> list[dict]:
    """Load a CSV file and return list of dicts."""
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def seed_diseases(db, filepath: str) -> dict[str, int]:
    """Import diseases from CSV, skip duplicates. Returns name->id mapping."""
    rows = load_csv(filepath)
    if not rows:
        print("[WARN] No disease data to import.")
        return {}

    name_to_id = {}
    imported = 0
    skipped = 0

    for row in rows:
        name = row.get("disease_name", "").strip()
        if not name:
            continue

        existing = db.query(Disease).filter(Disease.name == name).first()
        if existing:
            name_to_id[name] = existing.disease_id
            skipped += 1
            continue

        disease = Disease(
            name=name,
            description=row.get("description", "").strip(),
            precautions=row.get("precautions", "").strip(),
            consult_doctor_if=row.get("consult_doctor_if", "").strip(),
            severity_level=row.get("severity_level", "").strip(),
        )
        db.add(disease)
        db.flush()
        name_to_id[name] = disease.disease_id
        imported += 1

    db.commit()
    print(f"[DISEASES] Imported: {imported}, Skipped (duplicates): {skipped}")
    return name_to_id


def seed_symptoms(db, filepath: str, name_to_id: dict[str, int]) -> None:
    """Import symptoms from CSV and link to diseases."""
    rows = load_csv(filepath)
    if not rows:
        print("[WARN] No symptom data to import.")
        return

    imported = 0
    skipped = 0

    for row in rows:
        disease_name = row.get("disease_name", "").strip()
        disease_id = name_to_id.get(disease_name)

        if not disease_id:
            disease = db.query(Disease).filter(Disease.name == disease_name).first()
            if disease:
                disease_id = disease.disease_id
                name_to_id[disease_name] = disease_id
            else:
                skipped += 1
                continue

        keyword = row.get("symptom_keyword", "").strip()
        description = row.get("symptom_description", "").strip()

        if not keyword:
            continue

        existing = (
            db.query(DiseaseSymptom)
            .filter(
                DiseaseSymptom.disease_id == disease_id,
                DiseaseSymptom.symptom_keyword == keyword,
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        symptom = DiseaseSymptom(
            disease_id=disease_id,
            symptom_keyword=keyword,
            symptom_description=description,
            severity=row.get("severity", "").strip(),
        )
        db.add(symptom)
        imported += 1

    db.commit()
    print(f"[SYMPTOMS] Imported: {imported}, Skipped (duplicates): {skipped}")


def main():
    """Run the full database seeding process."""
    print("=" * 50)
    print("  DERMA ASSIST — Database Seeder")
    print("=" * 50)

    # Create tables
    init_database()

    # Open session
    db = SessionLocal()
    try:
        # Seed diseases
        print("\n[1/2] Importing diseases...")
        name_to_id = seed_diseases(db, settings.DISEASES_CSV)

        # Seed symptoms
        print("\n[2/2] Importing disease symptoms...")
        seed_symptoms(db, settings.SYMPTOMS_CSV, name_to_id)

        print("\n[DONE] Database seeding complete!")
        print(f"  Diseases in DB: {db.query(Disease).count()}")
        print(f"  Symptoms in DB: {db.query(DiseaseSymptom).count()}")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
