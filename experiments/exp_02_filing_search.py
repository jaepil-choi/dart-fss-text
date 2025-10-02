"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original Goal: Filing Search & Metadata Extraction
Date Created: 2025-10-02
Status: ❌ INCORRECT - Replaced by exp_02c_correct_search_api.py

WHAT THIS EXPERIMENT TRIED TO ACHIEVE:
---------------------------------------
1. Search for Samsung Electronics filings by stock code and date range
2. Extract PIT-critical metadata (rcept_no, report_nm, rcept_dt)
3. Filter by report type (annual, semi-annual)
4. Validate the discovery pipeline workflow

WHAT WAS WRONG:
---------------
The search call was missing a critical parameter:

    ❌ WRONG CODE:
    filings = corp.search_filings(
        bgn_de='20240101',
        end_de='20241231'
    )
    # Result: Returned 0 or very few filings

The issue: Did NOT specify pblntf_detail_ty parameter to filter by report type.
Without this parameter, the API either returns all filings (overwhelming) or 
filters in an unexpected way.

RESULT:
- For Samsung Electronics (stock code 005930)
- Date range: 2024-01-01 to 2024-12-31
- Expected: Multiple annual/semi-annual reports
- Actually got: 0 filings

This should have been an immediate red flag! Samsung definitely has annual 
reports in 2024. The fact that we got 0 results should have triggered 
investigation, not workarounds.

MISTAKE: Instead of investigating, I:
1. Created exp_02b to try broader search (without date filters)
2. Still didn't find the root cause
3. Moved on with hardcoded rcept_no values in exp_03b

This violated POC Experiment Principles:
- ❌ Hid the error instead of failing loudly
- ❌ Used workarounds without understanding root cause
- ❌ Created false confidence that the workflow was correct

WHAT WE LEARNED:
----------------
1. **Always use sanity checks**: If Samsung has 0 annual reports, the CODE is 
   wrong, not the data. Should have immediately stopped and investigated.

2. **Read documentation thoroughly**: The dart-fss documentation clearly shows 
   the pblntf_detail_ty parameter exists and is important for filtering.

3. **Never hide errors in POC experiments**: Experiments should FAIL LOUDLY 
   when assumptions are wrong. Silent failures or workarounds create false 
   confidence.

4. **Verify results match reality**: Before proceeding, check if results make 
   sense. Zero filings for a major company = something is wrong.

THE CORRECT APPROACH:
---------------------
✅ CORRECT CODE (from exp_02c_correct_search_api.py):

    from dart_fss.api import filings
    
    # Method 1: Use Corp.search_filings() with pblntf_detail_ty
    corp = corp_list.find_by_stock_code('005930')
    annual_reports = corp.search_filings(
        bgn_de='20230101',
        pblntf_detail_ty='A001'  # ← THIS WAS MISSING!
    )
    # Result: 3 Samsung annual reports (2022, 2023, 2024) ✓
    
    # Method 2: Use search_annual_report() helper
    from dart_fss.fs.extract import search_annual_report
    
    annual_reports = search_annual_report(
        corp_code=corp.corp_code,
        bgn_de='20230101',
        end_de='20241231'
    )
    # Result: 2 Samsung annual reports ✓

Report Type Codes:
- 'A001': 사업보고서 (Annual Report)
- 'A002': 반기보고서 (Semi-Annual Report)  
- 'A003': 분기보고서 (Quarterly Report)

HOW WE IMPROVED:
----------------
1. Created exp_02c_correct_search_api.py that:
   - Tests 3 different search methods systematically
   - Documents which methods work and why
   - Includes sanity checks for result validation
   - Fails loudly when results don't make sense

2. Updated experiments.md with "Experiment Principles (CRITICAL)":
   - Never Fake Results
   - Never Hide Errors
   - Always Investigate Failures
   - Test with Real Data

3. Updated implementation.md with "POC Experiment Rules":
   - Rule 1: Real Data Only
   - Rule 2: No Silent Failures
   - Rule 3: Document Why, Not Just What
   - Rule 4: Verify Results Make Sense

4. Created FINDINGS.md to document the complete investigation and lessons

REPLACEMENT:
------------
This experiment is replaced by:
→ experiments/exp_02c_correct_search_api.py

See also:
→ experiments/FINDINGS.md for complete root cause analysis
→ docs/vibe_coding/experiments.md for updated POC principles
→ docs/vibe_coding/implementation.md for POC experiment rules

KEY TAKEAWAY:
-------------
In POC experiments, getting zero results when you expect many is NOT a "close 
enough" situation. It's a critical failure that requires immediate investigation.

Never move forward with workarounds (hardcoded values) when the underlying 
system behavior doesn't match reality. That's how you build confidence in 
broken systems.

POC experiments are meant to PROVE concepts work with real data. If they don't 
work, that's valuable information—don't hide it!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file kept as lessons learned reference. Do not execute.
Use exp_02c_correct_search_api.py for the correct implementation.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
