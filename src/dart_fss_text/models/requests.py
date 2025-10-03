"""
Request models for API and service layer operations.

These Pydantic models provide type-safe, validated interfaces for
filing search and other operations.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator, ConfigDict

from dart_fss_text.validators import (
    validate_stock_code,
    validate_date_yyyymmdd,
    validate_report_types
)


class SearchFilingsRequest(BaseModel):
    """
    Request model for searching DART filings.
    
    This model validates all inputs using validators from dart_fss_text.validators
    and provides a type-safe interface for filing search operations.
    
    Attributes:
        stock_codes: List of 6-digit Korean stock codes (e.g., ['005930', '000660'])
        start_date: Start date in YYYYMMDD format (e.g., '20240101')
        end_date: End date in YYYYMMDD format (e.g., '20241231')
        report_types: List of report type codes (e.g., ['A001', 'A002'])
    
    Example:
        >>> request = SearchFilingsRequest(
        ...     stock_codes=['005930'],
        ...     start_date='20240101',
        ...     end_date='20241231',
        ...     report_types=['A001', 'A002']
        ... )
        >>> request.stock_codes
        ['005930']
    
    Raises:
        ValidationError: If any field fails validation
    """
    
    stock_codes: List[str] = Field(
        ...,
        min_length=1,
        description="List of 6-digit Korean stock codes with leading zeros preserved",
        examples=[["005930", "000660"]]
    )
    
    start_date: str = Field(
        ...,
        description="Start date in YYYYMMDD format for filing search range",
        examples=["20240101"]
    )
    
    end_date: str = Field(
        ...,
        description="End date in YYYYMMDD format for filing search range",
        examples=["20241231"]
    )
    
    report_types: List[str] = Field(
        ...,
        min_length=1,
        description="List of report type codes to search (at least one required)",
        examples=[["A001", "A002", "A003"]]
    )
    
    # Apply validators using field_validator decorator
    @field_validator('stock_codes')
    @classmethod
    def validate_stock_codes_list(cls, v: List[str]) -> List[str]:
        """Validate each stock code in the list."""
        return [validate_stock_code(code) for code in v]
    
    _validate_start_date = field_validator('start_date')(validate_date_yyyymmdd)
    _validate_end_date = field_validator('end_date')(validate_date_yyyymmdd)
    _validate_report_types = field_validator('report_types')(validate_report_types)
    
    # Model configuration
    model_config = ConfigDict(
        frozen=True,  # Make model immutable
        json_schema_extra={
            "examples": [{
                "stock_codes": ["005930"],
                "start_date": "20240101",
                "end_date": "20241231",
                "report_types": ["A001", "A002"]
            }]
        }
    )

