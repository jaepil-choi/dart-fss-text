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

from typing import Dict, List, Union
import logging
from pathlib import Path

from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.services.filing_search import FilingSearchService
from dart_fss_text.services.document_download import DocumentDownloadService
from dart_fss_text.models.requests import SearchFilingsRequest
from dart_fss_text.models.section import SectionDocument
from dart_fss_text.config import get_toc_mapping
from dart_fss_text.parsers.xml_parser import build_section_index, extract_section_by_code
from datetime import datetime

logger = logging.getLogger(__name__)


def download_document(filing, base_dir: str = "data") -> Path:
    """
    Download DART filing document using DocumentDownloadService.
    
    Args:
        filing: Filing object from FilingSearchService
        base_dir: Base directory for downloads (default: "data")
    
    Returns:
        Path to main XML file
    
    Raises:
        FileNotFoundError: If download or extraction fails
        ValueError: If main XML not found in ZIP
    
    Example:
        xml_path = download_document(filing)
        # Returns: data/2024/005930/20240312000736/20240312000736.xml
    """
    service = DocumentDownloadService(base_dir=base_dir)
    
    result = service.download_filing(
        rcept_no=filing.rcept_no,
        rcept_dt=filing.rcept_dt,
        corp_code=filing.corp_code,
        report_nm=getattr(filing, 'report_nm', None)
    )
    
    if result.status == 'failed':
        raise RuntimeError(f"Download failed: {result.error}")
    
    if not result.main_xml_path:
        raise FileNotFoundError(f"Main XML not found for {filing.rcept_no}")
    
    logger.info(
        f"Downloaded {filing.rcept_no}: "
        f"status={result.status}, "
        f"files={len(result.xml_files)}"
    )
    
    return result.main_xml_path


def parse_xml_to_sections(xml_path: Path, filing, report_type: str = "A001") -> List[SectionDocument]:
    """
    Parse XML file to SectionDocument objects using existing parsers.
    
    Args:
        xml_path: Path to XML file
        filing: Filing object with metadata
        report_type: Report type code (default: "A001")
    
    Returns:
        List of SectionDocument objects
    
    Raises:
        Exception: If XML parsing fails
    
    Example:
        sections = parse_xml_to_sections(xml_path, filing)
        # Returns: [SectionDocument(...), SectionDocument(...), ...]
    """
    # Load TOC mapping
    toc_mapping = get_toc_mapping(report_type)
    
    # Build section index from XML
    section_index = build_section_index(xml_path, toc_mapping)
    
    # Extract year from rcept_dt (YYYYMMDD -> YYYY)
    year = filing.rcept_dt[:4]
    
    # Convert each section to SectionDocument
    sections = []
    for atocid, metadata in section_index.items():
        section_code = metadata['section_code']
        
        # Skip unmapped sections
        if not section_code:
            logger.debug(f"Skipping unmapped section: {metadata['title']}")
            continue
        
        # Extract section content
        parsed_section = extract_section_by_code(section_index, section_code)
        
        if not parsed_section:
            logger.warning(f"Failed to extract section {section_code}")
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
    
    logger.info(f"Parsed {len(sections)} sections from {xml_path.name}")
    
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
        logger.info("DisclosurePipeline initialized with injected StorageService")
    
    def download_and_parse(
        self,
        stock_codes: Union[str, List[str]],
        years: Union[int, List[int]],
        report_type: str = "A001"
    ) -> Dict[str, int]:
        """
        Complete workflow: search → download → parse → store.
        
        Args:
            stock_codes: Company stock codes (e.g., ["005930", "000660"] or "005930")
            years: Years to fetch (e.g., [2023, 2024] or 2024)
            report_type: DART report type code (default: "A001" for Annual Report)
        
        Returns:
            Statistics dictionary:
            {
                'reports': 4,      # Reports successfully processed
                'sections': 194,   # Total sections stored
                'failed': 0        # Failed operations
            }
        
        Design:
            - Normalizes inputs (single → list)
            - Processes each company × year combination
            - Continues processing after individual failures (resilience)
            - Tracks statistics for monitoring
        
        Example:
            stats = pipeline.download_and_parse(
                stock_codes=["005930", "000660"],
                years=[2023, 2024],
                report_type="A001"
            )
        """
        # Normalize inputs
        stock_codes = self._normalize_stock_codes(stock_codes)
        years = self._normalize_years(years)
        
        # Initialize statistics
        stats = self._init_statistics()
        
        logger.info(
            f"Starting pipeline: {len(stock_codes)} companies, "
            f"{len(years)} years, report_type={report_type}"
        )
        
        # Process each year and company
        for year in years:
            for stock_code in stock_codes:
                try:
                    # Search filings
                    request = SearchFilingsRequest(
                        stock_codes=[stock_code],
                        start_date=f"{year}0101",
                        end_date=f"{year}1231",
                        report_types=[report_type]
                    )
                    filings = self._filing_search.search_filings(request)
                    
                    # Process each filing
                    for filing in filings:
                        try:
                            # Download
                            xml_path = download_document(filing)
                            logger.debug(f"Downloaded {filing.rcept_no} to {xml_path}")
                            
                            # Parse
                            sections = parse_xml_to_sections(xml_path, filing)
                            logger.debug(f"Parsed {len(sections)} sections from {filing.rcept_no}")
                            
                            # Store
                            self._storage.insert_sections(sections)
                            logger.info(
                                f"Stored {len(sections)} sections from {filing.rcept_no}"
                            )
                            
                            # Update statistics
                            stats['reports'] += 1
                            stats['sections'] += len(sections)
                            
                        except Exception as e:
                            logger.error(
                                f"Failed to process filing {filing.rcept_no}: {e}",
                                exc_info=True
                            )
                            stats['failed'] += 1
                            # Continue processing remaining filings
                            continue
                
                except ValueError as e:
                    # Authentication/Authorization errors should fail fast
                    if 'Unauthorized' in str(e) or 'api_key' in str(e).lower():
                        logger.error(
                            f"Authentication failed: {e}. "
                            "Check OPENDART_API_KEY in .env file."
                        )
                        raise ValueError(
                            f"Authentication failed: {e}. "
                            "Stopping pipeline. Please check OPENDART_API_KEY."
                        ) from e
                    
                    # Other ValueErrors - continue processing
                    logger.error(
                        f"Failed to search filings for {stock_code} {year}: {e}",
                        exc_info=True
                    )
                    stats['failed'] += 1
                    continue
                
                except Exception as e:
                    logger.error(
                        f"Failed to search filings for {stock_code} {year}: {e}",
                        exc_info=True
                    )
                    stats['failed'] += 1
                    # Continue processing remaining companies/years
                    continue
        
        logger.info(
            f"Pipeline complete: {stats['reports']} reports, "
            f"{stats['sections']} sections, {stats['failed']} failures"
        )
        
        return stats
    
    def _normalize_stock_codes(self, stock_codes: Union[str, List[str]]) -> List[str]:
        """
        Normalize stock_codes to list format.
        
        Args:
            stock_codes: Single code or list of codes
        
        Returns:
            List of stock codes
        
        Example:
            "005930" → ["005930"]
            ["005930", "000660"] → ["005930", "000660"]
        """
        if isinstance(stock_codes, str):
            return [stock_codes]
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
            'failed': 0
        }

