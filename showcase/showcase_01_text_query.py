"""
Showcase 01: TextQuery End-to-End Workflow

This showcase demonstrates the complete query interface workflow:
1. Insert sample data into MongoDB
2. Query data using TextQuery
3. Demonstrate all 4 research use cases
4. Clean up test data

Requirements:
- MongoDB running on localhost:27017
- Environment variable: MONGODB_DATABASE (default: FS)
- Collection will be created: A001_showcase

Status: Live smoke test with real MongoDB
"""

from datetime import datetime

print("=" * 80)
print("SHOWCASE 01: TextQuery End-to-End Workflow")
print("=" * 80)

# === Step 1: Setup ===

print("\n[Step 1] Importing modules...")
from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.api import TextQuery
from dart_fss_text.models import SectionDocument, create_document_id
from dart_fss_text.config import get_app_config

# Load configuration from config facade
config = get_app_config()

# Use temporary collection for showcase (override default A001)
COLLECTION = "A001_showcase"

print(f"  MongoDB URI: {config.mongodb_uri}")
print(f"  Database: {config.mongodb_database}")
print(f"  Collection: {COLLECTION}")

# === Step 2: Initialize Services ===

print("\n[Step 2] Initializing services...")
# Override collection only (other config from facade)
storage = StorageService(collection=COLLECTION)

query = TextQuery(storage_service=storage)
print("  ✓ StorageService initialized")
print("  ✓ TextQuery initialized")

# === Step 3: Create Sample Data ===

print("\n[Step 3] Creating sample data...")

# Clear any existing data from previous runs
try:
    storage.collection.delete_many({})
    print("  ✓ Cleared existing data from collection")
except Exception as e:
    print(f"  Note: Could not clear existing data: {e}")

# We'll create data for two companies (Samsung and SK Hynix) across two years (2023, 2024)
sample_data = [
    # Samsung 2023
    {
        "rcept_no": "20230312000736",
        "rcept_dt": "20230312",
        "year": "2023",
        "stock_code": "005930",
        "corp_code": "00126380",
        "corp_name": "삼성전자",
        "sections": [
            ("020000", "II. 사업의 내용", 1, "9", None, ["020000"], 
             "2023년 삼성전자의 사업 내용입니다."),
            ("020100", "1. 사업의 개요", 2, "10", "020000", ["020000", "020100"],
             "삼성전자는 2023년에 반도체, 디스플레이, 모바일 사업을 영위했습니다."),
            ("020200", "2. 주요 제품 및 서비스", 2, "11", "020000", ["020000", "020200"],
             "주요 제품으로는 갤럭시 스마트폰, 반도체, TV 등이 있습니다."),
        ]
    },
    # Samsung 2024
    {
        "rcept_no": "20240312000736",
        "rcept_dt": "20240312",
        "year": "2024",
        "stock_code": "005930",
        "corp_code": "00126380",
        "corp_name": "삼성전자",
        "sections": [
            ("020000", "II. 사업의 내용", 1, "9", None, ["020000"],
             "2024년 삼성전자의 사업 내용입니다."),
            ("020100", "1. 사업의 개요", 2, "10", "020000", ["020000", "020100"],
             "삼성전자는 2024년에 AI 반도체, 차세대 디스플레이, 폴더블 스마트폰 사업을 확대했습니다."),
            ("020200", "2. 주요 제품 및 서비스", 2, "11", "020000", ["020000", "020200"],
             "주요 제품으로는 갤럭시 S24, HBM3 메모리, QD-OLED TV 등이 있습니다."),
        ]
    },
    # SK Hynix 2023
    {
        "rcept_no": "20230314000123",
        "rcept_dt": "20230314",
        "year": "2023",
        "stock_code": "000660",
        "corp_code": "00164779",
        "corp_name": "SK하이닉스",
        "sections": [
            ("020000", "II. 사업의 내용", 1, "9", None, ["020000"],
             "2023년 SK하이닉스의 사업 내용입니다."),
            ("020100", "1. 사업의 개요", 2, "10", "020000", ["020000", "020100"],
             "SK하이닉스는 2023년에 메모리 반도체 사업에 집중했습니다."),
            ("020200", "2. 주요 제품 및 서비스", 2, "11", "020000", ["020000", "020200"],
             "주요 제품으로는 DRAM, NAND Flash 등이 있습니다."),
        ]
    },
    # SK Hynix 2024
    {
        "rcept_no": "20240314000123",
        "rcept_dt": "20240314",
        "year": "2024",
        "stock_code": "000660",
        "corp_code": "00164779",
        "corp_name": "SK하이닉스",
        "sections": [
            ("020000", "II. 사업의 내용", 1, "9", None, ["020000"],
             "2024년 SK하이닉스의 사업 내용입니다."),
            ("020100", "1. 사업의 개요", 2, "10", "020000", ["020000", "020100"],
             "SK하이닉스는 2024년에 HBM3E 등 고부가가치 메모리에 주력했습니다."),
            ("020200", "2. 주요 제품 및 서비스", 2, "11", "020000", ["020000", "020200"],
             "주요 제품으로는 HBM3E, DDR5, 176단 NAND 등이 있습니다."),
        ]
    },
]

# Convert to SectionDocument objects and insert
inserted_count = 0
for report in sample_data:
    for section_data in report["sections"]:
        section_code, title, level, atocid, parent, path, text = section_data
        
        doc = SectionDocument(
            document_id=create_document_id(report["rcept_no"], section_code),
            rcept_no=report["rcept_no"],
            rcept_dt=report["rcept_dt"],
            year=report["year"],
            corp_code=report["corp_code"],
            corp_name=report["corp_name"],
            stock_code=report["stock_code"],
            report_type="A001",
            report_name="사업보고서",
            section_code=section_code,
            section_title=title,
            level=level,
            atocid=atocid,
            parent_section_code=parent,
            parent_section_title="II. 사업의 내용" if parent else None,
            section_path=path,
            text=text,
            char_count=len(text),
            word_count=len(text.split()),
            parsed_at=datetime.now(),
            parser_version="1.0.0"
        )
        
        storage.insert_sections([doc])
        inserted_count += 1

