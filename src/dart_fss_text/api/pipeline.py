"""
High-level pipeline orchestrator for DART disclosure data.

DisclosurePipeline coordinates the complete workflow:
- Search filings (via FilingSearchService)
- Download documents
- Parse XML to sections
- Store in MongoDB (via StorageService)

Design Philosophy:
- Explicit database control (StorageService injected by user)
- Resilient processing (continues after individual failures)
- Statistics-based monitoring (returns actionable metrics)
"""

from typing import Dict, List, Union, Optional
import logging
from pathlib import Path
import pandas as pd

from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.services.filing_search import FilingSearchService
from dart_fss_text.services.document_download import DocumentDownloadService
from dart_fss_text.services.corp_list_service import CorpListService
from dart_fss_text.models.requests import SearchFilingsRequest
from dart_fss_text.models.section import SectionDocument
from dart_fss_text.config import get_toc_mapping
from dart_fss_text.parsers.xml_parser import build_section_index, extract_section_by_code
from datetime import datetime

logger = logging.getLogger(__name__)


def download_document(filing, base_dir: str = "data", fallback: bool = True, corp_name: str = None, stock_code: str = None) -> Path:
    """
    Download DART filing document using DocumentDownloadService.
    
    Args:
        filing: Filing object from FilingSearchService
        base_dir: Base directory for downloads (default: "data")
        fallback: If True, use first available XML if main XML not found (default: True)
        corp_name: Company name for logging (optional, will be looked up if not provided)
        stock_code: Stock code for logging (optional, will be looked up if not provided)
    
    Returns:
        Path to main XML file (or fallback XML if main not found and fallback=True)
    
    Raises:
        FileNotFoundError: If download or extraction fails
        ValueError: If main XML not found in ZIP and fallback=False
    
    Example:
        xml_path = download_document(filing)
        # Returns: data/2024/005930/20240312000736/20240312000736.xml
    """
    # Get company info for logging if not provided
    if not corp_name or not stock_code:
        from dart_fss_text.services import CorpListService
        corp_service = CorpListService()
        corp_data = corp_service.find_by_corp_code(filing.corp_code)
        if corp_data:
            if not stock_code:
                stock_code = corp_data.get('stock_code') or filing.corp_code
            if not corp_name:
                corp_name = corp_data.get('corp_name', 'Unknown')
        else:
            stock_code = stock_code or filing.corp_code
            corp_name = corp_name or 'Unknown'
    
    logger.info(
        f"Downloading filing {filing.rcept_no} for {stock_code} ({corp_name})"
    )
    
    service = DocumentDownloadService(base_dir=base_dir)
    
    try:
        result = service.download_filing(
            rcept_no=filing.rcept_no,
            rcept_dt=filing.rcept_dt,
            corp_code=filing.corp_code,
            report_nm=getattr(filing, 'report_nm', None),
            fallback=fallback
        )
    except Exception as e:
        logger.error(
            f"Download failed for {filing.rcept_no} ({stock_code} - {corp_name}): {e}",
            exc_info=True
        )
        raise
    
    if result.status == 'failed':
        error_msg = f"Download failed for {filing.rcept_no} ({stock_code} - {corp_name}): {result.error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    if not result.main_xml_path:
        error_msg = f"Main XML not found for {filing.rcept_no} ({stock_code} - {corp_name})"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    # Check if fallback was used
    main_xml_name = result.main_xml_path.name
    if main_xml_name != f"{filing.rcept_no}.xml":
        logger.warning(
            f"Used fallback XML for {filing.rcept_no} ({stock_code} - {corp_name}): {main_xml_name}"
        )
    
    logger.info(
        f"Downloaded {filing.rcept_no} ({stock_code} - {corp_name}): "
        f"status={result.status}, "
        f"files={len(result.xml_files)}, "
        f"main_xml={main_xml_name}"
    )
    
    return result.main_xml_path


