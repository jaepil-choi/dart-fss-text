"""
Showcase 05: Collect Data for All Listed Companies

This showcase demonstrates the new "all" stock_codes feature:
1. Initialize CorpListService (one-time setup)
2. Use DisclosurePipeline with stock_codes="all" (default)
3. Collect data for ALL listed companies automatically
4. Process years 2023-2024
5. Show statistics and progress

This is the SIMPLEST way to collect data for all companies without
manually specifying stock codes.

Requirements:
- MongoDB running on localhost:27017
- OPENDART API key in .env file
- Internet connection for DART API calls
- CorpListService must be initialized first

Status: Live smoke test with all listed companies
Note: This will process ~3,900-4,000 companies, which may take
      significant time and API calls. Consider using target_section_codes
      to reduce storage and processing time.
"""

from pathlib import Path
from datetime import datetime

print("=" * 80)
print("SHOWCASE 05: Collect Data for All Listed Companies")
print("=" * 80)

# === Step 1: Setup ===

print("\n[Step 1] Importing modules...")
from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.api import DisclosurePipeline, TextQuery
from dart_fss_text import initialize_corp_list
from dart_fss_text.config import get_app_config

# Load config
config = get_app_config()
print(f"  ✓ Config loaded")
print(f"    - MongoDB: {config.mongodb_uri}")
print(f"    - Database: {config.mongodb_database}")
print(f"    - Collection: {config.mongodb_collection}")
print(f"    - API Key: {'***' + config.opendart_api_key[-4:] if config.opendart_api_key else 'NOT SET'}")

# === Step 2: Initialize CorpListService ===

print("\n[Step 2] Initializing CorpListService...")
print("  This is a one-time setup that loads all companies from DART API.")
print("  Takes ~7 seconds, then caches to CSV for fast access.")
print()

start_time = datetime.now()
csv_path = initialize_corp_list()
init_time = (datetime.now() - start_time).total_seconds()

print(f"  ✓ CorpListService initialized in {init_time:.2f}s")
print(f"  ✓ CSV saved to: {csv_path}")

# Get statistics about listed companies
from dart_fss_text.services import CorpListService
service = CorpListService()
all_listed = service.get_all_listed_stock_codes()
print(f"  ✓ Found {len(all_listed):,} listed companies")
print(f"    Sample: {all_listed[:5]}...")

# === Step 3: Initialize StorageService ===

print("\n[Step 3] Initializing StorageService...")
storage = StorageService()
print(f"  ✓ Connected to MongoDB: {config.mongodb_database}.{config.mongodb_collection}")

# Check existing data
existing_count = storage.collection.count_documents({})
if existing_count > 0:
    print(f"  ⚠️  Found {existing_count:,} existing documents in collection")
    print("  Note: skip_existing=True will skip already downloaded data")
else:
    print("  ✓ Collection is empty (fresh start)")

# === Step 4: Initialize DisclosurePipeline ===

print("\n[Step 4] Initializing DisclosurePipeline...")
pipeline = DisclosurePipeline(storage_service=storage)
print(f"  ✓ DisclosurePipeline ready")

# === Step 5: Execute Complete Workflow for ALL Companies ===

YEARS = list(range(2012, 2026))

print("\n" + "=" * 80)
print("[Step 5] Executing Complete Workflow for ALL Listed Companies")
print("=" * 80)
print()
print("  Configuration:")
print(f"    - Stock codes: 'all' (default) - {len(all_listed):,} companies")
print(f"    - Years: {YEARS}")
print("    - Report Type: A001 (Annual Reports)")
print("    - Target Sections: 020000 (II. 사업의 내용), 020100 (1. 사업의 개요)")
print("    - Skip Existing: True (safe to re-run)")
print()
print("  Note:")
print("    - Targeting specific sections reduces storage and processing time")
print("    - Some older documents may only have 020000 (without 020100)")
print("    - Both sections will be extracted when available")
print()
print("  ⚠️  WARNING:")
print(f"    - This will process {len(all_listed):,} companies × {len(YEARS)} years = {len(all_listed) * len(YEARS):,} combinations")
print("    - Each combination may have 1+ reports")
print("    - This will take SIGNIFICANT time and API calls")
print()
print("  Press Ctrl+C to cancel, or wait 5 seconds to continue...")
import time
time.sleep(5)

