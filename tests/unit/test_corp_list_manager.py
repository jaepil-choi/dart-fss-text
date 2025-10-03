"""
Unit tests for CorpListManager (Phase 0).

Tests the corporation list caching and lookup functionality that enables
stock_code → corp_code conversion for the discovery pipeline.

Validated against Experiment 5:
- 3,901 listed corporations successfully cached
- 0 duplicates in stock_code or corp_code
- 70.9% have complete metadata (corp_cls, sector, product)
- Schema: 11 columns from DART API
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
import tempfile
import shutil

from dart_fss_text.services.corp_list_manager import CorpListManager


class TestCorpListManagerInitialization:
    """Test CorpListManager initialization and configuration."""
    
    def test_default_cache_path(self):
        """Should use default cache path data/corp_list.csv."""
        manager = CorpListManager()
        assert manager._cache_path == Path("data/corp_list.csv")
    
    def test_custom_cache_path(self):
        """Should accept custom cache path."""
        custom_path = Path("custom/path/corps.csv")
        manager = CorpListManager(cache_path=custom_path)
        assert manager._cache_path == custom_path
    
    def test_initial_state_empty(self):
        """Should initialize with empty lookup dict."""
        manager = CorpListManager()
        assert manager._lookup == {}
        assert manager._corp_list is None


class TestCorpListManagerLoadFromCache:
    """Test loading corporation list from CSV cache."""
    
    @pytest.fixture
    def temp_cache_file(self):
        """Create temporary CSV cache file with sample data."""
        temp_dir = Path(tempfile.mkdtemp())
        cache_file = temp_dir / "corp_list.csv"
        
        # Create sample data matching Experiment 5 schema
        sample_data = {
            'corp_code': ['00126380', '00164779', '00259148'],
            'corp_name': ['삼성전자', 'SK하이닉스', 'LG전자'],
            'corp_eng_name': ['Samsung Electronics Co., Ltd.', 'SK hynix Inc.', 'LG Electronics Inc.'],
            'stock_code': ['005930', '000660', '066570'],
            'modify_date': ['20240101', '20240101', '20240101'],
            'corp_cls': ['Y', 'Y', 'Y'],
            'market_type': ['stockMkt', 'stockMkt', 'stockMkt'],
            'sector': ['전기전자', '전기전자', '전기전자'],
            'product': ['반도체', '반도체', '전자제품'],
            'trading_halt': [None, None, None],
            'issue': [None, None, None]
        }
        df = pd.DataFrame(sample_data)
        df.to_csv(cache_file, index=False, encoding='utf-8-sig')
        
        yield cache_file
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_load_from_existing_cache(self, temp_cache_file):
        """Should load from CSV cache when file exists."""
        manager = CorpListManager(cache_path=temp_cache_file)
        manager.load()
        
        # Should populate lookup dict
        assert len(manager._lookup) == 3
        assert manager._lookup['005930'] == '00126380'
        assert manager._lookup['000660'] == '00164779'
        assert manager._lookup['066570'] == '00259148'
    
    def test_load_from_cache_preserves_data_types(self, temp_cache_file):
        """Should preserve string types for codes (no numeric conversion)."""
        manager = CorpListManager(cache_path=temp_cache_file)
        manager.load()
        
        # Codes should remain strings
        assert isinstance(manager._lookup['005930'], str)
        assert manager._lookup['005930'] == '00126380'
    
    def test_load_does_not_call_api_when_cache_exists(self, temp_cache_file):
        """Should NOT call DART API when cache file exists."""
        manager = CorpListManager(cache_path=temp_cache_file)
        
        with patch('dart_fss.get_corp_list') as mock_get_corp_list:
            manager.load()
            mock_get_corp_list.assert_not_called()


class TestCorpListManagerLoadFromAPI:
    """Test loading corporation list from DART API."""
    
    @pytest.fixture
    def mock_corp_list(self):
        """Create mock CorpList with sample Corp objects."""
        # Create mock Corp objects
        mock_samsung = Mock()
        mock_samsung.stock_code = '005930'
        mock_samsung.to_dict.return_value = {
            'corp_code': '00126380',
            'corp_name': '삼성전자',
            'corp_eng_name': 'Samsung Electronics Co., Ltd.',
            'stock_code': '005930',
            'modify_date': '20240101',
            'corp_cls': 'Y',
            'market_type': 'stockMkt',
            'sector': '전기전자',
            'product': '반도체',
            'trading_halt': None,
            'issue': None
        }
        
        mock_unlisted = Mock()
        mock_unlisted.stock_code = None  # Unlisted corp
        
        # Create mock CorpList
        mock_corp_list = Mock()
        mock_corp_list.corps = [mock_samsung, mock_unlisted]
        
        return mock_corp_list
    
    def test_load_from_api_when_cache_missing(self, mock_corp_list):
        """Should fetch from DART API when cache doesn't exist."""
        temp_dir = Path(tempfile.mkdtemp())
        cache_file = temp_dir / "corp_list.csv"
        
        manager = CorpListManager(cache_path=cache_file)
        
        with patch('dart_fss.get_corp_list', return_value=mock_corp_list):
            manager.load()
        
        # Should populate lookup
        assert '005930' in manager._lookup
        assert manager._lookup['005930'] == '00126380'
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_load_from_api_filters_unlisted(self, mock_corp_list):
        """Should filter out corporations without stock_code (unlisted)."""
        temp_dir = Path(tempfile.mkdtemp())
        cache_file = temp_dir / "corp_list.csv"
        
        manager = CorpListManager(cache_path=cache_file)
        
        with patch('dart_fss.get_corp_list', return_value=mock_corp_list):
            manager.load()
        
        # Should only have 1 listed corp (Samsung), not 2
        assert len(manager._lookup) == 1
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_load_from_api_saves_to_csv(self, mock_corp_list):
        """Should save fetched data to CSV cache."""
        temp_dir = Path(tempfile.mkdtemp())
        cache_file = temp_dir / "corp_list.csv"
        
        manager = CorpListManager(cache_path=cache_file)
        
        with patch('dart_fss.get_corp_list', return_value=mock_corp_list):
            manager.load()
        
        # CSV should be created
        assert cache_file.exists()
        
        # CSV should contain correct data
        df = pd.read_csv(cache_file, dtype=str)  # Read as strings to preserve leading zeros
        assert len(df) == 1  # Only listed corps
        assert df.iloc[0]['stock_code'] == '005930'
        assert df.iloc[0]['corp_code'] == '00126380'
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_load_from_api_creates_parent_directories(self, mock_corp_list):
        """Should create parent directories if they don't exist."""
        temp_dir = Path(tempfile.mkdtemp())
        cache_file = temp_dir / "nested" / "path" / "corp_list.csv"
        
        manager = CorpListManager(cache_path=cache_file)
        
        with patch('dart_fss.get_corp_list', return_value=mock_corp_list):
            manager.load()
        
        # Parent directories should be created
        assert cache_file.parent.exists()
        assert cache_file.exists()
        
        # Cleanup
        shutil.rmtree(temp_dir)


