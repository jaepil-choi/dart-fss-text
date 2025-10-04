"""
Unit tests for Sequence collection class.

Tests the user-facing collection that groups SectionDocument objects
and provides convenient access patterns.
"""

import pytest
from datetime import datetime

from dart_fss_text.models import Sequence, SectionDocument, ReportMetadata


# === Fixtures ===

@pytest.fixture
def sample_sections():
    """Create a list of sample SectionDocument objects."""
    base_time = datetime(2024, 3, 12, 10, 30, 0)
    
    return [
        SectionDocument(
            document_id="20240312000736_020000",
            rcept_no="20240312000736",
            rcept_dt="20240312",
            year="2024",
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            report_type="A001",
            report_name="사업보고서",
            section_code="020000",
            section_title="II. 사업의 내용",
            level=1,
            atocid="9",
            parent_section_code=None,
            parent_section_title=None,
            section_path=["020000"],
            text="사업의 내용 전체 텍스트...",
            char_count=1000,
            word_count=150,
            parsed_at=base_time,
            parser_version="1.0.0"
        ),
        SectionDocument(
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
            parsed_at=base_time,
            parser_version="1.0.0"
        ),
        SectionDocument(
            document_id="20240312000736_020200",
            rcept_no="20240312000736",
            rcept_dt="20240312",
            year="2024",
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            report_type="A001",
            report_name="사업보고서",
            section_code="020200",
            section_title="2. 주요 제품 및 서비스",
            level=2,
            atocid="11",
            parent_section_code="020000",
            parent_section_title="II. 사업의 내용",
            section_path=["020000", "020200"],
            text="주요 제품은 반도체...",
            char_count=3000,
            word_count=500,
            parsed_at=base_time,
            parser_version="1.0.0"
        ),
    ]


@pytest.fixture
def sample_sequence(sample_sections):
    """Create a sample Sequence."""
    return Sequence(sample_sections)


@pytest.fixture
def mismatched_sections(sample_sections):
    """Create sections with mismatched metadata."""
    # First two sections are from Samsung
    sections = sample_sections[:2]
    
    # Add a section from a different company
    sections.append(
        SectionDocument(
            document_id="20240312000737_020000",
            rcept_no="20240312000737",  # Different rcept_no
            rcept_dt="20240312",
            year="2024",
            corp_code="00660380",
            corp_name="SK하이닉스",  # Different company
            stock_code="000660",  # Different stock code
            report_type="A001",
            report_name="사업보고서",
            section_code="020000",
            section_title="II. 사업의 내용",
            level=1,
            atocid="9",
            parent_section_code=None,
            parent_section_title=None,
            section_path=["020000"],
            text="SK하이닉스 사업 내용...",
            char_count=1200,
            word_count=180,
            parsed_at=datetime(2024, 3, 12, 10, 30, 0),
            parser_version="1.0.0"
        )
    )
    
    return sections


# === Initialization Tests ===

def test_create_sequence_with_valid_sections(sample_sections):
    """Test creating Sequence with valid sections."""
    seq = Sequence(sample_sections)
    
    assert len(seq) == 3
    assert seq.section_count == 3


def test_create_sequence_empty_list_raises_error():
    """Test that creating Sequence with empty list raises ValueError."""
    with pytest.raises(ValueError, match="must contain at least one section"):
        Sequence([])


def test_create_sequence_mismatched_metadata_raises_error(mismatched_sections):
    """Test that sections with different metadata raise ValueError."""
    with pytest.raises(ValueError, match="must share same report metadata"):
        Sequence(mismatched_sections)


def test_sequence_extracts_metadata(sample_sequence):
    """Test that Sequence extracts ReportMetadata correctly."""
    assert isinstance(sample_sequence.metadata, ReportMetadata)
    assert sample_sequence.metadata.rcept_no == "20240312000736"
    assert sample_sequence.metadata.stock_code == "005930"


# === Metadata Delegation Tests ===

def test_metadata_delegation_rcept_no(sample_sequence):
    """Test rcept_no property is delegated to metadata."""
    assert sample_sequence.rcept_no == "20240312000736"
    assert sample_sequence.rcept_no == sample_sequence.metadata.rcept_no


def test_metadata_delegation_year(sample_sequence):
    """Test year property is delegated to metadata."""
    assert sample_sequence.year == "2024"
    assert sample_sequence.year == sample_sequence.metadata.year


def test_metadata_delegation_corp_name(sample_sequence):
    """Test corp_name property is delegated to metadata."""
    assert sample_sequence.corp_name == "삼성전자"
    assert sample_sequence.corp_name == sample_sequence.metadata.corp_name


def test_metadata_delegation_stock_code(sample_sequence):
    """Test stock_code property is delegated to metadata."""
    assert sample_sequence.stock_code == "005930"
    assert sample_sequence.stock_code == sample_sequence.metadata.stock_code


def test_metadata_delegation_report_type(sample_sequence):
    """Test report_type property is delegated to metadata."""
    assert sample_sequence.report_type == "A001"
    assert sample_sequence.report_type == sample_sequence.metadata.report_type


# === Indexing Tests ===

