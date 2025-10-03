"""
Integration tests for DocumentDownloadService

Tests download functionality with real DART API calls.
Requires OPENDART_API_KEY environment variable.
"""

import pytest
import os
from pathlib import Path
import tempfile
import shutil
from dotenv import load_dotenv
import dart_fss as dart

from dart_fss_text.services import FilingSearchService, DocumentDownloadService
from dart_fss_text.models.requests import SearchFilingsRequest


pytestmark = pytest.mark.integration


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="module", autouse=True)
def setup_api_key():
    """Load and set API key for integration tests."""
    load_dotenv()
    api_key = os.getenv("OPENDART_API_KEY")
    if not api_key:
        pytest.skip("OPENDART_API_KEY not found in environment")
    dart.set_api_key(api_key)


@pytest.fixture(scope="module")
def temp_download_dir():
    """Temporary directory for integration test downloads."""
    temp_dir = Path(tempfile.mkdtemp(prefix="dart_integration_"))
    yield temp_dir
    # Cleanup after all tests
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture(scope="module")
def sample_filings():
    """Get sample Samsung filings from Phase 1 service."""
    request = SearchFilingsRequest(
        stock_codes=["005930"],  # Samsung
        start_date="20240101",
        end_date="20241231",
        report_types=["A001"]  # Annual reports only
    )
    
    service = FilingSearchService()
    filings = service.search_filings(request)
    
    # Limit to 2 for testing
    return filings[:2]


@pytest.fixture
def download_service(temp_download_dir):
    """DocumentDownloadService with temp directory."""
    return DocumentDownloadService(base_dir=str(temp_download_dir))


# ============================================================================
# BASIC DOWNLOAD TESTS
# ============================================================================

def test_download_single_filing(download_service, sample_filings):
    """Should download a single filing successfully."""
    if len(sample_filings) == 0:
        pytest.skip("No filings found for testing")
    
    filing = sample_filings[0]
    
    result = download_service.download_filing(
        rcept_no=filing.rcept_no,
        rcept_dt=filing.rcept_dt,
        corp_code=filing.corp_code,
        report_nm=filing.report_nm
    )
    
    # Verify result
    assert result.status == 'success'
    assert result.rcept_no == filing.rcept_no
    assert result.year == filing.rcept_dt[:4]
    assert result.stock_code == "005930"
    assert len(result.xml_files) >= 1  # At least main XML
    assert result.main_xml_path is not None
    assert result.main_xml_path.exists()
    assert result.download_time_sec > 0
    assert result.zip_size_mb > 0
    
    # Verify main XML content
    assert result.main_xml_path.stat().st_size > 0


def test_download_idempotency(sample_filings):
    """Should skip download if already exists."""
    if len(sample_filings) == 0:
        pytest.skip("No filings found for testing")
    
    filing = sample_filings[0]
    
    # Create isolated service with unique temp directory for this test
    isolated_temp_dir = Path(tempfile.mkdtemp(prefix="dart_idempotency_"))
    isolated_service = DocumentDownloadService(base_dir=str(isolated_temp_dir))
    
    try:
        # First download (guaranteed fresh state)
        result1 = isolated_service.download_filing(
            rcept_no=filing.rcept_no,
            rcept_dt=filing.rcept_dt,
            corp_code=filing.corp_code
        )
        
        assert result1.status == 'success'  # Should be fresh download
        assert result1.main_xml_path.exists()
        assert result1.download_time_sec is not None  # Was downloaded
        
        # Second download (should skip because file exists)
        result2 = isolated_service.download_filing(
            rcept_no=filing.rcept_no,
            rcept_dt=filing.rcept_dt,
            corp_code=filing.corp_code
        )
        
        assert result2.status == 'existing'  # Should skip
        assert result2.main_xml_path == result1.main_xml_path
        assert result2.download_time_sec is None  # Not downloaded
        
        # Verify file actually exists
        assert result2.main_xml_path.exists()
        
    finally:
        # Cleanup isolated temp directory
        if isolated_temp_dir.exists():
            shutil.rmtree(isolated_temp_dir)


