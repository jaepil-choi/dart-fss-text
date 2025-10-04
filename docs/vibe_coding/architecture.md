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
     - `DisclosurePipeline`: High-level orchestrator for search → download → parse → store workflow
     - `TextQuery`: Query interface for retrieving parsed sections from database
   - **Design Principle**: Explicit database control via dependency injection
   - **Responsibilities**: Input validation, parameter normalization, error handling, workflow orchestration

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

#### 1. **SectionDocument** (MongoDB Model)
The primary data model representing a single section stored in MongoDB. Defined in `models/section.py` using Pydantic for validation.

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class SectionDocument(BaseModel):
    """
    MongoDB document schema for DART report sections.
    
    Each section is stored as a separate document with:
    - Document metadata (rcept_no, dates, company info)
    - Section identity (code, title, level)
    - Hierarchy info (parent, path)
    - Text content (paragraphs + tables flattened to text)
    - Statistics and parsing metadata
    
    Design Rationale:
    - Flat structure (one document per section) for query performance
    - Denormalized metadata (shared across all sections) for time-series queries
    - Text-only content (tables flattened) for MVP simplicity
    - Composite document_id as natural key: {rcept_no}_{section_code}
    """
    
    # Composite Key
    document_id: str = Field(..., description="Unique ID: {rcept_no}_{section_code}")
    
    # Document Metadata (Shared)
    rcept_no: str = Field(..., min_length=14, max_length=14)
    rcept_dt: str = Field(..., pattern=r'^\d{8}$')
    year: str = Field(..., pattern=r'^\d{4}$')
    
    # Company Information (Shared)
    corp_code: str = Field(..., min_length=8, max_length=8)
    corp_name: str
    stock_code: str = Field(..., pattern=r'^\d{6}$')
    
    # Report Type (Shared)
    report_type: str
    report_name: str
    
    # Section Identity
    section_code: str
    section_title: str
    level: int = Field(..., ge=1, le=4)
    atocid: str  # Auto Table of Contents ID from XML
    
    # Hierarchy
    parent_section_code: Optional[str] = None
    parent_section_title: Optional[str] = None
    section_path: List[str] = Field(default_factory=list)
    
    # Content
    text: str  # Paragraphs + tables flattened to text
    
    # Statistics
    char_count: int = Field(..., ge=0)
    word_count: int = Field(..., ge=0)
    
    # Parsing Metadata
    parsed_at: datetime
    parser_version: str
```

#### 2. **ReportMetadata** (Composition Component)
Pydantic model for shared report-level metadata, extracted from SectionDocument.

```python
from pydantic import BaseModel, Field

class ReportMetadata(BaseModel):
    """
    Shared report-level metadata extracted from SectionDocument.
    
    Design Pattern: Composition over Inheritance
    - Used by Sequence to provide shared metadata access
    - Immutable (frozen) to ensure consistency
    - Validated by Pydantic on creation
    
    Rationale:
    - Avoids inheritance issues (Sequence contains multiple sections)
    - Clear "has-a" relationship instead of "is-a"
    - Enables metadata reuse without duplication
    """
    rcept_no: str = Field(..., min_length=14, max_length=14)
    rcept_dt: str = Field(..., pattern=r'^\d{8}$')
    year: str = Field(..., pattern=r'^\d{4}$')
    corp_code: str = Field(..., min_length=8, max_length=8)
    corp_name: str
    stock_code: str = Field(..., pattern=r'^\d{6}$')
    report_type: str
    report_name: str
    
    model_config = {"frozen": True}  # Immutable
    
    @classmethod
    def from_section_document(cls, doc: SectionDocument) -> 'ReportMetadata':
        """Extract metadata from SectionDocument."""
        return cls(
            rcept_no=doc.rcept_no,
            rcept_dt=doc.rcept_dt,
            year=doc.year,
            corp_code=doc.corp_code,
            corp_name=doc.corp_name,
            stock_code=doc.stock_code,
            report_type=doc.report_type,
            report_name=doc.report_name,
        )
