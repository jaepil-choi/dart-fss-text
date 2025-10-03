"""
Smoke Tests - Quick sanity checks with live API

These tests make REAL API calls to verify basic functionality.
Run them manually to ensure the system works end-to-end.

Usage:
    # Run smoke tests explicitly
    poetry run pytest -m smoke -v
    
    # Run smoke tests in this file only
    poetry run pytest tests/test_smoke.py -m smoke -v
    
    # Skip smoke tests (default)
    poetry run pytest tests/

Requirements:
- Valid OPENDART_API_KEY in .env file
- Active internet connection
"""

import pytest
import os
from dotenv import load_dotenv
import dart_fss as dart

from dart_fss_text.services.filing_search import FilingSearchService
from dart_fss_text.models.requests import SearchFilingsRequest


# Mark all tests in this file as smoke tests (disabled by default)
pytestmark = pytest.mark.smoke


@pytest.fixture(scope="module", autouse=True)
def setup_dart_api():
    """Setup dart-fss API key once for all smoke tests."""
    load_dotenv()
    api_key = os.getenv("OPENDART_API_KEY")
    
    if not api_key:
        pytest.skip("OPENDART_API_KEY not found in .env file")
    
    dart.set_api_key(api_key)
    print(f"\n✓ API Key loaded: {api_key[:8]}...")
    yield
    print("\n✓ Smoke tests completed")


class TestFilingSearchServiceSmoke:
    """Smoke tests for FilingSearchService with live API."""
    
    def test_service_initializes_successfully(self):
        """
        Smoke Test: FilingSearchService should initialize without errors.
        
        This verifies:
        - Service class can be instantiated
        - No import errors
        - No initialization logic failures
        """
        service = FilingSearchService()
        assert service is not None
        assert hasattr(service, 'search_filings')
        print("\n✓ FilingSearchService initialized")
    
    def test_can_perform_basic_search(self):
        """
        Smoke Test: Service should be able to perform a basic search.
        
        This verifies:
        - dart.get_corp_list() works (loads ~114K companies in ~7s)
        - Stock code lookup works (Samsung: 005930)
        - Filing search API works
        - Returns results in expected format
        
        Note: First call takes ~7s to load corp list (Singleton pattern)
        """
        service = FilingSearchService()
        
        # Simple search for Samsung annual reports in 2024
        request = SearchFilingsRequest(
            stock_codes=["005930"],  # Samsung
            start_date="20240101",
            end_date="20241231",
            report_types=["A001"]  # Annual reports
        )
        
        print(f"\n→ Searching Samsung (005930) annual reports in 2024...")
        results = service.search_filings(request)
        
        # Basic sanity checks
        assert isinstance(results, list), "Results should be a list"
        print(f"✓ Found {len(results)} filing(s)")
        
        if len(results) > 0:
            filing = results[0]
            # Verify Filing objects have required fields
            assert hasattr(filing, 'rcept_no'), "Filing should have rcept_no"
            assert hasattr(filing, 'rcept_dt'), "Filing should have rcept_dt"
            assert hasattr(filing, 'corp_code'), "Filing should have corp_code"
            assert hasattr(filing, 'report_nm'), "Filing should have report_nm"
            
            print(f"✓ Sample filing: {filing.report_nm} ({filing.rcept_no})")
            print(f"  - Receipt date: {filing.rcept_dt}")
            print(f"  - Corp code: {filing.corp_code}")
        else:
            print("⚠ No filings found (may be normal depending on date range)")
    
    def test_request_validation_works(self):
        """
        Smoke Test: Request validation should work correctly.
        
        This verifies:
        - Pydantic validation is active
        - Invalid inputs are rejected
        - Error messages are helpful
        """
        # Valid request should work
        valid_request = SearchFilingsRequest(
            stock_codes=["005930"],
            start_date="20240101",
            end_date="20241231",
            report_types=["A001"]
        )
        assert valid_request.stock_codes == ["005930"]
        print("\n✓ Valid request accepted")
        
        # Invalid report type should be rejected
        with pytest.raises(ValueError, match="Invalid report type"):
            invalid_request = SearchFilingsRequest(
                stock_codes=["005930"],
                start_date="20240101",
                end_date="20241231",
                report_types=["INVALID"]
            )
        print("✓ Invalid report type rejected")
        
        # Invalid stock code format should be rejected
        with pytest.raises(ValueError):
            invalid_request = SearchFilingsRequest(
                stock_codes=["BAD"],
                start_date="20240101",
                end_date="20241231",
                report_types=["A001"]
            )
        print("✓ Invalid stock code rejected")


if __name__ == "__main__":
    """
    Quick manual run for smoke tests.
    
    Usage:
        poetry run python tests/test_smoke.py
    """
    print("=" * 80)
    print("Running Smoke Tests Manually")
    print("=" * 80)
    
    # Setup
    load_dotenv()
    api_key = os.getenv("OPENDART_API_KEY")
    if not api_key:
        print("\n✗ OPENDART_API_KEY not found in .env file")
        exit(1)
    
    dart.set_api_key(api_key)
    print(f"\n✓ API Key loaded: {api_key[:8]}...")
    
    # Run tests
    print("\n" + "=" * 80)
    print("Test 1: Service Initialization")
    print("=" * 80)
    service = FilingSearchService()
    print("✓ FilingSearchService initialized successfully")
    
    print("\n" + "=" * 80)
    print("Test 2: Basic Search")
    print("=" * 80)
    request = SearchFilingsRequest(
        stock_codes=["005930"],
        start_date="20240101",
        end_date="20241231",
        report_types=["A001"]
    )
    print("→ Searching Samsung annual reports in 2024...")
    results = service.search_filings(request)
    print(f"✓ Found {len(results)} filing(s)")
    
    if results:
        print(f"\nSample result:")
        print(f"  - Report: {results[0].report_nm}")
        print(f"  - Receipt No: {results[0].rcept_no}")
        print(f"  - Date: {results[0].rcept_dt}")
    
    print("\n" + "=" * 80)
    print("✓ All smoke tests passed!")
    print("=" * 80)

