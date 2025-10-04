"""
Sequence collection class for ordered SectionDocument objects.

This module defines Sequence, a user-facing collection class that groups
SectionDocument objects from the same report and provides convenient access
patterns including merged text, indexing, and statistics.
"""

from typing import List, Iterator, Union, overload
from .section import SectionDocument
from .metadata import ReportMetadata


class Sequence:
    """
    Ordered collection of SectionDocument objects from the same report.
    
    All sections in a Sequence must share the same report metadata (rcept_no,
    year, stock_code, etc.). This class provides convenient access to sections
    and their merged text content.
    
    Key Features:
    - Contains List[SectionDocument] with shared metadata
    - Provides merged text access with customizable separator
    - Supports indexing by position (int), section_code (str), or slice
    - Validates all sections share same report metadata
    - Offers collection statistics (total chars, words, section count)
    
    Design Pattern: Composition
    - "Has-a" ReportMetadata (shared metadata)
    - "Contains" List[SectionDocument] (sections)
    
    Attributes:
        metadata: Shared ReportMetadata for all sections
        
    Example:
        >>> from dart_fss_text.models import SectionDocument, Sequence
        >>> sections = [doc1, doc2, doc3]  # SectionDocument objects
        >>> seq = Sequence(sections)
        >>> 
        >>> # Access sections
        >>> first = seq[0]                  # By index → SectionDocument
        >>> specific = seq["020100"]        # By code → SectionDocument
        >>> subset = seq[1:3]               # By slice → Sequence
        >>> 
        >>> # Merged text
        >>> text = seq.text                 # Default separator: \\n\\n
        >>> text = seq.get_text(sep="\\n")  # Custom separator
        >>> 
        >>> # Metadata (shared across all sections)
        >>> print(seq.corp_name, seq.year)
        '삼성전자 2024'
        >>> 
        >>> # Statistics
        >>> print(seq.total_word_count, seq.section_count)
        12500 15
    """
    
    def __init__(self, sections: List[SectionDocument]):
        """
        Initialize Sequence from list of SectionDocument objects.
        
        Args:
            sections: List of SectionDocument objects (must share same report metadata)
        
        Raises:
            ValueError: If sections list is empty
            ValueError: If sections have different report metadata
        
        Example:
            >>> seq = Sequence([doc1, doc2, doc3])
        """
        if not sections:
            raise ValueError("Sequence must contain at least one section")
        
        # Extract and validate shared metadata
        first_doc = sections[0]
        first_meta = ReportMetadata.from_section_document(first_doc)
        
        for i, doc in enumerate(sections[1:], start=1):
            doc_meta = ReportMetadata.from_section_document(doc)
            if doc_meta != first_meta:
                raise ValueError(
                    f"All sections must share same report metadata. "
                    f"Section at index {i} has mismatched metadata: "
                    f"rcept_no={doc.rcept_no} (expected {first_meta.rcept_no})"
                )
        
        self._sections = sections
        self.metadata = first_meta
    
    # === Report Metadata (delegated to metadata) ===
    
    @property
    def rcept_no(self) -> str:
        """Receipt number (shared across all sections)."""
        return self.metadata.rcept_no
    
    @property
    def rcept_dt(self) -> str:
        """Receipt date (shared across all sections)."""
        return self.metadata.rcept_dt
    
    @property
    def year(self) -> str:
        """Year (shared across all sections)."""
        return self.metadata.year
    
    @property
    def corp_code(self) -> str:
        """Corporation code (shared across all sections)."""
        return self.metadata.corp_code
    
    @property
    def corp_name(self) -> str:
        """Company name (shared across all sections)."""
        return self.metadata.corp_name
    
    @property
    def stock_code(self) -> str:
        """Stock code (shared across all sections)."""
        return self.metadata.stock_code
    
    @property
    def report_type(self) -> str:
        """Report type (shared across all sections)."""
        return self.metadata.report_type
    
    @property
    def report_name(self) -> str:
        """Report name (shared across all sections)."""
        return self.metadata.report_name
    
    # === Collection Access ===
    
    @overload
    def __getitem__(self, key: int) -> SectionDocument: ...
    
    @overload
    def __getitem__(self, key: str) -> SectionDocument: ...
    
    @overload
    def __getitem__(self, key: slice) -> 'Sequence': ...
    
    def __getitem__(self, key: Union[int, str, slice]) -> Union[SectionDocument, 'Sequence']:
        """
        Access sections by index, section_code, or slice.
        
        Args:
            key: Integer index, section_code string, or slice
        
        Returns:
            SectionDocument if key is int or str
            Sequence if key is slice
        
        Raises:
            KeyError: If section_code not found
            IndexError: If integer index out of range
        
        Examples:
            >>> seq[0]           # First section → SectionDocument
            >>> seq["020100"]    # By section code → SectionDocument
            >>> seq[1:3]         # Slice → Sequence
        """
        if isinstance(key, int):
            return self._sections[key]
        elif isinstance(key, str):
            # Find by section_code
            for section in self._sections:
                if section.section_code == key:
                    return section
            raise KeyError(f"No section with code '{key}' in sequence")
        elif isinstance(key, slice):
            sliced_sections = self._sections[key]
            if not sliced_sections:
                raise ValueError("Slice resulted in empty sequence")
            return Sequence(sliced_sections)
        else:
            raise TypeError(f"Invalid key type: {type(key).__name__}")
    
    def __iter__(self) -> Iterator[SectionDocument]:
        """
        Iterate over sections in order.
        
        Yields:
            SectionDocument objects in sequence order
        
        Example:
            >>> for section in seq:
            ...     print(section.section_title)
        """
        return iter(self._sections)
    
    def __len__(self) -> int:
        """
        Number of sections in sequence.
        
        Returns:
            Section count
        
        Example:
            >>> len(seq)
            15
        """
        return len(self._sections)
    
    def __contains__(self, section_code: str) -> bool:
        """
        Check if section_code exists in sequence.
        
        Args:
            section_code: Section code to check
        
        Returns:
            True if section exists, False otherwise
        
        Example:
            >>> "020100" in seq
            True
        """
        return any(s.section_code == section_code for s in self._sections)
    
    # === Text Access ===
    
    @property
    def text(self) -> str:
        """
        Merged text of all sections.
        
        Sections are joined with double newline separator.
        Order is preserved from the sequence.
        
        Returns:
            Merged text string
        
        Example:
            >>> text = seq.text
            >>> print(len(text))
            125000
        """
        return self.get_text(separator="\n\n")
    
    def get_text(self, separator: str = "\n\n") -> str:
        """
        Get merged text with custom separator.
        
        Args:
            separator: String to join section texts (default: double newline)
        
        Returns:
            Merged text string
        
        Example:
            >>> text = seq.get_text(separator="\\n")  # Single newline
            >>> text = seq.get_text(separator="\\n---\\n")  # With divider
        """
        return separator.join(s.text for s in self._sections)
    
    # === Section Metadata ===
    
    @property
    def section_codes(self) -> List[str]:
        """
        List of all section codes in sequence.
        
        Returns:
            List of section codes in order
        
        Example:
            >>> seq.section_codes
            ['020000', '020100', '020200']
        """
        return [s.section_code for s in self._sections]
    
    @property
    def section_titles(self) -> List[str]:
        """
        List of all section titles in sequence.
        
        Returns:
            List of section titles in order
        
        Example:
            >>> seq.section_titles
            ['II. 사업의 내용', '1. 사업의 개요', '2. 주요 제품 및 서비스']
        """
        return [s.section_title for s in self._sections]
    
    # === Statistics ===
    
    @property
    def section_count(self) -> int:
        """
        Number of sections (same as len()).
        
        Returns:
            Section count
        
        Example:
            >>> seq.section_count
            15
        """
        return len(self._sections)
    
    @property
    def total_char_count(self) -> int:
        """
        Sum of character counts across all sections.
        
        Returns:
            Total character count
        
        Example:
            >>> seq.total_char_count
            125000
        """
        return sum(s.char_count for s in self._sections)
    
    @property
    def total_word_count(self) -> int:
        """
        Sum of word counts across all sections.
        
        Returns:
            Total word count
        
        Example:
            >>> seq.total_word_count
            12500
        """
        return sum(s.word_count for s in self._sections)
    
    # === Export ===
    
    def to_dict(self) -> dict:
        """
        Convert to dictionary.
        
        Returns:
            Dictionary with metadata, sections, and statistics
        
        Example:
            >>> data = seq.to_dict()
            >>> data.keys()
            dict_keys(['metadata', 'sections', 'statistics'])
        """
        return {
            "metadata": self.metadata.model_dump(),
            "sections": [s.model_dump() for s in self._sections],
            "statistics": {
                "section_count": self.section_count,
                "total_char_count": self.total_char_count,
                "total_word_count": self.total_word_count,
            }
        }
    
    def to_list(self) -> List[SectionDocument]:
        """
        Convert to list of SectionDocument objects.
        
        Returns:
            List of SectionDocument objects
        
        Example:
            >>> sections = seq.to_list()
            >>> isinstance(sections[0], SectionDocument)
            True
        """
        return list(self._sections)
    
    def __repr__(self) -> str:
        return (
            f"Sequence(corp='{self.corp_name}', year={self.year}, "
            f"sections={self.section_count}, words={self.total_word_count})"
        )
    
    def __str__(self) -> str:
        sections_str = ", ".join(self.section_codes[:3])
        if len(self.section_codes) > 3:
            sections_str += ", ..."
        return f"Sequence[{sections_str}] ({self.section_count} sections)"

