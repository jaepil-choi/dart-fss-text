# Implementation Guide: dart-fss-text

## Current Implementation Status

### Phase 1: Filing Discovery ✅ (Complete - v0.1.0)

**Components Implemented:**
- ✅ Configuration Layer (`config.py`, `types.yaml`)
- ✅ Validation Layer (`validators.py`)
- ✅ Model Layer (`models/requests.py` with `SearchFilingsRequest`)
- ✅ Discovery Layer (`types.py` with helper classes)
- ✅ Service Layer (`services/filing_search.py` with `FilingSearchService`)

**Test Suite:**
- 115 unit tests (100% passing)
- 10 integration tests (100% passing, requires API key)
- 3 smoke tests (pytest markers, disabled by default with `-m "not smoke"`)
- Total: 128 tests, ~14s execution time

**Key Experiments:**
- ✅ `exp_08_corplist_test.py` - Documents dart-fss Singleton behavior
  - Validates ~7s initial load, instant subsequent calls
  - Confirms 114,147 total companies, 3,901 listed

---

### Phase 4: XML Parsing & Section Extraction ✅ (Complete)

**Components Implemented:**
- ✅ TOC Mapping (`config/toc.yaml` - 123 section definitions)
- ✅ Model Layer (`models/section.py` with `SectionDocument` Pydantic model)
- ✅ Parser Layer (`parsers/xml_parser.py` - Low-level XML utilities)
- ✅ Parser Layer (`parsers/section_parser.py` - Section extraction & hierarchy)
- ✅ Parser Layer (`parsers/table_parser.py` - Table parsing)

**Test Suite:**
- 34 unit tests (100% passing)
- Tests cover: TOC mapping, section indexing, extraction, hierarchy reconstruction
- Critical validations: ATOCID extraction, flat XML structure handling, content parsing

**Key Experiments:**
- ✅ `exp_10_xml_structure_exploration.py` - XML structure validation
  - Discovered ATOCID on TITLE tag (not SECTION)
  - Discovered flat XML structure (programmatic hierarchy reconstruction)
  - Validated on-demand parsing strategy
  - Performance: 0.167s indexing (155K lines), 0.010s extraction

**Key Findings:**
- XML structure is flat (siblings, not nested) - hierarchy reconstructed from ATOCID sequence
- Only SECTION-1 and SECTION-2 exist (maximum depth: 2 levels)
- Must use `.//P` and `.//TABLE` for recursive content extraction
- Coverage: 39.8% (49/123 sections) - many toc.yaml sections are optional

---

### Phase 5: MongoDB Storage Layer ✅ (Complete)

**Components Implemented:**
- ✅ Model Layer (`models/section.py` with `SectionDocument` - Pydantic validation)
- ✅ Service Layer (`services/storage_service.py` with `StorageService`)
  - Environment-based configuration (MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION)
  - Full CRUD operations (insert, get, delete, upsert)
  - Query helpers (by company, by section code, by year)
  - Index management for performance
  - Context manager support

**Test Suite:**
- 23 unit tests (100% passing, mocked MongoDB)
- 22 integration tests (100% passing, requires MongoDB)
- Total: 45 tests, ~2.5s execution time
- Coverage: Initialization, CRUD operations, queries, error handling

**Key Experiments:**
- ✅ `exp_11_mongodb_storage.py` - Schema design and storage validation
  - Validated flat document structure (one doc per section)
  - Tested Pydantic validation and conversion
  - Verified MongoDB connection and operations
  - Performance: <2s total workflow (parse + store + verify)

**Key Findings:**
- Flat document structure superior to nested (easier queries, better indexing)
- Composite document_id enables idempotent inserts
- Shared metadata (denormalization) enables efficient time-series queries
- Text flattening sufficient for MVP (structured tables can come later)
- PyMongo collection truthiness issue (use `is None` checks)
- Numerical sorting of atocid required (MongoDB sorts strings alphabetically)

**Schema Design:**
- One document per section (flat, not nested)
- Composite document_id: `{rcept_no}_{section_code}`
- Shared metadata: rcept_no, corp_code, stock_code, year
- Hierarchy: parent_section_code, section_path array
- Text-only content (paragraphs + tables flattened)
- Statistics: char_count, word_count
- Parsing metadata: parsed_at, parser_version

---

### Phase 6: Query Interface & Data Models ✅ (Complete)

**Components Implemented:**
- ✅ Model Layer (`models/metadata.py` with `ReportMetadata` - composition component)
- ✅ Model Layer (`models/sequence.py` with `Sequence` - collection class)
- ✅ API Layer (`api/query.py` with `TextQuery` - user-facing query interface)
- ✅ Configuration Facade (`config.py` extended with `get_app_config()` and `get_toc_mapping()`)

