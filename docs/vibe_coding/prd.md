# Product Requirements Document: dart-fss-text

## Executive Summary

**dart-fss-text** is a Python library that extends the capabilities of **dart-fss** by providing structured access to textual data from Korean financial statements. While dart-fss excels at retrieving **numerical financial data** (balance sheets, income statements, cash flows) and XBRL-formatted data, textual narratives from disclosure documents remain largely untapped. This library fills that gap by offering a clean, intuitive API for discovering, downloading, parsing, and storing financial statement narratives in a structured database.

---

## Problem Statement

### Current Limitations

1. **dart-fss Focus Mismatch**: The dart-fss library focuses on numerical financial statements and XBRL data. While it can download XML disclosure documents via `download_document()`, it provides no support for extracting or structuring the textual content within.
2. **No Discovery/Filtering API**: Users must manually search for relevant filings, track metadata (published date, amended date), and ensure point-in-time (PIT) data integrity.
3. **Complex XML Parsing**: The DART XML format contains nested elements, tables, and markup that requires domain knowledge to navigate effectively.
4. **No Storage Layer**: Extracted text has nowhere to go—no standardized schema or database for persistence, versioning, or downstream NLP tasks.
5. **Repetitive Boilerplate**: Every project reinvents the wheel for discovery, download, parsing, and storage.

### User Pain Points

- Quantitative analysts need narrative sections to complement numerical data
- Researchers require structured access to business descriptions and risk disclosures
- Financial engineers want to incorporate textual features into their models without dealing with XML parsing complexity

---

## Solution Overview

**dart-fss-text** provides an end-to-end pipeline for textual financial data: **discover → download → parse → store → query**. It leverages dart-fss for API authentication and company code management, then builds a complete workflow for textual disclosure documents.

The library is designed with **explicit database control** - users connect to their database first, then inject that connection into the pipeline and query components. This ensures users can verify their database setup before processing any data.

### Key Differentiators

- **Complete Pipeline**: From filing discovery to database storage—not just parsing
- **Explicit Database Control**: Database connection managed separately, then injected into pipeline and query components
- **Point-in-Time Aware**: Tracks published/amended dates to ensure proper temporal alignment
- **NoSQL Database**: MongoDB backend for flexible storage, versioning, and vector embedding support
- **Semantic Parsing**: Identifies document sections by their financial reporting meaning (e.g., "business overview", "risk factors")
- **Complementary to dart-fss**: Focuses on textual narratives while dart-fss handles numerical statements
- **NLP-Ready**: Structured storage enables downstream tasks (embeddings, sentiment analysis, topic modeling)

---

## Objectives & Success Criteria

### Primary Objectives

1. **Complete Data Pipeline**: Reduce the time from "I need company X's disclosures" to "structured data in database" from days to minutes
2. **Ensure PIT Integrity**: Track all temporal metadata (published, amended dates) to prevent forward-looking bias in quantitative models
3. **Enable NLP Workflows**: Provide storage layer that seamlessly integrates with embedding models and vector databases
4. **Standardize Access Patterns**: Consistent APIs for filtering, downloading, parsing, and querying
5. **Maintain Quality**: Preserve semantic structure and relationships in the original documents

### Success Metrics

- Users can go from company list to populated database with < 20 lines of code
- API covers ≥ 80% of commonly requested textual sections
- Zero data loss compared to manual parsing
- 100% PIT-correct metadata tracking
- Compatible with dart-fss ≥ 0.4.14
- Database schema supports vector embeddings without migrations

---

## Target Users & Use Cases

### Primary Users

1. **Quantitative Analysts**: Building multi-factor models that incorporate textual features (sentiment, topic modeling)
2. **Financial Researchers**: Conducting academic studies on disclosure quality, management tone, or industry trends
3. **Data Scientists**: Creating datasets for NLP models trained on Korean financial text
4. **Compliance Teams**: Monitoring changes in risk disclosures or business descriptions over time

### Core Use Cases

#### Use Case 1: Fetch and Store Reports

