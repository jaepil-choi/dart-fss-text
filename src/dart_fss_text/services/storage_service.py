"""
MongoDB storage service for DART report sections.

Handles all MongoDB operations for storing and retrieving parsed sections:
- Insertion (bulk, upsert)
- Querying (by report, company, section code)
- Deletion
- Index management
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, ConnectionFailure, PyMongoError

from dart_fss_text.models import SectionDocument
from dart_fss_text.config import get_app_config


class StorageService:
    """
    MongoDB storage service for DART report sections.
    
    Provides methods for storing, retrieving, and managing parsed sections
    in MongoDB. Supports environment-based configuration and connection pooling.
    
    Usage:
        >>> service = StorageService()
        >>> result = service.insert_sections(documents)
        >>> sections = service.get_report_sections('20240312000736')
        >>> service.close()
    
    Context Manager:
        >>> with StorageService() as service:
        ...     service.insert_sections(documents)
    
    Environment Variables (via config facade):
        - MONGO_HOST: MongoDB host (default: localhost:27017)
        - DB_NAME: Database name (default: FS)
        - COLLECTION_NAME: Collection name (default: A001)
    """
    
    def __init__(
        self,
        mongo_uri: Optional[str] = None,
        database: Optional[str] = None,
        collection: Optional[str] = None
    ):
        """
        Initialize StorageService with MongoDB connection.
        
        Configuration is loaded via config facade (get_app_config()).
        Parameters take precedence over config values.
        
        Args:
            mongo_uri: MongoDB connection string (overrides config if provided)
            database: Database name (overrides config if provided)
            collection: Collection name (overrides config if provided)
        
        Raises:
            ConnectionFailure: If MongoDB connection fails
        
        Example:
            >>> # Use config defaults
            >>> service = StorageService()
            >>> 
            >>> # Override specific values
            >>> service = StorageService(database='test_db')
        """
        # Load configuration from config facade
        config = get_app_config()
        
        # Get configuration (priority: parameter > config > default)
        self.mongo_uri = mongo_uri or config.mongodb_uri
        self.database_name = database or config.mongodb_database
        self.collection_name = collection or config.mongodb_collection
        
        # Connect to MongoDB
        self.client = MongoClient(
            self.mongo_uri,
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )
        
        # Test connection
        self.client.admin.command('ping')
        
        # Get database and collection
        self.db = self.client[self.database_name]
        self.collection = self.db[self.collection_name]
    
    def insert_sections(self, documents: List[SectionDocument]) -> Dict[str, Any]:
        """
        Insert multiple section documents to MongoDB.
        
        Args:
            documents: List of SectionDocument instances
        
        Returns:
            Dictionary with:
                - success (bool): True if insertion succeeded
                - inserted_count (int): Number of documents inserted
                - error (str): Error message if failed (optional)
        
        Example:
            >>> result = service.insert_sections([doc1, doc2, doc3])
            >>> print(result)
            {'success': True, 'inserted_count': 3}
        """
        if not documents:
            return {
                'success': True,
                'inserted_count': 0
            }
        
        try:
            # Convert SectionDocument to dict
            mongo_docs = [doc.to_mongo_dict() for doc in documents]
            
            # Insert to MongoDB
            result = self.collection.insert_many(mongo_docs)
            
            return {
                'success': True,
                'inserted_count': len(result.inserted_ids)
            }
        
        except DuplicateKeyError as e:
            return {
                'success': False,
                'inserted_count': 0,
                'error': f"Duplicate key error: {str(e)}"
            }
        
        except PyMongoError as e:
            return {
                'success': False,
                'inserted_count': 0,
                'error': f"MongoDB error: {str(e)}"
            }
    
    def get_section(self, rcept_no: str, section_code: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific section by rcept_no and section_code.
        
        Args:
            rcept_no: Receipt number (14 digits)
            section_code: Section code (e.g., '020100')
        
        Returns:
            Section document dict if found, None otherwise
        
        Example:
            >>> section = service.get_section('20240312000736', '020100')
            >>> print(section['section_title'])
            '1. 사업의 개요'
        """
        return self.collection.find_one({
            'rcept_no': rcept_no,
            'section_code': section_code
        })
    
    def get_section_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a section by its composite document_id.
        
        Args:
            document_id: Composite ID in format '{rcept_no}_{section_code}'
        
        Returns:
            Section document dict if found, None otherwise
        
        Example:
            >>> section = service.get_section_by_id('20240312000736_020100')
        """
        return self.collection.find_one({
            'document_id': document_id
        })
    
    def get_report_sections(self, rcept_no: str) -> List[Dict[str, Any]]:
        """
        Retrieve all sections for a report, sorted by atocid.
        
        Args:
            rcept_no: Receipt number (14 digits)
        
        Returns:
            List of section documents sorted by atocid (document order)
        
        Example:
            >>> sections = service.get_report_sections('20240312000736')
            >>> print(f"Found {len(sections)} sections")
        """
        sections = list(self.collection.find({
            'rcept_no': rcept_no
        }))
        
        # Sort by atocid numerically (MongoDB sorts strings alphabetically)
        sections.sort(key=lambda x: int(x.get('atocid', 0)))
        
        return sections
    
    def delete_report(self, rcept_no: str) -> Dict[str, Any]:
        """
        Delete all sections of a report.
        
        Args:
            rcept_no: Receipt number (14 digits)
        
        Returns:
            Dictionary with:
                - success (bool): True if deletion succeeded
                - deleted_count (int): Number of documents deleted
        
        Example:
            >>> result = service.delete_report('20240312000736')
            >>> print(f"Deleted {result['deleted_count']} sections")
        """
        try:
            result = self.collection.delete_many({
                'rcept_no': rcept_no
            })
            
            return {
                'success': True,
                'deleted_count': result.deleted_count
            }
        
        except PyMongoError as e:
            return {
                'success': False,
                'deleted_count': 0,
                'error': f"MongoDB error: {str(e)}"
            }
    
    def upsert_sections(self, documents: List[SectionDocument]) -> Dict[str, Any]:
        """
        Insert or update sections (idempotent operation).
        
        Uses bulk_write with ReplaceOne operations to ensure idempotency.
        Re-parsing the same document will update existing sections.
        
        Args:
            documents: List of SectionDocument instances
        
        Returns:
            Dictionary with:
                - success (bool): True if operation succeeded
                - upserted_count (int): Number of new documents inserted
                - modified_count (int): Number of existing documents updated
        
        Example:
            >>> result = service.upsert_sections([doc1, doc2])
            >>> print(f"Upserted: {result['upserted_count']}, Modified: {result['modified_count']}")
        """
        if not documents:
            return {
                'success': True,
                'upserted_count': 0,
                'modified_count': 0
            }
        
        try:
            from pymongo import ReplaceOne
            
            # Build bulk operations
            operations = []
            for doc in documents:
                mongo_doc = doc.to_mongo_dict()
                operations.append(
                    ReplaceOne(
                        {'document_id': doc.document_id},
                        mongo_doc,
                        upsert=True
                    )
                )
            
            # Execute bulk write
            result = self.collection.bulk_write(operations)
            
            return {
                'success': True,
                'upserted_count': result.upserted_count,
                'modified_count': result.modified_count
            }
        
        except PyMongoError as e:
            return {
                'success': False,
                'upserted_count': 0,
                'modified_count': 0,
                'error': f"MongoDB error: {str(e)}"
            }
    
    def get_sections_by_company(
        self,
        stock_code: str,
        year: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all sections for a company, optionally filtered by year.
        
        Args:
            stock_code: Stock code (6 digits, e.g., '005930')
            year: Optional year filter (e.g., '2024')
        
        Returns:
            List of section documents
        
        Example:
            >>> sections = service.get_sections_by_company('005930', year='2024')
        """
        query = {'stock_code': stock_code}
        
        if year:
            query['year'] = year
        
        return list(self.collection.find(query))
    
    def get_sections_by_code(self, section_code: str) -> List[Dict[str, Any]]:
        """
        Retrieve specific section across all reports.
        
        Useful for comparing same section across companies or time.
        
        Args:
            section_code: Section code (e.g., '020000' for "II. 사업의 내용")
        
        Returns:
            List of section documents
        
        Example:
            >>> sections = service.get_sections_by_code('020000')
            >>> print(f"Found {len(sections)} business description sections")
        """
        return list(self.collection.find({
            'section_code': section_code
        }))
    
    def create_indexes(self) -> None:
        """
        Create recommended MongoDB indexes for query performance.
        
        Creates indexes on:
        - (rcept_no, section_code) - unique, for get_section()
        - (document_id) - unique, for get_section_by_id()
        - (stock_code, year) - for time-series queries
        - (section_code) - for cross-report section queries
        
        Should be called once during initial setup or deployment.
        
        Example:
            >>> service.create_indexes()
            >>> print("Indexes created")
        """
        # Composite index for report + section queries (unique)
        self.collection.create_index(
            [('rcept_no', ASCENDING), ('section_code', ASCENDING)],
            unique=True,
            name='idx_rcept_no_section_code'
        )
        
        # Document ID index (unique)
        self.collection.create_index(
            [('document_id', ASCENDING)],
            unique=True,
            name='idx_document_id'
        )
        
        # Company + year index for time-series queries
        self.collection.create_index(
            [('stock_code', ASCENDING), ('year', ASCENDING)],
            name='idx_stock_code_year'
        )
        
        # Section code index for cross-report queries
        self.collection.create_index(
            [('section_code', ASCENDING)],
            name='idx_section_code'
        )
    
    def close(self) -> None:
        """
        Close MongoDB connection.
        
        Should be called when service is no longer needed.
        Automatically called when using context manager.
        
        Example:
            >>> service = StorageService()
            >>> # ... use service ...
            >>> service.close()
        """
        if self.client:
            self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.close()
        return False  # Don't suppress exceptions

