#!/usr/bin/env python3
"""
Reset ChargeBnB Database
Deletes all bookings and recreates the tables
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "backend" / "chargebnb.db"

def reset_database():
    print("\n" + "="*60)
    print("RESETTING CHARGEBNB DATABASE")
    print("="*60)

    try:
        # Delete old database if it exists
        if DB_PATH.exists():
            print(f"\nRemoving old database: {DB_PATH}")
            DB_PATH.unlink()
            print("✓ Old database removed")

        # Create new database with table
        print("\nCreating new database...")
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Create bookings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL,
                suburb TEXT NOT NULL,
                title TEXT NOT NULL,
                start TEXT NOT NULL,
                end TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                vehicle TEXT,
                promo TEXT,
                hours REAL NOT NULL,
                quoted_price_per_hour REAL NOT NULL,
                backend_price_per_hour REAL NOT NULL,
                frontend_total_amount REAL NOT NULL,
                backend_expected_total REAL NOT NULL,
                status TEXT NOT NULL,
                time_band TEXT NOT NULL
            )
        """)

        conn.commit()

        # Verify
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"\n✓ Database created successfully")
        print(f"✓ File: {DB_PATH}")
        print(f"✓ Size: {DB_PATH.stat().st_size} bytes")
        print(f"\nTables created:")
        for table in tables:
            print(f"  - {table[0]}")

        conn.close()

        print("\n" + "="*60)
        print("✓ DATABASE RESET COMPLETE")
        print("="*60 + "\n")
        print("Next steps:")
        print("1. Start the backend: python3 -m uvicorn main:app --reload")
        print("2. Start the frontend: npm run dev")
        print("3. Try booking a charger")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    reset_database()