**Test Suite:**
- 78 unit tests for Sequence (100% passing)
- 45 unit tests for StorageService (100% passing)
- Integration tests with live MongoDB
- Total test count: 200+ tests across all phases

**Key Design Decisions:**
- **Composition over Inheritance**: `ReportMetadata` composed into `Sequence`, not inherited
- **Dependency Injection**: `StorageService` injected into `TextQuery` for testability
- **Universal Return Format**: `Dict[year][stock_code] → Sequence` for all research use cases
- **No Wrapper Classes**: Plain dictionary return (no `QueryResult` wrapper)
- **Config Facade Pattern**: All configuration accessed through `config.py` singleton

**Query Interface Design:**
```python
# Initialize with injected StorageService
storage = StorageService()  # User controls DB connection
query = TextQuery(storage_service=storage)

# Single method for all use cases
result = query.get(
    stock_codes=["005930", "000660"],
    years=[2023, 2024],
    section_codes="020100"
)
# Returns: {year: {stock_code: Sequence}}
```

**Research Use Cases Supported:**
1. Single retrieval: Single firm, single year, specific section
2. Cross-sectional: Multiple firms, single year (comparative analysis)
3. Time-series: Single firm, multiple years (temporal analysis)
4. Panel data: Multiple firms, multiple years (econometric models)

**Key Findings:**
- Composition pattern clearer than inheritance for collections with shared metadata
- Dependency injection essential for testability (easy to mock `StorageService`)
- Universal return structure simplifies API (same format for all use cases)
- Config facade ensures single source of truth (no scattered `os.getenv()` calls)

**Showcase Scripts:**
- ✅ `showcase/showcase_01_text_query.py` - Sample data demonstration
- ✅ `showcase/showcase_02_live_data_query.py` - Live DART data integration
  - Downloads and parses Samsung (005930) and SK Hynix (000660) for 2023-2024
  - Demonstrates all 4 research use cases with real MongoDB data
  - Non-interactive (automated testing friendly)

---

### Phase 7: Pipeline Orchestrator (In Progress)

**Planned Components:**
- ⏳ `api/pipeline.py` - `DisclosurePipeline` orchestrator
  - Takes `StorageService` as injected dependency (explicit DB control)
  - `download_and_parse()` method for complete workflow
  - Returns statistics dictionary: `{'reports': N, 'sections': M, 'failed': 0}`
  - Coordinates `FilingSearchService`, XML parsing, and storage

**Design Philosophy:**
- Users establish database connection first (explicit control)
- Inject `StorageService` into pipeline (testability)
- Pipeline handles: search → download → parse → store
- Returns statistics for monitoring and validation

**Next Steps:**
- Implement `DisclosurePipeline` class
- Integrate all components (search, download, parse, store)
- Update `showcase_02_live_data_query.py` to use pipeline
- Performance optimization: Connection pooling, bulk operations

---

## Development Methodology

### Core Principles

1. **Test-Driven Development (TDD)**: Write tests before implementation to ensure code correctness and maintainability
2. **Continuous Live Testing**: Validate assumptions with real DART API data throughout development—don't wait until the end
3. **Experiment-Driven**: Use `experiments/` directory for rapid prototyping and validation with actual data
4. **Incremental Progress**: Build features in small, verifiable steps that compound into robust functionality
5. **Never Fake POC Results** (CRITICAL): Experiments must prove concepts work with real data—no hardcoded workarounds
6. **Fail Loudly in Experiments**: When POC experiments fail, stop and investigate—don't hide errors with fallbacks

**Rationale**: Financial data pipelines require high reliability. TDD + live testing catches edge cases early, while experiments validate domain assumptions that can't be unit-tested. **POC experiments that pass with fake data or hidden errors create false confidence and waste time.**

---

## POC Experiment Rules (Non-Negotiable)

### Rule 1: Real Data Only
**Experiments validate APIs and workflows with live data. No mocks, no hardcoded values.**

❌ **WRONG**:
```python
# If search fails, use known document ID
filings = search_filings(...)
if not filings:
    rcept_no = "20250814003156"  # Hardcoded fallback
```

✅ **CORRECT**:
```python
# If search fails, investigate and fix
filings = search_filings(...)
if not filings:
    raise ValueError("Search failed - need to debug search parameters")
```

### Rule 2: No Silent Failures
**Experiments should fail loudly when assumptions are wrong.**

❌ **WRONG**:
```python
try:
    result = parse_xml(file)
except Exception:
    result = None  # Silent failure
    print("Parsing failed, continuing...")
```

✅ **CORRECT**:
```python
try:
    result = parse_xml(file)
except Exception as e:
    print(f"❌ Parsing failed: {e}")
    print(f"  File: {file}")
    print(f"  This needs investigation before proceeding")
    raise  # Let it fail loudly
```

