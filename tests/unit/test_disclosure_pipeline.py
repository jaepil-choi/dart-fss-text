"""
Unit tests for DisclosurePipeline.

Tests the high-level orchestrator that coordinates:
- Filing search (via FilingSearchService)
- Document download
- XML parsing
- Section storage (via StorageService)

All external dependencies are mocked for fast, isolated unit tests.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from pathlib import Path

# Import will fail until we create the module - that's expected for TDD
# from dart_fss_text.api.pipeline import DisclosurePipeline
from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.models.section import SectionDocument


class TestDisclosurePipelineInitialization:
    """Test pipeline initialization with dependency injection."""
    
    def test_init_with_storage_service(self):
        """Pipeline should accept StorageService via dependency injection."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        
        # Act
        from dart_fss_text.api.pipeline import DisclosurePipeline
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Assert
        assert pipeline._storage == mock_storage
    
    def test_init_creates_filing_search_service(self):
        """Pipeline should initialize FilingSearchService internally."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        
        # Act
        from dart_fss_text.api.pipeline import DisclosurePipeline
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Assert
        assert hasattr(pipeline, '_filing_search')
        assert pipeline._filing_search is not None


class TestDisclosurePipelineInputNormalization:
    """Test input parameter normalization."""
    
    def test_normalize_single_stock_code_to_list(self):
        """Single stock_code should be converted to list."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act - we'll test this through download_and_parse
        # This test verifies the internal normalization logic
        stock_codes = "005930"
        normalized = pipeline._normalize_stock_codes(stock_codes)
        
        # Assert
        assert isinstance(normalized, list)
        assert normalized == ["005930"]
    
    def test_normalize_list_stock_codes_unchanged(self):
        """List of stock_codes should remain unchanged."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stock_codes = ["005930", "000660"]
        normalized = pipeline._normalize_stock_codes(stock_codes)
        
        # Assert
        assert normalized == ["005930", "000660"]
    
    def test_normalize_single_year_to_list(self):
        """Single year (int) should be converted to list."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        year = 2024
        normalized = pipeline._normalize_years(year)
        
        # Assert
        assert isinstance(normalized, list)
        assert normalized == [2024]
    
    def test_normalize_list_years_unchanged(self):
        """List of years should remain unchanged."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        years = [2023, 2024]
        normalized = pipeline._normalize_years(years)
        
        # Assert
        assert normalized == [2023, 2024]


class TestDisclosurePipelineWorkflow:
    """Test workflow orchestration (search → download → parse → store)."""
    
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline.download_document')
    @patch('dart_fss_text.api.pipeline.parse_xml_to_sections')
    def test_download_and_parse_coordinates_all_steps(
        self,
        mock_parse,
        mock_download,
        mock_filing_search_class
    ):
        """download_and_parse should coordinate all workflow steps."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        
        # Mock FilingSearchService
        mock_search_instance = Mock()
        mock_filing_search_class.return_value = mock_search_instance
        
        # Mock filing object
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.stock_code = "005930"
        mock_search_instance.search_filings.return_value = [mock_filing]
        
        # Mock download returns path
        mock_download.return_value = Path("/fake/path/20240312000736.xml")
        
        # Mock parse returns sections
        mock_sections = [
            Mock(spec=SectionDocument, section_code="010000"),
            Mock(spec=SectionDocument, section_code="020000")
        ]
        mock_parse.return_value = mock_sections
        
        # Mock storage insert
        mock_storage.insert_sections.return_value = None
        
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline.download_and_parse(
            stock_codes="005930",
            years=2024,
            report_type="A001"
        )
        
        # Assert - verify each step was called
        mock_search_instance.search_filings.assert_called_once()
        mock_download.assert_called_once_with(mock_filing)
        mock_parse.assert_called_once()
        mock_storage.insert_sections.assert_called_once_with(mock_sections)
        
        # Verify statistics
        assert stats['reports'] == 1
        assert stats['sections'] == 2
        assert stats['failed'] == 0
    
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline.download_document')
    @patch('dart_fss_text.api.pipeline.parse_xml_to_sections')
    def test_download_and_parse_handles_multiple_companies(
        self,
        mock_parse,
        mock_download,
        mock_filing_search_class
    ):
        """Pipeline should process multiple companies."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        
        # Mock FilingSearchService
        mock_search_instance = Mock()
        mock_filing_search_class.return_value = mock_search_instance
        
        # Mock filings for two companies (separate searches per company)
        mock_filing1 = Mock(rcept_no="20240312000736", stock_code="005930")
        mock_filing2 = Mock(rcept_no="20240312000737", stock_code="000660")
        # Pipeline searches once per company
        mock_search_instance.search_filings.side_effect = [
            [mock_filing1],  # First company
            [mock_filing2]   # Second company
        ]
        
        # Mock download
        mock_download.side_effect = [
            Path("/fake/20240312000736.xml"),
            Path("/fake/20240312000737.xml")
        ]
        
        # Mock parse
        mock_parse.side_effect = [
            [Mock(spec=SectionDocument), Mock(spec=SectionDocument)],
            [Mock(spec=SectionDocument), Mock(spec=SectionDocument), Mock(spec=SectionDocument)]
        ]
        
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline.download_and_parse(
            stock_codes=["005930", "000660"],
            years=2024,
            report_type="A001"
        )
        
        # Assert
        assert stats['reports'] == 2
        assert stats['sections'] == 5  # 2 + 3
        assert stats['failed'] == 0
        assert mock_download.call_count == 2
        assert mock_parse.call_count == 2
        # Verify search was called once per company
        assert mock_search_instance.search_filings.call_count == 2
    
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline.download_document')
    @patch('dart_fss_text.api.pipeline.parse_xml_to_sections')
    def test_download_and_parse_handles_multiple_years(
        self,
        mock_parse,
        mock_download,
        mock_filing_search_class
    ):
        """Pipeline should process multiple years."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        
        # Mock FilingSearchService
        mock_search_instance = Mock()
        mock_filing_search_class.return_value = mock_search_instance
        
        # Mock filings for two years (called twice)
        mock_search_instance.search_filings.side_effect = [
            [Mock(rcept_no="20230312000736")],  # 2023
            [Mock(rcept_no="20240312000736")]   # 2024
        ]
        
        mock_download.side_effect = [
            Path("/fake/2023.xml"),
            Path("/fake/2024.xml")
        ]
        
        mock_parse.side_effect = [
            [Mock(spec=SectionDocument)],
            [Mock(spec=SectionDocument)]
        ]
        
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline.download_and_parse(
            stock_codes="005930",
            years=[2023, 2024],
            report_type="A001"
        )
        
        # Assert
        assert stats['reports'] == 2
        assert mock_search_instance.search_filings.call_count == 2