def test_index_by_int_positive(sample_sequence):
    """Test indexing by positive integer."""
    first = sample_sequence[0]
    assert first.section_code == "020000"
    
    second = sample_sequence[1]
    assert second.section_code == "020100"
    
    third = sample_sequence[2]
    assert third.section_code == "020200"


def test_index_by_int_negative(sample_sequence):
    """Test indexing by negative integer."""
    last = sample_sequence[-1]
    assert last.section_code == "020200"
    
    second_last = sample_sequence[-2]
    assert second_last.section_code == "020100"


def test_index_by_int_out_of_range(sample_sequence):
    """Test indexing with out-of-range integer raises IndexError."""
    with pytest.raises(IndexError):
        _ = sample_sequence[10]


def test_index_by_section_code(sample_sequence):
    """Test indexing by section_code string."""
    section = sample_sequence["020100"]
    assert section.section_code == "020100"
    assert section.section_title == "1. 사업의 개요"


def test_index_by_nonexistent_section_code(sample_sequence):
    """Test indexing by non-existent section_code raises KeyError."""
    with pytest.raises(KeyError, match="No section with code '999999'"):
        _ = sample_sequence["999999"]


def test_index_by_slice(sample_sequence):
    """Test slicing returns new Sequence."""
    subset = sample_sequence[0:2]
    
    assert isinstance(subset, Sequence)
    assert len(subset) == 2
    assert subset[0].section_code == "020000"
    assert subset[1].section_code == "020100"


def test_index_by_slice_step(sample_sequence):
    """Test slicing with step."""
    subset = sample_sequence[::2]  # Every other section
    
    assert isinstance(subset, Sequence)
    assert len(subset) == 2
    assert subset[0].section_code == "020000"
    assert subset[1].section_code == "020200"


def test_index_by_slice_empty_raises_error(sample_sequence):
    """Test slicing that results in empty list raises ValueError."""
    with pytest.raises(ValueError, match="empty sequence"):
        _ = sample_sequence[10:20]


def test_index_by_invalid_type(sample_sequence):
    """Test indexing with invalid type raises TypeError."""
    with pytest.raises(TypeError, match="Invalid key type"):
        _ = sample_sequence[3.14]


# === Iteration Tests ===

def test_iterate_over_sequence(sample_sequence):
    """Test iterating over Sequence yields SectionDocument objects."""
    sections = list(sample_sequence)
    
    assert len(sections) == 3
    assert all(isinstance(s, SectionDocument) for s in sections)
    assert sections[0].section_code == "020000"
    assert sections[1].section_code == "020100"
    assert sections[2].section_code == "020200"


def test_for_loop_iteration(sample_sequence):
    """Test for-loop iteration."""
    codes = []
    for section in sample_sequence:
        codes.append(section.section_code)
    
    assert codes == ["020000", "020100", "020200"]


# === Containment Tests ===

def test_contains_existing_section_code(sample_sequence):
    """Test __contains__ returns True for existing section_code."""
    assert "020000" in sample_sequence
    assert "020100" in sample_sequence
    assert "020200" in sample_sequence


def test_contains_nonexistent_section_code(sample_sequence):
    """Test __contains__ returns False for non-existent section_code."""
    assert "999999" not in sample_sequence
    assert "010000" not in sample_sequence


# === Length Tests ===

def test_len(sample_sequence):
    """Test len() returns section count."""
    assert len(sample_sequence) == 3


def test_section_count_matches_len(sample_sequence):
    """Test section_count property matches len()."""
    assert sample_sequence.section_count == len(sample_sequence)


# === Text Access Tests ===

def test_text_property_default_separator(sample_sequence):
    """Test .text property uses double newline separator."""
    text = sample_sequence.text
    
    assert "사업의 내용 전체 텍스트..." in text
    assert "당사는 본사를 거점으로..." in text
    assert "주요 제품은 반도체..." in text
    assert "\n\n" in text


def test_get_text_custom_separator(sample_sequence):
    """Test get_text() with custom separator."""
    text = sample_sequence.get_text(separator="\n---\n")
    
    assert "사업의 내용 전체 텍스트..." in text
    assert "당사는 본사를 거점으로..." in text
    assert "\n---\n" in text


def test_get_text_single_newline(sample_sequence):
    """Test get_text() with single newline."""
    text = sample_sequence.get_text(separator="\n")
    
    assert "\n" in text
    assert "\n\n" not in text  # Should not have double newlines


def test_get_text_empty_separator(sample_sequence):
    """Test get_text() with empty separator."""
    text = sample_sequence.get_text(separator="")
    
    # Text should be concatenated directly
    assert "사업의 내용 전체 텍스트...당사는 본사를 거점으로..." in text


# === Section Metadata Tests ===

def test_section_codes_property(sample_sequence):
    """Test section_codes returns list of codes."""
    codes = sample_sequence.section_codes
    
    assert codes == ["020000", "020100", "020200"]


def test_section_titles_property(sample_sequence):
    """Test section_titles returns list of titles."""
    titles = sample_sequence.section_titles
    
    assert titles == ["II. 사업의 내용", "1. 사업의 개요", "2. 주요 제품 및 서비스"]


