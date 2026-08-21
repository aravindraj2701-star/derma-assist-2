#!/usr/bin/env python3
"""
DermaAssist CLI — First-Time Admin Account Promotion & Bootstrap Tool.

Usage:
    python scripts/promote_admin.py <email>
    python scripts/promote_admin.py admin@dermaassist.local --name "Lead Administrator" --password "secureAdminPass123"

This script safely elevates an existing user account to 'admin' role or creates a new administrator account.
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database.connection import SessionLocal
from backend.database.init_db import init_database
from backend.database.models import User, AdminAuditLog, LoginActivity
from backend.utils.hash_utils import hash_password


def promote_or_create_admin(email: str, name: str = None, password: str = None, role: str = "admin") -> bool:
    init_database()
    db = SessionLocal()

    clean_email = email.strip().lower()
    clean_role = role.strip().lower() if role else "admin"
    if clean_role not in ("admin", "super_admin"):
        clean_role = "admin"

    if not clean_email or "@" not in clean_email:
        print(f"[ERROR] Invalid email address: '{email}'")
        return False

    try:
        user = db.query(User).filter(User.email == clean_email).first()

        if user:
            old_role = user.role
            user.role = clean_role
            user.is_active = True
            if password:
                user.hashed_password = hash_password(password)
            if name:
                user.name = name

            db.commit()
            db.refresh(user)

            # Record bootstrap audit log
            audit = AdminAuditLog(
                admin_id=user.user_id,
                action="USER_PROMOTED_CLI",
                target_user_id=user.user_id,
                details=f"User promoted to '{clean_role}' via promote_admin.py CLI script (previously '{old_role}').",
            )
            db.add(audit)
            db.commit()

            role_label = "SUPER ADMINISTRATOR" if clean_role == "super_admin" else "ADMINISTRATOR"
            print("=" * 60)
            print(f"  [SUCCESS] USER PROMOTED TO {role_label}")
            print("=" * 60)
            print(f"  User ID:    {user.user_id}")
            print(f"  Name:       {user.name}")
            print(f"  Email:      {user.email}")
            print(f"  Role:       {user.role} (was: {old_role})")
            print(f"  Status:     {'Active' if user.is_active else 'Suspended'}")
            print("=" * 60)
            print("  You can now log in at http://localhost:5173/login and access")
            print("  the Admin Console navigation item.")
            print("=" * 60)
            return True
        else:
            # Create new admin
            admin_name = name or ("Chief Administrator" if clean_role == "super_admin" else "System Administrator")
            admin_pass = password or "AdminPass@2026"
            hashed = hash_password(admin_pass)

            new_user = User(
                name=admin_name,
                email=clean_email,
                hashed_password=hashed,
                role=clean_role,
                is_active=True,
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            audit = AdminAuditLog(
                admin_id=new_user.user_id,
                action="ADMIN_CREATED_CLI",
                target_user_id=new_user.user_id,
                details=f"New {clean_role} account created directly via promote_admin.py CLI.",
            )
            db.add(audit)
            db.commit()

            role_label = "SUPER ADMINISTRATOR" if clean_role == "super_admin" else "ADMINISTRATOR"
            print("=" * 60)
            print(f"  [SUCCESS] NEW {role_label} ACCOUNT CREATED")
            print("=" * 60)
            print(f"  User ID:    {new_user.user_id}")
            print(f"  Name:       {new_user.name}")
            print(f"  Email:      {new_user.email}")
            print(f"  Role:       {new_user.role}")
            print(f"  Password:   {admin_pass if not password else '[Provided Password]'}")
            print("=" * 60)
            print("  You can now log in at http://localhost:5173/login and access")
            print("  the Admin Console navigation item.")
            print("=" * 60)
            return True

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to promote/create admin: {e}")
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Promote a user account to Admin or Super Admin role.")
    parser.add_argument("email", nargs="?", help="Email address of the user account to promote.")
    parser.add_argument("--email", dest="opt_email", help="Email address (alternative flag syntax).")
    parser.add_argument("--name", help="Name for newly created admin account.")
    parser.add_argument("--password", help="Password for newly created account or password reset.")
    parser.add_argument("--role", choices=["admin", "super_admin"], default="admin", help="Role to assign (admin or super_admin). Default: admin.")

    args = parser.parse_args()
    target_email = args.email or args.opt_email

    if not target_email:
        print("Usage: python scripts/promote_admin.py <email> [--role admin|super_admin] [--name <name>] [--password <password>]")
        sys.exit(1)

    success = promote_or_create_admin(
        email=target_email,
        name=args.name,
        password=args.password,
        role=args.role,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