### Rule 3: Document Why, Not Just What
**Experiments should explain why methods work or don't work.**

❌ **WRONG**:
```python
# This works
filings = search_filings(corp_code, bgn_de, end_de)
```

✅ **CORRECT**:
```python
# NOTE: Must use module-level search_filings() with pblntf_detail_ty
# Corp.search_filings() doesn't filter by report type correctly
# See: https://dart-fss.readthedocs.io/en/latest/dart_search.html
filings = search_filings(
    corp_code=corp_code,
    bgn_de=bgn_de, 
    end_de=end_de,
    pblntf_detail_ty='A001'  # Annual reports
)
```

### Rule 4: Verify Results Make Sense
**Check if results pass the "smell test"—do they match reality?**

❌ **WRONG**:
```python
filings = search_filings(...)
print(f"Found {len(filings)} filings")  # Prints "Found 0 filings"
# Continues anyway...
```

✅ **CORRECT**:
```python
filings = search_filings(...)
print(f"Found {len(filings)} filings")

# Sanity check: Samsung should have annual reports!
if stock_code == "005930" and report_type == "annual":
    if len(filings) == 0:
        print("❌ SANITY CHECK FAILED:")
        print("   Samsung Electronics should have annual reports")
        print("   Search method is likely incorrect")
        raise ValueError("Search returned implausible results")
```

---

## Development Workflow

### Standard Feature Development Process

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

### Workflow Stages Explained

#### Stage 1: Write Experiment
**Purpose**: Rapidly validate feasibility and explore the problem space

**Example**:
```python
# experiments/exp_01_download_document.py
import dart_fss as dart

# Quick-and-dirty script to test document download
dart.set_api_key('YOUR_API_KEY')
document = dart.api.filings.download_document('20240101000001', 'test.zip')
print(f"Downloaded: {document}")

# Manually inspect the XML structure
# Document findings in experiments/data/findings.json
```

**When to Skip**: Simple refactoring or bug fixes with clear solutions

#### Stage 2: Run Live Test
**Purpose**: Inspect real-world data behavior and edge cases

**Key Activities**:
- Download sample documents from various companies
- Examine XML structure variations
- Identify encoding issues or malformed data
- Document unexpected patterns

**Output**: `experiments/data/findings.json` with observations

#### Stage 3: Write Tests
**Purpose**: Formalize requirements as executable specifications

**Example**:
```python
# tests/unit/test_document_parser.py
import pytest
from dart_fss_text.parsers import DocumentParser

def test_parse_section_extracts_text():
    """Parser should extract clean text from section."""
    xml_content = """
    <SECTION USERMARK="F-14 B">
        <P>주요 사업의 내용</P>
    </SECTION>
    """
    parser = DocumentParser()
    section = parser.parse_section(xml_content)
    
    assert section.name == "주요 사업의 내용"
    assert section.usermark == "F-14 B"
```

**Coverage Target**: ≥ 85% for production code

#### Stage 4: Implement Code
**Purpose**: Write production-quality implementation

**Code Quality Checklist**:
- [ ] Type hints on all functions
- [ ] Docstrings with parameter descriptions
- [ ] Error handling with specific exceptions
- [ ] Logging at appropriate levels
- [ ] No magic numbers or hardcoded strings

#### Stage 5: Verify Tests Pass
**Purpose**: Ensure implementation meets specifications

**Command**:
```bash
poetry run pytest tests/unit/ -v --cov
```

#### Stage 6: Run Live Smoke Test
**Purpose**: Validate against real DART data (final reality check)

**Example**:
```bash
poetry run python experiments/exp_01_download_document.py
# Manually verify output matches expectations
```

---

## Experiments Directory Structure

### Organization

```
experiments/
  ├── exp_01_download_document.py      # Validate download mechanics
  ├── exp_02_parse_xml_structure.py    # Explore XML patterns
  ├── exp_03_filing_search.py          # Test dart-fss search APIs
  ├── exp_04_metadata_extraction.py    # Validate PIT metadata
  ├── exp_05_section_identification.py # Map USERMARK to section names
  ├── exp_06_table_parsing.py          # Extract and structure tables
  └── data/                            # Downloaded samples & findings
      ├── raw/                         # Raw XML samples
      │   ├── 20240101000001.xml
      │   ├── 20230615000002.xml
      │   └── ...
      ├── findings.json                # Documented observations
      └── analysis/                    # Ad-hoc analysis notebooks
          └── xml_structure_analysis.ipynb
```

### Experiment Naming Convention

**Format**: `exp_{NN}_{brief_description}.py`

**Guidelines**:
- Use sequential numbering (01, 02, ...)
- Keep descriptions brief (3-5 words)
- Focus on one concept per experiment