def parse_xml_to_sections(
    xml_path: Path, 
    filing, 
    report_type: str = "A001",
    target_section_codes: Optional[List[str]] = None
) -> List[SectionDocument]:
    """
    Parse XML file to SectionDocument objects using existing parsers.
    
    Args:
        xml_path: Path to XML file
        filing: Filing object with metadata
        report_type: Report type code (default: "A001")
        target_section_codes: Optional list of section codes to extract.
                             If None, extracts all sections.
                             If specified, only extracts matching sections.
    
    Returns:
        List of SectionDocument objects (filtered by target_section_codes if provided)
    
    Raises:
        Exception: If XML parsing fails
    
    Example:
        # Extract all sections
        sections = parse_xml_to_sections(xml_path, filing)
        
        # Extract only specific section
        sections = parse_xml_to_sections(xml_path, filing, target_section_codes=["020100"])
    """
    # Load TOC mapping
    toc_mapping = get_toc_mapping(report_type)
    
    # Build section index from XML
    section_index = build_section_index(xml_path, toc_mapping)
    
    # Log section index statistics
    total_sections_found = len(section_index)
    mapped_sections = [m for m in section_index.values() if m.get('section_code')]
    unmapped_sections = [m for m in section_index.values() if not m.get('section_code')]
    
    logger.info(
        f"Built section index from {xml_path.name}: "
        f"{total_sections_found} total sections, "
        f"{len(mapped_sections)} mapped, "
        f"{len(unmapped_sections)} unmapped"
    )
    
    # Log available section codes if target is specified
    if target_section_codes:
        available_codes = [m['section_code'] for m in mapped_sections if m.get('section_code')]
        missing_codes = [code for code in target_section_codes if code not in available_codes]
        found_codes = [code for code in target_section_codes if code in available_codes]
        
        logger.info(
            f"Target sections {target_section_codes}: "
            f"found {len(found_codes)} ({found_codes}), "
            f"missing {len(missing_codes)} ({missing_codes}). "
            f"Available codes: {available_codes[:10]}{'...' if len(available_codes) > 10 else ''}"
        )
    
    # Extract year from rcept_dt (YYYYMMDD -> YYYY)
    year = filing.rcept_dt[:4]
    
    # Convert each section to SectionDocument
    sections = []
    skipped_unmapped = 0
    skipped_non_target = 0
    failed_extraction = 0
    
    for atocid, metadata in section_index.items():
        section_code = metadata['section_code']
        
        # Skip unmapped sections
        if not section_code:
            skipped_unmapped += 1
            logger.debug(f"Skipping unmapped section: {metadata.get('title', 'Unknown')}")
            continue
        
        # Filter by target sections if specified
        if target_section_codes and section_code not in target_section_codes:
            skipped_non_target += 1
            logger.debug(f"Skipping non-target section: {section_code} - {metadata.get('title', 'Unknown')}")
            continue
        
        # Extract section content
        parsed_section = extract_section_by_code(section_index, section_code)
        
        if not parsed_section:
            failed_extraction += 1
            logger.warning(f"Failed to extract section {section_code} from {xml_path.name}")
            continue
        
        # Convert to SectionDocument
        section_doc = _convert_to_section_document(
            parsed_section=parsed_section,
            filing=filing,
            year=year
        )
        
        sections.append(section_doc)
        
        logger.debug(
            f"Parsed section {section_code}: "
            f"{len(parsed_section.get('paragraphs', []))} paragraphs, "
            f"{len(parsed_section.get('tables', []))} tables"
        )
    
    # Log detailed parsing results
    if len(sections) == 0:
        logger.warning(
            f"⚠️  Parsed 0 sections from {xml_path.name}! "
            f"Total sections: {total_sections_found}, "
            f"Mapped: {len(mapped_sections)}, "
            f"Skipped unmapped: {skipped_unmapped}, "
            f"Skipped non-target: {skipped_non_target}, "
            f"Failed extraction: {failed_extraction}"
        )
        if target_section_codes:
            logger.warning(
                f"Target sections were: {target_section_codes}. "
                f"Available mapped codes: {[m['section_code'] for m in mapped_sections]}"
            )
    else:
        logger.info(
            f"Parsed {len(sections)} sections from {xml_path.name} "
            f"(skipped {skipped_unmapped} unmapped, {skipped_non_target} non-target, "
            f"{failed_extraction} failed extraction)"
        )
    
    return sections


