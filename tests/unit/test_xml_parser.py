"""
Unit tests for XML parsing functionality.

Based on Experiment 10 findings:
- ATOCID is on TITLE tag, NOT SECTION tag
- XML structure is FLAT (siblings), not nested
- Only SECTION-1 and SECTION-2 exist
- Must use .//P and .//TABLE for content extraction
"""

import pytest
from pathlib import Path
from lxml import etree


# Test data paths
TEST_XML = Path('experiments/data/xml_sample/20240312000736.xml')
TOC_CONFIG = Path('config/toc.yaml')


class TestTOCMapping:
    """Test TOC (Table of Contents) mapping from toc.yaml."""
    
    def test_load_toc_mapping(self):
        """Should load toc.yaml and create title → section_code mapping."""
        from src.dart_fss_text.parsers import load_toc_mapping
        
        mapping = load_toc_mapping()
        
        # Should have 123 sections for A001
        assert len(mapping) == 123, f"Expected 123 sections, got {len(mapping)}"
        
        # Should contain major sections
        assert 'I. 회사의 개요' in mapping
        assert mapping['I. 회사의 개요'] == '010000'
        assert 'II. 사업의 내용' in mapping
        assert mapping['II. 사업의 내용'] == '020000'
    
    def test_toc_contains_major_sections(self):
        """Should contain all 12 major sections (I-XII)."""
        # TODO: Verify sections 010000-120000 exist
        pass
    
    def test_toc_structure_has_children(self):
        """Should preserve hierarchical structure with children."""
        # TODO: Verify section 020000 has 7 children
        pass


@pytest.fixture(scope="module")
def xml_tree():
    """Load test XML file (module-scoped for performance)."""
    parser = etree.XMLParser(recover=True, huge_tree=True, encoding='utf-8')
    return etree.parse(str(TEST_XML), parser)


class TestSectionIndexing:
    """Test section index building from XML."""
    
    def test_build_section_index(self, xml_tree):
        """Should build index of all SECTION-N elements."""
        from src.dart_fss_text.parsers import load_toc_mapping, build_section_index
        
        toc_mapping = load_toc_mapping()
        index = build_section_index(TEST_XML, toc_mapping)
        
        # Should find ~53 sections
        assert len(index) >= 50, f"Expected ~53 sections, got {len(index)}"
        assert len(index) <= 60, f"Expected ~53 sections, got {len(index)}"
        
        # Index should have proper structure
        for atocid, metadata in index.items():
            assert 'level' in metadata
            assert 'title' in metadata
            assert 'atocid' in metadata
            assert 'element' in metadata
    
    def test_extract_atocid_from_title_tag(self, xml_tree):
        """CRITICAL: ATOCID is on TITLE tag, NOT SECTION tag."""
        root = xml_tree.getroot()
        
        # Find first SECTION-1
        section = root.find('.//SECTION-1')
        assert section is not None
        
        # WRONG: ATOCID on SECTION tag (returns None)
        atocid_on_section = section.get('ATOCID')
        assert atocid_on_section is None, "ATOCID should NOT be on SECTION tag"
        
        # CORRECT: ATOCID on TITLE tag
        title_elem = section.find('TITLE')
        assert title_elem is not None
        atocid_on_title = title_elem.get('ATOCID')
        assert atocid_on_title is not None, "ATOCID should be on TITLE tag"
        assert atocid_on_title.isdigit(), "ATOCID should be numeric"
    
    def test_section_structure_is_flat(self, xml_tree):
        """CRITICAL: SECTION-N tags are siblings, not nested."""
        root = xml_tree.getroot()
        
        # Find first SECTION-1
        section_1 = root.find('.//SECTION-1')
        assert section_1 is not None
        
        # Check for nested SECTION-2 (should be 0 - they're siblings!)
        nested_section_2 = section_1.findall('SECTION-2')
        assert len(nested_section_2) == 0, "SECTION-2 should NOT be nested inside SECTION-1"
        
        # All SECTION-2 should be siblings in BODY
        body = root.find('.//BODY')
        all_section_2 = body.findall('.//SECTION-2') if body is not None else []
        assert len(all_section_2) > 0, "SECTION-2 should exist as siblings"
    
    def test_section_distribution(self, xml_tree):
        """Most sections are SECTION-1 and SECTION-2 (SECTION-3+ are rare)."""
        root = xml_tree.getroot()
        
        section_1 = root.findall('.//SECTION-1')
        section_2 = root.findall('.//SECTION-2')
        section_3 = root.findall('.//SECTION-3')
        section_4 = root.findall('.//SECTION-4')
        
        # Primary sections exist in large numbers
        assert len(section_1) > 10, f"SECTION-1 should be common, found {len(section_1)}"
        assert len(section_2) > 30, f"SECTION-2 should be common, found {len(section_2)}"
        
        # SECTION-3 is rare (may exist in some documents)
        assert len(section_3) < 5, f"SECTION-3 should be rare, found {len(section_3)}"
        
        # SECTION-4 is very rare or non-existent
        assert len(section_4) < 2, f"SECTION-4 should be very rare, found {len(section_4)}"
        
        # Primary structure is 2-level hierarchy
        total_sections = len(section_1) + len(section_2) + len(section_3) + len(section_4)
        primary_sections = len(section_1) + len(section_2)
        assert (primary_sections / total_sections) > 0.90, "90%+ sections should be level 1-2"
    
    def test_index_contains_required_metadata(self):
        """Each indexed section should have: level, title, section_code, atocid."""
        # TODO: Verify index structure
        # Expected keys: level, title, section_code, atocid, element
        pass
    
    def test_index_performance(self):
        """Indexing 155K lines should take < 1 second."""
        # TODO: Measure indexing time
        # Expected: < 1.0s (actual: 0.144-0.167s)
        pass


