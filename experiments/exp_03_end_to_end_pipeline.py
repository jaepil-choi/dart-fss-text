"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original Goal: End-to-End Pipeline (Search → Download → Store)
Date Created: 2025-10-02
Status: ❌ INCORRECT - Used wrong search method from exp_02

WHAT THIS EXPERIMENT TRIED TO ACHIEVE:
---------------------------------------
Test the complete discovery and download workflow:
1. Search for filings by stock code and date range
2. Filter by report type (annual, semi-annual)
3. Download ZIP files
4. Extract XML documents
5. Organize in structured directory
6. Save execution results and metadata

This was meant to be the "full pipeline" proof-of-concept.

WHAT WAS WRONG:
---------------
This experiment inherited the bug from exp_02_filing_search.py:

    ❌ WRONG CODE:
    filings = corp.search_filings(
        bgn_de=start_date.replace('-', ''),
        end_de=end_date.replace('-', '')
    )
    # Missing pblntf_detail_ty parameter!

Then the code tried to filter manually AFTER retrieval:
    
    if report_filter:
        filings = [f for f in filings 
                   if any(r in f.report_nm for r in report_filter)]

This is problematic because:
1. If search returns 0 results, filtering 0 results still gives 0
2. Manual filtering by report name is fragile (depends on exact strings)
3. The API has a proper parameter for this—use it!

RESULT:
For Samsung Electronics with date range 2024-01-01 to 2024-12-31:
- Search returned 0 or very few filings
- Pipeline downloaded 0 documents
- Appeared to "work" but produced no useful output

MISTAKE: Building on broken foundation
- Took the broken search code from exp_02
- Added more complexity (download, unzip, store) on top
- Pipeline "worked" but was based on incorrect search logic
- Created false confidence that the full workflow was validated

This is why POC experiments must fail loudly! If the search fails, the 
pipeline should stop immediately, not continue with empty results.

WHAT WE LEARNED:
----------------
1. **Don't build on broken foundations**: Before implementing a complex 
   pipeline, ensure each component works correctly in isolation. If search 
   is broken, fix it FIRST before adding download/storage logic.

2. **Garbage in, garbage out**: A perfectly working download/storage system 
   is useless if the search returns no data. Validate inputs at each stage.

3. **Test components in correct order**: 
   - Phase 1: Search & Discovery (exp_02) ← Fix this FIRST
   - Phase 2: Download & Storage (exp_03) ← Build on working Phase 1
   - Phase 3: Parsing (later)

4. **Pipeline sanity checks**: A pipeline that downloads 0 documents and 
   reports "success" is NOT successful. Add validation:
   
   ```python
   if len(filings) == 0:
       raise ValueError("Search returned no filings - pipeline cannot proceed")
   
   if downloaded_count == 0:
       raise ValueError("Pipeline downloaded 0 documents - something is wrong")
   ```

THE CORRECT APPROACH:
---------------------
✅ CORRECT SEARCH (Step 1 - Fix this first):
    
    corp = corp_list.find_by_stock_code(stock_code)
    
    # Use pblntf_detail_ty parameter for filtering
    filings = corp.search_filings(
        bgn_de='20230101',
        pblntf_detail_ty='A001'  # Filter at API level, not manually!
    )
    
    # Sanity check
    if len(filings) == 0 and stock_code == "005930":
        raise ValueError("Samsung should have annual reports - search is wrong!")

✅ CORRECT PIPELINE (Step 2 - Build on working search):

    # 1. Search with correct method
    filings = corp.search_filings(bgn_de=start_date, pblntf_detail_ty=report_type)
    
    # 2. Validate search results
    if len(filings) == 0:
        raise ValueError(f"No {report_type} filings found for {stock_code}")
    
    print(f"Found {len(filings)} filings to download")
    
    # 3. Download only if we have valid data
    for filing in filings[:max_downloads]:
        # Download, unzip, validate...
        pass
    
    # 4. Final validation
    if downloaded_count == 0:
        raise ValueError("Pipeline failed to download any documents")

HOW WE IMPROVED:
----------------
1. Fixed search in exp_02c_correct_search_api.py FIRST
2. Documented proper component testing order
3. Added sanity checks at each pipeline stage
4. Made pipeline fail loudly when inputs are invalid

REPLACEMENT:
------------
To create a correct end-to-end pipeline:

Step 1: Use the correct search from exp_02c:
→ experiments/exp_02c_correct_search_api.py

Step 2: Build pipeline on working search (TODO):
→ experiments/exp_03_corrected_pipeline.py (to be created)

See also:
→ experiments/FINDINGS.md for root cause analysis
→ docs/vibe_coding/experiments.md for proper pipeline development methodology

KEY TAKEAWAY:
-------------
**Build pipelines incrementally, validating each stage before adding the next.**

DON'T DO THIS:
❌ Search (broken) → Download (works) → Store (works) = Pipeline "works"

DO THIS:
✅ Search (fix until it works with real data)
✅ THEN add Download (validate it works)
✅ THEN add Store (validate it works)

A pipeline is only as good as its weakest component. If search returns no 
data, the rest of the pipeline is irrelevant.

Always validate that each stage produces sensible results before proceeding 
to the next stage. "Working code" that processes zero items is not working!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file kept as lessons learned reference. Do not execute.
Build corrected pipeline on exp_02c's working search method.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
