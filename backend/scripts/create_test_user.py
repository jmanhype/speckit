#!/usr/bin/env python
"""Create a test user for local development.

Usage:
    python scripts/create_test_user.py
"""
import sys
from pathlib import Path

# Add parent directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import SessionLocal
from src.models.vendor import Vendor
from src.services.auth_service import AuthService


def create_test_user():
    """Create a test vendor account for development."""
    db = SessionLocal()
    auth_service = AuthService()

    try:
        # Check if test user already exists
        existing = db.query(Vendor).filter(Vendor.email == "test@example.com").first()

        if existing:
            print("✅ Test user already exists!")
            print(f"   Email: test@example.com")
            print(f"   Password: test123")
            print(f"   Business: {existing.business_name}")
            return

        # Create test vendor
        vendor = Vendor(
            email="test@example.com",
            password_hash=auth_service.hash_password("test123"),
            business_name="Test Farmers Market",
            subscription_tier="mvp",
            subscription_status="trial",
            square_connected=False,
        )

        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        print("✅ Test user created successfully!")
        print("")
        print("Login credentials:")
        print("  Email: test@example.com")
        print("  Password: test123")
        print("")
        print(f"  Vendor ID: {vendor.id}")
        print(f"  Business: {vendor.business_name}")
        print(f"  Subscription: {vendor.subscription_tier} ({vendor.subscription_status})")
        print("")
        print("Use these credentials to login at http://localhost:3000")

    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_test_user()
