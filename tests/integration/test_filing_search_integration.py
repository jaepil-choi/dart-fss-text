"""
Integration tests for Filing Search Service

Tests with live DART API to validate real-world behavior.
Based on Experiment 7 (exp_07_search_download_organize.py) findings.

IMPORTANT: These tests require:
- Valid OPENDART_API_KEY in .env file
- Active internet connection
- DART API availability
"""

import pytest
import os
from dotenv import load_dotenv
import dart_fss as dart

from dart_fss_text.services.filing_search import FilingSearchService
from dart_fss_text.models.requests import FetchReportsRequest


# Skip all tests if no API key
load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENDART_API_KEY"),
    reason="OPENDART_API_KEY not found in .env"
)


@pytest.fixture(scope="module")
def setup_dart_api():
    """Setup dart-fss API key once for all tests."""
    api_key = os.getenv("OPENDART_API_KEY")
    dart.set_api_key(api_key)
    yield
    # No teardown needed


class TestRealSearchWithSamsungElectronics:
    """
    Test with Samsung Electronics (005930) - validated in Experiment 7.
    
    Experiment 7 results (2023-01-01 to 2024-12-31):
    - A001 (Annual): 2 reports
    - A002 (Semi-annual): 2 reports
    - A003 (Quarterly): 4 reports
    - Total: 8 filings
    """
    
    def test_search_samsung_annual_reports(self, setup_dart_api):
        """Should find Samsung annual reports (validated in Experiment 7)."""
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        results = service.search_filings(request)
        
        # From Experiment 7: Should find 2 annual reports
        assert len(results) >= 2, "Samsung should have at least 2 annual reports in 2023-2024"
        
        # Verify all are annual reports
        for filing in results:
            assert "사업보고서" in filing.report_nm
        
        # Verify expected filings from Experiment 7
        rcept_nos = [f.rcept_no for f in results]
        assert "20240312000736" in rcept_nos  # 2023 FY (published 2024-03-12)
        assert "20230307000542" in rcept_nos  # 2022 FY (published 2023-03-07)
    
    def test_search_samsung_semi_annual_reports(self, setup_dart_api):
        """Should find Samsung semi-annual reports."""
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A002"]
        )
        
        results = service.search_filings(request)
        
        # From Experiment 7: Should find 2 semi-annual reports
        assert len(results) >= 2, "Samsung should have at least 2 semi-annual reports"
        
        # Verify all are semi-annual reports
        for filing in results:
            assert "반기보고서" in filing.report_nm
    
    def test_search_samsung_quarterly_reports(self, setup_dart_api):
        """Should find Samsung quarterly reports."""
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A003"]
        )
        
        results = service.search_filings(request)
        
        # From Experiment 7: Should find 4 quarterly reports
        assert len(results) >= 4, "Samsung should have at least 4 quarterly reports"
        
        # Verify all are quarterly reports
        for filing in results:
            assert "분기보고서" in filing.report_nm
    
    def test_search_multiple_report_types(self, setup_dart_api):
        """Should search multiple report types and aggregate results."""
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001", "A002", "A003"]
        )
        
        results = service.search_filings(request)
        
        # From Experiment 7: Should find 8 total (2 + 2 + 4)
        assert len(results) >= 8, "Samsung should have at least 8 periodic reports"
        
        # Verify mix of report types
        report_names = [f.report_nm for f in results]
        assert any("사업보고서" in name for name in report_names)
        assert any("반기보고서" in name for name in report_names)
        assert any("분기보고서" in name for name in report_names)


