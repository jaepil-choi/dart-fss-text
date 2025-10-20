"""
Batch Data Collection Script

Collects annual reports (A001) for all non-pennystock companies
and extracts only section 020100 (Business Overview).

Target Section: 020100 (1. 사업의 개요 - Business Overview)
Companies: All stocks from not_pennystock.txt (~2,370 companies)
Years: 2023, 2024, 2025
Report Type: A001 (Annual Reports)

Note: Uses target_section_codes to extract only one section per report,
      reducing storage by 99%+ and avoiding MongoDB 16MB size limits.
"""

from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.api import DisclosurePipeline
from dart_fss_text.config import get_app_config
from datetime import datetime

print("=" * 80)
print("BATCH DATA COLLECTION: Korean Annual Reports - Business Overview Section")
print("=" * 80)

# === Step 1: Load Configuration ===
print("\n[Step 1] Loading configuration...")
config = get_app_config()
print(f"  ✓ Config loaded")
print(f"    - MongoDB: {config.mongodb_uri}")
print(f"    - Database: {config.mongodb_database}")
print(f"    - Collection: {config.mongodb_collection}")
print(f"    - API Key: {'***' + config.opendart_api_key[-4:]}")

# === Step 2: Initialize MongoDB Connection ===
print("\n[Step 2] Connecting to MongoDB...")
storage = StorageService()
print(f"  ✓ Connected to MongoDB: {config.mongodb_database}.{config.mongodb_collection}")

# === Step 3: Load Stock Codes ===
print("\n[Step 3] Loading stock codes...")
with open("not_pennystock.txt", "r") as f:
    stock_codes = f.read().splitlines()
print(f"  ✓ Loaded {len(stock_codes)} stock codes from not_pennystock.txt")

# === Step 4: Configure Years ===
years = list(range(2010, 2023))
# years = [2023, 2024, 2025]
years = years[::-1]
print(f"\n[Step 4] Target years: {years}")

# === Step 5: Clear Previous Data ===
# print("\n[Step 5] Clearing previous data...")
# deleted_count = storage.collection.delete_many({}).deleted_count
# print(f"  ✓ Deleted {deleted_count} existing documents")

# === Step 6: Initialize Pipeline ===
print("\n[Step 6] Initializing DisclosurePipeline...")
pipeline = DisclosurePipeline(storage_service=storage)
print(f"  ✓ DisclosurePipeline ready")

# === Step 7: Execute Batch Collection ===
print("\n[Step 7] Starting batch data collection...")
print(f"  Companies: {len(stock_codes)} stocks")
print(f"  Years: {years}")
print(f"  Report Type: A001 (Annual Reports)")
print(f"  Target Section: 020100 (1. 사업의 개요 - Business Overview)")
print(f"  Skip Existing: Enabled (will skip already downloaded data)")
print()
print("  Note: Already downloaded year+stock combinations will be skipped")
print("        to save API calls. Safe to resume after interruption!")
print()
print("  This may take a while... Processing will continue even if individual files fail.")
print()

start_time = datetime.now()

stats = pipeline.download_and_parse(
    stock_codes=stock_codes,
    years=years,
    report_type="A001",
    # Target sections: 020100 (newer reports 2015+) or 020000 (older reports 2010-2014)
    # Will extract whichever exists in the report
    target_section_codes=["020100", "020000"],
    skip_existing=True  # Skip already downloaded data (default, safe for resuming)
)

elapsed = (datetime.now() - start_time).total_seconds()

# === Step 8: Display Results ===
print("\n" + "=" * 80)
print("BATCH COLLECTION COMPLETE")
print("=" * 80)
print()
print(f"⏱️  Total Time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
print()
print("📊 Statistics:")
print(f"    ✓ Reports processed: {stats['reports']}")
print(f"    ✓ Sections stored: {stats['sections']}")
print(f"    ⏭️  Skipped (existing): {stats['skipped']}")
print(f"    ✗ Failed: {stats['failed']}")
print()
print(f"💾 Storage: MongoDB collection '{config.mongodb_collection}' now contains {stats['sections']} sections")
print()
print("=" * 80)