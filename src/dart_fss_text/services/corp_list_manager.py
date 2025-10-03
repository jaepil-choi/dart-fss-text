"""
Corporation List Manager (Phase 0).

Manages the corporation list cache that enables stock_code → corp_code conversion.
This is the foundation service that must run before any discovery operations.

Validated in Experiment 5:
- 3,901 listed corporations successfully cached
- 0 duplicates in stock_code or corp_code
- 100% success rate with real DART data
- Performance: CSV load (~100ms) vs API call (~10s) = 100x faster
"""

from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import dart_fss


class CorpListManager:
    """
    Manage corporation list with CSV caching.
    
    This service provides the Phase 0 foundation for the discovery pipeline:
    - Loads corporation list from CSV cache (fast path)
    - Fetches from DART API if cache missing (slow path)
    - Filters to only listed stocks (stock_code is not None)
    - Provides stock_code → corp_code lookup
    - Provides company metadata retrieval
    
    Rationale:
    - dart-fss.get_corp_list() loads 114K+ corps (~10s API call)
    - Users provide stock codes, DART API needs corp codes
    - Cache to CSV enables instant lookup without repeated API calls
    - Validated in Experiment 5: 3,901 listed stocks successfully cached
    
    Usage:
        # Phase 0: Build/load company list FIRST
        manager = CorpListManager()
        manager.load()  # Auto-loads from cache or fetches if missing
        
        # Phase 1: Now ready for stock_code → corp_code conversion
        corp_code = manager.get_corp_code("005930")
        info = manager.get_company_info("005930")
    """
    
    def __init__(self, cache_path: Path = Path("data/corp_list.csv")):
        """
        Initialize CorpListManager.
        
        Args:
            cache_path: Path to CSV cache file. Defaults to data/corp_list.csv
        """
        self._cache_path = cache_path
        self._corp_list: Optional[dart_fss.CorpList] = None
        self._lookup: Dict[str, str] = {}  # stock_code -> corp_code
        self._df: Optional[pd.DataFrame] = None  # Full company data
    
    def load(self, force_refresh: bool = False) -> None:
        """
        Load corporation list from cache or fetch from DART API.
        
        This is the Phase 0 initialization step that must run before
        any fetch_reports() calls in Phase 1.
        
        Args:
            force_refresh: If True, fetch from API even if cache exists
        
        Behavior:
            - If cache exists and not force_refresh: Load from CSV (~100ms)
            - If cache missing or force_refresh: Fetch from DART API (~10s)
            - Filters to only listed stocks (stock_code is not None)
            - Saves to CSV for future runs
        """
        if not force_refresh and self._cache_path.exists():
            # Fast path: Load from CSV
            self._df = pd.read_csv(self._cache_path, dtype=str)  # Keep as strings
            self._lookup = self._df.set_index('stock_code')['corp_code'].to_dict()
        else:
            # Slow path: Fetch from DART API
            self._corp_list = dart_fss.get_corp_list()
            listed = [c for c in self._corp_list.corps if c.stock_code]
            
            # Extract data to list of dicts using .to_dict()
            corp_data = [corp.to_dict() for corp in listed]
            self._df = pd.DataFrame(corp_data)
            
            # Save to CSV for future runs
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._df.to_csv(self._cache_path, index=False, encoding='utf-8-sig')
            
            # Build lookup dict
            self._lookup = self._df.set_index('stock_code')['corp_code'].to_dict()
    
    def get_corp_code(self, stock_code: str) -> str:
        """
        Convert stock_code to corp_code.
        
        Args:
            stock_code: 6-digit stock code (e.g., "005930" for Samsung)
        
        Returns:
            8-digit corp_code for DART API calls
        
        Raises:
            ValueError: If stock_code not found in loaded corporation list
        
        Example:
            >>> manager = CorpListManager()
            >>> manager.load()
            >>> corp_code = manager.get_corp_code("005930")
            >>> print(corp_code)
            '00126380'
        """
        if stock_code not in self._lookup:
            raise ValueError(f"Stock code not found: {stock_code}")
        return self._lookup[stock_code]
    
    def get_company_info(self, stock_code: str) -> Dict:
        """
        Get full company metadata from cache.
        
        Args:
            stock_code: 6-digit stock code
        
        Returns:
            Dictionary with all company metadata (11 columns from DART):
            - corp_code: Corporation code (8 digits)
            - corp_name: Company name (Korean)
            - corp_eng_name: Company name (English)
            - stock_code: Stock code (6 digits)
            - modify_date: Last modification date
            - corp_cls: Market classification (Y/K/N/E)
            - market_type: Market type (redundant with corp_cls)
            - sector: Industry sector (may be None for 29% of corps)
            - product: Main products (may be None for 29% of corps)
            - trading_halt: Trading halt status
            - issue: Issue status
        
        Raises:
            ValueError: If stock_code not found
        
        Example:
            >>> info = manager.get_company_info("005930")
            >>> print(info['corp_name'])
            '삼성전자'
            >>> print(info['corp_cls'])
            'Y'  # KOSPI
        """
        if stock_code not in self._lookup:
            raise ValueError(f"Stock code not found: {stock_code}")
        
        # Get row for this stock code
        row = self._df[self._df['stock_code'] == stock_code].iloc[0]
        
        # Convert to dict
        return row.to_dict()

