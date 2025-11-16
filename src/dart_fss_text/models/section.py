"""
Pydantic models for DART report sections (MongoDB documents).

Schema Design:
- One document per section (flat structure, not nested)
- Shared metadata across all sections of a report
- Text-only content (paragraphs + tables flattened to text)
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List


class SectionDocument(BaseModel):
    """
    MongoDB document schema for DART report sections.
    
    Each section is stored as a separate document with:
    - Document metadata (rcept_no, dates, company info)
    - Section identity (code, title, level)
    - Hierarchy info (parent, path)
    - Text content (paragraphs + tables as text)
    - Statistics and parsing metadata
    
    Example:
        >>> section = SectionDocument(
        ...     document_id="20240312000736_020100",
        ...     rcept_no="20240312000736",
        ...     rcept_dt="20240312",
        ...     year="2024",
        ...     corp_code="00126380",
        ...     corp_name="삼성전자",
        ...     stock_code="005930",
        ...     report_type="A001",
        ...     report_name="사업보고서",
        ...     section_code="020100",
        ...     section_title="1. 사업의 개요",
        ...     level=2,
        ...     section_path=["020000", "020100"],
        ...     text="당사는 본사를 거점으로...",
        ...     char_count=2500,
        ...     word_count=450,
        ...     parsed_at=datetime.now(),
        ...     parser_version="1.0.0"
        ... )
    """
    
    # === Composite Key ===
    document_id: str = Field(
        ...,
        description="Unique identifier: {rcept_no}_{section_code}",
        examples=["20240312000736_020100"]
    )
    
    # === Document Metadata (Shared) ===
    rcept_no: str = Field(
        ...,
        min_length=14,
        max_length=14,
        description="Receipt number from DART",
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
        description="Year extracted from rcept_dt for time-based queries",
        examples=["2024"]
    )
    
    # === Company Information (Shared) ===
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
    
    # === Report Type (Shared) ===
    report_type: str = Field(
        ...,
        description="Report type code (e.g., A001, A002, A003)",
        examples=["A001"]
    )
    
    report_name: str = Field(
        ...,
        description="Report type name in Korean",
        examples=["사업보고서"]
    )
    
    # === Section Identity ===
    section_code: str = Field(
        ...,
        description="Section code from toc.yaml (e.g., 020100)",
        examples=["020100"]
    )
    
    section_title: str = Field(
        ...,
        description="Section title in Korean",
        examples=["1. 사업의 개요"]
    )
    
    level: int = Field(
        ...,
        ge=1,
        le=4,
        description="Section level (1=root, 2=subsection, etc.)",
        examples=[2]
    )
    
    # === Hierarchy ===
    section_path: List[str] = Field(
        default_factory=list,
        description="Hierarchical path from root to this section (ordered list of section_codes)",
        examples=[["020000", "020100"]]
    )
    
    # === Content ===
    text: str = Field(
        ...,
        description="Section text content (paragraphs + tables flattened to text)"
    )

    # === Basic Statistics ===
    char_count: int = Field(
        ...,
        ge=0,
        description="Total character count (before truncation if applied)"
    )
    
    word_count: int = Field(
        ...,
        ge=0,
        description="Total word count"
    )
    
    # === Parsing Metadata ===
    parsed_at: datetime = Field(
        ...,
        description="Timestamp when this document was parsed"
    )
    
    parser_version: str = Field(
        ...,
        description="Version of parser used",
        examples=["1.0.0"]
    )
    
    @field_validator('text')
    @classmethod
    def truncate_text_if_too_large(cls, v: str) -> str:
        """
        Truncate text if it exceeds safe MongoDB document size.

        MongoDB has a 16MB BSON document limit. To stay well under this limit,
        we truncate individual text fields to 50,000 characters (~150KB UTF-8).
        This prevents "BSON document too large" errors.

        Most sections are under 10KB. Sections exceeding 50K chars are likely
        malformed (e.g., tables with embedded binary data or XML parsing errors).
        """
        MAX_TEXT_LENGTH = 50_000

        if len(v) > MAX_TEXT_LENGTH:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Text field truncated from {len(v):,} to {MAX_TEXT_LENGTH:,} chars "
                f"to prevent MongoDB BSON size limit error"
            )
            return v[:MAX_TEXT_LENGTH] + "\n\n[... TRUNCATED - Original length: {:,} chars]".format(len(v))

        return v

    @field_validator('document_id')
    @classmethod
    def validate_document_id_format(cls, v: str) -> str:
        """Validate document_id follows {rcept_no}_{section_code} format."""
        parts = v.split('_')
        if len(parts) != 2:
            raise ValueError(
                f"document_id must be in format '{{rcept_no}}_{{section_code}}', "
                f"got: '{v}'"
            )

        rcept_no, section_code = parts
        if len(rcept_no) != 14 or not rcept_no.isdigit():
            raise ValueError(
                f"rcept_no part must be 14 digits, got: '{rcept_no}'"
            )

        return v
    
    @field_validator('section_path')
    @classmethod
    def validate_section_path_contains_current(cls, v: List[str], info) -> List[str]:
        """Validate section_path ends with current section_code."""
        # Note: info.data is available in Pydantic v2
        # This validator runs after section_code is set
        if v and 'section_code' in info.data:
            section_code = info.data['section_code']
            if v[-1] != section_code:
                raise ValueError(
                    f"section_path must end with section_code '{section_code}', "
                    f"got path: {v}"
                )
        return v
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "document_id": "20240312000736_020100",
                    "rcept_no": "20240312000736",
                    "rcept_dt": "20240312",
                    "year": "2024",
                    "corp_code": "00126380",
                    "corp_name": "삼성전자",
                    "stock_code": "005930",
                    "report_type": "A001",
                    "report_name": "사업보고서",
                    "section_code": "020100",
                    "section_title": "1. 사업의 개요",
                    "level": 2,
                    "section_path": ["020000", "020100"],
                    "text": "당사는 본사를 거점으로 한국과 DX 부문 산하 해외 9개 지역총괄...",
                    "char_count": 2500,
                    "word_count": 450,
                    "parsed_at": "2025-10-03T12:34:56Z",
                    "parser_version": "1.0.0"
                }
            ]
        }
    }
    
    def to_mongo_dict(self) -> dict:
        """
        Convert to dictionary suitable for MongoDB insertion.
        
        Returns:
            Dictionary with datetime converted to MongoDB format
        """
        data = self.model_dump()
        # MongoDB handles datetime objects directly
        return data
    
    def __repr__(self) -> str:
        """
        Custom repr that truncates text field to prevent terminal explosion.
        
        Shows first 200 chars of text with ellipsis if longer.
        """
        text_preview = self.text[:200] + "..." if len(self.text) > 200 else self.text
        return (
            f"SectionDocument("
            f"document_id='{self.document_id}', "
            f"corp_name='{self.corp_name}', "
            f"section_code='{self.section_code}', "
            f"section_title='{self.section_title}', "
            f"text='{text_preview}', "
            f"char_count={self.char_count})"
        )


def create_document_id(rcept_no: str, section_code: str) -> str:
    """
    Create composite document ID.
    
    Args:
        rcept_no: Receipt number (14 digits)
        section_code: Section code (e.g., '020100')
    
    Returns:
        Composite ID in format: {rcept_no}_{section_code}
    
    Example:
        >>> create_document_id("20240312000736", "020100")
        '20240312000736_020100'
    """
    return f"{rcept_no}_{section_code}"