### Sample Experiment Template

```python
"""
Experiment: {Brief Title}
Date: YYYY-MM-DD
Purpose: {One-sentence description of what we're validating}

Hypothesis: {What we expect to happen}
Success Criteria: {How we'll know if it works}
"""

import dart_fss as dart
from pathlib import Path
import json

# Configuration
API_KEY = "YOUR_API_KEY"  # Use environment variable in practice
RCEPT_NO = "20240101000001"
OUTPUT_DIR = Path("experiments/data/raw")

# Experiment code
def main():
    dart.set_api_key(API_KEY)
    
    # Download document
    output_path = OUTPUT_DIR / f"{RCEPT_NO}.zip"
    dart.api.filings.download_document(RCEPT_NO, str(output_path))
    
    # Validate result
    assert output_path.exists(), "Download failed"
    print(f"✓ Successfully downloaded to {output_path}")
    
    # Document findings
    findings = {
        "date": "2024-03-25",
        "rcept_no": RCEPT_NO,
        "file_size_mb": output_path.stat().st_size / 1024 / 1024,
        "observations": [
            "ZIP contains single XML file",
            "XML uses UTF-8 encoding",
            "Sections marked with USERMARK attribute"
        ]
    }
    
    findings_path = OUTPUT_DIR / "findings.json"
    with open(findings_path, 'w', encoding='utf-8') as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Findings saved to {findings_path}")

if __name__ == "__main__":
    main()
```

---

## Testing Strategy

### Test Types & Purposes

| Test Type | Purpose | Location | Execution Speed | CI Integration |
|-----------|---------|----------|----------------|----------------|
| **Unit Tests** | Validate isolated logic | `tests/unit/` | Fast (< 1s) | Every commit |
| **Integration Tests** | Verify component interactions | `tests/integration/` | Medium (< 10s) | Every commit |
| **End-to-End Tests** | Full pipeline validation | `tests/e2e/` | Slow (> 1min) | Pre-release only |
| **Smoke Tests** | Manual reality checks | `experiments/` | Variable | Manual |
| **Regression Tests** | Prevent known bugs | `tests/regression/` | Fast | Every commit |

### Unit Tests

**Focus**: Pure functions with no external dependencies

**Examples**:
- Text cleaning functions
- USERMARK pattern parsing
- Section name normalization
- Table row/column extraction

**Mocking Strategy**: Mock all external calls (dart-fss, MongoDB, filesystem)

**Example**:
```python
# tests/unit/test_text_cleaning.py
import pytest
from dart_fss_text.utils import clean_text

def test_clean_text_removes_extra_whitespace():
    """clean_text should normalize whitespace."""
    input_text = "당사는    반도체\n\n제조"
    expected = "당사는 반도체 제조"
    
    result = clean_text(input_text)
    
    assert result == expected

@pytest.mark.parametrize("input_text,expected", [
    ("", ""),
    ("   ", ""),
    ("\n\n\n", ""),
])
def test_clean_text_handles_empty_strings(input_text, expected):
    """clean_text should handle edge cases."""
    assert clean_text(input_text) == expected
```

### Integration Tests

**Focus**: Component interactions with mocked external services

**Examples**:
- MongoDB storage operations (with test database)
- Document parser with filesystem (temp directories)
- dart-fss adapter (with mocked API responses)

**Setup/Teardown**: Use pytest fixtures for clean test isolation

**Example**:
```python
# tests/integration/test_storage_manager.py
import pytest
from mongomock import MongoClient
from dart_fss_text.storage import StorageManager
from dart_fss_text.models import FilingMetadata, Section

@pytest.fixture
def storage_manager():
    """Provide StorageManager with mock MongoDB."""
    client = MongoClient()
    db = client["test_dart_disclosures"]
    manager = StorageManager(db)
    yield manager
    client.drop_database("test_dart_disclosures")

def test_insert_filing_stores_metadata(storage_manager):
    """StorageManager should persist filing metadata."""
    metadata = FilingMetadata(
        stock_code="005930",
        company_name="삼성전자",
        report_type="A001",
        published_date=datetime(2024, 3, 15),
        rcept_no="20240101000001",
        filing_url="https://dart.fss.or.kr/..."
    )
    sections = [
        Section(name="주요 사업의 내용", usermark="F-14 B", ...)
    ]
    
    filing_id = storage_manager.insert_filing(metadata, sections)
    
    assert filing_id is not None
    retrieved = storage_manager.get_filing(filing_id)
    assert retrieved.stock_code == "005930"
```

### End-to-End Tests

**Focus**: Complete pipeline with real DART API (marked for CI skip)

**When to Run**: Before releases, manually by developers

