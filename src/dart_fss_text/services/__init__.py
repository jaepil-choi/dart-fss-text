"""
Business logic layer services for dart-fss-text.

This module contains service classes that implement core business logic:
- FilingSearchService: Filing search and filtering (uses dart-fss directly)
- DocumentDownloadService: Document download and extraction
- DocumentParserService: XML parsing (TODO)
- MetadataExtractor: Extract PIT-critical metadata (TODO)
"""

from dart_fss_text.services.filing_search import FilingSearchService
from dart_fss_text.services.document_download import (
    DocumentDownloadService,
    DownloadResult
)
from dart_fss_text.services.storage_service import StorageService

__all__ = [
    'FilingSearchService',
    'DocumentDownloadService',
    'DownloadResult',
    'StorageService'
]

