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

**Status**: Phase 1 POC COMPLETE - Ready for production implementation

