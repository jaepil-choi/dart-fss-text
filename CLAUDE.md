# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**dart-fss-text** is a Python library for extracting and structuring text data from Korean DART (Data Analysis, Retrieval and Transfer System) business reports. Unlike dart-fss which focuses on numerical financial data, this library extracts narrative text content organized by table of contents sections for NLP analysis and research.

**Core Purpose**: Enable automated extraction of structured text from DART annual reports (사업보고서) for text analysis, academic research, and quantitative studies.

## Environment

- **OS**: Windows
- **Shell**: PowerShell (use PowerShell commands, NOT Unix/Linux commands)
- **Python**: 3.12.x (strictly enforced, ≥3.12, <3.13)
- **Package Manager**: Poetry (always use `poetry run` prefix for Python commands)

## Development Commands

### Environment Setup

```powershell
# Install dependencies
poetry install

# Activate virtual environment (if needed)
poetry shell
```

### Testing

```powershell
# Run all tests (excluding smoke tests by default)
poetry run pytest

# Run only unit tests (fast, no network)
poetry run pytest -m unit

# Run integration tests (may touch filesystem/network)
poetry run pytest -m integration

# Run smoke tests (requires API key and DART API access)
poetry run pytest -m smoke

# Run specific test file
poetry run pytest tests/path/to/test_file.py

# Run with verbose output and full traceback
poetry run pytest -v --tb=long
```

**Important**: Smoke tests are disabled by default via pytest configuration (`-m "not smoke"`). They require a valid OPENDART_API_KEY in `.env` and make live API calls.

### Running Showcase Scripts

```powershell
# Sample data demo (uses test fixtures)
poetry run python showcase/showcase_01_text_query.py

# Live DART data integration (requires API key)
poetry run python showcase/showcase_02_live_data_query.py

# High-level API demo
poetry run python showcase/showcase_03_disclosure_pipeline.py
```

### Data Collection

```powershell
# Collect data for specific companies and years
poetry run python collect_data.py

# Backfill historical data
poetry run python backfill_data.py
```

### PowerShell Commands (NOT Unix commands)

```powershell
# List files (use Get-ChildItem, not ls)
Get-ChildItem
Get-ChildItem -Path src/ -Recurse

# Find files
Get-ChildItem -Recurse -Filter "*.py"

# Search content (use Select-String, not grep)
Select-String -Path "*.py" -Pattern "TODO"

# Remove files/directories
Remove-Item file.txt
Remove-Item -Recurse -Force directory/

# Copy files
Copy-Item source.txt destination.txt

# Move files
Move-Item source.txt destination.txt

# Create directory
New-Item -ItemType Directory -Path new_folder
```

## Git Workflow

### Important Git Rules

**NEVER use `git add .` or `git add -A`**

Always specify files explicitly when staging:

```powershell
# ✅ CORRECT: Specify files explicitly
git add src/dart_fss_text/api/query.py
git add tests/test_query.py
git add CLAUDE.md

# ✅ CORRECT: Add multiple specific files
git add src/dart_fss_text/api/query.py src/dart_fss_text/api/pipeline.py

# ❌ WRONG: Never use blanket add
git add .
git add -A
git add --all
```

### Standard Git Commands

```powershell
# Check status
git status

# Stage specific files only
git add path/to/file1.py path/to/file2.py

# Commit with message
git commit -m "feat: add new feature"

# Push to remote
git push origin branch-name

# Create new branch
git checkout -b feature/new-feature

# View diff
git diff
git diff --staged
```

## Architecture

### Module Structure

```
src/dart_fss_text/
├── api/              # User-facing high-level interfaces
│   ├── query.py      # TextQuery: retrieve stored sections
│   ├── pipeline.py   # DisclosurePipeline: download & parse workflow
│   └── backfill.py   # BackfillService: bulk data collection
├── models/           # Data models and schemas
│   ├── section.py    # SectionDocument: MongoDB schema
│   ├── sequence.py   # Sequence: collection wrapper
│   ├── metadata.py   # Filing metadata models
│   └── requests.py   # API request/response models
├── parsers/          # XML and text parsing
│   ├── xml_parser.py         # XML structure parsing
│   ├── section_parser.py     # Section extraction logic
│   ├── section_matcher.py    # Text-based section matching
│   └── table_parser.py       # Table flattening
├── services/         # Core business logic
│   ├── storage_service.py    # MongoDB CRUD operations
│   ├── filing_search.py      # DART API search wrapper
│   └── document_download.py  # ZIP download & extraction
├── config.py         # Configuration management
├── types.py          # Type definitions
└── validators.py     # Input validation utilities

config/
├── toc.yaml          # Table of contents mapping (section codes)
└── types.yaml        # DART API type specifications
```

### Key Design Patterns

**1. Dependency Injection for Services**
- `StorageService`, `FilingSearchService`, and `DocumentDownloadService` are injected into higher-level components
- Enables testing with mock dependencies
- Example: `TextQuery(storage_service=storage)`, `DisclosurePipeline(storage_service=storage)`

