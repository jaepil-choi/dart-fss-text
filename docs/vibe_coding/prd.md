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

### Key Differentiators
- **Complete Pipeline**: From filing discovery to database storage—not just parsing
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

#### Use Case 1: Download and Store Disclosures
```python
from dart_fss_text import DisclosurePipeline

# Initialize pipeline with MongoDB connection
pipeline = DisclosurePipeline(mongo_uri="mongodb://localhost:27017/dart_disclosures")

# Define search filters
pipeline.fetch_and_store(
    stock_codes=["005930", "000660"],  # Samsung, SK Hynix
    start_date="2023-01-01",
    end_date="2024-12-31",
    report_types=["annual", "half"],   # Annual and semi-annual reports
)

# Returns summary: {downloaded: 8, parsed: 8, stored: 8, failed: 0}
```

#### Use Case 2: Query Stored Text
```python
from dart_fss_text import TextQuery

# Query database for specific sections
query = TextQuery(mongo_uri="mongodb://localhost:27017/dart_disclosures")

# Get business descriptions for Samsung across time
results = query.get_section(
    stock_code="005930",
    section_name="주요 사업의 내용",
    start_date="2020-01-01",
    end_date="2024-12-31",
    as_of_date="2024-03-01"  # PIT: only docs published before this date
)

for doc in results:
    print(f"{doc.published_date}: {doc.text[:200]}...")
    print(f"Tables: {doc.tables}")
```

#### Use Case 3: NLP Integration
```python
from dart_fss_text import TextQuery
from sentence_transformers import SentenceTransformer

# Load embedding model
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Query and embed
query = TextQuery(mongo_uri="mongodb://localhost:27017/dart_disclosures")
sections = query.get_section(stock_code="005930", section_name="주요 사업의 내용")

for section in sections:
    # Generate embeddings
    embedding = model.encode(section.text)
    
    # Store back to MongoDB
    query.update_embedding(section.id, embedding.tolist())

# Now ready for semantic search, clustering, etc.
```

---

## Key Features

### Phase 1: Discovery & Download Pipeline (MVP)
1. **Filing Discovery & Filtering**
   - **Input Parameters**:
     - `stock_codes` (List[str], mandatory): Company stock codes (e.g., ["005930", "000660"])
     - `start_date`, `end_date` (str): Date range for filing search
     - `report_types` (List[str]): Which reports to fetch (see Report Types catalog below)
   - Leverage dart-fss for company code lookup and API authentication
   - Search filings that match all filters

2. **Catalog & Discovery APIs**
   - `list_available_report_types()`: Show all supported report types
   - `preview_filings(filters)`: Show matching filings before download (with metadata)
   - `get_company_info(stock_code)`: Retrieve company names and metadata

3. **Metadata Management (PIT-Critical)**
   - Track **published_date** (original disclosure date)
   - Track **amended_date** (if document was corrected/updated)
   - Track **download_timestamp** (when we retrieved it)
   - Store **rcept_no** (DART document ID)
   - Store **stock_code**, **company_name**
   - This ensures point-in-time (PIT) integrity for backtesting and research

4. **Document Download & Storage**
   - Use `dart_fss.api.filings.download_document()` for retrieval
   - Automatic unzipping and XML extraction
   - Store raw XML in local filesystem with organized directory structure:
     ```
     data/
       raw/
         {stock_code}/
           {report_type}/
             {rcept_no}_{published_date}.xml
     ```
   - Track download status in metadata database

### Phase 2: XML Parsing & Structuring
5. **Section Identification**
   - Detect major sections using `USERMARK` attributes (e.g., `USERMARK="F-14 B"`)
   - Map USERMARK patterns to semantic section names
   - Handle variations in formatting across different filing types

6. **Text Extraction**
   - Clean text extraction from `<P>`, `<SPAN>`, and other text elements
   - Preserve paragraph boundaries and semantic structure
   - Handle special characters and encoding issues

7. **Table Parsing**
   - Extract tables (`<TABLE>`) with headers and data rows
   - Convert to structured dict (ready for MongoDB)
   - Maintain relationships between tables and their surrounding context

### Phase 3: Database Layer
8. **MongoDB Schema Design**
   - **Collections**:
     - `filings_metadata`: Tracks all downloaded filings (PIT metadata)
     - `document_sections`: Stores parsed sections with text and tables
     - `embeddings`: Stores vector embeddings for semantic search (optional)
   
