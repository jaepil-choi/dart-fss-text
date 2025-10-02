"""
Experiment 2C: Correct Filing Search API

Goal: Fix the search API issue - test CORRECT dart-fss search methods
Previous experiments used Corp.search_filings() which didn't work properly.
Now testing the module-level search functions with proper parameters.

PRINCIPLE: Never fake results - investigate and fix the root cause!
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import dart_fss as dart

print("=" * 80)
print("EXPERIMENT 2C: CORRECT FILING SEARCH API")
print("=" * 80)

# Setup
print("\n[Setup] Loading environment configuration...")
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)
print(f"✓ API Key configured: {api_key[:10]}***")

# Get Samsung's corp_code
print("\n[Step 1] Getting Samsung Electronics corp_code...")
corp_list = dart.get_corp_list()
samsung = corp_list.find_by_stock_code("005930")
corp_code = samsung.corp_code
print(f"✓ Samsung Electronics corp_code: {corp_code}")

# Test different search methods
print("\n" + "=" * 80)
print("TESTING DIFFERENT SEARCH METHODS")
print("=" * 80)

# Method 1: Module-level search_filings with pblntf_detail_ty
print("\n[Method 1] Module-level search_filings() with pblntf_detail_ty='A001'")
print("=" * 60)
try:
    from dart_fss.api.filings import search_filings
    
    print("Searching for annual reports (사업보고서)...")
    method1_results = search_filings(
        corp_code=corp_code,
        bgn_de='20230101',
        end_de='20241231',
        pblntf_detail_ty='A001',  # Annual reports
        page_count=100
    )
    
    print(f"✓ Found {len(method1_results)} annual report(s)")
    
    if len(method1_results) > 0:
        print("\nFirst 3 results:")
        # Convert to list if it's a generator/iterator
        if not isinstance(method1_results, list):
            method1_results = list(method1_results)
        
        for i, report in enumerate(method1_results[:3], 1):
            print(f"\n{i}. {report.report_nm}")
            print(f"   rcept_no: {report.rcept_no}")
            print(f"   rcept_dt: {report.rcept_dt}")
    else:
        print("❌ SANITY CHECK FAILED: Samsung should have annual reports!")
        
except Exception as e:
    print(f"✗ Method 1 failed: {e}")
    import traceback
    traceback.print_exc()
    method1_results = []

# Method 2: search_annual_report helper
print("\n[Method 2] search_annual_report() helper function")
print("=" * 60)
try:
    from dart_fss.fs.extract import search_annual_report
    
    print("Searching for annual reports using helper...")
    method2_results = search_annual_report(
        corp_code=corp_code,
        bgn_de='20230101',
        end_de='20241231',
        separate=False
    )
    
    print(f"✓ Found {len(method2_results)} annual report(s)")
    
    if len(method2_results) > 0:
        print("\nFirst 3 results:")
        for i, report in enumerate(method2_results[:3], 1):
            print(f"\n{i}. {report.report_nm}")
            print(f"   rcept_no: {report.rcept_no}")
            print(f"   rcept_dt: {report.rcept_dt}")
    else:
        print("❌ SANITY CHECK FAILED: Samsung should have annual reports!")
        
except Exception as e:
    print(f"✗ Method 2 failed: {e}")
    method2_results = []

# Method 3: Corp.search_filings with pblntf_detail_ty (what we tried before)
print("\n[Method 3] Corp.search_filings() with pblntf_detail_ty")
print("=" * 60)
try:
    print("Searching using Corp object method...")
    method3_results = samsung.search_filings(
        bgn_de='20230101',
        pblntf_detail_ty='A001'
    )
    
    print(f"✓ Found {len(method3_results)} annual report(s)")
    
    if len(method3_results) > 0:
        print("\nFirst 3 results:")
        for i, report in enumerate(method3_results[:3], 1):
            print(f"\n{i}. {report.report_nm}")
            print(f"   rcept_no: {report.rcept_no}")
            print(f"   rcept_dt: {report.rcept_dt}")
    else:
        print("⚠ Warning: This method returned no results")
        
except Exception as e:
    print(f"✗ Method 3 failed: {e}")
    method3_results = []

# Summary and comparison
print("\n" + "=" * 80)
print("SUMMARY: Which Method Works Best?")
print("=" * 80)

summary = {
    "Method 1 (search_filings with pblntf_detail_ty)": len(method1_results),
    "Method 2 (search_annual_report helper)": len(method2_results),
    "Method 3 (Corp.search_filings)": len(method3_results),
}

for method, count in summary.items():
    status = "✓ WORKS" if count > 0 else "✗ FAILED"
    print(f"{status}: {method} - {count} results")

# Detailed comparison if we have results
if len(method1_results) > 0 or len(method2_results) > 0:
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS")
    print("=" * 80)
    
    working_method = "Method 1" if len(method1_results) > 0 else "Method 2"
    working_results = method1_results if len(method1_results) > 0 else method2_results
    
    print(f"\n{working_method} returned {len(working_results)} reports")
    print("\nAll results:")
    
    for i, report in enumerate(working_results, 1):
        print(f"\n{i}. {report.report_nm}")
        print(f"   Date: {report.rcept_dt}")
        print(f"   rcept_no: {report.rcept_no}")
    
    # Save results
    output = []
    for report in working_results:
        output.append({
            'rcept_no': report.rcept_no,
            'report_nm': report.report_nm,
            'rcept_dt': report.rcept_dt,
            'corp_code': report.corp_code,
            'corp_name': report.corp_name if hasattr(report, 'corp_name') else 'N/A'
        })
    
    output_file = Path("./experiments/data/correct_search_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved results to {output_file}")

print("\n" + "=" * 80)
print("✅ EXPERIMENT 2C COMPLETE")
print("=" * 80)

# Final verdict
if len(method1_results) == 0 and len(method2_results) == 0:
    print("\n❌ CRITICAL: All search methods failed!")
    print("   This requires further investigation of dart-fss API")
    print("   Check dart-fss version, API key permissions, etc.")
else:
    recommended = "search_filings()" if len(method1_results) > 0 else "search_annual_report()"
    print(f"\n✓ RECOMMENDED: Use {recommended} for searching annual reports")
    print("  This method successfully returned Samsung annual reports")

