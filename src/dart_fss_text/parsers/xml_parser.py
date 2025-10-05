"""
Low-level XML parsing utilities for DART reports.

Key architectural discoveries (Experiment 10):
1. ATOCID is on <TITLE> tag, NOT <SECTION> tag
2. XML structure is FLAT - all SECTION-N are siblings
3. Hierarchy reconstructed from ATOCID sequence + level numbers
"""

from pathlib import Path
from typing import Dict, Any, Optional
from lxml import etree


def load_toc_mapping(report_type: str = 'A001') -> Dict[str, str]:
    """
    Load TOC (Table of Contents) mapping via config facade.
    
    DEPRECATED: This function is maintained for backward compatibility.
    New code should use `from dart_fss_text.config import get_toc_mapping` directly.
    
    Creates a title → section_code mapping for specified report type.
    
    Args:
        report_type: Report type code (e.g., 'A001' for Annual Report)
    
    Returns:
        Dictionary mapping section titles to section codes
        Example: {'I. 회사의 개요': '010000', ...}
    
    Example:
        >>> toc = load_toc_mapping('A001')
        >>> toc['I. 회사의 개요']
        '010000'
    """
    from dart_fss_text.config import get_toc_mapping
    return get_toc_mapping(report_type)


def build_section_index(
    xml_path: Path,
    toc_mapping: Dict[str, str]
) -> Dict[str, Dict[str, Any]]:
    """
    Build lightweight index of all SECTION-N elements in XML.
    
    CRITICAL: Uses flat structure scanning, not recursive descent.
    - ATOCID extracted from TITLE tag (not SECTION tag)
    - All sections are siblings in XML tree
    - Hierarchy reconstructed later from ATOCID sequence
    
    Args:
        xml_path: Path to DART XML file
        toc_mapping: Title → section_code mapping from toc.yaml
    
    Returns:
        Dictionary mapping ATOCID to section metadata:
        {
            '3': {
                'level': 1,
                'title': 'I. 회사의 개요',
                'section_code': '010000',
                'atocid': '3',
                'aclass': 'MANDATORY',
                'element': <lxml.Element>
            },
            ...
        }
    """
    # Parse XML with encoding fallback (UTF-8 → EUC-KR)
    # DART XML files are sometimes encoded in EUC-KR instead of UTF-8
    tree = None
    last_error = None
    
    for encoding in ['utf-8', 'euc-kr']:
        try:
            parser = etree.XMLParser(recover=True, huge_tree=True, encoding=encoding)
            tree = etree.parse(str(xml_path), parser)
            break  # Success - stop trying
        except etree.XMLSyntaxError as e:
            if 'encoding' in str(e).lower():
                # Encoding error - try next encoding
                last_error = e
                continue
            else:
                # Non-encoding error - raise immediately
                raise
        except Exception as e:
            # Unexpected error - raise immediately
            raise
    
    if tree is None:
        # Both encodings failed
        raise ValueError(
            f"Failed to parse XML with UTF-8 or EUC-KR encoding. "
            f"File: {xml_path}. "
            f"Last error: {last_error}"
        )
    
    root = tree.getroot()
    
    index = {}
    
    # Find all SECTION-N tags (flat structure scan)
    sections = root.xpath("//SECTION-1 | //SECTION-2 | //SECTION-3 | //SECTION-4")
    
    for section in sections:
        level = int(section.tag.split('-')[1])
        
        # CRITICAL: Extract ATOCID from TITLE tag (not SECTION tag!)
        title_elem = section.find('TITLE')
        if title_elem is None:
            continue  # Skip sections without TITLE
        
        title = ''.join(title_elem.itertext()).strip()
        atocid = title_elem.get('ATOCID')  # Get ATOCID from TITLE
        
        # Skip sections without ATOCID
        if not atocid:
            continue
        
        # Map title to section_code using toc.yaml
        section_code = map_title_to_section_code(title, toc_mapping)
        
        index[atocid] = {
            'level': level,
            'title': title,
            'section_code': section_code,
            'atocid': atocid,
            'aclass': section.get('ACLASS'),
            'element': section  # Store reference for later content extraction
        }
    
    return index


def map_title_to_section_code(
    title: str,
    toc_mapping: Dict[str, str]
) -> Optional[str]:
    """
    Map XML section title to standardized section code from toc.yaml.
    
    Uses fuzzy matching to handle whitespace variations.
    
    Args:
        title: Section title from XML
        toc_mapping: Title → section_code mapping
    
    Returns:
        Section code (e.g., '010000') or None if not found
    """
    # Exact match
    if title in toc_mapping:
        return toc_mapping[title]
    
    # Normalized whitespace match
    normalized_title = ' '.join(title.split())
    if normalized_title in toc_mapping:
        return toc_mapping[normalized_title]
    
    # Fuzzy match (contains or contained by)
    for toc_title, code in toc_mapping.items():
        if title in toc_title or toc_title in title:
            return code
    
    return None  # Unmapped section


def extract_section_by_code(
    section_index: Dict[str, Dict[str, Any]],
    section_code: str
) -> Optional[Dict[str, Any]]:
    """
    Extract specific section by section code.
    
    Args:
        section_index: Section index from build_section_index()
        section_code: Target section code (e.g., '020000')
    
    Returns:
        Structured section dictionary with content, or None if not found
    """
    from .section_parser import parse_section_content
    
    # Find section with matching code
    target = None
    for atocid, metadata in section_index.items():
        if metadata['section_code'] == section_code:
            target = metadata
            break
    
    if not target:
        return None
    
    section_elem = target['element']
    parent_atocid = target['atocid']
    
    return parse_section_content(section_elem, section_index, section_code, parent_atocid)


def validate_section_coverage(
    section_index: Dict[str, Dict[str, Any]],
    toc_mapping: Dict[str, str]
) -> Dict[str, Any]:
    """
    Compare extracted sections against toc.yaml structure.
    
    Args:
        section_index: Section index from build_section_index()
        toc_mapping: Title → section_code mapping from toc.yaml
    
    Returns:
        Coverage statistics dictionary
    """
    expected_codes = set(toc_mapping.values())
    extracted_codes = set(
        s['section_code'] for s in section_index.values() 
        if s['section_code']
    )
    unmapped_count = sum(
        1 for s in section_index.values() 
        if s['section_code'] is None
    )
    
    missing = expected_codes - extracted_codes
    extra = extracted_codes - expected_codes
    
    return {
        'total_expected': len(expected_codes),
        'total_extracted': len(extracted_codes),
        'total_in_xml': len(section_index),
        'unmapped_count': unmapped_count,
        'missing_sections': sorted(list(missing)),
        'extra_sections': sorted(list(extra)),
        'coverage_rate': len(extracted_codes) / len(expected_codes) if expected_codes else 0
    }

