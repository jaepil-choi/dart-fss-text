"""
XML Parsing modules for DART financial reports.

Based on Experiments 10, 12, 13:
- XML structure is FLAT (siblings), not nested
- Text-based matching (ATOCID absent in older reports)
- Pluggable matching strategies (exact, fuzzy, cascade)
- Must use .//P and .//TABLE for content extraction
"""

from .xml_parser import load_toc_mapping, build_section_index, extract_section_by_code
from .section_parser import parse_section_content
from .table_parser import parse_table
from .section_matcher import (
    SectionMatcher,
    ExactMatcher,
    FuzzyMatcher,
    CascadeMatcher,
    create_default_matcher
)

__all__ = [
    # XML Parsing
    'load_toc_mapping',
    'build_section_index',
    'extract_section_by_code',
    'parse_section_content',
    'parse_table',
    # Matching Strategies
    'SectionMatcher',
    'ExactMatcher',
    'FuzzyMatcher',
    'CascadeMatcher',
    'create_default_matcher',
]

