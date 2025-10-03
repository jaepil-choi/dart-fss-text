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

import dart_fss as dart
from dart_fss.utils import request
from dart_fss.auth import get_api_key
from lxml import etree


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
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Load corp_list once for stock_code lookups (Singleton pattern)
        self._corp_list = None
    
    @property
    def corp_list(self):
        """Lazy-load corp_list (Singleton, ~7s first time)."""
        if self._corp_list is None:
            self._corp_list = dart.get_corp_list()
        return self._corp_list
    
    def download_filing(
        self,
        rcept_no: str,
        rcept_dt: str,
        corp_code: str,
        report_nm: Optional[str] = None
    ) -> DownloadResult:
        """
        Download and extract a single filing.
        
        Args:
            rcept_no: Receipt number (unique filing ID)
            rcept_dt: Receipt date (YYYYMMDD) - used for PIT year
            corp_code: Corporation code (8 digits)
            report_nm: Report name (for logging)
        
        Returns:
            DownloadResult with status and file paths
        
        Raises:
            FileNotFoundError: If download or extraction fails
            ValueError: If main XML not found in ZIP
        """
        import time
        
        # Extract PIT metadata
        year = rcept_dt[:4]
        
        # Get stock_code for directory structure
        corp = self.corp_list.find_by_corp_code(corp_code)
        stock_code = corp.stock_code if corp and corp.stock_code else corp_code
        
        # Create PIT-aware directory structure
        filing_dir = self.base_dir / year / stock_code / rcept_no
        filing_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already downloaded (idempotency)
        main_xml = filing_dir / f"{rcept_no}.xml"
        if main_xml.exists():
            # Already exists, return existing files
            xml_files = sorted(filing_dir.glob("*.xml"))
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
        
        request.download(url=url, path=str(filing_dir) + "/", payload=payload)
        
        download_time = time.time() - start_time
        
        # Verify ZIP exists
        zip_path = filing_dir / f"{rcept_no}.zip"
        if not zip_path.exists():
            raise FileNotFoundError(f"Download failed: ZIP not found at {zip_path}")
        
        zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
        
        # Extract all XMLs from ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            all_files = zip_ref.namelist()
            xml_files_in_zip = [f for f in all_files if f.endswith('.xml')]
            
            if len(xml_files_in_zip) == 0:
                raise ValueError(f"No XML files found in ZIP. Contents: {all_files}")
            
            # Extract all XMLs
            for xml_file in xml_files_in_zip:
                zip_ref.extract(xml_file, filing_dir)
        
        # Verify main XML exists
        if not main_xml.exists():
            raise FileNotFoundError(
                f"Main XML not found: {rcept_no}.xml\n"
                f"Available XMLs: {xml_files_in_zip}"
            )
        
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

