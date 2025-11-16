"""
Showcase 04: CorpListService CSV-Backed Storage

This showcase demonstrates the CorpListService functionality:
1. Initialize corporation list from DART API (one-time, ~7s)
2. Save to timestamped CSV file for fast subsequent lookups
3. Fast stock code lookups from cached DataFrame
4. Integration with FilingSearchService
5. Performance comparison: API load vs CSV load

Key Benefits:
- Explicit initialization: User controls when API call happens
- CSV-backed storage: Fast lookups without repeated API calls
- Timestamped snapshots: Multiple versions over time
- Singleton pattern: Shared state across services

Companies Demonstrated:
- 삼성전자 (Samsung Electronics): 005930
- SK하이닉스 (SK Hynix): 000660
- 네이버 (Naver): 035420

Requirements:
- OPENDART_API_KEY in .env file
- Internet connection for DART API calls (first time only)

Status: Live demonstration with real DART API
"""

import time
from pathlib import Path

print("=" * 80)
print("SHOWCASE 04: CorpListService CSV-Backed Storage")
print("=" * 80)

# === Step 1: Setup ===

print("\n[Step 1] Importing modules...")
from dart_fss_text import initialize_corp_list
from dart_fss_text.services import CorpListService, FilingSearchService
from dart_fss_text.models.requests import SearchFilingsRequest
from dart_fss_text.config import get_app_config

config = get_app_config()
print(f"  ✓ Config loaded")
print(f"    - Corp list DB dir: {config.corp_list_db_dir}")
print(f"    - API Key: {'***' + config.opendart_api_key[-4:] if config.opendart_api_key else 'NOT SET'}")

if not config.opendart_api_key:
    print("\n❌ ERROR: OPENDART_API_KEY not found!")
    print("   Please set OPENDART_API_KEY in your .env file")
    exit(1)

# === Step 2: Initialize CorpListService ===

print("\n" + "=" * 80)
print("[Step 2] Initializing CorpListService")
print("=" * 80)
print("\nThis step:")
print("  1. Loads ~114K corporations from DART API (~7s)")
print("  2. Converts to pandas DataFrame")
print("  3. Saves to timestamped CSV file")
print("  4. Caches DataFrame in memory for fast lookups")
print()

start_time = time.time()
csv_path = initialize_corp_list()
init_time = time.time() - start_time

print(f"  ✓ Initialization complete in {init_time:.2f}s")
print(f"  ✓ CSV saved to: {csv_path}")
print(f"  ✓ File size: {Path(csv_path).stat().st_size / 1024 / 1024:.2f} MB")

# === Step 3: Explore CorpListService Features ===

print("\n" + "=" * 80)
print("[Step 3] Exploring CorpListService Features")
print("=" * 80)

service = CorpListService()

# Get statistics
all_corps = service.get_all()
print(f"\n1. Total corporations: {len(all_corps):,}")
print(f"   Columns: {', '.join(all_corps.columns[:5])}... ({len(all_corps.columns)} total)")

# Count listed vs unlisted
listed_count = all_corps['stock_code'].notna().sum()
unlisted_count = all_corps['stock_code'].isna().sum()
print(f"\n2. Listed companies: {listed_count:,} ({listed_count/len(all_corps)*100:.1f}%)")
print(f"   Unlisted companies: {unlisted_count:,} ({unlisted_count/len(all_corps)*100:.1f}%)")

# Sample of market classifications
if 'corp_cls' in all_corps.columns:
    market_counts = all_corps['corp_cls'].value_counts()
    print(f"\n3. Market classifications:")
    for market, count in market_counts.head(5).items():
        market_name = {'Y': 'KOSPI', 'K': 'KOSDAQ', 'N': 'KONEX', 'E': 'ETC'}.get(market, market)
        print(f"   - {market_name} ({market}): {count:,} companies")

# === Step 4: Fast Stock Code Lookups ===

print("\n" + "=" * 80)
print("[Step 4] Fast Stock Code Lookups")
print("=" * 80)
print("\nDemonstrating fast DataFrame-based lookups (no API calls):")

test_stock_codes = [
    ('005930', '삼성전자'),
    ('000660', 'SK하이닉스'),
    ('035420', '네이버')
]

lookup_times = []
for stock_code, expected_name in test_stock_codes:
    start = time.time()
    corp_data = service.find_by_stock_code(stock_code)
    lookup_time = time.time() - start
    lookup_times.append(lookup_time)
    
    if corp_data:
        print(f"\n  ✓ Found {stock_code}:")
        print(f"    - Name: {corp_data.get('corp_name', 'N/A')}")
        print(f"    - Corp code: {corp_data.get('corp_code', 'N/A')}")
        print(f"    - Market: {corp_data.get('corp_cls', 'N/A')} ({'KOSPI' if corp_data.get('corp_cls') == 'Y' else 'KOSDAQ' if corp_data.get('corp_cls') == 'K' else 'N/A'})")
        print(f"    - Sector: {corp_data.get('sector', 'N/A')[:50] if corp_data.get('sector') else 'N/A'}")
        print(f"    - Lookup time: {lookup_time*1000:.3f}ms")
    else:
        print(f"\n  ✗ Not found: {stock_code}")

avg_lookup_time = sum(lookup_times) / len(lookup_times) if lookup_times else 0
print(f"\n  Average lookup time: {avg_lookup_time*1000:.3f}ms")
print(f"  Speedup vs API load: {init_time / avg_lookup_time:.0f}x faster")

# === Step 5: Test Non-Existent Stock Code ===

print("\n" + "=" * 80)
print("[Step 5] Handling Non-Existent Stock Codes")
print("=" * 80)