```

#### 3. **Sequence** (Collection Class)
User-facing collection of SectionDocument objects from the same report.

```python
from typing import List, Iterator, Union

class Sequence:
    """
    Ordered collection of SectionDocument objects from the same report.
    
    Key Features:
    - Contains List[SectionDocument] with shared metadata
    - Provides merged text access with customizable separator
    - Supports indexing by position (int), section_code (str), or slice
    - Validates all sections share same report metadata
    - Offers collection statistics (total chars, words, section count)
    
    Design Pattern: Composition
    - "Has-a" ReportMetadata (shared metadata)
    - "Contains" List[SectionDocument] (sections)
    
    Usage:
        # Create from SectionDocument objects
        seq = Sequence([doc1, doc2, doc3])
        
        # Access sections
        first = seq[0]                  # By index → SectionDocument
        specific = seq["020100"]        # By code → SectionDocument
        subset = seq[1:3]               # By slice → Sequence
        
        # Merged text
        text = seq.text                 # Default separator: \n\n
        text = seq.get_text(sep="\n")  # Custom separator
        
        # Metadata (shared across all sections)
        print(seq.corp_name, seq.year)
        
        # Statistics
        print(seq.total_word_count, seq.section_count)
    """
    
    def __init__(self, sections: List[SectionDocument]):
        # Validate all sections share same report metadata
        # Extract and store shared ReportMetadata
        # Cache sections list
        ...
    
    # Report metadata access (delegated to self.metadata)
    @property
    def rcept_no(self) -> str: ...
    @property
    def year(self) -> str: ...
    @property
    def stock_code(self) -> str: ...
    @property
    def corp_name(self) -> str: ...
    
    # Collection access
    def __getitem__(self, key: Union[int, str, slice]) -> Union[SectionDocument, Sequence]: ...
    def __iter__(self) -> Iterator[SectionDocument]: ...
    def __len__(self) -> int: ...
    
    # Text access
    @property
    def text(self) -> str: ...
    def get_text(self, separator: str = "\n\n") -> str: ...
    
    # Statistics
    @property
    def total_char_count(self) -> int: ...
    @property
    def total_word_count(self) -> int: ...
    @property
    def section_count(self) -> int: ...
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

## Query Interface Architecture

### Design Overview

The query interface provides a **simple, universal API** for retrieving sections from MongoDB. It supports four primary research use cases with a single method signature.

#### Design Principles

1. **Simplicity**: One method (`get()`) handles all use cases
2. **Dependency Injection**: `StorageService` injected for testability
3. **Universal Return Format**: `Dict[year][stock_code] → Sequence`
4. **No Unnecessary Abstraction**: Plain dictionary return (no wrapper class)
5. **Composition over Inheritance**: Avoid complex inheritance hierarchies

### Core Components

#### 1. **TextQuery** (Query Interface)

```python
from typing import Dict, List, Union, Optional

class TextQuery:
    """
    High-level query interface for retrieving sections.
    
    Design Philosophy:
    - Single method for all use cases (simplicity)
    - Dependency injection for StorageService (testability)
    - Returns plain dictionary (no wrapper overhead)
    - Handles year range or explicit year list
    
    Initialization:
        storage = StorageService(mongo_uri="...", database="FS", collection="A001")
        query = TextQuery(storage_service=storage)
    """
    
    def __init__(self, storage_service: StorageService):
        """Inject StorageService dependency."""
        self._storage = storage_service
    
    def get(
        self,
        stock_codes: Union[str, List[str]],
        years: Union[str, int, List[Union[str, int]], None] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        section_codes: Union[str, List[str]] = "020000",
    ) -> Dict[str, Dict[str, Sequence]]:
        """
        Universal query method supporting all research use cases.
        
        Parameters accept both single values and lists for flexibility:
        - stock_codes: "005930" or ["005930", "000660"]
        - years: 2024, [2023, 2024], or None (use start_year/end_year)
        - start_year/end_year: Alternative to years (inclusive range)
        - section_codes: "020100" or ["020100", "020200"]
        
        Returns:
            {
                "2024": {
                    "005930": Sequence([SectionDocument, ...]),
                    "000660": Sequence([SectionDocument, ...])
                },
                "2023": { ... }
            }
        
        Validation:
        - Mutually exclusive: years vs start_year/end_year
        - Required pairing: start_year + end_year together or neither
        - Range check: end_year >= start_year
        """
```

