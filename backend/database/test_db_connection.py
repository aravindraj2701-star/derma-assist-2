"""
Database Connectivity Test Script
Tests the database connection, connection pool, SSL handshake, and table inspection.
"""

import os
import sys
from sqlalchemy import text, inspect

from backend.config import settings
from backend.database.connection import engine, check_db_connection


def run_connectivity_test():
    print("=" * 60)
    print("  DERMA ASSIST — Database Connectivity Test")
    print("=" * 60)
    
    db_url = (settings.DATABASE_URL or os.getenv("DATABASE_URL") or "").strip()
    # Mask password for secure console output
    masked_url = db_url
    if "@" in db_url and "://" in db_url:
        prefix, rest = db_url.split("://", 1)
        if ":" in rest.split("@")[0]:
            user_part, host_part = rest.split("@", 1)
            username = user_part.split(":")[0]
            masked_url = f"{prefix}://{username}:****@{host_part}"
    
    print(f"Target Database URL: {masked_url}")
    print(f"Dialect Engine:     {engine.dialect.name}")
    print(f"Connection Pool:    Size={engine.pool.size()}, Overflow={engine.pool._max_overflow}")

    status = check_db_connection()
    if status.get("connected"):
        print("\n[SUCCESS] Connectivity Test Passed! (SELECT 1 succeeded)")
        print(f"[STATUS] Database is healthy. Is PostgreSQL: {status.get('is_postgres')}")
        
        # Test inspecting tables
        try:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"[INFO] Existing tables in database ({len(tables)}): {', '.join(tables)}")
        except Exception as e:
            print(f"[WARNING] Table inspection error: {e}")
            
        print("=" * 60)
        return 0
    else:
        print("\n[ERROR] Connectivity Test Failed!")
        print(f"[ERROR DETAIL] {status.get('error')}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(run_connectivity_test())
