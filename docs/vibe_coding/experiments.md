# Experiment Plan: Phase 1 - Discovery & Download POC

## Objective

Validate the **discovery and download workflow** for dart-fss-text. This Phase 1 focuses on searching for filings, extracting metadata (especially point-in-time fields), and downloading documents—NOT on parsing XML (that comes in Phase 2/3).

**Key Distinction**: We're building the foundation for a complete data pipeline:
1. **Phase 1 (This Experiment)**: Discovery → Download → Metadata extraction
2. **Phase 2 (Later)**: XML parsing → Section/table extraction  
3. **Phase 3 (Later)**: MongoDB storage → Querying

---

## Experiment Scope

### Goals
1. **Search Filings**: Use dart-fss to search for filings by stock code, date range, and report type
2. **Extract Metadata**: Get published_date, amended_date, rcept_no for PIT integrity
3. **Download Document**: Use `download_document()` to retrieve ZIP file
4. **Unzip & Store**: Extract XML and organize in structured directory
5. **Validate Workflow**: Confirm the end-to-end discovery → download → storage pipeline

### Non-Goals (For This Experiment)
- XML parsing and section extraction (Phase 2)
- MongoDB integration (Phase 3)
- Error handling and retries (production hardening)
- Batch processing optimization

---

## Experiment Principles (CRITICAL)

### 1. **Never Fake Results**
- ❌ DON'T use hardcoded data to make experiments "pass"
- ❌ DON'T use workarounds without understanding root cause
- ✅ DO investigate failures thoroughly
- ✅ DO document what actually works vs. what doesn't

### 2. **Never Hide Errors**
- ❌ DON'T catch exceptions and continue silently
- ❌ DON'T use fallbacks without logging the failure
- ✅ DO let experiments fail loudly when something is wrong
- ✅ DO document unexpected behavior

### 3. **Always Investigate Failures**
- ❌ DON'T move to workarounds immediately
- ❌ DON'T assume "close enough" is good enough
- ✅ DO check documentation thoroughly
- ✅ DO try multiple approaches to understand the API
- ✅ DO document why one approach works and another doesn't

### 4. **Test with Real Data**
- ❌ DON'T use mock data in POC experiments
- ❌ DON'T skip verification steps
- ✅ DO use live API calls to validate assumptions
- ✅ DO verify results make sense (e.g., Samsung should have annual reports!)

**Example of WRONG approach**:
```python
# BAD: Empty results? Use hardcoded rcept_no!
filings = corp.search_filings(...)
if len(filings) == 0:
    # Just use a known document ID
    rcept_no = "20250814003156"  # ❌ WRONG!
```

**Example of CORRECT approach**:
```python
# GOOD: Empty results? Investigate why!
filings = corp.search_filings(...)
if len(filings) == 0:
    # Stop and investigate
    print("❌ No filings found - investigating...")
    print("1. Checking if pblntf_detail_ty parameter is needed")
    print("2. Checking if we're using the right search function")
    print("3. Checking dart-fss documentation")
    raise ValueError("Search returned no results - need to fix search method")
```

---

## Prerequisites

### Environment Setup
- [x] Python ≥ 3.12 installed
- [x] `dart-fss` library available (v0.4.14)
- [x] `python-dotenv` installed
- [x] `OPENDART_API_KEY` stored in `.env` file at project root

### Test Data

**Target Company**: Samsung Electronics (삼성전자)
- **Stock Code**: `005930`
- **Sample Receipt Number**: `20250814003156` (for direct download test)
- **Date Range**: 2024-01-01 to 2024-12-31 (for search test)
- **Report Types**: Annual (A001), Semi-Annual (A002)

We'll test both:
1. **Direct download** by rcept_no (validates download mechanics)
2. **Search + download** workflow (validates full discovery pipeline)

---

## Experiment Steps

### Experiment 1: Direct Document Download

#### Step 1.1: Environment Configuration
**Goal**: Load API key and configure dart-fss

```python
import os
from pathlib import Path
from dotenv import load_dotenv
import dart_fss as dart

# Load environment variables from project root
load_dotenv()
api_key = os.getenv("OPENDART_API_KEY")

if not api_key:
    raise ValueError("OPENDART_API_KEY not found in .env file")

# Set API key for dart-fss
dart.set_api_key(api_key=api_key)

print(f"API Key configured: {api_key[:10]}***")
```

**Validation**:
- ✓ API key loads without error
- ✓ Key is properly masked in output

