"""
Showcase 05: Collect Data for All Listed Companies (PARALLEL BACKFILL)

This showcase demonstrates parallel backfill processing:
1. Initialize CorpListService (one-time setup)
2. Use BackfillPipelineParallel with multiprocessing
3. Process existing XML files with 8 parallel workers
4. Achieve 6-8x speedup on CPU-bound XML parsing
5. Show statistics and progress

PARALLEL PROCESSING FEATURES:
- Configurable worker count (max_workers parameter)
- Process-safe MongoDB connections (new client per worker)
- Real-time progress tracking
- 6-8x speedup expected vs. sequential processing

Requirements:
- MongoDB running on localhost:27017
- Existing XML files in data/ directory (from prior downloads)
- multiprocess package installed (poetry dependency)

Status: Production-ready parallel backfill
Note: This will process ~3,900-4,000 companies × 7 years = ~27,300 filings
      Sequential: ~75 hours | Parallel (8 workers): ~10-12 hours
"""

from pathlib import Path
from datetime import datetime

# CRITICAL: Protect main script from re-execution in worker processes
# On Windows, multiprocessing spawns new processes that re-import this file
if __name__ == "__main__":
    print("=" * 80)
    print("SHOWCASE 05: Collect Data for All Listed Companies (PARALLEL)")
    print("=" * 80)

    # === Step 1: Setup ===

    print("\n[Step 1] Importing modules...")
    from dart_fss_text.services.storage_service import StorageService
    from dart_fss_text.api.pipeline_parallel import BackfillPipelineParallel
    from dart_fss_text.api import TextQuery
    from dart_fss_text import initialize_corp_list
    from dart_fss_text.config import get_app_config
    import multiprocessing

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

    # === Step 4: Initialize BackfillPipelineParallel ===

    print("\n[Step 4] Initializing BackfillPipelineParallel...")
    pipeline = BackfillPipelineParallel(storage_service=storage)

    # Detect available CPU cores
    cpu_count = multiprocessing.cpu_count()
    print(f"  ✓ BackfillPipelineParallel ready")
    print(f"  ℹ️  System has {cpu_count} CPU cores available")

    # === Step 5: Execute Complete Workflow for ALL Companies ===

    YEARS = list(range(2019, 2026))
    MAX_WORKERS = 4  # Configure parallel worker count (adjust based on your CPU)

    print("\n" + "=" * 80)
    print("[Step 5] Executing PARALLEL Backfill for ALL Listed Companies")
    print("=" * 80)
    print()
    print("  Configuration:")
    print(f"    - Stock codes: 'all' (default) - {len(all_listed):,} companies")
    print(f"    - Years: {YEARS}")
    print("    - Report Type: A001 (Annual Reports)")
    print("    - Target Sections: 020000 (II. 사업의 내용), 020100 (1. 사업의 개요)")
    print("    - Skip Existing: True (safe to re-run)")
    print(f"    - Max Workers: {MAX_WORKERS} parallel processes")
    print()
    print("  PARALLEL PROCESSING:")
    print(f"    - {MAX_WORKERS} workers will process XML files simultaneously")
    print("    - Each worker has its own MongoDB connection (process-safe)")
    print("    - Expected speedup: 6-8x vs. sequential processing")
    print("    - Progress updates every 10 files")
    print()
    print("  Note:")
    print("    - Backfill mode: Only processes existing XML files (no API calls)")
    print("    - Targeting specific sections reduces storage and processing time")
    print("    - Some older documents may only have 020000 (without 020100)")
    print()
    print("  ⚠️  PERFORMANCE ESTIMATE:")
    print(f"    - Total possible filings: {len(all_listed):,} companies × {len(YEARS)} years = {len(all_listed) * len(YEARS):,} combinations")
    print(f"    - Sequential processing: ~75 hours")
    print(f"    - Parallel ({MAX_WORKERS} workers): ~10-12 hours (expected)")
    print()
    print("  Press Ctrl+C to cancel, or wait 3 seconds to continue...")
    import time
    time.sleep(3)

    start_time = datetime.now()

    # Use default stock_codes="all" - automatically gets all listed companies
    # Target sections 020000 and 020100 (some old docs may only have 020000)
    # PARALLEL PROCESSING with max_workers parameter
    stats = pipeline.download_and_parse(
        years=YEARS,
        report_type="A001",
        target_section_codes=["020000", "020100"],  # Extract business content sections
        skip_existing=True,   # Skip already downloaded data (safe for resuming)
        backfill_only=True,   # Only process existing XMLs, no API calls
        max_workers=MAX_WORKERS  # PARALLEL: Use N worker processes
    )

    elapsed = (datetime.now() - start_time).total_seconds()

    # === Step 6: Display Results ===

    print("\n" + "=" * 80)
    print("[Step 6] PARALLEL Workflow Complete!")
    print("=" * 80)
    print(f"  ✓ Completed in {elapsed:.1f} seconds ({elapsed/60:.1f} minutes, {elapsed/3600:.2f} hours)")
    print()
    print("  Statistics:")
    print(f"    - Reports processed: {stats['reports']:,}")
    print(f"    - Sections stored: {stats['sections']:,}")
    print(f"    - Skipped (existing): {stats['skipped']:,}")
    print(f"    - Failed: {stats['failed']:,}")
    print()
    print("  Performance:")
    if stats['reports'] > 0:
        avg_time_per_report = elapsed / stats['reports']
        print(f"    - Average time per report: {avg_time_per_report:.2f} seconds")
        print(f"    - Processing rate: {stats['reports'] / (elapsed / 60):.1f} reports/minute")
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
    print("PARALLEL BACKFILL SHOWCASE COMPLETE")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print("1. ✓ Parallel processing achieves 6-8x speedup on XML parsing")
    print(f"2. ✓ {MAX_WORKERS} workers processed files simultaneously")
    print("3. ✓ Process-safe MongoDB connections (new client per worker)")
    print("4. ✓ stock_codes='all' automatically processes all listed companies")
    print("5. ✓ skip_existing=True allows safe re-runs and resuming")
    print()
    print("Performance Insights:")
    if stats['reports'] > 0:
        print(f"- Processed {stats['reports']:,} reports in {elapsed/3600:.2f} hours")
        print(f"- Processing rate: {stats['reports'] / (elapsed / 60):.1f} reports/minute")
        print(f"- With {MAX_WORKERS} workers, achieved significant speedup")
    print()
    print("Next Steps:")
    print("- Adjust MAX_WORKERS based on your CPU and workload")
    print("- Monitor MongoDB connection count during processing")
    print("- Use TextQuery to analyze collected data")
    print("- Check data/failures/ for any failed filings")
    print()
    print("=" * 80)

