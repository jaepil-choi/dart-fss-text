"""
Unit tests for StorageService.

Tests storage service logic with mocked MongoDB operations.
Integration tests with real MongoDB are in tests/integration/.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from typing import List

# Import will fail until we create the module - that's TDD!
from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.models import SectionDocument, create_document_id


class TestStorageServiceInitialization:
    """Test StorageService initialization and configuration."""
    
    def test_init_with_connection_string(self):
        """Should initialize with MongoDB connection string."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            service = StorageService(
                mongo_uri="mongodb://localhost:27017/",
                database="test_db",
                collection="test_collection"
            )
            
            assert service.database_name == "test_db"
            assert service.collection_name == "test_collection"
    
    def test_init_with_environment_variables(self):
        """Should load config from environment variables."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            with patch.dict('os.environ', {
                'MONGODB_URI': 'mongodb://testhost:27017/',
                'MONGODB_DATABASE': 'env_db',
                'MONGODB_COLLECTION': 'env_collection'
            }):
                service = StorageService()
                
                assert service.database_name == "env_db"
                assert service.collection_name == "env_collection"
    
    def test_init_with_defaults(self):
        """Should use default values when no config provided."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            with patch.dict('os.environ', {}, clear=True):
                service = StorageService()
                
                assert service.database_name == "dart_fss_text"
                assert service.collection_name == "A001"


class TestInsertSections:
    """Test inserting section documents to MongoDB."""
    
    @pytest.fixture
    def mock_collection(self):
        """Mock MongoDB collection."""
        return MagicMock()
    
    @pytest.fixture
    def storage_service(self, mock_collection):
        """StorageService with mocked collection."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            service = StorageService()
            service.collection = mock_collection
            return service
    
    @pytest.fixture
    def sample_documents(self) -> List[SectionDocument]:
        """Sample SectionDocument instances."""
        return [
            SectionDocument(
                document_id="20240312000736_020100",
                rcept_no="20240312000736",
                rcept_dt="20240312",
                year="2024",
                corp_code="00126380",
                corp_name="삼성전자",
                stock_code="005930",
                report_type="A001",
                report_name="사업보고서",
                section_code="020100",
                section_title="1. 사업의 개요",
                level=2,
                atocid="10",
                parent_section_code="020000",
                parent_section_title="II. 사업의 내용",
                section_path=["020000", "020100"],
                text="당사는 본사를 거점으로...",
                char_count=2092,
                word_count=364,
                parsed_at=datetime(2024, 10, 4, 12, 0, 0),
                parser_version="1.0.0"
            ),
            SectionDocument(
                document_id="20240312000736_020200",
                rcept_no="20240312000736",
                rcept_dt="20240312",
                year="2024",
                corp_code="00126380",
                corp_name="삼성전자",
                stock_code="005930",
                report_type="A001",
                report_name="사업보고서",
                section_code="020200",
                section_title="2. 주요 제품 및 서비스",
                level=2,
                atocid="11",
                parent_section_code="020000",
                parent_section_title="II. 사업의 내용",
                section_path=["020000", "020200"],
                text="주요 제품은...",
                char_count=637,
                word_count=131,
                parsed_at=datetime(2024, 10, 4, 12, 0, 0),
                parser_version="1.0.0"
            )
        ]
    
    def test_insert_sections_success(self, storage_service, mock_collection, sample_documents):
        """Should insert multiple sections successfully."""
        # Mock successful insert
        mock_result = Mock()
        mock_result.inserted_ids = ['id1', 'id2']
        mock_collection.insert_many.return_value = mock_result
        
        # Insert sections
        result = storage_service.insert_sections(sample_documents)
        
        # Verify
        assert result['inserted_count'] == 2
        assert result['success'] is True
        mock_collection.insert_many.assert_called_once()
    
    def test_insert_sections_empty_list(self, storage_service, mock_collection):
        """Should handle empty document list gracefully."""
        result = storage_service.insert_sections([])
        
        assert result['inserted_count'] == 0
        assert result['success'] is True
        mock_collection.insert_many.assert_not_called()
    
    def test_insert_sections_with_duplicate_document_id(self, storage_service, mock_collection, sample_documents):
        """Should handle duplicate document_id errors."""
        from pymongo.errors import DuplicateKeyError
        
        # Mock duplicate key error
        mock_collection.insert_many.side_effect = DuplicateKeyError("E11000 duplicate key error")
        
        result = storage_service.insert_sections(sample_documents)
        
        assert result['success'] is False
        assert 'duplicate' in result['error'].lower()
    
    def test_insert_sections_converts_to_dict(self, storage_service, mock_collection, sample_documents):
        """Should convert SectionDocument to dict before insertion."""
        mock_result = Mock()
        mock_result.inserted_ids = ['id1', 'id2']
        mock_collection.insert_many.return_value = mock_result
        
        storage_service.insert_sections(sample_documents)
        
        # Verify insert_many was called with list of dicts
        call_args = mock_collection.insert_many.call_args[0][0]
        assert isinstance(call_args, list)
        assert all(isinstance(doc, dict) for doc in call_args)
        assert call_args[0]['document_id'] == "20240312000736_020100"


class TestGetSection:
    """Test retrieving single section from MongoDB."""
    
    @pytest.fixture
    def storage_service(self):
        """StorageService with mocked collection."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            service = StorageService()
            service.collection = MagicMock()
            return service
    
    def test_get_section_found(self, storage_service):
        """Should return section when found."""
        # Mock find_one result
        storage_service.collection.find_one.return_value = {
            'document_id': '20240312000736_020100',
            'rcept_no': '20240312000736',
            'section_code': '020100',
            'section_title': '1. 사업의 개요',
            'text': '당사는...',
            'char_count': 2092,
            'word_count': 364
        }
        
        section = storage_service.get_section('20240312000736', '020100')
        
        assert section is not None
        assert section['document_id'] == '20240312000736_020100'
        assert section['section_code'] == '020100'
        storage_service.collection.find_one.assert_called_once_with({
            'rcept_no': '20240312000736',
            'section_code': '020100'
        })
    
    def test_get_section_not_found(self, storage_service):
        """Should return None when section not found."""
        storage_service.collection.find_one.return_value = None
        
        section = storage_service.get_section('99999999999999', '999999')
        
        assert section is None
    
    def test_get_section_by_document_id(self, storage_service):
        """Should retrieve section by composite document_id."""
        storage_service.collection.find_one.return_value = {
            'document_id': '20240312000736_020100',
            'section_title': '1. 사업의 개요'
        }
        
        section = storage_service.get_section_by_id('20240312000736_020100')
        
        assert section is not None
        storage_service.collection.find_one.assert_called_once_with({
            'document_id': '20240312000736_020100'
        })