start_time = datetime.now()

# Use default stock_codes="all" - automatically gets all listed companies
# Target sections 020000 and 020100 (some old docs may only have 020000)
stats = pipeline.download_and_parse(
    years=YEARS,
    report_type="A001",
    target_section_codes=["020000", "020100"],  # Extract business content sections
    skip_existing=True  # Skip already downloaded data (safe for resuming)
)

elapsed = (datetime.now() - start_time).total_seconds()

# === Step 6: Display Results ===

print("\n" + "=" * 80)
print("[Step 6] Workflow Complete!")
print("=" * 80)
print(f"  ✓ Completed in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
print()
print("  Statistics:")
print(f"    - Reports processed: {stats['reports']:,}")
print(f"    - Sections stored: {stats['sections']:,}")
print(f"    - Skipped (existing): {stats['skipped']:,}")
print(f"    - Failed: {stats['failed']:,}")
print()

# Calculate success rate
total_attempted = stats['reports'] + stats['failed'] + stats['skipped']
if total_attempted > 0:
    success_rate = (stats['reports'] / total_attempted) * 100
    print(f"  Success rate: {success_rate:.1f}%")
    print()

# === Step 7: Verify Data with TextQuery ===

print("\n" + "=" * 80)
print("[Step 7] Verifying Stored Data")
print("=" * 80)

query = TextQuery(storage_service=storage)

# Query a sample of companies to verify data
sample_companies = all_listed[:5]  # First 5 companies
print(f"\n  Querying sample companies: {sample_companies}")

try:
    result = query.get(
        stock_codes=sample_companies,
        years=YEARS,
        section_codes=["020000", "020100"]  # Business content sections
    )
    
    print(f"  ✓ Query executed successfully")
    print()
    print("  Results:")
    for year in sorted(result.keys()):
        print(f"    Year {year}:")
        for stock_code in sorted(result[year].keys()):
            sequence = result[year][stock_code]
            if sequence:
                print(f"      {stock_code} ({sequence.corp_name}):")
                print(f"        - Sections: {sequence.section_count}")
                print(f"        - Total words: {sequence.total_word_count:,}")
            else:
                print(f"      {stock_code}: No data found")
except Exception as e:
    print(f"  ⚠️  Query failed: {e}")
    print("  Note: This may be normal if no data was collected yet")

# === Step 8: Database Statistics ===

print("\n" + "=" * 80)
print("[Step 8] Database Statistics")
print("=" * 80)

try:
    # Count total documents
    total_docs = storage.collection.count_documents({})
    print(f"\n  Total documents in MongoDB: {total_docs:,}")
    
    # Count by year
    pipeline_stats = [
        {'$group': {
            '_id': '$year',
            'count': {'$sum': 1}
        }},
        {'$sort': {'_id': 1}}
    ]
    year_stats = list(storage.collection.aggregate(pipeline_stats))
    
    if year_stats:
        print("\n  Documents by year:")
        for stat in year_stats:
            year = stat['_id']
            count = stat['count']
            print(f"    {year}: {count:,} documents")
    
    # Count unique companies
    unique_companies = storage.collection.distinct('stock_code')
    print(f"\n  Unique companies: {len(unique_companies):,}")
    
except Exception as e:
    print(f"  ⚠️  Could not generate statistics: {e}")

# === Step 9: Summary ===

print("\n" + "=" * 80)
print("SHOWCASE COMPLETE")
print("=" * 80)
print()
print("Key Takeaways:")
print("1. ✓ stock_codes='all' automatically processes all listed companies")
print("2. ✓ No need to manually specify stock codes")
print("3. ✓ CorpListService provides cached access to all companies")
print("4. ✓ skip_existing=True allows safe re-runs and resuming")
print()
print("Next Steps:")
print("- Monitor API rate limits (DART has daily/hourly limits)")
print("- Consider processing in batches if hitting rate limits")
print("- Use TextQuery to analyze collected data")
print("- Note: Some older documents may only have 020000 section")
print()
print("=" * 80)

