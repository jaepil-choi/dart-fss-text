"""
Unit tests for ReportMetadata model.

Tests the composition component that extracts and stores shared report-level
metadata from SectionDocument objects.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from dart_fss_text.models import ReportMetadata, SectionDocument


# === Fixtures ===

@pytest.fixture
def sample_section_document():
    """Create a sample SectionDocument for testing."""
    return SectionDocument(
        document_id="20240312000736_020100",
        rcept_no="20240312000736",
        rcept_dt="20240312",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A001",
        report_name="사업보고서",
        section_code="020100",
        section_title="1. 사업의 개요",
        level=2,
        atocid="10",
        parent_section_code="020000",
        parent_section_title="II. 사업의 내용",
        section_path=["020000", "020100"],
        text="당사는 본사를 거점으로...",
        char_count=2500,
        word_count=450,
        parsed_at=datetime.now(),
        parser_version="1.0.0"
    )


@pytest.fixture
def sample_metadata():
    """Create a sample ReportMetadata directly."""
    return ReportMetadata(
        rcept_no="20240312000736",
        rcept_dt="20240312",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A001",
        report_name="사업보고서"
    )


# === Creation Tests ===

def test_create_metadata_from_section_document(sample_section_document):
    """Test extracting metadata from SectionDocument."""
    metadata = ReportMetadata.from_section_document(sample_section_document)
    
    assert metadata.rcept_no == "20240312000736"
    assert metadata.rcept_dt == "20240312"
    assert metadata.year == "2024"
    assert metadata.corp_code == "00126380"
    assert metadata.corp_name == "삼성전자"
    assert metadata.stock_code == "005930"
    assert metadata.report_type == "A001"
    assert metadata.report_name == "사업보고서"


def test_create_metadata_directly():
    """Test creating ReportMetadata directly."""
    metadata = ReportMetadata(
        rcept_no="20240312000736",
        rcept_dt="20240312",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A001",
        report_name="사업보고서"
    )
    
    assert metadata.rcept_no == "20240312000736"
    assert metadata.corp_name == "삼성전자"


# === Validation Tests ===

def test_validate_rcept_no_length():
    """Test rcept_no must be exactly 14 characters."""
    # Too short
    with pytest.raises(ValidationError) as exc_info:
        ReportMetadata(
            rcept_no="2024031200073",  # 13 chars
            rcept_dt="20240312",
            year="2024",
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            report_type="A001",
            report_name="사업보고서"
        )
    assert "rcept_no" in str(exc_info.value)
    
    # Too long
    with pytest.raises(ValidationError) as exc_info:
        ReportMetadata(
            rcept_no="202403120007361",  # 15 chars
            rcept_dt="20240312",
            year="2024",
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            report_type="A001",
            report_name="사업보고서"
        )
    assert "rcept_no" in str(exc_info.value)


def test_validate_rcept_dt_pattern():
    """Test rcept_dt must be 8 digits (YYYYMMDD)."""
    with pytest.raises(ValidationError) as exc_info:
        ReportMetadata(
            rcept_no="20240312000736",
            rcept_dt="2024-03-12",  # Wrong format
            year="2024",
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            report_type="A001",
            report_name="사업보고서"
        )
    assert "rcept_dt" in str(exc_info.value)


def test_validate_year_pattern():
    """Test year must be 4 digits (YYYY)."""
    with pytest.raises(ValidationError) as exc_info:
        ReportMetadata(
            rcept_no="20240312000736",
            rcept_dt="20240312",
            year="24",  # Too short
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            report_type="A001",
            report_name="사업보고서"
        )
    assert "year" in str(exc_info.value)


def test_validate_corp_code_length():
    """Test corp_code must be exactly 8 characters."""
    with pytest.raises(ValidationError) as exc_info:
        ReportMetadata(
            rcept_no="20240312000736",
            rcept_dt="20240312",
            year="2024",
            corp_code="0012638",  # 7 chars
            corp_name="삼성전자",
            stock_code="005930",
            report_type="A001",
            report_name="사업보고서"
        )
    assert "corp_code" in str(exc_info.value)


def test_validate_stock_code_pattern():
    """Test stock_code must be exactly 6 digits."""
    with pytest.raises(ValidationError) as exc_info:
        ReportMetadata(
            rcept_no="20240312000736",
            rcept_dt="20240312",
            year="2024",
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="5930",  # Too short
            report_type="A001",
            report_name="사업보고서"
        )
    assert "stock_code" in str(exc_info.value)


# === Immutability Tests ===

def test_metadata_is_frozen(sample_metadata):
    """Test that ReportMetadata is immutable (frozen)."""
    with pytest.raises(ValidationError) as exc_info:
        sample_metadata.year = "2025"
    
    # Pydantic v2 raises ValidationError for frozen models
    assert "frozen" in str(exc_info.value).lower() or "immutable" in str(exc_info.value).lower()


def test_metadata_cannot_add_attributes(sample_metadata):
    """Test that new attributes cannot be added to frozen model."""
    with pytest.raises((ValidationError, AttributeError)):
        sample_metadata.new_field = "value"


# === Equality Tests ===

def test_metadata_equality():
    """Test two ReportMetadata with same values are equal."""
    metadata1 = ReportMetadata(
        rcept_no="20240312000736",
        rcept_dt="20240312",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A001",
        report_name="사업보고서"
    )
    
    metadata2 = ReportMetadata(
        rcept_no="20240312000736",
        rcept_dt="20240312",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A001",
        report_name="사업보고서"
    )
    
    assert metadata1 == metadata2


def test_metadata_inequality_different_rcept_no():
    """Test ReportMetadata with different rcept_no are not equal."""
    metadata1 = ReportMetadata(
        rcept_no="20240312000736",
        rcept_dt="20240312",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A001",
        report_name="사업보고서"
    )
    
    metadata2 = ReportMetadata(
        rcept_no="20240312000737",  # Different
        rcept_dt="20240312",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A001",
        report_name="사업보고서"
    )
    
    assert metadata1 != metadata2


def test_metadata_inequality_different_stock_code():
    """Test ReportMetadata with different stock_code are not equal."""
    metadata1 = ReportMetadata(
        rcept_no="20240312000736",
        rcept_dt="20240312",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A001",
        report_name="사업보고서"
    )
    
    metadata2 = ReportMetadata(
        rcept_no="20240312000736",
        rcept_dt="20240312",
        year="2024",
        corp_code="00660380",  # Different corp
        corp_name="SK하이닉스",
        stock_code="000660",  # Different
        report_type="A001",
        report_name="사업보고서"
    )
    
    assert metadata1 != metadata2


# === String Representation Tests ===

def test_repr(sample_metadata):
    """Test __repr__ includes key information."""
    repr_str = repr(sample_metadata)
    
    assert "ReportMetadata" in repr_str
    assert "삼성전자" in repr_str
    assert "005930" in repr_str
    assert "2024" in repr_str
    assert "A001" in repr_str


def test_str(sample_metadata):
    """Test __str__ is human-readable."""
    str_repr = str(sample_metadata)
    
    assert "삼성전자" in str_repr
    assert "005930" in str_repr
    assert "2024" in str_repr
    assert "사업보고서" in str_repr


# === Serialization Tests ===

def test_model_dump(sample_metadata):
    """Test converting to dictionary."""
    data = sample_metadata.model_dump()
    
    assert isinstance(data, dict)
    assert data["rcept_no"] == "20240312000736"
    assert data["corp_name"] == "삼성전자"
    assert data["stock_code"] == "005930"
    assert data["year"] == "2024"


def test_model_dump_json(sample_metadata):
    """Test JSON serialization."""
    json_str = sample_metadata.model_dump_json()
    
    assert isinstance(json_str, str)
    assert "20240312000736" in json_str
    assert "삼성전자" in json_str
    assert "005930" in json_str


# === Edge Cases ===

def test_metadata_with_different_report_types():
    """Test metadata for different report types (A002, A003)."""
    # Semi-annual report
    metadata_a002 = ReportMetadata(
        rcept_no="20240814003284",
        rcept_dt="20240814",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A002",
        report_name="반기보고서"
    )
    assert metadata_a002.report_type == "A002"
    assert metadata_a002.report_name == "반기보고서"
    
    # Quarterly report
    metadata_a003 = ReportMetadata(
        rcept_no="20241114002642",
        rcept_dt="20241114",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A003",
        report_name="분기보고서"
    )
    assert metadata_a003.report_type == "A003"
    assert metadata_a003.report_name == "분기보고서"


def test_metadata_extraction_preserves_all_fields(sample_section_document):
    """Test that from_section_document extracts all required fields."""
    metadata = ReportMetadata.from_section_document(sample_section_document)
    
    # Verify all 8 fields are extracted
    assert hasattr(metadata, 'rcept_no')
    assert hasattr(metadata, 'rcept_dt')
    assert hasattr(metadata, 'year')
    assert hasattr(metadata, 'corp_code')
    assert hasattr(metadata, 'corp_name')
    assert hasattr(metadata, 'stock_code')
    assert hasattr(metadata, 'report_type')
    assert hasattr(metadata, 'report_name')