9. **CRUD Operations**
   - Insert parsed documents with full metadata
   - Query by stock_code, date range, section name
   - **PIT queries**: Filter by `as_of_date` to ensure temporal correctness
   - Update embeddings without re-parsing documents

10. **Data Versioning**
    - Handle amended filings by storing multiple versions
    - Track parsing pipeline version (for reproducibility)

### Phase 4: Advanced Parsing
11. **Subsection Parsing**
    - Identify hierarchical structure (e.g., DX 부문, DS 부문 within 주요 사업의 내용)
    - Create nested data structures reflecting document organization

12. **Cross-Reference Resolution**
    - Parse references like "Ⅱ. 사업의 내용"
    - Link related sections

### Phase 5: Analytics & NLP
13. **Time-Series Analysis**
    - Compare sections across multiple filings
    - Track changes over time (diff functionality)
    - Visualize disclosure evolution

14. **NLP Preprocessing Pipeline**
    - Tokenization optimized for Korean financial text
    - Named entity recognition (company names, products, financial terms)
    - Sentence boundary detection

15. **Embedding & Semantic Search**
    - Generate embeddings for all sections
    - Store in MongoDB with vector search support
    - Semantic similarity queries across companies/time

---

## Technical Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Application                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  dart-fss-text API                           │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Discovery        │  │ Query            │                │
│  │ Pipeline         │  │ Interface        │                │
│  └────────┬─────────┘  └──────────────────┘                │
└───────────┼────────────────────────────────────────────────┘
            │
     ┌──────┴──────┬─────────────────────────┐
     │             │                         │
┌────▼─────┐ ┌────▼─────────┐ ┌─────────────▼───────────────┐
│ Filing   │ │ Document     │ │     MongoDB Storage         │
│ Search   │ │ Parser       │ │  ┌─────────────────────┐    │
│          │ │ (XML)        │ │  │ filings_metadata    │    │
└────┬─────┘ └────┬─────────┘ │  └─────────────────────┘    │
     │            │            │  ┌─────────────────────┐    │
     │            │            │  │ document_sections   │    │
     │            │            │  └─────────────────────┘    │
     │            │            │  ┌─────────────────────┐    │
     │            │            │  │ embeddings          │    │
     │            │            │  └─────────────────────┘    │
     │            │            └─────────────────────────────┘
     │            │
┌────▼────────────▼────────────────────────────────────────────┐
│                 File System Cache                            │
│                  (Raw XML Storage)                           │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                     dart-fss                                 │
│      (API Auth, Company Codes, download_document())          │
└──────────────────────────────────────────────────────────────┘
```

### Design Principles
1. **Single Responsibility**: Each module handles one aspect of text extraction
2. **Separation of Concerns**: Download logic (dart-fss) vs. parsing logic (dart-fss-text)
3. **Fail-Safe Parsing**: Gracefully handle malformed XML or unexpected structures
4. **Performance**: Lazy loading and caching for large documents
5. **Testability**: Pure functions for parsing, dependency injection for external calls

---

## Data Models

### Core Classes

```python
@dataclass
class Section:
    """Represents a major section in a financial statement."""
    name: str                    # e.g., "주요 사업의 내용"
    usermark: str               # e.g., "F-14 B"
    text: str                   # Cleaned, concatenated text
    paragraphs: List[str]       # Individual paragraphs
    tables: List[Table]         # Embedded tables
    subsections: List[Section]  # Hierarchical children
    metadata: dict              # Page numbers, raw XML snippet, etc.

