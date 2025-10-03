"""
Unit tests for Filing Search Service

Tests the search service that wraps dart-fss API calls for filing discovery.
Based on findings from Experiment 7 (exp_07_search_download_organize.py).
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from dart_fss_text.services.filing_search import FilingSearchService
from dart_fss_text.models.requests import FetchReportsRequest


class TestFilingSearchServiceInitialization:
    """Test service initialization and configuration."""
    
    def test_service_initializes_without_error(self):
        """Service should initialize without requiring arguments."""
        service = FilingSearchService()
        assert service is not None
    
    def test_service_has_search_filings_method(self):
        """Service should expose search_filings method."""
        service = FilingSearchService()
        assert hasattr(service, 'search_filings')
        assert callable(service.search_filings)


class TestSearchFilingsMethodSignature:
    """Test the search_filings method interface."""
    
    def test_accepts_fetch_reports_request(self):
        """Should accept FetchReportsRequest as input."""
        service = FilingSearchService()
        
        # Valid request (uses our validated Pydantic model)
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        # Should not raise on valid request (will fail on missing API key, but that's integration test)
        assert request.stock_codes == ["005930"]
    
    def test_returns_list_of_filings(self):
        """Should return a list (empty or populated)."""
        # This will be tested in integration tests with real API
        # Unit test just validates the interface
        pass


class TestStockCodeToCorpCodeLookup:
    """Test conversion from stock_code to corp_code using dart-fss."""
    
    @patch('dart_fss_text.services.filing_search.dart.get_corp_list')
    def test_uses_dart_fss_get_corp_list(self, mock_get_corp_list):
        """Should use dart-fss Singleton to get corp list."""
        # Mock the corp list
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.corp_code = "00126380"
        mock_corp.corp_name = "삼성전자"
        mock_corp.search_filings = Mock(return_value=[])
        
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_get_corp_list.return_value = mock_corp_list
        
        # Create service and search
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        service.search_filings(request)
        
        # Verify dart.get_corp_list() was called (Singleton pattern)
        mock_get_corp_list.assert_called_once()
        
        # Verify find_by_stock_code was called with correct stock code
        mock_corp_list.find_by_stock_code.assert_called_with("005930")
    
    @patch('dart_fss_text.services.filing_search.dart.get_corp_list')
    def test_handles_multiple_stock_codes(self, mock_get_corp_list):
        """Should look up multiple stock codes."""
        # Mock corp list with multiple companies
        mock_corp_list = Mock()
        
        # Samsung
        mock_samsung = Mock()
        mock_samsung.corp_code = "00126380"
        mock_samsung.search_filings = Mock(return_value=[])
        
        # SK Hynix
        mock_hynix = Mock()
        mock_hynix.corp_code = "00164779"
        mock_hynix.search_filings = Mock(return_value=[])
        
        def find_by_code(stock_code):
            if stock_code == "005930":
                return mock_samsung
            elif stock_code == "000660":
                return mock_hynix
            else:
                raise ValueError(f"Unknown stock code: {stock_code}")
        
        mock_corp_list.find_by_stock_code = Mock(side_effect=find_by_code)
        mock_get_corp_list.return_value = mock_corp_list
        
        # Search multiple companies
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930", "000660"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        service.search_filings(request)
        
        # Verify both lookups happened
        assert mock_corp_list.find_by_stock_code.call_count == 2
        mock_corp_list.find_by_stock_code.assert_any_call("005930")
        mock_corp_list.find_by_stock_code.assert_any_call("000660")


class TestFilingSearch:
    """Test actual filing search using Corp.search_filings()."""
    
    @patch('dart_fss_text.services.filing_search.dart.get_corp_list')
    def test_calls_corp_search_filings_with_correct_params(self, mock_get_corp_list):
        """
        Should call Corp.search_filings() with bgn_de and pblntf_detail_ty.
        
        From Experiment 7: Corp.search_filings(bgn_de, pblntf_detail_ty) is the
        correct method that returns Filing objects.
        """
        # Mock corp
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.corp_code = "00126380"
        mock_corp.search_filings = Mock(return_value=[])
        
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_get_corp_list.return_value = mock_corp_list
        
        # Search
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        service.search_filings(request)
        
        # Verify Corp.search_filings was called with correct parameters
        mock_corp.search_filings.assert_called_once_with(
            bgn_de="20230101",
            end_de="20241231",
            pblntf_detail_ty="A001"
        )
    
    @patch('dart_fss_text.services.filing_search.dart.get_corp_list')
    def test_searches_multiple_report_types(self, mock_get_corp_list):
        """
        Should search each report type separately.
        
        From Experiment 7: We search A001, A002, A003 separately and
        aggregate results.
        """
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.corp_code = "00126380"
        
        # Mock returns different results for each report type
        def mock_search(**kwargs):
            report_type = kwargs.get('pblntf_detail_ty')
            if report_type == "A001":
                return [Mock(report_nm="사업보고서")]
            elif report_type == "A002":
                return [Mock(report_nm="반기보고서")]
            elif report_type == "A003":
                return [Mock(report_nm="분기보고서")]
            return []
        
        mock_corp.search_filings = Mock(side_effect=mock_search)
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_get_corp_list.return_value = mock_corp_list
        
        # Search multiple report types
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001", "A002", "A003"]
        )
        
        results = service.search_filings(request)
        
        # Should call search_filings 3 times (once per report type)
        assert mock_corp.search_filings.call_count == 3
        
        # Should aggregate results from all searches
        assert len(results) == 3
    
    @patch('dart_fss_text.services.filing_search.dart.get_corp_list')
    def test_aggregates_results_from_multiple_companies_and_types(self, mock_get_corp_list):
        """
        Should aggregate all results across companies and report types.
        
        If searching 2 companies × 2 report types, should return combined list.
        """
        mock_corp_list = Mock()
        
        # Company 1: Returns 1 filing per search
        mock_corp1 = Mock()
        mock_corp1.search_filings = Mock(return_value=[Mock(corp_code="00126380")])
        
        # Company 2: Returns 2 filings per search
        mock_corp2 = Mock()
        mock_corp2.search_filings = Mock(return_value=[
            Mock(corp_code="00164779"),
            Mock(corp_code="00164779")
        ])
        
        def find_by_code(stock_code):
            return mock_corp1 if stock_code == "005930" else mock_corp2
        
        mock_corp_list.find_by_stock_code = Mock(side_effect=find_by_code)
        mock_get_corp_list.return_value = mock_corp_list
        
        # Search 2 companies × 2 report types
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930", "000660"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001", "A002"]
        )
        
        results = service.search_filings(request)
        
        # Expected: (1 filing × 2 types) + (2 filings × 2 types) = 6 total
        assert len(results) == 6


class TestFilingSearchResults:
    """Test the structure and content of search results."""
    
    @patch('dart_fss_text.services.filing_search.dart.get_corp_list')
    def test_returns_filing_objects_with_required_fields(self, mock_get_corp_list):
        """
        Results should have rcept_no, rcept_dt, corp_code, report_nm.
        
        From Experiment 7: Filing objects have these critical fields for
        PIT-aware download and organization.
        """
        # Create mock Filing with required fields
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"
        mock_filing.corp_code = "00126380"
        mock_filing.report_nm = "사업보고서 (2023.12)"
        
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.search_filings = Mock(return_value=[mock_filing])
        
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_get_corp_list.return_value = mock_corp_list
        
        # Search
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        results = service.search_filings(request)
        
        # Verify result has required fields
        assert len(results) == 1
        filing = results[0]
        assert hasattr(filing, 'rcept_no')
        assert hasattr(filing, 'rcept_dt')
        assert hasattr(filing, 'corp_code')
        assert hasattr(filing, 'report_nm')
        
        # Verify values match Experiment 7 data
        assert filing.rcept_no == "20240312000736"
        assert filing.rcept_dt == "20240312"
        assert filing.corp_code == "00126380"


class TestErrorHandling:
    """Test error handling for edge cases."""
    
    @patch('dart_fss_text.services.filing_search.dart.get_corp_list')
    def test_raises_error_on_invalid_stock_code(self, mock_get_corp_list):
        """Should raise error if stock code is not found."""
        mock_corp_list = Mock()
        mock_corp_list.find_by_stock_code = Mock(
            side_effect=ValueError("Stock code not found")
        )
        mock_get_corp_list.return_value = mock_corp_list
        
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["999999"],  # Invalid code
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        # Should propagate the error
        with pytest.raises(ValueError, match="Stock code not found"):
            service.search_filings(request)
    
    @patch('dart_fss_text.services.filing_search.dart.get_corp_list')
    def test_handles_empty_search_results(self, mock_get_corp_list):
        """
        Should return empty list if no filings found.
        
        This is valid - a company might not have filings in the date range.
        """
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.search_filings = Mock(return_value=[])  # No results
        
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_get_corp_list.return_value = mock_corp_list
        
        service = FilingSearchService()
        request = FetchReportsRequest(
            stock_codes=["005930"],
            start_date="20200101",
            end_date="20200131",  # Very narrow range
            report_types=["A001"]
        )
        
        results = service.search_filings(request)
        
        # Should return empty list, not raise error
        assert results == []
        assert isinstance(results, list)


class TestPerformanceConsiderations:
    """Test performance-related behavior."""
    
    @patch('dart_fss_text.services.filing_search.dart.get_corp_list')
    def test_get_corp_list_called_only_once_per_search(self, mock_get_corp_list):
        """
        Should leverage dart-fss Singleton pattern.
        
        From Experiment 6: dart.get_corp_list() is a Singleton - first call
        takes ~7s, subsequent calls are instant (0.000ms).
        """
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.search_filings = Mock(return_value=[])
        
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_get_corp_list.return_value = mock_corp_list
        
        service = FilingSearchService()
        
        # Search with multiple companies and report types
        request = FetchReportsRequest(
            stock_codes=["005930", "000660"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001", "A002"]
        )
        
        service.search_filings(request)
        
        # get_corp_list should be called only once (Singleton pattern)
        # Even though we're searching 2 companies × 2 report types = 4 searches
        assert mock_get_corp_list.call_count == 1


class TestInputValidation:
    """Test that service properly uses validated inputs."""
    
    def test_rejects_invalid_request_object(self):
        """Should only accept FetchReportsRequest, not arbitrary dicts."""
        service = FilingSearchService()
        
        # Invalid input (plain dict instead of validated model)
        with pytest.raises((TypeError, AttributeError)):
            service.search_filings({
                'stock_codes': ['005930'],
                'start_date': 'invalid',
                'report_types': ['INVALID']
            })
    
    def test_accepts_only_validated_report_types(self):
        """
        FetchReportsRequest should reject invalid report types.
        
        This is tested in test_models.py, but verifying service relies on it.
        """
        # This should raise during Pydantic validation
        with pytest.raises(ValueError, match="Invalid report type"):
            FetchReportsRequest(
                stock_codes=["005930"],
                start_date="20230101",
                end_date="20241231",
                report_types=["INVALID"]
            )

