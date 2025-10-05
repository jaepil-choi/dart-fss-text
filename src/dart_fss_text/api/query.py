"""
High-level query interface for retrieving sections.

This module provides TextQuery, a simple and powerful interface for
querying stored financial disclosure sections with support for all
research use cases.
"""

from typing import Dict, List, Union, Optional

from dart_fss_text.models import Sequence
from dart_fss_text.services.storage_service import StorageService


class TextQuery:
    """
    High-level query interface for retrieving sections.
    
    Provides a simple get() method that handles all common use cases:
    - Single firm, single year
    - Cross-sectional analysis (multiple firms, single year)
    - Time series analysis (single firm, multiple years)
    - Panel data (multiple firms, multiple years)
    
    Returns data in universal format: {year: {stock_code: Sequence}}
    
    Example:
        >>> from dart_fss_text.api import TextQuery
        >>> from dart_fss_text.services import StorageService
        >>> 
        >>> storage = StorageService(
        ...     mongo_uri="mongodb://localhost:27017/",
        ...     database="FS",
        ...     collection="A001"
        ... )
        >>> query = TextQuery(storage_service=storage)
        >>> 
        >>> # Query Samsung's 2024 business overview
        >>> result = query.get(
        ...     stock_codes="005930",
        ...     years=2024,
        ...     section_codes="020100"
        ... )
        >>> text = result["2024"]["005930"].text
    """
    
    def __init__(self, storage_service: StorageService):
        """
        Initialize with injected storage service.
        
        Args:
            storage_service: StorageService instance for MongoDB access
        
        Example:
            >>> storage = StorageService(mongo_uri="...", database="FS", collection="A001")
            >>> query = TextQuery(storage_service=storage)
        """
        self._storage = storage_service
    
    def get(
        self,
        stock_codes: Union[str, List[str]],
        years: Union[str, int, List[Union[str, int]], None] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        section_codes: Union[str, List[str]] = "020000",
    ) -> Dict[str, Dict[str, Sequence]]:
        """
        Retrieve sections in universal format.
        
        Args:
            stock_codes: Single stock code or list
                        Examples: "005930" or ["005930", "000660"]
            
            years: Single year or list (mutually exclusive with start_year/end_year)
                  Examples: 2024, "2024", [2023, 2024]
                  If None, must provide start_year/end_year
            
            start_year: Start of year range (inclusive)
                       Must be provided with end_year
            
            end_year: End of year range (inclusive)
                     Must be provided with start_year
            
            section_codes: Single section code or list
                          Examples: "020100" or ["020100", "020200"]
                          Parent codes (e.g., "020000") retrieve all descendants
                          Default: "020000" (II. 사업의 내용)
        
        Returns:
            Dictionary: {year: {stock_code: Sequence}}
            
            Structure:
            {
                "2024": {
                    "005930": Sequence([SectionDocument, ...]),
                    "000660": Sequence([...])
                },
                "2023": {
                    "005930": Sequence([...]),
                    "000660": Sequence([...])
                }
            }
        
        Raises:
            ValueError: If both years and start_year/end_year provided
            ValueError: If only one of start_year/end_year provided
            ValueError: If end_year < start_year
            ValueError: If neither years nor start_year/end_year provided
            ValueError: If years list is empty
        
        Examples:
            # Single firm, single year
            result = query.get(stock_codes="005930", years=2024)
            
            # Cross-sectional
            result = query.get(stock_codes=["005930", "000660"], years=2024)
            
            # Time series
            result = query.get(stock_codes="005930", start_year=2020, end_year=2024)
            
            # Panel data
            result = query.get(
                stock_codes=["005930", "000660"],
                start_year=2020,
                end_year=2024
            )
        """
        # Validate arguments
        self._validate_get_args(years, start_year, end_year)
        
        # Normalize inputs to lists
        stock_codes_list = self._normalize_list(stock_codes)
        section_codes_list = self._normalize_list(section_codes)
        years_list = self._normalize_years(years, start_year, end_year)
        
        # Build result structure: {year: {stock_code: Sequence}}
        result: Dict[str, Dict[str, Sequence]] = {}
        
        for year in years_list:
            result[str(year)] = {}
            
            for stock_code in stock_codes_list:
                # Fetch sections from storage
                section_docs = self._fetch_sections(
                    stock_code=stock_code,
                    year=str(year),
                    section_codes=section_codes_list
                )
                
                if section_docs:
                    # Create Sequence from SectionDocument objects
                    result[str(year)][stock_code] = Sequence(section_docs)
        
        return result
    
    # === Private Helper Methods ===
    
    def _validate_get_args(
        self,
        years: Union[str, int, List[Union[str, int]], None],
        start_year: Optional[int],
        end_year: Optional[int]
    ) -> None:
        """Validate get() method arguments."""
        # Check mutual exclusivity
        has_years = years is not None
        has_year_range = start_year is not None or end_year is not None
        
        if has_years and has_year_range:
            raise ValueError(
                "Cannot provide both 'years' and 'start_year'/'end_year'. "
                "Use one or the other."
            )
        
        if not has_years and not has_year_range:
            raise ValueError(
                "Must provide either 'years' or 'start_year'/'end_year'."
            )
        
        # Check year range pairing
        if (start_year is None) != (end_year is None):
            raise ValueError(
                "Must provide both 'start_year' and 'end_year', or neither."
            )
        
        # Check year range validity
        if start_year is not None and end_year is not None:
            if end_year < start_year:
                raise ValueError(
                    f"end_year ({end_year}) must be >= start_year ({start_year})"
                )
        
        # Check years not empty list
        if isinstance(years, list) and len(years) == 0:
            raise ValueError("'years' list cannot be empty")
    
    def _normalize_list(self, value: Union[str, List[str]]) -> List[str]:
        """Convert single value to list."""
        return [value] if isinstance(value, str) else value
    
    def _normalize_years(
        self,
        years: Union[str, int, List[Union[str, int]], None],
        start_year: Optional[int],
        end_year: Optional[int]
    ) -> List[int]:
        """Convert year arguments to list of integers."""
        if years is not None:
            if isinstance(years, (str, int)):
                return [int(years)]
            else:
                return [int(y) for y in years]
        elif start_year is not None and end_year is not None:
            return list(range(start_year, end_year + 1))
        else:
            raise ValueError("Must provide either 'years' or 'start_year'/'end_year'")
    
    def _fetch_sections(
        self,
        stock_code: str,
        year: str,
        section_codes: List[str]
    ) -> List:
        """
        Fetch sections from storage.
        
        Handles:
        - Single section retrieval
        - Parent section + all descendants retrieval
        - Multiple section codes
        - Multiple reports per company/year (uses latest report)
        
        Note:
            If a company has multiple reports for the same year (e.g., amendments),
            this returns sections from the LATEST report only (highest rcept_no).
        """
        # Get all sections for this company and year
        sections_data = self._storage.get_sections_by_company(stock_code=stock_code, year=year)
        
        if not sections_data:
            return []
        
        # Convert to SectionDocument objects
        from dart_fss_text.models import SectionDocument
        all_sections = [SectionDocument(**data) for data in sections_data]
        
        # Handle multiple reports per company/year
        # Group by rcept_no and select the latest (highest rcept_no = most recent filing)
        from collections import defaultdict
        by_rcept_no = defaultdict(list)
        for section in all_sections:
            by_rcept_no[section.rcept_no].append(section)
        
        # Select latest report (rcept_no is sortable: YYYYMMDDNNNNNN format)
        latest_rcept_no = max(by_rcept_no.keys())
        all_sections = by_rcept_no[latest_rcept_no]
        
        # Filter to requested section codes (including descendants)
        # Descendants are identified by section_path containing the parent code
        filtered_sections = []
        for section_code in section_codes:
            for section in all_sections:
                # Include section if:
                # 1. Exact match (section.section_code == section_code)
                # 2. Section is a descendant (section_code in section.section_path)
                if section.section_code == section_code or section_code in section.section_path:
                    if section not in filtered_sections:  # Avoid duplicates
                        filtered_sections.append(section)
        
        # Sort by section_code to maintain TOC order
        # section_code is zero-padded 6-digit string (e.g., "010000", "010100")
        # Can be sorted lexicographically
        if filtered_sections:
            filtered_sections.sort(key=lambda s: s.section_code)
        
        return filtered_sections

