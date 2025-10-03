"""
Filing Search Service

Service for searching DART filings using dart-fss API.
Converts user-friendly stock codes to corp codes and searches for filings
by report type and date range.

Based on Experiment 7 (exp_07_search_download_organize.py) findings:
- Uses Corp.search_filings() with pblntf_detail_ty parameter
- Leverages dart.get_corp_list() Singleton pattern
- Returns Filing objects with PIT-critical fields
"""

from typing import List
import dart_fss as dart

from dart_fss_text.models.requests import SearchFilingsRequest


class FilingSearchService:
    """
    Service for searching DART filings.
    
    This service wraps dart-fss API calls to provide a clean interface for
    filing discovery. It handles:
    - Stock code → corp code conversion
    - Filing search by report type and date range
    - Result aggregation across multiple companies and report types
    
    Usage:
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
        - First call: ~7s (dart.get_corp_list() loads ~114K corps)
        - Subsequent calls: instant (Singleton pattern)
        - Each search: ~0.26s (validated in Experiment 7)
    """
    
    def __init__(self):
        """Initialize the filing search service."""
        pass  # No initialization needed - dart-fss handles state
    
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
            - Uses dart.get_corp_list() which is a Singleton (cached after first call)
            - Searches each report type separately and aggregates results
            - Returns empty list if no filings found (not an error)
            - All returned filings have rcept_dt within [start_date, end_date]
        """
        # Get corporation list (Singleton - instant after first call)
        corp_list = dart.get_corp_list()
        
        # Aggregate all results
        all_filings = []
        
        # Search each stock code
        for stock_code in request.stock_codes:
            # Convert stock code to corp object
            corp = corp_list.find_by_stock_code(stock_code)
            
            # Search each report type
            for report_type in request.report_types:
                # Use Corp.search_filings() with correct parameters
                # (validated in Experiment 7 and Experiment 2C)
                filings = corp.search_filings(
                    bgn_de=request.start_date,
                    end_de=request.end_date,
                    pblntf_detail_ty=report_type
                )
                
                # Aggregate results
                all_filings.extend(filings)
        
        return all_filings

