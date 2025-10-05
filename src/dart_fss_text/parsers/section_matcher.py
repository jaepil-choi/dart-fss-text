"""
Section Matching Strategies

Provides pluggable strategies for matching TITLE tags to section codes.
Supports multiple matching algorithms with configurable parameters.

Design:
- Strategy Pattern: Matchers are interchangeable
- Each matcher implements the same interface
- Parser is agnostic to matching strategy
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
from difflib import SequenceMatcher


class SectionMatcher(ABC):
    """
    Abstract base class for section matching strategies.
    
    Matches TITLE text to section codes from toc.yaml.
    """
    
    @abstractmethod
    def match(
        self,
        title_text: str,
        toc_mapping: Dict[str, str]
    ) -> Optional[str]:
        """
        Match title text to a section code.
        
        Args:
            title_text: Cleaned title text from TITLE tag
            toc_mapping: Dict mapping section_name → section_code
        
        Returns:
            section_code if matched, None otherwise
        """
        pass


class ExactMatcher(SectionMatcher):
    """
    Exact string matching against toc.yaml section names.
    
    Fast and deterministic. Use as primary matcher.
    """
    
    def match(
        self,
        title_text: str,
        toc_mapping: Dict[str, str]
    ) -> Optional[str]:
        """Match via exact string comparison."""
        # Try direct lookup
        if title_text in toc_mapping:
            return toc_mapping[title_text]
        
        # Try with normalized whitespace
        title_clean = ' '.join(title_text.split())
        if title_clean in toc_mapping:
            return toc_mapping[title_clean]
        
        return None


class FuzzyMatcher(SectionMatcher):
    """
    Fuzzy string matching using SequenceMatcher.
    
    Handles minor variations in section titles (e.g., "감사인" vs "회계감사인").
    Use as fallback with conservative threshold.
    
    Args:
        threshold: Minimum similarity score (0.0-1.0). Default: 0.90
    """
    
    def __init__(self, threshold: float = 0.90):
        """
        Initialize fuzzy matcher.
        
        Args:
            threshold: Minimum similarity score (0.0-1.0).
                      0.90 (90%) recommended for production.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {threshold}")
        
        self.threshold = threshold
    
    def match(
        self,
        title_text: str,
        toc_mapping: Dict[str, str]
    ) -> Optional[str]:
        """
        Match via fuzzy string comparison.
        
        Returns best match if similarity >= threshold.
        """
        best_match: Optional[Tuple[str, str, float]] = None
        best_score = 0.0
        
        title_clean = ' '.join(title_text.split())
        
        for section_name, section_code in toc_mapping.items():
            ratio = SequenceMatcher(None, title_clean, section_name).ratio()
            
            if ratio > best_score:
                best_score = ratio
                best_match = (section_name, section_code, ratio)
        
        if best_match and best_score >= self.threshold:
            return best_match[1]  # Return section_code
        
        return None


class CascadeMatcher(SectionMatcher):
    """
    Cascade multiple matchers in sequence.
    
    Tries each matcher in order until one succeeds.
    Recommended: ExactMatcher → FuzzyMatcher(0.90)
    
    Args:
        matchers: List of matchers to try in order
    
    Example:
        >>> matcher = CascadeMatcher([
        ...     ExactMatcher(),
        ...     FuzzyMatcher(threshold=0.90)
        ... ])
    """
    
    def __init__(self, matchers: list):
        """
        Initialize cascade matcher.
        
        Args:
            matchers: List of SectionMatcher instances
        """
        if not matchers:
            raise ValueError("Must provide at least one matcher")
        
        self.matchers = matchers
    
    def match(
        self,
        title_text: str,
        toc_mapping: Dict[str, str]
    ) -> Optional[str]:
        """
        Try each matcher in sequence until one succeeds.
        """
        for matcher in self.matchers:
            result = matcher.match(title_text, toc_mapping)
            if result is not None:
                return result
        
        return None


def create_default_matcher() -> SectionMatcher:
    """
    Create default matching strategy.
    
    Strategy: Exact → Fuzzy (0.90)
    
    This is the recommended production configuration based on
    Experiment 13 findings:
    - Exact matching: 62.9% success rate
    - Fuzzy (0.90+): Additional 8.6% (high confidence)
    - Total: 71.5% match rate on all titles
    - 100% match rate on content sections
    
    Returns:
        CascadeMatcher with exact and fuzzy (0.90) strategies
    """
    return CascadeMatcher([
        ExactMatcher(),
        FuzzyMatcher(threshold=0.90)
    ])