**Example**:
```python
# tests/e2e/test_complete_pipeline.py
import pytest
import os

@pytest.mark.skipif(
    not os.getenv("RUN_E2E_TESTS"),
    reason="E2E tests require real DART API (set RUN_E2E_TESTS=1)"
)
def test_fetch_and_store_samsung_annual_report():
    """Full pipeline: search → download → parse → store."""
    from dart_fss_text import DisclosurePipeline
    
    pipeline = DisclosurePipeline(
        mongo_uri=os.getenv("TEST_MONGO_URI"),
        dart_api_key=os.getenv("DART_API_KEY")
    )
    
    result = pipeline.fetch_and_store(
        stock_codes=["005930"],
        start_date="2024-01-01",
        end_date="2024-12-31",
        report_types=["annual"]
    )
    
    assert result["downloaded"] >= 1
    assert result["parsed"] >= 1
    assert result["stored"] >= 1
    assert result["failed"] == 0
```

### Regression Tests

**Focus**: Prevent recurrence of known bugs

**Approach**: Save XML fixtures that previously caused failures

**Example**:
```python
# tests/regression/test_malformed_xml.py
import pytest
from pathlib import Path
from dart_fss_text.parsers import DocumentParser

def test_parser_handles_missing_usermark():
    """Regression: Parser crashed on sections without USERMARK (Issue #15)."""
    fixture_path = Path("tests/fixtures/xml/missing_usermark.xml")
    parser = DocumentParser()
    
    # Should not raise exception
    sections = parser.parse(fixture_path)
    
    # Should still extract sections using fallback heuristics
    assert len(sections) > 0
```

---

## Code Quality Standards

### Type Hints

**Requirement**: All public functions and methods must have type hints

**Example**:
```python
from typing import List, Dict, Optional
from pathlib import Path

def parse_section(
    xml_path: Path,
    section_name: str,
    fallback: Optional[str] = None
) -> Optional[Section]:
    """
    Parse a specific section from XML document.
    
    Args:
        xml_path: Path to XML file
        section_name: Semantic section name to extract
        fallback: Fallback USERMARK pattern if section_name not found
    
    Returns:
        Parsed Section object, or None if section not found
    
    Raises:
        ValueError: If xml_path does not exist
        ParseError: If XML is malformed
    """
    ...
```

### Docstrings

**Style**: Google-style docstrings

**Required Elements**:
- One-line summary
- Args section (parameter descriptions)
- Returns section
- Raises section (if applicable)

### Error Handling

**Principle**: Be specific with exceptions

**Bad**:
```python
def parse_document(path):
    try:
        # ... parsing logic
    except Exception as e:  # Too broad
        print(f"Error: {e}")  # Silent failure
        return None
```

**Good**:
```python
def parse_document(path: Path) -> Document:
    if not path.exists():
        raise FileNotFoundError(f"XML file not found: {path}")
    
    try:
        tree = etree.parse(str(path))
    except etree.XMLSyntaxError as e:
        raise ParseError(f"Malformed XML in {path}: {e}") from e
    
    # ... rest of parsing logic
```

### Logging

**Levels**:
- **DEBUG**: Detailed parsing steps, intermediate values
- **INFO**: Pipeline progress, document counts
- **WARNING**: Unexpected structures, partial failures
- **ERROR**: Critical failures requiring attention

**Example**:
```python
import logging

logger = logging.getLogger(__name__)

def parse_document(path: Path) -> Document:
    logger.info(f"Parsing document: {path.name}")
    
    sections = self._extract_sections(path)
    logger.debug(f"Extracted {len(sections)} sections")
    
    if len(sections) == 0:
        logger.warning(f"No sections found in {path.name} - possible format issue")
    
    return Document(sections=sections, ...)
```

---

## Configuration Management

### Config Facade Pattern

All configuration is accessed through a centralized facade in `config.py` to ensure consistency and maintainability.

**Design Principle**: Single source of truth for all configuration—no scattered `os.getenv()` calls or hardcoded paths.

**Config Facade Components**:

```python
# src/dart_fss_text/config.py

# 1. Application Config (from .env)
class AppConfig(BaseSettings):
    """Runtime configuration from environment variables."""
    mongo_host: str = Field(default="localhost:27017")
    db_name: str = Field(default="FS")
    collection_name: str = Field(default="A001")
    opendart_api_key: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file='.env',
        case_sensitive=False
    )
    
    @property
    def mongodb_uri(self) -> str:
        return f"mongodb://{self.mongo_host}/"

# Singleton accessor
def get_app_config() -> AppConfig:
    """Get cached application config."""
    ...

# 2. TOC Mapping (from config/toc.yaml)
def get_toc_mapping(report_type: str = 'A001') -> Dict[str, str]:
    """Get cached TOC mapping for report type."""
    ...

# 3. Report Types Config (from config/types.yaml)
def get_config() -> ReportTypesConfig:
    """Get cached report types config."""
    ...
```