**2. Config Facade Pattern**
- `get_config()`: YAML-based DART specifications (report types, TOC mapping)
- `get_app_config()`: Environment-based runtime config (.env)
- `get_toc_mapping()`: Section code mappings for A001 reports
- All configs are lazy-loaded singletons cached in memory

**3. Collection Pattern (Sequence)**
- `Sequence` wraps multiple `SectionDocument` objects
- Provides list-like access (`sequence[0]`, `sequence[1:3]`)
- Supports dict-like lookup by section code (`sequence["020100"]`)
- Aggregates text via `.text` property
- This is the primary return type for `TextQuery.get()`

**4. Text-Based Section Matching**
- Parser uses fuzzy text matching against `config/toc.yaml` titles
- Resilient to XML attribute changes across years (2010-2024 support)
- See `parsers/section_matcher.py` for implementation

**5. Encoding Fallback Strategy**
- Primary: UTF-8 parsing
- Fallback: EUC-KR for older reports (pre-2015)
- See `parsers/xml_parser.py:parse_xml_file()`

### Data Flow

```
User Request
    ↓
TextQuery.get(stock_codes, years, section_codes)
    ↓
StorageService.query_sections() → MongoDB
    ↓
Returns: Dict[year, Dict[stock_code, Sequence[SectionDocument]]]

Data Collection Pipeline
    ↓
DisclosurePipeline.download_and_parse()
    ↓
FilingSearchService → Search DART API
    ↓
DocumentDownloadService → Download ZIP files
    ↓
XMLParser → Parse XML structure
    ↓
SectionParser → Extract sections with text matching
    ↓
StorageService → Save to MongoDB
```

### MongoDB Schema

**Collection**: Configured via `COLLECTION_NAME` in `.env` (default: `A001`)

**Document Structure** (SectionDocument):
```python
{
    "document_id": str,      # {rcept_no}_{section_code}
    "rcept_no": str,         # Filing receipt number
    "stock_code": str,       # 6-digit stock code
    "corp_name": str,        # Company name (Korean)
    "year": str,             # Filing year (YYYY)
    "section_code": str,     # 6-digit code (e.g., "020000")
    "section_title": str,    # Korean title
    "level": int,            # TOC hierarchy level (1-4)
    "section_path": list,    # Hierarchical path of codes
    "text": str,             # Extracted text content
    "char_count": int,       # Character count
    "word_count": int,       # Word count
    "parsed_at": str,        # ISO timestamp
    "parser_version": str    # Parser version string
}
```

**Indexes**: `document_id` (unique), compound index on `(stock_code, year, section_code)`

## Configuration

### Required Files

**`.env`** (copy from `.env.example`):
```bash
OPENDART_API_KEY=your_api_key_here  # Get from https://opendart.fss.or.kr/
MONGO_HOST=localhost:27017
DB_NAME=FS
COLLECTION_NAME=A001
```

**`config/toc.yaml`**: Defines standard section codes for A001 reports (already exists)

**`config/types.yaml`**: DART API type specifications (already exists)

### Section Codes (config/toc.yaml)