def _convert_to_section_document(
    parsed_section: Dict,
    filing,
    year: str
) -> SectionDocument:
    """
    Convert parsed section dictionary to SectionDocument model.
    
    Args:
        parsed_section: Parsed section dictionary from extract_section_by_code
        filing: Filing object with metadata
        year: Year extracted from rcept_dt
    
    Returns:
        SectionDocument object
    """
    # Flatten text: paragraphs + tables
    text_parts = parsed_section.get('paragraphs', []).copy()
    
    # Flatten tables to text
    for table in parsed_section.get('tables', []):
        table_text = _flatten_table_to_text(table)
        if table_text:
            text_parts.append(table_text)
    
    # Join all text
    full_text = '\n\n'.join(text_parts)
    
    # Calculate statistics
    char_count = len(full_text)
    word_count = len(full_text.split())
    
    # Build section_path (for hierarchy)
    section_path = [parsed_section['section_code']]
    
    # Create composite document_id
    document_id = f"{filing.rcept_no}_{parsed_section['section_code']}"
    
    # Get report name (with fallback)
    report_name = getattr(filing, 'report_nm', 'Unknown Report')
    
    return SectionDocument(
        document_id=document_id,
        rcept_no=filing.rcept_no,
        rcept_dt=filing.rcept_dt,
        year=year,
        corp_code=filing.corp_code,
        corp_name=getattr(filing, 'corp_name', ''),
        stock_code=getattr(filing, 'stock_code', filing.corp_code),
        report_type="A001",  # TODO: Make dynamic
        report_name=report_name,
        section_code=parsed_section['section_code'],
        section_title=parsed_section['title'],
        level=parsed_section['level'],
        section_path=section_path,
        text=full_text,
        char_count=char_count,
        word_count=word_count,
        parsed_at=datetime.now(),
        parser_version="0.1.0"
    )


def _flatten_table_to_text(table: Dict) -> str:
    """
    Flatten table structure to text for MVP.
    
    Args:
        table: Table dictionary with headers and rows
    
    Returns:
        Flattened text representation
    """
    parts = []
    
    # Add headers
    headers = table.get('headers', [])
    if headers:
        parts.append(' | '.join(headers))
    
    # Add rows
    for row in table.get('rows', []):
        if row:
            parts.append(' | '.join(str(cell) for cell in row))
    
    return '\n'.join(parts)