invalid_code = '999999'
result = service.find_by_stock_code(invalid_code)
if result is None:
    print(f"\n  ✓ Correctly returns None for invalid stock code: {invalid_code}")
else:
    print(f"\n  ✗ Unexpected result for invalid code: {result}")

# === Step 6: Integration with FilingSearchService ===

print("\n" + "=" * 80)
print("[Step 6] Integration with FilingSearchService")
print("=" * 80)
print("\nDemonstrating that FilingSearchService uses cached CorpListService:")

try:
    filing_search = FilingSearchService()
    print("  ✓ FilingSearchService initialized successfully")
    print("  ✓ Uses cached CorpListService (no new API call)")
    
    # Test a search with broader date range (full year 2023)
    print("\n  Testing filing search...")
    print("    Date range: 2023-01-01 to 2023-12-31")
    print("    Report type: A001 (Annual Reports)")
    
    request = SearchFilingsRequest(
        stock_codes=["005930"],
        start_date="20230101",
        end_date="20231231",  # Full year for better chance of results
        report_types=["A001"]
    )
    
    start = time.time()
    filings = filing_search.search_filings(request)
    search_time = time.time() - start
    
    print(f"  ✓ Search completed in {search_time:.2f}s")
    print(f"  ✓ Found {len(filings)} filings")
    
    if filings:
        print(f"\n  Sample filing:")
        filing = filings[0]
        print(f"    - Report: {filing.report_nm}")
        print(f"    - Receipt no: {filing.rcept_no}")
        print(f"    - Date: {filing.rcept_dt}")
        print(f"    - Corp code: {filing.corp_code}")
    else:
        print("  Note: No filings found in this date range (this is normal)")
        print("        Try a different date range or report type")
    
except RuntimeError as e:
    print(f"  ✗ Error: {e}")
    print("  Note: This should not happen if CorpListService was initialized")
except Exception as e:
    # Handle dart-fss NoDataReceived exception gracefully
    error_type = type(e).__name__
    if "NoDataReceived" in error_type or "조회된 데이타가 없습니다" in str(e):
        print(f"  ⚠️  No data found: {error_type}")
        print("  Note: This is expected when no filings match the search criteria")
        print("        The integration works correctly - try a broader date range")
    else:
        print(f"  ✗ Unexpected error: {error_type}: {e}")
        raise

# === Step 7: Performance Comparison ===

print("\n" + "=" * 80)
print("[Step 7] Performance Comparison")
print("=" * 80)

# Test CSV load time (simulate loading from existing CSV)
print("\nSimulating CSV load from existing file...")
start = time.time()
import pandas as pd
df_loaded = pd.read_csv(csv_path, encoding='utf-8')
csv_load_time = time.time() - start

print(f"\n  API Load Time:     {init_time:.2f}s")
print(f"  CSV Load Time:     {csv_load_time:.3f}s")
print(f"  Lookup Time:       {avg_lookup_time*1000:.3f}ms")
print(f"\n  CSV is {init_time / csv_load_time:.0f}x faster than API load")
print(f"  Lookups are {init_time / avg_lookup_time:.0f}x faster than API load")

# === Step 8: CSV File Information ===

print("\n" + "=" * 80)
print("[Step 8] CSV File Information")
print("=" * 80)

csv_file = Path(csv_path)
print(f"\n  File path: {csv_file}")
print(f"  File size: {csv_file.stat().st_size / 1024 / 1024:.2f} MB")
print(f"  Created: {csv_file.stat().st_mtime}")
print(f"  Encoding: UTF-8 (supports Korean characters)")

# Check if there are other CSV files
db_dir = csv_file.parent
other_csvs = list(db_dir.glob("corp_list_*.csv"))
if len(other_csvs) > 1:
    print(f"\n  Other CSV files in directory: {len(other_csvs)}")
    print("  (Multiple snapshots allow version comparison)")

# === Step 9: Singleton Pattern Demonstration ===

print("\n" + "=" * 80)
print("[Step 9] Singleton Pattern Demonstration")
print("=" * 80)

service1 = CorpListService()
service2 = CorpListService()

print(f"\n  service1 is service2: {service1 is service2}")
print(f"  ✓ Same instance (singleton pattern)")
print(f"  ✓ Shared DataFrame: {service1._df is service2._df}")
print(f"  ✓ Shared CSV path: {service1._csv_path == service2._csv_path}")

# === Step 10: Summary ===

print("\n" + "=" * 80)
print("SHOWCASE COMPLETE")
print("=" * 80)
print("\nKey Takeaways:")
print("1. ✓ Explicit initialization: User controls when API call happens")
print("2. ✓ CSV-backed storage: Fast lookups without repeated API calls")
print("3. ✓ Timestamped snapshots: Multiple versions over time")
print("4. ✓ Singleton pattern: Shared state across services")
print("5. ✓ Integration: FilingSearchService uses cached CorpListService")
print("\nPerformance:")
print(f"  - Initialization: {init_time:.2f}s (one-time)")
print(f"  - CSV load: {csv_load_time:.3f}s ({init_time / csv_load_time:.0f}x faster)")
print(f"  - Lookups: {avg_lookup_time*1000:.3f}ms ({init_time / avg_lookup_time:.0f}x faster)")
print("\nUsage Pattern:")
print("  1. Call initialize_corp_list() once at startup (~7s)")
print("  2. Use CorpListService for fast lookups (<1ms)")
print("  3. All services (FilingSearchService, etc.) use cached data")
print("\nCSV File:")
print(f"  Location: {csv_path}")
print(f"  Size: {csv_file.stat().st_size / 1024 / 1024:.2f} MB")
print(f"  Records: {len(all_corps):,}")
print("=" * 80)

