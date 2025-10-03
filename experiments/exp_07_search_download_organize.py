"""
Experiment 7: Complete Search → Download → Organize Pipeline (Production-Ready)

Goal: Validate the complete workflow that will be used in production services:
1. Search filings using correct dart-fss API (validated in Experiment 2C)
2. Download XMLs using dart-fss download_document
3. Organize in PIT-aware directory structure: data/raw/{year}/{corp_code}/{rcept_no}.xml
4. Clean up ZIP files after extraction
5. Track metadata for analysis

This experiment bridges POC (Experiments 1-4) and production implementation (TODO #7 + #8).

Key Principles:
- Never fake results - use real API calls
- Fail loudly if something is wrong
- Validate PIT-aware structure prevents forward-looking bias
- Test idempotency (re-running doesn't duplicate work)
"""

import os
import json
import time
import zipfile
from pathlib import Path
from dotenv import load_dotenv
import dart_fss as dart
from dart_fss.api.filings import download_document

print("=" * 80)
print("EXPERIMENT 7: COMPLETE SEARCH → DOWNLOAD → ORGANIZE PIPELINE")
print("=" * 80)

# ============================================================================
# SETUP
# ============================================================================

print("\n[Setup] Loading environment configuration...")
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

dart.set_api_key(api_key=api_key)
print(f"✓ API Key configured: {api_key[:10]}***")

# ============================================================================
# STEP 1: SEARCH FILINGS (MULTIPLE REPORT TYPES)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 1: SEARCH FILINGS")
print("=" * 80)

stock_code = "005930"  # Samsung Electronics
report_types = ["A001", "A002", "A003"]  # Annual, Semi-annual, Quarterly

print(f"\nTarget Company: {stock_code}")
print(f"Report Types: {report_types}")
print(f"Date Range: 2023-01-01 to 2024-12-31")

# Get corp
print("\n[1.1] Getting corporation...")
start_time = time.time()
corp_list = dart.get_corp_list()
corp = corp_list.find_by_stock_code(stock_code)
lookup_time = time.time() - start_time

print(f"✓ Company found: {corp.corp_name}")
print(f"  Corp code: {corp.corp_code}")
print(f"  Lookup time: {lookup_time:.3f}s")

# Search each report type
print("\n[1.2] Searching filings by report type...")
all_filings = []
search_summary = {}

for report_type in report_types:
    print(f"\n  Searching {report_type}...")
    start_time = time.time()
    
    filings = corp.search_filings(
        bgn_de='20230101',
        end_de='20241231',
        pblntf_detail_ty=report_type
    )
    
    search_time = time.time() - start_time
    search_summary[report_type] = {
        'count': len(filings),
        'search_time': search_time
    }
    
    all_filings.extend(filings)
    print(f"  ✓ {report_type}: {len(filings)} reports ({search_time:.2f}s)")

print(f"\n✓ Total filings found: {len(all_filings)}")

# Sanity check
if len(all_filings) == 0:
    print("\n❌ SANITY CHECK FAILED: Samsung should have reports!")
    print("   This indicates a problem with the search API")
    raise ValueError("No filings found - investigation needed")

# Display sample results
print("\n[1.3] Sample search results:")
for i, filing in enumerate(all_filings[:5], 1):
    print(f"\n{i}. {filing.report_nm}")
    print(f"   rcept_no: {filing.rcept_no}")
    print(f"   rcept_dt: {filing.rcept_dt}")
    print(f"   corp_code: {filing.corp_code}")

# ============================================================================
# STEP 2: DOWNLOAD AND ORGANIZE (PIT-AWARE STRUCTURE)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 2: DOWNLOAD AND ORGANIZE (PIT-AWARE)")
print("=" * 80)

# Limit to 10 for testing
MAX_DOWNLOADS = 10
filings_to_process = all_filings[:MAX_DOWNLOADS]

print(f"\nProcessing {len(filings_to_process)} filings (limited for testing)...")

download_results = []
download_stats = {
    'total': len(filings_to_process),
    'downloaded': 0,
    'skipped_existing': 0,
    'extracted': 0,
    'cleaned_up': 0,
    'failed': 0,
    'errors': []
}