```python
from dart_fss_text import StorageService, DisclosurePipeline

# Step 1: Establish database connection explicitly
storage = StorageService()  # Reads from .env or config
# User can verify connection before proceeding

# Step 2: Initialize pipeline with storage connection
pipeline = DisclosurePipeline(storage_service=storage)

# Step 3: Fetch, parse, and store reports
stats = pipeline.download_and_parse(
    stock_codes=["005930", "000660"],  # Samsung, SK Hynix
    years=[2023, 2024],
    report_type="A001"  # Annual Report
)

# Returns statistics: {'reports': 4, 'sections': 194, 'failed': 0}

# Note: dart-fss handles company lookup automatically
# First call: ~7s to load corp list, subsequent calls: instant (cached)
```

#### Use Case 2: Query Stored Text

```python
from dart_fss_text import StorageService, TextQuery

# Connect to database containing parsed sections
storage = StorageService()

# Initialize query interface
query = TextQuery(storage_service=storage)

# Retrieve specific sections across companies and time
result = query.get(
    stock_codes=["005930", "000660"],  # Samsung, SK Hynix
    years=[2023, 2024],
    section_codes="020100"  # Business overview section
)

# Result structure: {year: {stock_code: Sequence}}
# Access text for Samsung 2024
samsung_2024 = result["2024"]["005930"]
print(f"Text: {samsung_2024.text[:200]}...")
print(f"Sections: {samsung_2024.section_count}")
```

#### Use Case 3: NLP Integration

```python
from dart_fss_text import StorageService, TextQuery
from sentence_transformers import SentenceTransformer

# Connect to database
storage = StorageService()
query = TextQuery(storage_service=storage)

# Load embedding model
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Retrieve business descriptions across multiple years
result = query.get(
    stock_codes="005930",
    years=[2020, 2021, 2022, 2023, 2024],
    section_codes="020100"  # Business overview
)

# Generate embeddings for time series analysis
for year, companies in result.items():
    sequence = companies["005930"]
    embedding = model.encode(sequence.text)
    # Store embeddings for semantic similarity analysis
    # ... downstream NLP workflows ...
```

---

## Key Features

> **Technical Details**: For system architecture, data models, and technical design patterns, see **[architecture.md](architecture.md)**.

### Discovery & Download Pipeline (MVP)

**Company Lookup**: Handled automatically by dart-fss

- dart-fss provides `get_corp_list()` with **Singleton pattern**
- First call: ~7s to load 114,106+ corporations  
- Subsequent calls: **instant** (returns same cached object)
- `find_by_stock_code()`: **instant** lookup (0.000ms)
- **No external caching needed** - dart-fss handles it perfectly

**Validated in Experiment 6**: dart-fss's built-in caching eliminates need for CSV caching layer

---

### Filing Discovery & Filtering

1. **Complete Pipeline Orchestration**
   - **Design Philosophy**: Users first establish explicit database connection, then inject it into pipeline components
   - **Primary Method**: `pipeline.download_and_parse()` handles the full workflow: search → download → parse → store
   - **Input Parameters**: Stock codes, years/date ranges, report types
   - **Return Value**: Statistics dictionary with counts of reports processed, sections stored, and failures
   - **Separation of Concerns**: 
     - `StorageService`: Database connection (explicit, verifiable)
     - `DisclosurePipeline`: Orchestrates discovery, download, parsing, storage (injected storage)
     - `TextQuery`: Retrieves parsed data from database (injected storage)

2. **Discovering Available Report Types**
   - Users discover valid codes via existing `ReportTypes` helper class:
   ```python
   from dart_fss_text import ReportTypes
   
   # List all available types
   ReportTypes.list_available()
   # → {'A001': '사업보고서', 'A002': '반기보고서', ...}
   
   # Get only periodic reports
   ReportTypes.list_periodic()
   # → {'A001': '사업보고서', 'A002': '반기보고서', 'A003': '분기보고서'}
   ```
   