#### 2. **Universal Return Structure**

The return format `Dict[str, Dict[str, Sequence]]` is designed to handle all four research scenarios:

```python
# Structure: {year: {stock_code: Sequence}}

{
    "2024": {
        "005930": Sequence([SectionDocument, SectionDocument, ...]),
        "000660": Sequence([SectionDocument, ...])
    },
    "2023": {
        "005930": Sequence([...]),
        "000660": Sequence([...])
    }
}
```

**Why This Structure?**

1. **Time-Series Ready**: Outer key is year → natural iteration for temporal analysis
2. **Cross-Sectional Ready**: Inner dict is {stock_code: Sequence} → natural firm comparison
3. **Panel Data Ready**: Nested structure supports multi-dimensional queries
4. **Consistent**: Same format for all use cases → predictable API
5. **Flexible**: Easy to extract subsets (single year, single firm, etc.)

### Research Use Cases

#### Use Case 1: Single Firm, Single Year, Single Section

**Scenario**: Get Samsung's 2024 business overview section

```python
result = query.get(
    stock_codes="005930",
    years=2024,
    section_codes="020100"
)

# Access
seq = result["2024"]["005930"]
text = seq.text
print(f"Samsung 2024 business overview: {seq.total_word_count} words")
```

#### Use Case 2: Cross-Sectional Analysis

**Scenario**: Compare business descriptions across semiconductor firms in 2024

```python
result = query.get(
    stock_codes=["005930", "000660", "005380"],  # Samsung, SK Hynix, Hyundai
    years=2024,
    section_codes="020100"
)

# Cross-sectional comparison
for stock_code, seq in result["2024"].items():
    print(f"{seq.corp_name}: {seq.total_char_count} chars")

# Text similarity analysis
texts = [seq.text for seq in result["2024"].values()]
# ... compute similarity matrix
```

#### Use Case 3: Time-Series Analysis

**Scenario**: Track changes in Samsung's business description over 5 years

```python
result = query.get(
    stock_codes="005930",
    start_year=2020,
    end_year=2024,
    section_codes="020100"
)

# Time-series analysis
years = sorted(result.keys())
for year in years:
    seq = result[year]["005930"]
    print(f"{year}: {seq.total_word_count} words")

# Year-over-year change analysis
for i in range(len(years) - 1):
    curr = result[years[i+1]]["005930"].total_word_count
    prev = result[years[i]]["005930"].total_word_count
    change = (curr - prev) / prev * 100
    print(f"{years[i+1]}: {change:+.1f}% change")
```

#### Use Case 4: Panel Data Research

**Scenario**: Multi-firm, multi-year analysis for econometric models

```python
result = query.get(
    stock_codes=["005930", "000660", "005380"],
    start_year=2020,
    end_year=2024,
    section_codes="020000"  # Parent section with children
)

# Panel data structure
for year in sorted(result.keys()):
    for stock_code, seq in result[year].items():
        print(f"{year} {seq.corp_name}: "
              f"{seq.section_count} sections, "
              f"{seq.total_word_count} words")

# Export to analysis-ready format
panel_data = []
for year, firms in result.items():
    for stock_code, seq in firms.items():
        for doc in seq:  # Iterate SectionDocument objects
            panel_data.append({
                'year': year,
                'stock_code': stock_code,
                'corp_name': seq.corp_name,
                'section_code': doc.section_code,
                'section_title': doc.section_title,
                'text': doc.text,
                'word_count': doc.word_count,
            })

# Convert to pandas for regression analysis
import pandas as pd
df = pd.DataFrame(panel_data)
df = df.set_index(['year', 'stock_code', 'section_code'])
```

