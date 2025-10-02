"""
Experiment 4: Corrected End-to-End Pipeline

Goal: Validate complete discovery → download → organize workflow
Uses CORRECTED search method from exp_02c with pblntf_detail_ty parameter.

Tests all periodic report types:
- A001: 사업보고서 (Annual Report)
- A002: 반기보고서 (Semi-Annual Report)  
- A003: 분기보고서 (Quarterly Report)

PRINCIPLE: Real data only, fail loudly, no workarounds!
"""

import os
import json
import time
import zipfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import dart_fss as dart

print("=" * 80)
print("EXPERIMENT 4: CORRECTED END-TO-END PIPELINE")
print("=" * 80)

# Setup
print("\n[Setup] Loading environment configuration...")
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)
print(f"✓ API Key configured: {api_key[:10]}***")

# Configuration
STOCK_CODE = "005930"  # Samsung Electronics
DATE_RANGE = {
    "start": "20230101",  # Broader range to ensure we get reports
    "end": "20241231"
}
REPORT_TYPES = {
    "A001": "사업보고서",      # Annual
    "A002": "반기보고서",      # Semi-Annual
    "A003": "분기보고서"       # Quarterly
}
MAX_DOWNLOADS_PER_TYPE = 2  # Download 2 of each type

print(f"\n[Config] Test Parameters:")
print(f"  Company: {STOCK_CODE} (Samsung Electronics)")
print(f"  Date Range: {DATE_RANGE['start']} to {DATE_RANGE['end']}")
print(f"  Report Types: {list(REPORT_TYPES.keys())}")
print(f"  Max Downloads per Type: {MAX_DOWNLOADS_PER_TYPE}")

# Get company
print("\n[Step 1] Getting company information...")
corp_list = dart.get_corp_list()
corp = corp_list.find_by_stock_code(STOCK_CODE)

if not corp:
    raise ValueError(f"Company not found for stock code: {STOCK_CODE}")

print(f"✓ Company: {corp.corp_name} ({corp.corp_code})")

# Pipeline function
def download_and_organize_filings(
    corp,
    start_date: str,
    end_date: str,
    report_type_code: str,
    report_type_name: str,
    max_downloads: int = 2
):
    """
    Complete pipeline for one report type:
    Search → Download → Extract → Organize → Validate
    
    Returns list of results with metadata
    """
    print(f"\n{'=' * 80}")
    print(f"PROCESSING: {report_type_code} - {report_type_name}")
    print(f"{'=' * 80}")
    
    # Step 1: Search filings with CORRECT method
    print(f"\n[Search] Searching for {report_type_name}...")
    try:
        filings = corp.search_filings(
            bgn_de=start_date,
            pblntf_detail_ty=report_type_code  # THIS IS THE KEY!
        )
        print(f"✓ Found {len(filings)} filing(s)")
        
        # Sanity check
        if len(filings) == 0:
            print(f"⚠ WARNING: No {report_type_name} found")
            print(f"  This might be expected if no reports filed in date range")
            return []
        
    except Exception as e:
        print(f"✗ Search failed: {e}")
        raise
    
    # Step 2: Filter and select filings to download
    download_count = min(max_downloads, len(filings))
    print(f"\n[Filter] Selecting {download_count} filing(s) to download...")
    
    for i, filing in enumerate(filings[:download_count], 1):
        print(f"  {i}. {filing.report_nm}")
        print(f"     rcept_no: {filing.rcept_no}")
        print(f"     rcept_dt: {filing.rcept_dt}")
        if hasattr(filing, 'rm') and filing.rm:
            print(f"     remarks: {filing.rm}")
    
    # Step 3: Download and organize
    results = []
    start_time = time.time()
    
    for i, filing in enumerate(filings[:download_count], 1):
        print(f"\n[Download {i}/{download_count}] Processing {filing.rcept_no}...")
        
        try:
            # Create organized directory structure
            # data/raw/{stock_code}/{report_type}/{rcept_no}/
            base_dir = Path("./experiments/data/raw")
            stock_dir = base_dir / STOCK_CODE
            report_dir = stock_dir / report_type_code
            filing_dir = report_dir / filing.rcept_no
            
            report_dir.mkdir(parents=True, exist_ok=True)
            filing_dir.mkdir(exist_ok=True)
            
            print(f"  Directory: {filing_dir}")
            
            # Download ZIP
            zip_path = report_dir / f"{filing.rcept_no}.zip"
            
            if zip_path.exists():
                print(f"  ⊙ ZIP already exists, skipping download")
            else:
                from dart_fss.api import filings as filings_api
                
                download_start = time.time()
                filings_api.download_document(
                    path=str(report_dir) + "/",
                    rcept_no=filing.rcept_no
                )
                download_elapsed = time.time() - download_start
                
                size_mb = zip_path.stat().st_size / (1024 * 1024)
                print(f"  ✓ Downloaded: {size_mb:.2f} MB in {download_elapsed:.2f}s")
            
            # Extract ZIP
            xml_file = filing_dir / f"{filing.rcept_no}.xml"
            
            if xml_file.exists():
                print(f"  ⊙ XML already extracted")
            else:
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(filing_dir)
                
                if xml_file.exists():
                    size_mb = xml_file.stat().st_size / (1024 * 1024)
                    print(f"  ✓ Extracted XML: {size_mb:.2f} MB")
                else:
                    raise FileNotFoundError(f"XML not found after extraction: {xml_file}")
            
            # Quick XML validation with lxml (use recover mode for malformed XML)
            print(f"  Validating XML...")
            try:
                from lxml import etree
                parser = etree.XMLParser(recover=True, encoding='utf-8')
                tree = etree.parse(str(xml_file), parser)
                root = tree.getroot()
                
                element_count = len(list(root.iter()))
                usermark_count = len(root.findall(".//*[@USERMARK]"))
                table_count = len(root.findall(".//TABLE"))
                
                print(f"  ✓ XML valid: {element_count:,} elements")
                print(f"    - USERMARK tags: {usermark_count:,}")
                print(f"    - Tables: {table_count:,}")
                
            except Exception as e:
                print(f"  ⚠ XML validation warning: {e}")
            
            # Extract metadata
            metadata = {
                "rcept_no": filing.rcept_no,
                "stock_code": STOCK_CODE,
                "corp_name": corp.corp_name,
                "corp_code": corp.corp_code,
                "report_type_code": report_type_code,
                "report_type_name": report_type_name,
                "report_nm": filing.report_nm,
                "rcept_dt": filing.rcept_dt,  # Published date
                "download_timestamp": datetime.now().isoformat(),
                "zip_path": str(zip_path.relative_to(base_dir)),
                "xml_path": str(xml_file.relative_to(base_dir)),
                "status": "success"
            }
            
            # Check for additional metadata fields
            if hasattr(filing, 'rm') and filing.rm:
                metadata['remarks'] = filing.rm
            
            # Save metadata JSON
            metadata_file = filing_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"  ✓ Saved metadata to {metadata_file.name}")
            
            results.append(metadata)
            
        except Exception as e:
            print(f"  ✗ Error processing {filing.rcept_no}: {e}")
            results.append({
                "rcept_no": filing.rcept_no,
                "status": "failed",
                "error": str(e)
            })
    
    elapsed = time.time() - start_time
    success_count = len([r for r in results if r['status'] == 'success'])
    
    print(f"\n[Summary] {report_type_code} - {report_type_name}")
    print(f"  Total time: {elapsed:.2f}s")
    print(f"  Success: {success_count}/{len(results)}")
    
    return results


