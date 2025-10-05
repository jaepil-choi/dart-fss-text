"""
Showcase 03: High-Level DisclosurePipeline API

This showcase demonstrates the simplified high-level API for the complete workflow:
1. Initialize StorageService (explicit DB control)
2. Initialize DisclosurePipeline with StorageService
3. Execute complete workflow: search -> download -> parse -> store
4. Review statistics
5. Verify data with TextQuery

This is the SIMPLEST way to use dart-fss-text for data collection.

Companies:
- 삼성전자 (Samsung Electronics): 005930
- SK하이닉스 (SK Hynix): 000660

Years: 2023, 2024
Report Type: A001 (Annual Reports)

Requirements:
- MongoDB running on localhost:27017
- OPENDART API key in .env file
- Internet connection for DART API calls

Status: Live smoke test with high-level API
"""

from pathlib import Path
from datetime import datetime

print("=" * 80)
print("SHOWCASE 03: High-Level DisclosurePipeline API")
print("=" * 80)

# === Step 1: Setup ===

print("\n[Step 1] Importing modules...")
from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.api import DisclosurePipeline, TextQuery
from dart_fss_text.config import get_app_config

# Load config
config = get_app_config()
print(f"  ✓ Config loaded")
print(f"    - MongoDB: {config.mongodb_uri}")
print(f"    - Database: {config.mongodb_database}")
print(f"    - Collection: {config.mongodb_collection}")
print(f"    - API Key: {'***' + config.opendart_api_key[-4:]}")

# === Step 2: Initialize StorageService (Explicit DB Control) ===

print("\n[Step 2] Initializing StorageService...")
storage = StorageService()
print(f"  ✓ Connected to MongoDB: {config.mongodb_database}.{config.mongodb_collection}")

# Clear previous showcase data
print("  - Clearing previous data...")
storage.collection.delete_many({})
print(f"  ✓ Collection cleared")

# === Step 3: Initialize DisclosurePipeline ===

print("\n[Step 3] Initializing DisclosurePipeline...")
pipeline = DisclosurePipeline(storage_service=storage)
print(f"  ✓ DisclosurePipeline ready")

# === Step 4: Execute Complete Workflow ===

YEARS = [2018]

print("\n[Step 4] Executing complete workflow...")
print("  Companies: 삼성전자 (005930), SK하이닉스 (000660)")
print(f"  Years: {YEARS}")
print("  Report Type: A001 (Annual Reports)")
print()

start_time = datetime.now()

# Single method call to do everything!
stats = pipeline.download_and_parse(
    stock_codes=["005930", "000660"],
    years=YEARS,
    report_type="A001"
)

elapsed = (datetime.now() - start_time).total_seconds()

print("\n[Step 5] Workflow Complete!")
print(f"  ✓ Completed in {elapsed:.1f} seconds")
print()
print("  Statistics:")
print(f"    - Reports processed: {stats['reports']}")
print(f"    - Sections stored: {stats['sections']}")
print(f"    - Failed: {stats['failed']}")
print()

# === Step 5: Verify Data with TextQuery ===

print("\n[Step 6] Verifying stored data with TextQuery...")
query = TextQuery(storage_service=storage)

# Query all years and companies
result = query.get(
    stock_codes=["005930", "000660"],
    years=YEARS,
    section_codes=["020000"]  # 사업의 내용
)

print(f"  ✓ Query executed")
print()
print("  Results structure:")
print(result)
for year in sorted(result.keys()):
    print(f"    Year {year}:")
    for stock_code in sorted(result[year].keys()):
        sequence = result[year][stock_code]
        print(f"      {stock_code}")
        if sequence:
            metadata = sequence.metadata
            print(f"      {stock_code} ({metadata.corp_name}): {len(sequence)} sections")
            print(f"        - Report: {metadata.report_name}")
            print(f"        - Text length: {len(sequence.text):,} characters")
            
            # Show first section details
            if len(sequence) > 0:
                first_section = sequence[0]
                print(f"        - First section: {first_section.section_title}")
                print(f"        - Preview: {first_section.text[:100]}...")
        else:
            print(f"      {stock_code}: No data found")

# === Step 6: Summary ===

print("\n" + "=" * 80)
print("SHOWCASE COMPLETE")
print("=" * 80)
print()
print("Key Takeaways:")
print("1. ✓ DisclosurePipeline provides a single method for the entire workflow")
print("2. ✓ Explicit StorageService initialization allows DB connection verification")
print("3. ✓ Statistics returned for monitoring and debugging")
print("4. ✓ Data immediately queryable via TextQuery")
print()
print("Compare this to showcase_02:")
print("  - showcase_02: ~200 lines (low-level, manual workflow)")
print("  - showcase_03: ~130 lines (high-level, automated workflow)")
print()
print("This is the RECOMMENDED way to use dart-fss-text for data collection.")
print()
print("=" * 80)

