# Technical Architecture: dart-fss-text

## Overview

**dart-fss-text** is structured as a **layered pipeline architecture** that transforms raw DART XML documents into semantically-structured, queryable text stored in MongoDB. Each layer maintains clear separation of concerns while supporting the end-to-end workflow: **discover → download → parse → store → query**.

---

## System Architecture

### High-Level Component Diagram

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

### Architectural Layers

#### 1. **API Layer**
   - **Purpose**: User-facing interfaces for discovery and querying
   - **Components**:
     - `DisclosurePipeline`: Orchestrates the complete workflow
     - `TextQuery`: Query interface for stored documents
     - `DiscoveryAPI`: Search and preview filings before download
   - **Responsibilities**: Input validation, parameter normalization, error handling

#### 2. **Business Logic Layer**
   - **Purpose**: Core processing and orchestration
   - **Components**:
     - `CorpListManager`: Manage corporation list cache and stock_code → corp_code mapping
     - `FilingSearchService`: Search and filter filings using dart-fss
     - `DocumentParserService`: Parse XML into structured sections
     - `MetadataExtractor`: Extract and validate PIT-critical metadata
     - `SectionMapper`: Map USERMARK patterns to semantic section names
   - **Responsibilities**: Business rule enforcement, data transformation

#### 3. **Data Access Layer**
   - **Purpose**: Abstract storage operations
   - **Components**:
     - `StorageManager`: MongoDB CRUD operations
     - `FileSystemCache`: Raw XML file management
     - `EmbeddingRepository`: Vector embedding storage and retrieval
   - **Responsibilities**: Persistence, data integrity, transactional operations

#### 4. **Integration Layer**
   - **Purpose**: External system integration
   - **Components**:
     - `MongoDBClient`: MongoDB connection management
   - **Responsibilities**: Connection pooling, database abstraction
   - **Note**: Services use `dart-fss` directly - no adapter needed as it's already a well-designed API wrapper

---

## Design Principles

### 1. **Single Responsibility Principle (SRP)**
Each module handles one specific aspect of text extraction:
- **FilingSearchService**: Only searches/filters filings
- **DocumentParserService**: Only parses XML structure
- **StorageManager**: Only handles persistence

**Rationale**: Improves testability, maintainability, and enables independent evolution of each component.

### 2. **Separation of Concerns**
Clear boundaries between layers:
- **Download logic**: Delegated to `dart-fss`
- **Parsing logic**: Handled by `dart-fss-text`
- **Storage logic**: Encapsulated in data access layer

**Rationale**: Prevents tight coupling, enables technology substitution (e.g., switching databases).