---

#### Step 1.2: Download Document by rcept_no
**Goal**: Retrieve the ZIP file containing the XML document

```python
from dart_fss.api import filings
import time

# Target receipt number
rcept_no = "20250814003156"

# Download path (will be created if doesn't exist)
download_path = Path("./experiments/data/")
download_path.mkdir(parents=True, exist_ok=True)

print(f"Downloading document {rcept_no}...")
start_time = time.time()

# Download document
# NOTE: According to user, this downloads to path/{rcept_no}.zip
result = filings.download_document(
    path=str(download_path) + "/",  # Ensure trailing slash
    rcept_no=rcept_no
)

elapsed = time.time() - start_time
print(f"Download completed in {elapsed:.2f}s")
print(f"Result: {result}")

# Verify file exists
zip_file = download_path / f"{rcept_no}.zip"
if zip_file.exists():
    size_mb = zip_file.stat().st_size / (1024 * 1024)
    print(f"✓ ZIP file created: {zip_file}")
    print(f"  Size: {size_mb:.2f} MB")
else:
    print(f"✗ Expected file not found: {zip_file}")
```

**Expected Outcome**:
- File downloaded to `experiments/data/20250814003156.zip`
- File size: ~0.5-2 MB (depending on document)
- Download time: ~2-10 seconds (depending on network)

**Validation**:
- ✓ ZIP file exists at expected path
- ✓ File is a valid ZIP archive (can be opened)
- ✓ Download time is reasonable

---

#### Step 1.3: Extract ZIP Archive
**Goal**: Unzip the archive and access the XML file

```python
import zipfile

# Paths
zip_path = download_path / f"{rcept_no}.zip"
extract_path = download_path / rcept_no

# Create extraction directory
extract_path.mkdir(exist_ok=True)

# Extract
print(f"Extracting {zip_path} to {extract_path}...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    file_list = zip_ref.namelist()
    print(f"  Files in archive: {file_list}")
    zip_ref.extractall(extract_path)

# List extracted files
extracted_files = list(extract_path.glob("*"))
print(f"Extracted {len(extracted_files)} file(s):")
for f in extracted_files:
    size_mb = f.stat().st_size / (1024 * 1024)
    print(f"  - {f.name} ({size_mb:.2f} MB)")

# Locate XML file (should be {rcept_no}.xml)
xml_file = extract_path / f"{rcept_no}.xml"
if xml_file.exists():
    print(f"✓ XML file found: {xml_file}")
else:
    # Sometimes it might be named differently; check all .xml files
    xml_files = list(extract_path.glob("*.xml"))
    if xml_files:
        xml_file = xml_files[0]
        print(f"✓ XML file found (alternate name): {xml_file}")
    else:
        raise FileNotFoundError(f"No XML file found in {extract_path}")
```

**Expected Outcome**:
- Single XML file: `20250814003156.xml`
- File size: ~1-5 MB (contains full financial statement)

