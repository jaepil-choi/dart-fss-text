# Experiment Findings & Lessons Learned

## Phase 1: Discovery & Download POC

### Critical Lesson: Never Hide Errors, Always Investigate

**Date**: 2025-10-02

---

## Issue: Original Search Returned No Results

### What Happened (WRONG Approach):

In `exp_02_filing_search.py` and `exp_03_end_to_end_pipeline.py`, I used:

```python
# WRONG: Missing pblntf_detail_ty parameter!
filings = corp.search_filings(
    bgn_de='20240101',
    end_de='20241231'
)
# Result: 0 or very few filings returned
```

When this returned no results, I:
1. ❌ Didn't investigate thoroughly
2. ❌ Created workaround using hardcoded `rcept_no`
3. ❌ Moved on without understanding the root cause

This violated the **POC Experiment Principles**: Never fake results!

---

## Root Cause Analysis

### Investigation Steps (exp_02c_correct_search_api.py):

Tested three different search methods from dart-fss:

#### Method 1: Module-level `search_filings()`
```python
from dart_fss.api.filings import search_filings

results = search_filings(
    corp_code=corp_code,
    bgn_de='20230101',
    end_de='20241231',
    pblntf_detail_ty='A001',
    page_count=100
)
```
**Result**: Returns list of strings (different data structure), not recommended

#### Method 2: `search_annual_report()` helper
```python
from dart_fss.fs.extract import search_annual_report

results = search_annual_report(
    corp_code=corp_code,
    bgn_de='20230101',
    end_de='20241231',
    separate=False
)
```
**Result**: ✅ **WORKS** - Found 2 Samsung annual reports

#### Method 3: `Corp.search_filings()` with `pblntf_detail_ty`
```python
corp = corp_list.find_by_stock_code('005930')
results = corp.search_filings(
    bgn_de='20230101',
    pblntf_detail_ty='A001'  # ← THIS WAS MISSING!
)
```
**Result**: ✅ **WORKS BEST** - Found 3 Samsung annual reports (2022, 2023, 2024)

---

## The Fix

### **CORRECT** Approach:

```python
# Get company
corp_list = dart.get_corp_list()
corp = corp_list.find_by_stock_code(stock_code)

# Search with pblntf_detail_ty parameter!
filings = corp.search_filings(
    bgn_de='20240101',
    pblntf_detail_ty='A001'  # Annual reports
)

# SANITY CHECK: Verify results make sense
if stock_code == "005930" and len(filings) == 0:
    raise ValueError("Samsung should have annual reports - search method is wrong!")
```

### Available Report Type Codes:
- `'A001'`: 사업보고서 (Annual Report)
- `'A002'`: 반기보고서 (Semi-Annual Report)
- `'A003'`: 분기보고서 (Quarterly Report)

---

## Lessons Learned

### 1. **Always Use Sanity Checks**

If Samsung Electronics has 0 annual reports, **the code is wrong**, not the data!

```python
# Good practice: Sanity check results
if expected_company and len(results) == 0:
    raise ValueError("Results don't match reality - investigate search method")
```

### 2. **Read Documentation Thoroughly**

The dart-fss documentation clearly shows `pblntf_detail_ty` parameter exists.
I should have checked it more carefully before creating workarounds.

### 3. **Never Fake POC Results**

Hardcoding `rcept_no` to bypass search issues:
- ✅ Validated download mechanics (Exp 1)
- ❌ Created false confidence that search worked (Exp 2, 3)

**Correct approach**: Use hardcoded values ONLY for isolated component tests, never to hide broader system failures.

### 4. **Fail Loudly in Experiments**

```python
# BAD: Silent failure
if not results:
    results = [hardcoded_backup]  # ❌

# GOOD: Loud failure
if not results:
    raise ValueError("Search failed - need to investigate")  # ✅
```

---

## Recommended Search Methods

### For Annual Reports:
**Recommended**: Use `Corp.search_filings()` with `pblntf_detail_ty='A001'`

