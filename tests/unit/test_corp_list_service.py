"""
Unit tests for CorpListService.

Tests CSV-backed corporation list storage and lookup functionality.
All tests use mocked dart-fss API to avoid network calls.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from dart_fss_text.services.corp_list_service import CorpListService
from dart_fss_text.config import get_app_config


@pytest.fixture
def mock_corp_list():
    """Create a mock CorpList with sample corps."""
    mock_corp_list = Mock()
    
    # Create sample corp objects
    samsung = Mock()
    samsung.to_dict.return_value = {
        'corp_code': '00126380',
        'corp_name': '삼성전자',
        'corp_eng_name': 'Samsung Electronics',
        'stock_code': '005930',
        'corp_cls': 'Y',
        'modify_date': '20240101'
    }
    
    sk_hynix = Mock()
    sk_hynix.to_dict.return_value = {
        'corp_code': '00118332',
        'corp_name': 'SK하이닉스',
        'corp_eng_name': 'SK Hynix',
        'stock_code': '000660',
        'corp_cls': 'Y',
        'modify_date': '20240101'
    }
    
    unlisted = Mock()
    unlisted.to_dict.return_value = {
        'corp_code': '99999999',
        'corp_name': '비상장회사',
        'corp_eng_name': 'Unlisted Corp',
        'stock_code': None,
        'corp_cls': None,
        'modify_date': '20240101'
    }
    
    mock_corp_list.corps = [samsung, sk_hynix, unlisted]
    mock_corp_list.find_by_stock_code = Mock(side_effect=lambda code: {
        '005930': samsung,
        '000660': sk_hynix
    }.get(code, None))
    
    return mock_corp_list


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset CorpListService singleton before each test."""
    CorpListService._instance = None
    CorpListService._initialized = False
    yield
    CorpListService._instance = None
    CorpListService._initialized = False


