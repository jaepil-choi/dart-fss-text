"""
Experiment 12: Investigating Old Report Formats (2018)

Date: 2025-10-05
Status: In Progress

Objective:
- Investigate what format older DART reports use (2018)
- Examine ZIP file contents
- Understand if XML parsing is even possible for old reports
- Determine if we need alternative parsing strategies

Hypothesis:
- Older reports (2018 and earlier) may not use XML format
- They might use HTML, HWP, or other formats
- We may need format-specific parsers

Success Criteria:
- [ ] Download 2018 reports successfully
- [ ] Examine ZIP contents (file types, sizes)
- [ ] Determine primary document format
- [ ] Document findings for alternative parsing strategy

Companies:
- 삼성전자 (Samsung Electronics): 005930
- SK하이닉스 (SK Hynix): 000660

Year: 2018
Report Type: A001 (Annual Reports)
"""

from pathlib import Path
from datetime import datetime
import zipfile
import os

print("=" * 80)
print("EXPERIMENT 12: Old Report Format Investigation (2018)")
print("=" * 80)

# === Step 1: Setup ===

print("\n[Step 1] Importing modules...")
from dart_fss_text.services.filing_search import FilingSearchService
from dart_fss_text.services.document_download import DocumentDownloadService
from dart_fss_text.models.requests import SearchFilingsRequest

print("  ✓ Modules imported")

# === Step 2: Search for 2018 Reports ===

print("\n[Step 2] Searching for 2018 Annual Reports...")

filing_search = FilingSearchService()

request = SearchFilingsRequest(
    stock_codes=["005930", "000660"],  # Samsung, SK Hynix
    start_date="20180101",
    end_date="20181231",
    report_types=["A001"]
)

filings = filing_search.search_filings(request)

print(f"  ✓ Found {len(filings)} reports")
print()
print("  Report Details:")
for filing in filings:
    print(f"    - {filing.corp_name} ({filing.stock_code})")
    print(f"      Report: {filing.report_nm}")
    print(f"      Receipt No: {filing.rcept_no}")
    print(f"      Receipt Date: {filing.rcept_dt}")
print()

# === Step 3: Download Reports (Keep ZIP) ===

print("\n[Step 3] Downloading reports (keeping ZIP files)...")

# Use experiment-specific directory
download_service = DocumentDownloadService(base_dir="experiments/data/exp_12_downloads")

results = []
for i, filing in enumerate(filings, 1):
    print(f"\n  [{i}/{len(filings)}] Downloading {filing.corp_name} ({filing.rcept_no})...")
    
    # Download using the service
    result = download_service.download_filing(
        rcept_no=filing.rcept_no,
        rcept_dt=filing.rcept_dt,
        corp_code=filing.corp_code,
        report_nm=filing.report_nm
    )
    
    results.append(result)
    
    print(f"      Status: {result.status}")
    print(f"      Directory: {result.year}/{result.stock_code}/{result.rcept_no}")
    print(f"      XML files found: {len(result.xml_files)}")
    if result.download_time_sec:
        print(f"      Download time: {result.download_time_sec:.2f}s")
        print(f"      ZIP size: {result.zip_size_mb:.2f} MB")

# === Step 4: Examine ZIP Contents (Re-download to keep ZIP) ===

print("\n" + "=" * 80)
print("STEP 4: EXAMINING ZIP CONTENTS")
print("=" * 80)

for result in results:
    filing_dir = Path(f"experiments/data/exp_12_downloads/{result.year}/{result.stock_code}/{result.rcept_no}")
    
    print(f"\n[{result.stock_code}] {result.rcept_no}")
    print("-" * 40)
    
    # Re-download to get ZIP (since it was deleted)
    if result.status == 'success':
        print("  Note: ZIP was deleted during extraction")
        print("  Re-downloading to examine ZIP contents...")
        
        from dart_fss.auth import get_api_key
        from dart_fss.utils import request as dart_request
        
        url = 'https://opendart.fss.or.kr/api/document.xml'
        payload = {
            'crtfc_key': get_api_key(),
            'rcept_no': result.rcept_no,
        }
        
        dart_request.download(url=url, path=str(filing_dir) + "/", payload=payload)
        
        zip_path = filing_dir / f"{result.rcept_no}.zip"
        
        if zip_path.exists():
            print(f"  ✓ ZIP downloaded: {zip_path}")
            print(f"    Size: {zip_path.stat().st_size / (1024 * 1024):.2f} MB")
            
            # Examine ZIP contents
            print("\n  ZIP Contents:")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Group by file type
                file_types = {}
                for filename in file_list:
                    ext = Path(filename).suffix.lower()
                    if ext not in file_types:
                        file_types[ext] = []
                    file_types[ext].append(filename)
                
                print(f"    Total files: {len(file_list)}")
                print()
                print("    Files by type:")
                for ext, files in sorted(file_types.items()):
                    print(f"      {ext if ext else '(no extension)'}: {len(files)} files")
                    for filename in files[:3]:  # Show first 3
                        file_info = zip_ref.getinfo(filename)
                        size_kb = file_info.file_size / 1024
                        print(f"        - {filename} ({size_kb:.1f} KB)")
                    if len(files) > 3:
                        print(f"        ... and {len(files) - 3} more")
                print()
                
                # Extract ALL files to examine
                print("    Extracting all files for examination...")
                zip_ref.extractall(filing_dir)
                print(f"    ✓ Extracted to {filing_dir}")
    
    # List all extracted files
    print("\n  Extracted Directory Contents:")
    all_files = sorted(filing_dir.rglob("*"))
    
    for file_path in all_files:
        if file_path.is_file():
            rel_path = file_path.relative_to(filing_dir)
            size_kb = file_path.stat().st_size / 1024
            print(f"    - {rel_path} ({size_kb:.1f} KB)")
    
    print()

