"""
CorpList Service

Service for managing corporation list data with CSV-backed storage.
Replaces direct dart.get_corp_list() calls with cached CSV lookups for faster access.

Design:
- Singleton pattern (similar to dart-fss CorpList)
- Explicit initialization via initialize() method
- CSV storage in data/temp/corp_list_{timestamp}.csv
- Fast DataFrame-based lookups after initialization
"""

from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import logging

import dart_fss as dart
import pandas as pd

from dart_fss_text.config import get_app_config

logger = logging.getLogger(__name__)


class CorpListService:
    """
    Service for managing corporation list data with CSV-backed storage.
    
    Provides fast lookups of corporation data without requiring API calls
    after initial initialization. Uses pandas DataFrame for efficient
    in-memory lookups.
    
    Usage:
        # Initialize once (loads from API and saves to CSV)
        service = CorpListService()
        service.initialize()
        
        # Fast lookups (from cached DataFrame)
        corp_data = service.find_by_stock_code('005930')
        if corp_data:
            print(f"Found: {corp_data['corp_name']}")
        
        # Get all corps as DataFrame
        all_corps = service.get_all()
    
    Performance:
        - initialize(): ~7s first time (API load), then saves to CSV
        - find_by_stock_code(): <0.001s (DataFrame lookup)
        - get_all(): Returns cached DataFrame instantly
    """
    
    _instance: Optional['CorpListService'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton pattern - return same instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._df: Optional[pd.DataFrame] = None
            cls._instance._csv_path: Optional[Path] = None
            cls._instance._corp_list: Optional[object] = None  # dart-fss CorpList object
        return cls._instance
    
    def initialize(self) -> Path:
        """
        Explicit initialization function.
        
        Loads corporation list from DART API, converts to DataFrame,
        and saves to timestamped CSV file. Caches DataFrame in memory
        for fast subsequent lookups.
        
        Returns:
            Path to the saved CSV file
            
        Raises:
            ValueError: If OPENDART_API_KEY is not set
            
        Example:
            >>> service = CorpListService()
            >>> csv_path = service.initialize()
            >>> print(f"Saved to: {csv_path}")
            Saved to: data/temp/corp_list_20250115_143022.csv
        """
        if self._initialized and self._df is not None:
            logger.info("CorpListService already initialized, using cached data")
            return self._csv_path
        
        config = get_app_config()
        
        # Set API key for dart-fss
        if not config.opendart_api_key:
            raise ValueError(
                "OPENDART_API_KEY not found in environment. "
                "Please set it in .env file or environment variables."
            )
        
        dart.set_api_key(api_key=config.opendart_api_key)
        
        # Load from API
        logger.info("Loading corporation list from DART API...")
        self._corp_list = dart.get_corp_list()
        
        # Convert to list of dictionaries
        logger.info(f"Converting {len(self._corp_list.corps)} corps to dictionaries...")
        corp_dicts = [corp.to_dict() for corp in self._corp_list.corps]
        
        # Create DataFrame
        logger.info("Creating DataFrame...")
        self._df = pd.DataFrame(corp_dicts)
        
        # Ensure data/temp directory exists
        db_dir = Path(config.corp_list_db_dir)
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._csv_path = db_dir / f"corp_list_{timestamp}.csv"
        
        # Save to CSV
        logger.info(f"Saving to {self._csv_path}...")
        self._df.to_csv(self._csv_path, index=False, encoding='utf-8')
        
        logger.info(f"✓ Saved {len(self._df)} corps to CSV")
        self._initialized = True
        
        return self._csv_path
    
    def find_by_stock_code(self, stock_code: str) -> Optional[Dict]:
        """
        Find corporation data by stock code.
        
        Fast lookup from cached DataFrame. Returns None if stock code
        is not found.
        
        **Important**: This method includes delisted companies (unlike dart-fss
        default behavior). The DataFrame contains ALL companies from DART API,
        including those that have been delisted. This is critical for historical
        data analysis.
        
        Args:
            stock_code: 6-digit stock code (e.g., '005930')
            
        Returns:
            Dictionary with corp data (all attributes from Corp.to_dict())
            or None if not found
            
        Raises:
            RuntimeError: If service not initialized
            
        Example:
            >>> service = CorpListService()
            >>> service.initialize()
            >>> corp_data = service.find_by_stock_code('005930')
            >>> if corp_data:
            ...     print(corp_data['corp_name'])
            삼성전자
            
        Note:
            Unlike dart-fss's find_by_stock_code() which defaults to
            include_delisting=False, this method always includes delisted companies
            since the DataFrame contains all companies from the API.
        """
        if not self._initialized or self._df is None:
            raise RuntimeError(
                "CorpListService not initialized. Call initialize() first."
            )
        
        # Filter DataFrame by stock_code
        result = self._df[self._df['stock_code'] == stock_code]
        
        if len(result) == 0:
            return None
        
        # Convert first row to dict
        corp_data = result.iloc[0].to_dict()
        
        # Convert pandas types to native Python types
        # (handles NaN, etc.)
        for key, value in corp_data.items():
            if pd.isna(value):
                corp_data[key] = None
            elif isinstance(value, (pd.Timestamp, pd.Timedelta)):
                corp_data[key] = str(value)
            elif hasattr(value, 'item'):  # numpy scalar
                corp_data[key] = value.item()
        
        return corp_data
    
    def find_by_corp_code(self, corp_code: str) -> Optional[Dict]:
        """
        Find corporation data by corporation code.
        
        Fast lookup from cached DataFrame. Returns None if corp code
        is not found.
        
        Args:
            corp_code: 8-digit corporation code (e.g., '00126380')
            
        Returns:
            Dictionary with corp data (all attributes from Corp.to_dict())
            or None if not found
            
        Raises:
            RuntimeError: If service not initialized
            
        Example:
            >>> service = CorpListService()
            >>> service.initialize()
            >>> corp_data = service.find_by_corp_code('00126380')
            >>> if corp_data:
            ...     print(corp_data['corp_name'])
            삼성전자
        """
        if not self._initialized or self._df is None:
            raise RuntimeError(
                "CorpListService not initialized. Call initialize() first."
            )
        
        # Filter DataFrame by corp_code
        result = self._df[self._df['corp_code'] == corp_code]
        
        if len(result) == 0:
            return None
        
        # Convert first row to dict
        corp_data = result.iloc[0].to_dict()
        
        # Convert pandas types to native Python types
        # (handles NaN, etc.)
        for key, value in corp_data.items():
            if pd.isna(value):
                corp_data[key] = None
            elif isinstance(value, (pd.Timestamp, pd.Timedelta)):
                corp_data[key] = str(value)
            elif hasattr(value, 'item'):  # numpy scalar
                corp_data[key] = value.item()
        
        return corp_data
    
    def get_all(self) -> pd.DataFrame:
        """
        Get all corporations as DataFrame.
        
        Returns cached DataFrame with all corporation data.
        
        Returns:
            DataFrame with all corps (columns from Corp.to_dict())
            
        Raises:
            RuntimeError: If service not initialized
            
        Example:
            >>> service = CorpListService()
            >>> service.initialize()
            >>> all_corps = service.get_all()
            >>> print(f"Total corps: {len(all_corps)}")
            Total corps: 114595
        """
        if not self._initialized or self._df is None:
            raise RuntimeError(
                "CorpListService not initialized. Call initialize() first."
            )
        
        return self._df.copy()
    
    def get_all_listed_stock_codes(self) -> List[str]:
        """
        Get all listed stock codes (companies with non-null stock_code).
        
        Filters the cached DataFrame to return only companies that have
        a stock_code (listed companies). Returns stock codes as strings.
        
        Returns:
            List of stock codes (e.g., ["005930", "000660", ...])
            
        Raises:
            RuntimeError: If service not initialized
            
        Example:
            >>> service = CorpListService()
            >>> service.initialize()
            >>> stock_codes = service.get_all_listed_stock_codes()
            >>> print(f"Total listed companies: {len(stock_codes)}")
            Total listed companies: 3901
            >>> print(f"First 5: {stock_codes[:5]}")
            First 5: ['005930', '000660', '035420', ...]
        """
        if not self._initialized or self._df is None:
            raise RuntimeError(
                "CorpListService not initialized. Call initialize() first."
            )
        
        # Filter to only listed companies (stock_code not null)
        listed_corps = self._df[self._df['stock_code'].notna()]
        
        # Convert to list of strings, removing any NaN values
        stock_codes = listed_corps['stock_code'].astype(str).tolist()
        
        # Filter out any invalid codes (e.g., 'nan' strings)
        stock_codes = [code for code in stock_codes if code != 'nan' and len(code) == 6]
        
        return stock_codes
    
    def get_latest_db_path(self) -> Optional[Path]:
        """
        Get path to the most recent CSV file.
        
        Returns:
            Path to latest CSV file, or None if not initialized
            
        Example:
            >>> service = CorpListService()
            >>> service.initialize()
            >>> path = service.get_latest_db_path()
            >>> print(path)
            data/temp/corp_list_20250115_143022.csv
        """
        return self._csv_path
    
    def load_from_csv(self, csv_path: Path) -> None:
        """
        Load corporation data from a specific CSV file.
        
        Useful for loading backup files or specific snapshots.
        Overwrites current cached DataFrame.
        
        Args:
            csv_path: Path to CSV file to load
            
        Raises:
            FileNotFoundError: If CSV file doesn't exist
            
        Example:
            >>> service = CorpListService()
            >>> service.load_from_csv(Path('data/temp/corp_list_20250115_143022.csv'))
            >>> corp_data = service.find_by_stock_code('005930')
        """
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        logger.info(f"Loading corporation data from {csv_path}...")
        self._df = pd.read_csv(csv_path, encoding='utf-8')
        self._csv_path = csv_path
        
        # Note: When loading from CSV, we don't have Corp objects
        # User will need to call initialize() if they need Corp objects for search_filings()
        self._initialized = True
        logger.info(f"✓ Loaded {len(self._df)} corps from CSV")
        logger.warning("Note: Corp objects not available when loading from CSV. Call initialize() if needed.")
    
    def get_corp_list(self):
        """
        Get the cached dart-fss CorpList object.
        
        Returns the CorpList object from dart-fss, which provides access to
        Corp objects with methods like search_filings(). Only available
        after calling initialize() (not available when loading from CSV).
        
        Returns:
            dart-fss CorpList object
            
        Raises:
            RuntimeError: If service not initialized or CorpList not available
            
        Example:
            >>> service = CorpListService()
            >>> service.initialize()
            >>> corp_list = service.get_corp_list()
            >>> corp = corp_list.find_by_stock_code('005930')
            >>> filings = corp.search_filings(bgn_de='20230101', pblntf_detail_ty='A001')
        """
        if not self._initialized:
            raise RuntimeError(
                "CorpListService not initialized. Call initialize() first."
            )
        
        if self._corp_list is None:
            raise RuntimeError(
                "CorpList object not available. This happens when loading from CSV. "
                "Call initialize() to load from API and get Corp objects."
            )
        
        return self._corp_list

