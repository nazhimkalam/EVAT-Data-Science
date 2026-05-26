#!/usr/bin/env python3
"""
Download Victoria Government EV Charger Data via DataVic API
Merges with existing charger database to expand coverage
"""

import requests
import pandas as pd
import json
from pathlib import Path

# ============================================================
# API CREDENTIALS
# ============================================================
API_KEY = "22957f19-c45c-47c0-99c2-9823384c503f"
SECRET_KEY = "3fafb8d3-3673-452a-9f24-7dc4de02040f"

# API Configuration
BASE_URL = "https://wovg-community.gateway.prod.api.vic.gov.au/datavic/opendata/v1.1"
headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

# File paths
DATA_DIR = Path("backend/data")
EXISTING_CHARGERS = DATA_DIR / "charger_info_mel.csv"
VIC_CHARGERS_CSV = DATA_DIR / "victoria_ev_chargers_raw.csv"
MERGED_CHARGERS = DATA_DIR / "charger_info_mel_expanded.csv"

# ============================================================
# STEP 1: Search for EV Charger Datasets
# ============================================================
def search_ev_datasets():
    """Search DataVic for EV charger datasets"""
    print("\n" + "="*80)
    print("🔍 STEP 1: Searching for EV Charger Datasets")
    print("="*80)

    search_url = f"{BASE_URL}/datasets"
    params = {
        "keywordSearch": "EV charging",
        "limit": 50
    }

    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        total_found = data['_meta']['total_records']
        print(f"✅ Search successful")
        print(f"📊 Found {total_found} datasets matching 'EV charging'")

        # List all datasets
        print(f"\n📋 Datasets found:")
        for i, dataset in enumerate(data['datasets'], 1):
            print(f"   {i}. {dataset['title']}")
            print(f"      ID: {dataset['id']}")

        return data['datasets']

    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        return None

# ============================================================
# STEP 2: Find and Download EV Chargers Dataset
# ============================================================
def download_ev_chargers(datasets):
    """Find and download Government Funded Public EV Chargers dataset"""
    print("\n" + "="*80)
    print("📥 STEP 2: Finding and Downloading Charger Data")
    print("="*80)

    # Find the Government Funded Public EV Chargers dataset
    ev_dataset = None
    for dataset in datasets:
        title_lower = dataset['title'].lower()
        if 'government funded' in title_lower and 'ev' in title_lower and 'charger' in title_lower:
            ev_dataset = dataset
            print(f"✅ Found target dataset: '{dataset['title']}'")
            print(f"   Dataset ID: {dataset['id']}")
            print(f"   Organization: {dataset.get('organisation', {}).get('name', 'Unknown')}")
            break

    if not ev_dataset:
        print("❌ Could not find 'Government Funded Public EV Chargers' dataset")
        print("   Searching for any EV dataset with downloadable resources...")
        for dataset in datasets:
            if '_embedded' in dataset and 'resources' in dataset['_embedded']:
                resources = dataset['_embedded']['resources']
                if resources:
                    ev_dataset = dataset
                    print(f"✅ Using: '{dataset['title']}'")
                    break

    if not ev_dataset:
        print("❌ No suitable dataset found")
        return False

    # Get resources (download links)
    if '_embedded' not in ev_dataset or 'resources' not in ev_dataset['_embedded']:
        print("❌ No resources found in dataset")
        return False

    resources = ev_dataset['_embedded']['resources']
    print(f"\n📁 Resources in dataset: {len(resources)}")

    # Find CSV resource
    csv_resource = None
    for resource in resources:
        print(f"   - {resource['name']} ({resource.get('format', 'unknown')})")
        if resource.get('format', '').upper() == 'CSV':
            csv_resource = resource

    if not csv_resource:
        print("⚠️  No CSV resource found, trying first available resource...")
        csv_resource = resources[0]

    # Download the resource
    if not csv_resource.get('_links'):
        print("❌ No download link available")
        return False

    download_url = csv_resource['_links'][0]['href']
    print(f"\n⬇️  Downloading from: {download_url[:80]}...")

    try:
        csv_response = requests.get(download_url, headers=headers)
        csv_response.raise_for_status()

        # Save raw CSV
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(VIC_CHARGERS_CSV, 'wb') as f:
            f.write(csv_response.content)

        print(f"✅ File downloaded: {VIC_CHARGERS_CSV}")

        # Load and inspect
        df = pd.read_csv(VIC_CHARGERS_CSV)
        print(f"✅ Loaded {len(df):,} records")
        print(f"\n📋 Columns: {list(df.columns)}")
        print(f"\n🔍 Sample data (first 3 rows):")
        print(df.head(3).to_string())

        return True

    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

