"""
Discovery helper classes for exploring DART specifications.

Provides user-facing APIs to discover available report types, corporation
classifications, and remark codes from config/types.yaml.
"""

from typing import Dict
from dart_fss_text.config import get_config


class ReportTypes:
    """
    Helper class for discovering available DART report types.
    
    All methods use the centralized configuration from types.yaml
    and return immutable views (copies) to prevent accidental mutations.
    
    Example:
        >>> # List all available report types
        >>> ReportTypes.list_available()
        {'A001': '사업보고서', 'A002': '반기보고서', ...}
        
        >>> # Get periodic reports only
        >>> ReportTypes.list_periodic()
        {'A001': '사업보고서', 'A002': '반기보고서', 'A003': '분기보고서'}
        
        >>> # Check if a code is valid
        >>> ReportTypes.is_valid('A001')
        True
    """
    
    @staticmethod
    def list_available() -> Dict[str, str]:
        """
        List all available report type codes with Korean descriptions.
        
        Returns:
            Dictionary mapping report type codes to Korean descriptions
        
        Example:
            >>> types = ReportTypes.list_available()
            >>> len(types)
            60+
            >>> types['A001']
            '사업보고서'
        """
        return get_config().pblntf_detail_ty.copy()
    
    @staticmethod
    def list_by_category(prefix: str) -> Dict[str, str]:
        """
        List report types filtered by category prefix.
        
        Args:
            prefix: Category prefix (e.g., 'A' for periodic, 'B' for material events)
        
        Returns:
            Dictionary of report types matching the prefix
        
        Example:
            >>> # Get all periodic reports (A category)
            >>> ReportTypes.list_by_category('A')
            {'A001': '사업보고서', 'A002': '반기보고서', ...}
        """
        all_types = get_config().pblntf_detail_ty
        return {k: v for k, v in all_types.items() if k.startswith(prefix)}
    
    @staticmethod
    def get_description(code: str) -> str:
        """
        Get Korean description for a report type code.
        
        Args:
            code: Report type code (e.g., 'A001')
        
        Returns:
            Korean description string
        
        Raises:
            ValueError: If code is not found
        
        Example:
            >>> ReportTypes.get_description('A001')
            '사업보고서'
        """
        try:
            return get_config().get_report_description(code)
        except KeyError as e:
            raise ValueError(f"Unknown report type: {code}") from e
    
    @staticmethod
    def is_valid(code: str) -> bool:
        """
        Check if a report type code is valid.
        
        Args:
            code: Report type code to validate
        
        Returns:
            True if code exists, False otherwise
        
        Example:
            >>> ReportTypes.is_valid('A001')
            True
            >>> ReportTypes.is_valid('Z999')
            False
        """
        return get_config().is_valid_report_type(code)
    
    @staticmethod
    def list_periodic() -> Dict[str, str]:
        """
        List only periodic reports (annual, semi-annual, quarterly).
        
        Returns:
            Dictionary with A001, A002, A003 report types
        
        Example:
            >>> periodic = ReportTypes.list_periodic()
            >>> len(periodic)
            3
            >>> periodic['A001']
            '사업보고서'
        """
        all_types = get_config().pblntf_detail_ty
        periodic_codes = ['A001', 'A002', 'A003']
        return {k: all_types[k] for k in periodic_codes if k in all_types}


class CorpClass:
    """
    Helper class for discovering corporation classification codes.
    
    Corporation classes represent market segments:
    - Y: KOSPI (유가증권)
    - K: KOSDAQ (코스닥)
    - N: KONEX (코넥스)
    - E: Others (기타)
    
    Example:
        >>> CorpClass.list_available()
        {'Y': '유가증권', 'K': '코스닥', 'N': '코넥스', 'E': '기타'}
        
        >>> CorpClass.get_description('Y')
        '유가증권'
    """
    
    @staticmethod
    def list_available() -> Dict[str, str]:
        """
        List all corporation classification codes.
        
        Returns:
            Dictionary mapping codes to Korean descriptions
        
        Example:
            >>> classes = CorpClass.list_available()
            >>> classes['Y']
            '유가증권'
        """
        return get_config().corp_cls.copy()
    
    @staticmethod
    def get_description(code: str) -> str:
        """
        Get Korean description for a corporation class code.
        
        Args:
            code: Corporation class code (Y, K, N, or E)
        
        Returns:
            Korean description
        
        Raises:
            ValueError: If code is not found
        
        Example:
            >>> CorpClass.get_description('Y')
            '유가증권'
        """
        config = get_config()
        if code not in config.corp_cls:
            raise ValueError(f"Unknown corporation class: {code}")
        return config.corp_cls[code]
    
    @staticmethod
    def is_valid(code: str) -> bool:
        """
        Check if a corporation class code is valid.
        
        Args:
            code: Corporation class code to validate
        
        Returns:
            True if code exists, False otherwise
        
        Example:
            >>> CorpClass.is_valid('Y')
            True
            >>> CorpClass.is_valid('Z')
            False
        """
        return code in get_config().corp_cls


class RemarkCodes:
    """
    Helper class for discovering remark codes.
    
    Remark codes provide additional context about filings:
    - 연: Consolidated report
    - 정: Amended report
    - 철: Withdrawn report
    etc.
    
    Example:
        >>> RemarkCodes.list_available()
        {'연': '본 보고서는 연결...', '정': '정정신고가...', ...}
        
        >>> RemarkCodes.get_description('연')
        '본 보고서는 연결부분을 포함한 것임'
    """
    
    @staticmethod
    def list_available() -> Dict[str, str]:
        """
        List all remark codes with explanations.
        
        Returns:
            Dictionary mapping codes to Korean explanations
        
        Example:
            >>> remarks = RemarkCodes.list_available()
            >>> '연' in remarks
            True
        """
        return get_config().rm.copy()
    
    @staticmethod
    def get_description(code: str) -> str:
        """
        Get explanation for a remark code.
        
        Args:
            code: Remark code
        
        Returns:
            Korean explanation
        
        Raises:
            ValueError: If code is not found
        
        Example:
            >>> RemarkCodes.get_description('연')
            '본 보고서는 연결부분을 포함한 것임'
        """
        config = get_config()
        if code not in config.rm:
            raise ValueError(f"Unknown remark code: {code}")
        return config.rm[code]
    
    @staticmethod
    def is_valid(code: str) -> bool:
        """
        Check if a remark code is valid.
        
        Args:
            code: Remark code to validate
        
        Returns:
            True if code exists, False otherwise
        
        Example:
            >>> RemarkCodes.is_valid('연')
            True
            >>> RemarkCodes.is_valid('INVALID')
            False
        """
        return code in get_config().rm

