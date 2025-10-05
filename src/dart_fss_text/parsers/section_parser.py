"""
Section content extraction and hierarchy reconstruction.

Handles the FLAT XML structure by reconstructing hierarchy from:
1. Index key sequence (ATOCID or sequential number)
2. Level numbers (SECTION-1, SECTION-2, etc.)
3. Sequential scanning to identify parent-child relationships
"""

from typing import Dict, Any, List, Optional
from lxml import etree
from .table_parser import parse_table


def _extract_sort_key(index_key: str) -> int:
    """
    Extract numeric sort key from index key.
    
    Handles:
    - Numeric ATOCID: "3" → 3
    - Sequential key: "seq:3" → 3 (but we won't actually use these for hierarchy)
    - None-based sequential: "1", "2", "3" → 1, 2, 3
    
    Args:
        index_key: Index key from section_index
    
    Returns:
        Numeric sort key (0 if not parseable)
    """
    if not index_key:
        return 0
    
    # Handle sequential keys: "seq:3" → 3
    if index_key.startswith('seq:'):
        try:
            return int(index_key.split(':')[1])
        except (IndexError, ValueError):
            return 0
    
    # Handle numeric keys: "3" → 3
    if index_key.isdigit():
        return int(index_key)
    
    return 0


def parse_section_content(
    section_elem: etree._Element,
    section_index: Dict[str, Dict[str, Any]],
    section_code: str,
    parent_index_key: str
) -> Dict[str, Any]:
    """
    Parse section element into structured data.
    
    CRITICAL: XML structure is FLAT (all SECTION-N are siblings)!
    Hierarchy is reconstructed from:
    1. Index key sequence (ATOCID or sequential)
    2. Level numbers (SECTION-1 vs SECTION-2)
    3. TITLE text matching
    
    Args:
        section_elem: lxml Element for section
        section_index: Section index for looking up subsections
        section_code: Section code of this section
        parent_index_key: Index key of this section (ATOCID or sequential)
    
    Returns:
        Structured section dictionary with content and subsections
    """
    # Get actual ATOCID (may be None for older reports)
    parent_metadata = None
    for key, metadata in section_index.items():
        if key == parent_index_key:
            parent_metadata = metadata
            break
    
    actual_atocid = parent_metadata['atocid'] if parent_metadata else None
    
    result = {
        'title': '',
        'section_code': section_code,
        'level': int(section_elem.tag.split('-')[1]),
        'atocid': actual_atocid,  # Preserve actual ATOCID (may be None)
        'paragraphs': [],
        'tables': [],
        'subsections': []
    }
    
    # Extract title
    title_elem = section_elem.find('TITLE')
    if title_elem is not None:
        result['title'] = ''.join(title_elem.itertext()).strip()
    
    # Extract ALL paragraphs (including nested - structure is flat!)
    # CRITICAL: Must use .//P to get nested content
    for p in section_elem.findall('.//P'):
        text = ''.join(p.itertext()).strip()
        if text and not is_empty_paragraph(text):
            result['paragraphs'].append(text)
    
    # Extract ALL tables (including nested - structure is flat!)
    # CRITICAL: Must use .//TABLE to get nested content
    for table in section_elem.findall('.//TABLE[@ACLASS="NORMAL"]'):
        parsed_table = parse_table(table)
        if parsed_table['headers'] or parsed_table['rows']:
            result['tables'].append(parsed_table)
    
    # Find child sections from flat structure
    # Children are sections with:
    # 1. Higher level number (e.g., SECTION-2 is child of SECTION-1)
    # 2. Index key immediately following parent
    # 3. Before next same-or-higher level section
    parent_level = result['level']
    parent_sort_key = _extract_sort_key(parent_index_key)
    
    # Sort all sections by index key
    sorted_sections = sorted(
        section_index.items(),
        key=lambda x: _extract_sort_key(x[0])
    )
    
    # Find children: sections after parent with higher level
    for index_key, metadata in sorted_sections:
        sort_key = _extract_sort_key(index_key)
        
        # Skip if before or at parent
        if sort_key <= parent_sort_key:
            continue
        
        section_level = metadata['level']
        
        # Stop if we hit a same-or-higher level (sibling or aunt)
        if section_level <= parent_level:
            break
        
        # This is a direct child if level is exactly parent+1
        if section_level == parent_level + 1:
            child_elem = metadata['element']
            child_code = metadata['section_code']
            
            # Skip if child has no section_code (unmatched section)
            if not child_code:
                continue
            
            child_section = parse_section_content(
                child_elem, section_index, child_code, index_key
            )
            result['subsections'].append(child_section)
    
    return result


def is_empty_paragraph(text: str) -> bool:
    """
    Check if paragraph is empty or contains only whitespace.
    
    Args:
        text: Paragraph text
    
    Returns:
        True if empty/whitespace-only
    """
    return not text or text.isspace()


def extract_all_text(section: Dict[str, Any]) -> List[str]:
    """
    Extract all paragraph text from section and its subsections.
    
    Args:
        section: Structured section dictionary
    
    Returns:
        List of all paragraph texts
    """
    texts = section['paragraphs'].copy()
    
    # Recursively extract from subsections
    for subsection in section['subsections']:
        texts.extend(extract_all_text(subsection))
    
    return texts


def count_elements(section: Dict[str, Any]) -> Dict[str, int]:
    """
    Count paragraphs, tables, and subsections recursively.
    
    Args:
        section: Structured section dictionary
    
    Returns:
        Dictionary with counts
    """
    counts = {
        'paragraphs': len(section['paragraphs']),
        'tables': len(section['tables']),
        'subsections': len(section['subsections'])
    }
    
    # Add counts from subsections
    for subsection in section['subsections']:
        sub_counts = count_elements(subsection)
        counts['paragraphs'] += sub_counts['paragraphs']
        counts['tables'] += sub_counts['tables']
        counts['subsections'] += sub_counts['subsections']
    
    return counts