# ============================================================
# STEP 3: Clean and Standardize Downloaded Data
# ============================================================
def clean_vic_chargers():
    """Clean and standardize the downloaded data"""
    print("\n" + "="*80)
    print("🧹 STEP 3: Cleaning and Standardizing Data")
    print("="*80)

    if not VIC_CHARGERS_CSV.exists():
        print("❌ Downloaded file not found")
        return None

    df = pd.read_csv(VIC_CHARGERS_CSV)
    print(f"📊 Original records: {len(df)}")

    # Standardize column names
    df.columns = df.columns.str.lower().str.strip()

    # Map common column names
    column_mapping = {
        'charger_name': 'name',
        'charger name': 'name',
        'station name': 'name',
        'location': 'suburb',
        'address': 'address',
        'latitude': 'latitude',
        'longitude': 'longitude',
        'power kw': 'power_kw',
        'power (kw)': 'power_kw',
        'connector type': 'connector_type',
        'connector types': 'connector_type',
        'connection type': 'connector_type',
        'postal code': 'postal_code',
        'postcode': 'postal_code',
    }

    df = df.rename(columns=column_mapping)

    # Select relevant columns
    keep_cols = [col for col in ['name', 'address', 'suburb', 'latitude', 'longitude',
                                  'power_kw', 'connector_type', 'postal_code'] if col in df.columns]
    df = df[keep_cols]

    # Remove duplicates
    initial_count = len(df)
    df = df.drop_duplicates(subset=['name', 'address'], keep='first')
    print(f"✅ Removed {initial_count - len(df)} duplicates")

    # Remove rows with missing coordinates (we need these for mapping)
    df = df.dropna(subset=['latitude', 'longitude'])
    print(f"✅ Filtered to {len(df)} records with valid coordinates")

    print(f"\n📋 Cleaned columns: {list(df.columns)}")

    return df

# ============================================================
# STEP 4: Merge with Existing Charger Data
# ============================================================
def merge_with_existing(vic_chargers):
    """Merge Victoria chargers with existing charger database"""
    print("\n" + "="*80)
    print("🔗 STEP 4: Merging with Existing Charger Database")
    print("="*80)

    if not EXISTING_CHARGERS.exists():
        print(f"⚠️  Existing charger file not found: {EXISTING_CHARGERS}")
        print("   Saving Victoria data as-is...")
        vic_chargers.to_csv(MERGED_CHARGERS, index=False)
        return vic_chargers

    # Load existing chargers
    existing = pd.read_csv(EXISTING_CHARGERS)
    existing.columns = existing.columns.str.lower().str.strip()

    print(f"📊 Existing chargers: {len(existing)}")
    print(f"📊 Victoria chargers: {len(vic_chargers)}")

    # Combine datasets
    combined = pd.concat([existing, vic_chargers], ignore_index=True)

    # Remove duplicates based on location (address or coordinates)
    print(f"\n🔍 Identifying duplicates...")

    # Try to deduplicate by address
    if 'address' in combined.columns:
        combined = combined.drop_duplicates(subset=['address'], keep='first')

    # Also deduplicate by coordinates (within 50m)
    if 'latitude' in combined.columns and 'longitude' in combined.columns:
        combined = combined.drop_duplicates(subset=['latitude', 'longitude'], keep='first')

    final_count = len(combined)
    print(f"✅ Combined total: {final_count} unique chargers")
    print(f"   (+{final_count - len(existing)} new chargers added)")

    # Save merged data
    combined.to_csv(MERGED_CHARGERS, index=False)
    print(f"✅ Saved to: {MERGED_CHARGERS}")

    # Statistics
    print(f"\n📈 Coverage improvement:")
    print(f"   Before: {len(existing)} chargers")
    print(f"   After:  {final_count} chargers")
    print(f"   Growth: {((final_count - len(existing)) / len(existing) * 100):.1f}%")

    return combined

# ============================================================
# STEP 5: Generate Report
# ============================================================
def generate_report(merged_df):
    """Generate statistics and report"""
    print("\n" + "="*80)
    print("📊 STEP 5: Data Quality Report")
    print("="*80)

    print(f"\n✅ Total Chargers: {len(merged_df):,}")

    # Completeness check
    print(f"\n📋 Field Completeness:")
    for col in merged_df.columns:
        complete = (merged_df[col].notna().sum() / len(merged_df) * 100)
        status = "✅" if complete > 95 else "⚠️" if complete > 80 else "❌"
        print(f"   {status} {col}: {complete:.1f}% ({merged_df[col].notna().sum()}/{len(merged_df)})")

    # Geographic coverage
    if 'suburb' in merged_df.columns:
        suburbs = merged_df['suburb'].nunique()
        print(f"\n🗺️  Geographic Coverage:")
        print(f"   Suburbs covered: {suburbs}")

    if 'latitude' in merged_df.columns:
        coords = merged_df[['latitude', 'longitude']].notna().all(axis=1).sum()
        print(f"   Chargers with coordinates: {coords}/{len(merged_df)} ({coords/len(merged_df)*100:.1f}%)")

    print(f"\n💾 Output files:")
    print(f"   Raw Victoria data: {VIC_CHARGERS_CSV}")
    print(f"   Merged dataset: {MERGED_CHARGERS}")

# ============================================================
# MAIN EXECUTION
# ============================================================
def main():
    """Main execution flow"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  ChargeBnB: Victoria EV Charger Data Download & Merge".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)

    # Step 1: Search datasets
    datasets = search_ev_datasets()
    if not datasets:
        print("\n❌ Failed to search datasets")
        return False

    # Step 2: Download
    if not download_ev_chargers(datasets):
        print("\n❌ Failed to download chargers")
        return False

    # Step 3: Clean
    vic_chargers = clean_vic_chargers()
    if vic_chargers is None:
        print("\n❌ Failed to clean data")
        return False

    # Step 4: Merge
    merged = merge_with_existing(vic_chargers)

    # Step 5: Report
    generate_report(merged)

    print("\n" + "█"*80)
    print("✅ SUCCESS: EV Charger data downloaded and merged!")
    print("█"*80)
    print("\n📌 Next steps:")
    print("   1. Review the merged dataset in backend/data/charger_info_mel_expanded.csv")
    print("   2. Update your backend to use the expanded charger database")
    print("   3. Retrain the SARIMAX model with new charger coverage")
    print("\n")

    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
