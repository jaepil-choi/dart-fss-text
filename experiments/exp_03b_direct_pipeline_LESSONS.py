"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original: exp_03b_direct_pipeline.py
Date Created: 2025-10-02  
Status: ❌ WORKAROUND - Used hardcoded rcept_no to bypass search failures

WHAT THIS EXPERIMENT TRIED TO ACHIEVE:
---------------------------------------
When exp_03_end_to_end_pipeline.py failed to find filings via search, this 
experiment was created to test the download/extract workflow using a known 
rcept_no directly from exp_01.

WHAT WAS WRONG:
---------------
Used hardcoded rcept_no = "20250814003156" to bypass broken search.

✅ LEGITIMATE: Testing download mechanics with known ID (component test)
❌ ILLEGITIMATE: Using it to bypass search in "pipeline" test

WHERE DO YOU GET rcept_no IN REAL PIPELINE? From search! And search was broken!

THE CORRECT APPROACH:
---------------------
Fix search FIRST (exp_02c), THEN build pipeline on working foundation.

Component test: Hardcoded inputs OK
Integration test: Must use real data flow

See experiments/FINDINGS.md for complete analysis.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Kept as lessons learned. Do not execute. Use exp_02c for correct search.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