### Design Rationale

#### Why No QueryResult Wrapper?

**Decision**: Return plain `Dict[str, Dict[str, Sequence]]` instead of wrapping in a custom class.

**Rationale**:
1. **Simplicity**: Users understand dictionaries natively
2. **No Overhead**: No extra abstraction layer to learn
3. **Flexibility**: Standard dict operations (`.items()`, `.keys()`, `.values()`)
4. **Text-Focused**: Unlike numerical data, text doesn't benefit from DataFrame conversion
5. **Explicit is Better**: Users see the structure clearly

**Rejected Alternative**:
```python
# ❌ Rejected: QueryResult wrapper
class QueryResult:
    def __init__(self, data: Dict[str, Dict[str, Sequence]]):
        self._data = data
    
    def to_dataframe(self) -> pd.DataFrame:
        # Problem: DataFrames not built for massive text data
        # Problem: Adds abstraction without clear value
```

#### Why Composition over Inheritance?

**Decision**: Use `ReportMetadata` as a shared component in `Sequence`, not inheritance.

**Problem with Inheritance**:
```python
# ❌ BAD: Inheritance approach
class ReportObject:
    rcept_no: str
    year: str
    stock_code: str
    section_code: str  # ❌ What if object contains MULTIPLE sections?
    section_title: str  # ❌ Ambiguous for collections

class Sequence(ReportObject):  # ❌ Doesn't make sense
    sections: List[SectionDocument]
```

**Solution with Composition**:
```python
# ✅ GOOD: Composition approach
class ReportMetadata(BaseModel):
    """Shared metadata extracted from SectionDocument."""
    rcept_no: str
    year: str
    stock_code: str
    # ... (no section-specific fields)
    
    model_config = {"frozen": True}

class Sequence:
    """Collection of SectionDocument objects."""
    def __init__(self, sections: List[SectionDocument]):
        self.metadata = ReportMetadata.from_section_document(sections[0])
        self._sections = sections
    
    @property
    def year(self) -> str:
        return self.metadata.year  # Delegated access
```

**Benefits**:
1. ✅ **Clear Semantics**: "Has-a" relationship (Sequence *has* metadata)
2. ✅ **No Ambiguity**: Sequence doesn't inherit section-specific fields
3. ✅ **Python Best Practice**: "Favor composition over inheritance" (Gang of Four)
4. ✅ **Flexibility**: Easy to swap or extend metadata implementation

#### Why Dependency Injection?

**Decision**: Inject `StorageService` into `TextQuery` constructor.

```python
# ✅ GOOD: Dependency Injection
class TextQuery:
    def __init__(self, storage_service: StorageService):
        self._storage = storage_service

# Usage
storage = StorageService(mongo_uri="...", database="FS", collection="A001")
query = TextQuery(storage_service=storage)
```

**Benefits**:
1. ✅ **Testability**: Easy to mock `StorageService` in unit tests
2. ✅ **Separation of Concerns**: TextQuery doesn't know about MongoDB connection details
3. ✅ **Flexibility**: Can swap storage backends without changing TextQuery
4. ✅ **Reusability**: Multiple `TextQuery` instances can share same `StorageService`

