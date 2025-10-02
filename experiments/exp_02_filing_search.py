"""
Experiment 2: Filing Search & Metadata Extraction

Goal: Validate the discovery pipeline
- Search filings by stock code and date range
- Extract PIT-critical metadata
- Filter by report type
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import dart_fss as dart

print("=" * 80)
print("EXPERIMENT 2: FILING SEARCH & METADATA EXTRACTION")
print("=" * 80)

# Setup
print("\n[Setup] Loading environment configuration...")
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)
print(f"✓ API Key configured: {api_key[:10]}***")

# Step 2.1: Search Filings by Company
print("\n[Step 2.1] Searching filings by company...")
stock_code = "005930"  # Samsung Electronics
start_date = "2024-01-01"
end_date = "2024-12-31"

print(f"Stock code: {stock_code}")
print(f"Date range: {start_date} to {end_date}")

try:
    print("Getting company list...")
    corp_list = dart.get_corp_list()
    print(f"✓ Loaded {len(corp_list.corps)} companies")
    
    print(f"Finding company with stock code: {stock_code}")
    corp = corp_list.find_by_stock_code(stock_code)
    
    if not corp:
        raise ValueError(f"No company found with stock code {stock_code}")
    
    print(f"✓ Company found: {corp.corp_name} ({corp.corp_code})")
except Exception as e:
    print(f"✗ Failed to get company: {e}")
    raise

try:
    print("Searching filings...")
    filings = corp.search_filings(
        bgn_de=start_date.replace('-', ''),
        end_de=end_date.replace('-', ''),
    )
    
    print(f"✓ Found {len(filings)} filing(s)")
    
    # Display first 5 filings
    print("\nFirst 5 filings:")
    for i, filing in enumerate(filings[:5], 1):
        print(f"\n{i}. Filing:")
        print(f"   rcept_no: {filing.rcept_no}")
        print(f"   report_nm: {filing.report_nm}")
        print(f"   flr_nm: {filing.flr_nm}")
        print(f"   rcept_dt: {filing.rcept_dt}")
        
        # Check for more attributes
        for attr in ['corp_code', 'corp_name', 'rm']:
            if hasattr(filing, attr):
                value = getattr(filing, attr)
                if value:
                    print(f"   {attr}: {value}")
    
except Exception as e:
    print(f"✗ Filing search failed: {e}")
    raise

# Step 2.2: Extract Metadata from Filings
print("\n[Step 2.2] Extracting metadata from filings...")
metadata_list = []

print(f"Analyzing first 10 filings for metadata structure...")
for i, filing in enumerate(filings[:10], 1):
    print(f"  Processing filing {i}/10: {filing.rcept_no}")
    
    metadata = {
        "rcept_no": filing.rcept_no,
        "report_nm": filing.report_nm,
        "rcept_dt": filing.rcept_dt,
    }
    
    # Check for additional date fields
    for attr in dir(filing):
        if 'date' in attr.lower() or 'dt' in attr.lower():
            value = getattr(filing, attr, None)
            if value and not callable(value):
                metadata[attr] = str(value)
    
    # Check for report type code
    if hasattr(filing, 'pblntf_ty'):
        metadata['report_type_code'] = filing.pblntf_ty
    
    # Check for amendment flag
    if hasattr(filing, 'rm') and filing.rm:
        metadata['remarks'] = filing.rm
    
    metadata_list.append(metadata)

# Display sample metadata
print("\n✓ Metadata extraction complete")
print("\nSample metadata structure (first filing):")
print(json.dumps(metadata_list[0], indent=2, ensure_ascii=False))

# Save all metadata
output_file = Path("./experiments/data/filing_metadata.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(metadata_list, f, indent=2, ensure_ascii=False)

print(f"\n✓ Metadata saved to {output_file}")

# Step 2.3: Filter by Report Type
print("\n[Step 2.3] Filtering by report type...")

REPORT_TYPES = {
    'A001': '사업보고서',  # Annual
    'A002': '반기보고서',  # Semi-annual
    'A003': '분기보고서',  # Quarterly
}

print(f"Filtering for: {REPORT_TYPES['A001']}, {REPORT_TYPES['A002']}")

filtered_filings = []
for filing in filings:
    if any(report_nm in filing.report_nm for report_nm in [REPORT_TYPES['A001'], REPORT_TYPES['A002']]):
        filtered_filings.append({
            'rcept_no': filing.rcept_no,
            'report_nm': filing.report_nm,
            'rcept_dt': filing.rcept_dt,
        })

print(f"✓ Filtered to {len(filtered_filings)} annual/semi-annual reports")

# Display filtered results
print("\nFiltered results (first 5):")
for i, f in enumerate(filtered_filings[:5], 1):
    print(f"{i}. {f['report_nm']} - {f['rcept_dt']} - {f['rcept_no']}")

# Save filtered list
output_file = Path("./experiments/data/filtered_filings.json")
with open(output_file, 'w', encoding='utf-8') as file:
    json.dump(filtered_filings, file, indent=2, ensure_ascii=False)

print(f"\n✓ Filtered filings saved to {output_file}")

print("\n" + "=" * 80)
print("✅ EXPERIMENT 2 COMPLETE: Filing search and metadata extraction successful!")
print("=" * 80)
print(f"\nSummary:")
print(f"  - Total filings found: {len(filings)}")
print(f"  - Annual/semi-annual reports: {len(filtered_filings)}")
print(f"  - Metadata samples analyzed: {len(metadata_list)}")
print(f"  - Output files created: 2 JSON files")