class TestFilingObjectStructure:
    """Verify Filing objects have required fields for PIT-aware download."""
    
    def test_filing_has_required_fields(self, setup_dart_api):
        """
        Filing objects must have rcept_no, rcept_dt, corp_code, report_nm.
        
        These fields are critical for:
        - rcept_no: Document download
        - rcept_dt: PIT-aware directory structure (year extraction)
        - corp_code: Directory organization
        - report_nm: Logging and validation
        """
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20231231",
            report_types=["A001"]
        )
        
        results = service.search_filings(request)
        assert len(results) > 0, "Should find at least one filing"
        
        # Verify first result has all required fields
        filing = results[0]
        assert hasattr(filing, 'rcept_no'), "Missing rcept_no"
        assert hasattr(filing, 'rcept_dt'), "Missing rcept_dt"
        assert hasattr(filing, 'corp_code'), "Missing corp_code"
        assert hasattr(filing, 'report_nm'), "Missing report_nm"
        
        # Verify field formats
        assert len(filing.rcept_no) == 14, "rcept_no should be 14 digits"
        assert len(filing.rcept_dt) == 8, "rcept_dt should be YYYYMMDD (8 digits)"
        assert len(filing.corp_code) == 8, "corp_code should be 8 digits"
        assert filing.corp_code == "00126380", "Samsung corp_code"
        
        # Verify rcept_dt is within search range
        assert filing.rcept_dt >= "20230101"
        assert filing.rcept_dt <= "20231231"


class TestMultipleCompanies:
    """Test searching multiple companies simultaneously."""
    
    def test_search_samsung_and_sk_hynix(self, setup_dart_api):
        """Should search multiple companies and return combined results."""
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930", "000660"],  # Samsung, SK Hynix
            start_date="20230101",
            end_date="20231231",
            report_types=["A001"]
        )
        
        results = service.search_filings(request)
        
        # Should find annual reports from both companies
        assert len(results) >= 2, "Should find at least 1 report from each company"
        
        # Verify both companies present
        corp_codes = set(f.corp_code for f in results)
        assert "00126380" in corp_codes, "Samsung should be in results"
        assert "00164779" in corp_codes, "SK Hynix should be in results"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_results_for_narrow_date_range(self, setup_dart_api):
        """Should return empty list if no filings in date range."""
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20200101",
            end_date="20200105",  # Very narrow range
            report_types=["A001"]
        )
        
        results = service.search_filings(request)
        
        # Should return empty list (not raise error)
        assert isinstance(results, list)
        # May or may not be empty depending on actual filings
    
    def test_invalid_stock_code_raises_error(self, setup_dart_api):
        """Should raise error for invalid stock code."""
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["999999"],  # Invalid code
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        # Should raise error from dart-fss
        with pytest.raises((ValueError, AttributeError, TypeError)):
            service.search_filings(request)


class TestPerformance:
    """Test performance characteristics."""
    
    def test_search_performance(self, setup_dart_api):
        """
        Search should complete in reasonable time.
        
        From Experiment 7: Each search takes ~0.26s
        Multiple searches should be proportional.
        """
        import time
        
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001", "A002", "A003"]
        )
        
        start_time = time.time()
        results = service.search_filings(request)
        elapsed = time.time() - start_time
        
        # Should complete in reasonable time (3 searches × ~0.26s ≈ 1s + overhead)
        assert elapsed < 5.0, f"Search took {elapsed:.2f}s - should be < 5s"
        
        # Verify we got results
        assert len(results) > 0
    
    def test_corp_list_singleton_performance(self, setup_dart_api):
        """
        Second search should be faster due to Singleton caching.
        
        From Experiment 6: First get_corp_list() ~7s, subsequent 0.000ms
        """
        import time
        
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20231231",
            report_types=["A001"]
        )
        
        # First search (may include corp_list load)
        start_time = time.time()
        results1 = service.search_filings(request)
        first_search_time = time.time() - start_time
        
        # Second search (should use cached corp_list)
        start_time = time.time()
        results2 = service.search_filings(request)
        second_search_time = time.time() - start_time
        
        # Second search should not be significantly slower
        # (corp_list is cached, only API call for search)
        assert len(results1) == len(results2), "Should return same results"
        
        # Both searches should complete in reasonable time
        assert first_search_time < 10.0
        assert second_search_time < 5.0


class TestDateRangeFiltering:
    """Test that date range filtering works correctly."""
    
    def test_results_within_date_range(self, setup_dart_api):
        """All results should have rcept_dt within requested range."""
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20231231",
            report_types=["A001", "A002", "A003"]
        )
        
        results = service.search_filings(request)
        
        # Verify all rcept_dt within range
        for filing in results:
            assert filing.rcept_dt >= "20230101", f"Filing {filing.rcept_no} before start date"
            assert filing.rcept_dt <= "20231231", f"Filing {filing.rcept_no} after end date"

