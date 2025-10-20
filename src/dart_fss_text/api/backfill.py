"""
Backfill utility for parsing existing XML files and inserting missing data to MongoDB.

Use this when:
- MongoDB was offline during data collection
- Downloaded XML files exist but weren't inserted into MongoDB
- You want to re-parse existing XMLs with updated parsers
"""

from pathlib import Path
from typing import Dict, List, Optional
import logging

from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.api.pipeline import parse_xml_to_sections
from dart_fss_text.models.section import SectionDocument

logger = logging.getLogger(__name__)


class BackfillService:
    """
    Service for backfilling MongoDB from existing XML files.
    
    Traverses data directory structure, checks if data exists in MongoDB,
    and parses/inserts missing data.
    
    Usage:
        storage = StorageService()
        backfill = BackfillService(storage)
        stats = backfill.backfill_from_directory("data", target_section_codes=["020100"])
    """
    
    def __init__(self, storage_service: StorageService):
        """
        Initialize BackfillService with storage connection.
        
        Args:
            storage_service: Initialized StorageService instance
        """
        self.storage = storage_service
    
    def check_exists(self, rcept_no: str) -> bool:
        """
        Check if receipt number already exists in MongoDB.
        
        Args:
            rcept_no: Receipt number to check
        
        Returns:
            True if data exists, False otherwise
        """
        count = self.storage.collection.count_documents({'rcept_no': rcept_no})
        return count > 0
    
    def backfill_from_directory(
        self,
        base_dir: str = "data",
        target_section_codes: Optional[List[str]] = None,
        report_type: str = "A001",
        force: bool = False
    ) -> Dict[str, int]:
        """
        Traverse data directory and backfill missing data to MongoDB.
        
        Directory structure: data/year/stock_code/rcept_no/rcept_no.xml
        
        Args:
            base_dir: Base data directory (default: "data")
            target_section_codes: Optional list of section codes to extract
            report_type: Report type code (default: "A001")
            force: If True, re-parse and update even if exists (default: False)
        
        Returns:
            Statistics dictionary:
            {
                'scanned': 100,      # Total XML files scanned
                'existing': 50,      # Already in MongoDB (skipped)
                'processed': 40,     # Newly processed and inserted
                'sections': 40,      # Total sections inserted
                'failed': 10         # Failed to process
            }
        
        Example:
            >>> storage = StorageService()
            >>> backfill = BackfillService(storage)
            >>> stats = backfill.backfill_from_directory(
            ...     "data",
            ...     target_section_codes=["020100"]
            ... )
            >>> print(f"Processed {stats['processed']} new reports")
        """
        base_path = Path(base_dir)
        
        if not base_path.exists():
            raise ValueError(f"Directory not found: {base_dir}")
        
        # Initialize statistics
        stats = {
            'scanned': 0,
            'existing': 0,
            'processed': 0,
            'sections': 0,
            'failed': 0
        }
        
        logger.info(f"Starting backfill from {base_dir}")
        logger.info(f"Target sections: {target_section_codes or 'ALL'}")
        logger.info(f"Force re-parse: {force}")
        
        # Traverse: data/year/stock_code/rcept_no/*.xml
        for year_dir in sorted(base_path.iterdir()):
            if not year_dir.is_dir():
                continue
            
            year = year_dir.name
            logger.info(f"Processing year: {year}")
            
            for stock_dir in sorted(year_dir.iterdir()):
                if not stock_dir.is_dir():
                    continue
                
                stock_code = stock_dir.name
                
                for rcept_dir in sorted(stock_dir.iterdir()):
                    if not rcept_dir.is_dir():
                        continue
                    
                    rcept_no = rcept_dir.name
                    
                    # Find main XML file
                    xml_path = rcept_dir / f"{rcept_no}.xml"
                    
                    if not xml_path.exists():
                        logger.warning(
                            f"Main XML not found: {xml_path}. "
                            f"Expected {rcept_no}.xml in {rcept_dir}"
                        )
                        continue
                    
                    stats['scanned'] += 1
                    
                    # Check if already exists in MongoDB
                    if not force and self.check_exists(rcept_no):
                        logger.debug(f"Skipping {rcept_no} - already in MongoDB")
                        stats['existing'] += 1
                        continue
                    
                    # Parse and insert
                    try:
                        logger.info(f"Processing {xml_path}")
                        
                        # Create mock filing object with required attributes
                        class MockFiling:
                            def __init__(self, rcept_no, rcept_dt, corp_code, stock_code):
                                self.rcept_no = rcept_no
                                self.rcept_dt = rcept_dt
                                self.corp_code = corp_code
                                self.stock_code = stock_code
                                self.corp_name = ""  # Will be filled from XML if available
                                self.report_nm = f"사업보고서 ({year})"
                        
                        # Extract metadata from directory structure
                        # rcept_dt is first 8 digits of rcept_no (YYYYMMDD)
                        rcept_dt = rcept_no[:8]
                        
                        filing = MockFiling(
                            rcept_no=rcept_no,
                            rcept_dt=rcept_dt,
                            corp_code="",  # Not available from file path
                            stock_code=stock_code
                        )
                        
                        # Parse XML to sections
                        sections = parse_xml_to_sections(
                            xml_path=xml_path,
                            filing=filing,
                            report_type=report_type,
                            target_section_codes=target_section_codes
                        )
                        
                        if not sections:
                            logger.warning(f"No sections extracted from {xml_path}")
                            stats['failed'] += 1
                            continue
                        
                        # Insert or update sections
                        if force:
                            result = self.storage.upsert_sections(sections)
                        else:
                            result = self.storage.insert_sections(sections)
                        
                        if result['success']:
                            logger.info(
                                f"✓ Inserted {len(sections)} sections from {rcept_no}"
                            )
                            stats['processed'] += 1
                            stats['sections'] += len(sections)
                        else:
                            logger.error(
                                f"✗ Failed to insert {rcept_no}: {result.get('error')}"
                            )
                            stats['failed'] += 1
                    
                    except Exception as e:
                        logger.error(
                            f"✗ Failed to process {xml_path}: {e}",
                            exc_info=True
                        )
                        stats['failed'] += 1
                        continue
        
        logger.info(
            f"Backfill complete: {stats['scanned']} scanned, "
            f"{stats['existing']} existing, {stats['processed']} processed, "
            f"{stats['sections']} sections inserted, {stats['failed']} failed"
        )
        
        return stats