**Rejected Alternative**:
```python
# ❌ BAD: Tight coupling
class TextQuery:
    def __init__(self, mongo_uri: str, database: str, collection: str):
        self._storage = StorageService(mongo_uri, database, collection)
        # Problem: Hard to test (requires real MongoDB)
        # Problem: Duplicates connection logic
```

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
      query.py                     # TextQuery interface (simple query API)
      pipeline.py                  # DisclosurePipeline orchestrator (future)
    
    services/
      __init__.py
      filing_search.py             # FilingSearchService (uses dart-fss directly)
      document_download.py         # DocumentDownloadService
      storage_service.py           # StorageService (MongoDB CRUD)
    
    parsers/
      __init__.py
      xml_parser.py                # Low-level XML parsing (load XML, build index)
      section_parser.py            # Section extraction logic (content + hierarchy)
      table_parser.py              # Table parsing and text flattening
    
    models/
      __init__.py
      section.py                   # SectionDocument (Pydantic, MongoDB schema)
      metadata.py                  # ReportMetadata (composition component)
      sequence.py                  # Sequence (collection of SectionDocuments)
      requests.py                  # Request models (SearchFilingsRequest, etc.)
    
    utils/
      __init__.py
      text_cleaning.py             # Text normalization utilities
      validators.py                # Input validation functions
      logging.py                   # Logging configuration
    
    config.py                      # Configuration loading (Pydantic Settings)
    types.py                       # Helper classes (ReportTypes, etc.)
```

### Module Responsibilities

#### **api/**
- **query.py**: User-facing query interface (`TextQuery`)
  - Single `get()` method for all research use cases
  - Dependency injection for `StorageService`
  - Returns `Dict[year][stock_code] → Sequence`
- **pipeline.py**: High-level orchestrator (`DisclosurePipeline`)
  - Takes `StorageService` as injected dependency
  - `download_and_parse()` method for complete workflow
  - Returns statistics dictionary: `{'reports': N, 'sections': M, 'failed': 0}`
  - Coordinates `FilingSearchService`, XML parsing, and storage

#### **services/**
- **filing_search.py**: Filing discovery using dart-fss
  - `FilingSearchService.search_filings()` - Search and filter filings
  - Direct dart-fss integration (no adapter layer)
- **document_download.py**: Document download and organization
  - `DocumentDownloadService.download()` - Download XML files
  - PIT-aware directory structure
- **storage_service.py**: MongoDB storage operations
  - `StorageService.insert_section()` - Insert SectionDocument
  - `StorageService.get_section_with_descendants()` - Query with hierarchy
  - `StorageService.get_report_sections()` - Get all sections of a report

#### **parsers/**
- **xml_parser.py**: Low-level XML utilities
  - `load_xml()` - Load and validate XML with recovery mode
  - `build_section_index()` - Create ATOCID-based section index
  - `map_titles_to_toc()` - Match XML titles to TOC entries
- **section_parser.py**: Section content extraction
  - `extract_section_content()` - Extract paragraphs and tables
  - `reconstruct_hierarchy()` - Build parent-child relationships
- **table_parser.py**: Table handling
  - `parse_table()` - Extract table structure
  - `flatten_table_to_text()` - Convert to text for MVP

#### **models/**
- **section.py**: `SectionDocument` (Pydantic model, 1:1 MongoDB mapping)
- **metadata.py**: `ReportMetadata` (shared metadata, composition component)
- **sequence.py**: `Sequence` (collection class with merged text capability)
- **requests.py**: Request models for validation

#### **utils/**
- **validators.py**: Reusable validation functions
- **text_cleaning.py**: Text normalization
- **logging.py**: Logging configuration

---

## Design Patterns

### 1. **Composition Pattern** (Data Model Design)

Use composition over inheritance for data models to avoid ambiguity and maintain clear semantics.

```python
# ✅ GOOD: Composition Pattern
class ReportMetadata(BaseModel):
    """Shared report-level metadata (immutable)."""
    rcept_no: str
    year: str
    stock_code: str
    corp_name: str
    # ... (no section-specific fields)
    
    model_config = {"frozen": True}
    
    @classmethod
    def from_section_document(cls, doc: SectionDocument) -> 'ReportMetadata':
        """Extract from SectionDocument."""
        return cls(rcept_no=doc.rcept_no, year=doc.year, ...)