**Usage Across Codebase**:

```python
# ✅ CORRECT: Use config facade
from dart_fss_text.config import get_app_config, get_toc_mapping

config = get_app_config()
storage = StorageService(
    mongo_uri=config.mongodb_uri,
    database=config.mongodb_database,
    collection=config.mongodb_collection
)

toc = get_toc_mapping('A001')
section_code = toc.get('I. 회사의 개요')
```

```python
# ❌ WRONG: Direct environment variable access
import os
from dotenv import load_dotenv

load_dotenv()
mongo_uri = os.getenv("MONGODB_URI")  # Scattered, inconsistent
```

**Benefits**:
- ✅ Single source of truth (no duplicate loading logic)
- ✅ Consistent access pattern across codebase
- ✅ Easier testing (mock `get_app_config()` instead of `os.getenv()`)
- ✅ Caching (singleton pattern prevents redundant file reads)
- ✅ Type safety (Pydantic validation)

---

## Parameter Validation & Discovery

### Specification-Based Validation with Pydantic Settings

All parameters defined in `config/types.yaml` are validated using **Pydantic Settings** for automatic, type-safe configuration management.

### Architecture Overview

**4-Layer Design**:
1. **Config Layer**: Pydantic Settings auto-loads YAML
2. **Validator Layer**: Reusable field validators
3. **Model Layer**: Request/response models with validators
4. **Discovery Layer**: Helper classes for exploring options

---

### Layer 1: Config Management (Pydantic Settings)

```python
# src/dart_fss_text/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict

class ReportTypesConfig(BaseSettings):
    """
    Configuration automatically loaded from config/types.yaml.
    Pydantic Settings handles file resolution and parsing.
    """
    
    pblntf_detail_ty: Dict[str, str] = Field(
        description="Valid report type codes with Korean descriptions"
    )
    corp_cls: Dict[str, str] = Field(
        description="Corporation classification codes (KOSPI, KOSDAQ, etc.)"
    )
    rm: Dict[str, str] = Field(
        description="Remark codes for filing metadata"
    )
    
    model_config = SettingsConfigDict(
        yaml_file='config/types.yaml',
        yaml_file_encoding='utf-8',
        extra='ignore'
    )
    
    def is_valid_report_type(self, code: str) -> bool:
        """Check if report type code is valid."""
        return code in self.pblntf_detail_ty
    
    def get_report_description(self, code: str) -> str:
        """Get description for report type."""
        if code not in self.pblntf_detail_ty:
            raise KeyError(f"Unknown report type: {code}")
        return self.pblntf_detail_ty[code]


# Singleton pattern - loaded once, cached forever
_config: ReportTypesConfig = None

def get_config() -> ReportTypesConfig:
    """Get global config instance (lazy-loaded)."""
    global _config
    if _config is None:
        _config = ReportTypesConfig()
    return _config
```

**Benefits**:
- ✅ No manual path traversal (`.parent.parent`)
- ✅ Automatic YAML parsing and validation
- ✅ Type-safe config access
- ✅ Lazy loading with singleton pattern

---

### Layer 2: Reusable Validators

```python
# src/dart_fss_text/validators.py
from typing import List
from pydantic import ValidationError

def validate_report_types(codes: List[str]) -> List[str]:
    """
    Reusable validator for report type codes.
    Use with @field_validator in Pydantic models.
    
    Raises:
        ValueError: If any code is invalid
    """
    config = get_config()
    invalid = [c for c in codes if not config.is_valid_report_type(c)]
    
    if invalid:
        valid_sample = list(config.pblntf_detail_ty.keys())[:10]
        raise ValueError(
            f"Invalid report type codes: {invalid}\n"
            f"Valid codes include: {valid_sample}...\n"
            f"Use ReportTypes.list_available() to see all options."
        )
    
    return codes


def validate_stock_code(code: str) -> str:
    """Validate Korean stock code format (6 digits)."""
    if not code.isdigit() or len(code) != 6:
        raise ValueError(
            f"Stock code must be 6 digits, got: '{code}'\n"
            f"Example: '005930' (Samsung Electronics)"
        )
    return code


def validate_date_yyyymmdd(date: str) -> str:
    """Validate YYYYMMDD date format."""
    if not date.isdigit() or len(date) != 8:
        raise ValueError(
            f"Date must be YYYYMMDD format, got: '{date}'\n"
            f"Example: '20240101'"
        )
    # Optional: Add date range validation
    year = int(date[:4])
    if year < 1980 or year > 2100:
        raise ValueError(f"Year {year} is out of valid range (1980-2100)")
    return date
```

---

### Layer 3: Pydantic Models with Validation

