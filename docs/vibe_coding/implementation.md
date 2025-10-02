# Implementation Guide: dart-fss-text

## Development Methodology

### Core Principles

1. **Test-Driven Development (TDD)**: Write tests before implementation to ensure code correctness and maintainability
2. **Continuous Live Testing**: Validate assumptions with real DART API data throughout development—don't wait until the end
3. **Experiment-Driven**: Use `experiments/` directory for rapid prototyping and validation with actual data
4. **Incremental Progress**: Build features in small, verifiable steps that compound into robust functionality

**Rationale**: Financial data pipelines require high reliability. TDD + live testing catches edge cases early, while experiments validate domain assumptions that can't be unit-tested.

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

**Last Updated**: 2025-10-02  
**Version**: 1.0  
**Status**: Draft

