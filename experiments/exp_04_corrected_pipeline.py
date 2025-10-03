"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original Goal: Validate Complete Discovery → Download → Organize Workflow
Date Created: 2025-10-02
Status: ✅ VALIDATED - Superseded by exp_07_search_download_organize.py

WHAT THIS EXPERIMENT ACHIEVED:
-------------------------------
First WORKING end-to-end pipeline after fixing the search bug in exp_02c.

Successfully tested:
1. Search filings with CORRECT method (pblntf_detail_ty parameter)
2. Download ZIP files for multiple report types
3. Extract XML documents
4. Organize in structured directory: data/raw/{stock_code}/{report_type}/{rcept_no}/
5. Save metadata.json for each filing
6. Quick XML validation with lxml

KEY FINDINGS:
-------------
1. **Pipeline Works End-to-End**: With correct search, the full workflow succeeds
   - Search: Found filings for all 3 periodic report types
   - Download: Successfully downloaded ZIP files
   - Extract: Extracted XML from ZIPs
   - Validate: XML parsing confirmed document structure

2. **Directory Structure** (v1 - before PIT-aware):
   ```
   data/raw/
     {stock_code}/
       {report_type}/        # A001, A002, A003
         {rcept_no}/
           {rcept_no}.xml
           metadata.json
         {rcept_no}.zip       # Kept for debugging
   ```

3. **Metadata Captured**:
   ```json
   {
     "rcept_no": "20240312000736",
     "stock_code": "005930",
     "corp_name": "삼성전자",
     "corp_code": "00126380",
     "report_type_code": "A001",
     "report_type_name": "사업보고서",
     "report_nm": "사업보고서 (2023.12)",
     "rcept_dt": "20240312",
     "download_timestamp": "2025-10-02T15:30:45",
     "zip_path": "005930/A001/20240312000736.zip",
     "xml_path": "005930/A001/20240312000736/20240312000736.xml",
     "status": "success"
   }
   ```

4. **Performance**:
   - Samsung (3 report types, 2 each = 6 total filings)
   - Total time: ~30 seconds
   - Average: ~5 seconds per filing (download + extract + validate)

WHAT WE LEARNED:
----------------
1. **Build on Working Foundation**: This experiment ONLY worked because we
   fixed search first in exp_02c. Never build complex pipelines on broken
   components!

2. **Sanity Checks at Each Stage**:
   ```python
   # After search
   if len(filings) == 0:
       raise ValueError("No filings found - cannot proceed")
   
   # After download
   if not zip_path.exists():
       raise FileNotFoundError("Download failed")
   
   # After extraction
   if not xml_file.exists():
       raise FileNotFoundError("Extraction failed")
   ```

3. **Idempotency**: Check if files already exist before re-downloading
   ```python
   if zip_path.exists():
       print("ZIP already exists, skipping download")
   ```

4. **Error Resilience**: One filing failure shouldn't stop entire pipeline
   - Catch exceptions per-filing
   - Log errors and continue
   - Report summary at end

LIMITATIONS (Why Superseded by exp_07):
----------------------------------------
1. **Directory Structure Not PIT-Aware**:
   - Organized by stock_code/report_type
   - Should be year/corp_code for Point-in-Time correctness
   - Year should come from rcept_dt (publication date), not report period

2. **Not Production-Ready**:
   - No ZIP cleanup after extraction
   - Metadata structure not finalized
   - Error handling could be better
   - No retry logic for network failures

3. **Limited Testing**:
   - Only tested with Samsung Electronics
   - Only tested 2 filings per report type
   - Didn't test edge cases (missing fields, malformed XML, etc.)

WHY THIS IS NOW OBSOLETE:
--------------------------
1. **Better Version Exists**: exp_07_search_download_organize.py is the
   improved version with:
   - PIT-aware directory structure (year/corp_code/rcept_no)
   - ZIP cleanup after extraction
   - Better error handling
   - More comprehensive testing
   - Documented for Phase 2 implementation

2. **Production Code Coming**: Phase 2 (Document Download) will implement:
   - DocumentDownloadService
   - FilesystemCache with PIT-aware structure
   - Proper retry logic and error handling
   - Full test coverage

REPLACEMENT:
------------
For pipeline testing:
→ experiments/exp_07_search_download_organize.py (improved version)

For Phase 2 implementation:
→ src/dart_fss_text/services/download_service.py (TODO)
→ src/dart_fss_text/storage/filesystem_cache.py (TODO)

See also:
→ experiments/FINDINGS.md for complete analysis
→ docs/vibe_coding/architecture.md for Phase 2 architecture
→ docs/vibe_coding/architecture.md#file-system-structure for PIT-aware structure

KEY TAKEAWAY:
-------------
**Point-in-Time (PIT) correctness requires organizing files by publication date.**

Directory structure should be: `data/raw/{year}/{corp_code}/{rcept_no}.xml`

Where {year} comes from rcept_dt (publication date), NOT the report period.

Example:
- FY 2023 Annual Report published on 2024-03-12
- Should go in: `data/raw/2024/00126380/20240312000736.xml`
- NOT in: `data/raw/2023/...` (that would be forward-looking bias!)

This ensures that when querying historical data, you only access information
that was publicly available at that point in time.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file kept as lessons learned reference. Do not execute.
Use exp_07_search_download_organize.py for pipeline testing.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Original code removed - see git history if needed
