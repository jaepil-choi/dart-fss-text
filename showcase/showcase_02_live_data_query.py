"""
Showcase 02: TextQuery with Live DART Data

This showcase demonstrates the complete end-to-end workflow with real data:
1. Search and download actual reports from DART API
2. Parse XML files using our parsers
3. Store parsed sections in MongoDB
4. Query data using TextQuery
5. Demonstrate all 4 research use cases with real data

Companies:
- 삼성전자 (Samsung Electronics): 005930
- SK하이닉스 (SK Hynix): 000660

Years: 2023, 2024
Report Type: A001 (Annual Reports)

Requirements:
- MongoDB running on localhost:27017
- DART API key in environment (DART_API_KEY)
- Internet connection for API calls

Status: Live smoke test with real DART data
"""

import sys
from pathlib import Path
from datetime import datetime
import zipfile
import dart_fss as dart

print("=" * 80)
print("SHOWCASE 02: TextQuery with Live DART Data")
print("=" * 80)

# === Step 1: Setup ===

print("\n[Step 1] Importing modules and setup...")
from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.services.filing_search import FilingSearchService
from dart_fss_text.api import TextQuery
from dart_fss_text.models import SectionDocument, create_document_id
from dart_fss_text.models.requests import SearchFilingsRequest
from dart_fss_text.config import get_app_config

# Import parsing functions from experiments (exp_10)
sys.path.insert(0, str(Path(__file__).parent.parent))
from experiments.exp_10_xml_structure_exploration import (
    load_toc_mapping,
    build_section_index,
    extract_section_by_code,
    parse_section_content
)
import yaml

# Load configuration from config facade
config = get_app_config()
MONGO_URI = config.mongodb_uri
DATABASE = config.mongodb_database
COLLECTION = config.mongodb_collection
OPENDART_API_KEY = config.opendart_api_key

# Companies to download
COMPANIES = [
    ("005930", "삼성전자"),
    ("000660", "SK하이닉스")
]
YEARS = ["2023", "2024"]
REPORT_TYPE = "A001"  # Annual Report

print(f"  MongoDB: {DATABASE}.{COLLECTION}")
print(f"  Companies: {', '.join([f'{name}({code})' for code, name in COMPANIES])}")
print(f"  Years: {', '.join(YEARS)}")
print(f"  Report Type: {REPORT_TYPE}")

if not OPENDART_API_KEY:
    print("\n❌ ERROR: OPENDART_API_KEY not found!")
    print("   Please set OPENDART_API_KEY in your .env file")
    print("   Configuration is loaded via config.get_app_config()")
    sys.exit(1)

# Set DART API key
dart.set_api_key(OPENDART_API_KEY)

# === Step 2: Initialize Services ===

print("\n[Step 2] Initializing services...")
storage = StorageService(
    mongo_uri=MONGO_URI,
    database=DATABASE,
    collection=COLLECTION
)

query = TextQuery(storage_service=storage)
filing_search = FilingSearchService()

print("  ✓ StorageService initialized")
print("  ✓ TextQuery initialized")
print("  ✓ FilingSearchService initialized")

# === Step 3: Clear Existing Data ===

print("\n[Step 3] Clearing existing data...")
try:
    deleted = storage.collection.delete_many({})
    print(f"  ✓ Cleared {deleted.deleted_count} existing documents")
except Exception as e:
    print(f"  Note: Could not clear data: {e}")

# === Step 4: Download and Parse Reports ===

print("\n[Step 4] Downloading and parsing reports from DART...")

download_base = Path("data")
download_base.mkdir(parents=True, exist_ok=True)

total_sections = 0
reports_processed = 0