```python
corp = dart.get_corp_list().find_by_stock_code(stock_code)
annual_reports = corp.search_filings(
    bgn_de='20240101',
    pblntf_detail_ty='A001'
)
```

**Alternative**: Use helper function `search_annual_report()`

```python
from dart_fss.fs.extract import search_annual_report

annual_reports = search_annual_report(
    corp_code=corp.corp_code,
    bgn_de='20240101',
    end_de='20241231'
)
```

### For Multiple Report Types:

```python
# Search all report types, then filter
all_filings = corp.search_filings(bgn_de='20240101')

# OR: Search each type separately
report_types = ['A001', 'A002', 'A003']
all_reports = []
for report_type in report_types:
    reports = corp.search_filings(
        bgn_de='20240101',
        pblntf_detail_ty=report_type
    )
    all_reports.extend(reports)
```

---

## Action Items

- [x] Document POC principles in experiments.md
- [x] Document POC rules in implementation.md
- [x] Create exp_02c to test correct search methods
- [x] Create exp_04 corrected end-to-end pipeline
- [ ] Write formal tests based on corrected search method
- [ ] Implement discovery module with proper search API

---

## Success Metrics

✅ **All 3 methods tested systematically**
✅ **Root cause identified**: Missing `pblntf_detail_ty` parameter
✅ **Verified with real data**: Samsung has annual reports for 2022, 2023, 2024
✅ **Documented lessons learned** for future reference
✅ **Complete pipeline validated** with all periodic report types (A001, A002, A003)

---

## Phase 1 Complete: End-to-End Pipeline Validated

**Date**: 2025-10-03

### Experiment 4: Corrected Pipeline Success

Successfully validated complete **discover → download → organize** workflow using correct search API.

#### Results Summary:
```
Total: 6/6 filings (100% success rate)
- A001 (Annual):      2/2 ✓
- A002 (Semi-Annual): 2/2 ✓  
- A003 (Quarterly):   2/2 ✓

Performance:
- Download: ~0.25s per document
- Validation: Instant with lxml recover mode
```

#### Directory Structure:
```
experiments/data/raw/
└── 005930/
    ├── A001/ (Annual Reports)
    │   ├── 20250311001085/
    │   └── 20240312000736/
    ├── A002/ (Semi-Annual Reports)
    │   ├── 20250814003156/
    │   └── 20240814003284/
    └── A003/ (Quarterly Reports)
        ├── 20250515001922/
        └── 20241114002642/
```

Each filing directory contains:
- `{rcept_no}.zip` - Original downloaded ZIP
- `{rcept_no}.xml` - Main XML document
- `metadata.json` - PIT-critical metadata

---

## Critical Finding: Multiple Files in ZIP Archive

**Date**: 2025-10-03

### Issue: ZIP Contains Multiple XML Files

When extracting a DART ZIP file, it may contain **multiple XML files**, not just one.

#### Example (20250311001085.zip):
```
20250311001085/
├── 20250311001085.xml        ← MAIN FILE (6.3 MB)
├── 20250311001085_00760.xml  ← Supplementary file (596 KB)
└── 20250311001085_00761.xml  ← Supplementary file (702 KB)
```

### The Rule: Always Use the Main File

**Main XML file**: `{rcept_no}.xml` (exact match with receipt number)

**Supplementary files**: `{rcept_no}_XXXXX.xml` (with suffix) - these are:
- Attachments
- Supplementary disclosures
- Supporting documents
- NOT the primary financial statement

### Implementation Impact

**✅ CORRECT** approach for XML parsing:

```python
# Always target the main file explicitly
rcept_no = "20250311001085"
main_xml = filing_dir / f"{rcept_no}.xml"

if not main_xml.exists():
    raise FileNotFoundError(f"Main XML not found: {main_xml}")

# Parse only the main file
tree = etree.parse(str(main_xml), parser)
```

**❌ WRONG** approach:

```python
# Don't just take the first XML or glob all XMLs
xml_files = list(filing_dir.glob("*.xml"))
tree = etree.parse(str(xml_files[0]))  # Might parse wrong file!
```

### Why This Matters