class TestInitialize:
    """Test initialize() method."""
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_initialize_creates_csv_file(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should create CSV file with correct timestamp format."""
        # Setup mocks
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        # Initialize
        service = CorpListService()
        csv_path = service.initialize()
        
        # Verify CSV file created
        assert Path(csv_path).exists()
        assert csv_path.startswith(str(tmp_path))
        assert 'corp_list_' in csv_path
        assert csv_path.endswith('.csv')
        
        # Verify timestamp format (YYYYMMDD_HHMMSS)
        filename = Path(csv_path).name
        timestamp_part = filename.replace('corp_list_', '').replace('.csv', '')
        assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS
        assert '_' in timestamp_part
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_initialize_saves_all_corps(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should save all corps to CSV."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        csv_path = service.initialize()
        
        # Load CSV and verify
        df = pd.read_csv(csv_path, encoding='utf-8')
        assert len(df) == 3  # samsung, sk_hynix, unlisted
        assert 'corp_code' in df.columns
        assert 'corp_name' in df.columns
        assert 'stock_code' in df.columns
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_initialize_caches_dataframe(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should cache DataFrame in memory."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        service.initialize()
        
        # Verify DataFrame is cached
        assert service._df is not None
        assert len(service._df) == 3
    
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_initialize_raises_without_api_key(self, mock_get_config):
        """Should raise ValueError if API key not set."""
        mock_config = Mock()
        mock_config.opendart_api_key = None
        mock_get_config.return_value = mock_config
        
        service = CorpListService()
        
        with pytest.raises(ValueError, match="OPENDART_API_KEY"):
            service.initialize()
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_initialize_idempotent(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should be idempotent - second call returns cached data."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        csv_path1 = service.initialize()
        
        # Second call should not call API again
        csv_path2 = service.initialize()
        
        assert csv_path1 == csv_path2
        assert mock_get_corp_list.call_count == 1  # Only called once


class TestFindByStockCode:
    """Test find_by_stock_code() method."""
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_find_by_stock_code_returns_corp_data(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should return dict with corp data for valid stock code."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        service.initialize()
        
        # Find Samsung
        corp_data = service.find_by_stock_code('005930')
        
        assert corp_data is not None
        assert corp_data['corp_code'] == '00126380'
        assert corp_data['corp_name'] == '삼성전자'
        assert corp_data['stock_code'] == '005930'
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_find_by_stock_code_returns_none_for_invalid(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should return None for non-existent stock code."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        service.initialize()
        
        result = service.find_by_stock_code('999999')
        assert result is None
    
    def test_find_by_stock_code_raises_if_not_initialized(self):
        """Should raise RuntimeError if not initialized."""
        service = CorpListService()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            service.find_by_stock_code('005930')


class TestFindByCorpCode:
    """Test find_by_corp_code() method."""
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_find_by_corp_code_returns_corp_data(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should return dict with corp data for valid corp code."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        service.initialize()
        
        # Find Samsung by corp_code
        corp_data = service.find_by_corp_code('00126380')
        
        assert corp_data is not None
        assert corp_data['corp_code'] == '00126380'
        assert corp_data['corp_name'] == '삼성전자'
        assert corp_data['stock_code'] == '005930'
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_find_by_corp_code_returns_none_for_invalid(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should return None for non-existent corp code."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        service.initialize()
        
        result = service.find_by_corp_code('99999999')
        assert result is None
    
    def test_find_by_corp_code_raises_if_not_initialized(self):
        """Should raise RuntimeError if not initialized."""
        service = CorpListService()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            service.find_by_corp_code('00126380')


class TestDelistedCompanies:
    """Test that delisted companies are included (critical fix)."""
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_find_by_stock_code_includes_delisted(self, mock_get_config, mock_get_corp_list, tmp_path):
        """Should include delisted companies (unlike dart-fss default)."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        # Create mock with delisted company
        mock_corp_list = Mock()
        delisted_corp = Mock()
        delisted_corp.to_dict.return_value = {
            'corp_code': '99999999',
            'corp_name': '상장폐지회사',
            'stock_code': '123456',  # Has stock_code but delisted
            'corp_cls': None,  # Missing corp_cls indicates delisted
            'modify_date': '20170630'
        }
        
        mock_corp_list.corps = [delisted_corp]
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        service.initialize()
        
        # Should find delisted company
        corp_data = service.find_by_stock_code('123456')
        
        assert corp_data is not None
        assert corp_data['corp_name'] == '상장폐지회사'
        assert corp_data['corp_cls'] is None  # Delisted indicator
        
        # Verify this is different from dart-fss default behavior
        # (dart-fss would exclude this with include_delisting=False)


class TestGetAll:
    """Test get_all() method."""
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_get_all_returns_dataframe(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should return DataFrame with all corps."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        service.initialize()
        
        df = service.get_all()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert 'corp_code' in df.columns
        assert 'corp_name' in df.columns
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_get_all_returns_copy(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should return a copy, not the original DataFrame."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        service.initialize()
        
        df1 = service.get_all()
        df2 = service.get_all()
        
        # Should be different objects (copies)
        assert df1 is not df2
    
    def test_get_all_raises_if_not_initialized(self):
        """Should raise RuntimeError if not initialized."""
        service = CorpListService()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            service.get_all()


class TestGetCorpList:
    """Test get_corp_list() method."""
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_get_corp_list_returns_cached_object(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should return cached CorpList object."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        service.initialize()
        
        corp_list = service.get_corp_list()
        
        assert corp_list is mock_corp_list
    
    def test_get_corp_list_raises_if_not_initialized(self):
        """Should raise RuntimeError if not initialized."""
        service = CorpListService()
        
        with pytest.raises(RuntimeError, match="not initialized"):
            service.get_corp_list()
    
    def test_get_corp_list_raises_if_loaded_from_csv(self, tmp_path):
        """Should raise RuntimeError if loaded from CSV (no Corp objects)."""
        # Create a CSV file
        csv_path = tmp_path / "corp_list_test.csv"
        df = pd.DataFrame([
            {'corp_code': '00126380', 'corp_name': '삼성전자', 'stock_code': '005930'}
        ])
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        service = CorpListService()
        service.load_from_csv(csv_path)
        
        with pytest.raises(RuntimeError, match="not available"):
            service.get_corp_list()


class TestLoadFromCsv:
    """Test load_from_csv() method."""
    
    def test_load_from_csv_loads_data(self, tmp_path):
        """Should load DataFrame from CSV file."""
        # Create CSV file
        csv_path = tmp_path / "corp_list_test.csv"
        df = pd.DataFrame([
            {'corp_code': '00126380', 'corp_name': '삼성전자', 'stock_code': '005930'},
            {'corp_code': '00118332', 'corp_name': 'SK하이닉스', 'stock_code': '000660'}
        ])
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        service = CorpListService()
        service.load_from_csv(csv_path)
        
        assert service._df is not None
        assert len(service._df) == 2
        assert service._initialized is True
    
    def test_load_from_csv_raises_if_file_not_found(self):
        """Should raise FileNotFoundError if CSV doesn't exist."""
        service = CorpListService()
        
        with pytest.raises(FileNotFoundError):
            service.load_from_csv(Path("nonexistent.csv"))


class TestGetLatestDbPath:
    """Test get_latest_db_path() method."""
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_get_latest_db_path_returns_path(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should return path to latest CSV file."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service = CorpListService()
        csv_path = service.initialize()
        
        latest_path = service.get_latest_db_path()
        
        assert latest_path == Path(csv_path)
    
    def test_get_latest_db_path_returns_none_if_not_initialized(self):
        """Should return None if not initialized."""
        service = CorpListService()
        
        assert service.get_latest_db_path() is None


class TestSingleton:
    """Test singleton pattern."""
    
    def test_singleton_returns_same_instance(self):
        """Should return same instance on multiple calls."""
        service1 = CorpListService()
        service2 = CorpListService()
        
        assert service1 is service2
    
    @patch('dart_fss_text.services.corp_list_service.dart.get_corp_list')
    @patch('dart_fss_text.services.corp_list_service.get_app_config')
    def test_singleton_shares_state(self, mock_get_config, mock_get_corp_list, mock_corp_list, tmp_path):
        """Should share state across instances."""
        mock_config = Mock()
        mock_config.opendart_api_key = 'test_key'
        mock_config.corp_list_db_dir = str(tmp_path)
        mock_get_config.return_value = mock_config
        
        mock_get_corp_list.return_value = mock_corp_list
        
        service1 = CorpListService()
        service1.initialize()
        
        service2 = CorpListService()
        
        # Both should have same DataFrame
        assert service2._df is not None
        assert service2._initialized is True
        assert service1._df is service2._df