class Sequence:
    """Collection of SectionDocument objects."""
    def __init__(self, sections: List[SectionDocument]):
        # "Has-a" relationship with ReportMetadata
        self.metadata = ReportMetadata.from_section_document(sections[0])
        self._sections = sections
    
    @property
    def year(self) -> str:
        return self.metadata.year  # Delegate to metadata
    
    @property
    def text(self) -> str:
        return "\n\n".join(s.text for s in self._sections)
```

**Benefits**:
- **Clear "has-a" relationship**: Sequence *has* metadata, not *is* metadata
- **No ambiguity**: Sequence doesn't inherit section-specific fields (which would be meaningless for collections)
- **Flexibility**: Easy to change metadata implementation
- **Python best practice**: Gang of Four design principle

**Why Not Inheritance?**
```python
# ❌ BAD: Inheritance creates ambiguity
class ReportObject:
    section_code: str  # ❌ What code if Sequence contains MULTIPLE sections?
    section_title: str # ❌ Ambiguous for collections

class Sequence(ReportObject):  # ❌ Doesn't make semantic sense
    sections: List[SectionDocument]
```

### 2. **Repository Pattern** (Data Access)
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

### 3. **Strategy Pattern** (Parsing Strategies)
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

### 4. **Direct dart-fss Company Lookup**
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

### 5. **Download Service with dart-fss**
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

### 6. **Facade Pattern** (API Layer)
High-level orchestrator with explicit database control:

```python
from typing import List, Dict, Union

class DisclosurePipeline:
    """
    Facade for the complete workflow: search → download → parse → store.
    
    Design Philosophy:
    - Explicit database control: StorageService injected by user
    - User verifies DB connection before processing
    - Coordinates FilingSearchService and parsing components
    - Returns statistics for monitoring and validation
    """
    
    def __init__(self, storage_service: StorageService):
        """
        Initialize pipeline with injected storage service.
        
        Args:
            storage_service: Pre-initialized StorageService with verified connection
        
        Example:
            storage = StorageService()  # User controls DB connection
            pipeline = DisclosurePipeline(storage_service=storage)
        """
        self._storage = storage_service
        self._filing_search = FilingSearchService()
        # Parsing services initialized as needed
    
    def download_and_parse(
        self,
        stock_codes: Union[str, List[str]],
        years: Union[int, List[int]],
        report_type: str = "A001"
    ) -> Dict[str, int]:
        """
        Complete workflow: search → download → parse → store.
        
        Args:
            stock_codes: Company stock codes (e.g., ["005930", "000660"])
            years: Years to fetch (e.g., [2023, 2024])
            report_type: DART report type code (default: "A001")
        
        Returns:
            Statistics dictionary:
            {
                'reports': 4,      # Reports processed
                'sections': 194,   # Sections stored
                'failed': 0        # Failed operations
            }
        
        Example:
            stats = pipeline.download_and_parse(
                stock_codes=["005930", "000660"],
                years=[2023, 2024],
                report_type="A001"
            )
            print(f"Stored {stats['sections']} sections from {stats['reports']} reports")
        """
        # Normalize inputs
        stock_codes = [stock_codes] if isinstance(stock_codes, str) else stock_codes
        years = [years] if isinstance(years, int) else years
        
        # Initialize statistics
        stats = {'reports': 0, 'sections': 0, 'failed': 0}
        
        # Process each company and year
        for year in years:
            for stock_code in stock_codes:
                try:
                    # Search for filings
                    filings = self._filing_search.search_filings(...)
                    
                    # Download XML
                    xml_path = self._download(filing)
                    
                    # Parse sections
                    sections = self._parse(xml_path)
                    
                    # Store in MongoDB (using injected storage)
                    self._storage.insert_sections(sections)
                    
                    stats['reports'] += 1
                    stats['sections'] += len(sections)
                    
                except Exception as e:
                    stats['failed'] += 1
                    # Log error
        
        return stats