class TestCorpListManagerForceRefresh:
    """Test force refresh functionality."""
    
    @pytest.fixture
    def temp_cache_with_old_data(self):
        """Create cache with outdated data."""
        temp_dir = Path(tempfile.mkdtemp())
        cache_file = temp_dir / "corp_list.csv"
        
        # Old data with only 1 corp
        old_data = {
            'corp_code': ['00126380'],
            'corp_name': ['삼성전자'],
            'corp_eng_name': ['Samsung Electronics Co., Ltd.'],
            'stock_code': ['005930'],
            'modify_date': ['20200101'],  # Old date
            'corp_cls': ['Y'],
            'market_type': ['stockMkt'],
            'sector': ['전기전자'],
            'product': ['반도체'],
            'trading_halt': [None],
            'issue': [None]
        }
        df = pd.DataFrame(old_data)
        df.to_csv(cache_file, index=False, encoding='utf-8-sig')
        
        yield cache_file
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_force_refresh_fetches_from_api(self, temp_cache_with_old_data):
        """Should fetch from API when force_refresh=True even if cache exists."""
        manager = CorpListManager(cache_path=temp_cache_with_old_data)
        
        # Mock new data with 2 corps
        mock_samsung = Mock()
        mock_samsung.stock_code = '005930'
        mock_samsung.to_dict.return_value = {
            'corp_code': '00126380',
            'corp_name': '삼성전자',
            'stock_code': '005930',
            'modify_date': '20240101',
            'corp_cls': 'Y',
        }
        
        mock_sk = Mock()
        mock_sk.stock_code = '000660'
        mock_sk.to_dict.return_value = {
            'corp_code': '00164779',
            'corp_name': 'SK하이닉스',
            'stock_code': '000660',
            'modify_date': '20240101',
            'corp_cls': 'Y',
        }
        
        mock_corp_list = Mock()
        mock_corp_list.corps = [mock_samsung, mock_sk]
        
        with patch('dart_fss.get_corp_list', return_value=mock_corp_list) as mock_get:
            manager.load(force_refresh=True)
            
            # Should call API
            mock_get.assert_called_once()
            
            # Should have new data
            assert len(manager._lookup) == 2


