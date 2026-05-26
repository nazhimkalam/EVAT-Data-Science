#!/usr/bin/env python3
"""
Process Victoria EV Chargers CSV (after converting from Shapefile)
Merge with existing charger database
"""

import pandas as pd
from pathlib import Path
import sys

print("\n" + "█"*80)
print("█" + "  Victoria EV Chargers - CSV Processor".center(78) + "█")
print("█"*80)

# Paths
DATA_DIR = Path("backend/data")
DOWNLOADED_CSV = DATA_DIR / "victoria_ev_chargers.csv"  # <-- Your downloaded file
EXISTING_CHARGERS = DATA_DIR / "charger_info_mel.csv"
MERGED_CHARGERS = DATA_DIR / "charger_info_mel_expanded.csv"

# ============================================================
# STEP 1: Load Downloaded CSV
# ============================================================
print("\n📥 STEP 1: Loading downloaded CSV...")

if not DOWNLOADED_CSV.exists():
    print(f"❌ File not found: {DOWNLOADED_CSV}")
    print(f"\n📌 Please download and convert the shapefile first:")
    print(f"   1. Download from: https://discover.data.vic.gov.au/dataset/government-funded-public-ev-chargers")
    print(f"   2. Convert at: https://mygeodata.cloud/")
    print(f"   3. Save to: {DOWNLOADED_CSV}")
    sys.exit(1)

try:
    df = pd.read_csv(DOWNLOADED_CSV)
    print(f"✅ Loaded {len(df):,} records")
    print(f"📋 Columns: {list(df.columns)[:10]}")
except Exception as e:
    print(f"❌ Error reading CSV: {e}")
    sys.exit(1)

# ============================================================
# STEP 2: Clean and Standardize
# ============================================================
print("\n🧹 STEP 2: Cleaning data...")

# Lowercase all columns
df.columns = df.columns.str.lower().str.strip()

# Map common column names
column_mapping = {
    'name': 'charger_name',
    'site_name': 'charger_name',
    'sitename': 'charger_name',
    'location': 'charger_name',
    'address': 'address',
    'site_address': 'address',
    'suburb': 'suburb',
    'town': 'suburb',
    'lganame': 'suburb',  # Local Government Area Name
    'postcode': 'postal_code',
    'post_code': 'postal_code',
    'lat': 'latitude',
    'lon': 'longitude',
    'longitude': 'longitude',
    'latitude': 'latitude',
}

for old_col, new_col in column_mapping.items():
    if old_col in df.columns and new_col not in df.columns:
        df = df.rename(columns={old_col: new_col})

# Select relevant columns (only those we have)
available_cols = [col for col in ['charger_name', 'address', 'suburb', 'latitude', 'longitude', 'postal_code']
                   if col in df.columns]
df = df[available_cols]

print(f"✅ Standardized columns: {available_cols}")
print(f"✅ Records: {len(df)}")

# ============================================================
# STEP 3: Merge with Existing
# ============================================================
print("\n🔗 STEP 3: Merging with existing chargers...")

if not EXISTING_CHARGERS.exists():
    print(f"⚠️  Existing charger file not found: {EXISTING_CHARGERS}")
    combined = df
    print(f"   Using Victoria data only")
else:
    existing = pd.read_csv(EXISTING_CHARGERS)
    existing.columns = existing.columns.str.lower().str.strip()

    print(f"   Existing: {len(existing):,} chargers")
    print(f"   Victoria: {len(df):,} chargers")

    # Combine
    combined = pd.concat([existing, df], ignore_index=True)

    # Remove duplicates
    initial_count = len(combined)

    if 'address' in combined.columns:
        combined = combined.drop_duplicates(subset=['address'], keep='first')

    if 'latitude' in combined.columns and 'longitude' in combined.columns:
        combined = combined.drop_duplicates(subset=['latitude', 'longitude'], keep='first')

    removed = initial_count - len(combined)
    print(f"   Merged: {len(combined):,} unique chargers (+{len(combined) - len(existing)} new)")
    if removed > 0:
        print(f"   Removed {removed} duplicates")

# ============================================================
# STEP 4: Save
# ============================================================
print("\n💾 STEP 4: Saving merged dataset...")

combined.to_csv(MERGED_CHARGERS, index=False)
print(f"✅ Saved: {MERGED_CHARGERS}")

# ============================================================
# FINAL REPORT
# ============================================================
print("\n" + "█"*80)
print("✅ SUCCESS!")
print("█"*80)

print(f"\n📊 Final Statistics:")
print(f"   Total chargers: {len(combined):,}")
print(f"   Columns: {list(combined.columns)}")
print(f"   File: {MERGED_CHARGERS}")

# Data quality
print(f"\n📋 Data Quality:")
for col in combined.columns:
    complete = (combined[col].notna().sum() / len(combined) * 100)
    status = "✅" if complete > 95 else "⚠️" if complete > 80 else "❌"
    print(f"   {status} {col}: {complete:.0f}% complete")

print(f"\n📌 Next Steps:")
print(f"   1. Update backend/data/charger_info_mel.csv with {MERGED_CHARGERS}")
print(f"   2. Retrain your pricing model with expanded coverage")
print(f"   3. Test charger availability across more suburbs")

print("\n" + "█"*80)
print()