class DisclosurePipeline:
    """
    High-level orchestrator for DART disclosure data pipeline.
    
    Coordinates the complete workflow from filing search to database storage.
    
    Design Principles:
    - Explicit DB control: StorageService injected by user
    - Resilient: Continues processing after individual failures
    - Observable: Returns statistics for monitoring
    - Testable: All dependencies injected or mockable
    
    Example:
        # Step 1: User establishes database connection
        storage = StorageService()  # User controls DB connection
        
        # Step 2: Initialize pipeline with storage
        pipeline = DisclosurePipeline(storage_service=storage)
        
        # Step 3: Process filings
        stats = pipeline.download_and_parse(
            stock_codes=["005930", "000660"],
            years=[2023, 2024],
            report_type="A001"
        )
        print(f"Processed {stats['reports']} reports, "
              f"{stats['sections']} sections, "
              f"{stats['failed']} failures")
    """
    
    def __init__(self, storage_service: StorageService):
        """
        Initialize pipeline with injected storage service.
        
        Args:
            storage_service: Pre-initialized StorageService with verified connection
        
        Example:
            storage = StorageService()  # User verifies DB connection first
            pipeline = DisclosurePipeline(storage_service=storage)
        """
        self._storage = storage_service
        self._filing_search = FilingSearchService()
        self._corp_list_service = CorpListService()
        logger.info("DisclosurePipeline initialized with injected StorageService")
    
    def download_and_parse(
        self,
        stock_codes: Union[str, List[str]] = "all",
        years: Union[int, List[int]] = None,
        report_type: str = "A001",
        target_section_codes: Optional[List[str]] = None,
        skip_existing: bool = True,
        base_dir: str = "data"
    ) -> Dict[str, int]:
        """
        Complete workflow: search → download → parse → store.
        
        Args:
            stock_codes: Company stock codes. Can be:
                        - "all" (default): Automatically gets all listed companies
                        - Single code: "005930"
                        - List of codes: ["005930", "000660"]
            years: Years to fetch (e.g., [2023, 2024] or 2024). Required if not provided.
            report_type: DART report type code (default: "A001" for Annual Report)
            target_section_codes: Optional list of section codes to extract.
                                 If None, extracts all sections.
                                 If specified, only extracts matching sections.
                                 Example: ["020100"] for "1. 사업의 개요"
            skip_existing: If True, skips year+stock_code combinations that already
                          have downloaded data in base_dir/year/stock_code/.
                          Saves API calls when resuming. (default: True)
            base_dir: Base directory for downloads (default: "data")
        
        Returns:
            Statistics dictionary:
            {
                'reports': 4,      # Reports successfully processed
                'sections': 194,   # Total sections stored
                'failed': 0,       # Failed operations
                'skipped': 10      # Skipped (already downloaded)
            }
        
        Design:
            - Normalizes inputs (single → list)
            - If stock_codes="all", automatically fetches all listed companies from CorpListService
            - Processes each company × year combination
            - Skips already-downloaded data when skip_existing=True
            - Continues processing after individual failures (resilience)
            - Tracks statistics for monitoring
        
        Example:
            # Extract all sections for all listed companies
            stats = pipeline.download_and_parse(
                years=[2023, 2024],
                report_type="A001"
            )
            
            # Extract all sections for specific companies
            stats = pipeline.download_and_parse(
                stock_codes=["005930", "000660"],
                years=[2023, 2024],
                report_type="A001"
            )
            
            # Extract only specific section for all companies
            stats = pipeline.download_and_parse(
                years=[2023],
                report_type="A001",
                target_section_codes=["020100"]
            )
            
            # Resume after interruption (skips existing downloads)
            stats = pipeline.download_and_parse(
                years=[2023],
                report_type="A001",
                skip_existing=True  # Default behavior
            )
        """
        # Validate years is provided
        if years is None:
            raise ValueError(
                "years parameter is required. "
                "Example: years=[2023, 2024] or years=2024"
            )
        
        # Normalize inputs
        stock_codes = self._normalize_stock_codes(stock_codes)
        years = self._normalize_years(years)
        
        # Initialize statistics
        stats = self._init_statistics()
        stats['skipped'] = 0  # Track skipped downloads
        
        # Track failures per year for CSV export
        failures_by_year: Dict[int, List[Dict]] = {}
        
        logger.info(
            f"Starting pipeline: {len(stock_codes)} companies, "
            f"{len(years)} years, report_type={report_type}"
        )
        
        # Process each year and company
        for year in years:
            failures_by_year[year] = []  # Initialize failure list for this year
            for stock_code in stock_codes:
                # Get company name for logging
                corp_data = self._corp_list_service.find_by_stock_code(stock_code)
                corp_name = corp_data.get('corp_name', 'Unknown') if corp_data else 'Unknown'
                
                logger.info(
                    f"Processing {stock_code} ({corp_name}) - Year {year}"
                )
                
                # Check if data already exists in MongoDB (correct check)
                if skip_existing:
                    existing_sections = self._storage.get_sections_by_company(
                        stock_code=stock_code,
                        year=str(year)
                    )
                    if existing_sections:
                        logger.info(
                            f"Skipping {stock_code} ({corp_name}) {year} - "
                            f"already in MongoDB ({len(existing_sections)} sections found)"
                        )
                        stats['skipped'] += 1
                        continue  # Skip to next stock_code
                    
                    # Check if XML files exist but not in MongoDB (need to process)
                    data_dir = Path(base_dir) / str(year) / stock_code
                    if data_dir.exists() and any(data_dir.iterdir()):
                        # Process existing XML files directly (backfill mode)
                        logger.info(
                            f"Found existing XML files for {stock_code} ({corp_name}) {year} "
                            f"but not in MongoDB - processing existing files"
                        )
                        
                        # Process each existing XML file
                        for rcept_dir in sorted(data_dir.iterdir()):
                            if not rcept_dir.is_dir():
                                continue
                            
                            rcept_no = rcept_dir.name
                            
                            # Check if this specific filing already in MongoDB
                            existing_for_filing = self._storage.collection.count_documents({'rcept_no': rcept_no})
                            if existing_for_filing > 0:
                                logger.debug(f"Skipping {rcept_no} - already in MongoDB")
                                continue
                            
                            # Find XML file (main or fallback)
                            main_xml = rcept_dir / f"{rcept_no}.xml"
                            xml_path = None
                            
                            if main_xml.exists():
                                xml_path = main_xml
                            else:
                                # Try fallback XMLs
                                xml_files = sorted(rcept_dir.glob("*.xml"))
                                if xml_files:
                                    xml_path = xml_files[0]
                                    logger.warning(
                                        f"Main XML not found for {rcept_no}, using fallback: {xml_path.name}"
                                    )
                            
                            if not xml_path or not xml_path.exists():
                                logger.warning(f"No XML found for {rcept_no} in {rcept_dir}")
                                continue
                            
                            # Create mock filing object
                            rcept_dt = rcept_no[:8]  # Extract date from rcept_no
                            class MockFiling:
                                def __init__(self, rcept_no, rcept_dt, corp_code, stock_code, corp_name):
                                    self.rcept_no = rcept_no
                                    self.rcept_dt = rcept_dt
                                    self.corp_code = corp_code
                                    self.stock_code = stock_code
                                    self.corp_name = corp_name
                                    self.report_nm = f"사업보고서 ({year})"
                            
                            filing = MockFiling(
                                rcept_no=rcept_no,
                                rcept_dt=rcept_dt,
                                corp_code=corp_data['corp_code'],
                                stock_code=stock_code,
                                corp_name=corp_name
                            )
                            
                            # Parse and store existing XML
                            try:
                                logger.info(
                                    f"Processing existing XML {xml_path.name} for {rcept_no} "
                                    f"({stock_code} - {corp_name})"
                                )
                                
                                sections = parse_xml_to_sections(
                                    xml_path=xml_path,
                                    filing=filing,
                                    report_type=report_type,
                                    target_section_codes=target_section_codes
                                )
                                
                                if len(sections) == 0:
                                    logger.warning(
                                        f"⚠️  No sections parsed from existing XML {xml_path.name} "
                                        f"for {rcept_no} ({stock_code} - {corp_name})"
                                    )
                                    failures_by_year[year].append({
                                        'corp_code': corp_data['corp_code'],
                                        'stock_code': stock_code,
                                        'corp_name': corp_name,
                                        'rcept_no': rcept_no,
                                        'rcept_dt': rcept_dt,
                                        'year': str(year),
                                        'error': 'No sections parsed from existing XML',
                                        'error_type': 'ParseError'
                                    })
                                    stats['failed'] += 1
                                    continue
                                
                                # Store sections
                                self._storage.insert_sections(sections)
                                logger.info(
                                    f"Stored {len(sections)} sections from existing XML {xml_path.name} "
                                    f"for {rcept_no} ({stock_code} - {corp_name})"
                                )
                                
                                stats['reports'] += 1
                                stats['sections'] += len(sections)
                                
                            except Exception as e:
                                error_msg = str(e)
                                logger.error(
                                    f"Failed to process existing XML {xml_path.name} for {rcept_no} "
                                    f"({stock_code} - {corp_name}): {error_msg}",
                                    exc_info=True
                                )
                                failures_by_year[year].append({
                                    'corp_code': corp_data['corp_code'],
                                    'stock_code': stock_code,
                                    'corp_name': corp_name,
                                    'rcept_no': rcept_no,
                                    'rcept_dt': rcept_dt,
                                    'year': str(year),
                                    'error': error_msg,
                                    'error_type': type(e).__name__
                                })
                                stats['failed'] += 1
                                continue
                        
                        # After processing existing files, continue to next stock_code
                        continue
                
                try:
                    # Search filings via API (for files not yet downloaded)
                    request = SearchFilingsRequest(
                        stock_codes=[stock_code],
                        start_date=f"{year}0101",
                        end_date=f"{year}1231",
                        report_types=[report_type]
                    )
                    filings = self._filing_search.search_filings(request)
                    
                    logger.info(
                        f"Found {len(filings)} filing(s) via API for {stock_code} ({corp_name}) - Year {year}"
                    )
                    
                    # Process each filing from API
                    for filing in filings:
                        try:
                            # Download (pass company info for better logging)
                            xml_path = download_document(
                                filing, 
                                base_dir=base_dir, 
                                fallback=True,
                                corp_name=corp_name,
                                stock_code=stock_code
                            )
                            logger.debug(
                                f"Downloaded {filing.rcept_no} for {stock_code} ({corp_name}) "
                                f"to {xml_path}"
                            )
                            
                            # Parse
                            logger.debug(
                                f"Parsing XML {xml_path.name} for {filing.rcept_no} "
                                f"({stock_code} - {corp_name})"
                            )
                            sections = parse_xml_to_sections(
                                xml_path, 
                                filing, 
                                report_type=report_type,
                                target_section_codes=target_section_codes
                            )
                            
                            # Warn if no sections were parsed
                            if len(sections) == 0:
                                logger.warning(
                                    f"⚠️  No sections parsed from {filing.rcept_no} "
                                    f"({stock_code} - {corp_name})! "
                                    f"XML file: {xml_path.name}. "
                                    f"This may indicate a parsing issue or missing target sections."
                                )
                            else:
                                logger.debug(
                                    f"Parsed {len(sections)} sections from {filing.rcept_no} "
                                    f"({stock_code} - {corp_name})"
                                )
                            
                            # Store (even if empty - insert_sections handles empty lists)
                            self._storage.insert_sections(sections)
                            
                            if len(sections) > 0:
                                logger.info(
                                    f"Stored {len(sections)} sections from {filing.rcept_no} "
                                    f"({stock_code} - {corp_name})"
                                )
                            else:
                                logger.warning(
                                    f"⚠️  Stored 0 sections from {filing.rcept_no} "
                                    f"({stock_code} - {corp_name}) - "
                                    f"report counted but no data stored!"
                                )
                            
                            # Update statistics
                            stats['reports'] += 1
                            stats['sections'] += len(sections)
                            
                        except Exception as e:
                            error_msg = str(e)
                            logger.error(
                                f"Failed to process filing {filing.rcept_no} "
                                f"({stock_code} - {corp_name}): {error_msg}",
                                exc_info=True
                            )
                            
                            # Track failure for CSV export
                            failures_by_year[year].append({
                                'corp_code': filing.corp_code,
                                'stock_code': stock_code,
                                'corp_name': corp_name,
                                'rcept_no': filing.rcept_no,
                                'rcept_dt': filing.rcept_dt,
                                'year': str(year),
                                'error': error_msg,
                                'error_type': type(e).__name__
                            })
                            
                            stats['failed'] += 1
                            # Continue processing remaining filings
                            continue
                
                except ValueError as e:
                    # Authentication/Authorization errors should fail fast
                    if 'Unauthorized' in str(e) or 'api_key' in str(e).lower():
                        logger.error(
                            f"Authentication failed for {stock_code} ({corp_name}) {year}: {e}. "
                            "Check OPENDART_API_KEY in .env file."
                        )
                        raise ValueError(
                            f"Authentication failed: {e}. "
                            "Stopping pipeline. Please check OPENDART_API_KEY."
                        ) from e
                    
                    # Other ValueErrors - continue processing
                    error_msg = str(e)
                    logger.error(
                        f"Failed to search filings for {stock_code} ({corp_name}) {year}: {error_msg}",
                        exc_info=True
                    )
                    
                    # Track failure for CSV export
                    failures_by_year[year].append({
                        'corp_code': None,  # Not available at search stage
                        'stock_code': stock_code,
                        'corp_name': corp_name,
                        'rcept_no': None,
                        'rcept_dt': None,
                        'year': str(year),
                        'error': error_msg,
                        'error_type': type(e).__name__
                    })
                    
                    stats['failed'] += 1
                    continue
                
                except Exception as e:
                    # Check for API usage limit exceeded
                    error_msg = str(e)
                    if '사용한도를 초과하였습니다' in error_msg or 'OverQueryLimit' in str(type(e).__name__):
                        logger.error(
                            f"API usage limit exceeded (사용한도를 초과하였습니다). "
                            f"Stopping pipeline immediately. "
                            f"Last processed: {stock_code} ({corp_name}) {year}"
                        )
                        
                        # Track failure for CSV export before stopping
                        failures_by_year[year].append({
                            'corp_code': None,
                            'stock_code': stock_code,
                            'corp_name': corp_name,
                            'rcept_no': None,
                            'rcept_dt': None,
                            'year': str(year),
                            'error': error_msg,
                            'error_type': type(e).__name__
                        })
                        
                        # Save failures CSV for current year before stopping
                        if failures_by_year[year]:
                            self._save_failures_csv(failures_by_year[year], year, base_dir)
                        
                        logger.info(
                            f"Pipeline stopped early due to API limit. "
                            f"Stats so far: {stats['reports']} reports, "
                            f"{stats['sections']} sections, {stats['skipped']} skipped, "
                            f"{stats['failed']} failed"
                        )
                        # Return stats immediately without continuing
                        return stats
                    
                    error_msg = str(e)
                    logger.error(
                        f"Failed to search filings for {stock_code} ({corp_name}) {year}: {error_msg}",
                        exc_info=True
                    )
                    
                    # Track failure for CSV export
                    failures_by_year[year].append({
                        'corp_code': None,  # Not available at search stage
                        'stock_code': stock_code,
                        'corp_name': corp_name,
                        'rcept_no': None,
                        'rcept_dt': None,
                        'year': str(year),
                        'error': error_msg,
                        'error_type': type(e).__name__
                    })
                    
                    stats['failed'] += 1
                    # Continue processing remaining companies/years
                    continue
            
            # Save failures to CSV for this year
            if failures_by_year[year]:
                self._save_failures_csv(failures_by_year[year], year, base_dir)
        
        logger.info(
            f"Pipeline complete: {stats['reports']} reports, "
            f"{stats['sections']} sections, {stats['skipped']} skipped, "
            f"{stats['failed']} failures"
        )
        
        return stats
    
    def _normalize_stock_codes(self, stock_codes: Union[str, List[str]]) -> List[str]:
        """
        Normalize stock_codes to list format.
        
        If stock_codes is "all", automatically fetches all listed stock codes
        from CorpListService.
        
        Args:
            stock_codes: Single code, list of codes, or "all"
        
        Returns:
            List of stock codes
        
        Raises:
            RuntimeError: If stock_codes="all" but CorpListService not initialized
        
        Example:
            "005930" → ["005930"]
            ["005930", "000660"] → ["005930", "000660"]
            "all" → ["005930", "000660", ...] (all listed companies)
        """
        # Handle "all" case - get all listed companies
        if stock_codes == "all":
            if not self._corp_list_service._initialized:
                raise RuntimeError(
                    "CorpListService not initialized. "
                    "Call initialize_corp_list() or CorpListService().initialize() first."
                )
            
            all_listed = self._corp_list_service.get_all_listed_stock_codes()
            logger.info(f"Using 'all' stock_codes: found {len(all_listed)} listed companies")
            return all_listed
        
        # Handle single string (not "all")
        if isinstance(stock_codes, str):
            return [stock_codes]
        
        # Already a list
        return stock_codes
    
    def _normalize_years(self, years: Union[int, List[int]]) -> List[int]:
        """
        Normalize years to list format.
        
        Args:
            years: Single year or list of years
        
        Returns:
            List of years
        
        Example:
            2024 → [2024]
            [2023, 2024] → [2023, 2024]
        """
        if isinstance(years, int):
            return [years]
        return years
    
    def _init_statistics(self) -> Dict[str, int]:
        """
        Initialize statistics dictionary.
        
        Returns:
            Statistics dict with counters set to zero
        """
        return {
            'reports': 0,
            'sections': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def _save_failures_csv(self, failures: List[Dict], year: int, base_dir: str):
        """
        Save failed attempts to CSV file for a specific year.
        
        Args:
            failures: List of failure dictionaries with company info and error
            year: Year being processed
            base_dir: Base directory for saving CSV files
        """
        if not failures:
            return
        
        try:
            # Create failures directory
            failures_dir = Path(base_dir) / "failures"
            failures_dir.mkdir(parents=True, exist_ok=True)
            
            # Create DataFrame from failures
            df = pd.DataFrame(failures)
            
            # Save to CSV
            csv_path = failures_dir / f"failures_{year}.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8')
            
            logger.info(
                f"Saved {len(failures)} failure(s) for year {year} to {csv_path}"
            )
        except Exception as e:
            logger.error(
                f"Failed to save failures CSV for year {year}: {e}",
                exc_info=True
            )