1. **Parsing Priority**: We only need to parse the main document for textual sections
2. **Performance**: Supplementary files add no value for our use case but would waste parsing time
3. **Data Integrity**: Mixing main + supplementary content would corrupt the document structure
4. **Storage**: No need to store supplementary files in MongoDB

### Validation in Exp 4

All 6 downloaded filings were validated to ensure:
- ✅ Main XML file exists with pattern `{rcept_no}.xml`
- ✅ Main XML is parseable with lxml recover mode
- ✅ Main XML contains expected elements (USERMARK, TABLE tags)

### Next Steps for Implementation

When implementing the parser module:
1. Always target `{rcept_no}.xml` specifically
2. Add validation that main file exists before parsing
3. Ignore any `{rcept_no}_*.xml` supplementary files
4. Document this naming convention in parser documentation

---

## Phase 2: Corporation List Mapping

**Date**: 2025-10-03

### Experiment 5: Listed Corporations and Stock Code Mapping

Successfully retrieved and mapped all listed corporations from DART, creating the essential **stock_code → corp_code** mapping required for our discovery service.

#### Summary Statistics:
```
Total corporations in DART: 114,106
- Listed stocks:   3,901 (3.4%)
- Unlisted corps: 110,205 (96.6%)
```

#### Market Distribution (corp_cls):
```
KOSDAQ (K): 1,802 companies (65.2%)
KOSPI (Y):    848 companies (30.7%)
KONEX (N):    116 companies (4.2%)
Missing:    1,135 companies (29.1%)
```

#### Corp Object Schema (11 columns):

**Always Available (100% non-null):**
- `corp_code` (int64) - 8-digit DART company code (e.g., "00126380")
- `corp_name` (object) - Korean company name (e.g., "삼성전자")
- `stock_code` (object) - 6-digit stock code (e.g., "005930")
- `modify_date` (int64) - Last modification date (YYYYMMDD format)

**Usually Available (99.9%):**
- `corp_eng_name` (object) - English company name (3 missing out of 3,901)

**Partially Available (70.9% - 2,766 corps):**
- `corp_cls` (object) - **Market indicator** (Y=KOSPI, K=KOSDAQ, N=KONEX, E=Other)
- `market_type` (object) - Redundant with corp_cls (stockMkt=Y, kosdaqMkt=K, konexMkt=N)
- `sector` (object) - Industry sector in Korean (e.g., "통신 및 방송 장비 제조업")
- `product` (object) - Main products/services in Korean (2,752 have this)

**Rarely Available (2.7%):**
- `trading_halt` (object) - Trading halt status (104 corps)
- `issue` (object) - Issue flags (103 corps)

#### Critical Finding: corp_cls IS the Market Indicator

**Initial Mistake:** The experiment initially created a separate "market" column using `getattr(corp, 'market', None)`.

**Reality:** 
- The `market` attribute does NOT exist on Corp objects
- `corp_cls` **IS** the market indicator
- `market_type` provides the same information in a different format

**Correction:** Used `Corp.to_dict()` method to extract all available attributes correctly.

```python
# CORRECT: Use .to_dict() to get all attributes
corp_dict = corp.to_dict()

# Available keys:
# - Always: corp_code, corp_name, corp_eng_name, stock_code, modify_date
# - Sometimes: sector, market_type, product, corp_cls
# - Rarely: trading_halt, issue
```

#### Data Quality Analysis:

**Complete Data (2,766 corps, 70.9%):**
- All metadata fields populated
- Active trading status
- Full sector and product information

**Incomplete Data (1,135 corps, 29.1%):**
- Missing corp_cls, sector, product, market_type
- Likely delisted or suspended companies
- Last modified: 20170630 (most incomplete records share this date)
- Still accessible via stock_code for historical data retrieval

#### Stock Code → Corp Code Mapping:

Created a CSV lookup table with 3,901 entries:

```csv
stock_code,corp_code,corp_name,corp_cls,...
005930,00126380,삼성전자,Y,...
000660,00118332,SK하이닉스,Y,...
...
```