class TestGetReportSections:
    """Test retrieving all sections of a report."""
    
    @pytest.fixture
    def storage_service(self):
        """StorageService with mocked collection."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            service = StorageService()
            service.collection = MagicMock()
            return service
    
    def test_get_report_sections_found(self, storage_service):
        """Should return all sections for a report."""
        mock_data = [
            {'document_id': '20240312000736_020100', 'section_code': '020100', 'atocid': '1'},
            {'document_id': '20240312000736_020200', 'section_code': '020200', 'atocid': '2'},
            {'document_id': '20240312000736_010000', 'section_code': '010000', 'atocid': '3'}
        ]
        storage_service.collection.find.return_value = mock_data
        
        sections = storage_service.get_report_sections('20240312000736')
        
        assert len(sections) == 3
        assert sections[0]['section_code'] == '020100'
        storage_service.collection.find.assert_called_once_with({
            'rcept_no': '20240312000736'
        })
    
    def test_get_report_sections_not_found(self, storage_service):
        """Should return empty list when no sections found."""
        storage_service.collection.find.return_value = []
        
        sections = storage_service.get_report_sections('99999999999999')
        
        assert sections == []
    
    def test_get_report_sections_sorted_by_atocid(self, storage_service):
        """Should sort sections by atocid numerically."""
        # Mock unsorted data
        mock_data = [
            {'atocid': '11', 'section_code': 'B'},
            {'atocid': '3', 'section_code': 'A'},
            {'atocid': '10', 'section_code': 'C'}
        ]
        storage_service.collection.find.return_value = mock_data
        
        sections = storage_service.get_report_sections('20240312000736')
        
        # Should be sorted numerically: 3, 10, 11
        assert sections[0]['atocid'] == '3'
        assert sections[1]['atocid'] == '10'
        assert sections[2]['atocid'] == '11'


class TestDeleteReport:
    """Test deleting all sections of a report."""
    
    @pytest.fixture
    def storage_service(self):
        """StorageService with mocked collection."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            service = StorageService()
            service.collection = MagicMock()
            return service
    
    def test_delete_report_success(self, storage_service):
        """Should delete all sections of a report."""
        mock_result = Mock()
        mock_result.deleted_count = 53
        storage_service.collection.delete_many.return_value = mock_result
        
        result = storage_service.delete_report('20240312000736')
        
        assert result['deleted_count'] == 53
        assert result['success'] is True
        storage_service.collection.delete_many.assert_called_once_with({
            'rcept_no': '20240312000736'
        })
    
    def test_delete_report_not_found(self, storage_service):
        """Should handle deletion of non-existent report."""
        mock_result = Mock()
        mock_result.deleted_count = 0
        storage_service.collection.delete_many.return_value = mock_result
        
        result = storage_service.delete_report('99999999999999')
        
        assert result['deleted_count'] == 0
        assert result['success'] is True