```python
# src/dart_fss_text/models/requests.py
from pydantic import BaseModel, field_validator
from typing import List

class SearchFilingsRequest(BaseModel):
    """
    Request model for Phase 1: search_filings() validation.
    All fields are automatically validated against types.yaml.
    
    Status: ✅ Implemented and tested (v0.1.0)
    """
    stock_codes: List[str]  # Multiple stock codes for batch operations
    start_date: str
    end_date: str
    report_types: List[str]
    
    # Apply validators using field_validator decorator
    @field_validator('stock_codes')
    @classmethod
    def validate_stock_codes_list(cls, v: List[str]) -> List[str]:
        """Validate each stock code in the list."""
        return [validate_stock_code(code) for code in v]
    
    _validate_start_date = field_validator('start_date')(validate_date_yyyymmdd)
    _validate_end_date = field_validator('end_date')(validate_date_yyyymmdd)
    _validate_report_types = field_validator('report_types')(validate_report_types)
    
    model_config = {
        "frozen": True,  # Immutable model
        "json_schema_extra": {
            "examples": [{
                "stock_codes": ["005930", "000660"],
                "start_date": "20240101",
                "end_date": "20241231",
                "report_types": ["A001", "A002"]  # Actual DART codes
            }]
        }
    }
```

**Usage in Pipeline**:
```python
class DisclosurePipeline:
    def fetch_reports(
        self, 
        stock_codes: List[str], 
        start_date: str, 
        end_date: str, 
        report_types: List[str]
    ) -> Dict[str, int]:
        """
        Search, download, parse, and store filings.
        
        Note: dart-fss get_corp_list() uses Singleton pattern - first call
        takes ~7s, all subsequent calls are instant (0.000ms).
        
        Status: Search phase implemented (v0.1.0), download/parse/store pending.
        """
        # Validation happens automatically via Pydantic
        request = SearchFilingsRequest(
            stock_codes=stock_codes,
            start_date=start_date,
            end_date=end_date,
            report_types=report_types  # Actual codes like ["A001", "A002"]
        )
        
        # Now guaranteed all inputs are valid!
        # FilingSearchService handles stock→corp conversion internally
        search_service = FilingSearchService()
        filings = search_service.search_filings(request)
        
        # Proceed with download, parse, store (TODO: Phase 2-4)...
```

---

### Layer 4: Discovery Helpers

```python
# src/dart_fss_text/types.py
from typing import Dict

class ReportTypes:
    """Helper class for discovering available report types."""
    
    @staticmethod
    def list_available() -> Dict[str, str]:
        """List all valid report type codes from types.yaml."""
        return get_config().pblntf_detail_ty.copy()
    
    @staticmethod
    def list_periodic() -> Dict[str, str]:
        """List only periodic report types (A001, A002, A003)."""
        all_types = get_config().pblntf_detail_ty
        periodic_codes = ['A001', 'A002', 'A003']
        return {k: v for k, v in all_types.items() if k in periodic_codes}
    
    @staticmethod
    def list_by_category(prefix: str) -> Dict[str, str]:
        """List report types by category (A, B, C, etc.)."""
        all_types = get_config().pblntf_detail_ty
        return {k: v for k, v in all_types.items() if k.startswith(prefix)}
    
    @staticmethod
    def get_description(code: str) -> str:
        """Get description for a report type code."""
        return get_config().get_report_description(code)


# Example usage
class CorpClass:
    """Helper for discovering corporation classifications."""
    
    @staticmethod
    def list_available() -> Dict[str, str]:
        """List all corp_cls codes (KOSPI, KOSDAQ, etc.)."""
        return get_config().corp_cls.copy()
```

**User-Facing Discovery**:
```python
# Users discover valid codes before calling fetch_reports()
from dart_fss_text import ReportTypes

# See all available report types
all_types = ReportTypes.list_available()
# → {'A001': '사업보고서', 'A002': '반기보고서', ...}

# Get only periodic reports (MVP focus)
periodic = ReportTypes.list_periodic()
# → {'A001': '사업보고서', 'A002': '반기보고서', 'A003': '분기보고서'}

# Then use actual codes in fetch_reports()
pipeline.fetch_reports(
    stock_codes=["005930"],
    start_date="20240101",
    end_date="20241231",
    report_types=["A001", "A002"]  # Use codes directly, no aliases
)
```

**CLI Integration**:
```python
@click.command()
def list_types():
    """List all available report types."""
    types = ReportTypes.list_available()
    for code, desc in sorted(types.items()):
        click.echo(f"{code}: {desc}")

@click.command()
@click.option('--category', default='A', help='Report category (A, B, C, etc.)')
def list_category(category: str):
    """List report types by category."""
    types = ReportTypes.list_by_category(category)
    for code, desc in sorted(types.items()):
        click.echo(f"{code}: {desc}")
```




