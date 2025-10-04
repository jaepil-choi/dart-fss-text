"""
Report metadata model for shared metadata composition.

This module defines ReportMetadata, a Pydantic model that extracts and stores
shared report-level metadata from SectionDocument objects.

Design Pattern: Composition over Inheritance
- Used by Sequence to provide shared metadata access
- Immutable (frozen) to ensure consistency across all sections
- Validated by Pydantic on creation
"""

from pydantic import BaseModel, Field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .section import SectionDocument


class ReportMetadata(BaseModel):
    """
    Shared report-level metadata extracted from SectionDocument.
    
    This model contains metadata that is common to all sections within a single
    filing/report. It is used as a composition component in the Sequence class
    to avoid inheritance issues.
    
    Design Rationale:
    - Composition: Sequence "has-a" ReportMetadata (not "is-a")
    - Immutable: Frozen to prevent accidental modification
    - Validated: Pydantic ensures all fields meet constraints
    - Reusable: Can be shared across multiple Sequence objects
    
    Attributes:
        rcept_no: DART receipt number (14 digits)
        rcept_dt: Receipt date in YYYYMMDD format
        year: Year extracted from rcept_dt (YYYY)
        corp_code: DART corporation code (8 digits)
        corp_name: Company name in Korean
        stock_code: Stock code (6 digits)
        report_type: Report type code (e.g., A001)
        report_name: Report type name in Korean
    
    Example:
        >>> from dart_fss_text.models import SectionDocument, ReportMetadata
        >>> section = SectionDocument(...)  # Load from MongoDB
        >>> metadata = ReportMetadata.from_section_document(section)
        >>> print(f"{metadata.corp_name} ({metadata.stock_code})")
        '삼성전자 (005930)'
    """
    
    # === Receipt Information ===
    rcept_no: str = Field(
        ...,
        min_length=14,
        max_length=14,
        description="DART receipt number",
        examples=["20240312000736"]
    )
    
    rcept_dt: str = Field(
        ...,
        pattern=r'^\d{8}$',
        description="Receipt date (publication date) in YYYYMMDD format",
        examples=["20240312"]
    )
    
    year: str = Field(
        ...,
        pattern=r'^\d{4}$',
        description="Year extracted from rcept_dt",
        examples=["2024"]
    )
    
    # === Company Information ===
    corp_code: str = Field(
        ...,
        min_length=8,
        max_length=8,
        description="DART corporation code (8 digits)",
        examples=["00126380"]
    )
    
    corp_name: str = Field(
        ...,
        description="Korean company name",
        examples=["삼성전자"]
    )
    
    stock_code: str = Field(
        ...,
        pattern=r'^\d{6}$',
        description="Korean stock code (6 digits)",
        examples=["005930"]
    )
    
    # === Report Type ===
    report_type: str = Field(
        ...,
        description="Report type code",
        examples=["A001"]
    )
    
    report_name: str = Field(
        ...,
        description="Report type name in Korean",
        examples=["사업보고서"]
    )
    
    model_config = {
        "frozen": True,  # Immutable to ensure consistency
        "json_schema_extra": {
            "examples": [
                {
                    "rcept_no": "20240312000736",
                    "rcept_dt": "20240312",
                    "year": "2024",
                    "corp_code": "00126380",
                    "corp_name": "삼성전자",
                    "stock_code": "005930",
                    "report_type": "A001",
                    "report_name": "사업보고서"
                }
            ]
        }
    }
    
    @classmethod
    def from_section_document(cls, doc: 'SectionDocument') -> 'ReportMetadata':
        """
        Extract metadata from SectionDocument.
        
        Args:
            doc: SectionDocument instance (typically from MongoDB)
        
        Returns:
            ReportMetadata instance with extracted fields
        
        Example:
            >>> section = SectionDocument(...)
            >>> metadata = ReportMetadata.from_section_document(section)
            >>> print(metadata.stock_code)
            '005930'
        """
        return cls(
            rcept_no=doc.rcept_no,
            rcept_dt=doc.rcept_dt,
            year=doc.year,
            corp_code=doc.corp_code,
            corp_name=doc.corp_name,
            stock_code=doc.stock_code,
            report_type=doc.report_type,
            report_name=doc.report_name,
        )
    
    def __repr__(self) -> str:
        return (
            f"ReportMetadata(corp='{self.corp_name}', "
            f"stock='{self.stock_code}', "
            f"year={self.year}, "
            f"type='{self.report_type}')"
        )
    
    def __str__(self) -> str:
        return f"{self.corp_name} ({self.stock_code}) - {self.year} {self.report_name}"

