"""
Document Download Service

Handles downloading and extracting DART filing documents with:
- PIT-aware directory structure: {year}/{stock_code}/{rcept_no}/
- All XMLs extracted from ZIP (main + attachments)
- Fail-fast error handling
- Idempotent downloads (skip if already exists)

Based on Experiment 09 findings.
"""

import zipfile
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

from dart_fss.utils import request
from dart_fss.auth import get_api_key
from lxml import etree

from dart_fss_text.services.corp_list_service import CorpListService

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a single filing download operation."""
    rcept_no: str
    rcept_dt: str
    stock_code: str
    year: str
    status: str  # 'success', 'existing', 'failed'
    xml_files: List[Path]
    main_xml_path: Optional[Path] = None
    error: Optional[str] = None
    download_time_sec: Optional[float] = None
    zip_size_mb: Optional[float] = None


class DocumentDownloadService:
    """
    Service for downloading DART filing documents.
    
    Organizes files in PIT-aware structure:
        data/raw/{year}/{stock_code}/{rcept_no}/
            {rcept_no}.xml              # Main document
            {rcept_no}_00760.xml        # Attachment 1
            {rcept_no}_00761.xml        # Attachment 2
    
    Usage:
        service = DocumentDownloadService(base_dir="data/raw")
        results = service.download_filings(filings)
    """
    
    def __init__(self, base_dir: str = "data/raw"):
        """
        Initialize download service.
        
        Args:
            base_dir: Base directory for downloaded files
            
        Raises:
            RuntimeError: If CorpListService not initialized
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Use CorpListService for cached corp lookups
        self._corp_list_service = CorpListService()
        
        # Check if initialized (for cached lookups)
        if not self._corp_list_service._initialized:
            raise RuntimeError(
                "CorpListService not initialized. "
                "Call CorpListService().initialize() first."
            )
    
    def download_filing(
        self,
        rcept_no: str,
        rcept_dt: str,
        corp_code: str,
        report_nm: Optional[str] = None,
        fallback: bool = True
    ) -> DownloadResult:
        """
        Download and extract a single filing.
        
        Args:
            rcept_no: Receipt number (unique filing ID)
            rcept_dt: Receipt date (YYYYMMDD) - used for PIT year
            corp_code: Corporation code (8 digits)
            report_nm: Report name (for logging)
            fallback: If True, use first available XML if main XML not found (default: True)
        
        Returns:
            DownloadResult with status and file paths
        
        Raises:
            FileNotFoundError: If download or extraction fails
            ValueError: If main XML not found in ZIP and fallback=False
        """
        import time
        
        # Extract PIT metadata
        year = rcept_dt[:4]
        
        # Get stock_code and company name for logging using cached CorpListService
        corp_data = self._corp_list_service.find_by_corp_code(corp_code)
        if corp_data:
            stock_code = corp_data.get('stock_code') or corp_code
            corp_name = corp_data.get('corp_name', 'Unknown')
        else:
            # Fallback: use corp_code as stock_code if not found in cache
            stock_code = corp_code
            corp_name = 'Unknown'
        
        logger.debug(
            f"Downloading {rcept_no} for {stock_code} ({corp_name})"
        )
        
        # Create PIT-aware directory structure
        filing_dir = self.base_dir / year / stock_code / rcept_no
        filing_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already downloaded (idempotency)
        main_xml = filing_dir / f"{rcept_no}.xml"
        if main_xml.exists():
            # Already exists, return existing files
            xml_files = sorted(filing_dir.glob("*.xml"))
            logger.debug(
                f"Filing {rcept_no} ({stock_code} - {corp_name}) already exists, skipping download"
            )
            return DownloadResult(
                rcept_no=rcept_no,
                rcept_dt=rcept_dt,
                stock_code=stock_code,
                year=year,
                status='existing',
                xml_files=xml_files,
                main_xml_path=main_xml
            )
        
        # Download ZIP
        start_time = time.time()
        
        url = 'https://opendart.fss.or.kr/api/document.xml'
        payload = {
            'crtfc_key': get_api_key(),
            'rcept_no': rcept_no,
        }
        
        logger.debug(
            f"Requesting download for {rcept_no} ({stock_code} - {corp_name})"
        )
        
        try:
            request.download(url=url, path=str(filing_dir) + "/", payload=payload)
        except FileNotFoundError as e:
            logger.error(
                f"Download request failed for {rcept_no} ({stock_code} - {corp_name}): {e}"
            )
            raise FileNotFoundError(
                f"Download failed for {rcept_no} ({stock_code} - {corp_name}): {e}"
            ) from e
        
        download_time = time.time() - start_time
        
        # Verify ZIP exists
        zip_path = filing_dir / f"{rcept_no}.zip"
        if not zip_path.exists():
            error_msg = f"Download failed: ZIP not found at {zip_path} for {rcept_no} ({stock_code} - {corp_name})"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        logger.debug(
            f"ZIP downloaded for {rcept_no} ({stock_code} - {corp_name}): "
            f"{zip_size_mb:.2f} MB in {download_time:.2f}s"
        )
        
        # Extract all XMLs from ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            all_files = zip_ref.namelist()
            xml_files_in_zip = [f for f in all_files if f.endswith('.xml')]
            
            if len(xml_files_in_zip) == 0:
                error_msg = f"No XML files found in ZIP for {rcept_no} ({stock_code} - {corp_name}). Contents: {all_files}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.debug(
                f"Found {len(xml_files_in_zip)} XML file(s) in ZIP for {rcept_no} ({stock_code} - {corp_name}): "
                f"{xml_files_in_zip}"
            )
            
            # Extract all XMLs
            for xml_file in xml_files_in_zip:
                zip_ref.extract(xml_file, filing_dir)
        
        # Verify main XML exists
        if not main_xml.exists():
            # FALLBACK LOGIC DISABLED - No longer using alternative XML files
            # if fallback and xml_files_in_zip:
            #     # Use first available XML as fallback
            #     fallback_xml_name = xml_files_in_zip[0]
            #     fallback_xml_path = filing_dir / fallback_xml_name
            #
            #     if fallback_xml_path.exists():
            #         logger.warning(
            #             f"Main XML not found for {rcept_no} ({stock_code} - {corp_name}), "
            #             f"using fallback: {fallback_xml_name}. "
            #             f"Available XMLs: {xml_files_in_zip}"
            #         )
            #         main_xml = fallback_xml_path
            #     else:
            #         error_msg = (
            #             f"Main XML not found for {rcept_no} ({stock_code} - {corp_name}): {rcept_no}.xml\n"
            #             f"Fallback XML also not found: {fallback_xml_name}\n"
            #             f"Available XMLs: {xml_files_in_zip}"
            #         )
            #         logger.error(error_msg)
            #         raise FileNotFoundError(error_msg)
            # else:
            error_msg = (
                f"Main XML not found for {rcept_no} ({stock_code} - {corp_name}): {rcept_no}.xml\n"
                f"Available XMLs: {xml_files_in_zip}"
            )
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Cleanup ZIP
        zip_path.unlink()
        
        # Get all extracted XML paths
        xml_files = sorted(filing_dir.glob("*.xml"))
        
        return DownloadResult(
            rcept_no=rcept_no,
            rcept_dt=rcept_dt,
            stock_code=stock_code,
            year=year,
            status='success',
            xml_files=xml_files,
            main_xml_path=main_xml,
            download_time_sec=download_time,
            zip_size_mb=zip_size_mb
        )
    
    def download_filings(
        self,
        filings: List[object],
        max_downloads: Optional[int] = None
    ) -> List[DownloadResult]:
        """
        Download multiple filings.
        
        Args:
            filings: List of filing objects from FilingSearchService
            max_downloads: Optional limit on number of downloads
        
        Returns:
            List of DownloadResult objects
        """
        results = []
        
        filings_to_process = filings[:max_downloads] if max_downloads else filings
        
        for filing in filings_to_process:
            try:
                result = self.download_filing(
                    rcept_no=filing.rcept_no,
                    rcept_dt=filing.rcept_dt,
                    corp_code=filing.corp_code,
                    report_nm=getattr(filing, 'report_nm', None)
                )
                results.append(result)
            except Exception as e:
                # Fail-fast: re-raise exception
                raise RuntimeError(
                    f"Download failed for {filing.rcept_no}: {e}"
                ) from e
        
        return results
    
    def validate_xml(self, xml_path: Path) -> Dict[str, int]:
        """
        Validate XML structure and return element counts.
        
        Args:
            xml_path: Path to XML file
        
        Returns:
            Dict with element counts
        
        Raises:
            Exception: If XML parsing fails
        """
        parser = etree.XMLParser(recover=True, encoding='utf-8')
        tree = etree.parse(str(xml_path), parser)
        root = tree.getroot()
        
        return {
            'total_elements': len(list(root.iter())),
            'usermark_sections': len(root.findall(".//*[@USERMARK]")),
            'tables': len(root.findall(".//TABLE"))
        }

