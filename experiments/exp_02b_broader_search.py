"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original Goal: Broader Search Without Date Filters
Date Created: 2025-10-02
Status: ❌ DEBUGGING ATTEMPT - Root cause was elsewhere

WHAT THIS EXPERIMENT TRIED TO ACHIEVE:
---------------------------------------
This was a debugging experiment created when exp_02_filing_search.py returned
limited results. The hypothesis was:

"Maybe the date filters (2024-01-01 to 2024-12-31) are too restrictive?"

So this experiment tested searching WITHOUT date filters to see if we could 
get any filings at all.

WHAT WAS WRONG:
---------------
The hypothesis was incorrect. The problem wasn't the date range—it was the 
missing pblntf_detail_ty parameter!

    ❌ WRONG HYPOTHESIS:
    "Date range too narrow → Try without dates"
    
    ✅ ACTUAL ISSUE:
    "Missing pblntf_detail_ty parameter → Add report type filter"

This experiment was a symptom of not investigating the root cause thoroughly 
enough. Instead of reading the dart-fss documentation carefully to understand 
all available parameters, I tried to work around the issue by changing inputs.

RESULT:
Even without date filters, the search still didn't return the expected results
because the REAL problem was the missing report type parameter.

MISTAKE: This was "debugging in the dark"
- Changing inputs without understanding the system
- Trying workarounds instead of reading documentation
- Treating the API as a black box instead of studying its interface

WHAT WE LEARNED:
----------------
1. **Read documentation FIRST, experiment SECOND**: Before trying different 
   input combinations, understand what parameters the API actually accepts.

2. **Hypothesis-driven debugging**: When debugging, explicitly state your 
   hypothesis ("I think X is causing Y because Z"). This helps identify when 
   you're going down the wrong path.

3. **Don't debug in the dark**: If an API isn't working as expected, the first 
   step is to read its documentation thoroughly, not to randomly try different 
   inputs.

4. **One variable at a time**: When debugging, change one variable at a time. 
   This experiment changed date filters, but the actual problem was report type 
   filtering—two separate concerns.

THE CORRECT APPROACH:
---------------------
Instead of this experiment, I should have:

1. ✅ Read dart-fss documentation for search_filings() parameters
2. ✅ Noticed pblntf_detail_ty parameter exists
3. ✅ Tested with that parameter added
4. ✅ Compared results with vs without the parameter

This is exactly what exp_02c_correct_search_api.py does—it systematically 
tests different search methods with proper parameters.

CORRECT CODE (from exp_02c):
    corp = corp_list.find_by_stock_code('005930')
    
    # Test WITH proper parameters
    filings = corp.search_filings(
        bgn_de='20230101',
        pblntf_detail_ty='A001'  # The missing piece!
    )
    # Result: 3 Samsung annual reports ✓

HOW WE IMPROVED:
----------------
1. Created exp_02c that systematically tests ALL search methods from dart-fss
2. Each method is tested with proper parameters based on documentation
3. Results are compared to identify which method works best
4. Sanity checks ensure results match reality

REPLACEMENT:
------------
This debugging experiment is superseded by:
→ experiments/exp_02c_correct_search_api.py

See also:
→ experiments/FINDINGS.md for root cause analysis
→ docs/vibe_coding/experiments.md for proper debugging methodology

KEY TAKEAWAY:
-------------
When an API doesn't work as expected:

1. 📚 Read the documentation thoroughly FIRST
2. 🔍 Understand all available parameters and their effects
3. 🧪 Test systematically with proper parameters
4. ❌ DON'T randomly try input combinations hoping something works

Debugging in the dark wastes time. Understanding the system saves time.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file kept as lessons learned reference. Do not execute.
This represents a common anti-pattern: debugging without understanding.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