### 3. **Fail-Safe Parsing**
Gracefully handle malformed or unexpected XML structures:
- Partial parsing success (extract what's parseable)
- Detailed error logging with context
- Fallback mechanisms for missing sections

**Rationale**: DART documents vary in structure; strict parsing would reject valid but non-standard documents.

### 4. **Performance Optimization**
- **Lazy Loading**: Parse sections on-demand, not all at once
- **Caching**: Store raw XML locally to avoid redundant downloads
- **Streaming**: Process large documents without loading entirely into memory

**Rationale**: Financial documents can be multi-megabyte XML files; eager loading would cause memory issues.

### 5. **Testability**
- **Pure Functions**: Parsing functions with no side effects
- **Dependency Injection**: External services injected (dart-fss, MongoDB)
- **Test Doubles**: Support mocking for all external dependencies

**Rationale**: Enables fast unit tests and isolated integration tests.

### 6. **Domain-Driven Design**
Model financial statement concepts explicitly:
- `Section`, `Table`, `Document` are **domain entities**
- `USERMARK` → semantic mapping reflects **domain knowledge**
- PIT metadata tracking reflects **domain constraints**

**Rationale**: Code should reflect the financial reporting domain, not just technical structures.

### 7. **Specification-Based Validation**
All parameters defined in `config/types.yaml` must be validated against the specification using **Pydantic Settings** for type-safe, automatic configuration management:

- **Automatic Loading**: Config loaded from YAML using `pydantic-settings`
- **Type-Safe Validation**: Pydantic field validators ensure correctness
- **Discoverability**: Helper classes expose available values
- **Single Source of Truth**: `types.yaml` is the canonical reference

**Architecture**:

```python
# 1. Config Layer: Pydantic Settings auto-loads YAML
from pydantic_settings import BaseSettings
from typing import Dict

class ReportTypesConfig(BaseSettings):
    """Auto-loaded from config/types.yaml."""
    pblntf_detail_ty: Dict[str, str]
    corp_cls: Dict[str, str]
    rm: Dict[str, str]
    
    model_config = SettingsConfigDict(
        yaml_file='config/types.yaml',
        yaml_file_encoding='utf-8'
    )
    
    def is_valid_report_type(self, code: str) -> bool:
        return code in self.pblntf_detail_ty

# Singleton instance
def get_config() -> ReportTypesConfig:
    """Lazy-loaded singleton."""
    ...


# 2. Validation Layer: Reusable field validators
def validate_report_types(codes: List[str]) -> List[str]:
    """Validate report type codes against config."""
    config = get_config()
    invalid = [c for c in codes if not config.is_valid_report_type(c)]
    if invalid:
        raise ValueError(f"Invalid codes: {invalid}")
    return codes


# 3. Model Layer: Pydantic models with validators
class SearchFilingsRequest(BaseModel):
    stock_code: str
    report_types: List[str]
    
    # Apply validator
    _validate = field_validator('report_types')(validate_report_types)


# 4. Discovery Layer: Helper classes
class ReportTypes:
    @staticmethod
    def list_available() -> Dict[str, str]:
        return get_config().pblntf_detail_ty.copy()
    
    @staticmethod
    def list_by_category(prefix: str) -> Dict[str, str]:
        all_types = get_config().pblntf_detail_ty
        return {k: v for k, v in all_types.items() 
                if k.startswith(prefix)}


# 5. Usage: Clean and automatic
def search_filings(stock_code: str, report_types: List[str]):
    # Validate via Pydantic model
    request = SearchFilingsRequest(
        stock_code=stock_code,
        report_types=report_types  # Auto-validated!
    )
    # Proceed with guaranteed-valid inputs
    ...
```

**Benefits**:
- **No manual path handling**: Pydantic Settings resolves config paths automatically
- **Type safety**: Config fields are typed and validated
- **Automatic validation**: Field validators run on model creation
- **Easy testing**: Override config in tests with `model_config`
- **Self-documenting**: Field descriptions become API documentation
- **Better errors**: Pydantic provides detailed validation errors with context

**User-Facing Discovery**:
```bash
# CLI commands
dart-fss-text types list
dart-fss-text types describe A001

# Python API
from dart_fss_text import ReportTypes
print(ReportTypes.list_available())
print(ReportTypes.get_description('A001'))  # "사업보고서"
```

---

## Data Models

### Core Domain Classes

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
import pandas as pd

@dataclass
class Section:
    """
    Represents a major section in a financial statement.
    
    Attributes:
        name: Semantic section name (e.g., "주요 사업의 내용")
        usermark: DART XML marker (e.g., "F-14 B")
        text: Cleaned, concatenated text content
        paragraphs: Individual paragraphs preserving structure
        tables: Embedded tables within this section
        subsections: Hierarchical children (for nested sections)
        metadata: Additional info (page numbers, raw XML snippet, etc.)
    """
    name: str
    usermark: str
    text: str
    paragraphs: List[str]
    tables: List['Table']
    subsections: List['Section']
    metadata: Dict[str, any]


@dataclass
class Table:
    """
    Structured representation of a financial table.
    
    Attributes:
        headers: Column headers
        rows: Data rows (each row is a list of cell values)
        context: Surrounding text for semantic context
    """
    headers: List[str]
    rows: List[List[str]]
    context: str
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame for analysis."""
        return pd.DataFrame(self.rows, columns=self.headers)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage."""
        return {
            "headers": self.headers,
            "rows": self.rows,
            "context": self.context
        }


@dataclass
class Document:
    """
    Top-level document container representing a complete filing.
    
    Attributes:
        rcept_no: DART receipt number (unique document ID)
        sections: Mapping of section names to Section objects
        raw_xml_path: Path to raw XML file in filesystem cache
        metadata: Filing metadata (dates, company info, etc.)
    """
    rcept_no: str
    sections: Dict[str, Section]
    raw_xml_path: Path
    metadata: 'FilingMetadata'


@dataclass
class FilingMetadata:
    """
    Point-in-time (PIT) critical metadata for a filing.
    
    Attributes:
        stock_code: Company stock code (e.g., "005930")
        company_name: Company name (e.g., "삼성전자")
        report_type: Report type code (e.g., "A001")
        published_date: Original disclosure date
        amended_date: Correction/amendment date (if applicable)
        download_timestamp: When we retrieved the document
        rcept_no: DART receipt number
        filing_url: DART URL to original document
    """
    stock_code: str
    company_name: str
    report_type: str
    published_date: datetime
    amended_date: Optional[datetime]
    download_timestamp: datetime
    rcept_no: str
    filing_url: str
```

---

## MongoDB Schema Design

### Database Structure

**Database Name**: `dart_disclosures` (configurable)

**Collections**:

#### 1. `filings_metadata`
Tracks all downloaded filings with PIT-critical temporal metadata.

```javascript
{
  "_id": ObjectId("..."),
  "rcept_no": "20240101000001",          // DART receipt number (unique)
  "stock_code": "005930",                 // Company code
  "company_name": "삼성전자",              // Company name
  "report_type": "A001",                  // Report type code
  "published_date": ISODate("2024-03-15"),  // Original disclosure
  "amended_date": ISODate("2024-03-20"),    // Correction date (nullable)
  "download_timestamp": ISODate("2024-03-25T10:30:00Z"),
  "filing_url": "https://dart.fss.or.kr/...",
  "raw_xml_path": "data/raw/005930/A001/20240101000001_20240315.xml",
  "parsing_status": "completed",          // completed | failed | pending
  "parsing_version": "0.1.0",             // Pipeline version for reproducibility
  "created_at": ISODate("2024-03-25T10:30:00Z"),
  "updated_at": ISODate("2024-03-25T10:35:00Z")
}
```

**Indexes**:
- `{rcept_no: 1}` - Unique index for filing lookup
- `{stock_code: 1, published_date: -1}` - Company time-series queries
- `{report_type: 1, published_date: -1}` - Report type filtering
- `{stock_code: 1, report_type: 1, published_date: -1}` - Combined queries

#### 2. `document_sections`
Stores parsed sections with text and tables.

```javascript
{
  "_id": ObjectId("..."),
  "rcept_no": "20240101000001",          // Foreign key to filings_metadata
  "stock_code": "005930",                 // Denormalized for query performance
  "section_name": "주요 사업의 내용",       // Semantic section name
  "usermark": "F-14 B",                   // DART XML marker
  "text": "당사는 반도체 제조...",          // Full text content
  "paragraphs": [                         // Structured paragraphs
    "당사는 반도체 제조...",
    "DX 부문은..."
  ],
  "tables": [                             // Embedded tables
    {
      "headers": ["구분", "매출액", "비율"],
      "rows": [["DX", "100억", "50%"], ...],
      "context": "부문별 매출 현황"
    }
  ],
  "subsections": [                        // Nested sections (optional)
    {
      "name": "DX 부문",
      "text": "...",
      "paragraphs": [...],
      "tables": [...]
    }
  ],
  "metadata": {                           // Additional parsing metadata
    "page_numbers": [12, 13, 14],
    "word_count": 2847,
    "table_count": 3
  },
  "published_date": ISODate("2024-03-15"),  // Denormalized for PIT queries
  "created_at": ISODate("2024-03-25T10:35:00Z")
}
```

**Indexes**:
- `{rcept_no: 1, section_name: 1}` - Section lookup
- `{stock_code: 1, section_name: 1, published_date: -1}` - Time-series queries
- `{stock_code: 1, published_date: -1}` - PIT queries

#### 3. `embeddings`
Stores vector embeddings for semantic search (optional, for advanced NLP features).

```javascript
{
  "_id": ObjectId("..."),
  "section_id": ObjectId("..."),          // Foreign key to document_sections
  "rcept_no": "20240101000001",
  "stock_code": "005930",
  "section_name": "주요 사업의 내용",
  "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
  "embedding_vector": [0.123, -0.456, ...],  // 384-dimensional vector
  "embedding_metadata": {
    "text_length": 2847,
    "embedding_date": ISODate("2024-03-26T09:00:00Z")
  },
  "created_at": ISODate("2024-03-26T09:00:00Z")
}
```

**Indexes**:
- `{section_id: 1}` - Unique index
- MongoDB Atlas Vector Search index on `embedding_vector` (for semantic search)

### Point-in-Time (PIT) Query Pattern

To ensure temporal correctness (no forward-looking bias), queries must filter by `as_of_date`:

```python
# Example: Get sections published before 2024-03-01
query = {
    "stock_code": "005930",
    "section_name": "주요 사업의 내용",
    "published_date": {"$lte": datetime(2024, 3, 1)}
}
```

This ensures backtesting integrity—no future information leaks into historical queries.

---

## File System Structure

### Raw XML Storage

```
data/
  raw/
    {year}/               # Year from rcept_dt (publication date)
      {corp_code}/        # Corporation code (not stock code)
        {rcept_no}.xml
        
Example:
data/
  raw/
    2023/
      00126380/           # Samsung (corp_code)
        20230307000542.xml  # 2022 FY Annual Report (published 2023-03-07)
        20230814003284.xml  # 2023 H1 Semi-Annual (published 2023-08-14)
    2024/
      00126380/
        20240312000736.xml  # 2023 FY Annual Report (published 2024-03-12)
```

**Directory Convention**:
- `{year}`: Extracted from `rcept_dt` (receipt/publication date, YYYY)
- `{corp_code}`: DART corporation code (6-8 digits, more stable than stock code)
- `{rcept_no}`: DART receipt number (unique document ID)

**Rationale (PIT-Aware)**:
1. **Year from rcept_dt**: Ensures Point-in-Time correctness. A FY 2022 report published in March 2023 goes in `2023/` because that's when it became publicly available for trading decisions.
2. **Corp code vs stock code**: Corp codes don't change; stock codes can change or be delisted.
3. **Flat within corp**: All document types for one company in same folder for simpler queries.
4. **Hierarchical by year**: Easy to partition data, delete old data, or query by availability date.

---

## Technology Stack

### Core Dependencies

| Dependency | Version | Purpose | Usage |
|-----------|---------|---------|-------|
| **dart-fss** | ≥ 0.4.14 | DART API integration | Document download, company code lookup, API authentication |
| **pymongo** | ≥ 4.0 | MongoDB driver | Database operations, connection management |
| **lxml** | ≥ 5.0 | XML parsing | Fast XML parsing with XPath support |
| **python-dotenv** | ≥ 1.0 | Environment variables | Configuration management (API keys, DB URIs) |
| **pandas** | ≥ 2.0 (optional) | Data manipulation | Table export to DataFrame |
| **pydantic** | ≥ 2.0 | Data validation | Input validation, configuration schemas |

### Alternative XML Parsers

**Primary**: `lxml` (C-based, fast, full XPath support)  
**Fallback**: `xml.etree.ElementTree` (standard library, slower but no external dependency)

**Rationale**: lxml offers significant performance benefits for large documents, but we'll support ElementTree for environments where C extensions can't be installed.

---

## Module Structure

```
src/
  dart_fss_text/
    __init__.py                    # Public API exports
    
    api/
      __init__.py
      discovery.py                 # DiscoveryAPI class
      pipeline.py                  # DisclosurePipeline orchestrator
      query.py                     # TextQuery interface
    
    services/
      __init__.py
      filing_search.py             # FilingSearchService (uses dart-fss directly)
      document_parser.py           # DocumentParserService
      metadata_extractor.py        # MetadataExtractor
      section_mapper.py            # SectionMapper (USERMARK → name)
    
    parsers/
      __init__.py
      xml_parser.py                # Low-level XML parsing
      section_parser.py            # Section extraction logic
      table_parser.py              # Table parsing logic
    
    storage/
      __init__.py
      storage_manager.py           # StorageManager (MongoDB CRUD)
      filesystem_cache.py          # FileSystemCache
      embedding_repository.py      # EmbeddingRepository
    
    integrations/
      __init__.py
      mongodb_client.py            # MongoDBClient (database connection only)
    
    models/
      __init__.py
      domain.py                    # Section, Table, Document, FilingMetadata
      config.py                    # Configuration schemas (Pydantic)
    
    utils/
      __init__.py
      text_cleaning.py             # Text normalization utilities
      validators.py                # Input validation functions
      logging.py                   # Logging configuration
```

---

## Design Patterns

### 1. **Repository Pattern** (Data Access)
Abstract storage operations behind interfaces:

```python
class StorageManager(ABC):
    @abstractmethod
    def insert_filing(self, metadata: FilingMetadata, sections: List[Section]) -> str:
        """Insert a complete filing. Returns filing ID."""
        pass
    
    @abstractmethod
    def query_sections(
        self, 
        stock_code: str, 
        section_name: str, 
        as_of_date: datetime
    ) -> List[Section]:
        """Query sections with PIT filtering."""
        pass
```

**Benefits**: Enables testing with in-memory storage; allows future database migration.

### 2. **Strategy Pattern** (Parsing Strategies)
Different parsing strategies for different document types:

```python
class ParsingStrategy(ABC):
    @abstractmethod
    def parse(self, xml_root: Element) -> Dict[str, Section]:
        """Parse XML into sections."""
        pass

class AnnualReportParser(ParsingStrategy):
    """Parser for A001 (Annual Reports)."""
    pass

class QuarterlyReportParser(ParsingStrategy):
    """Parser for A003 (Quarterly Reports)."""
    pass
```

**Benefits**: Extensible to new document types without modifying core logic.

### 3. **Direct dart-fss Company Lookup**
Use dart-fss's built-in Singleton caching for company lookups. **No external caching needed!**

```python
import dart_fss

class FilingSearchService:
    """
    Search service using dart-fss directly for company lookups.
    
    Rationale (Experiment 6):
    - dart-fss.get_corp_list() uses Singleton pattern
    - First call: ~7s (loads 114K+ corporations once per process)
    - Subsequent calls: 0.000ms (returns same cached object)
    - find_by_stock_code(): instant lookup (0.000ms)
    - No need for CSV caching or Phase 0 initialization!
    
    Usage:
        service = FilingSearchService()
        
        # dart-fss handles caching automatically
        filings = service.search_filings(
            stock_codes=["005930"],
            start_date="20240101",
            end_date="20241231",
            report_types=["A001"]
        )
    """
    
    def search_filings(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        report_types: List[str]
    ) -> List[Filing]:
        """Search filings using dart-fss directly."""
        # dart-fss Singleton - instant after first call
        corp_list = dart.get_corp_list()
        
        all_filings = []
        for stock_code in stock_codes:
            # Instant lookup using dart-fss
            corp = corp_list.find_by_stock_code(stock_code)
            
            for report_type in report_types:
                # Use dart-fss search with proper parameters
                filings = corp.search_filings(
                    bgn_de=start_date,
                    pblntf_detail_ty=report_type
                )
                all_filings.extend(filings)
        
        return all_filings
    
    def get_company_info(self, stock_code: str) -> Dict:
        """Get company metadata directly from dart-fss."""
        corp_list = dart.get_corp_list()  # Singleton
        corp = corp_list.find_by_stock_code(stock_code)
        return corp.to_dict()
```

**Benefits**:
- **Simpler**: No CSV layer, no caching logic
- **Faster**: dart-fss Singleton is instant after first load
- **Less Code**: No CorpListManager needed (-925 lines)
- **Reliable**: Leverage dart-fss's proven architecture
- **Maintained**: dart-fss team handles updates

**Validated in Experiment 6**: dart-fss's built-in caching eliminates need for external CSV caching

### 4. **Download Service with dart-fss**
Services use dart-fss directly rather than through an adapter:

```python
from dart_fss.api import filings
import dart_fss

class DownloadService:
    """Download service using dart-fss directly."""
    
    def download_filing(self, filing: dart_fss.Filing, base_path: Path) -> Path:
        """Download and organize by PIT-aware directory structure."""
        # Extract year from rcept_dt for PIT correctness
        year = filing.rcept_dt[:4]
        save_dir = base_path / year / filing.corp_code
        
        # Call dart-fss directly
        filings.download_document(
            path=str(save_dir) + "/",
            rcept_no=filing.rcept_no
        )
        return save_dir / f"{filing.rcept_no}.xml"
```

**Benefits**: 
- Simpler architecture (no wrapper around a wrapper)
- dart-fss is already well-designed and stable
- Users can mix dart-fss and our library naturally
- Easy to mock dart-fss in tests using standard pytest patterns

**Rationale**: dart-fss IS the adapter layer for DART API. Adding another layer would be over-engineering.

### 5. **Facade Pattern** (API Layer)
Simplified interface leveraging dart-fss directly:

```python
class DisclosurePipeline:
    """
    Facade for the complete workflow.
    
    Simplified: No Phase 0 needed - dart-fss handles company lookup.
    """
    
    def __init__(self, mongo_uri: str):
        # Initialize all subsystems
        self._search_service = FilingSearchService()
        self._parser_service = DocumentParserService()
        self._storage_manager = StorageManager(mongo_uri)
        # No corp_manager needed - dart-fss handles it!
    
    def fetch_reports(
        self, 
        stock_codes: List[str], 
        start_date: str,
        end_date: str,
        report_types: List[str]
    ) -> Dict[str, int]:
        """
        Search, download, parse, and store filings.
        
        Args:
            stock_codes: List of 6-digit stock codes (e.g., ["005930"])
            start_date: Start date in YYYYMMDD format (e.g., "20240101")
            end_date: End date in YYYYMMDD format (e.g., "20241231")
            report_types: DART codes (e.g., ["A001", "A002"])
        
        Returns:
            Summary: {downloaded: int, parsed: int, stored: int, failed: int}
        
        Note:
            dart-fss get_corp_list() loads once (~7s first call),
            then instant on all subsequent calls (Singleton).
        """
        # Search filings - dart-fss handles company lookup internally
        filings = self._search_service.search_filings(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            report_types=report_types
        )
        
        # Download, parse, store...
        results = {
            "downloaded": 0,
            "parsed": 0,
            "stored": 0,
            "failed": 0
        }
        
        for filing in filings:
            # Download
            xml_path = self._search_service.download_filing(filing)
            results["downloaded"] += 1
            
            # Parse
            document = self._parser_service.parse(xml_path)
            results["parsed"] += 1
            
            # Store
            self._storage_manager.insert_filing(document)
            results["stored"] += 1
        
        return results
    
    def get_company_info(self, stock_code: str) -> Dict:
        """Helper: Get company metadata via dart-fss."""
        return self._search_service.get_company_info(stock_code)
```

**Benefits**: 
- **Simpler**: No Phase 0, no explicit initialization
- **Less code**: Removed 925 lines (CorpListManager + tests)
- **Leverages dart-fss**: Uses proven Singleton caching
- **Just works**: No cache management needed

---

## Performance Considerations

### 1. **Lazy Loading**
Parse sections on-demand, not all at document load:

```python
class Document:
    def __init__(self, xml_path: Path):
        self._xml_path = xml_path
        self._sections_cache = {}
    
    def get_section(self, name: str) -> Section:
        """Load and parse section only when requested."""
        if name not in self._sections_cache:
            self._sections_cache[name] = self._parse_section(name)
        return self._sections_cache[name]
```

### 2. **Streaming XML Parsing**
Use `iterparse` for large documents:

```python
from lxml import etree

def parse_sections_streaming(xml_path: Path) -> Iterator[Section]:
    """Parse sections incrementally without loading entire XML."""
    context = etree.iterparse(xml_path, events=('end',), tag='SECTION')
    for event, elem in context:
        yield parse_section_element(elem)
        elem.clear()  # Free memory
```

### 3. **Connection Pooling**
Reuse MongoDB connections:

```python
class MongoDBClient:
    def __init__(self, uri: str, max_pool_size: int = 50):
        self._client = MongoClient(uri, maxPoolSize=max_pool_size)
```

### 4. **Batch Operations**
Insert multiple sections in single transaction:

```python
def insert_filing_batch(self, filings: List[Document]) -> None:
    """Bulk insert for performance."""
    with self._client.start_session() as session:
        with session.start_transaction():
            # Batch insert metadata
            self._db.filings_metadata.insert_many([...])
            # Batch insert sections
            self._db.document_sections.insert_many([...])
```

---

## Error Handling Strategy

### Error Classification

| Error Type | Severity | Handling Strategy |
|-----------|----------|-------------------|
| **Network Errors** | Transient | Retry with exponential backoff (max 3 attempts) |
| **Malformed XML** | Recoverable | Partial parsing, log warnings, continue |
| **Missing Sections** | Expected | Return None, log info |
| **Database Errors** | Critical | Rollback transaction, raise exception |
| **Invalid Input** | Validation | Raise `ValueError` with clear message |

### Logging Levels

- **DEBUG**: Detailed parsing steps, XML structure info
- **INFO**: Pipeline progress, document counts
- **WARNING**: Partial parsing failures, unexpected structures
- **ERROR**: Critical failures (DB connection, authentication)

---

## Security Considerations

1. **API Key Management**: Never hardcode DART API keys—use environment variables
2. **MongoDB Authentication**: Enforce authentication in production environments
3. **Input Validation**: Sanitize all user inputs (stock codes, dates, section names)
4. **Path Traversal Prevention**: Validate file paths to prevent directory traversal attacks
5. **Rate Limiting**: Respect DART API rate limits to avoid IP bans

---

## Scalability & Future Extensions

### Horizontal Scaling
- Stateless API layer: Can run multiple instances behind load balancer
- MongoDB sharding: Partition by `stock_code` for large datasets

### Cloud Deployment
- **AWS**: Lambda + DocumentDB + S3 (raw XML)
- **GCP**: Cloud Run + MongoDB Atlas + Cloud Storage
- **Azure**: Container Instances + Cosmos DB + Blob Storage

### Vector Search (Phase 7)
MongoDB Atlas supports vector embeddings natively:

```python
# Create vector search index
db.embeddings.create_search_index({
    "name": "semantic_search",
    "definition": {
        "mappings": {
            "dynamic": False,
            "fields": {
                "embedding_vector": {
                    "type": "knnVector",
                    "dimensions": 384,
                    "similarity": "cosine"
                }
            }
        }
    }
})

# Semantic search query
results = db.embeddings.aggregate([
    {
        "$vectorSearch": {
            "index": "semantic_search",
            "path": "embedding_vector",
            "queryVector": query_embedding,
            "numCandidates": 100,
            "limit": 10
        }
    }
])
```

---

## Testing Architecture

### Test Types

1. **Unit Tests** (`tests/unit/`)
   - Pure functions (text cleaning, USERMARK parsing)
   - Isolated logic with no external dependencies
   - Fast execution (< 1 second total)

2. **Integration Tests** (`tests/integration/`)
   - MongoDB operations (with test database)
   - dart-fss API calls (mocked responses)
   - File system operations (temporary directories)

3. **End-to-End Tests** (`tests/e2e/`)
   - Full pipeline with real DART API (marked for CI skip)
   - Manual validation with known-good documents

4. **Regression Tests** (`tests/fixtures/`)
   - XML samples saved as fixtures
   - Ensure parsing consistency across versions

### Test Fixtures

```
tests/
  fixtures/
    xml/
      annual_report_005930_2024.xml     # Samsung annual report
      quarterly_report_000660_2024.xml  # SK Hynix quarterly
      edge_case_malformed.xml            # Malformed XML test case
    expected_outputs/
      annual_report_005930_2024.json    # Expected parsed result
```

---

## Monitoring & Observability

### Metrics to Track

1. **Performance Metrics**:
   - Download time per document
   - Parsing time per document
   - Database insert latency

2. **Quality Metrics**:
   - Parsing success rate
   - Section extraction coverage
   - Validation error frequency

3. **Operational Metrics**:
   - API error rate
   - Retry counts
   - Database connection pool utilization

### Logging Structure

```python
{
    "timestamp": "2024-03-25T10:35:00Z",
    "level": "INFO",
    "module": "document_parser",
    "rcept_no": "20240101000001",
    "stock_code": "005930",
    "message": "Parsed 15 sections from document",
    "metrics": {
        "sections_found": 15,
        "tables_found": 8,
        "parsing_time_ms": 234
    }
}
```

---

## Deployment Considerations

### Environment Configuration

```yaml
# config/production.yaml
dart_api:
  api_key: ${DART_API_KEY}
  rate_limit: 1000  # requests per day

mongodb:
  uri: ${MONGODB_URI}
  database: dart_disclosures
  max_pool_size: 50

storage:
  raw_xml_path: /data/raw
  cache_size_gb: 100

logging:
  level: INFO
  format: json
  destination: /var/log/dart-fss-text/app.log
```

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

# Copy application
COPY src/ ./src/

# Run application
CMD ["python", "-m", "dart_fss_text.cli"]
```

---

## Implementation Status

### Phase 1: Filing Discovery ✅ (Complete - v0.1.0)

**Completed Components:**
- ✅ Configuration Layer
  - `config.py` - Pydantic Settings with YAML auto-loading
  - `types.yaml` - Specification for all DART codes
  - Lazy-loaded singleton pattern
  
- ✅ Validation Layer  
  - `validators.py` - Reusable field validators
  - `validate_stock_code()` - 6-digit format validation
  - `validate_date_yyyymmdd()` - Date format validation
  - `validate_report_types()` - Spec-based validation
  
- ✅ Model Layer
  - `models/requests.py` - `SearchFilingsRequest` with automatic validation
  - Frozen/immutable models
  - Helpful validation error messages
  
- ✅ Discovery Layer
  - `types.py` - Helper classes (ReportTypes, CorpClass, RemarkCodes)
  - User-facing discovery API
  
- ✅ Service Layer
  - `services/filing_search.py` - `FilingSearchService`
  - Direct dart-fss integration (no wrapper)
  - Batch search for multiple companies and report types
  - Leverages dart-fss Singleton pattern (114K corps in ~7s, instant thereafter)

**Test Coverage:**
- 115 unit tests (100% passing)
- 10 integration tests (100% passing)
- 3 smoke tests (pytest markers, disabled by default)
- Total: 128 tests, ~14s execution time

**Experiments:**
- ✅ exp_08_corplist_test.py - Documents dart-fss behavior
  - Validates Singleton caching
  - Confirms 114,147 total companies, 3,901 listed
  - Proves instant lookups after initial load

### Phase 2: Document Download (Next)

**Planned Components:**
- ⏳ `services/download_service.py` - Document download orchestration
- ⏳ `storage/filesystem_cache.py` - PIT-aware file organization
- ⏳ Experiment 09 - Download workflow validation

**Target Architecture:**
```python
# data/raw/{year}/{corp_code}/{rcept_no}.xml
# Year from rcept_dt (publication date) for PIT correctness
```

### Phase 3: Document Parsing (Pending)

**Planned Components:**
- ⏳ `services/document_parser.py` - DocumentParserService
- ⏳ `parsers/xml_parser.py` - Low-level XML parsing
- ⏳ `parsers/section_parser.py` - Section extraction
- ⏳ `parsers/table_parser.py` - Table parsing
- ⏳ `services/section_mapper.py` - USERMARK → semantic name mapping

### Phase 4: MongoDB Storage (Pending)

**Planned Components:**
- ⏳ `storage/storage_manager.py` - CRUD operations
- ⏳ `integrations/mongodb_client.py` - Connection management
- ⏳ Schema creation and indexing scripts

### Phase 5: API Layer (Pending)

**Planned Components:**
- ⏳ `api/pipeline.py` - DisclosurePipeline orchestrator
- ⏳ `api/query.py` - TextQuery interface
- ⏳ End-to-end pipeline integration

### Development Metrics (as of 2025-10-03)

| Metric | Value |
|--------|-------|
| Total Tests | 128 (125 run by default) |
| Test Pass Rate | 100% |
| Code Coverage | ~95% (Phase 1 only) |
| Phases Complete | 1/5 |
| Lines of Code | ~2,500 |
| API Calls Used | 59/20,000 daily quota |

---

## References & Standards

- **DART OPEN API Specification**: https://opendart.fss.or.kr/guide/main.do
- **MongoDB Best Practices**: https://www.mongodb.com/docs/manual/administration/production-notes/
- **Python Type Hints**: PEP 484, PEP 526
- **Korean Financial Reporting Standards**: K-IFRS

---

**Last Updated**: 2025-10-03  
**Version**: 1.1  
**Status**: Active Development (Phase 1 Complete)

