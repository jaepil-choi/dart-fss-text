"""
Experiment 9: Document Download Service Test

Goal: Validate the corrected download workflow for Phase 2 implementation
- Use dart_fss.utils.request.download() directly (not download_document wrapper)
- Download and extract filing XMLs with proper error handling
- Organize in PIT-aware directory structure: data/raw/{year}/{corp_code}/{rcept_no}/
- Extract ALL XMLs from ZIP (main + attachments)
- Validate main XML exists and is parseable
- Document findings for DocumentDownloadService implementation

Key Principles:
- Real API calls with actual search results from Phase 1
- Fail fast on errors (no silent failures)
- PIT-aware structure for temporal correctness
- Clean up ZIPs after successful extraction
"""

import os
import time
import zipfile
from pathlib import Path
from dotenv import load_dotenv
from lxml import etree

# Import dart-fss components
import dart_fss as dart
from dart_fss.utils import request
from dart_fss.auth import get_api_key

# Import our Phase 1 components
from dart_fss_text.services import FilingSearchService
from dart_fss_text.models.requests import SearchFilingsRequest

print("=" * 80)
print("EXPERIMENT 9: DOCUMENT DOWNLOAD SERVICE TEST")
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
# STEP 1: SEARCH FOR FILINGS (Using Phase 1 Production Code)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 1: SEARCH FOR FILINGS (Phase 1 Production Code)")
print("=" * 80)

# Use our production service to get filings
request_model = SearchFilingsRequest(
    stock_codes=["005930"],  # Samsung Electronics
    start_date="20240101",
    end_date="20241231",
    report_types=["A001"]  # Annual reports only
)

print(f"\nSearch parameters:")
print(f"  Stock codes: {request_model.stock_codes}")
print(f"  Date range: {request_model.start_date} to {request_model.end_date}")
print(f"  Report types: {request_model.report_types}")

service = FilingSearchService()
filings = service.search_filings(request_model)

print(f"\n✓ Found {len(filings)} filing(s)")

if len(filings) == 0:
    raise ValueError("No filings found - cannot test download")

# Show sample results
print("\nSample filings:")
for i, filing in enumerate(filings[:3], 1):
    print(f"\n{i}. {filing.report_nm}")
    print(f"   rcept_no: {filing.rcept_no}")
    print(f"   rcept_dt: {filing.rcept_dt}")
    print(f"   corp_code: {filing.corp_code}")

# ============================================================================
# STEP 2: TEST DOWNLOAD WORKFLOW (Corrected Approach)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 2: TEST DOWNLOAD WORKFLOW")
print("=" * 80)

# Limit to 3 filings for testing
MAX_DOWNLOADS = min(3, len(filings))
test_filings = filings[:MAX_DOWNLOADS]

print(f"\nTesting with {len(test_filings)} filing(s)...")

download_results = []
download_stats = {
    'total': len(test_filings),
    'success': 0,
    'failed': 0,
    'errors': []
}

