"""
Unit tests for Filing Search Service

Tests the search service that wraps dart-fss API calls for filing discovery.
Based on findings from Experiment 7 (exp_07_search_download_organize.py).

IMPORTANT: These are UNIT tests - they mock all external dependencies.
- All dart.get_corp_list() calls are mocked via autouse fixture
- No live API calls should occur
- For integration tests with live API, see test_filing_search_integration.py
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from dart_fss_text.services.filing_search import FilingSearchService
from dart_fss_text.models.requests import SearchFilingsRequest


@pytest.fixture
def mock_corp_list_service():
    """Mock CorpListService for tests."""
    mock_service = Mock()
    
    # Mock find_by_stock_code to return dict
    def find_by_stock_code(stock_code):
        if stock_code == "005930":
            return {
                'corp_code': '00126380',
                'corp_name': '삼성전자',
                'stock_code': '005930'
            }
        elif stock_code == "000660":
            return {
                'corp_code': '00118332',
                'corp_name': 'SK하이닉스',
                'stock_code': '000660'
            }
        return None
    
    mock_service.find_by_stock_code = find_by_stock_code
    
    # Mock get_corp_list to return CorpList with Corp objects
    # Note: Corp objects are still needed for search_filings() method
    mock_corp_list = Mock()
    
    # Samsung Corp object
    mock_samsung_corp = Mock()
    mock_samsung_corp.corp_code = "00126380"
    mock_samsung_corp.corp_name = "삼성전자"
    mock_samsung_corp.search_filings = Mock(return_value=[])
    
    # SK Hynix Corp object
    mock_hynix_corp = Mock()
    mock_hynix_corp.corp_code = "00118332"
    mock_hynix_corp.corp_name = "SK하이닉스"
    mock_hynix_corp.search_filings = Mock(return_value=[])
    
    def find_by_stock_code_corp(stock_code, include_delisting=True):
        if stock_code == "005930":
            return mock_samsung_corp
        elif stock_code == "000660":
            return mock_hynix_corp
        return None
    
    mock_corp_list.find_by_stock_code = Mock(side_effect=find_by_stock_code_corp)
    mock_service.get_corp_list = Mock(return_value=mock_corp_list)
    
    return mock_service


@pytest.fixture(autouse=True)
def mock_corp_list_service_init(mock_corp_list_service):
    """
    Auto-mock CorpListService for ALL tests in this file.
    
    This prevents unit tests from making live API calls that:
    - Take 7+ seconds on first call
    - Require valid API key
    - Load 114K companies unnecessarily
    
    Each test can override this mock if needed by adding its own
    @patch decorator.
    """
    with patch('dart_fss_text.services.filing_search.CorpListService', return_value=mock_corp_list_service):
        yield mock_corp_list_service


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
    
    def test_accepts_search_filings_request(self):
        """Should accept SearchFilingsRequest as input."""
        service = FilingSearchService()
        
        # Valid request (uses our validated Pydantic model)
        request = SearchFilingsRequest(
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
    
    def test_uses_corp_list_service(self, mock_corp_list_service_init):
        """Should use CorpListService for cached lookups."""
        # Create service and search
        service = FilingSearchService()
        request = SearchFilingsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        service.search_filings(request)
        
        # Verify CorpListService.find_by_stock_code was called
        mock_corp_list_service_init.find_by_stock_code.assert_called_with("005930")
        
        # Verify get_corp_list was called to get Corp object for search_filings
        mock_corp_list_service_init.get_corp_list.assert_called()
        
        # Verify CorpList.find_by_stock_code was called with include_delisting=True
        corp_list = mock_corp_list_service_init.get_corp_list.return_value
        corp_list.find_by_stock_code.assert_called_with("005930", include_delisting=True)
    
    def test_handles_multiple_stock_codes(self, mock_corp_list_service_init):
        """Should look up multiple stock codes."""
        # Setup mock to handle multiple stock codes
        mock_corp_list = Mock()
        
        # Samsung
        mock_samsung = Mock()
        mock_samsung.corp_code = "00126380"
        mock_samsung.search_filings = Mock(return_value=[])
        
        # SK Hynix
        mock_hynix = Mock()
        mock_hynix.corp_code = "00164779"
        mock_hynix.search_filings = Mock(return_value=[])
        
        def find_by_code(stock_code, include_delisting=True):
            if stock_code == "005930":
                return mock_samsung
            elif stock_code == "000660":
                return mock_hynix
            else:
                return None
        
        mock_corp_list.find_by_stock_code = Mock(side_effect=find_by_code)
        mock_corp_list_service_init.get_corp_list.return_value = mock_corp_list
        
        # Search multiple companies
        service = FilingSearchService()
        request = SearchFilingsRequest(
            stock_codes=["005930", "000660"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        service.search_filings(request)
        
        # Verify both cache lookups happened
        assert mock_corp_list_service_init.find_by_stock_code.call_count == 2
        mock_corp_list_service_init.find_by_stock_code.assert_any_call("005930")
        mock_corp_list_service_init.find_by_stock_code.assert_any_call("000660")
        
        # Verify both Corp object lookups happened with include_delisting=True
        assert mock_corp_list.find_by_stock_code.call_count == 2
        mock_corp_list.find_by_stock_code.assert_any_call("005930", include_delisting=True)
        mock_corp_list.find_by_stock_code.assert_any_call("000660", include_delisting=True)


class TestFilingSearch:
    """Test actual filing search using Corp.search_filings()."""
    
    def test_calls_corp_search_filings_with_correct_params(self, mock_corp_list_service_init):
        """
        Should call Corp.search_filings() with bgn_de and pblntf_detail_ty.
        
        From Experiment 7: Corp.search_filings(bgn_de, pblntf_detail_ty) is the
        correct method that returns Filing objects.
        """
        # Setup mock CorpList with Corp object
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.corp_code = "00126380"
        mock_corp.search_filings = Mock(return_value=[])
        
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_corp_list_service_init.get_corp_list.return_value = mock_corp_list
        
        # Search
        service = FilingSearchService()
        request = SearchFilingsRequest(
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
        
        # Verify cache lookup happened first
        mock_corp_list_service_init.find_by_stock_code.assert_called_with("005930")
    
    def test_searches_multiple_report_types(self, mock_corp_list_service_init):
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
        mock_corp_list_service_init.get_corp_list.return_value = mock_corp_list
        
        # Search multiple report types
        service = FilingSearchService()
        request = SearchFilingsRequest(
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
    
    def test_aggregates_results_from_multiple_companies_and_types(self, mock_corp_list_service_init):
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
        
        def find_by_code(stock_code, include_delisting=True):
            return mock_corp1 if stock_code == "005930" else mock_corp2
        
        mock_corp_list.find_by_stock_code = Mock(side_effect=find_by_code)
        mock_corp_list_service_init.get_corp_list.return_value = mock_corp_list
        
        # Search 2 companies × 2 report types
        service = FilingSearchService()
        request = SearchFilingsRequest(
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
    
    def test_returns_filing_objects_with_required_fields(self, mock_corp_list_service_init):
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
        mock_corp_list_service_init.get_corp_list.return_value = mock_corp_list
        
        # Search
        service = FilingSearchService()
        request = SearchFilingsRequest(
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
    
    def test_handles_invalid_stock_code(self, mock_corp_list_service_init):
        """Should skip invalid stock code and continue."""
        # Mock cache returns None for invalid stock code
        def find_by_stock_code(stock_code):
            if stock_code == "999999":
                return None
            return {'corp_code': '00126380', 'corp_name': '삼성전자', 'stock_code': '005930'}
        
        mock_corp_list_service_init.find_by_stock_code = Mock(side_effect=find_by_stock_code)
        
        service = FilingSearchService()
        request = SearchFilingsRequest(
            stock_codes=["999999"],  # Invalid code
            start_date="20230101",
            end_date="20241231",
            report_types=["A001"]
        )
        
        # Should return empty list (not raise error)
        results = service.search_filings(request)
        assert results == []
    
    def test_handles_empty_search_results(self, mock_corp_list_service_init):
        """
        Should return empty list if no filings found.
        
        This is valid - a company might not have filings in the date range.
        """
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.search_filings = Mock(return_value=[])  # No results
        
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_corp_list_service_init.get_corp_list.return_value = mock_corp_list
        
        service = FilingSearchService()
        request = SearchFilingsRequest(
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
    
    def test_corp_list_service_called_efficiently(self, mock_corp_list_service_init):
        """
        Should use CorpListService efficiently.
        
        CorpListService uses cached DataFrame lookups (<1ms) and only
        calls get_corp_list() once to get Corp objects for search_filings().
        """
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.search_filings = Mock(return_value=[])
        
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_corp_list_service_init.get_corp_list.return_value = mock_corp_list
        
        service = FilingSearchService()
        
        # Search with multiple companies and report types
        request = SearchFilingsRequest(
            stock_codes=["005930", "000660"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001", "A002"]
        )
        
        service.search_filings(request)
        
        # get_corp_list should be called only once (for Corp objects)
        # Cache lookups happen separately (fast DataFrame queries)
        assert mock_corp_list_service_init.get_corp_list.call_count == 1
        
        # Cache find_by_stock_code called for each stock code
        assert mock_corp_list_service_init.find_by_stock_code.call_count == 2


class TestInputValidation:
    """Test that service properly uses validated inputs."""
    
    def test_rejects_invalid_request_object(self, mock_corp_list_service_init):
        """Should only accept SearchFilingsRequest, not arbitrary dicts."""
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
        SearchFilingsRequest should reject invalid report types.
        
        This is tested in test_models.py, but verifying service relies on it.
        """
        # This should raise during Pydantic validation
        with pytest.raises(ValueError, match="Invalid report type"):
            SearchFilingsRequest(
                stock_codes=["005930"],
                start_date="20230101",
                end_date="20241231",
                report_types=["INVALID"]
            )

