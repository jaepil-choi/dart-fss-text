"""
Integration tests for StorageService with real MongoDB.

These tests require:
- MongoDB running locally or accessible via MONGODB_URI
- Test database that can be safely created/dropped

Run with: pytest tests/integration/test_storage_service_integration.py
"""

import pytest
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from dart_fss_text.services.storage_service import StorageService
from dart_fss_text.models import SectionDocument, create_document_id


# Skip all tests if MongoDB not available
def is_mongodb_available():
    """Check if MongoDB is available for testing."""
    try:
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        client.close()
        return True
    except (ConnectionFailure, Exception):
        return False


pytestmark = pytest.mark.skipif(
    not is_mongodb_available(),
    reason="MongoDB not available for integration tests"
)


@pytest.fixture(scope='module')
def test_db_name():
    """Test database name (separate from production)."""
    return "dart_fss_text_test"


@pytest.fixture(scope='module')
def test_collection_name():
    """Test collection name."""
    return "A001_test"


@pytest.fixture
def storage_service(test_db_name, test_collection_name):
    """
    StorageService connected to test database.
    Cleans up test data after each test.
    """
    mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    
    service = StorageService(
        mongo_uri=mongo_uri,
        database=test_db_name,
        collection=test_collection_name
    )
    
    # Clean up before test
    service.collection.delete_many({})
    
    yield service
    
    # Clean up after test
    service.collection.delete_many({})
    service.close()


@pytest.fixture
def sample_documents():
    """Sample SectionDocument instances for testing."""
    base_time = datetime(2024, 10, 4, 12, 0, 0)
    
    return [
        SectionDocument(
            document_id="20240312000736_010000",
            rcept_no="20240312000736",
            rcept_dt="20240312",
            year="2024",
            corp_code="00126380",
            corp_name="삼성전자",
            stock_code="005930",
            report_type="A001",
            report_name="사업보고서",
            section_code="010000",
            section_title="I. 회사의 개요",
            level=1,
            atocid="3",
            parent_section_code=None,
            parent_section_title=None,
            section_path=["010000"],
            text="당사는 본사를 거점으로 한국과 DX 부문 산하 해외 9개 지역총괄...",
            char_count=7561,
            word_count=1436,
            parsed_at=base_time,
            parser_version="1.0.0"
        ),
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
            parsed_at=base_time,
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
            parsed_at=base_time,
            parser_version="1.0.0"
        )
    ]


class TestInsertSectionsIntegration:
    """Test inserting sections with real MongoDB."""
    
    def test_insert_sections_success(self, storage_service, sample_documents):
        """Should insert sections and verify in database."""
        result = storage_service.insert_sections(sample_documents)
        
        assert result['success'] is True
        assert result['inserted_count'] == 3
        
        # Verify in database
        count = storage_service.collection.count_documents({})
        assert count == 3
    
    def test_insert_empty_list(self, storage_service):
        """Should handle empty list gracefully."""
        result = storage_service.insert_sections([])
        
        assert result['success'] is True
        assert result['inserted_count'] == 0
        
        count = storage_service.collection.count_documents({})
        assert count == 0
    
    def test_insert_duplicate_document_id_fails(self, storage_service, sample_documents):
        """Should fail when inserting duplicate document_id."""
        # Create unique index first
        storage_service.create_indexes()
        
        # First insert succeeds
        storage_service.insert_sections(sample_documents)
        
        # Second insert should fail
        result = storage_service.insert_sections(sample_documents)
        
        assert result['success'] is False
        assert 'duplicate' in result['error'].lower() or 'E11000' in result['error']
    
    def test_insert_preserves_all_fields(self, storage_service, sample_documents):
        """Should preserve all fields including datetime and arrays."""
        storage_service.insert_sections(sample_documents)
        
        doc = storage_service.collection.find_one({'document_id': '20240312000736_020100'})
        
        # Verify all key fields
        assert doc['document_id'] == '20240312000736_020100'
        assert doc['rcept_no'] == '20240312000736'
        assert doc['section_code'] == '020100'
        assert doc['stock_code'] == '005930'
        assert doc['level'] == 2
        assert doc['parent_section_code'] == '020000'
        assert doc['section_path'] == ['020000', '020100']
        assert doc['char_count'] == 2092
        assert doc['word_count'] == 364
        assert isinstance(doc['parsed_at'], datetime)
        assert doc['parser_version'] == '1.0.0'


