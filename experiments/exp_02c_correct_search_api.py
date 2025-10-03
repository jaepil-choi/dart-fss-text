"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original Goal: Fix Filing Search API - Test CORRECT dart-fss Search Methods
Date Created: 2025-10-02
Status: ✅ VALIDATED - Now implemented in Phase 1 (FilingSearchService)

WHAT THIS EXPERIMENT ACHIEVED:
-------------------------------
This was the BREAKTHROUGH experiment that fixed the search issues from exp_02.

Successfully validated THREE different dart-fss search methods:
1. Module-level search_filings() with pblntf_detail_ty
2. search_annual_report() helper function
3. Corp.search_filings() with pblntf_detail_ty

KEY FINDINGS:
-------------
1. **The Missing Parameter**: `pblntf_detail_ty` is CRITICAL!
   
   ❌ WRONG (from exp_02):
   ```python
   filings = corp.search_filings(
       bgn_de='20240101',
       end_de='20241231'
   )
   # Result: 0 or very few filings
   ```
   
   ✅ CORRECT:
   ```python
   filings = corp.search_filings(
       bgn_de='20240101',
       pblntf_detail_ty='A001'  # ← THIS WAS MISSING!
   )
   # Result: Found 3 Samsung annual reports ✓
   ```

2. **Method Comparison Results** (Samsung Electronics, 2023-2024):
   
   | Method | Results | Recommendation |
   |--------|---------|----------------|
   | Module search_filings() | Works but returns strings | Not recommended |
   | search_annual_report() | 2 reports | Works for annual only |
   | Corp.search_filings() | 3 reports | ✅ RECOMMENDED |
   
3. **Report Type Codes** (from types.yaml):
   - 'A001': 사업보고서 (Annual Report)
   - 'A002': 반기보고서 (Semi-Annual Report)
   - 'A003': 분기보고서 (Quarterly Report)

WHAT WE LEARNED:
----------------
1. **RTFM First**: Before trying workarounds, READ THE DOCUMENTATION!
   - dart-fss docs clearly show pblntf_detail_ty parameter
   - Could have saved time by reading docs first instead of experimenting

2. **Sanity Checks Are Critical**: Zero results for Samsung = bug in code
   ```python
   if len(filings) == 0 and stock_code == "005930":
       raise ValueError("Samsung should have annual reports - search is wrong!")
   ```

3. **Filter at API Level**: Use pblntf_detail_ty parameter instead of:
   - Retrieving all filings
   - Manually filtering by report_nm strings
   - Fragile string matching

4. **Systematic Testing**: Test multiple methods to find the best one
   - Don't assume first working method is optimal
   - Compare performance, data structure, completeness

WHY THIS IS NOW OBSOLETE:
--------------------------
This experiment's findings are now implemented in production code:

1. **Production Implementation**: 
   - `FilingSearchService` in `src/dart_fss_text/services/filing_search.py`
   - Uses Corp.search_filings() with pblntf_detail_ty
   - Full type safety with Pydantic models
   - Comprehensive error handling

2. **Full Test Coverage**:
   - 115 unit tests (mocked dart-fss calls)
   - 10 integration tests (real API calls)
   - 3 smoke tests (quick sanity checks)
   - 100% passing, 128 total tests

3. **Type-Safe API**:
   - SearchFilingsRequest validates all inputs
   - Report types validated against types.yaml
   - Helpful error messages guide users

REPLACEMENT:
------------
For production use:
→ src/dart_fss_text/services/filing_search.py (FilingSearchService)

For testing search with real API:
→ tests/integration/test_filing_search_integration.py
→ tests/test_smoke.py (requires --run-live-tests flag)

For Phase 2 pipeline:
→ experiments/exp_07_search_download_organize.py

See also:
→ experiments/FINDINGS.md for complete root cause analysis
→ src/dart_fss_text/models/requests.py for SearchFilingsRequest model
→ config/types.yaml for all valid report type codes

KEY TAKEAWAY:
-------------
**When an API doesn't work as expected, read the documentation FIRST!**

Don't debug in the dark by trying random input combinations. Understand what
parameters the API accepts, what they do, and how they affect results.

This experiment wasted time because we didn't read dart-fss documentation
carefully before experimenting. The fix was right there in the docs all along.

CORRECT PATTERN FOR PRODUCTION:
--------------------------------
```python
from dart_fss_text.services import FilingSearchService
from dart_fss_text.models.requests import SearchFilingsRequest

# Type-safe, validated request
request = SearchFilingsRequest(
    stock_codes=["005930"],
    start_date="20240101",
    end_date="20241231",
    report_types=["A001", "A002"]  # Annual and semi-annual
)

# Search with proper error handling
service = FilingSearchService()
filings = service.search_filings(request)

# filings is a list of Filing objects with full metadata
for filing in filings:
    print(f"{filing.report_nm} - {filing.rcept_dt}")
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file kept as lessons learned reference. Do not execute.
Use FilingSearchService for production code. Use exp_07 for pipeline testing.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Original code removed - see git history if needed
