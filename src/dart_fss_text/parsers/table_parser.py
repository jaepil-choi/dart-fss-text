"""
Table parsing utilities for DART XML reports.

Extracts tables with headers and rows from XML elements.
"""

from typing import Dict, Any, List
from lxml import etree


def parse_table(table_elem: etree._Element) -> Dict[str, Any]:
    """
    Extract table with headers and rows.
    
    Args:
        table_elem: lxml Element for TABLE
    
    Returns:
        Dictionary with 'headers' and 'rows' keys:
        {
            'headers': ['Header1', 'Header2', ...],
            'rows': [
                ['Cell1', 'Cell2', ...],
                ['Cell1', 'Cell2', ...],
                ...
            ]
        }
    """
    headers = []
    rows = []
    
    # Extract headers from THEAD
    thead = table_elem.find('THEAD')
    if thead is not None:
        for th in thead.findall('.//TH'):
            headers.append(''.join(th.itertext()).strip())
    
    # Extract rows from TBODY
    tbody = table_elem.find('TBODY')
    if tbody is not None:
        for tr in tbody.findall('TR'):
            row = []
            for td in tr.findall('TD'):
                row.append(''.join(td.itertext()).strip())
            if row:  # Only add non-empty rows
                rows.append(row)
    
    return {
        'headers': headers,
        'rows': rows
    }


def table_to_dict(table: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Convert table to list of dictionaries (one per row).
    
    Args:
        table: Parsed table from parse_table()
    
    Returns:
        List of dictionaries with header keys:
        [
            {'Header1': 'Cell1', 'Header2': 'Cell2', ...},
            {'Header1': 'Cell1', 'Header2': 'Cell2', ...},
            ...
        ]
    """
    if not table['headers']:
        return []
    
    result = []
    headers = table['headers']
    
    for row in table['rows']:
        row_dict = {}
        for i, header in enumerate(headers):
            # Handle rows with fewer cells than headers
            row_dict[header] = row[i] if i < len(row) else ''
        result.append(row_dict)
    
    return result


def count_tables(section: Dict[str, Any]) -> int:
    """
    Count total tables in section and subsections.
    
    Args:
        section: Structured section dictionary
    
    Returns:
        Total table count
    """
    count = len(section['tables'])
    
    # Add counts from subsections
    for subsection in section.get('subsections', []):
        count += count_tables(subsection)
    
    return count


def extract_all_tables(section: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all tables from section and its subsections.
    
    Args:
        section: Structured section dictionary
    
    Returns:
        List of all parsed tables
    """
    tables = section['tables'].copy()
    
    # Recursively extract from subsections
    for subsection in section.get('subsections', []):
        tables.extend(extract_all_tables(subsection))
    
    return tables