3. **Additional Helper Methods**
   - `get_company_info(stock_code)`: Retrieve company metadata via `dart.get_corp_list().find_by_stock_code()`
   - `preview_filings(filters)`: Show matching filings before download (with metadata)

4. **Metadata Management (PIT-Critical)**
   - Track **published_date** (original disclosure date)
   - Track **amended_date** (if document was corrected/updated)
   - Track **download_timestamp** (when we retrieved it)
   - Store **rcept_no** (DART document ID)
   - Store **stock_code**, **company_name**
   - This ensures point-in-time (PIT) integrity for backtesting and research

5. **Document Download & Storage**
   - Use `dart_fss.api.filings.download_document()` for retrieval
   - Automatic unzipping and XML extraction
   - Store raw XML in local filesystem with PIT-aware directory structure:

     ```
     data/
       raw/
         {year}/              # Year from rcept_dt (receipt/publication date)
           {corp_code}/       # Company code (not stock code, for uniqueness)
             {rcept_no}.xml
     ```

   - **Rationale**: Using `rcept_dt` year ensures PIT correctness. A 2022 FY report published in March 2023 (rcept_dt=20230307) should be in `2023/` folder, as that's when it became publicly available.
   - Track download status in metadata database

### XML Parsing & Structuring

6. **Section Identification**
   - Detect major sections using `USERMARK` attributes (e.g., `USERMARK="F-14 B"`)
   - Map USERMARK patterns to semantic section names
   - Handle variations in formatting across different filing types

7. **Text Extraction**
   - Clean text extraction from `<P>`, `<SPAN>`, and other text elements
   - Preserve paragraph boundaries and semantic structure
   - Handle special characters and encoding issues

8. **Table Parsing**
   - Extract tables (`<TABLE>`) with headers and data rows
   - Convert to structured dict (ready for MongoDB)
   - Maintain relationships between tables and their surrounding context

### Database Layer

9. **MongoDB Schema Design**
   - **Collections**:
     - `filings_metadata`: Tracks all downloaded filings (PIT metadata)
     - `document_sections`: Stores parsed sections with text and tables
     - `embeddings`: Stores vector embeddings for semantic search (optional)

10. **CRUD Operations**
   - Insert parsed documents with full metadata
   - Query by stock_code, date range, section name
   - **PIT queries**: Filter by `as_of_date` to ensure temporal correctness
   - Update embeddings without re-parsing documents

11. **Data Versioning**
    - Handle amended filings by storing multiple versions
    - Track parsing pipeline version (for reproducibility)

### Advanced Parsing

12. **Subsection Parsing**
    - Identify hierarchical structure (e.g., DX 부문, DS 부문 within 주요 사업의 내용)
    - Create nested data structures reflecting document organization

13. **Cross-Reference Resolution**
    - Parse references like "Ⅱ. 사업의 내용"
    - Link related sections

### Analytics & NLP

14. **Time-Series Analysis**
    - Compare sections across multiple filings
    - Track changes over time (diff functionality)
    - Visualize disclosure evolution

15. **NLP Preprocessing Pipeline**
    - Tokenization optimized for Korean financial text
    - Named entity recognition (company names, products, financial terms)
    - Sentence boundary detection

16. **Embedding & Semantic Search**
    - Generate embeddings for all sections
    - Store in MongoDB with vector search support
    - Semantic similarity queries across companies/time

---

## Non-Goals

**Out of Scope for This Library:**

1. **Financial Statement Numbers**: dart-fss already provides excellent APIs for numerical data (XBRL, financial statements)—we won't duplicate this
2. **PDF Rendering**: We work with the XML source, not visual representations
3. **Translation**: Text remains in original Korean (users can integrate translation separately)
4. **OCR or Image Processing**: We only handle structured XML, not scanned documents
5. **Real-Time Alerts**: No push notifications for new filings (users can build this on top)

---

## Known Limitations (MVP Scope)

### Multiple Report Versions (Amendments) - Latest Only

