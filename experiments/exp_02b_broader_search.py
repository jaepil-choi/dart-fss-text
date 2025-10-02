"""
Experiment 2B: Broader Filing Search

Goal: Find annual reports without tight date restrictions
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import dart_fss as dart

print("=" * 80)
print("EXPERIMENT 2B: BROADER FILING SEARCH")
print("=" * 80)

# Setup
print("\n[Setup] Loading environment configuration...")
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)
print(f"✓ API Key configured: {api_key[:10]}***")

# Get company
print("\n[Step 1] Getting Samsung Electronics...")
corp_list = dart.get_corp_list()
corp = corp_list.find_by_stock_code("005930")
print(f"✓ Company: {corp.corp_name} ({corp.corp_code})")

# Try search without date restrictions
print("\n[Step 2] Searching all filings (no date filter)...")
try:
    all_filings = corp.search_filings()
    print(f"✓ Found {len(all_filings)} total filings")
    
    # Display first 10
    print("\nFirst 10 filings:")
    for i, filing in enumerate(all_filings[:10], 1):
        print(f"{i}. {filing.report_nm} - {filing.rcept_dt}")
    
except Exception as e:
    print(f"✗ Search failed: {e}")

# Filter for annual/semi-annual
print("\n[Step 3] Filtering for annual and semi-annual reports...")
annual_reports = []
for filing in all_filings:
    if '사업보고서' in filing.report_nm or '반기보고서' in filing.report_nm:
        annual_reports.append(filing)

print(f"✓ Found {len(annual_reports)} annual/semi-annual reports")

# Display first 5 annual reports
print("\nFirst 5 annual/semi-annual reports:")
for i, filing in enumerate(annual_reports[:5], 1):
    print(f"{i}. {filing.report_nm}")
    print(f"   Date: {filing.rcept_dt}")
    print(f"   rcept_no: {filing.rcept_no}")

# Save for use in Experiment 3
if annual_reports:
    output = []
    for filing in annual_reports[:5]:
        output.append({
            'rcept_no': filing.rcept_no,
            'report_nm': filing.report_nm,
            'rcept_dt': filing.rcept_dt,
            'corp_code': filing.corp_code,
            'corp_name': filing.corp_name
        })
    
    output_file = Path("./experiments/data/annual_reports_found.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Saved {len(output)} reports to {output_file}")

print("\n" + "=" * 80)
print("✅ EXPERIMENT 2B COMPLETE")
print("=" * 80)
print(f"\nSummary:")
print(f"  - Total filings: {len(all_filings)}")
print(f"  - Annual/semi-annual reports: {len(annual_reports)}")

