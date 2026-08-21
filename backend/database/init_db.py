from sqlalchemy import inspect, text
from backend.database.connection import engine, Base
from backend.database.models import User, Disease, DiseaseSymptom, CaseHistory, PredictionDetail  # noqa


def init_database():
    """Create all tables if they don't exist and apply missing column/constraint migrations."""
    print("[DB] Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Check and migrate users table schema in SQLite/PostgreSQL if needed
    try:
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

                conn.commit()
    except Exception as e:
        print(f"[DB] Migration check notice: {e}")

    print("[DB] All tables created/verified successfully.")



if __name__ == "__main__":
    init_database()

