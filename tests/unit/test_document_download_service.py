"""
Unit tests for DocumentDownloadService

Tests download functionality with mocked external dependencies:
- Mock dart_fss.utils.request.download()
- Mock dart.get_corp_list()
- Mock filesystem operations
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import zipfile

from dart_fss_text.services.document_download import (
    DocumentDownloadService,
    DownloadResult
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_base_dir(tmp_path):
    """Temporary directory for downloads."""
    return tmp_path / "downloads"


@pytest.fixture
def mock_corp_list():
    """Mock CorpList with find_by_corp_code method."""
    mock_list = Mock()
    
    def find_by_corp_code(corp_code):
        """Return mock corp with proper string attributes."""
        mock_corp = Mock()
        mock_corp.stock_code = "005930"  # Real string, not Mock
        mock_corp.corp_code = corp_code
        mock_corp.corp_name = "삼성전자"
        return mock_corp
    
    mock_list.find_by_corp_code = find_by_corp_code
    return mock_list


@pytest.fixture(autouse=True)
def mock_get_corp_list(mock_corp_list):
    """Mock dart.get_corp_list() for all tests in this module."""
    with patch('dart_fss_text.services.document_download.dart.get_corp_list', return_value=mock_corp_list):
        yield


@pytest.fixture
def service(temp_base_dir):
    """DocumentDownloadService with mocked dependencies."""
    return DocumentDownloadService(base_dir=str(temp_base_dir))


@pytest.fixture
def sample_filing():
    """Sample filing object for testing."""
    filing = Mock()
    filing.rcept_no = "20240312000736"
    filing.rcept_dt = "20240312"
    filing.corp_code = "00126380"
    filing.report_nm = "사업보고서 (2023.12)"
    return filing


@pytest.fixture
def create_mock_zip(tmp_path):
    """Helper to create mock ZIP files with XMLs."""
    def _create_zip(rcept_no: str, xml_count: int = 3) -> Path:
        """Create a mock ZIP file with test XMLs."""
        zip_path = tmp_path / f"{rcept_no}.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            # Main XML
            main_xml = f"{rcept_no}.xml"
            zf.writestr(main_xml, f"<DOCUMENT>{rcept_no}</DOCUMENT>")
            
            # Additional XMLs
            for i in range(1, xml_count):
                xml_name = f"{rcept_no}_{i:05d}.xml"
                zf.writestr(xml_name, f"<ATTACHMENT>{i}</ATTACHMENT>")
        
        return zip_path
    
    return _create_zip


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

def test_service_initialization(temp_base_dir):
    """Service should initialize with base directory."""
    service = DocumentDownloadService(base_dir=str(temp_base_dir))
    
    assert service.base_dir == temp_base_dir
    assert temp_base_dir.exists()


def test_service_lazy_loads_corp_list(temp_base_dir):
    """Service should lazy-load corp_list on first access."""
    # Create isolated patch for this specific test
    with patch('dart_fss_text.services.document_download.dart.get_corp_list') as mock_get:
        mock_get.return_value = Mock()
        
        service = DocumentDownloadService(base_dir=str(temp_base_dir))
        
        # Not called on init
        mock_get.assert_not_called()
        
        # Called on first access
        _ = service.corp_list
        mock_get.assert_called_once()
        
        # Not called again (cached)
        _ = service.corp_list
        mock_get.assert_called_once()


# ============================================================================
# DOWNLOAD_FILING TESTS
# ============================================================================

def test_download_filing_success(service, sample_filing, temp_base_dir, create_mock_zip):
    """Should download and extract filing successfully."""
    rcept_no = sample_filing.rcept_no
    
    # Mock the download to create a real ZIP file
    def mock_download(url, path, payload):
        # Create mock ZIP in the target directory
        target_dir = Path(path.rstrip('/'))
        zip_path = create_mock_zip(rcept_no, xml_count=3)
        
        # Move ZIP to target directory
        import shutil
        shutil.copy(zip_path, target_dir / f"{rcept_no}.zip")
    
    with patch('dart_fss_text.services.document_download.request.download', side_effect=mock_download):
        with patch('dart_fss_text.services.document_download.get_api_key', return_value='test_key'):
            result = service.download_filing(
                rcept_no=sample_filing.rcept_no,
                rcept_dt=sample_filing.rcept_dt,
                corp_code=sample_filing.corp_code,
                report_nm=sample_filing.report_nm
            )
    
    # Verify result
    assert result.status == 'success'
    assert result.rcept_no == rcept_no
    assert result.stock_code == "005930"
    assert result.year == "2024"
    assert len(result.xml_files) == 3
    assert result.main_xml_path is not None
    assert result.main_xml_path.exists()
    assert result.download_time_sec is not None
    assert result.zip_size_mb is not None
    
    # Verify directory structure
    expected_dir = temp_base_dir / "2024" / "005930" / rcept_no
    assert expected_dir.exists()
    assert (expected_dir / f"{rcept_no}.xml").exists()
    
    # Verify ZIP was cleaned up
    assert not (expected_dir / f"{rcept_no}.zip").exists()


def test_download_filing_idempotency(service, sample_filing, temp_base_dir):
    """Should skip download if XML already exists."""
    rcept_no = sample_filing.rcept_no
    
    # Create existing XML
    filing_dir = temp_base_dir / "2024" / "005930" / rcept_no
    filing_dir.mkdir(parents=True, exist_ok=True)
    main_xml = filing_dir / f"{rcept_no}.xml"
    main_xml.write_text("<DOCUMENT>existing</DOCUMENT>")
    
    with patch('dart_fss_text.services.document_download.request.download') as mock_download:
        result = service.download_filing(
            rcept_no=sample_filing.rcept_no,
            rcept_dt=sample_filing.rcept_dt,
            corp_code=sample_filing.corp_code
        )
    
    # Should not download
    mock_download.assert_not_called()
    
    # Should return existing status
    assert result.status == 'existing'
    assert result.main_xml_path == main_xml
    assert result.main_xml_path.exists()


def test_download_filing_missing_zip(service, sample_filing):
    """Should raise FileNotFoundError if ZIP not created."""
    with patch('dart_fss_text.services.document_download.request.download'):
        # download() doesn't create ZIP (simulate failure)
        with patch('dart_fss_text.services.document_download.get_api_key', return_value='test_key'):
            with pytest.raises(FileNotFoundError, match="Download failed: ZIP not found"):
                service.download_filing(
                    rcept_no=sample_filing.rcept_no,
                    rcept_dt=sample_filing.rcept_dt,
                    corp_code=sample_filing.corp_code
                )


def test_download_filing_no_xml_in_zip(service, sample_filing, temp_base_dir):
    """Should raise ValueError if ZIP contains no XML files."""
    rcept_no = sample_filing.rcept_no
    
    def mock_download(url, path, payload):
        # Create ZIP with no XMLs
        target_dir = Path(path.rstrip('/'))
        zip_path = target_dir / f"{rcept_no}.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("readme.txt", "No XMLs here!")
    
    with patch('dart_fss_text.services.document_download.request.download', side_effect=mock_download):
        with patch('dart_fss_text.services.document_download.get_api_key', return_value='test_key'):
            with pytest.raises(ValueError, match="No XML files found in ZIP"):
                service.download_filing(
                    rcept_no=sample_filing.rcept_no,
                    rcept_dt=sample_filing.rcept_dt,
                    corp_code=sample_filing.corp_code
                )


def test_download_filing_missing_main_xml(service, sample_filing, temp_base_dir):
    """Should raise FileNotFoundError if main XML not in ZIP."""
    rcept_no = sample_filing.rcept_no
    
    def mock_download(url, path, payload):
        # Create ZIP with only attachment XMLs (no main)
        target_dir = Path(path.rstrip('/'))
        zip_path = target_dir / f"{rcept_no}.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr(f"{rcept_no}_00760.xml", "<ATTACHMENT>1</ATTACHMENT>")
            zf.writestr(f"{rcept_no}_00761.xml", "<ATTACHMENT>2</ATTACHMENT>")
    
    with patch('dart_fss_text.services.document_download.request.download', side_effect=mock_download):
        with patch('dart_fss_text.services.document_download.get_api_key', return_value='test_key'):
            with pytest.raises(FileNotFoundError, match="Main XML not found"):
                service.download_filing(
                    rcept_no=sample_filing.rcept_no,
                    rcept_dt=sample_filing.rcept_dt,
                    corp_code=sample_filing.corp_code
                )


def test_download_filing_pit_aware_structure(service, sample_filing, temp_base_dir, create_mock_zip):
    """Should organize files in PIT-aware structure."""
    rcept_no = sample_filing.rcept_no
    
    def mock_download(url, path, payload):
        target_dir = Path(path.rstrip('/'))
        zip_path = create_mock_zip(rcept_no, xml_count=2)
        import shutil
        shutil.copy(zip_path, target_dir / f"{rcept_no}.zip")
    
    with patch('dart_fss_text.services.document_download.request.download', side_effect=mock_download):
        with patch('dart_fss_text.services.document_download.get_api_key', return_value='test_key'):
            result = service.download_filing(
                rcept_no=rcept_no,
                rcept_dt="20230307",  # Different year
                corp_code=sample_filing.corp_code
            )
    
    # Should use year from rcept_dt
    assert result.year == "2023"
    
    # Verify structure
    expected_dir = temp_base_dir / "2023" / "005930" / rcept_no
    assert expected_dir.exists()


def test_download_filing_uses_stock_code(service, sample_filing, temp_base_dir, create_mock_zip):
    """Should use stock_code for directory structure."""
    rcept_no = sample_filing.rcept_no
    
    def mock_download(url, path, payload):
        target_dir = Path(path.rstrip('/'))
        zip_path = create_mock_zip(rcept_no, xml_count=1)
        import shutil
        shutil.copy(zip_path, target_dir / f"{rcept_no}.zip")
    
    with patch('dart_fss_text.services.document_download.request.download', side_effect=mock_download):
        with patch('dart_fss_text.services.document_download.get_api_key', return_value='test_key'):
            result = service.download_filing(
                rcept_no=rcept_no,
                rcept_dt=sample_filing.rcept_dt,
                corp_code=sample_filing.corp_code
            )
    
    # Directory should use stock_code (005930), not corp_code (00126380)
    stock_code_dir = temp_base_dir / "2024" / "005930"
    corp_code_dir = temp_base_dir / "2024" / "00126380"
    
    assert stock_code_dir.exists()
    assert not corp_code_dir.exists()


# ============================================================================
# DOWNLOAD_FILINGS TESTS (Batch)
# ============================================================================

def test_download_filings_batch(service, temp_base_dir, create_mock_zip):
    """Should download multiple filings."""
    filings = [
        Mock(rcept_no=f"2024031200073{i}", rcept_dt="20240312", corp_code="00126380")
        for i in range(3)
    ]
    
    def mock_download(url, path, payload):
        target_dir = Path(path.rstrip('/'))
        rcept_no = payload['rcept_no']
        zip_path = create_mock_zip(rcept_no, xml_count=1)
        import shutil
        shutil.copy(zip_path, target_dir / f"{rcept_no}.zip")
    
    with patch('dart_fss_text.services.document_download.request.download', side_effect=mock_download):
        with patch('dart_fss_text.services.document_download.get_api_key', return_value='test_key'):
            results = service.download_filings(filings)
    
    assert len(results) == 3
    assert all(r.status == 'success' for r in results)


def test_download_filings_with_max_limit(service, create_mock_zip):
    """Should respect max_downloads limit."""
    filings = [
        Mock(rcept_no=f"2024031200073{i}", rcept_dt="20240312", corp_code="00126380")
        for i in range(10)
    ]
    
    def mock_download(url, path, payload):
        target_dir = Path(path.rstrip('/'))
        rcept_no = payload['rcept_no']
        zip_path = create_mock_zip(rcept_no, xml_count=1)
        import shutil
        shutil.copy(zip_path, target_dir / f"{rcept_no}.zip")
    
    with patch('dart_fss_text.services.document_download.request.download', side_effect=mock_download):
        with patch('dart_fss_text.services.document_download.get_api_key', return_value='test_key'):
            results = service.download_filings(filings, max_downloads=3)
    
    # Should only download 3
    assert len(results) == 3


def test_download_filings_fail_fast(service):
    """Should fail fast on first error."""
    filings = [
        Mock(rcept_no=f"2024031200073{i}", rcept_dt="20240312", corp_code="00126380")
        for i in range(3)
    ]
    
    with patch('dart_fss_text.services.document_download.request.download') as mock_download:
        # First download fails (no ZIP created)
        with patch('dart_fss_text.services.document_download.get_api_key', return_value='test_key'):
            with pytest.raises(RuntimeError, match="Download failed"):
                service.download_filings(filings)


# ============================================================================
# VALIDATE_XML TESTS
# ============================================================================

def test_validate_xml_success(service, temp_base_dir):
    """Should validate XML and return element counts."""
    xml_path = temp_base_dir / "test.xml"
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<DOCUMENT>
    <SECTION USERMARK="I. 회사의 개요">
        <TABLE>
            <TR><TD>Data</TD></TR>
        </TABLE>
    </SECTION>
    <SECTION USERMARK="II. 사업의 내용">
        <TABLE>
            <TR><TD>More data</TD></TR>
        </TABLE>
    </SECTION>
</DOCUMENT>"""
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(xml_content, encoding='utf-8')
    
    counts = service.validate_xml(xml_path)
    
    assert counts['total_elements'] > 0
    assert counts['usermark_sections'] == 2
    assert counts['tables'] == 2


def test_validate_xml_malformed(service, temp_base_dir):
    """Should handle malformed XML with recover mode."""
    xml_path = temp_base_dir / "malformed.xml"
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<DOCUMENT>
    <SECTION>Unclosed section
    <TABLE>Unclosed table
</DOCUMENT>"""
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(xml_content, encoding='utf-8')
    
    # Should not raise exception (recover mode)
    counts = service.validate_xml(xml_path)
    
    assert counts['total_elements'] > 0