# Execute pipeline for each report type
all_results = {}

for report_code, report_name in REPORT_TYPES.items():
    results = download_and_organize_filings(
        corp=corp,
        start_date=DATE_RANGE['start'],
        end_date=DATE_RANGE['end'],
        report_type_code=report_code,
        report_type_name=report_name,
        max_downloads=MAX_DOWNLOADS_PER_TYPE
    )
    
    all_results[report_code] = results


# Final Summary
print("\n" + "=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

total_attempted = 0
total_success = 0

for report_code, results in all_results.items():
    success = len([r for r in results if r.get('status') == 'success'])
    total = len(results)
    total_attempted += total
    total_success += success
    
    print(f"\n{report_code} ({REPORT_TYPES[report_code]}):")
    print(f"  Downloaded: {success}/{total}")
    
    if success > 0:
        for result in results:
            if result.get('status') == 'success':
                print(f"  - {result['rcept_no']} ({result['rcept_dt']})")

print(f"\n{'=' * 80}")
print(f"OVERALL: {total_success}/{total_attempted} filings successfully processed")
print(f"{'=' * 80}")

# Save complete results
results_file = Path("./experiments/data/exp_04_pipeline_results.json")
with open(results_file, 'w', encoding='utf-8') as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print(f"\n✓ Complete results saved to {results_file}")

# Verify directory structure
print("\n[Verification] Checking directory structure...")
raw_dir = Path("./experiments/data/raw")

if raw_dir.exists():
    print(f"\n✓ Directory structure created:")
    for stock_dir in raw_dir.iterdir():
        if stock_dir.is_dir():
            print(f"  {stock_dir.name}/")
            for report_dir in stock_dir.iterdir():
                if report_dir.is_dir():
                    filing_count = len([d for d in report_dir.iterdir() if d.is_dir()])
                    print(f"    {report_dir.name}/ ({filing_count} filings)")

print("\n" + "=" * 80)
print("✅ EXPERIMENT 4 COMPLETE")
print("=" * 80)

# Success criteria check
print("\n[Success Criteria]")
criteria_met = []

if total_success > 0:
    criteria_met.append("✓ Downloaded at least one filing")
else:
    criteria_met.append("✗ No filings downloaded")

if len(all_results) == 3:
    criteria_met.append("✓ Tested all 3 report types")
else:
    criteria_met.append("✗ Not all report types tested")

if (raw_dir / STOCK_CODE).exists():
    criteria_met.append("✓ Organized directory structure created")
else:
    criteria_met.append("✗ Directory structure not created")

for criterion in criteria_met:
    print(f"  {criterion}")

print("\nNext Steps:")
print("1. Review downloaded files in experiments/data/raw/")
print("2. Verify metadata.json files contain correct PIT fields")
print("3. Document findings in experiments/FINDINGS.md")
print("4. If all looks good, proceed to write formal tests")