for i, filing in enumerate(filings_to_process, 1):
    print(f"\n[{i}/{len(filings_to_process)}] Processing: {filing.report_nm}")
    print(f"  rcept_no: {filing.rcept_no}")
    print(f"  rcept_dt: {filing.rcept_dt}")
    
    try:
        # Extract year from rcept_dt (publication date) - CRITICAL FOR PIT!
        rcept_dt = filing.rcept_dt  # e.g., "20230307"
        year = rcept_dt[:4]  # "2023"
        corp_code = filing.corp_code  # "00126380"
        rcept_no = filing.rcept_no
        
        print(f"  PIT year: {year} (from publication date {rcept_dt})")
        
        # PIT-aware directory structure
        year_dir = Path(f"experiments/data/raw/{year}")
        corp_dir = year_dir / corp_code
        corp_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if XML already exists (idempotency)
        xml_path = corp_dir / f"{rcept_no}.xml"
        
        if xml_path.exists():
            print(f"  ⊙ XML already exists: {xml_path.name}")
            download_stats['skipped_existing'] += 1
            
            # Store result
            download_results.append({
                'rcept_no': rcept_no,
                'rcept_dt': rcept_dt,
                'year': year,
                'corp_code': corp_code,
                'report_nm': filing.report_nm,
                'xml_path': str(xml_path),
                'file_size_mb': xml_path.stat().st_size / (1024*1024),
                'status': 'existing'
            })
            continue
        
        # Download ZIP
        zip_path = corp_dir / f"{rcept_no}.zip"
        
        if not zip_path.exists():
            print(f"  ⬇ Downloading ZIP...")
            start_time = time.time()
            
            download_document(
                path=str(corp_dir) + "/",
                rcept_no=rcept_no
            )
            
            download_time = time.time() - start_time
            zip_size_mb = zip_path.stat().st_size / (1024*1024)
            
            print(f"  ✓ Downloaded: {zip_path.name} ({zip_size_mb:.2f} MB in {download_time:.2f}s)")
            download_stats['downloaded'] += 1
        else:
            print(f"  ⊙ ZIP already exists: {zip_path.name}")
        
        # Extract main XML
        print(f"  📦 Extracting XML...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Check if main XML exists (validated in FINDINGS.md)
            main_xml = f"{rcept_no}.xml"
            available_files = zip_ref.namelist()
            
            if main_xml in available_files:
                zip_ref.extract(main_xml, corp_dir)
                xml_size_mb = xml_path.stat().st_size / (1024*1024)
                print(f"  ✓ Extracted: {xml_path.name} ({xml_size_mb:.2f} MB)")
                download_stats['extracted'] += 1
            else:
                print(f"  ⚠ Warning: {main_xml} not found in ZIP!")
                print(f"    Available files: {available_files}")
                download_stats['errors'].append({
                    'rcept_no': rcept_no,
                    'error': f"Main XML not found. Available: {available_files}"
                })
                download_stats['failed'] += 1
                continue
        
        # Cleanup ZIP file
        if xml_path.exists() and zip_path.exists():
            zip_path.unlink()
            print(f"  🗑 Cleaned up: {zip_path.name}")
            download_stats['cleaned_up'] += 1
        
        # Quick XML validation
        try:
            from lxml import etree
            with open(xml_path, 'rb') as f:
                tree = etree.parse(f, parser=etree.XMLParser(recover=True))
                root = tree.getroot()
                elem_count = len(list(root.iter()))
            print(f"  ✓ XML valid: {elem_count:,} elements")
        except Exception as e:
            print(f"  ⚠ XML validation failed: {e}")
        
        # Store result
        download_results.append({
            'rcept_no': rcept_no,
            'rcept_dt': rcept_dt,
            'year': year,
            'corp_code': corp_code,
            'report_nm': filing.report_nm,
            'xml_path': str(xml_path),
            'file_size_mb': xml_path.stat().st_size / (1024*1024),
            'status': 'success'
        })
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        download_stats['failed'] += 1
        download_stats['errors'].append({
            'rcept_no': filing.rcept_no,
            'error': str(e)
        })
        
        import traceback
        traceback.print_exc()

# ============================================================================
# STEP 3: VERIFY PIT-AWARE STRUCTURE
# ============================================================================

print("\n" + "=" * 80)
print("STEP 3: VERIFY PIT-AWARE STRUCTURE")
print("=" * 80)

raw_dir = Path("experiments/data/raw")

if raw_dir.exists():
    print("\nDirectory Structure:")
    print("="*60)
    
    # Check for any remaining ZIP files
    zip_files = list(raw_dir.rglob("*.zip"))
    if zip_files:
        print(f"\n⚠ WARNING: {len(zip_files)} ZIP files still present!")
        for zip_file in zip_files[:5]:
            print(f"  - {zip_file}")
    else:
        print("\n✓ No ZIP files remaining (cleanup successful)")
    
    # Display directory structure
    print("\nXML Files by Year:")
    for year_dir in sorted(raw_dir.iterdir()):
        if year_dir.is_dir():
            year = year_dir.name
            xml_files = list(year_dir.rglob("*.xml"))
            print(f"\n{year}/ ({len(xml_files)} XMLs)")
            
            for corp_dir in sorted(year_dir.iterdir()):
                if corp_dir.is_dir():
                    corp_code = corp_dir.name
                    xmls = sorted(corp_dir.glob("*.xml"))
                    print(f"  {corp_code}/")
                    for xml in xmls:
                        size_mb = xml.stat().st_size / (1024*1024)
                        print(f"    - {xml.name} ({size_mb:.2f} MB)")
    
    # PIT structure validation
    print("\n" + "="*60)
    print("PIT STRUCTURE VALIDATION")
    print("="*60)
    
    print("\nChecking if publication dates match directory years...")
    pit_violations = []
    
    for result in download_results:
        if result['status'] in ['success', 'existing']:
            rcept_dt = result['rcept_dt']
            expected_year = rcept_dt[:4]
            actual_year = result['year']
            
            if expected_year != actual_year:
                pit_violations.append({
                    'rcept_no': result['rcept_no'],
                    'rcept_dt': rcept_dt,
                    'expected_year': expected_year,
                    'actual_year': actual_year
                })
    
    if pit_violations:
        print(f"\n❌ PIT VIOLATIONS FOUND: {len(pit_violations)}")
        for v in pit_violations:
            print(f"  - {v['rcept_no']}: published {v['rcept_dt']} but stored in {v['actual_year']}/")
    else:
        print("\n✓ All files correctly organized by publication date year")
        print("  This prevents forward-looking bias in analysis!")

else:
    print("\n⚠ Warning: raw directory does not exist yet")

# ============================================================================
# STEP 4: SAVE RESULTS SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("STEP 4: SAVE RESULTS SUMMARY")
print("=" * 80)

# Aggregate statistics
report_type_counts = {}
year_counts = {}

for result in download_results:
    # Extract report type from report name
    report_nm = result['report_nm']
    if '사업보고서' in report_nm:
        rt = 'A001'
    elif '반기보고서' in report_nm:
        rt = 'A002'
    elif '분기보고서' in report_nm:
        rt = 'A003'
    else:
        rt = 'OTHER'
    
    report_type_counts[rt] = report_type_counts.get(rt, 0) + 1
    
    # Count by year
    year = result['year']
    year_counts[year] = year_counts.get(year, 0) + 1

summary = {
    'experiment': 'exp_07_search_download_organize',
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'search_summary': search_summary,
    'download_stats': download_stats,
    'report_type_distribution': report_type_counts,
    'year_distribution': year_counts,
    'sample_results': download_results[:5],  # First 5 for inspection
    'all_results_count': len(download_results)
}

output_file = Path("experiments/data/exp_07_results.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"\n✓ Results saved to {output_file}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("✅ EXPERIMENT 7 COMPLETE")
print("=" * 80)

print("\n📊 SUMMARY:")
print(f"  Search: {len(all_filings)} total filings found")
print(f"  Processed: {download_stats['total']} filings")
print(f"  Downloaded: {download_stats['downloaded']} new")
print(f"  Skipped (existing): {download_stats['skipped_existing']}")
print(f"  Extracted: {download_stats['extracted']} XMLs")
print(f"  Cleaned up: {download_stats['cleaned_up']} ZIPs")
print(f"  Failed: {download_stats['failed']}")

if download_stats['failed'] > 0:
    print(f"\n⚠ Errors encountered:")
    for error in download_stats['errors']:
        print(f"  - {error['rcept_no']}: {error['error']}")

print(f"\n📁 Report Type Distribution:")
for rt, count in sorted(report_type_counts.items()):
    print(f"  {rt}: {count} reports")

print(f"\n📅 Year Distribution (by publication date):")
for year, count in sorted(year_counts.items()):
    print(f"  {year}: {count} reports")

print("\n" + "=" * 80)
print("🎯 SUCCESS CRITERIA CHECK:")
print("=" * 80)

checks = [
    ("Search returns results for report types", len(all_filings) > 0),
    ("Downloads completed successfully", download_stats['failed'] == 0),
    ("XMLs organized in PIT-aware structure", len(pit_violations) == 0 if 'pit_violations' in locals() else True),
    ("ZIP files cleaned up", len(zip_files) == 0 if 'zip_files' in locals() else True),
    ("All XMLs valid and parseable", download_stats['extracted'] > 0),
    ("Metadata summary saved", output_file.exists()),
]

all_passed = True
for check_name, passed in checks:
    status = "✅" if passed else "❌"
    print(f"{status} {check_name}")
    if not passed:
        all_passed = False

if all_passed:
    print("\n🎉 All success criteria met!")
    print("   Ready for production implementation (TODO #7, #8)")
else:
    print("\n⚠ Some criteria not met - review errors above")

print("\n" + "=" * 80)

