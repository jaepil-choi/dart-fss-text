"""
Filing Search Service

Service for searching DART filings using dart-fss API.
Converts user-friendly stock codes to corp codes and searches for filings
by report type and date range.

Based on Experiment 7 (exp_07_search_download_organize.py) findings:
- Uses Corp.search_filings() with pblntf_detail_ty parameter
- Uses CorpListService for cached corp lookups (replaces dart.get_corp_list())
- Returns Filing objects with PIT-critical fields
"""

from typing import List
import logging

from dart_fss_text.models.requests import SearchFilingsRequest
from dart_fss_text.config import get_app_config
from dart_fss_text.services.corp_list_service import CorpListService


logger = logging.getLogger(__name__)


class FilingSearchService:
    """
    Service for searching DART filings.
    
    This service wraps dart-fss API calls to provide a clean interface for
    filing discovery. It handles:
    - Stock code → corp code conversion
    - Filing search by report type and date range
    - Result aggregation across multiple companies and report types
    
    Usage:
        # Initialize corp list first (one-time, ~7s)
        from dart_fss_text.services.corp_list_service import CorpListService
        CorpListService().initialize()
        
        # Then use FilingSearchService
        service = FilingSearchService()
        request = SearchFilingsRequest(
            stock_codes=["005930"],
            start_date="20230101",
            end_date="20241231",
            report_types=["A001", "A002"]
        )
        filings = service.search_filings(request)
        
        # Process filings
        for filing in filings:
            print(f"{filing.report_nm}: {filing.rcept_no}")
    
    Performance:
        - Requires CorpListService.initialize() first (~7s one-time)
        - Subsequent searches: instant (uses cached CorpList)
        - Each search: ~0.26s (validated in Experiment 7)
    """
    
    def __init__(self):
        """
        Initialize the filing search service.
        
        Uses CorpListService for cached corp lookups. CorpListService must
        be initialized first via initialize().
        
        Raises:
            RuntimeError: If CorpListService not initialized
        """
        self._corp_list_service = CorpListService()
        
        # Check if initialized
        try:
            self._corp_list = self._corp_list_service.get_corp_list()
        except RuntimeError:
            raise RuntimeError(
                "CorpListService not initialized. "
                "Call CorpListService().initialize() first."
            )
    
    def search_filings(self, request: SearchFilingsRequest) -> List:
        """
        Search for filings matching the request criteria.
        
        Args:
            request: SearchFilingsRequest with validated inputs:
                - stock_codes: List of 6-digit stock codes (e.g., ["005930"])
                - start_date: Start date in YYYYMMDD format
                - end_date: End date in YYYYMMDD format
                - report_types: DART report type codes (e.g., ["A001", "A002"])
        
        Returns:
            List of Filing objects from dart-fss, each containing:
                - rcept_no: 14-digit receipt number (for document download)
                - rcept_dt: 8-digit publication date YYYYMMDD (for PIT structure)
                - corp_code: 8-digit corporation code
                - report_nm: Report name in Korean (e.g., "사업보고서 (2023.12)")
        
        Raises:
            ValueError: If stock code is not found in DART database
            AttributeError: If dart-fss API returns unexpected structure
        
        Example:
            >>> service = FilingSearchService()
            >>> request = SearchFilingsRequest(
            ...     stock_codes=["005930"],
            ...     start_date="20230101",
            ...     end_date="20231231",
            ...     report_types=["A001"]
            ... )
            >>> filings = service.search_filings(request)
            >>> len(filings)
            2
            >>> filings[0].rcept_no
            '20240312000736'
        
        Notes:
            - Uses CorpListService for cached corp lookups (replaces dart.get_corp_list())
            - Searches each report type separately and aggregates results
            - Returns empty list if no filings found (not an error)
            - All returned filings have rcept_dt within [start_date, end_date]
        """
        # Aggregate all results
        all_filings = []
        
        # Search each stock code
        for stock_code in request.stock_codes:
            # First check cache (includes delisted companies)
            corp_data = self._corp_list_service.find_by_stock_code(stock_code)
            
            if corp_data is None:
                logger.warning(
                    f"Stock code {stock_code} not found in DART database. "
                    f"Company may be delisted or not registered with DART."
                )
                continue
            
            # Get Corp object for search_filings() method
            # Explicitly include delisted companies to match cache behavior
            corp = self._corp_list.find_by_stock_code(stock_code, include_delisting=True)
            
            # Double-check: Corp object should exist if cache found it
            if corp is None:
                logger.warning(
                    f"Stock code {stock_code} found in cache but not in CorpList. "
                    f"This should not happen. Skipping."
                )
                continue
            
            # Search each report type
            for report_type in request.report_types:
                # Use Corp.search_filings() with correct parameters
                # (validated in Experiment 7 and Experiment 2C)
                try:
                    filings = corp.search_filings(
                        bgn_de=request.start_date,
                        end_de=request.end_date,
                        pblntf_detail_ty=report_type
                    )
                    
                    # Aggregate results
                    all_filings.extend(filings)
                except Exception as e:
                    # Handle NoDataReceived exception from dart-fss gracefully
                    # This happens when no filings match the search criteria
                    error_type = type(e).__name__
                    if "NoDataReceived" in error_type or "조회된 데이타가 없습니다" in str(e):
                        # No filings found - this is normal, continue to next report type
                        logger.debug(
                            f"No filings found for {stock_code}, "
                            f"report type {report_type}, date range {request.start_date}-{request.end_date}"
                        )
                        continue
                    else:
                        # Unexpected error - re-raise
                        raise
        
        return all_filings

