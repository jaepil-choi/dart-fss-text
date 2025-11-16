"""
dart-fss-text: Korean DART business report text extraction library.

Main package exports for user-facing API.
"""

from dart_fss_text.services import CorpListService
from dart_fss_text.api import TextQuery, DisclosurePipeline, BackfillService

__all__ = [
    'CorpListService',
    'TextQuery',
    'DisclosurePipeline',
    'BackfillService',
    'initialize_corp_list'
]


def initialize_corp_list() -> str:
    """
    Initialize corporation list database.
    
    Explicit initialization function that loads corporation data from DART API
    and saves to CSV for fast subsequent lookups. This must be called once
    before using services that require corp lookups (FilingSearchService,
    DocumentDownloadService, BackfillService).
    
    Returns:
        Path to the saved CSV file
        
    Raises:
        ValueError: If OPENDART_API_KEY is not set
        
    Example:
        >>> from dart_fss_text import initialize_corp_list
        >>> csv_path = initialize_corp_list()
        >>> print(f"Corp list saved to: {csv_path}")
        Corp list saved to: data/temp/corp_list_20250115_143022.csv
        
    Note:
        This is a one-time operation (~7s). Subsequent lookups use cached data.
    """
    service = CorpListService()
    csv_path = service.initialize()
    return str(csv_path)

