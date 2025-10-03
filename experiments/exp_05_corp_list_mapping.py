"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original Goal: Retrieve Listed Corporations and Create Stock Code Mapping
Date Created: 2025-10-02
Status: ✅ FINDINGS DOCUMENTED - Superseded by exp_08_corplist_test.py

WHAT THIS EXPERIMENT INVESTIGATED:
-----------------------------------
1. Load all corporations from DART using dart-fss
2. Filter to only listed stocks (non-null stock_code)
3. Extract all available attributes using Corp.to_dict()
4. Save to CSV for reference and validation
5. Understand corp_list structure and performance

CRITICAL FINDINGS:
------------------
1. **Corporation Counts**:
   - Total: 114,147 corporations
   - Listed (with stock_code): 3,901 (3.4%)
   - Unlisted: 110,246 (96.6%)

2. **Complete Schema** (11 columns via Corp.to_dict()):
   - Always present: corp_code, corp_name, corp_eng_name, stock_code, modify_date
   - Sometimes (70.9%): corp_cls, market_type, sector, product
   - Rarely (2.7%): trading_halt, issue

3. **Market Indicator** (corp_cls):
   - 'Y' = KOSPI (Korea Composite Stock Price Index)
   - 'K' = KOSDAQ (Korea Securities Dealers Automated Quotations)
   - 'N' = KONEX (Korea New Exchange)
   - 'E' = ETC (Exchange Traded Commodities)

4. **Data Completeness**:
   - 70.9% have complete metadata (corp_cls, sector, product)
   - 29.1% have missing data (likely delisted/suspended)

5. **Stock Code vs Corp Code**:
   - **stock_code**: 6 digits (e.g., "005930" for Samsung)
   - **corp_code**: 8 digits (e.g., "00126380" for Samsung)
   - Users provide stock_code, API requires corp_code
   - Mapping is essential for discovery service

WHAT WE LEARNED:
----------------
1. **Corp List Access**: Use `corp_list.corps` to get all corporations
   ```python
   corp_list = dart.get_corp_list()
   all_corps = corp_list.corps  # List of 114K+ Corp objects
   ```

2. **Listed vs Unlisted**: Filter by stock_code presence
   ```python
   listed = [c for c in corp_list.corps if c.stock_code is not None]
   # Result: 3,901 listed companies
   ```

3. **Stock→Corp Lookup**: Use find_by_stock_code()
   ```python
   samsung = corp_list.find_by_stock_code("005930")
   corp_code = samsung.corp_code  # "00126380"
   ```

4. **Performance Insight**: Initial load is slow (~7s), but:
   - Singleton pattern caches result
   - Subsequent calls are instant
   - No need for our own CSV caching!

5. **Attribute Access**: Use .to_dict() for all fields
   ```python
   corp_dict = corp.to_dict()
   # Returns dict with all 11 fields
   ```

WHY THIS IS NOW OBSOLETE:
--------------------------
1. **Better Experiment Exists**: exp_08_corplist_test.py provides:
   - More focused testing of CorpList behavior
   - Documents Singleton pattern with timing
   - Validates cached lookups are instant
   - More relevant to production use

2. **CSV Not Needed**: dart-fss's internal caching is sufficient
   - First call: ~7 seconds to load 114K companies
   - Subsequent calls: 0.000 seconds (Singleton)
   - No need to maintain our own CSV cache

3. **Schema Documented**: Complete Corp schema now in FINDINGS.md
   - All 11 fields documented
   - Data completeness statistics recorded
   - Market codes explained

4. **Production Implementation**: Phase 1 complete
   - FilingSearchService uses corp_list.find_by_stock_code() directly
   - No wrapper needed - dart-fss is efficient enough
   - Type-safe with SearchFilingsRequest validation

REPLACEMENT:
------------
For CorpList behavior documentation:
→ experiments/exp_08_corplist_test.py (focused testing)

For production use:
→ src/dart_fss_text/services/filing_search.py (FilingSearchService)

See also:
→ experiments/FINDINGS.md for complete schema documentation
→ experiments/exp_08_corplist_test.py for Singleton validation

KEY TAKEAWAYS:
--------------
1. **Trust the Library**: dart-fss already has excellent caching
   - Don't build redundant caching layers
   - Test the library's performance first
   - Only cache if there's a proven performance issue

2. **3.4% of Companies Are Listed**: Most companies in DART are unlisted
   - 3,901 listed vs 110,246 unlisted
   - Our pipeline only needs listed companies
   - corp_list.find_by_stock_code() filters automatically

3. **Corp Code vs Stock Code**:
   - Users think in stock codes (6 digits)
   - DART API uses corp codes (8 digits)
   - find_by_stock_code() handles the conversion
   - No manual mapping needed!

4. **Data Quality Varies**:
   - 70.9% have complete metadata
   - 29.1% missing corp_cls/sector/product
   - Missing data likely indicates delisted/suspended companies
   - Handle missing fields gracefully in production

CORRECT PATTERN FOR PRODUCTION:
--------------------------------
```python
import dart_fss as dart

# One-time setup (Singleton, ~7s first time, instant after)
corp_list = dart.get_corp_list()

# Fast lookups (instant after first load)
corp = corp_list.find_by_stock_code("005930")

# Access all fields
print(f"Corp: {corp.corp_name}")
print(f"Code: {corp.corp_code}")
print(f"Market: {corp.corp_cls}")  # Y=KOSPI, K=KOSDAQ
print(f"Sector: {corp.sector}")

# Search filings
filings = corp.search_filings(
    bgn_de='20240101',
    pblntf_detail_ty='A001'
)
```

No CSV caching needed. dart-fss handles it all!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file kept as lessons learned reference. Do not execute.
Use exp_08_corplist_test.py for focused CorpList testing.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Original code removed - see git history if needed