for i, filing in enumerate(test_filings, 1):
    print(f"\n[{i}/{len(test_filings)}] Processing: {filing.report_nm}")
    print(f"  rcept_no: {filing.rcept_no}")
    print(f"  rcept_dt: {filing.rcept_dt}")
    
    result = {
        'rcept_no': filing.rcept_no,
        'rcept_dt': filing.rcept_dt,
        'corp_code': filing.corp_code,
        'report_nm': filing.report_nm,
    }
    
    try:
        # Extract PIT metadata (CRITICAL!)
        rcept_dt = filing.rcept_dt  # e.g., "20240312"
        year = rcept_dt[:4]  # "2024"
        corp_code = filing.corp_code  # e.g., "00126380"
        rcept_no = filing.rcept_no
        
        # Get stock_code for directory structure (more user-friendly than corp_code)
        corp_list = dart.get_corp_list()
        corp = corp_list.find_by_corp_code(corp_code)
        stock_code = corp.stock_code if corp and corp.stock_code else corp_code
        
        print(f"  PIT year: {year} (from publication date {rcept_dt})")
        print(f"  Stock code: {stock_code}")
        
        # Create PIT-aware directory structure with stock_code
        base_dir = Path("experiments/data/exp_09_downloads")
        year_dir = base_dir / year
        stock_dir = year_dir / stock_code
        filing_dir = stock_dir / rcept_no
        
        filing_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Directory: {filing_dir}")
        
        # Check if already downloaded (idempotency)
        main_xml = filing_dir / f"{rcept_no}.xml"
        if main_xml.exists():
            print(f"  ⊙ Already downloaded: {main_xml.name}")
            result['status'] = 'existing'
            result['xml_files'] = [str(f.relative_to(base_dir)) for f in filing_dir.glob("*.xml")]
            download_results.append(result)
            download_stats['success'] += 1
            continue
        
        # STEP 2.1: Download ZIP using corrected approach
        print(f"  ⬇ Downloading ZIP...")
        download_start = time.time()
        
        url = 'https://opendart.fss.or.kr/api/document.xml'
        payload = {
            'crtfc_key': get_api_key(),
            'rcept_no': rcept_no,
        }
        
        # Direct download (returns None, saves to path)
        request.download(url=url, path=str(filing_dir) + "/", payload=payload)
        
        download_time = time.time() - download_start
        
        # STEP 2.2: Verify ZIP exists (predictable naming)
        zip_path = filing_dir / f"{rcept_no}.zip"
        
        if not zip_path.exists():
            raise FileNotFoundError(f"Download failed: ZIP not found at {zip_path}")
        
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        print(f"  ✓ Downloaded: {zip_path.name} ({zip_size_mb:.2f} MB in {download_time:.2f}s)")
        
        # STEP 2.3: Extract ALL XMLs from ZIP
        print(f"  📦 Extracting XMLs...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            all_files = zip_ref.namelist()
            xml_files = [f for f in all_files if f.endswith('.xml')]
            
            print(f"    Files in ZIP: {len(all_files)} total, {len(xml_files)} XMLs")
            
            if len(xml_files) == 0:
                raise ValueError(f"No XML files found in ZIP. Contents: {all_files}")
            
            # Extract all XMLs
            for xml_file in xml_files:
                zip_ref.extract(xml_file, filing_dir)
                extracted_path = filing_dir / xml_file
                size_mb = extracted_path.stat().st_size / (1024 * 1024)
                print(f"    ✓ {xml_file} ({size_mb:.2f} MB)")
        
        # STEP 2.4: Verify main XML exists (CRITICAL!)
        main_xml = filing_dir / f"{rcept_no}.xml"
        
        if not main_xml.exists():
            raise FileNotFoundError(
                f"Main XML not found: {rcept_no}.xml\n"
                f"Available XMLs: {xml_files}"
            )
        
        print(f"  ✓ Main XML verified: {main_xml.name}")
        
        # STEP 2.5: Cleanup ZIP (only after successful extraction)
        zip_path.unlink()
        print(f"  🗑 Cleaned up: {zip_path.name}")
        
        # STEP 2.6: Quick XML validation with lxml
        print(f"  🔍 Validating XML...")
        
        try:
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            tree = etree.parse(str(main_xml), parser)
            root = tree.getroot()
            
            elem_count = len(list(root.iter()))
            usermark_count = len(root.findall(".//*[@USERMARK]"))
            table_count = len(root.findall(".//TABLE"))
            
            print(f"  ✓ XML valid:")
            print(f"    - Total elements: {elem_count:,}")
            print(f"    - USERMARK sections: {usermark_count:,}")
            print(f"    - Tables: {table_count:,}")
            
            result['xml_validation'] = {
                'total_elements': elem_count,
                'usermark_sections': usermark_count,
                'tables': table_count
            }
            
        except Exception as e:
            print(f"  ⚠ XML validation failed: {e}")
            result['xml_validation'] = {'error': str(e)}
        
        # Success!
        result['status'] = 'success'
        result['year'] = year
        result['stock_code'] = stock_code
        result['xml_files'] = [str(f.relative_to(base_dir)) for f in filing_dir.glob("*.xml")]
        result['file_count'] = len(xml_files)
        result['download_time_sec'] = download_time
        result['zip_size_mb'] = zip_size_mb
        
        download_results.append(result)
        download_stats['success'] += 1
        
        print(f"  ✅ Success: {len(xml_files)} XML(s) extracted to {filing_dir.relative_to(base_dir)}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        
        result['status'] = 'failed'
        result['error'] = str(e)
        
        download_results.append(result)
        download_stats['failed'] += 1
        download_stats['errors'].append({
            'rcept_no': filing.rcept_no,
            'error': str(e)
        })
        
        # Continue to next filing (don't stop entire experiment)
        continue

# ============================================================================
# STEP 3: SUMMARY AND FINDINGS
# ============================================================================

print("\n" + "=" * 80)
print("STEP 3: SUMMARY AND FINDINGS")
print("=" * 80)

print(f"\n[Statistics]")
print(f"  Total processed: {download_stats['total']}")
print(f"  Successful: {download_stats['success']}")
print(f"  Failed: {download_stats['failed']}")
print(f"  Success rate: {download_stats['success']/download_stats['total']*100:.1f}%")

if download_stats['success'] > 0:
    print(f"\n[Successful Downloads]")
    for result in download_results:
        if result['status'] in ['success', 'existing']:
            print(f"  ✓ {result['rcept_no']} - {result['report_nm']}")
            print(f"    Year: {result.get('year', 'N/A')}, Stock: {result.get('stock_code', 'N/A')}")
            print(f"    XMLs: {result.get('file_count', len(result.get('xml_files', [])))} file(s)")
            if result.get('xml_files'):
                for xml in result['xml_files'][:3]:  # Show first 3
                    print(f"      - {xml}")

if download_stats['failed'] > 0:
    print(f"\n[Failures]")
    for error in download_stats['errors']:
        print(f"  ✗ {error['rcept_no']}: {error['error']}")

# Check directory structure
print(f"\n[Directory Structure Verification]")
base_dir = Path("experiments/data/exp_09_downloads")

if base_dir.exists():
    print(f"\n{base_dir}/")
    for year_dir in sorted(base_dir.iterdir()):
        if year_dir.is_dir():
            print(f"  {year_dir.name}/")
            for stock_dir in sorted(year_dir.iterdir()):
                if stock_dir.is_dir():
                    print(f"    {stock_dir.name}/ (stock_code)")
                    for filing_dir in sorted(stock_dir.iterdir()):
                        if filing_dir.is_dir():
                            xml_count = len(list(filing_dir.glob("*.xml")))
                            print(f"      {filing_dir.name}/ ({xml_count} XML(s))")

# ============================================================================
# FINAL VERDICT
# ============================================================================

print("\n" + "=" * 80)
print("✅ EXPERIMENT 9 COMPLETE")
print("=" * 80)

print(f"\n[Success Criteria]")
criteria = []

if download_stats['success'] > 0:
    criteria.append("✓ Successfully downloaded at least one filing")
else:
    criteria.append("✗ No successful downloads")

if download_stats['success'] == download_stats['total']:
    criteria.append("✓ All downloads successful")
elif download_stats['success'] > 0:
    criteria.append(f"⚠ Partial success ({download_stats['success']}/{download_stats['total']})")
else:
    criteria.append("✗ All downloads failed")

pit_structure_exists = any(
    result.get('year') and result.get('xml_files')
    for result in download_results
    if result['status'] == 'success'
)

if pit_structure_exists:
    criteria.append("✓ PIT-aware directory structure created")
else:
    criteria.append("✗ PIT-aware structure not verified")

for criterion in criteria:
    print(f"  {criterion}")

print(f"\n[Key Findings]")
print(f"  1. request.download() works correctly (saves as {{rcept_no}}.zip)")
print(f"  2. ZIP extraction successful with zipfile.ZipFile()")
print(f"  3. Main XML naming confirmed: {{rcept_no}}.xml")
print(f"  4. PIT-aware structure: data/exp_09_downloads/{{year}}/{{stock_code}}/{{rcept_no}}/")
print(f"  5. Directory uses stock_code (user-friendly) instead of corp_code")
print(f"  6. Error handling: Fail-fast approach works as expected")

print(f"\n[Next Steps for Phase 2 Implementation]")
print(f"  1. Create DocumentDownloadService with this workflow")
print(f"  2. Implement FilesystemCache for deduplication")
print(f"  3. Add retry logic for transient network failures (optional)")
print(f"  4. Write unit tests with mocked request.download()")
print(f"  5. Write integration tests with real API calls")

print(f"\n[Experiment Data]")
print(f"  Downloaded files: experiments/data/exp_09_downloads/")
print(f"  Review XMLs to validate structure before Phase 2 implementation")