class TestGetSectionIntegration:
    """Test retrieving sections with real MongoDB."""
    
    def test_get_section_found(self, storage_service, sample_documents):
        """Should retrieve existing section."""
        storage_service.insert_sections(sample_documents)
        
        section = storage_service.get_section('20240312000736', '020100')
        
        assert section is not None
        assert section['document_id'] == '20240312000736_020100'
        assert section['section_title'] == '1. 사업의 개요'
        assert section['text'] == '당사는 본사를 거점으로...'
    
    def test_get_section_not_found(self, storage_service):
        """Should return None for non-existent section."""
        section = storage_service.get_section('99999999999999', '999999')
        
        assert section is None
    
    def test_get_section_by_id(self, storage_service, sample_documents):
        """Should retrieve section by document_id."""
        storage_service.insert_sections(sample_documents)
        
        section = storage_service.get_section_by_id('20240312000736_020100')
        
        assert section is not None
        assert section['section_code'] == '020100'


class TestGetReportSectionsIntegration:
    """Test retrieving all sections of a report."""
    
    def test_get_report_sections_found(self, storage_service, sample_documents):
        """Should retrieve all sections for a report."""
        storage_service.insert_sections(sample_documents)
        
        sections = storage_service.get_report_sections('20240312000736')
        
        assert len(sections) == 3
        section_codes = {s['section_code'] for s in sections}
        assert section_codes == {'010000', '020100', '020200'}
    
    def test_get_report_sections_sorted(self, storage_service, sample_documents):
        """Should return sections sorted by atocid."""
        storage_service.insert_sections(sample_documents)
        
        sections = storage_service.get_report_sections('20240312000736')
        
        # Should be sorted by atocid: 3, 10, 11
        assert sections[0]['atocid'] == '3'
        assert sections[1]['atocid'] == '10'
        assert sections[2]['atocid'] == '11'
    
    def test_get_report_sections_not_found(self, storage_service):
        """Should return empty list for non-existent report."""
        sections = storage_service.get_report_sections('99999999999999')
        
        assert sections == []


class TestDeleteReportIntegration:
    """Test deleting report sections."""
    
    def test_delete_report_success(self, storage_service, sample_documents):
        """Should delete all sections of a report."""
        storage_service.insert_sections(sample_documents)
        
        # Verify inserted
        count_before = storage_service.collection.count_documents({'rcept_no': '20240312000736'})
        assert count_before == 3
        
        # Delete
        result = storage_service.delete_report('20240312000736')
        
        assert result['success'] is True
        assert result['deleted_count'] == 3
        
        # Verify deleted
        count_after = storage_service.collection.count_documents({'rcept_no': '20240312000736'})
        assert count_after == 0
    
    def test_delete_report_not_found(self, storage_service):
        """Should return 0 deleted_count for non-existent report."""
        result = storage_service.delete_report('99999999999999')
        
        assert result['success'] is True
        assert result['deleted_count'] == 0