**Issue**: Companies often file **amended reports** (기재정정) for the same fiscal year—e.g., an original filing in March, then a correction in June.

**MVP Behavior**: When multiple reports exist for the same company/year, `TextQuery.get()` returns **only the latest version** (highest `rcept_no`).

**Example**:
```python
# SK Hynix filed 2 reports for 2017 fiscal year:
# - 20180402004745 (April 2, 2018): Original
# - 20180615000111 (June 15, 2018): Amendment [기재정정]

# Query returns ONLY the June 15 version
result = query.get(stock_codes="000660", years=2018, section_codes="020000")
# result["2018"]["000660"].metadata.rcept_no == "20180615000111"
```

**Why This Limitation Exists**:

1. **MVP Focus on 사업의 내용 (Business Description)**
   - Section 020000 is rarely amended (business model rarely changes)
   - Amendments typically affect financial numbers, governance, or compliance sections
   - For our MVP use case, latest version is sufficient

2. **Complexity vs. Benefit Trade-off**
   - Full version management requires:
     - Schema changes (`filing_date`, `filing_sequence`, `is_amendment`, `supersedes_rcept_no`)
     - Query API enhancements (version selection, PIT queries with `as_of_date`)
     - Complex test coverage across all version scenarios
   - Benefit for MVP use case: **Minimal** (amendments don't materially affect 사업의 내용)

**Impact**:
- ✅ **Most users unaffected**: Get corrected/updated text automatically
- ❌ **Forward-looking bias possible**: Cannot retrieve original filing for true point-in-time (PIT) analysis
- ❌ **Amendment visibility**: Cannot compare what changed between versions

**Workaround for PIT-Critical Research**:
```python
# Current workaround: Query database directly by rcept_no
sections = storage.get_report_sections(rcept_no="20180402004745")  # Original filing
```

**Future Enhancement** (Post-MVP, Phase 7):

```python
# Proposed API for full version management
result = query.get(
    stock_codes="000660",
    years=2018,
    section_codes="020000",
    version="original"  # Options: "latest" (default), "original", "all"
)

# Or PIT query
result = query.get(
    stock_codes="000660",
    years=2018,
    section_codes="020000",
    as_of_date="20180430"  # Return version available on April 30, 2018
)
```

**Design Rationale**: 
- **Pragmatic MVP**: Deliver core value (textual section extraction) first
- **Documented clearly**: Users know the limitation upfront
- **Upgrade path defined**: Future enhancement path is clear (Phase 7)
- **Transparent trade-off**: Complexity deferred for valid reason (not material to MVP)

**References**:
- See `experiments/FINDINGS.md` - "Phase 6: Query Layer & Multiple Reports Handling" for technical details
- Discovery: `showcase_03` with 2018 data revealed SK하이닉스 with 2 filings

---

## DART Report Types Catalog

Based on the DART OPEN API specifications, the following report types are available.

**Complete Specification**: See `config/types.yaml` for all 60+ report type codes.

**Commonly Used Codes** (Periodic Reports):

| Code | Korean Name | English Description | Frequency |
|------|-------------|---------------------|-----------|
| `A001` | 사업보고서 | Annual Report | Annual |
| `A002` | 반기보고서 | Semi-Annual Report | Half-yearly |
| `A003` | 분기보고서 | Quarterly Report | Quarterly |

**Additional Categories** (examples):
- **A-series**: Periodic disclosures (A001-A005)
- **B-series**: Material events (B001-B003)
- **C-series**: Securities issuance (C001-C011)
- **D-series**: Shareholding disclosures (D001-D004)
- **E-F-G-H-I-J series**: Other disclosure types

**Discovery**: Use `ReportTypes.list_available()` to see all codes programmatically.

**Phase 1 Focus**: We'll initially support periodic reports (`A001`, `A002`, `A003`) as they contain the richest textual narratives.

**Parameter Usage**: Pass actual DART codes directly to `fetch_reports()`:
```python
report_types=["A001", "A002", "A003"]  # Use codes as-is
```

---

## Dependencies & Constraints

### Technical Dependencies

For detailed technical dependencies, module structure, and system architecture, see **[architecture.md](architecture.md)**.

**Key External Dependencies**:
- **dart-fss** (≥ 0.4.14) for DART API integration
- **MongoDB** (≥ 4.0) for document storage
- **Python** (≥ 3.12) as per project requirements

### Business Constraints

1. **Data Availability**: Limited to documents accessible via DART OPEN API
2. **XML Format Stability**: Relies on DART's XML structure remaining consistent
3. **Korean Language**: Initial focus on Korean financial statements
4. **API Rate Limits**: Subject to DART API rate limits and usage quotas

---

## MVP Complete - Achieved Milestones

### ✅ Milestone 1: Discovery & Download (Complete)

**Delivered**:
- ✅ `FilingSearchService`: Search DART API with dart-fss integration
- ✅ `DocumentDownloadService`: Download and organize XML files
- ✅ Year/stock_code/report_type partitioning scheme
- ✅ Helper classes: `ReportTypes`, `CorpClass`, `RemarkCodes`
- ✅ Experiments validated dart-fss Singleton caching (7s first load, instant thereafter)
- ✅ Test suite: 115 unit tests + 10 integration tests (100% passing)

### ✅ Milestone 2: XML Parsing (Complete)

**Delivered**:
- ✅ `xml_parser.py`: Low-level XML utilities with UTF-8/EUC-KR fallback
- ✅ `section_parser.py`: Section extraction with hierarchy reconstruction
- ✅ `section_matcher.py`: Strategy pattern for text-based matching (Exact → Fuzzy)
- ✅ `table_parser.py`: Table flattening to text for MVP
- ✅ Handles flat XML structure (siblings, not nested)
- ✅ Independent of ATOCID (works 2010-2024)
- ✅ Experiments: exp_10 (structure), exp_13 (text matching)
- ✅ Test suite: 34 unit tests (100% passing)

### ✅ Milestone 3: MongoDB Storage (Complete)

**Delivered**:
- ✅ `StorageService`: MongoDB CRUD with bulk operations
- ✅ `SectionDocument` model: 16 essential fields (optimized schema)
- ✅ Flat document structure (one doc per section)
- ✅ Denormalized metadata for efficient queries
- ✅ `section_path` for hierarchy (single field, no redundancy)
- ✅ Config facade integration (no scattered env vars)
- ✅ Test suite: 23 unit + 22 integration tests (100% passing)

### ✅ Milestone 4: Query Interface (Complete)

**Delivered**:
- ✅ `TextQuery`: Single `get()` method for all research use cases
- ✅ `ReportMetadata`: Immutable composition component
- ✅ `Sequence`: Collection class with merged text capability
- ✅ Universal return structure: `{year: {stock_code: Sequence}}`
- ✅ Supports: single retrieval, cross-sectional, time-series, panel data
- ✅ Dependency injection for testability
- ✅ Handles multiple report versions (returns latest for MVP)
- ✅ Test suite: 78 unit tests for Sequence (100% passing)

### ✅ Milestone 5: End-to-End Pipeline (Complete)

**Delivered**:
- ✅ `DisclosurePipeline`: High-level orchestrator
- ✅ `download_and_parse()`: Complete workflow (search → download → parse → store)
- ✅ Statistics reporting: `{'reports': N, 'sections': M, 'failed': 0}`
- ✅ Explicit database control via dependency injection
- ✅ Fail-fast authentication error handling
- ✅ Resilient encoding handling (UTF-8/EUC-KR)
- ✅ Test suite: 45+ unit tests (100% passing)
- ✅ Showcase scripts: 3 comprehensive demos

### ✅ MVP Complete: Production-Ready Library

**Current Status (v1.0.0)**:
- ✅ 300+ tests (100% passing)
- ✅ ~90% code coverage
- ✅ Complete end-to-end pipeline
- ✅ 15 years of data coverage (2010-2024)
- ✅ Supports 3,901 listed Korean companies
- ✅ Three showcase scripts demonstrating all features
- ✅ Comprehensive documentation (PRD, Architecture, Implementation, Findings)
- ✅ Config facade pattern for maintainability
- ✅ Strategy pattern for extensibility

**Data Availability**:
- ✅ XML format: 2010-present (verified)
- ✅ Companies: All KOSPI, KOSDAQ, KONEX listed firms
- ✅ Reports: A001 (Annual), A002 (Semi-Annual), A003 (Quarterly)
- ✅ MVP Focus: Section 020000 (사업의 내용 - Business Description)

---

## Future Enhancements (Post-MVP)

### Phase 7: Multiple Report Version Management

**Goal**: Handle original and amended filings separately for PIT correctness

**Features**:
- Store all report versions (original + amendments)
- Add `filing_date`, `filing_sequence`, `is_amendment` to schema
- Query API enhancement: `version="original"/"latest"/"all"`
- PIT query support: `as_of_date` parameter

**Value**: Eliminates forward-looking bias for rigorous research

**Status**: Documented, deferred (amendments rarely affect MVP sections)

### Phase 8: Advanced NLP Features

**Goal**: Enable semantic analysis workflows

**Features**:
- Embedding integration (sentence-transformers)
- Vector search with MongoDB Atlas
- Change detection across years
- Sentiment analysis pipelines
- Example notebooks

**Status**: Future enhancement

### Phase 9: Production Hardening

**Goal**: Enterprise-grade reliability

**Features**:
- Connection pooling optimization
- Retry logic with exponential backoff
- Comprehensive logging framework
- Performance profiling and optimization
- CI/CD pipeline (GitHub Actions)
- PyPI publication

**Status**: Planned for v2.0

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| DART XML format changes | Medium | High | Version XML schemas, maintain backward compatibility |
| Performance issues with large docs | Medium | Medium | Implement streaming parser, lazy loading |
| Inconsistent section markers | High | Medium | Build robust pattern matching, maintain exception mappings |
| dart-fss API changes | Low | High | Pin version, monitor dart-fss releases |

---

## Open Questions

1. **Section Taxonomy**: Should we create a standardized taxonomy of section names, or allow flexible user-defined patterns?
2. **Table Formats**: What's the best output format for tables (DataFrame, dict, custom class)?
3. **Encoding**: Are there encoding edge cases we need to handle beyond standard UTF-8?
4. **Versioning**: Should we track which version of DART's XML schema each document uses?

---

## Project Status

**Prepared by**: AI Assistant  
**Review Status**: ✅ Complete - MVP Delivered  
**Version**: 1.0.0  
**Last Updated**: 2025-10-05  
**Status**: Production-Ready

---

## Related Documentation

- **[architecture.md](architecture.md)**: Technical architecture, system design, data models, and technology stack
- **[implementation.md](implementation.md)**: Development methodology, testing strategy, and implementation guidelines
- **[experiments.md](experiments.md)**: Experimental findings and POC validation results
- **[FINDINGS.md](../../experiments/FINDINGS.md)**: Detailed experiment findings and lessons learned

---

## Summary

**dart-fss-text** is a **production-ready** Python library that provides structured access to textual data from Korean DART financial statements. The MVP is complete with:

- ✅ **Complete Pipeline**: Search → Download → Parse → Store → Query
- ✅ **15 Years of Data**: Full coverage of XML reports from 2010-2024
- ✅ **3,901 Companies**: All KOSPI, KOSDAQ, KONEX listed firms
- ✅ **4 Research Use Cases**: Single retrieval, cross-sectional, time-series, panel data
- ✅ **Production Quality**: 300+ tests, 90% coverage, comprehensive documentation
- ✅ **Resilient Design**: Text-based matching, encoding fallback, fail-fast errors
- ✅ **Developer Friendly**: Config facade, dependency injection, strategy patterns

**Next Steps**: Future enhancements include multiple report version management, advanced NLP features, and enterprise hardening for v2.0.