**Validation**:
- ✓ XML file exists
- ✓ File size is reasonable (> 100 KB)
- ✓ File is valid XML (can be parsed—we'll check next)

---

#### Step 1.4: Quick XML Sanity Check
**Goal**: Verify XML is valid and has expected structure

```python
import xml.etree.ElementTree as ET

# Parse XML (quick sanity check—full parsing comes in Phase 2)
print("Parsing XML...")
try:
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    print(f"✓ XML parsed successfully")
    print(f"  Root tag: <{root.tag}>")
    print(f"  Root attributes: {root.attrib}")
    print(f"  Total elements in tree: {len(list(root.iter()))}")
    
    # Quick check for expected element types
    p_tags = root.findall(".//P")
    table_tags = root.findall(".//TABLE")
    span_tags = root.findall(".//SPAN")
    
    print(f"  Element counts:")
    print(f"    <P> tags: {len(p_tags)}")
    print(f"    <TABLE> tags: {len(table_tags)}")
    print(f"    <SPAN> tags: {len(span_tags)}")
    
    # Check for USERMARK attributes (section markers)
    usermark_elems = root.findall(".//*[@USERMARK]")
    print(f"    Elements with USERMARK: {len(usermark_elems)}")
    
except ET.ParseError as e:
    print(f"✗ XML parsing failed: {e}")
    raise
```

**Expected Outcome**:
- XML parses without errors
- Contains thousands of elements (typical for full financial statements)
- Has P, TABLE, SPAN tags
- Has elements with USERMARK attributes

**Validation**:
- ✓ No XML parse errors
- ✓ Element counts are reasonable (not empty document)

---

---

### Experiment 2: Filing Search & Metadata Extraction

This experiment validates the **discovery pipeline**: searching for filings by company and date, then extracting PIT-critical metadata.

#### Step 2.1: Search Filings by Company
**Goal**: Use dart-fss to search for filings by stock code and report type

```python
# Search for Samsung Electronics filings
stock_code = "005930"  # Samsung Electronics
start_date = "2024-01-01"
end_date = "2024-12-31"

print(f"Searching filings for stock code {stock_code}...")
print(f"  Date range: {start_date} to {end_date}")

# Get company object
try:
    corp = dart.get_corp(stock_code)
    print(f"✓ Company found: {corp.corp_name} ({corp.corp_code})")
except Exception as e:
    print(f"✗ Failed to get company: {e}")
    raise

# Search filings
# According to dart-fss docs: corp.search_filings(start_dt, end_dt, bgn_de, end_de)
try:
    filings = corp.search_filings(
        start_dt=start_date,
        end_dt=end_date,
        # pblntf_ty=['A001', 'A002']  # Filter by report type if supported
    )
    
    print(f"✓ Found {len(filings)} filing(s)")
    
    # Display first 5 filings
    for i, filing in enumerate(filings[:5], 1):
        print(f"\n{i}. Filing:")
        print(f"   rcept_no: {filing.rcept_no}")
        print(f"   report_nm: {filing.report_nm}")
        print(f"   flr_nm: {filing.flr_nm}")
        print(f"   rcept_dt: {filing.rcept_dt}")
        
        # Check for more attributes
        for attr in ['corp_code', 'corp_name', 'rm']:
            if hasattr(filing, attr):
                print(f"   {attr}: {getattr(filing, attr)}")
    
except Exception as e:
    print(f"✗ Filing search failed: {e}")
    raise
```

**Expected Outcome**:
- Successfully retrieves Samsung filings for 2024
- Each filing has rcept_no, report_nm, rcept_dt
- List includes annual/semi-annual reports

**Validation**:
- ✓ Search returns results
- ✓ rcept_no format matches expected pattern (long numeric string)
- ✓ rcept_dt matches date range filter

---

#### Step 2.2: Extract Metadata from Filings
**Goal**: Extract PIT-critical metadata (published date, amended date)

```python
import json
from datetime import datetime

# Analyze metadata structure
metadata_list = []

for filing in filings[:10]:  # Analyze first 10
    metadata = {
        "rcept_no": filing.rcept_no,
        "report_nm": filing.report_nm,
        "rcept_dt": filing.rcept_dt,  # Receipt date (published date)
    }
    
    # Check for additional date fields (amended date, etc.)
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
        metadata['remarks'] = filing.rm  # May contain amendment info
    
    metadata_list.append(metadata)

# Display sample metadata
print(f"\nSample Metadata Structure:")
print(json.dumps(metadata_list[0], indent=2, ensure_ascii=False))

# Save all metadata
output_file = Path("./experiments/data/filing_metadata.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(metadata_list, f, indent=2, ensure_ascii=False)

print(f"\n✓ Metadata saved to {output_file}")
```

**Expected Outcome**:
- Each filing has at minimum: rcept_no, report_nm, rcept_dt
- May have additional fields: pblntf_ty (report type), rm (remarks/amendment info)
- Metadata saved to JSON for analysis

**Key Questions to Answer**:
1. What field contains the **original published date**? (likely `rcept_dt`)
2. Is there an **amended date** field? (check `rm` or other date fields)
3. What field contains the **report type code**? (A001, A002, etc.)
4. Are there any version/revision indicators?

**Validation**:
- ✓ rcept_dt is populated for all filings
- ✓ Date format is parseable (YYYYMMDD or similar)
- ✓ Metadata includes report type identifier

---

#### Step 2.3: Filter by Report Type
**Goal**: Test filtering by report type (annual, semi-annual, etc.)

```python
# Try to filter by report type
# Note: dart-fss API may or may not support filtering by pblntf_ty directly
# If not, we'll filter manually after retrieval

print("\nFiltering by report type...")

# Map of report types
REPORT_TYPES = {
    'A001': '사업보고서',  # Annual
    'A002': '반기보고서',  # Semi-annual
    'A003': '분기보고서',  # Quarterly
}

# Filter annual and semi-annual reports
filtered_filings = []
for filing in filings:
    # Check if report name matches annual or semi-annual
    if any(report_nm in filing.report_nm for report_nm in REPORT_TYPES.values()):
        filtered_filings.append({
            'rcept_no': filing.rcept_no,
            'report_nm': filing.report_nm,
            'rcept_dt': filing.rcept_dt,
        })

print(f"✓ Filtered to {len(filtered_filings)} annual/semi-annual reports")

# Display filtered results
for i, f in enumerate(filtered_filings[:5], 1):
    print(f"{i}. {f['report_nm']} - {f['rcept_dt']} - {f['rcept_no']}")

# Save filtered list
output_file = Path("./experiments/data/filtered_filings.json")
with open(output_file, 'w', encoding='utf-8') as file:
    json.dump(filtered_filings, file, indent=2, ensure_ascii=False)

print(f"\n✓ Filtered filings saved to {output_file}")
```

**Expected Outcome**:
- Successfully filters to annual (사업보고서) and semi-annual (반기보고서) reports
- Filtered list is smaller than original filing list
- Each filtered filing has complete metadata

**Validation**:
- ✓ Filtering logic works correctly
- ✓ Report names match expected patterns
- ✓ No quarterly or ad-hoc reports in filtered list

---

---

### Experiment 3: End-to-End Workflow

This experiment combines all steps: search → filter → download → unzip → store

#### Step 3.1: Full Pipeline Test

```python
# Full pipeline: Search → Filter → Download → Store
def download_and_store_filings(
    stock_code: str,
    start_date: str,
    end_date: str,
    report_filter: list = None,
    max_downloads: int = 3
):
    """
    Full pipeline test
    """
    # 1. Search filings
    corp = dart.get_corp(stock_code)
    filings = corp.search_filings(start_dt=start_date, end_dt=end_date)
    
    # 2. Filter by report type
    if report_filter:
        filings = [f for f in filings if any(r in f.report_nm for r in report_filter)]
    
    # 3. Download and store
    results = []
    for i, filing in enumerate(filings[:max_downloads], 1):
        print(f"\n[{i}/{min(max_downloads, len(filings))}] Processing {filing.rcept_no}...")
        
        try:
            # Create organized directory structure
            # data/raw/{stock_code}/{report_type}/{rcept_no}_{rcept_dt}.xml
            stock_dir = Path(f"./experiments/data/raw/{stock_code}")
            stock_dir.mkdir(parents=True, exist_ok=True)
            
            # Download
            zip_path = stock_dir / f"{filing.rcept_no}.zip"
            if not zip_path.exists():
                filings.download_document(
                    path=str(stock_dir) + "/",
                    rcept_no=filing.rcept_no
                )
                print(f"  ✓ Downloaded: {filing.rcept_no}.zip")
            else:
                print(f"  ⊙ Already exists: {filing.rcept_no}.zip")
            
            # Unzip
            extract_dir = stock_dir / filing.rcept_no
            extract_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(extract_dir)
            
            xml_file = extract_dir / f"{filing.rcept_no}.xml"
            if xml_file.exists():
                print(f"  ✓ Extracted: {xml_file.name}")
            
            # Store result
            results.append({
                "rcept_no": filing.rcept_no,
                "report_nm": filing.report_nm,
                "rcept_dt": filing.rcept_dt,
                "zip_path": str(zip_path),
                "xml_path": str(xml_file),
                "status": "success"
            })
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({
                "rcept_no": filing.rcept_no,
                "status": "failed",
                "error": str(e)
            })
    
    return results

# Run pipeline
pipeline_results = download_and_store_filings(
    stock_code="005930",
    start_date="2024-01-01",
    end_date="2024-12-31",
    report_filter=["사업보고서", "반기보고서"],
    max_downloads=3
)

# Save results
output_file = Path("./experiments/data/pipeline_results.json")
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(pipeline_results, f, indent=2, ensure_ascii=False)

print(f"\n✓ Pipeline completed: {len([r for r in pipeline_results if r['status']=='success'])} success, {len([r for r in pipeline_results if r['status']=='failed'])} failed")
print(f"✓ Results saved to {output_file}")
```

**Expected Outcome**:
- Successfully downloads 3 filings
- Organized directory structure created
- Each filing has ZIP + extracted XML
- Pipeline results saved to JSON

**Validation**:
- ✓ All steps complete without errors
- ✓ Directory structure is organized and clear
- ✓ XML files are valid
- ✓ Metadata is complete

---

---

## Expected Directory Structure After Experiments

```
experiments/
├── exp_01_download_document.py        # Experiment 1 script
├── exp_02_filing_search.py            # Experiment 2 script
├── exp_03_end_to_end_pipeline.py      # Experiment 3 script
└── data/
    ├── 20250814003156.zip             # Direct download test
    ├── 20250814003156/
    │   └── 20250814003156.xml
    ├── raw/                           # Organized storage
    │   └── 005930/                    # Samsung Electronics
    │       ├── {rcept_no}.zip
    │       └── {rcept_no}/
    │           └── {rcept_no}.xml
    ├── filing_metadata.json           # All filings metadata
    ├── filtered_filings.json          # Filtered filings
    └── pipeline_results.json          # Pipeline execution results
```

---

## Success Criteria

The Phase 1 experiments are successful if we can:

### Experiment 1: Direct Download
1. ✅ Load API key from .env file
2. ✅ Download a document by rcept_no using dart-fss
3. ✅ Unzip and access the XML file
4. ✅ Verify XML is valid and parseable

### Experiment 2: Filing Search
5. ✅ Search filings by stock code and date range
6. ✅ Extract complete metadata (rcept_no, report_nm, rcept_dt)
7. ✅ Identify PIT-critical fields (published date, amended date)
8. ✅ Filter filings by report type

### Experiment 3: End-to-End
9. ✅ Run complete pipeline: search → filter → download → unzip → store
10. ✅ Create organized directory structure
11. ✅ Handle multiple filings without errors
12. ✅ Save execution results and metadata

---

## Key Questions to Answer

### Metadata & PIT Integrity
1. **Published Date**: What field contains the original published date? (`rcept_dt`?)
2. **Amended Date**: Is there a field for amended/corrected filings? How do we detect amendments?
3. **Report Type**: What field/pattern identifies A001, A002, A003? Is it in `report_nm` or separate field?
4. **Version Control**: How do we handle multiple versions of the same filing (original + amendments)?

### Filing Search & Filtering
5. **Search API**: Does dart-fss support native filtering by report type, or must we filter post-retrieval?
6. **Date Filters**: Are search results properly filtered by start_dt/end_dt?
7. **Company Lookup**: How reliable is the stock_code → corp_code mapping?

### Download & Storage
8. **File Naming**: Is the pattern always `{rcept_no}.zip` → `{rcept_no}.xml`?
9. **Error Handling**: What errors can occur during download? (rate limiting, invalid rcept_no, network issues)
10. **Storage Strategy**: Best directory structure for organizing thousands of filings?

### XML Structure (Quick Check Only)
11. **Validity**: Are all downloaded XMLs valid and parseable?
12. **Size**: What's the typical file size range? Any outliers?
13. **Consistency**: Do all filings have similar XML structure, or are there major variations?

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| API rate limiting | Use cached document if download fails |
| Invalid rcept_no | Have 2-3 backup rcept_no values ready |
| XML parsing errors | Catch exceptions, try alternative parsers (lxml) |
| Unexpected XML structure | Document discrepancies, adjust parser design |

---

## Next Steps After Phase 1 Experiments

1. **Write Tests**: Create formal tests in `tests/` based on experiment findings
2. **Implement Discovery Module**: Build production code for filing search and metadata extraction
3. **Implement Download Module**: Build production code for downloading and organizing filings
4. **Document Metadata Schema**: Define data models for PIT-critical metadata
5. **Move to Phase 2**: Begin XML parsing experiments (USERMARK patterns, section extraction)

---

## Execution Plan

**Timeline**: Single session (~2-3 hours)

**Scripts**: Create separate Python scripts for each experiment
- `experiments/exp_01_download_document.py`: Direct download test
- `experiments/exp_02_filing_search.py`: Search and metadata extraction
- `experiments/exp_03_end_to_end_pipeline.py`: Full pipeline

**Alternative**: Can use `sandbox.ipynb` for interactive exploration

**Approval Gate**: User reviews this plan → Approval → Execute experiments

---

## Notes & Observations

(To be filled during experiment execution)

- **Performance**: Time taken for download, parsing
- **Surprises**: Unexpected XML structures or attributes
- **Challenges**: Any steps that required workarounds
- **Ideas**: Features or edge cases to consider for implementation

---

## Status

**Current Status**: 📝 **Awaiting User Approval**

Once approved, we'll execute this experiment in `sandbox.ipynb` and document all findings for the next phase of development.

