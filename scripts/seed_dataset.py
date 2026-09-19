"""
Idempotent Dataset Seeder Script for PostgreSQL / SQLite
Reads the combined dermatological dataset (CSV/JSON), populates conditions and condition_images tables,
prevents duplicates, and reports total rows, inserted records, images cataloged, and skipped duplicates.
"""

import os
import sys
import time
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings
from backend.database.connection import SessionLocal, engine, check_db_connection
from backend.database.init_db import init_database
from backend.database.models import Condition, ConditionImage


def seed_dataset(csv_path: str = None, batch_size: int = 500):
    print("=" * 65)
    print("  DERMA ASSIST — Idempotent Dataset Seeder")
    print("=" * 65)

    start_time = time.time()

    # Ensure tables exist
    init_database()

    # Verify DB connectivity
    status = check_db_connection()
    if not status.get("connected"):
        print(f"[ERROR] Cannot connect to database: {status.get('error')}")
        return False

    print(f"[DB] Connected to engine: {status.get('engine')} (PostgreSQL: {status.get('is_postgres')})")

    # Locate CSV
    if not csv_path:
        csv_v2 = PROJECT_ROOT / "combined_skin_disease_dataset_v2.csv"
        csv_v1 = PROJECT_ROOT / "combined_skin_disease_dataset.csv"
        csv_path = csv_v2 if csv_v2.exists() else csv_v1

    csv_path = Path(csv_path)
    if not csv_path.exists():
        print(f"[ERROR] Dataset CSV file not found at: {csv_path}")
        return False

    print(f"[FILE] Reading dataset from: {csv_path.name}")
    try:
        df = pd.read_csv(csv_path)
        print(f"[INFO] Loaded {len(df):,} rows from CSV.")
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
        return False

    # Standardize column headers
    df.columns = [c.strip() for c in df.columns]

    db = SessionLocal()
    try:
        # 1. Fetch existing keys for idempotency checking: (condition_name, image_path)
        print("[IDEMPOTENCY] Querying existing records in database...")
        existing_conditions = db.query(Condition.condition_name, Condition.image_path).all()
        existing_set = set((str(name).strip().lower(), str(path).replace("\\", "/").strip().lower()) for name, path in existing_conditions if name and path)
        print(f"[IDEMPOTENCY] Found {len(existing_set):,} pre-existing condition records in DB.")

        total_rows = len(df)
        inserted_conditions = 0
        inserted_images = 0
        duplicates_skipped = 0

        pending_conditions = []

        for idx, row in df.iterrows():
            disease_name = str(row.get("unified_disease_label") or row.get("disease_name") or "Cutaneous Lesion").strip()
            raw_img_path = str(row.get("image_path") or "").replace("\\", "/").strip()
            category = str(row.get("category") or "Dermatological Condition").strip()
            body_loc = str(row.get("body_location") or "General Cutaneous Site").strip()
            symptoms_desc = str(row.get("symptoms_description") or row.get("description") or "").strip()
            source = str(row.get("source") or "ISIC Archive").strip()
            split = str(row.get("split") or "train").strip()
            severity = str(row.get("severity_flag") or row.get("severity") or "").strip()

            mal_val = row.get("malignant", 0)
            is_mal = 1 if mal_val in (1, "1", True, "true", "True") or "malignant" in category.lower() or "carcinoma" in disease_name.lower() or "melanoma" in disease_name.lower() else 0

            if not severity:
                severity = "Malignant" if is_mal else ("Pre-cancerous" if "actinic" in disease_name.lower() else "Benign")

            # Check duplicate idempotency key
            idempotency_key = (disease_name.lower(), raw_img_path.lower())
            if idempotency_key in existing_set:
                duplicates_skipped += 1
                continue

            # Construct working URL/path:
            # If path is already an external URL (http/https), save to image_url
            image_url = ""
            if raw_img_path.startswith("http://") or raw_img_path.startswith("https://"):
                image_url = raw_img_path
            elif raw_img_path:
                image_url = f"/dataset/image?path={raw_img_path}"

            cond = Condition(
                condition_name=disease_name,
                category=category,
                body_locations=body_loc,
                description=symptoms_desc,
                symptoms=symptoms_desc,
                image_path=raw_img_path,
                image_url=image_url,
                source=source,
                severity=severity,
                malignant=is_mal,
                split=split,
                date_added=datetime.utcnow().strftime("%Y-%m-%d"),
                created_at=datetime.utcnow(),
            )

            # Create related primary ConditionImage
            cond_img = ConditionImage(
                image_path=raw_img_path,
                image_url=image_url,
                is_primary=True,
                caption=f"Clinical reference photo for {disease_name}",
                created_at=datetime.utcnow(),
            )
            cond.images.append(cond_img)

            pending_conditions.append(cond)
            existing_set.add(idempotency_key)
            inserted_conditions += 1
            inserted_images += 1

            # Commit in batches
            if len(pending_conditions) >= batch_size:
                db.add_all(pending_conditions)
                db.commit()
                pending_conditions = []
                print(f"  Processed {idx + 1:,}/{total_rows:,} rows... (Inserted: {inserted_conditions:,}, Skipped: {duplicates_skipped:,})")

        # Flush remaining
        if pending_conditions:
            db.add_all(pending_conditions)
            db.commit()

        elapsed = time.time() - start_time
        print("\n" + "=" * 65)
        print("  DATASET SEEDING SUMMARY")
        print("=" * 65)
        print(f"Total Rows Read from CSV:    {total_rows:,}")
        print(f"New Condition Records Added: {inserted_conditions:,}")
        print(f"New Condition Images Linked: {inserted_images:,}")
        print(f"Duplicates Skipped:          {duplicates_skipped:,}")
        print(f"Total Conditions in DB Now:  {db.query(Condition).count():,}")
        print(f"Total Images in DB Now:      {db.query(ConditionImage).count():,}")
        print(f"Execution Time:              {elapsed:.2f} seconds")
        print("=" * 65)
        return True
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seeding failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    target_csv = sys.argv[1] if len(sys.argv) > 1 else None
    success = seed_dataset(target_csv)
    sys.exit(0 if success else 1)