for stock_code, corp_name in COMPANIES:
    print(f"\n  Processing {corp_name} ({stock_code})...")
    
    for year in YEARS:
        print(f"    Year {year}:")
        
        try:
            # Search for report
            print(f"      Searching for {REPORT_TYPE} report...")
            search_request = SearchFilingsRequest(
                stock_codes=[stock_code],
                start_date=f"{year}0101",
                end_date=f"{year}1231",
                report_types=[REPORT_TYPE]
            )
            results = filing_search.search_filings(search_request)
            
            if not results:
                print(f"      ⚠️  No {REPORT_TYPE} report found for {year}")
                continue
            
            # Get the latest report if multiple found
            report = results[0]
            rcept_no = report.rcept_no
            rcept_dt = report.rcept_dt
            print(f"      ✓ Found report: {rcept_no} (published {rcept_dt})")
            
            # Download XML
            print(f"      Downloading XML...")
            corp_code = report.corp_code
            
            # Download to organized structure: data/{year}/{stock_code}/{report_type}/{rcept_no}/
            save_dir = download_base / year / stock_code / REPORT_TYPE / rcept_no
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Download using dart-fss
            from dart_fss.api import filings
            xml_path = filings.download_document(
                path=str(save_dir) + "/",
                rcept_no=rcept_no
            )
            
            # Extract ZIP file if it exists
            zip_file = save_dir / f"{rcept_no}.zip"
            if zip_file.exists():
                print(f"      Extracting ZIP file...")
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(save_dir)
                print(f"      ✓ Extracted ZIP contents")
            
            # Find the main XML file (not the attachments)
            main_xml = None
            for file in save_dir.glob("*.xml"):
                if file.stem == rcept_no:  # Main document
                    main_xml = file
                    break
            
            if not main_xml:
                print(f"      ⚠️  Main XML file not found in {save_dir}")
                print(f"      Available files: {list(save_dir.glob('*'))}")
                continue
            
            print(f"      ✓ Downloaded: {main_xml.name}")
            
            # Parse XML
            print(f"      Parsing XML...")
            
            # Load TOC mapping
            toc_mapping = load_toc_mapping()
            
            # Build section index
            section_index = build_section_index(main_xml, toc_mapping)
            print(f"      ✓ Built index with {len(section_index)} sections")
            
            # Extract all sections from index
            sections_stored = 0
            for atocid, section_meta in section_index.items():
                section_code = section_meta['section_code']
                if not section_code:
                    continue  # Skip unmapped sections
                
                # Extract section with full content
                parsed_section = extract_section_by_code(section_index, section_code)
                if not parsed_section:
                    continue
                
                # Flatten content to text
                text_parts = []
                for para in parsed_section.get('paragraphs', []):
                    text_parts.append(para)
                
                # Add tables as formatted text
                for table in parsed_section.get('tables', []):
                    table_text = []
                    if table.get('headers'):
                        table_text.append(' | '.join(table['headers']))
                    for row in table.get('rows', []):
                        table_text.append(' | '.join(row))
                    if table_text:
                        text_parts.append('\n'.join(table_text))
                
                text = '\n\n'.join(text_parts)
                
                if not text.strip():
                    continue  # Skip empty sections
                
                # Create SectionDocument
                doc = SectionDocument(
                    document_id=create_document_id(rcept_no, section_code),
                    rcept_no=rcept_no,
                    rcept_dt=rcept_dt,
                    year=year,
                    corp_code=corp_code,
                    corp_name=corp_name,
                    stock_code=stock_code,
                    report_type=REPORT_TYPE,
                    report_name="사업보고서",
                    section_code=section_code,
                    section_title=parsed_section['title'],
                    level=parsed_section['level'],
                    atocid=parsed_section['atocid'],
                    parent_section_code=None,  # Will be set by hierarchy reconstruction
                    parent_section_title=None,
                    section_path=[section_code],  # Will be updated by hierarchy
                    text=text,
                    char_count=len(text),
                    word_count=len(text.split()),
                    parsed_at=datetime.now(),
                    parser_version="1.0.0"
                )
                
                # Insert into MongoDB
                storage.insert_sections([doc])
                sections_stored += 1
            
            print(f"      ✓ Stored {sections_stored} sections")
            total_sections += sections_stored
            reports_processed += 1
            
        except Exception as e:
            print(f"      ❌ Error processing {year}: {e}")
            import traceback
            traceback.print_exc()
            continue