```

**Benefits**: 
- **Explicit Control**: User manages database connection separately
- **Testability**: Easy to inject mock StorageService for testing
- **Flexibility**: Can configure storage before passing to pipeline
- **Statistics**: Returns actionable metrics for validation
- **Separation of Concerns**: Pipeline doesn't manage database lifecycle

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

### Phase 3: Document Parsing (Complete)

**Completed Components:**
- ✅ `parsers/xml_parser.py` - Low-level XML parsing utilities
  - `load_toc_mapping()` - Load TOC (Table of Contents) mapping
  - `build_section_index()` - Create ATOCID-based section index
  - `extract_section_by_code()` - Extract section content
  - Handles flat XML structure with hierarchy reconstruction
  
- ✅ `models/section.py` - SectionDocument Pydantic model
  - MongoDB schema with validation
  - Flat structure (one document per section)
  - Denormalized metadata for query performance

**Experiments:**
- ✅ exp_10_xml_structure_exploration.py - Documents XML structure discovery
  - Flat XML structure requiring programmatic hierarchy reconstruction
  - ATOCID-based ordering and parent-child relationships
  - TOC-based section identification

### Phase 4: MongoDB Storage (Complete)

**Completed Components:**
- ✅ `services/storage_service.py` - StorageService
  - CRUD operations for SectionDocument
  - `insert_sections()` - Bulk insert with duplicate handling
  - `get_sections_by_company()` - Query by stock_code and year
  - `get_report_sections()` - Get all sections of a report (sorted by ATOCID)
  - Connection management with configurable parameters
  
- ✅ `models/metadata.py` - ReportMetadata (composition component)
- ✅ `models/sequence.py` - Sequence (collection class)
  - Ordered collection of SectionDocument objects
  - Merged text access with customizable separator
  - Indexing by position, section_code, or slice
  - Delegated metadata access

**Test Coverage:**
- ✅ Unit tests for StorageService (mocked MongoDB)
- ✅ Integration tests with live MongoDB
- ✅ Unit tests for ReportMetadata and Sequence

**Experiments:**
- ✅ exp_11_mongodb_storage.py - Validates MongoDB integration

### Phase 5: API Layer (In Progress)

**Completed Components:**
- ✅ `api/query.py` - TextQuery interface
  - Single `get()` method for all research use cases
  - Dependency injection for StorageService
  - Returns `Dict[year][stock_code] → Sequence`
  - Supports single retrieval, cross-sectional, time-series, and panel data queries

**In Progress:**
- ⏳ `api/pipeline.py` - DisclosurePipeline orchestrator
  - Takes `StorageService` as injected dependency
  - `download_and_parse()` method for complete workflow
  - Returns statistics dictionary

**Pending:**
- ⏳ End-to-end pipeline integration with all components

### Development Metrics (as of 2025-10-04)

| Metric | Value |
|--------|-------|
| Total Tests | 200+ |
| Test Pass Rate | 100% |
| Code Coverage | ~90% |
| Phases Complete | 4/5 (Phase 5 in progress) |
| Lines of Code | ~5,000+ |
| Key Components | FilingSearchService, StorageService, TextQuery, Parsers, Models |
| Showcase Scripts | 2 (sample data + live data) |

---

## References & Standards

- **DART OPEN API Specification**: https://opendart.fss.or.kr/guide/main.do
- **MongoDB Best Practices**: https://www.mongodb.com/docs/manual/administration/production-notes/
- **Python Type Hints**: PEP 484, PEP 526
- **Korean Financial Reporting Standards**: K-IFRS

---

**Last Updated**: 2025-10-04  
**Version**: 1.2  
**Status**: Active Development (Phase 5 in progress - DisclosurePipeline)