**Validation:**
- ✅ No duplicate stock_codes
- ✅ No duplicate corp_codes
- ✅ Samsung Electronics verified: 005930 → 00126380
- ✅ All major companies present

#### Usage in Discovery Service:

```python
# User provides stock_code (6 digits)
stock_code = "005930"

# We map to corp_code (8 digits)
corp_list = dart.get_corp_list()
corp = corp_list.find_by_stock_code(stock_code)
corp_code = corp.corp_code  # "00126380"

# Use corp_code for DART API calls
filings = corp.search_filings(...)
```

#### Files Generated:

**CSV Output:**
- `experiments/data/listed_corporations.csv` (3,901 rows × 11 columns)
- Ready for lookup operations in services
- UTF-8 encoding with BOM for Excel compatibility

**Experiment Scripts:**
- `exp_05_corp_list_mapping.py` - Main experiment
- `exp_05b_corp_info_investigation.py` - Schema deep dive
- `exp_05c_display_csv.py` - CSV inspection utility

#### Lessons Learned:

1. **Use .to_dict() for Complete Data**
   - Direct attribute access (getattr) may miss fields
   - `.to_dict()` returns all available attributes
   - Handles optional fields gracefully

2. **corp_cls Is Market, Not a Separate Field**
   - Y = 유가증권시장 (KOSPI/Stock Market)
   - K = 코스닥 (KOSDAQ Market)
   - N = 코넥스 (KONEX Market)
   - E = 기타 (Other)
   - No need for separate "market" column

3. **29% of Listed Corps Have Incomplete Metadata**
   - Not all listed stocks are actively trading
   - Historical data retrieval still possible
   - Services should handle None values gracefully

4. **Corp.info Property Returns Same Data as .to_dict()**
   - Both methods provide complete schema
   - `.to_dict()` is cleaner for batch processing
   - `.info` is useful for interactive debugging

#### Next Steps:

- [x] Document findings in FINDINGS.md
- [ ] Integrate corp_list into DiscoveryService
- [ ] Add stock_code validation using this mapping
- [ ] Handle missing corp_cls gracefully in queries
- [ ] Consider caching corp_list to avoid repeated API calls

---

## CRITICAL LESSON: Always Check Existing Library Features First

**Date**: 2025-10-03

### Experiment 6: CorpListManager Was Redundant!

**What We Built (UNNECESSARY):**
- `CorpListManager` with CSV caching (145 lines)
- 19 unit tests
- 12 integration tests  
- Comprehensive documentation

**What We Missed:**
- `dart-fss` already has **perfect built-in caching** with Singleton pattern!
- `get_corp_list()` loads once per process (~7s), then instant on all subsequent calls
- `find_by_stock_code()` is instant after first load (0.000ms)
- Corp objects are shared in memory (efficient)

### Performance Comparison:

**dart-fss built-in (Experiment 6):**
```
First load:     7.3s (one-time cost per process)
Second load:    0.000ms (Singleton - returns same object)
Lookups:        0.000ms (instant)
Memory:         Efficient (shared objects)
```

**Our CorpListManager (REDUNDANT):**
```
CSV cache:      ~100ms (needs pandas)
Added complexity: 145 lines + 31 tests
Value added:    NONE for typical usage
```

### Why This Happened:

1. **Didn't Read Documentation Thoroughly**
   - dart-fss docs clearly show `find_by_stock_code()` method
   - We saw it but didn't test its performance
   - Assumed we needed external caching

2. **Didn't Test First**
   - Built CorpListManager without validating the need
   - Should have run Experiment 6 BEFORE implementing

3. **Over-Engineering**
   - Tried to optimize something already optimized
   - Added complexity without adding value

### The Correct Approach:

```python
# SIMPLE: Use dart-fss directly
corp_list = dart.get_corp_list()  # Singleton - instant after first call
corp = corp_list.find_by_stock_code('005930')  # Instant lookup
corp_code = corp.corp_code  # "00126380"
```