class TestTitleMapping:
    """Test title → section_code mapping."""
    
    def test_map_exact_title_match(self):
        """Should map exact title matches to section codes."""
        # TODO: Test "II. 사업의 내용" → "020000"
        pass
    
    def test_map_with_whitespace_normalization(self):
        """Should handle extra whitespace in titles."""
        # TODO: Test normalization
        pass
    
    def test_mapping_accuracy(self):
        """Should achieve ≥90% mapping accuracy."""
        # TODO: Verify mapping accuracy
        # Expected: 49/53 = 92.5%
        pass


class TestHierarchyReconstruction:
    """Test hierarchy reconstruction from flat structure."""
    
    def test_find_children_by_atocid_sequence(self):
        """Should find child sections using ATOCID sequence."""
        # Given: Parent ATOCID=9, Level=1 (II. 사업의 내용)
        # Expected: Find 7 children (ATOCID 10-16, Level=2)
        # TODO: Implement find_children()
        pass
    
    def test_children_have_higher_level(self):
        """Children should have level = parent_level + 1."""
        # TODO: Verify level increments
        pass
    
    def test_stop_at_next_sibling(self):
        """Should stop finding children when hitting same-or-higher level."""
        # TODO: Test boundary detection
        pass


@pytest.fixture(scope="module")
def target_section_element(xml_tree):
    """Get target section (020000) element."""
    root = xml_tree.getroot()
    sections = root.findall('.//SECTION-1')
    for section in sections:
        title_elem = section.find('TITLE')
        if title_elem is not None:
            title = ''.join(title_elem.itertext()).strip()
            if 'II. 사업의 내용' in title:
                return section
    return None