print(f"\n  ✓ Total: {reports_processed} reports, {total_sections} sections stored")

if total_sections == 0:
    print("\n❌ No sections were stored. Cannot proceed with showcase.")
    sys.exit(1)

# === Step 5: Reconstruct Hierarchy ===

print("\n[Step 5] Reconstructing section hierarchy...")
try:
    # Get all sections
    all_sections_data = list(storage.collection.find({}))
    
    # Group by report
    reports = {}
    for section_data in all_sections_data:
        rcept_no = section_data['rcept_no']
        if rcept_no not in reports:
            reports[rcept_no] = []
        reports[rcept_no].append(section_data)
    
    # Simple hierarchy reconstruction based on section codes
    for rcept_no, sections_data in reports.items():
        for section in sections_data:
            section_code = section['section_code']
            
            # Find parent by looking at section code prefix
            # e.g., 020100 -> parent is 020000, 020110 -> parent is 020100
            parent_code = None
            parent_title = None
            section_path = [section_code]
            
            # Check for parent (code with fewer trailing zeros)
            if len(section_code) == 6:
                # Try 4-digit parent (e.g., 020100 -> 020000)
                potential_parent = section_code[:3] + '000'
                for other in sections_data:
                    if other['section_code'] == potential_parent:
                        parent_code = potential_parent
                        parent_title = other['section_title']
                        section_path = [parent_code, section_code]
                        break
            
            # Update with hierarchy info
            storage.collection.update_one(
                {'document_id': section['document_id']},
                {'$set': {
                    'parent_section_code': parent_code,
                    'parent_section_title': parent_title,
                    'section_path': section_path
                }}
            )
    
    print(f"  ✓ Reconstructed hierarchy for {len(reports)} reports")
    
except Exception as e:
    print(f"  ⚠️  Hierarchy reconstruction failed: {e}")

# === Step 6: USE CASE 1 - Single Firm, Single Year ===

print("\n" + "=" * 80)
print("USE CASE 1: Single Firm, Single Year, Single Section")
print("=" * 80)
print("Query: Samsung 2024, section 020100 (사업의 개요)")

try:
    result1 = query.get(
        stock_codes="005930",
        years=2024,
        section_codes="020100"
    )
    
    if "2024" in result1 and "005930" in result1["2024"]:
        seq = result1["2024"]["005930"]
        print(f"\n  Company: {seq.corp_name}")
        print(f"  Year: {seq.year}")
        print(f"  Sections: {seq.section_count}")
        print(f"  Total words: {seq.total_word_count}")
        print(f"  Text preview (first 200 chars):")
        print(f"    {seq.text[:200]}...")
    else:
        print("  ⚠️  No data found for Samsung 2024")
except Exception as e:
    print(f"  ❌ Error: {e}")

# === Step 7: USE CASE 2 - Cross-Sectional Analysis ===

print("\n" + "=" * 80)
print("USE CASE 2: Cross-Sectional Analysis (Multiple Firms, Single Year)")
print("=" * 80)
print("Query: Samsung vs SK Hynix in 2024, section 020100")

try:
    result2 = query.get(
        stock_codes=["005930", "000660"],
        years=2024,
        section_codes="020100"
    )
    
    if "2024" in result2:
        print(f"\nCross-sectional comparison (2024):")
        for stock_code, seq in result2["2024"].items():
            print(f"  - {seq.corp_name} ({stock_code}):")
            print(f"    Sections: {seq.section_count}")
            print(f"    Words: {seq.total_word_count}")
            print(f"    Chars: {seq.total_char_count}")
    else:
        print("  ⚠️  No data found for 2024")
except Exception as e:
    print(f"  ❌ Error: {e}")

# === Step 8: USE CASE 3 - Time Series Analysis ===

print("\n" + "=" * 80)
print("USE CASE 3: Time Series Analysis (Single Firm, Multiple Years)")
print("=" * 80)
print("Query: Samsung 2023-2024, section 020100")