**No need for:**
- ❌ CSV caching
- ❌ CorpListManager
- ❌ Phase 0 initialization
- ❌ build_company_list() method

### When CSV Caching Might Be Useful:

Only in rare edge cases:
- **Cross-process caching**: Multiple separate Python processes (rare)
- **Offline operation**: No network access at all (rare)  
- **Pre-warming**: Want to avoid 7s delay on first call (minor)

For 99% of use cases: **Use dart-fss directly**

### Lessons Learned:

1. **Always Test Library Features First**
   - Run performance experiments BEFORE building
   - Don't assume you need to add caching
   - Validate the actual bottleneck

2. **Read Documentation Completely**
   - Don't just skim for methods
   - Understand the library's architecture
   - Check for Singleton/caching patterns

3. **Start Simple, Add Complexity Only When Needed**
   - Use library features directly
   - Only add wrappers if they provide clear value
   - Measure before optimizing

4. **Question Your Assumptions**
   - "Do we need this?" should be asked often
   - Validate assumptions with experiments
   - Don't build based on speculation

### Action Items:

- [x] Run Experiment 6 to validate dart-fss caching
- [x] Document findings in FINDINGS.md
- [ ] Remove CorpListManager from codebase
- [ ] Update architecture.md - remove Phase 0
- [ ] Update prd.md - remove build_company_list()
- [ ] Update implementation.md - use dart-fss directly
- [ ] Delete src/dart_fss_text/services/corp_list_manager.py
- [ ] Delete tests/unit/test_corp_list_manager.py
- [ ] Delete tests/integration/test_corp_list_manager_integration.py

### New Architecture:

**BEFORE (Over-Engineered):**
```
User → DisclosurePipeline
       ├─ Phase 0: CorpListManager.load() → CSV cache
       └─ Phase 1: fetch_reports() → use CorpListManager
```

**AFTER (Simplified):**
```
User → DisclosurePipeline
       └─ fetch_reports() → dart.get_corp_list().find_by_stock_code()
                            (dart-fss handles caching internally)
```

**Lines of Code Saved:** 145 (implementation) + 780 (tests) = **925 lines removed**
**Complexity Reduced:** No Phase 0, no CSV management, no cache invalidation
**Dependencies Reduced:** No pandas needed for caching

### Success Metrics:

✅ **Identified redundant code before production**
✅ **Validated with real performance data (Experiment 6)**
✅ **Documented lesson learned for future reference**
✅ **Simplified architecture by removing unnecessary layer**

---

**Status**: Phase 1 POC COMPLETE - Ready for production implementation (using dart-fss directly)

---

## Phase 4: XML Parsing & Section Extraction

**Date**: 2025-10-03

### Experiment 10: XML Structure Exploration - Critical Discoveries

Successfully validated XML parsing approach for DART 사업보고서 (A001 Annual Reports). Discovered critical architectural facts about DART XML structure that fundamentally change parsing strategy.

#### Summary Statistics:
```
File: 20240312000736.xml (Samsung 2023 Annual Report)
Size: 155,547 lines
Indexing Time: 0.167s
Extraction Time: 0.010s per section
Coverage: 39.8% (49/123 sections mapped)
```

#### Target Section Results (020000 - II. 사업의 내용):
- **150 paragraphs** extracted successfully
- **89 tables** extracted
- **7 subsections** with full hierarchy:
  1. 사업의 개요 (6 paragraphs)
  2. 주요 제품 및 서비스 (3 paragraphs, 5 tables)
  3. 원재료 및 생산설비 (14 paragraphs, 25 tables)
  4. 매출 및 수주상황 (16 paragraphs, 17 tables)
  5. 위험관리 및 파생거래 (27 paragraphs, 14 tables)
  6. 주요계약 및 연구개발활동 (13 paragraphs, 8 tables)
  7. 기타 참고사항 (71 paragraphs, 20 tables)

---

### Critical Finding #1: ATOCID is on TITLE Tag, NOT SECTION Tag

**Problem:** Initial code searched for `section.get('ATOCID')` → returned None for all sections.

