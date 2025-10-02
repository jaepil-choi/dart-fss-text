"""
Reusable field validators for Pydantic models.

These validators work with config/types.yaml specifications and can be
used with Pydantic @field_validator decorator for automatic input validation.
"""

from typing import List, Optional
from dart_fss_text.config import get_config


def validate_report_types(codes: List[str]) -> List[str]:
    """
    Validate report type codes against config/types.yaml specification.
    
    This validator is designed to be used with Pydantic @field_validator
    decorator for automatic validation of report_types fields.
    
    Args:
        codes: List of report type codes to validate (e.g., ['A001', 'A002'])
    
    Returns:
        The validated list of codes (unchanged if all valid)
    
    Raises:
        ValueError: If any code is not found in config.pblntf_detail_ty,
                   with detailed error message listing invalid codes
    
    Example:
        >>> from pydantic import BaseModel, field_validator
        >>> class Request(BaseModel):
        ...     report_types: List[str]
        ...     _validate = field_validator('report_types')(validate_report_types)
        >>> Request(report_types=['A001', 'A002'])  # Valid
        >>> Request(report_types=['Z999'])  # Raises ValidationError
    """
    # Empty list is valid (no codes to validate)
    if not codes:
        return codes
    
    config = get_config()
    
    # Find all invalid codes
    invalid = [c for c in codes if not config.is_valid_report_type(c)]
    
    if invalid:
        # Get sample of valid codes for help message
        # Exclude codes already submitted by user to avoid confusion
        all_valid_codes = list(config.pblntf_detail_ty.keys())
        sample_codes = [c for c in all_valid_codes if c not in codes][:10]
        
        raise ValueError(
            f"Invalid report type codes: {invalid}\n"
            f"Valid codes include: {sample_codes}...\n"
            f"Use ReportTypes.list_available() to see all options."
        )
    
    return codes


def validate_stock_code(code: str) -> str:
    """
    Validate Korean stock code format (6 digits).
    
    Korean stock codes are always 6-digit numeric strings with leading
    zeros preserved (e.g., '005930' for Samsung Electronics).
    
    Args:
        code: Stock code to validate
    
    Returns:
        The validated stock code (unchanged if valid)
    
    Raises:
        ValueError: If code is not exactly 6 digits, with helpful error message
    
    Example:
        >>> validate_stock_code('005930')  # Samsung Electronics
        '005930'
        >>> validate_stock_code('000660')  # SK Hynix
        '000660'
        >>> validate_stock_code('ABC123')  # Raises ValueError
    """
    if not code or not code.isdigit() or len(code) != 6:
        raise ValueError(
            f"Stock code must be 6 digits, got: '{code}'\n"
            f"Example: '005930' (Samsung Electronics)"
        )
    
    return code


def validate_date_yyyymmdd(date: str) -> str:
    """
    Validate date string in YYYYMMDD format.
    
    Validates that the date is an 8-character numeric string in YYYYMMDD format
    with year in valid range (1980-2100).
    
    Args:
        date: Date string to validate (e.g., '20240101')
    
    Returns:
        The validated date string (unchanged if valid)
    
    Raises:
        ValueError: If date is not in YYYYMMDD format or year is out of range
    
    Example:
        >>> validate_date_yyyymmdd('20240101')
        '20240101'
        >>> validate_date_yyyymmdd('2024-01-01')  # Raises ValueError (dashes)
        >>> validate_date_yyyymmdd('19790101')    # Raises ValueError (too old)
    """
    # Check format: must be 8 digits
    if not date or not date.isdigit() or len(date) != 8:
        raise ValueError(
            f"Date must be YYYYMMDD format, got: '{date}'\n"
            f"Example: '20240101'"
        )
    
    # Validate year range (1980-2100)
    year = int(date[:4])
    if year < 1980 or year > 2100:
        raise ValueError(
            f"Year {year} is out of valid range (1980-2100)"
        )
    
    return date