def test_download_multiple_filings(download_service, sample_filings):
    """Should download multiple filings."""
    if len(sample_filings) < 2:
        pytest.skip("Need at least 2 filings for batch test")
    
    results = download_service.download_filings(sample_filings, max_downloads=2)
    
    assert len(results) == 2
    assert all(r.status in ['success', 'existing'] for r in results)
    assert all(r.main_xml_path.exists() for r in results)


# ============================================================================
# DIRECTORY STRUCTURE TESTS
# ============================================================================

def test_pit_aware_directory_structure(download_service, sample_filings, temp_download_dir):
    """Should organize files in PIT-aware structure."""
    if len(sample_filings) == 0:
        pytest.skip("No filings found for testing")
    
    filing = sample_filings[0]
    
    result = download_service.download_filing(
        rcept_no=filing.rcept_no,
        rcept_dt=filing.rcept_dt,
        corp_code=filing.corp_code
    )
    
    # Verify structure: {base}/{year}/{stock_code}/{rcept_no}/
    expected_path = (
        temp_download_dir / 
        result.year / 
        result.stock_code / 
        filing.rcept_no /
        f"{filing.rcept_no}.xml"
    )
    
    assert expected_path == result.main_xml_path
    assert expected_path.exists()


def test_uses_stock_code_not_corp_code(download_service, sample_filings, temp_download_dir):
    """Should use stock_code in directory path."""
    if len(sample_filings) == 0:
        pytest.skip("No filings found for testing")
    
    filing = sample_filings[0]
    
    result = download_service.download_filing(
        rcept_no=filing.rcept_no,
        rcept_dt=filing.rcept_dt,
        corp_code=filing.corp_code
    )
    
    # Check stock_code used (005930), not corp_code (00126380)
    assert "005930" in str(result.main_xml_path)
    assert "00126380" not in str(result.main_xml_path)


# ============================================================================
# XML VALIDATION TESTS
# ============================================================================

def test_validate_downloaded_xml(download_service, sample_filings):
    """Should validate downloaded XML structure."""
    if len(sample_filings) == 0:
        pytest.skip("No filings found for testing")
    
    filing = sample_filings[0]
    
    result = download_service.download_filing(
        rcept_no=filing.rcept_no,
        rcept_dt=filing.rcept_dt,
        corp_code=filing.corp_code
    )
    
    # Validate XML
    counts = download_service.validate_xml(result.main_xml_path)
    
    assert counts['total_elements'] > 0
    assert counts['usermark_sections'] > 0
    assert counts['tables'] >= 0  # May have 0 tables


def test_xml_contains_expected_elements(download_service, sample_filings):
    """Downloaded XML should contain expected DART elements."""
    if len(sample_filings) == 0:
        pytest.skip("No filings found for testing")
    
    filing = sample_filings[0]
    
    result = download_service.download_filing(
        rcept_no=filing.rcept_no,
        rcept_dt=filing.rcept_dt,
        corp_code=filing.corp_code
    )
    
    # Read XML content
    xml_content = result.main_xml_path.read_text(encoding='utf-8')
    
    # Basic sanity checks
    assert '<' in xml_content  # Has XML tags
    assert '>' in xml_content
    assert len(xml_content) > 1000  # Non-trivial content


# ============================================================================
# EDGE CASES
# ============================================================================

def test_handles_multiple_xml_files_in_zip(download_service, sample_filings):
    """Should extract all XMLs from ZIP (main + attachments)."""
    if len(sample_filings) == 0:
        pytest.skip("No filings found for testing")
    
    filing = sample_filings[0]
    
    result = download_service.download_filing(
        rcept_no=filing.rcept_no,
        rcept_dt=filing.rcept_dt,
        corp_code=filing.corp_code
    )
    
    # Check all extracted XMLs
    assert len(result.xml_files) >= 1
    
    # Main XML should always exist
    main_xml = result.main_xml_path
    assert main_xml.name == f"{filing.rcept_no}.xml"
    assert main_xml in result.xml_files
    
    # If attachments exist, verify naming pattern
    for xml_file in result.xml_files:
        if xml_file != main_xml:
            # Attachment naming: {rcept_no}_NNNNN.xml
            assert xml_file.name.startswith(filing.rcept_no)
            assert xml_file.name.endswith('.xml')