# === Statistics Tests ===

def test_total_char_count(sample_sequence):
    """Test total_char_count sums all section char_counts."""
    expected = 1000 + 2500 + 3000  # From sample_sections fixture
    assert sample_sequence.total_char_count == expected


def test_total_word_count(sample_sequence):
    """Test total_word_count sums all section word_counts."""
    expected = 150 + 450 + 500  # From sample_sections fixture
    assert sample_sequence.total_word_count == expected


def test_section_count(sample_sequence):
    """Test section_count returns number of sections."""
    assert sample_sequence.section_count == 3


# === Export Tests ===

def test_to_dict(sample_sequence):
    """Test to_dict() converts to dictionary."""
    data = sample_sequence.to_dict()
    
    assert isinstance(data, dict)
    assert "metadata" in data
    assert "sections" in data
    assert "statistics" in data
    
    # Verify metadata
    assert data["metadata"]["rcept_no"] == "20240312000736"
    assert data["metadata"]["corp_name"] == "삼성전자"
    
    # Verify sections
    assert len(data["sections"]) == 3
    assert all(isinstance(s, dict) for s in data["sections"])
    
    # Verify statistics
    assert data["statistics"]["section_count"] == 3
    assert data["statistics"]["total_char_count"] == 6500
    assert data["statistics"]["total_word_count"] == 1100


def test_to_list(sample_sequence, sample_sections):
    """Test to_list() returns list of SectionDocument objects."""
    sections = sample_sequence.to_list()
    
    assert isinstance(sections, list)
    assert len(sections) == 3
    assert all(isinstance(s, SectionDocument) for s in sections)
    assert sections == sample_sections


# === String Representation Tests ===

def test_repr(sample_sequence):
    """Test __repr__ includes key information."""
    repr_str = repr(sample_sequence)
    
    assert "Sequence" in repr_str
    assert "삼성전자" in repr_str
    assert "2024" in repr_str
    assert "sections=3" in repr_str
    assert "words=1100" in repr_str


def test_str(sample_sequence):
    """Test __str__ shows section codes."""
    str_repr = str(sample_sequence)
    
    assert "Sequence" in str_repr
    assert "020000" in str_repr
    assert "020100" in str_repr
    assert "020200" in str_repr
    assert "3 sections" in str_repr


def test_str_truncates_long_list():
    """Test __str__ truncates section list if more than 3."""
    # Create sequence with 5 sections
    base_time = datetime(2024, 3, 12, 10, 30, 0)
    sections = []
    for i in range(5):
        sections.append(
            SectionDocument(
                document_id=f"20240312000736_02010{i}",
                rcept_no="20240312000736",
                rcept_dt="20240312",
                year="2024",
                corp_code="00126380",
                corp_name="삼성전자",
                stock_code="005930",
                report_type="A001",
                report_name="사업보고서",
                section_code=f"02010{i}",
                section_title=f"Section {i}",
                level=2,
                atocid=str(10 + i),
                parent_section_code="020000",
                parent_section_title="II. 사업의 내용",
                section_path=["020000", f"02010{i}"],
                text=f"Text {i}",
                char_count=1000,
                word_count=150,
                parsed_at=base_time,
                parser_version="1.0.0"
            )
        )
    
    seq = Sequence(sections)
    str_repr = str(seq)
    
    assert "..." in str_repr  # Should be truncated
    assert "5 sections" in str_repr


# === Edge Cases ===

def test_single_section_sequence():
    """Test Sequence with only one section."""
    section = SectionDocument(
        document_id="20240312000736_020000",
        rcept_no="20240312000736",
        rcept_dt="20240312",
        year="2024",
        corp_code="00126380",
        corp_name="삼성전자",
        stock_code="005930",
        report_type="A001",
        report_name="사업보고서",
        section_code="020000",
        section_title="II. 사업의 내용",
        level=1,
        atocid="9",
        parent_section_code=None,
        parent_section_title=None,
        section_path=["020000"],
        text="사업의 내용 전체 텍스트...",
        char_count=1000,
        word_count=150,
        parsed_at=datetime(2024, 3, 12, 10, 30, 0),
        parser_version="1.0.0"
    )
    
    seq = Sequence([section])
    
    assert len(seq) == 1
    assert seq.section_count == 1
    assert seq[0] == section
    assert seq.text == section.text


def test_sequence_with_zero_word_count_sections():
    """Test Sequence with sections having zero word count."""
    sections = [
        SectionDocument(
            document_id="20240312000736_020000",
            rcept_no="20240312000736",
            rcept_dt="20240312",
            year="2024",
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            report_type="A001",
            report_name="사업보고서",
            section_code="020000",
            section_title="Empty Section",
            level=1,
            atocid="9",
            parent_section_code=None,
            parent_section_title=None,
            section_path=["020000"],
            text="",
            char_count=0,
            word_count=0,
            parsed_at=datetime(2024, 3, 12, 10, 30, 0),
            parser_version="1.0.0"
        )
    ]
    
    seq = Sequence(sections)
    
    assert seq.total_char_count == 0
    assert seq.total_word_count == 0
    assert seq.text == ""