# === Step 5: Examine XML Structure (if exists) ===

print("\n" + "=" * 80)
print("STEP 5: EXAMINING XML STRUCTURE")
print("=" * 80)

for result in results:
    filing_dir = Path(f"experiments/data/exp_12_downloads/{result.year}/{result.stock_code}/{result.rcept_no}")
    
    print(f"\n[{result.stock_code}] {result.rcept_no}")
    print("-" * 40)
    
    # Find main XML
    main_xml = filing_dir / f"{result.rcept_no}.xml"
    
    if main_xml.exists():
        print(f"  ✓ Main XML found: {main_xml.name}")
        print(f"    Size: {main_xml.stat().st_size / 1024:.1f} KB")
        
        # Try to parse
        try:
            from lxml import etree
            
            # Try both encodings
            tree = None
            encoding_used = None
            
            for encoding in ['utf-8', 'euc-kr']:
                try:
                    parser = etree.XMLParser(recover=True, huge_tree=True, encoding=encoding)
                    tree = etree.parse(str(main_xml), parser)
                    encoding_used = encoding
                    break
                except Exception as e:
                    continue
            
            if tree:
                root = tree.getroot()
                print(f"    Encoding: {encoding_used}")
                print(f"    Root tag: {root.tag}")
                
                # Get structure info
                all_elements = list(root.iter())
                print(f"    Total elements: {len(all_elements)}")
                
                # Find unique tags
                tags = set(elem.tag for elem in all_elements)
                print(f"    Unique tags: {len(tags)}")
                print(f"    Sample tags: {', '.join(sorted(tags)[:10])}")
                
                # Check for SECTION tags
                sections = root.xpath("//SECTION-1 | //SECTION-2")
                print(f"    SECTION-N tags found: {len(sections)}")
                
                # Check for TITLE tags
                titles = root.xpath("//TITLE")
                print(f"    TITLE tags found: {len(titles)}")
                if titles:
                    print("    First 3 titles:")
                    for title in titles[:3]:
                        title_text = ''.join(title.itertext()).strip()
                        atocid = title.get('ATOCID', 'N/A')
                        print(f"      - [{atocid}] {title_text[:50]}...")
                
                # Show XML preview (first 50 lines)
                print("\n    XML Preview (first 50 lines):")
                with open(main_xml, 'r', encoding=encoding_used, errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if i > 50:
                            print("      ... (truncated)")
                            break
                        print(f"      {i:3d}| {line.rstrip()}")
            else:
                print("    ✗ Failed to parse XML with UTF-8 or EUC-KR")
        
        except Exception as e:
            print(f"    ✗ Error parsing XML: {e}")
    else:
        print(f"  ✗ Main XML not found: {main_xml.name}")
    
    print()

# === Step 6: Summary ===

print("\n" + "=" * 80)
print("EXPERIMENT SUMMARY")
print("=" * 80)
print()
print(f"Reports examined: {len(results)}")
print()
print("Key Findings:")
print("- Check the output above to see:")
print("  1. What file types are in 2018 report ZIPs")
print("  2. Whether XML files exist")
print("  3. XML structure (if XML exists)")
print("  4. Presence of SECTION-N and TITLE tags")
print()
print("Next Steps:")
print("- Based on findings, determine if alternative parsing needed")
print("- If no XML, investigate HTML/HWP parsing strategies")
print("- Document format differences across years")
print()
print("=" * 80)