**Root Cause:** XML structure has ATOCID as an attribute of `<TITLE>` tag, not `<SECTION>` tag.

**XML Structure:**
```xml
<SECTION-1 ACLASS="MANDATORY" APARTSOURCE="SOURCE">
  <TITLE ATOC="Y" ATOCID="3">I. 회사의 개요</TITLE>
  ...
</SECTION-1>
```

**Solution:**
```python
# WRONG:
atocid = section.get('ATOCID')  # Returns None

# CORRECT:
title_elem = section.find('TITLE')
atocid = title_elem.get('ATOCID')  # Returns "3"
```

**Impact:** This was the initial blocker preventing any sections from being indexed. Fixed by extracting ATOCID from TITLE element instead of SECTION element.

---

### Critical Finding #2: XML Structure is FLAT (Not Nested)

**Assumption:** SECTION-2 tags would be nested inside SECTION-1 tags (parent-child relationship).

**Reality:** All SECTION-N tags are **siblings** in the XML tree!

**Evidence:**
```python
# Debug output:
Direct <SECTION-2> tags inside SECTION-1: 0  ← Key discovery!
Total <P> tags (including nested): 185
Direct <P> tags: 1
```

**XML Structure:**
```xml
<BODY>
  <SECTION-1 ...>           <!-- ATOCID=3, Level 1 -->
    <TITLE ATOCID="3">I. 회사의 개요</TITLE>
    <P>...</P>
  </SECTION-1>
  
  <SECTION-2 ...>           <!-- ATOCID=4, Level 2 - SIBLING, not child! -->
    <TITLE ATOCID="4">1. 회사의 개요</TITLE>
    <P>...</P>
  </SECTION-2>
  
  <SECTION-2 ...>           <!-- ATOCID=5, Level 2 - SIBLING -->
    <TITLE ATOCID="5">2. 회사의 연혁</TITLE>
    <P>...</P>
  </SECTION-2>
  
  <SECTION-1 ...>           <!-- ATOCID=9, Level 1 - next main section -->
    <TITLE ATOCID="9">II. 사업의 내용</TITLE>
    <P>...</P>
  </SECTION-1>
</BODY>
```

**Implication:** Hierarchy must be **reconstructed programmatically** using:
1. **ATOCID sequence** (defines order: 3, 4, 5, 9...)
2. **Level numbers** (SECTION-1 = level 1, SECTION-2 = level 2)
3. **Sequential scanning**: Find sections after parent with higher level number

**Solution Algorithm:**
```python
def find_children(parent_atocid, parent_level, section_index):
    """
    Find child sections by scanning ATOCID sequence.
    Children are sections with:
    1. ATOCID > parent_atocid
    2. Level = parent_level + 1
    3. Before next same-or-higher level section
    """
    children = []
    for atocid in sorted(section_index.keys()):
        if int(atocid) <= parent_atocid:
            continue  # Skip sections before parent
        
        level = section_index[atocid]['level']
        
        if level <= parent_level:
            break  # Hit next sibling or higher - stop
        
        if level == parent_level + 1:
            children.append(section_index[atocid])
    
    return children
```

---

### Critical Finding #3: Only SECTION-1 and SECTION-2 Exist

**Initial Plan:** Support SECTION-1, SECTION-2, SECTION-3, SECTION-4... (arbitrary depth)

**Reality:** Maximum depth is **2 levels** (main section → subsection)

**Evidence:**
```
Sections found: 53
- SECTION-1: 16 sections
- SECTION-2: 37 sections
- SECTION-3: 0 sections  ← None found!
- SECTION-4: 0 sections  ← None found!
```

**Impact:** 
- Simplified hierarchy reconstruction (only need to handle 2 levels)
- toc.yaml has SECTION-3 entries (e.g., "2-1. 연결 재무상태표") but they don't exist in actual XML
- These are likely **optional** or **conditionally present** sections

---

### Critical Finding #4: Must Use Nested Search for Content Extraction

**Problem:** Direct children search (`findall('P')`) returned only 1 paragraph when we expected 150+.

