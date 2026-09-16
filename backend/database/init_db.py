from sqlalchemy import inspect, text
from backend.database.connection import engine, Base
from backend.database.models import User, Disease, DiseaseSymptom, CaseHistory, PredictionDetail  # noqa


def init_database():
    """Create all tables if they don't exist and apply missing column/constraint migrations."""
    print("[DB] Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)

        # Check and migrate users table schema in SQLite/PostgreSQL if needed
        inspector = inspect(engine)
        if "users" in inspector.get_table_names():
            user_cols = {c["name"]: c for c in inspector.get_columns("users")}
            
            with engine.connect() as conn:
                # Add role column if missing
                if "role" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'patient'"))
                    conn.execute(text("UPDATE users SET role = 'patient' WHERE role IS NULL"))
                    print("[DB] Added missing 'role' column to users table.")

                # Add is_active column if missing
                if "is_active" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                    conn.execute(text("UPDATE users SET is_active = 1 WHERE is_active IS NULL"))
                    print("[DB] Added missing 'is_active' column to users table.")

                # Profile & Clinical Fields
                profile_fields = [
                    ("phone", "VARCHAR(50)"),
                    ("address", "TEXT"),
                    ("city", "VARCHAR(100)"),
                    ("state", "VARCHAR(100)"),
                    ("zip_code", "VARCHAR(30)"),
                    ("date_of_birth", "VARCHAR(50)"),
                    ("gender", "VARCHAR(30)"),
                    ("bio", "TEXT"),
                    ("specialization", "VARCHAR(150)"),
                    ("hospital_affiliation", "VARCHAR(255)"),
                    ("license_number", "VARCHAR(100)"),
                    ("emergency_contact", "VARCHAR(100)"),
                    ("emergency_phone", "VARCHAR(50)"),
                    ("allergies", "TEXT"),
                ]
                for col_name, col_type in profile_fields:
                    if col_name not in user_cols:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                        print(f"[DB] Added missing '{col_name}' column to users table.")

                conn.commit()

        # Auto-seed diseases and symptoms if empty
        from backend.database.connection import SessionLocal
        from backend.config import settings
        db = SessionLocal()
        try:
            if db.query(Disease).count() == 0:
                print("[DB] Empty database detected. Auto-seeding initial disease and symptom datasets...")
                from backend.database.seed_database import seed_diseases, seed_symptoms
                name_to_id = seed_diseases(db, settings.DISEASES_CSV)
                seed_symptoms(db, settings.SYMPTOMS_CSV, name_to_id)
                print("[DB] Auto-seeding completed successfully.")
        except Exception as seed_err:
            print(f"[DB NOTICE] Auto-seed notice: {seed_err}")
        finally:
            db.close()

        print("[DB] All tables created/verified successfully.")
    except Exception as e:
        print(f"[DB NOTICE] Table initialization notice: {e}")


if __name__ == "__main__":
    init_database()
