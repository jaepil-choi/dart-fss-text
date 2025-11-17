"""
Unit tests for BackfillPipelineParallel (parallel processing).

Tests parallel XML processing workflow with multiprocessing.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from dart_fss_text.api.pipeline_parallel import (
    BackfillPipelineParallel,
    _process_existing_xml_worker
)
from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.models.section import SectionDocument


@pytest.fixture
def mock_storage():
    """Create mock StorageService."""
    storage = Mock(spec=StorageService)
    storage.mongo_uri = "mongodb://localhost:27017"
    storage.database_name = "test_db"
    storage.collection_name = "test_collection"
    storage.collection = Mock()
    return storage


@pytest.fixture
def mongo_config():
    """MongoDB configuration for workers."""
    return {
        'uri': "mongodb://localhost:27017",
        'database': "test_db",
        'collection': "test_collection"
    }


@pytest.fixture
def sample_xml_info():
    """Sample XML file metadata for worker."""
    return {
        'xml_path': "/fake/path/2024/005930/20240312000736/20240312000736.xml",
        'rcept_no': "20240312000736",
        'rcept_dt': "20240312",
        'stock_code': "005930",
        'corp_code': "00126380",
        'corp_name': "삼성전자",
        'year': 2024
    }


@pytest.mark.unit
class TestWorkerFunction:
    """Tests for _process_existing_xml_worker()."""

    @patch('dart_fss_text.api.pipeline_parallel.StorageService')
    @patch('dart_fss_text.api.pipeline_parallel.parse_xml_to_sections')
    @patch('dart_fss_text.api.pipeline_parallel.Path')
    def test_worker_success(
        self,
        mock_path,
        mock_parse,
        mock_storage_class,
        sample_xml_info,
        mongo_config
    ):
        """Test worker successfully processes XML file."""
        # Setup mocks
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        # Mock parse_xml_to_sections to return sample sections
        mock_section = Mock(spec=SectionDocument)
        mock_parse.return_value = [mock_section, mock_section]  # 2 sections

        # Mock insert_sections
        mock_storage.insert_sections.return_value = {
            'success': True,
            'inserted_count': 2
        }

        # Execute worker
        result = _process_existing_xml_worker(
            xml_info=sample_xml_info,
            mongo_config=mongo_config,
            report_type="A001",
            target_section_codes=["020000"]
        )

        # Assertions
        assert result['success'] is True
        assert result['stock_code'] == "005930"
        assert result['year'] == 2024
        assert result['rcept_no'] == "20240312000736"
        assert result['stats']['reports'] == 1
        assert result['stats']['sections'] == 2
        assert result['stats']['failed'] == 0

        # Verify StorageService was created with config
        mock_storage_class.assert_called_once_with(
            mongo_uri=mongo_config['uri'],
            database=mongo_config['database'],
            collection=mongo_config['collection']
        )

        # Verify storage was closed
        mock_storage.close.assert_called_once()

    @patch('dart_fss_text.api.pipeline_parallel.StorageService')
    @patch('dart_fss_text.api.pipeline_parallel.parse_xml_to_sections')
    @patch('dart_fss_text.api.pipeline_parallel.Path')
    def test_worker_parse_failure(
        self,
        mock_path,
        mock_parse,
        mock_storage_class,
        sample_xml_info,
        mongo_config
    ):
        """Test worker handles parse failures gracefully."""
        # Setup mocks
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        # Mock parse_xml_to_sections to raise error
        mock_parse.side_effect = ValueError("XML parsing failed")

        # Execute worker
        result = _process_existing_xml_worker(
            xml_info=sample_xml_info,
            mongo_config=mongo_config,
            report_type="A001",
            target_section_codes=None
        )

        # Assertions
        assert result['success'] is False
        assert result['stats']['failed'] == 1
        assert result['stats']['reports'] == 0
        assert result['stats']['sections'] == 0

        # Verify failure info
        assert 'failure' in result
        assert result['failure']['error'] == "XML parsing failed"
        assert result['failure']['error_type'] == "ValueError"
        assert result['failure']['stock_code'] == "005930"

        # Verify storage was closed even on failure
        mock_storage.close.assert_called_once()


@pytest.mark.unit
class TestBackfillPipelineParallel:
    """Tests for BackfillPipelineParallel class."""

    @patch('dart_fss_text.api.pipeline.CorpListService')
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    def test_initialization(self, mock_filing_search, mock_corp_list, mock_storage):
        """Test pipeline initializes correctly."""
        pipeline = BackfillPipelineParallel(storage_service=mock_storage)

        assert pipeline._storage == mock_storage
        assert pipeline._filing_search is not None
        assert pipeline._corp_list_service is not None

    @patch('dart_fss_text.api.pipeline.CorpListService')
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    def test_backfill_only_required(self, mock_filing_search, mock_corp_list, mock_storage):
        """Test that backfill_only=True is enforced."""
        pipeline = BackfillPipelineParallel(storage_service=mock_storage)

        with pytest.raises(ValueError, match="only supports backfill_only=True"):
            pipeline.download_and_parse(
                years=[2024],
                backfill_only=False  # Should raise error
            )

    @patch('dart_fss_text.api.pipeline.CorpListService')
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    def test_years_parameter_required(self, mock_filing_search, mock_corp_list, mock_storage):
        """Test that years parameter is required."""
        pipeline = BackfillPipelineParallel(storage_service=mock_storage)

        with pytest.raises(ValueError, match="years parameter is required"):
            pipeline.download_and_parse(
                years=None,  # Should raise error
                backfill_only=True
            )

    @patch('dart_fss_text.api.pipeline.CorpListService')
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline_parallel.ProcessPoolExecutor')
    def test_empty_file_list(self, mock_executor, mock_filing_search, mock_corp_list, mock_storage):
        """Test behavior when no files to process."""
        # Setup mock storage
        mock_storage.collection.aggregate.return_value = []

        # Create pipeline
        pipeline = BackfillPipelineParallel(storage_service=mock_storage)

        # Mock file system to return no files
        with patch('dart_fss_text.api.pipeline_parallel.Path') as mock_path:
            mock_path.return_value.exists.return_value = False

            # Execute
            stats = pipeline.download_and_parse(
                stock_codes=["005930"],
                years=[2024],
                backfill_only=True
            )

        # Should return empty stats without calling executor
        assert stats['reports'] == 0
        assert stats['sections'] == 0
        assert stats['failed'] == 0
        assert stats['skipped'] == 0

        # Executor should not be used
        mock_executor.assert_not_called()

    @patch('dart_fss_text.api.pipeline.CorpListService')
    @patch('dart_fss_text.api.pipeline.FilingSearchService')
    @patch('dart_fss_text.api.pipeline_parallel.ProcessPoolExecutor')
    @patch('dart_fss_text.api.pipeline_parallel.Path')
    def test_parallel_processing_workflow(
        self,
        mock_path_class,
        mock_executor_class,
        mock_filing_search,
        mock_corp_list_class,
        mock_storage
    ):
        """Test full parallel processing workflow with mocked filesystem."""
        # Setup mock storage
        mock_storage.collection.aggregate.return_value = []
        mock_storage.collection.count_documents.return_value = 0

        # Setup mock CorpListService
        mock_corp_service = Mock()
        mock_corp_service.find_by_stock_code.return_value = {
            'stock_code': '005930',
            'corp_code': '00126380',
            'corp_name': '삼성전자'
        }
        mock_corp_list_class.return_value = mock_corp_service

        # Setup mock filesystem
        mock_data_dir = Mock()
        mock_xml_file = Mock()
        mock_xml_file.exists.return_value = True

        mock_rcept_dir = Mock()
        mock_rcept_dir.is_dir.return_value = True
        mock_rcept_dir.name = "20240312000736"
        # Enable path division on mock_rcept_dir
        mock_rcept_dir.__truediv__ = Mock(return_value=mock_xml_file)

        mock_data_dir.iterdir.return_value = [mock_rcept_dir]
        mock_data_dir.exists.return_value = True

        # Setup Path mocking - need to support path operations
        def path_init(path_str):
            mock_path = Mock()
            # Enable path division operator
            mock_path.__truediv__ = Mock(side_effect=lambda x: path_init(f"{path_str}/{x}"))
            mock_path.__str__ = Mock(return_value=str(path_str))

            if "2024/005930" in str(path_str):
                mock_path.exists.return_value = True
                mock_path.iterdir.return_value = [mock_rcept_dir]
                return mock_path
            elif "20240312000736.xml" in str(path_str):
                mock_path.exists.return_value = True
                return mock_path
            mock_path.exists.return_value = False
            return mock_path

        mock_path_class.side_effect = path_init

        # Setup mock executor
        mock_executor = Mock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor

        # Mock future results
        mock_future = Mock()
        mock_future.result.return_value = {
            'success': True,
            'stock_code': '005930',
            'year': 2024,
            'rcept_no': '20240312000736',
            'stats': {
                'reports': 1,
                'sections': 5,
                'failed': 0,
                'skipped': 0
            }
        }

        mock_executor.submit.return_value = mock_future

        # Mock as_completed
        with patch('dart_fss_text.api.pipeline_parallel.as_completed') as mock_as_completed:
            mock_as_completed.return_value = [mock_future]

            # Create pipeline
            pipeline = BackfillPipelineParallel(storage_service=mock_storage)

            # Execute
            stats = pipeline.download_and_parse(
                stock_codes=["005930"],
                years=[2024],
                max_workers=4,
                backfill_only=True
            )

        # Verify results
        assert stats['reports'] == 1
        assert stats['sections'] == 5
        assert stats['failed'] == 0

        # Verify executor was called with correct max_workers
        mock_executor_class.assert_called_once_with(max_workers=4)

        # Verify worker was submitted
        assert mock_executor.submit.called


@pytest.mark.integration
class TestBackfillPipelineParallelIntegration:
    """Integration tests with real filesystem (requires test data)."""

    @pytest.mark.skip(reason="Requires test XML files - run manually")
    def test_real_xml_processing(self, tmp_path):
        """
        Integration test with real XML files.

        To run this test:
        1. Place sample XML files in tmp_path structure
        2. Remove @pytest.mark.skip decorator
        3. Run: pytest tests/test_pipeline_parallel.py -k real_xml -v
        """
        # Create test directory structure
        year_dir = tmp_path / "2024" / "005930" / "20240312000736"
        year_dir.mkdir(parents=True)

        # Copy real XML file to test location
        # (This requires actual XML file for testing)

        # Create storage service
        storage = StorageService(
            mongo_uri="mongodb://localhost:27017",
            database="test_db",
            collection="test_collection"
        )

        try:
            # Create pipeline
            pipeline = BackfillPipelineParallel(storage_service=storage)

            # Execute with max_workers=2
            stats = pipeline.download_and_parse(
                stock_codes=["005930"],
                years=[2024],
                max_workers=2,
                base_dir=str(tmp_path),
                backfill_only=True
            )

            # Verify processing occurred
            assert stats['reports'] >= 0

        finally:
            storage.close()
