"""
User-facing API interfaces for dart-fss-text.

This module provides high-level query interfaces for retrieving
and working with stored financial disclosure sections.
"""

from dart_fss_text.api.query import TextQuery
from dart_fss_text.api.pipeline import DisclosurePipeline

__all__ = ['TextQuery', 'DisclosurePipeline']