@dataclass
class Table:
    """Structured representation of a financial table."""
    headers: List[str]
    rows: List[List[str]]
    context: str                # Surrounding text for context
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame."""
        ...

@dataclass
class Document:
    """Top-level document container."""
    rcept_no: str
    sections: Dict[str, Section]
    raw_xml_path: Path
    metadata: dict              # Filing date, company name, etc.
```

---

## Non-Goals

**Out of Scope for This Library:**
1. **Financial Statement Numbers**: dart-fss already provides excellent APIs for numerical data (XBRL, financial statements)—we won't duplicate this
2. **PDF Rendering**: We work with the XML source, not visual representations
3. **Translation**: Text remains in original Korean (users can integrate translation separately)
4. **OCR or Image Processing**: We only handle structured XML, not scanned documents
5. **Real-Time Alerts**: No push notifications for new filings (users can build this on top)

---

## DART Report Types Catalog

Based on the DART OPEN API specifications, the following report types are available:

| Report Type Code | Korean Name | English Description | Frequency |
|-----------------|-------------|---------------------|-----------|
| `A001` | 사업보고서 | Annual Report | Annual |
| `A002` | 반기보고서 | Semi-Annual Report | Half-yearly |
| `A003` | 분기보고서 | Quarterly Report | Quarterly |
| `A004` | 등기변경서 | Registration Change | Ad-hoc |
| `A005` | 증권발행실적보고서 | Securities Issuance Report | Ad-hoc |
| `B001` | 주요사항보고서 | Material Event Report | Ad-hoc |
| `B002` | 주식등의대량보유상황보고서 | Large Shareholding Report | Ad-hoc |
| `C001` | 자산유동화계획서 | Asset Securitization Plan | Ad-hoc |
| `D001` | 합병등종료보고서 | M&A Completion Report | Ad-hoc |

**Phase 1 Focus**: We'll initially support periodic reports (A001, A002, A003) as they contain the richest textual narratives.

**User-Friendly Aliases**:
- `"annual"` → A001
- `"half"` → A002
- `"quarterly"` or `"quarter"` → A003

---

## Development Methodology

### Principles
1. **Test-Driven Development (TDD)**: Write tests before implementation
2. **Continuous Live Testing**: Don't wait until the end—test with live DART API continuously
3. **Experiment-Driven**: Use `experiments/` directory for quick-and-dirty scripts to validate assumptions with real data
4. **Incremental Progress**: Small, verifiable steps that compound into robust features

### Workflow
```
┌─────────────────┐
│ Write Experiment│  (experiments/*.py - quick & dirty smoke test)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Run Live Test  │  (Test with actual DART API, inspect results)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Write Tests   │  (tests/*.py - formal TDD)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Implement Code  │  (src/dart_fss_text/*.py - production code)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Tests Pass?    │───No───► Fix Implementation
└────────┬────────┘
         │ Yes
         ▼
┌─────────────────┐
│  Live Smoke OK? │───No───► Fix & Retest
└────────┬────────┘
         │ Yes
         ▼
┌─────────────────┐
│   Next Feature  │
└─────────────────┘
```

### Experiments Directory Structure
```
experiments/
  ├── exp_01_download_document.py      # Validate download mechanics
  ├── exp_02_parse_xml_structure.py    # Explore XML patterns
  ├── exp_03_filing_search.py          # Test dart-fss search APIs
  ├── exp_04_metadata_extraction.py    # Validate PIT metadata
  └── data/                            # Downloaded samples & findings
      ├── {rcept_no}.zip
      ├── {rcept_no}.xml
      └── findings.json
```

### Testing Strategy
- **Unit Tests**: Pure functions (XML parsing, text cleaning)
- **Integration Tests**: API calls, database operations (mocked where appropriate)
- **Smoke Tests**: Live experiments with real DART data (manual validation)
- **Regression Tests**: Save known-good XML samples as fixtures

---

## Dependencies & Constraints

### External Dependencies
- **dart-fss** (≥ 0.4.14): Document download, API management, company code lookup
- **pymongo** (≥ 4.0): MongoDB driver for database operations
- **lxml** or **xml.etree.ElementTree**: XML parsing
- **python-dotenv**: Environment variable management (for experiments)
- **pandas** (optional): DataFrame export for tables

### Constraints
1. **Data Availability**: Limited to documents accessible via DART OPEN API
2. **XML Format Stability**: Relies on DART's XML structure remaining consistent
3. **Korean Language**: Initial focus on Korean financial statements
4. **Python Version**: Requires Python ≥ 3.12 (per pyproject.toml)

---

## Roadmap

### Milestone 1: Discovery & Download POC (Current Phase)
**Goal**: Validate we can search, filter, and download filings with complete metadata

**Experiments**:
- [ ] `exp_01_download_document.py`: Download single document by rcept_no, unzip, validate XML
- [ ] `exp_02_filing_search.py`: Use dart-fss to search filings by company + date range
- [ ] `exp_03_metadata_extraction.py`: Extract published_date, amended_date from filing metadata

**Tests**:
- [ ] Test dart-fss integration (mocked API responses)
- [ ] Test download and unzip workflow
- [ ] Test metadata extraction accuracy

**Deliverables**:
- [ ] Functional experiments in `experiments/` directory
- [ ] Test suite in `tests/` with ≥ 80% coverage
- [ ] Documentation of findings and XML structure patterns

---

### Milestone 2: MVP - Discovery & Download Module
**Goal**: Production-ready filing discovery and download system (no parsing yet)

**Features**:
- [ ] `DiscoveryAPI` class:
  - `list_available_report_types()`: Catalog of report types
  - `search_filings(stock_codes, date_range, report_types)`: Search with filters
  - `preview_filings(filters)`: Show metadata before download
  - `download_filings(filters, save_path)`: Bulk download with progress tracking

**Tests**:
- [ ] Unit tests for each API method (mocked dart-fss calls)
- [ ] Integration tests with live DART API (marked for CI skip)
- [ ] Edge cases: invalid stock codes, no results, API errors

**Deliverables**:
- [ ] Working code in `src/dart_fss_text/discovery/`
- [ ] Test suite with ≥ 85% coverage
- [ ] User documentation and examples

---

### Milestone 3: XML Parsing Module
**Goal**: Parse downloaded XML into structured sections and tables

**Experiments**:
- [ ] `exp_04_parse_xml_structure.py`: Identify USERMARK patterns, section boundaries
- [ ] `exp_05_extract_section.py`: Extract "주요 사업의 내용" with full context
- [ ] `exp_06_parse_tables.py`: Extract and structure tables

**Features**:
- [ ] `DocumentParser` class:
  - `load_xml(file_path)`: Load and validate XML
  - `get_sections()`: List all available sections
  - `extract_section(name)`: Extract specific section with text and tables
  - `extract_all_sections()`: Extract all sections

**Tests**:
- [ ] Unit tests with XML fixtures (known-good samples)
- [ ] Test edge cases: missing sections, malformed tables, encoding issues

**Deliverables**:
- [ ] Parser module in `src/dart_fss_text/parser/`
- [ ] Test suite with ≥ 90% coverage
- [ ] Documented section name mappings

---

### Milestone 4: MongoDB Storage Layer
**Goal**: Persist parsed data in MongoDB with PIT-aware schema

**Features**:
- [ ] MongoDB schema design (3 collections: metadata, sections, embeddings)
- [ ] `StorageManager` class:
  - `insert_filing(metadata, sections)`: Store complete filing
  - `query_sections(filters, as_of_date)`: PIT-aware queries
  - `update_embedding(section_id, embedding)`: Store embeddings

**Tests**:
- [ ] Unit tests with mock MongoDB
- [ ] Integration tests with test MongoDB instance
- [ ] Test PIT query logic

**Deliverables**:
- [ ] Storage module in `src/dart_fss_text/storage/`
- [ ] MongoDB schema documentation
- [ ] Migration scripts (if needed)

---

### Milestone 5: End-to-End Pipeline
**Goal**: Complete workflow from company list to populated database

**Features**:
- [ ] `DisclosurePipeline` class (orchestrator):
  - `fetch_and_store(stock_codes, dates, report_types)`: Full pipeline
  - Progress tracking and error handling
  - Idempotency (skip already-downloaded files)

**Tests**:
- [ ] End-to-end integration tests
- [ ] Performance benchmarks

**Deliverables**:
- [ ] Complete pipeline in `src/dart_fss_text/pipeline.py`
- [ ] CLI tool: `dart-fss-text fetch --stocks 005930 --start 2023-01-01`
- [ ] Comprehensive user guide

---

### Milestone 6: Production Hardening
**Goal**: Make library production-ready

- [ ] Error handling and retries (rate limiting, network errors)
- [ ] Logging framework
- [ ] Configuration management (YAML/TOML config files)
- [ ] Performance optimization (parallel downloads, caching)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] PyPI publication

---

### Milestone 7: NLP Features
**Goal**: Enable advanced NLP workflows

- [ ] Embedding integration (sentence-transformers)
- [ ] Semantic search capabilities
- [ ] Change detection across filings
- [ ] Example notebooks for common NLP tasks

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

## Approval & Next Steps

**Prepared by**: AI Assistant  
**Review Status**: Pending user approval  
**Next Action**: Conduct POC experiment as outlined in `experiments.md`

Once this PRD is approved, we'll proceed with the experiment to validate our understanding of the XML structure and download mechanics.

