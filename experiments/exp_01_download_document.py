"""
OBSOLETE EXPERIMENT - LESSONS LEARNED
======================================

Original Goal: Validate Basic Document Download Mechanics
Date Created: 2025-10-02
Status: ✅ VALIDATED - Superseded by exp_07_search_download_organize.py

WHAT THIS EXPERIMENT ACHIEVED:
-------------------------------
Successfully validated the basic download workflow:
1. Load API key from .env
2. Download document ZIP using dart-fss.api.filings.download_document()
3. Extract ZIP archive to get XML file
4. Parse XML with both ElementTree and lxml (recover mode for malformed XML)
5. Quick sanity checks on XML structure

KEY FINDINGS:
-------------
1. **Download API Works**: dart-fss.api.filings.download_document() is reliable
   - Downloads to specified path as {rcept_no}.zip
   - Typical file size: 0.5-2 MB
   - Download time: 1-3 seconds

2. **ZIP Structure**: Archives contain single XML file
   - Filename matches rcept_no: {rcept_no}.xml
   - No nested directories

3. **XML Parsing**: DART XMLs can be malformed
   - Standard ElementTree may fail
   - lxml with recover=True handles malformed XML gracefully
   - Recommended: Use lxml parser for production

4. **XML Structure**: Documents contain expected elements
   - <P> tags for paragraphs
   - <TABLE> tags for tables
   - Elements with USERMARK attribute for section identification
   - Typical document: 10,000-50,000 total elements, 100-500 USERMARK elements

WHAT WE LEARNED:
----------------
1. **Parsing Strategy**: Always use lxml with recover mode for DART documents
   ```python
   from lxml import etree
   parser = etree.XMLParser(recover=True, encoding='utf-8')
   tree = etree.parse(xml_path, parser)
   ```

2. **Error Handling**: DART XMLs can be malformed, so:
   - Don't rely on strict XML validation
   - Use forgiving parser (lxml recover mode)
   - Log parsing warnings but don't fail the pipeline

3. **File Organization**: Simple extraction works
   - No complex ZIP structures to handle
   - Direct extraction to target directory is sufficient

WHY THIS IS NOW OBSOLETE:
--------------------------
This experiment validated basic download mechanics in isolation. Now we have:

1. **More Comprehensive Testing**: exp_07_search_download_organize.py tests the
   complete pipeline (search → download → organize → cleanup) with PIT-aware
   directory structure.

2. **Production Implementation**: Phase 1 (Filing Discovery) is complete with
   full test coverage. Phase 2 (Document Download) will build on exp_07.

3. **Formal Tests**: Unit and integration tests now cover download mechanics
   with proper mocking and validation.

REPLACEMENT:
------------
For complete download workflow, use:
→ experiments/exp_07_search_download_organize.py

For production implementation:
→ src/dart_fss_text/services/download_service.py (Phase 2, TODO)

See also:
→ experiments/FINDINGS.md for complete experiment analysis
→ docs/vibe_coding/architecture.md for Phase 2 architecture

KEY TAKEAWAY:
-------------
**Always use lxml with recover=True for parsing DART XML documents.**

DART documents can have malformed XML that breaks strict parsers. Using a
forgiving parser prevents pipeline failures while still extracting valid content.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file kept as lessons learned reference. Do not execute.
Use exp_07_search_download_organize.py for complete download workflow.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Original code removed - see git history if needed