class TestContentExtraction:
    """Test paragraph and table extraction."""
    
    def test_extract_paragraphs_with_nested_search(self, target_section_element):
        """CRITICAL: Must use .//P to get all nested paragraphs."""
        assert target_section_element is not None
        
        # Direct children only (WRONG - returns ~1)
        direct_p = target_section_element.findall('P')
        
        # Nested search (CORRECT - returns ~185)
        nested_p = target_section_element.findall('.//P')
        
        assert len(nested_p) > len(direct_p), "Nested search should find more paragraphs"
        assert len(nested_p) >= 150, f"Should find ~185 paragraphs, got {len(nested_p)}"
    
    def test_extract_tables_with_nested_search(self, target_section_element):
        """Should extract tables using nested search."""
        assert target_section_element is not None
        
        # Find all tables
        tables = target_section_element.findall('.//TABLE[@ACLASS="NORMAL"]')
        
        assert len(tables) >= 80, f"Should find ~89 tables, got {len(tables)}"
    
    def test_extract_paragraph_text_with_itertext(self):
        """Should use itertext() to handle nested spans and formatting."""
        # TODO: Test text extraction with nested elements
        pass
    
    def test_filter_empty_paragraphs(self):
        """Should filter out empty or whitespace-only paragraphs."""
        # TODO: Test empty paragraph filtering
        pass


class TestSectionExtraction:
    """Test extracting specific sections by code."""
    
    def test_extract_section_020000(self):
        """Should extract section 020000 (II. 사업의 내용)."""
        from src.dart_fss_text.parsers import load_toc_mapping, build_section_index, extract_section_by_code
        
        toc_mapping = load_toc_mapping()
        index = build_section_index(TEST_XML, toc_mapping)
        section = extract_section_by_code(index, '020000')
        
        assert section is not None, "Section 020000 should exist"
        assert section['title'] == 'II. 사업의 내용'
        assert section['section_code'] == '020000'
        
        # Expected: 150 paragraphs, 89 tables, 7 subsections
        assert len(section['paragraphs']) >= 140, f"Expected ~150 paragraphs, got {len(section['paragraphs'])}"
        assert len(section['tables']) >= 80, f"Expected ~89 tables, got {len(section['tables'])}"
        assert len(section['subsections']) == 7, f"Expected 7 subsections, got {len(section['subsections'])}"
    
    def test_extract_section_020100(self):
        """Should extract section 020100 (1. 사업의 개요)."""
        from src.dart_fss_text.parsers import load_toc_mapping, build_section_index, extract_section_by_code
        
        toc_mapping = load_toc_mapping()
        index = build_section_index(TEST_XML, toc_mapping)
        section = extract_section_by_code(index, '020100')
        
        assert section is not None, "Section 020100 should exist"
        assert section['title'] == '1. 사업의 개요'
        assert section['section_code'] == '020100'
        
        # Expected: 6 paragraphs, 0 tables, 0 subsections
        assert len(section['paragraphs']) == 6, f"Expected 6 paragraphs, got {len(section['paragraphs'])}"
        assert len(section['tables']) == 0, f"Expected 0 tables, got {len(section['tables'])}"
        assert len(section['subsections']) == 0, f"Expected 0 subsections, got {len(section['subsections'])}"
        
        # Check first paragraph starts correctly
        assert section['paragraphs'][0].startswith('당사는 본사를 거점으로')
    
    def test_section_contains_full_text(self):
        """Should extract complete text content."""
        from src.dart_fss_text.parsers import load_toc_mapping, build_section_index, extract_section_by_code
        
        toc_mapping = load_toc_mapping()
        index = build_section_index(TEST_XML, toc_mapping)
        section = extract_section_by_code(index, '020100')
        
        # Verify paragraph 6 contains revenue information
        assert len(section['paragraphs']) >= 6
        last_paragraph = section['paragraphs'][5]  # 6th paragraph (0-indexed)
        assert '258조' in last_paragraph or '258조 9,355억원' in last_paragraph
    
    def test_section_contains_subsections(self):
        """Should recursively extract subsections."""
        # Expected subsections for 020000:
        # - 020100: 사업의 개요 (6 paragraphs)
        # - 020200: 주요 제품 및 서비스 (3 paragraphs, 5 tables)
        # - 020300: 원재료 및 생산설비 (14 paragraphs, 25 tables)
        # - 020400: 매출 및 수주상황 (16 paragraphs, 17 tables)
        # - 020500: 위험관리 및 파생거래 (27 paragraphs, 14 tables)
        # - 020600: 주요계약 및 연구개발활동 (13 paragraphs, 8 tables)
        # - 020700: 기타 참고사항 (71 paragraphs, 20 tables)
        pass
    
    def test_extraction_performance(self):
        """Extracting one section should take < 0.2 seconds."""
        # TODO: Measure extraction time
        # Expected: < 0.2s (actual: 0.009-0.010s)
        pass


