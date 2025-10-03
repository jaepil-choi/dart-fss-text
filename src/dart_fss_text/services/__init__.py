"""
Business logic layer services for dart-fss-text.

This module contains service classes that implement core business logic:
- FilingSearchService: Filing search and filtering (uses dart-fss directly)
- DocumentParserService: XML parsing
- MetadataExtractor: Extract PIT-critical metadata
"""

from dart_fss_text.services.filing_search import FilingSearchService

__all__ = [
    'FilingSearchService',
]