class TestDisclosurePipelineErrorHandling:
    """Test error handling and failure tracking."""
    
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    def test_handles_search_failure_gracefully(self, mock_filing_search_class):
        """Pipeline should handle search failures without crashing."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        
        # Mock search to raise exception
        mock_search_instance = Mock()
        mock_filing_search_class.return_value = mock_search_instance
        mock_search_instance.search_filings.side_effect = Exception("Search API error")
        
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline.download_and_parse(
            stock_codes="005930",
            years=2024,
            report_type="A001"
        )
        
        # Assert - should not crash, should track failure
        assert stats['reports'] == 0
        assert stats['sections'] == 0
        assert stats['failed'] == 1
    
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline.download_document')
    def test_handles_download_failure_gracefully(
        self,
        mock_download,
        mock_filing_search_class
    ):
        """Pipeline should handle download failures without crashing."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        
        # Mock successful search
        mock_search_instance = Mock()
        mock_filing_search_class.return_value = mock_search_instance
        mock_filing = Mock(rcept_no="20240312000736")
        mock_search_instance.search_filings.return_value = [mock_filing]
        
        # Mock download to raise exception
        mock_download.side_effect = Exception("Network error")
        
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline.download_and_parse(
            stock_codes="005930",
            years=2024,
            report_type="A001"
        )
        
        # Assert
        assert stats['reports'] == 0
        assert stats['sections'] == 0
        assert stats['failed'] == 1
    
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline.download_document')
    @patch('dart_fss_text.api.pipeline.parse_xml_to_sections')
    def test_handles_parse_failure_gracefully(
        self,
        mock_parse,
        mock_download,
        mock_filing_search_class
    ):
        """Pipeline should handle parsing failures without crashing."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        
        # Mock successful search and download
        mock_search_instance = Mock()
        mock_filing_search_class.return_value = mock_search_instance
        mock_filing = Mock(rcept_no="20240312000736")
        mock_search_instance.search_filings.return_value = [mock_filing]
        mock_download.return_value = Path("/fake/path.xml")
        
        # Mock parse to raise exception
        mock_parse.side_effect = Exception("XML parsing error")
        
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline.download_and_parse(
            stock_codes="005930",
            years=2024,
            report_type="A001"
        )
        
        # Assert
        assert stats['reports'] == 0
        assert stats['sections'] == 0
        assert stats['failed'] == 1
    
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline.download_document')
    @patch('dart_fss_text.api.pipeline.parse_xml_to_sections')
    def test_handles_storage_failure_gracefully(
        self,
        mock_parse,
        mock_download,
        mock_filing_search_class
    ):
        """Pipeline should handle storage failures without crashing."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        
        # Mock successful search, download, parse
        mock_search_instance = Mock()
        mock_filing_search_class.return_value = mock_search_instance
        mock_filing = Mock(rcept_no="20240312000736")
        mock_search_instance.search_filings.return_value = [mock_filing]
        mock_download.return_value = Path("/fake/path.xml")
        mock_parse.return_value = [Mock(spec=SectionDocument)]
        
        # Mock storage to raise exception
        mock_storage.insert_sections.side_effect = Exception("MongoDB connection error")
        
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline.download_and_parse(
            stock_codes="005930",
            years=2024,
            report_type="A001"
        )
        
        # Assert
        assert stats['reports'] == 0
        assert stats['sections'] == 0
        assert stats['failed'] == 1
    
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline.download_document')
    @patch('dart_fss_text.api.pipeline.parse_xml_to_sections')
    def test_continues_processing_after_partial_failure(
        self,
        mock_parse,
        mock_download,
        mock_filing_search_class
    ):
        """Pipeline should continue processing remaining items after a failure."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        
        # Mock two filings
        mock_search_instance = Mock()
        mock_filing_search_class.return_value = mock_search_instance
        mock_filing1 = Mock(rcept_no="20240312000736")
        mock_filing2 = Mock(rcept_no="20240312000737")
        mock_search_instance.search_filings.return_value = [mock_filing1, mock_filing2]
        
        # First download fails, second succeeds
        mock_download.side_effect = [
            Exception("Network error"),
            Path("/fake/20240312000737.xml")
        ]
        
        # Second parse succeeds
        mock_parse.return_value = [Mock(spec=SectionDocument), Mock(spec=SectionDocument)]
        
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline.download_and_parse(
            stock_codes="005930",
            years=2024,
            report_type="A001"
        )
        
        # Assert - should process second filing despite first failure
        assert stats['reports'] == 1  # Only second succeeded
        assert stats['sections'] == 2
        assert stats['failed'] == 1  # First failed


class TestDownloadDocumentFunction:
    """Test the download_document() helper function."""
    
    @patch('dart_fss_text.api.pipeline.DocumentDownloadService')
    def test_download_document_success(self, mock_service_class):
        """download_document should use DocumentDownloadService and return path."""
        # Arrange
        from dart_fss_text.api.pipeline import download_document
        from dart_fss_text.services.document_download import DownloadResult
        
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"
        mock_filing.corp_code = "00126380"
        mock_filing.report_nm = "사업보고서"
        
        # Mock DocumentDownloadService
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        mock_result = DownloadResult(
            rcept_no="20240312000736",
            rcept_dt="20240312",
            stock_code="005930",
            year="2024",
            status='success',
            xml_files=[Path("/fake/20240312000736.xml")],
            main_xml_path=Path("/fake/20240312000736.xml")
        )
        mock_service.download_filing.return_value = mock_result
        
        # Act
        result = download_document(mock_filing)
        
        # Assert
        assert result == Path("/fake/20240312000736.xml")
        mock_service.download_filing.assert_called_once_with(
            rcept_no="20240312000736",
            rcept_dt="20240312",
            corp_code="00126380",
            report_nm="사업보고서"
        )
    
    @patch('dart_fss_text.api.pipeline.DocumentDownloadService')
    def test_download_document_existing_file(self, mock_service_class):
        """download_document should handle existing files correctly."""
        # Arrange
        from dart_fss_text.api.pipeline import download_document
        from dart_fss_text.services.document_download import DownloadResult
        
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"
        mock_filing.corp_code = "00126380"
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # File already exists
        mock_result = DownloadResult(
            rcept_no="20240312000736",
            rcept_dt="20240312",
            stock_code="005930",
            year="2024",
            status='existing',
            xml_files=[Path("/fake/20240312000736.xml")],
            main_xml_path=Path("/fake/20240312000736.xml")
        )
        mock_service.download_filing.return_value = mock_result
        
        # Act
        result = download_document(mock_filing)
        
        # Assert - should still return the path
        assert result == Path("/fake/20240312000736.xml")
    
    @patch('dart_fss_text.api.pipeline.DocumentDownloadService')
    def test_download_document_failed_status(self, mock_service_class):
        """download_document should raise error on failed status."""
        # Arrange
        from dart_fss_text.api.pipeline import download_document
        from dart_fss_text.services.document_download import DownloadResult
        
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"
        mock_filing.corp_code = "00126380"
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Download failed
        mock_result = DownloadResult(
            rcept_no="20240312000736",
            rcept_dt="20240312",
            stock_code="005930",
            year="2024",
            status='failed',
            xml_files=[],
            error="Network error"
        )
        mock_service.download_filing.return_value = mock_result
        
        # Act & Assert
        with pytest.raises(RuntimeError, match="Download failed: Network error"):
            download_document(mock_filing)
    
    @patch('dart_fss_text.api.pipeline.DocumentDownloadService')
    def test_download_document_no_main_xml(self, mock_service_class):
        """download_document should raise error if main_xml_path is None."""
        # Arrange
        from dart_fss_text.api.pipeline import download_document
        from dart_fss_text.services.document_download import DownloadResult
        
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"
        mock_filing.corp_code = "00126380"
        
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Main XML not found
        mock_result = DownloadResult(
            rcept_no="20240312000736",
            rcept_dt="20240312",
            stock_code="005930",
            year="2024",
            status='success',
            xml_files=[],
            main_xml_path=None
        )
        mock_service.download_filing.return_value = mock_result
        
        # Act & Assert
        with pytest.raises(FileNotFoundError, match="Main XML not found"):
            download_document(mock_filing)


class TestParseXmlToSectionsFunction:
    """Test the parse_xml_to_sections() helper function."""
    
    @patch('dart_fss_text.api.pipeline.get_toc_mapping')
    @patch('dart_fss_text.api.pipeline.build_section_index')
    @patch('dart_fss_text.api.pipeline.extract_section_by_code')
    def test_parse_xml_to_sections_basic(
        self,
        mock_extract,
        mock_build_index,
        mock_get_toc
    ):
        """parse_xml_to_sections should use existing parsers and convert to SectionDocument."""
        # Arrange
        from dart_fss_text.api.pipeline import parse_xml_to_sections
        from pathlib import Path
        
        xml_path = Path("/fake/20240312000736.xml")
        
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"
        mock_filing.corp_code = "00126380"
        mock_filing.stock_code = "005930"
        mock_filing.corp_name = "삼성전자"
        mock_filing.report_nm = "사업보고서"
        
        # Mock TOC mapping
        mock_get_toc.return_value = {"I. 회사의 개요": "010000"}
        
        # Mock section index with one section
        mock_build_index.return_value = {
            "3": {
                'level': 1,
                'title': 'I. 회사의 개요',
                'section_code': '010000',
                'atocid': '3',
                'element': Mock()
            }
        }
        
        # Mock extracted section content
        mock_extract.return_value = {
            'title': 'I. 회사의 개요',
            'section_code': '010000',
            'level': 1,
            'atocid': '3',
            'paragraphs': ['회사 개요 내용입니다.'],
            'tables': [],
            'subsections': []
        }
        
        # Act
        sections = parse_xml_to_sections(xml_path, mock_filing)
        
        # Assert
        assert len(sections) == 1
        section = sections[0]
        
        # Verify it's a SectionDocument
        from dart_fss_text.models.section import SectionDocument
        assert isinstance(section, SectionDocument)
        
        # Verify metadata from filing
        assert section.rcept_no == "20240312000736"
        assert section.stock_code == "005930"
        assert section.corp_name == "삼성전자"
        
        # Verify section data
        assert section.section_code == "010000"
        assert section.section_title == "I. 회사의 개요"
        assert section.atocid == "3"
        assert "회사 개요 내용입니다." in section.text
    
    @patch('dart_fss_text.api.pipeline.get_toc_mapping')
    @patch('dart_fss_text.api.pipeline.build_section_index')
    @patch('dart_fss_text.api.pipeline.extract_section_by_code')
    def test_parse_xml_to_sections_multiple_sections(
        self,
        mock_extract,
        mock_build_index,
        mock_get_toc
    ):
        """parse_xml_to_sections should handle multiple sections."""
        # Arrange
        from dart_fss_text.api.pipeline import parse_xml_to_sections
        from pathlib import Path
        
        xml_path = Path("/fake/20240312000736.xml")
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"
        mock_filing.corp_code = "00126380"
        mock_filing.stock_code = "005930"
        mock_filing.corp_name = "삼성전자"
        mock_filing.report_nm = "사업보고서"
        
        mock_get_toc.return_value = {
            "I. 회사의 개요": "010000",
            "II. 사업의 내용": "020000"
        }
        
        # Mock section index with two sections
        mock_build_index.return_value = {
            "3": {
                'level': 1,
                'title': 'I. 회사의 개요',
                'section_code': '010000',
                'atocid': '3',
                'element': Mock()
            },
            "4": {
                'level': 1,
                'title': 'II. 사업의 내용',
                'section_code': '020000',
                'atocid': '4',
                'element': Mock()
            }
        }
        
        # Mock extraction returns different content for each section
        mock_extract.side_effect = [
            {
                'title': 'I. 회사의 개요',
                'section_code': '010000',
                'level': 1,
                'atocid': '3',
                'paragraphs': ['회사 개요'],
                'tables': [],
                'subsections': []
            },
            {
                'title': 'II. 사업의 내용',
                'section_code': '020000',
                'level': 1,
                'atocid': '4',
                'paragraphs': ['사업 내용'],
                'tables': [],
                'subsections': []
            }
        ]
        
        # Act
        sections = parse_xml_to_sections(xml_path, mock_filing)
        
        # Assert
        assert len(sections) == 2
        assert sections[0].section_code == "010000"
        assert sections[1].section_code == "020000"
    
    @patch('dart_fss_text.api.pipeline.get_toc_mapping')
    @patch('dart_fss_text.api.pipeline.build_section_index')
    @patch('dart_fss_text.api.pipeline.extract_section_by_code')
    def test_parse_xml_to_sections_skips_unmapped_sections(
        self,
        mock_extract,
        mock_build_index,
        mock_get_toc
    ):
        """parse_xml_to_sections should skip sections without section_code."""
        # Arrange
        from dart_fss_text.api.pipeline import parse_xml_to_sections
        from pathlib import Path
        
        xml_path = Path("/fake/20240312000736.xml")
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"
        mock_filing.corp_code = "00126380"
        mock_filing.stock_code = "005930"
        mock_filing.corp_name = "삼성전자"
        mock_filing.report_nm = "사업보고서"
        
        mock_get_toc.return_value = {"I. 회사의 개요": "010000"}
        
        # Mock section index with one mapped and one unmapped section
        mock_build_index.return_value = {
            "3": {
                'level': 1,
                'title': 'I. 회사의 개요',
                'section_code': '010000',
                'atocid': '3',
                'element': Mock()
            },
            "4": {
                'level': 1,
                'title': 'Unknown Section',
                'section_code': None,  # Unmapped
                'atocid': '4',
                'element': Mock()
            }
        }
        
        mock_extract.return_value = {
            'title': 'I. 회사의 개요',
            'section_code': '010000',
            'level': 1,
            'atocid': '3',
            'paragraphs': ['회사 개요'],
            'tables': [],
            'subsections': []
        }
        
        # Act
        sections = parse_xml_to_sections(xml_path, mock_filing)
        
        # Assert - only mapped section returned
        assert len(sections) == 1
        assert sections[0].section_code == "010000"
    
    @patch('dart_fss_text.api.pipeline.get_toc_mapping')
    @patch('dart_fss_text.api.pipeline.build_section_index')
    @patch('dart_fss_text.api.pipeline.extract_section_by_code')
    def test_parse_xml_to_sections_with_tables(
        self,
        mock_extract,
        mock_build_index,
        mock_get_toc
    ):
        """parse_xml_to_sections should handle sections with tables."""
        # Arrange
        from dart_fss_text.api.pipeline import parse_xml_to_sections
        from pathlib import Path
        
        xml_path = Path("/fake/20240312000736.xml")
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"
        mock_filing.corp_code = "00126380"
        mock_filing.stock_code = "005930"
        mock_filing.corp_name = "삼성전자"
        mock_filing.report_nm = "사업보고서"
        
        mock_get_toc.return_value = {"II. 사업의 내용": "020000"}
        
        mock_build_index.return_value = {
            "4": {
                'level': 1,
                'title': 'II. 사업의 내용',
                'section_code': '020000',
                'atocid': '4',
                'element': Mock()
            }
        }
        
        # Mock extraction with tables
        mock_extract.return_value = {
            'title': 'II. 사업의 내용',
            'section_code': '020000',
            'level': 1,
            'atocid': '4',
            'paragraphs': ['사업 내용'],
            'tables': [
                {
                    'headers': ['구분', '매출액'],
                    'rows': [['DX', '100억']]
                }
            ],
            'subsections': []
        }
        
        # Act
        sections = parse_xml_to_sections(xml_path, mock_filing)
        
        # Assert
        assert len(sections) == 1
        section = sections[0]
        # Tables should be flattened to text
        assert 'DX' in section.text or '100억' in section.text
    
    @patch('dart_fss_text.api.pipeline.get_toc_mapping')
    @patch('dart_fss_text.api.pipeline.build_section_index')
    def test_parse_xml_to_sections_handles_parse_errors(
        self,
        mock_build_index,
        mock_get_toc
    ):
        """parse_xml_to_sections should handle XML parsing errors gracefully."""
        # Arrange
        from dart_fss_text.api.pipeline import parse_xml_to_sections
        from pathlib import Path
        
        xml_path = Path("/fake/malformed.xml")
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        
        mock_get_toc.return_value = {}
        
        # Mock build_section_index raises error
        mock_build_index.side_effect = Exception("XML parsing error")
        
        # Act & Assert - should raise the error
        with pytest.raises(Exception, match="XML parsing error"):
            parse_xml_to_sections(xml_path, mock_filing)
    
    @patch('dart_fss_text.api.pipeline.get_toc_mapping')
    @patch('dart_fss_text.api.pipeline.build_section_index')
    @patch('dart_fss_text.api.pipeline.extract_section_by_code')
    def test_parse_xml_to_sections_sets_year_from_rcept_dt(
        self,
        mock_extract,
        mock_build_index,
        mock_get_toc
    ):
        """parse_xml_to_sections should extract year from rcept_dt."""
        # Arrange
        from dart_fss_text.api.pipeline import parse_xml_to_sections
        from pathlib import Path
        
        xml_path = Path("/fake/20240312000736.xml")
        mock_filing = Mock()
        mock_filing.rcept_no = "20240312000736"
        mock_filing.rcept_dt = "20240312"  # Year should be 2024
        mock_filing.corp_code = "00126380"
        mock_filing.stock_code = "005930"
        mock_filing.corp_name = "삼성전자"
        mock_filing.report_nm = "사업보고서"
        
        mock_get_toc.return_value = {"I. 회사의 개요": "010000"}
        
        mock_build_index.return_value = {
            "3": {
                'level': 1,
                'title': 'I. 회사의 개요',
                'section_code': '010000',
                'atocid': '3',
                'element': Mock()
            }
        }
        
        mock_extract.return_value = {
            'title': 'I. 회사의 개요',
            'section_code': '010000',
            'level': 1,
            'atocid': '3',
            'paragraphs': ['내용'],
            'tables': [],
            'subsections': []
        }
        
        # Act
        sections = parse_xml_to_sections(xml_path, mock_filing)
        
        # Assert
        assert sections[0].year == "2024"
        assert sections[0].rcept_dt == "20240312"


class TestDisclosurePipelineStatistics:
    """Test statistics collection and reporting."""
    
    def test_statistics_dict_structure(self):
        """Statistics should have correct structure."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline._init_statistics()
        
        # Assert
        assert 'reports' in stats
        assert 'sections' in stats
        assert 'failed' in stats
        assert stats['reports'] == 0
        assert stats['sections'] == 0
        assert stats['failed'] == 0
    
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline.download_document')
    @patch('dart_fss_text.api.pipeline.parse_xml_to_sections')
    def test_statistics_counts_sections_correctly(
        self,
        mock_parse,
        mock_download,
        mock_filing_search_class
    ):
        """Statistics should correctly count total sections."""
        # Arrange
        mock_storage = Mock(spec=StorageService)
        from dart_fss_text.api.pipeline import DisclosurePipeline
        
        # Mock multiple filings with different section counts
        mock_search_instance = Mock()
        mock_filing_search_class.return_value = mock_search_instance
        mock_filing1 = Mock(rcept_no="20240312000736")
        mock_filing2 = Mock(rcept_no="20240312000737")
        mock_search_instance.search_filings.return_value = [mock_filing1, mock_filing2]
        
        mock_download.side_effect = [
            Path("/fake/1.xml"),
            Path("/fake/2.xml")
        ]
        
        # Different section counts
        mock_parse.side_effect = [
            [Mock(spec=SectionDocument)] * 10,  # 10 sections
            [Mock(spec=SectionDocument)] * 15   # 15 sections
        ]
        
        pipeline = DisclosurePipeline(storage_service=mock_storage)
        
        # Act
        stats = pipeline.download_and_parse(
            stock_codes="005930",
            years=2024,
            report_type="A001"
        )
        
        # Assert
        assert stats['reports'] == 2
        assert stats['sections'] == 25  # 10 + 15
        assert stats['failed'] == 0