class TestTableParsing:
    """Test table parsing with headers and rows."""
    
    def test_parse_table_with_headers(self):
        """Should extract table headers from THEAD."""
        # TODO: Implement parse_table()
        pass
    
    def test_parse_table_with_rows(self):
        """Should extract table rows from TBODY."""
        # TODO: Test row extraction
        pass
    
    def test_table_structure(self):
        """Should return dict with 'headers' and 'rows' keys."""
        # TODO: Verify structure
        pass


class TestCoverageValidation:
    """Test coverage validation against toc.yaml."""
    
    def test_validate_section_coverage(self):
        """Should compare extracted sections vs. toc.yaml."""
        # Expected: 49/123 sections (39.8%)
        # Expected unmapped: 4 sections
        # Expected missing: 74 sections
        pass
    
    def test_identify_missing_sections(self):
        """Should identify sections in toc.yaml but not in XML."""
        # Expected missing: 030201, 030202, 030203, 030204, 030205, ...
        pass
    
    def test_identify_unmapped_sections(self):
        """Should identify sections in XML but not mapped to codes."""
        # Expected: 4 unmapped sections
        pass


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_handle_missing_atocid(self):
        """Should skip sections without ATOCID."""
        pass
    
    def test_handle_missing_title(self):
        """Should skip sections without TITLE element."""
        pass
    
    def test_handle_malformed_xml(self):
        """Should use lxml recover mode for malformed XML."""
        pass
    
    def test_handle_empty_sections(self):
        """Should handle sections with no paragraphs or tables."""
        pass


# Test data for validation
EXPECTED_SECTION_020100_PARAGRAPHS = [
    "당사는 본사를 거점으로 한국과 DX 부문 산하 해외 9개 지역총괄",
    "사업별로 보면, Set 사업은 DX(Device eXperience) 부문이 TV를 비롯하여",
    "지역별로 보면, 국내에서는 DX 부문 및 DS 부문 등을 총괄하는 본사와 35개의",
    "해외(미주, 유럽ㆍCIS, 중동ㆍ아프리카, 아시아 등지)에서는 생산, 판매, 연구활동",
    "유럽ㆍCIS에는 SEUK(UK), SEG(Germany), SEF(France), SEI(Italy)",
    "2023년 당사의 매출은 258조 9,355억원으로 전년 대비 14.3% 감소",
]

EXPECTED_SECTION_020000_SUBSECTIONS = [
    {'code': '020100', 'title': '1. 사업의 개요', 'paragraphs': 6, 'tables': 0},
    {'code': '020200', 'title': '2. 주요 제품 및 서비스', 'paragraphs': 3, 'tables': 5},
    {'code': '020300', 'title': '3. 원재료 및 생산설비', 'paragraphs': 14, 'tables': 25},
    {'code': '020400', 'title': '4. 매출 및 수주상황', 'paragraphs': 16, 'tables': 17},
    {'code': '020500', 'title': '5. 위험관리 및 파생거래', 'paragraphs': 27, 'tables': 14},
    {'code': '020600', 'title': '6. 주요계약 및 연구개발활동', 'paragraphs': 13, 'tables': 8},
    {'code': '020700', 'title': '7. 기타 참고사항', 'paragraphs': 71, 'tables': 20},
]