class TestUpsertSections:
    """Test upsert (insert or update) functionality."""
    
    @pytest.fixture
    def storage_service(self):
        """StorageService with mocked collection."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            service = StorageService()
            service.collection = MagicMock()
            return service
    
    def test_upsert_sections_new_documents(self, storage_service):
        """Should insert new documents when not existing."""
        mock_result = Mock()
        mock_result.upserted_count = 2
        mock_result.modified_count = 0
        storage_service.collection.bulk_write = Mock(return_value=mock_result)
        
        documents = [
            SectionDocument(
                document_id="20240312000736_020100",
                rcept_no="20240312000736",
                rcept_dt="20240312",
                year="2024",
                corp_code="00126380",
                corp_name="삼성전자",
                stock_code="005930",
                report_type="A001",
                report_name="사업보고서",
                section_code="020100",
                section_title="1. 사업의 개요",
                level=2,
                atocid="10",
                parent_section_code="020000",
                section_path=["020000", "020100"],
                text="New text",
                char_count=100,
                word_count=20,
                parsed_at=datetime.now(),
                parser_version="1.0.0"
            )
        ]
        
        result = storage_service.upsert_sections(documents)
        
        assert result['success'] is True
        assert result['upserted_count'] == 2


class TestConnectionManagement:
    """Test MongoDB connection lifecycle."""
    
    def test_close_connection(self):
        """Should close MongoDB connection."""
        with patch('dart_fss_text.services.storage_service.MongoClient') as mock_client:
            service = StorageService()
            service.close()
            
            mock_client.return_value.close.assert_called_once()
    
    def test_context_manager_support(self):
        """Should support context manager protocol."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            with StorageService() as service:
                assert service is not None
            
            # Connection should be closed after exiting context


class TestQueryHelpers:
    """Test helper methods for querying sections."""
    
    @pytest.fixture
    def storage_service(self):
        """StorageService with mocked collection."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            service = StorageService()
            service.collection = MagicMock()
            return service
    
    def test_get_sections_by_company(self, storage_service):
        """Should retrieve all sections for a company."""
        storage_service.collection.find.return_value = []
        
        storage_service.get_sections_by_company('005930')
        
        storage_service.collection.find.assert_called_once_with({
            'stock_code': '005930'
        })
    
    def test_get_sections_by_company_and_year(self, storage_service):
        """Should retrieve sections for company in specific year."""
        storage_service.collection.find.return_value = []
        
        storage_service.get_sections_by_company('005930', year='2024')
        
        storage_service.collection.find.assert_called_once_with({
            'stock_code': '005930',
            'year': '2024'
        })
    
    def test_get_section_by_code_across_reports(self, storage_service):
        """Should retrieve specific section across all reports."""
        storage_service.collection.find.return_value = []
        
        storage_service.get_sections_by_code('020000')
        
        storage_service.collection.find.assert_called_once_with({
            'section_code': '020000'
        })


class TestErrorHandling:
    """Test error handling in storage operations."""
    
    @pytest.fixture
    def storage_service(self):
        """StorageService with mocked collection."""
        with patch('dart_fss_text.services.storage_service.MongoClient'):
            service = StorageService()
            service.collection = MagicMock()
            return service
    
    def test_handles_connection_failure(self):
        """Should handle MongoDB connection failures gracefully."""
        from pymongo.errors import ConnectionFailure
        
        with patch('dart_fss_text.services.storage_service.MongoClient') as mock_client:
            mock_client.side_effect = ConnectionFailure("Connection failed")
            
            with pytest.raises(ConnectionFailure):
                StorageService()
    
    def test_handles_invalid_documents(self, storage_service):
        """Should validate documents before insertion."""
        invalid_docs = [
            {'invalid': 'document'}  # Not a SectionDocument
        ]
        
        with pytest.raises((TypeError, AttributeError)):
            storage_service.insert_sections(invalid_docs)

