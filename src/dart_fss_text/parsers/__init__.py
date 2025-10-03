"""
XML Parsing modules for DART financial reports.

Based on Experiment 10 findings:
- ATOCID is on TITLE tag, NOT SECTION tag
- XML structure is FLAT (siblings), not nested
- Hierarchy reconstructed from ATOCID sequence + level numbers
- Must use .//P and .//TABLE for content extraction
"""

from .xml_parser import load_toc_mapping, build_section_index, extract_section_by_code
from .section_parser import parse_section_content
from .table_parser import parse_table

__all__ = [
    'load_toc_mapping',
    'build_section_index',
    'extract_section_by_code',
    'parse_section_content',
    'parse_table',
]