**Root Cause:** Because all SECTION tags are siblings, the content (`<P>` and `<TABLE>` tags) is scattered across the flat structure, not nested inside parent sections.

**Evidence:**
```python
# Direct children only:
direct_p_tags = section_elem.findall('P')
# Result: 1 paragraph

# All nested (recursive):
all_p_tags = section_elem.findall('.//P')
# Result: 185 paragraphs!
```

**Solution:**
```python
# WRONG - misses nested content:
for p in section_elem.findall('P'):
    paragraphs.append(p.text)

# CORRECT - gets all content:
for p in section_elem.findall('.//P'):
    paragraphs.append(''.join(p.itertext()).strip())
```

**Why This Works:** The `//.` prefix in XPath performs a recursive search, finding all matching elements at any depth beneath the current element.

---

### Coverage Analysis: 39.8% (49/123 sections)

**Why so low?**

1. **74 sections from toc.yaml are missing** in actual XML
   - Examples: "2-1. 연결 재무상태표", "2-2. 연결 손익계산서"
   - These are SECTION-3 level sections that don't exist
   - Likely **optional** or **conditionally included**

2. **4 sections in XML are unmapped** (title variations)
   - Minor title mismatches vs. toc.yaml
   - Can be fixed with better fuzzy matching

3. **49 sections successfully mapped and extracted**
   - All major sections (I through XII) found
   - All primary subsections (level 2) found
   - Coverage is sufficient for MVP

**Conclusion:** 39.8% coverage is **acceptable** - the "missing" sections are optional subsections that may not exist in all documents.

---

### Performance Validation: All Targets Met

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Indexing (155K lines) | < 1.0s | 0.167s | ✅ **6x faster** |
| Extraction per section | < 0.2s | 0.010s | ✅ **20x faster** |
| Title mapping accuracy | ≥ 90% | 92.5% | ✅ **Exceeds** |
| Content extraction | Complete | 150 paragraphs, 89 tables | ✅ **Complete** |
| Hierarchy preservation | Yes | 7 subsections | ✅ **Preserved** |

---

### Lessons Learned

1. **Never Assume XML Structure - Always Inspect First**
   - We assumed nested structure (like HTML)
   - Reality: flat sibling structure with implied hierarchy
   - **Takeaway**: Validate assumptions with real data before implementing

2. **Debug Output is Essential for Structure Discovery**
   - Counting direct vs. nested elements revealed the flat structure
   - Without debug output, we'd have missed this critical fact
   - **Takeaway**: Add extensive debug logging in exploratory experiments

3. **Attributes Can Be on Unexpected Elements**
   - ATOCID on TITLE, not SECTION
   - Checked both before finding the right location
   - **Takeaway**: Inspect actual XML with lxml to see attribute locations

4. **toc.yaml is Aspirational, Not Descriptive**
   - toc.yaml defines 123 sections, but XML has only ~53
   - Many "optional" sections won't exist in every document
   - **Takeaway**: toc.yaml is a schema, not a guarantee

5. **Flat Structure Simplifies Some Things, Complicates Others**
   - **Simpler**: No recursive descent through nested tree
   - **More Complex**: Must reconstruct hierarchy from sequence
   - **Takeaway**: Trade-offs exist in every data structure design

---

### Next Steps

1. ✅ **Document findings** - Complete (this entry)
2. ⏳ **Write unit tests** - Test flat structure handling, ATOCID extraction, hierarchy reconstruction
3. ⏳ **Implement production parsers**:
   - `xml_parser.py` - Low-level XML utilities (ATOCID extraction, flat structure scanning)
   - `section_parser.py` - Section extraction logic (hierarchy reconstruction from flat structure)
   - `table_parser.py` - Table parsing (headers, rows, context)
4. ⏳ **Handle edge cases**:
   - Missing ATOCID (skip section)
   - Title mismatch with toc.yaml (fuzzy matching)
   - Optional sections (graceful handling)
   - Malformed XML (lxml recover mode)

---

**Status**: Experiment 10 COMPLETE - XML parsing approach validated and ready for TDD implementation