## Git Workflow

### Branch Strategy

**Main Branches**:
- `main`: Production-ready code
- `develop`: Integration branch for features

**Feature Branches**:
- Format: `feature/{issue-number}-{brief-description}`
- Example: `feature/42-mongodb-storage-layer`

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation updates
- `refactor`: Code restructuring without behavior change
- `test`: Test additions or modifications
- `chore`: Maintenance tasks

**Example**:
```
feat(parser): add table extraction from XML sections

Implement TableParser class that extracts <TABLE> elements
from XML sections and converts them to structured Table objects.

- Support for headers and data rows
- Handle merged cells with colspan/rowspan
- Preserve context text surrounding tables

Closes #23
```

### Pull Request Checklist

Before submitting PR, ensure:
- [ ] All tests pass (`poetry run pytest`)
- [ ] Code coverage ≥ 85% for new code
- [ ] Type hints on all new functions
- [ ] Docstrings on all public APIs
- [ ] No linter errors (`poetry run pylint src/`)
- [ ] Experiment validates feature with live data
- [ ] Update relevant documentation
- [ ] Add entry to CHANGELOG.md

---

## Environment Setup

### Development Environment

**Prerequisites**:
- Python ≥ 3.12
- Poetry for dependency management
- MongoDB instance (local or Atlas)
- DART API key (from https://opendart.fss.or.kr/)

**Setup Steps**:

```bash
# Clone repository
git clone https://github.com/your-org/dart-fss-text.git
cd dart-fss-text

# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your DART_API_KEY and MONGODB_URI

# Run tests to verify setup
poetry run pytest
```

### Environment Variables

```bash
# .env file
DART_API_KEY=your_api_key_here
MONGODB_URI=mongodb://localhost:27017/dart_disclosures
LOG_LEVEL=INFO
RAW_XML_PATH=./data/raw
```

### IDE Configuration

**Recommended**: Visual Studio Code with extensions:
- Python (Microsoft)
- Pylance (type checking)
- Pytest (test discovery)

**settings.json**:
```json
{
  "python.linting.pylintEnabled": true,
  "python.linting.enabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "editor.formatOnSave": true
}
```

---

## Debugging Tips

### Common Issues

#### Issue 1: XML Parsing Fails with Encoding Error
**Symptom**: `UnicodeDecodeError` when loading XML

**Solution**:
```python
# Explicitly specify encoding
with open(xml_path, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
```

#### Issue 2: MongoDB Connection Timeout
**Symptom**: `ServerSelectionTimeoutError`

**Check**:
1. MongoDB is running: `systemctl status mongod` (Linux) or check Docker
2. Connection string is correct (check port, database name)
3. Firewall allows connection

#### Issue 3: DART API Rate Limit
**Symptom**: `HTTP 429 Too Many Requests`

**Solution**: Implement exponential backoff
```python
import time
from functools import wraps

def retry_on_rate_limit(max_retries=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError:
                    if attempt == max_retries - 1:
                        raise
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
            return None
        return wrapper
    return decorator
```

---

## Performance Optimization

### Profiling

**CPU Profiling**:
```bash
poetry run python -m cProfile -o output.prof experiments/exp_02_parse_xml.py
poetry run python -m pstats output.prof
```

**Memory Profiling**:
```bash
poetry install --with dev
poetry run mprof run experiments/exp_02_parse_xml.py
poetry run mprof plot
```

### Optimization Checklist

- [ ] Use streaming XML parsing for large documents (`iterparse`)
- [ ] Implement connection pooling for MongoDB
- [ ] Cache parsed sections in memory (LRU cache)
- [ ] Parallelize downloads with `asyncio` or `concurrent.futures`
- [ ] Use MongoDB bulk operations for batch inserts

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mongodb:
        image: mongo:7.0
        ports:
          - 27017:27017
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install Poetry
        run: pip install poetry
      
      - name: Install dependencies
        run: poetry install
      
      - name: Run linters
        run: |
          poetry run pylint src/
          poetry run mypy src/
      
      - name: Run tests
        run: poetry run pytest --cov --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Documentation Standards

### Code Documentation
- All modules: Module-level docstring explaining purpose
- All classes: Class docstring with overview and usage example
- All public functions: Full docstring with Args/Returns/Raises

### Project Documentation
- **README.md**: Installation, quick start, basic examples
- **CHANGELOG.md**: Version history with breaking changes noted
- **CONTRIBUTING.md**: How to contribute (setup, workflow, standards)
- **API_REFERENCE.md**: Generated from docstrings (Sphinx)

---

**Last Updated**: 2025-10-04  
**Version**: 1.2  
**Status**: Active Development (Phase 7 in progress - Pipeline Orchestrator)