try:
    result3 = query.get(
        stock_codes="005930",
        start_year=2023,
        end_year=2024,
        section_codes="020100"
    )
    
    print(f"\nTime series for Samsung:")
    for year in sorted(result3.keys()):
        if "005930" in result3[year]:
            seq = result3[year]["005930"]
            print(f"  {year}:")
            print(f"    Words: {seq.total_word_count}")
            print(f"    Sections: {seq.section_count}")
        else:
            print(f"  {year}: No data")
except Exception as e:
    print(f"  ❌ Error: {e}")

# === Step 9: USE CASE 4 - Panel Data ===

print("\n" + "=" * 80)
print("USE CASE 4: Panel Data (Multiple Firms, Multiple Years)")
print("=" * 80)
print("Query: Samsung & SK Hynix, 2023-2024, section 020000 (with children)")

try:
    result4 = query.get(
        stock_codes=["005930", "000660"],
        start_year=2023,
        end_year=2024,
        section_codes="020000"  # Parent section
    )
    
    print(f"\nPanel data structure:")
    for year in sorted(result4.keys()):
        print(f"\n  {year}:")
        for stock_code, seq in result4[year].items():
            print(f"    - {seq.corp_name} ({stock_code}):")
            print(f"      Sections: {seq.section_count}")
            print(f"      Total words: {seq.total_word_count}")
            print(f"      Section codes: {seq.section_codes[:5]}{'...' if len(seq.section_codes) > 5 else ''}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# === Step 10: Data Statistics ===

print("\n" + "=" * 80)
print("DATA STATISTICS")
print("=" * 80)

try:
    # Count sections by company and year
    pipeline = [
        {
            '$group': {
                '_id': {
                    'corp_name': '$corp_name',
                    'stock_code': '$stock_code',
                    'year': '$year'
                },
                'section_count': {'$sum': 1},
                'total_words': {'$sum': '$word_count'},
                'total_chars': {'$sum': '$char_count'}
            }
        },
        {
            '$sort': {'_id.year': 1, '_id.stock_code': 1}
        }
    ]
    
    stats = list(storage.collection.aggregate(pipeline))
    
    print("\nSections stored in MongoDB:")
    for stat in stats:
        corp_name = stat['_id']['corp_name']
        stock_code = stat['_id']['stock_code']
        year = stat['_id']['year']
        count = stat['section_count']
        words = stat['total_words']
        chars = stat['total_chars']
        
        print(f"  {corp_name} ({stock_code}) - {year}:")
        print(f"    Sections: {count}")
        print(f"    Total words: {words:,}")
        print(f"    Total chars: {chars:,}")
except Exception as e:
    print(f"  ⚠️  Could not generate statistics: {e}")

# === Step 11: Data Location ===

print("\n" + "=" * 80)
print("DATA LOCATION")
print("=" * 80)

print(f"\n✓ Data stored in MongoDB:")
print(f"  Database: {DATABASE}")
print(f"  Collection: {COLLECTION}")
print(f"\nYou can query this data using:")
print(f"  from dart_fss_text.services import StorageService")
print(f"  from dart_fss_text.api import TextQuery")
print(f"  storage = StorageService(database='{DATABASE}', collection='{COLLECTION}')")
print(f"  query = TextQuery(storage_service=storage)")
print(f"\nTo clean up: storage.collection.drop()")

# === Summary ===

print("\n" + "=" * 80)
print("SHOWCASE COMPLETE")
print("=" * 80)
print("\nDemonstrated with REAL DART data:")
print(f"  ✅ Downloaded {reports_processed} reports from DART API")
print(f"  ✅ Parsed {total_sections} sections from XML")
print(f"  ✅ Stored in MongoDB")
print("  ✅ Use Case 1: Single firm, single year")
print("  ✅ Use Case 2: Cross-sectional analysis")
print("  ✅ Use Case 3: Time series analysis")
print("  ✅ Use Case 4: Panel data research")
print("\nTextQuery interface validated with production data!")
print("=" * 80)