print(f"  ✓ Inserted {inserted_count} sections into MongoDB")
print(f"    - Samsung 2023: 3 sections")
print(f"    - Samsung 2024: 3 sections")
print(f"    - SK Hynix 2023: 3 sections")
print(f"    - SK Hynix 2024: 3 sections")

# === Step 4: Use Case 1 - Single Firm, Single Year ===

print("\n" + "=" * 80)
print("USE CASE 1: Single Firm, Single Year, Single Section")
print("=" * 80)
print("Query: Samsung 2024, section 020100 (사업의 개요)")

result1 = query.get(
    stock_codes="005930",
    years=2024,
    section_codes="020100"
)

print(f"\nResult structure: {list(result1.keys())}")
print(f"  Years: {list(result1.keys())}")
print(f"  Firms in 2024: {list(result1['2024'].keys())}")

seq = result1["2024"]["005930"]
print(f"\n  Company: {seq.corp_name}")
print(f"  Year: {seq.year}")
print(f"  Sections: {seq.section_count}")
print(f"  Section codes: {seq.section_codes}")
print(f"  Text preview: {seq.text[:100]}...")

# === Step 5: Use Case 2 - Cross-Sectional Analysis ===

print("\n" + "=" * 80)
print("USE CASE 2: Cross-Sectional Analysis (Multiple Firms, Single Year)")
print("=" * 80)
print("Query: Samsung vs SK Hynix in 2024, section 020100")

result2 = query.get(
    stock_codes=["005930", "000660"],
    years=2024,
    section_codes="020100"
)

print(f"\nCross-sectional comparison (2024):")
for stock_code, seq in result2["2024"].items():
    print(f"  - {seq.corp_name} ({stock_code}):")
    print(f"    Sections: {seq.section_count}")
    print(f"    Words: {seq.total_word_count}")
    print(f"    Chars: {seq.total_char_count}")

# === Step 6: Use Case 3 - Time Series Analysis ===

print("\n" + "=" * 80)
print("USE CASE 3: Time Series Analysis (Single Firm, Multiple Years)")
print("=" * 80)
print("Query: Samsung 2023-2024, section 020100")

result3 = query.get(
    stock_codes="005930",
    start_year=2023,
    end_year=2024,
    section_codes="020100"
)

print(f"\nTime series for Samsung:")
for year in sorted(result3.keys()):
    seq = result3[year]["005930"]
    print(f"  {year}:")
    print(f"    Words: {seq.total_word_count}")
    print(f"    Text preview: {seq.text[:80]}...")

# === Step 7: Use Case 4 - Panel Data ===

print("\n" + "=" * 80)
print("USE CASE 4: Panel Data (Multiple Firms, Multiple Years)")
print("=" * 80)
print("Query: Samsung & SK Hynix, 2023-2024, section 020000 (with children)")

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
        print(f"      Codes: {seq.section_codes}")
        print(f"      Total words: {seq.total_word_count}")

# === Step 8: Demonstrate Sequence Features ===

print("\n" + "=" * 80)
print("SEQUENCE FEATURES DEMONSTRATION")
print("=" * 80)

# Get a sequence for demonstration
seq_demo = result4["2024"]["005930"]

print(f"\n1. Metadata access:")
print(f"   Company: {seq_demo.corp_name}")
print(f"   Stock code: {seq_demo.stock_code}")
print(f"   Year: {seq_demo.year}")
print(f"   Report type: {seq_demo.report_type}")

print(f"\n2. Indexing:")
print(f"   First section (by index): {seq_demo[0].section_title}")
if len(seq_demo) > 1:
    print(f"   Second section (by index): {seq_demo[1].section_title}")
if '020100' in seq_demo:
    print(f"   Specific section (by code): {seq_demo['020100'].section_title}")
else:
    print(f"   Note: '020100' not in this sequence (codes: {seq_demo.section_codes})")

print(f"\n3. Iteration:")
print(f"   All section titles:")
for section in seq_demo:
    print(f"     - [{section.section_code}] {section.section_title}")

print(f"\n4. Text merging:")
print(f"   Merged text length: {len(seq_demo.text)} chars")
print(f"   Custom separator: {len(seq_demo.get_text(separator='\\n---\\n'))} chars")

print(f"\n5. Statistics:")
print(f"   Section count: {seq_demo.section_count}")
print(f"   Total char count: {seq_demo.total_char_count}")
print(f"   Total word count: {seq_demo.total_word_count}")

# === Step 9: Clean Up ===

print("\n" + "=" * 80)
print("CLEANUP")
print("=" * 80)

# Drop the showcase collection
storage.collection.drop()
print(f"  ✓ Dropped collection '{COLLECTION}'")

# === Summary ===

print("\n" + "=" * 80)
print("SHOWCASE COMPLETE")
print("=" * 80)
print("\nDemonstrated:")
print("  ✅ Use Case 1: Single firm, single year")
print("  ✅ Use Case 2: Cross-sectional analysis")
print("  ✅ Use Case 3: Time series analysis")
print("  ✅ Use Case 4: Panel data research")
print("  ✅ Sequence features (indexing, iteration, text merging, statistics)")
print("\nTextQuery interface is ready for production use!")
print("=" * 80)