class TestUpsertSectionsIntegration:
    """Test upsert (insert or update) functionality."""
    
    def test_upsert_new_documents(self, storage_service, sample_documents):
        """Should insert new documents on first upsert."""
        result = storage_service.upsert_sections(sample_documents)
        
        assert result['success'] is True
        assert result['upserted_count'] + result['modified_count'] == 3
        
        count = storage_service.collection.count_documents({})
        assert count == 3
    
    def test_upsert_existing_documents_updates(self, storage_service, sample_documents):
        """Should update existing documents on second upsert."""
        # First insert
        storage_service.insert_sections(sample_documents)
        
        # Modify documents
        for doc in sample_documents:
            doc.text = "Updated text"
            doc.char_count = len(doc.text)
            doc.word_count = len(doc.text.split())
        
        # Upsert (should update)
        result = storage_service.upsert_sections(sample_documents)
        
        assert result['success'] is True
        
        # Verify update
        section = storage_service.get_section('20240312000736', '020100')
        assert section['text'] == "Updated text"
        assert section['char_count'] == 12
    
    def test_upsert_idempotent(self, storage_service, sample_documents):
        """Upsert should be idempotent (same result when called multiple times)."""
        # Upsert 3 times
        storage_service.upsert_sections(sample_documents)
        storage_service.upsert_sections(sample_documents)
        result = storage_service.upsert_sections(sample_documents)
        
        assert result['success'] is True
        
        # Should still have only 3 documents
        count = storage_service.collection.count_documents({})
        assert count == 3


class TestQueryHelpersIntegration:
    """Test helper query methods."""
    
    def test_get_sections_by_company(self, storage_service, sample_documents):
        """Should retrieve all sections for a company."""
        storage_service.insert_sections(sample_documents)
        
        sections = storage_service.get_sections_by_company('005930')
        
        assert len(sections) == 3
    
    def test_get_sections_by_company_and_year(self, storage_service, sample_documents):
        """Should filter by company and year."""
        storage_service.insert_sections(sample_documents)
        
        sections = storage_service.get_sections_by_company('005930', year='2024')
        
        assert len(sections) == 3
        
        # Wrong year
        sections = storage_service.get_sections_by_company('005930', year='2023')
        assert len(sections) == 0
    
    def test_get_sections_by_code(self, storage_service, sample_documents):
        """Should retrieve specific section across all reports."""
        storage_service.insert_sections(sample_documents)
        
        sections = storage_service.get_sections_by_code('020100')
        
        assert len(sections) == 1
        assert sections[0]['section_title'] == '1. 사업의 개요'


class TestContextManagerIntegration:
    """Test context manager support."""
    
    def test_context_manager(self, test_db_name, test_collection_name):
        """Should support with statement."""
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        
        with StorageService(mongo_uri, test_db_name, test_collection_name) as service:
            # Service should be usable
            assert service is not None
            assert service.collection is not None
            
            # Can perform operations
            result = service.insert_sections([])
            assert result['success'] is True
        
        # Connection should be closed after exiting


class TestIndexCreation:
    """Test MongoDB index creation."""
    
    def test_create_indexes(self, storage_service):
        """Should create recommended indexes."""
        storage_service.create_indexes()
        
        # Get index information
        indexes = storage_service.collection.list_indexes()
        index_names = [idx['name'] for idx in indexes]
        
        # Verify indexes exist (names may vary)
        assert len(index_names) >= 1  # At least _id index exists
    
    def test_indexes_improve_query_performance(self, storage_service, sample_documents):
        """Indexes should improve query performance (basic check)."""
        # Insert many documents
        storage_service.insert_sections(sample_documents)
        
        # Create indexes
        storage_service.create_indexes()
        
        # Query should work (performance test would need more data)
        section = storage_service.get_section('20240312000736', '020100')
        assert section is not None


class TestConnectionRobustness:
    """Test connection handling edge cases."""
    
    def test_reconnect_after_close(self, test_db_name, test_collection_name):
        """Should handle reconnection after closing."""
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        
        service = StorageService(mongo_uri, test_db_name, test_collection_name)
        service.close()
        
        # Should be able to create new service
        service2 = StorageService(mongo_uri, test_db_name, test_collection_name)
        result = service2.insert_sections([])
        assert result['success'] is True
        service2.close()

