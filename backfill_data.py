"""
Backfill Script: Parse existing XML files and insert missing data to MongoDB

Use this script when:
- MongoDB was offline during data collection
- XML files exist in data/ but aren't in MongoDB
- You want to re-parse existing files with updated parser

This script will:
1. Traverse all XML files in data/ directory
2. Check if each rcept_no exists in MongoDB
3. Parse and insert missing data
4. Skip already-existing data (unless --force is used)
"""

from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.api.backfill import BackfillService
from dart_fss_text.config import get_app_config
from datetime import datetime
import sys

print("=" * 80)
print("BACKFILL SCRIPT: Parse existing XMLs and insert to MongoDB")
print("=" * 80)

# === Step 1: Load Configuration ===
print("\n[Step 1] Loading configuration...")
config = get_app_config()
print(f"  ✓ Config loaded")
print(f"    - MongoDB: {config.mongodb_uri}")
print(f"    - Database: {config.mongodb_database}")
print(f"    - Collection: {config.mongodb_collection}")

# === Step 2: Connect to MongoDB ===
print("\n[Step 2] Connecting to MongoDB...")
try:
    storage = StorageService()
    print(f"  ✓ Connected to MongoDB: {config.mongodb_database}.{config.mongodb_collection}")
except Exception as e:
    print(f"  ✗ Failed to connect to MongoDB!")
    print(f"    Error: {e}")
    print()
    print("  Please ensure MongoDB is running:")
    print("    - Check if MongoDB service is started")
    print("    - Verify connection string in .env file")
    print()
    sys.exit(1)

# === Step 3: Initialize Backfill Service ===
print("\n[Step 3] Initializing BackfillService...")
backfill = BackfillService(storage_service=storage)
print(f"  ✓ BackfillService ready")

# === Step 4: Configure Backfill ===
BASE_DIR = "data"
TARGET_SECTIONS = ["020100"]  # Only Business Overview section
REPORT_TYPE = "A001"
FORCE_REPARSE = False  # Set to True to re-parse existing data

print("\n[Step 4] Configuration:")
print(f"  Base directory: {BASE_DIR}")
print(f"  Target sections: {TARGET_SECTIONS}")
print(f"  Report type: {REPORT_TYPE}")
print(f"  Force re-parse: {FORCE_REPARSE}")
print()
print("  Note: This will scan all XML files in data/ directory")
print("        and insert missing data to MongoDB.")
print()

# Confirm before proceeding
try:
    response = input("  Continue? [y/N]: ").strip().lower()
    if response != 'y':
        print("\n  Cancelled by user.")
        sys.exit(0)
except KeyboardInterrupt:
    print("\n\n  Cancelled by user.")
    sys.exit(0)

# === Step 5: Run Backfill ===
print("\n[Step 5] Starting backfill process...")
print("  This may take a while...")
print()

start_time = datetime.now()

stats = backfill.backfill_from_directory(
    base_dir=BASE_DIR,
    target_section_codes=TARGET_SECTIONS,
    report_type=REPORT_TYPE,
    force=FORCE_REPARSE
)

elapsed = (datetime.now() - start_time).total_seconds()

# === Step 6: Display Results ===
print("\n" + "=" * 80)
print("BACKFILL COMPLETE")
print("=" * 80)
print()
print(f"⏱️  Total Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
print()
print("📊 Statistics:")
print(f"    🔍 Files scanned: {stats['scanned']}")
print(f"    ✓ Already in DB: {stats['existing']}")
print(f"    ➕ Newly processed: {stats['processed']}")
print(f"    📄 Sections inserted: {stats['sections']}")
print(f"    ✗ Failed: {stats['failed']}")
print()
print(f"💾 MongoDB collection '{config.mongodb_collection}' now contains updated data")
print()
print("=" * 80)