class TestCorpListManagerGetCorpCode:
    """Test stock_code → corp_code lookup."""
    
    @pytest.fixture
    def loaded_manager(self, tmp_path):
        """Create manager with loaded data."""
        cache_file = tmp_path / "corp_list.csv"
        
        sample_data = {
            'corp_code': ['00126380', '00164779'],
            'corp_name': ['삼성전자', 'SK하이닉스'],
            'stock_code': ['005930', '000660'],
            'modify_date': ['20240101', '20240101'],
        }
        df = pd.DataFrame(sample_data)
        df.to_csv(cache_file, index=False, encoding='utf-8-sig')
        
        manager = CorpListManager(cache_path=cache_file)
        manager.load()
        return manager
    
    def test_get_corp_code_success(self, loaded_manager):
        """Should return corp_code for valid stock_code."""
        corp_code = loaded_manager.get_corp_code('005930')
        assert corp_code == '00126380'
    
    def test_get_corp_code_invalid_raises_error(self, loaded_manager):
        """Should raise ValueError for invalid stock_code."""
        with pytest.raises(ValueError, match="Stock code not found: 999999"):
            loaded_manager.get_corp_code('999999')
    
    def test_get_corp_code_preserves_leading_zeros(self, loaded_manager):
        """Should preserve leading zeros in stock codes."""
        corp_code = loaded_manager.get_corp_code('000660')
        assert corp_code == '00164779'


class TestCorpListManagerGetCompanyInfo:
    """Test get_company_info() helper method."""
    
    @pytest.fixture
    def loaded_manager_with_full_data(self, tmp_path):
        """Create manager with full company metadata."""
        cache_file = tmp_path / "corp_list.csv"
        
        sample_data = {
            'corp_code': ['00126380'],
            'corp_name': ['삼성전자'],
            'corp_eng_name': ['Samsung Electronics Co., Ltd.'],
            'stock_code': ['005930'],
            'modify_date': ['20240101'],
            'corp_cls': ['Y'],
            'market_type': ['stockMkt'],
            'sector': ['전기전자'],
            'product': ['반도체'],
            'trading_halt': [None],
            'issue': [None]
        }
        df = pd.DataFrame(sample_data)
        df.to_csv(cache_file, index=False, encoding='utf-8-sig')
        
        manager = CorpListManager(cache_path=cache_file)
        manager.load()
        return manager
    
    def test_get_company_info_returns_full_metadata(self, loaded_manager_with_full_data):
        """Should return complete company metadata dictionary."""
        info = loaded_manager_with_full_data.get_company_info('005930')
        
        assert info['corp_code'] == '00126380'
        assert info['corp_name'] == '삼성전자'
        assert info['corp_eng_name'] == 'Samsung Electronics Co., Ltd.'
        assert info['stock_code'] == '005930'
        assert info['corp_cls'] == 'Y'
        assert info['sector'] == '전기전자'
        assert info['product'] == '반도체'
    
    def test_get_company_info_invalid_stock_code_raises_error(self, loaded_manager_with_full_data):
        """Should raise ValueError for invalid stock_code."""
        with pytest.raises(ValueError, match="Stock code not found: 999999"):
            loaded_manager_with_full_data.get_company_info('999999')


class TestCorpListManagerEdgeCases:
    """Test edge cases and error handling."""
    
    def test_load_before_get_corp_code_raises_helpful_error(self):
        """Should raise helpful error if get_corp_code called before load()."""
        temp_dir = Path(tempfile.mkdtemp())
        cache_file = temp_dir / "corp_list.csv"
        
        manager = CorpListManager(cache_path=cache_file)
        # Don't call load()
        
        with pytest.raises(ValueError, match="Stock code not found: 005930"):
            manager.get_corp_code('005930')
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_empty_csv_creates_empty_lookup(self, tmp_path):
        """Should handle empty CSV gracefully."""
        cache_file = tmp_path / "corp_list.csv"
        
        # Create empty CSV with headers only
        df = pd.DataFrame(columns=['corp_code', 'stock_code', 'corp_name'])
        df.to_csv(cache_file, index=False)
        
        manager = CorpListManager(cache_path=cache_file)
        manager.load()
        
        assert manager._lookup == {}
    
    def test_csv_with_nan_values_handles_gracefully(self, tmp_path):
        """Should handle NaN values in CSV (delisted corps with incomplete data)."""
        cache_file = tmp_path / "corp_list.csv"
        
        # Data with NaN values (like 29.1% of corps in Experiment 5)
        sample_data = {
            'corp_code': ['00126380', '00999999'],
            'corp_name': ['삼성전자', '테스트회사'],
            'stock_code': ['005930', '123456'],
            'corp_cls': ['Y', None],  # NaN for second corp
            'sector': ['전기전자', None],
            'product': ['반도체', None],
        }
        df = pd.DataFrame(sample_data)
        df.to_csv(cache_file, index=False)
        
        manager = CorpListManager(cache_path=cache_file)
        manager.load()
        
        # Should still load both corps
        assert len(manager._lookup) == 2
        assert manager.get_corp_code('005930') == '00126380'
        assert manager.get_corp_code('123456') == '00999999'