Key sections to know:
- `010000`: I. 회사의 개요 (Company Overview)
- `020000`: II. 사업의 내용 (Business Description)
- `030000`: III. 재무에 관한 사항 (Financial Matters)
- `040000`: IV. 감사인의 감사의견 등 (Auditor's Opinion)
- `050000`: V. 이사회 등 회사의 기관에 관한 사항 (Board & Governance)

Each top-level section has nested subsections (e.g., `020100`, `020200`). See `config/toc.yaml` for full hierarchy.

### Report Types (config/types.yaml)

- `A001`: 사업보고서 (Annual Report) - **Primary focus**
- `A002`: 반기보고서 (Semi-Annual Report)
- `A003`: 분기보고서 (Quarterly Report)

Currently, the library is optimized for A001 reports.

## Development Methodology

### Experiment-Driven Development

This codebase follows **Experiment-Driven Development** as defined in `.cursor/rules/experiment-driven-development.mdc`. Key principles:

**1. Experiment Before Implementing**
- All features start with experiments in `experiments/` directory
- Experiments validate assumptions with real DART data
- See `experiments/FINDINGS.md` for documented learnings

**2. Document-Driven Workflow**
- Read documents BEFORE coding: `docs/vibe_coding/{prd.md, architecture.md, implementation.md}`
- Update documents when discoveries change understanding
- Architecture documents are living artifacts, not write-once specs

**3. Observable Experiments**
- Experiments use verbose `print()` output for LLM observability
- Example pattern:
  ```python
  print("="*60)
  print(f"Testing: {hypothesis}")
  print(f"Result: {actual}")
  print("✓ SUCCESS" if valid else "✗ FAILURE")
  print("="*60)
  ```

**4. Failed Experiments as Lessons**
- Failed experiments are marked `OBSOLETE` with explanations
- They document what NOT to do and why
- Example: `experiments/exp_03b_direct_pipeline_LESSONS.py`

### When Working on New Features

1. **Experiment First**: Create `experiments/exp_XX_feature_name.py` to validate approach
2. **Document Findings**: Update `experiments/FINDINGS.md` with discoveries
3. **Write Tests**: Create tests in `tests/` based on experiment results
4. **Implement**: Follow TDD (red-green-refactor) using documented architecture
5. **Update Docs**: If architecture changed, update `docs/vibe_coding/architecture.md`

## Common Development Tasks

### Adding Support for New Report Types

1. Update `config/types.yaml` if needed (DART types already defined)
2. Create new TOC mapping in `config/toc.yaml` for the report type
3. Update `get_toc_mapping()` in `config.py` to handle the new type
4. Run experiments to validate XML structure matches A001 assumptions
5. Update parsers if structure differs significantly

### Testing Against Live DART Data

```powershell
# Ensure .env has valid OPENDART_API_KEY
poetry run pytest -m smoke

# Or run specific showcase script
poetry run python showcase/showcase_02_live_data_query.py
```

### Debugging XML Parsing Issues

1. Use experiment scripts to inspect XML structure:
   ```python
   from dart_fss_text.parsers.xml_parser import XMLParser
   parser = XMLParser()
   tree = parser.parse_xml_file("path/to/file.xml")
   # Add verbose print statements to explore structure
   ```

2. Check encoding issues: Files from ~2010-2014 may need EUC-KR fallback
3. Verify section matching: Check `config/toc.yaml` titles match XML text content

### Working with MongoDB

```python
from dart_fss_text import StorageService

storage = StorageService()

# Save sections
storage.save_sections([section_doc1, section_doc2])

# Query sections
results = storage.query_sections(
    stock_codes=["005930"],
    years=[2024],
    section_codes=["020000"]
)

# Check connection
# MongoDB should be running on MONGO_HOST from .env
```

## Important Implementation Notes

### Data Coverage Limitations

- **Year Range**: 2010-2024 (DART XML format started in 2010)
- **Report Versions**: Only latest version of each report is stored (latest정정공시 overwrites originals)
- **Market Coverage**: KOSPI, KOSDAQ, KONEX listed companies only

### Text Extraction Behavior

- Tables are flattened to text format (MVP approach)
- HTML tags are stripped
- Multiple spaces/newlines are normalized
- See `parsers/table_parser.py:TableParser.flatten_table_to_text()`

### Section Matching Strategy

The parser uses **text-based fuzzy matching** instead of relying on XML attributes:
- Searches for TOC titles (from `config/toc.yaml`) in XML text content
- Uses similarity threshold for matching
- This approach is resilient to XML schema changes across years
- See experiments/exp_13_text_based_section_matching.py for validation

### Error Handling Philosophy

- **Fail Fast**: Invalid API keys, missing MongoDB, bad stock codes raise immediately
- **Graceful Degradation**: Encoding fallback (UTF-8 → EUC-KR)
- **Clear Messages**: All errors include actionable context

## Testing Strategy

### Test Markers

- `@pytest.mark.unit`: Fast, isolated, no external dependencies
- `@pytest.mark.integration`: May touch filesystem or mock network
- `@pytest.mark.smoke`: Live DART API calls (requires API key)

### Test Data

- Unit tests use fixtures in `tests/fixtures/`
- Integration tests may use sample XML files in `experiments/data/`
- Smoke tests hit real DART API with configured credentials

### Coverage Goals

- Target: 90%+ coverage (current status per README)
- Critical paths: parsers, storage, query logic
- Less critical: showcase scripts, experiment code

## Dependencies

**Core Runtime**:
- `dart-fss` (≥0.4.14): DART API wrapper for search/download
- `pymongo` (≥4.15.2): MongoDB driver
- `lxml` (≥6.0.2): XML parsing
- `pydantic` (≥2.11.9): Data validation
- `pyyaml` (≥6.0.3): Config file parsing

**Development**:
- `pytest` (≥8.4.2): Test framework
- `poetry`: Dependency management

## Troubleshooting

### MongoDB Connection Issues
- Verify MongoDB is running: `mongosh` or check Docker container
- Check `MONGO_HOST` in `.env` matches actual MongoDB host
- Default: `localhost:27017`

### DART API Authentication Errors
- Verify `OPENDART_API_KEY` in `.env` is valid
- Get key from: https://opendart.fss.or.kr/
- Check API rate limits (DART enforces limits per key)

### XML Parsing Failures
- Check file encoding (try EUC-KR if UTF-8 fails)
- Verify XML structure hasn't changed for very recent filings
- Consult `experiments/FINDINGS.md` for known edge cases

### Section Matching Issues
- Verify `config/toc.yaml` titles match actual report section titles
- Check similarity threshold in `parsers/section_matcher.py`
- Run `experiments/exp_13_text_based_section_matching.py` to debug

## Additional Resources

- **PRD**: `docs/vibe_coding/prd.md` - Product vision and requirements
- **Architecture**: `docs/vibe_coding/architecture.md` - System design details
- **Implementation Guide**: `docs/vibe_coding/implementation.md` - Coding standards
- **Findings**: `experiments/FINDINGS.md` - Experiment results and lessons learned
- **DART API Docs**: https://opendart.fss.or.kr/guide/detail.do
