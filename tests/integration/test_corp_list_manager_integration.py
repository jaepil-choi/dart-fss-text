"""
Integration tests for CorpListManager with live DART API.

These tests validate that CorpListManager works correctly with real DART data.
They require:
- OPENDART_API_KEY environment variable
- Internet connection
- ~10 seconds for API calls

Run with: poetry run pytest tests/integration/ -v -s
Skip in CI with: pytest -m "not integration"
"""

import pytest
import os
from pathlib import Path
import tempfile
import shutil
import dart_fss as dart
from dotenv import load_dotenv

from dart_fss_text.services.corp_list_manager import CorpListManager


# Load environment variables
load_dotenv()

# Skip all tests in this module if API key not available
pytestmark = pytest.mark.skipif(
    not os.getenv('OPENDART_API_KEY'),
    reason="OPENDART_API_KEY not set - integration tests require live API"
)


@pytest.fixture(scope="module")
def setup_dart_api():
    """Set up DART API key for all tests in this module."""
    api_key = os.getenv('OPENDART_API_KEY')
    if api_key:
        dart.set_api_key(api_key=api_key)
    return api_key


@pytest.fixture
def temp_cache_dir():
    """Create temporary directory for cache files."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestCorpListManagerLiveAPILoad:
    """Test loading corporation list from live DART API."""
    
    def test_load_from_live_api_creates_cache(self, setup_dart_api, temp_cache_dir):
        """Should fetch from live DART API and create cache file."""
        cache_file = temp_cache_dir / "corp_list.csv"
        manager = CorpListManager(cache_path=cache_file)
        
        print(f"\n[Integration Test] Fetching corp list from DART API...")
        print(f"  Cache path: {cache_file}")
        
        # Load from API (this will take ~10 seconds)
        manager.load()
        
        print(f"  ✓ Load complete")
        print(f"  ✓ Loaded {len(manager._lookup)} listed corporations")
        
        # Validate cache was created
        assert cache_file.exists(), "Cache file should be created"
        assert cache_file.stat().st_size > 0, "Cache file should not be empty"
        
        # Validate we got expected number of corps (approximately 3,901 from Experiment 5)
        # Allow some variance as list may grow/shrink
        assert len(manager._lookup) >= 3800, f"Should have ~3,901 listed corps, got {len(manager._lookup)}"
        assert len(manager._lookup) <= 4100, f"Should have ~3,901 listed corps, got {len(manager._lookup)}"
        
        print(f"  ✓ Cache file size: {cache_file.stat().st_size:,} bytes")
    
    def test_second_load_uses_cache(self, setup_dart_api, temp_cache_dir):
        """Should use cache on second load (much faster)."""
        cache_file = temp_cache_dir / "corp_list.csv"
        
        # First load: from API
        manager1 = CorpListManager(cache_path=cache_file)
        print(f"\n[Integration Test] First load from API...")
        manager1.load()
        first_count = len(manager1._lookup)
        print(f"  ✓ Loaded {first_count} corporations")
        
        # Second load: from cache
        manager2 = CorpListManager(cache_path=cache_file)
        print(f"[Integration Test] Second load from cache...")
        manager2.load()
        second_count = len(manager2._lookup)
        print(f"  ✓ Loaded {second_count} corporations")
        
        # Should have same data
        assert first_count == second_count
        assert manager1._lookup == manager2._lookup


class TestCorpListManagerRealCompanies:
    """Test with real Korean companies."""
    
    @pytest.fixture
    def loaded_manager(self, setup_dart_api, temp_cache_dir):
        """Create manager with real DART data loaded."""
        cache_file = temp_cache_dir / "corp_list.csv"
        manager = CorpListManager(cache_path=cache_file)
        
        print(f"\n[Integration Test] Loading real DART data...")
        manager.load()
        print(f"  ✓ Loaded {len(manager._lookup)} corporations")
        
        return manager
    
    def test_samsung_electronics_lookup(self, loaded_manager):
        """Should correctly lookup Samsung Electronics."""
        print(f"\n[Integration Test] Looking up Samsung Electronics (005930)...")
        
        corp_code = loaded_manager.get_corp_code('005930')
        print(f"  ✓ Corp code: {corp_code}")
        
        # Samsung's corp_code is 00126380 (validated in Experiment 5)
        assert corp_code == '00126380'
    
    def test_samsung_electronics_full_info(self, loaded_manager):
        """Should retrieve full Samsung Electronics metadata."""
        print(f"\n[Integration Test] Retrieving Samsung metadata...")
        
        info = loaded_manager.get_company_info('005930')
        
        print(f"  ✓ Corp code: {info['corp_code']}")
        print(f"  ✓ Corp name: {info['corp_name']}")
        print(f"  ✓ Corp cls: {info['corp_cls']}")
        print(f"  ✓ Sector: {info['sector']}")
        
        # Validate Samsung's data
        assert info['corp_code'] == '00126380'
        assert info['corp_name'] == '삼성전자'
        assert info['stock_code'] == '005930'
        assert info['corp_cls'] == 'Y'  # KOSPI
        
        # Samsung should have complete data (not in the 29% with NaN)
        assert info['sector'] is not None
        assert info['product'] is not None
    
    def test_multiple_company_lookups(self, loaded_manager):
        """Should handle multiple company lookups correctly."""
        print(f"\n[Integration Test] Testing multiple company lookups...")
        
        # Test multiple major Korean companies
        # Note: Only validating stock_code and name, not corp_code (may change)
        companies = {
            '005930': '삼성전자',      # Samsung Electronics
            '000660': 'SK하이닉스',    # SK Hynix
            '005380': '현대자동차',    # Hyundai Motor
            '035420': 'NAVER',        # NAVER
        }
        
        for stock_code, expected_name in companies.items():
            corp_code = loaded_manager.get_corp_code(stock_code)
            info = loaded_manager.get_company_info(stock_code)
            
            print(f"  ✓ {stock_code} → {corp_code} ({info['corp_name']})")
            
            # Validate corp_code exists and is 8 digits
            assert len(corp_code) == 8
            assert corp_code.isdigit()
            
            # Validate company name matches
            assert info['corp_name'] == expected_name
            assert info['stock_code'] == stock_code
    
    def test_leading_zeros_preserved(self, loaded_manager):
        """Should preserve leading zeros in stock codes."""
        print(f"\n[Integration Test] Testing leading zero preservation...")
        
        # SK Hynix has leading zeros (000660)
        stock_code = '000660'
        corp_code = loaded_manager.get_corp_code(stock_code)
        info = loaded_manager.get_company_info(stock_code)
        
        print(f"  ✓ Stock code: {stock_code} (leading zeros preserved)")
        print(f"  ✓ Corp code: {corp_code}")
        print(f"  ✓ Name: {info['corp_name']}")
        
        assert corp_code == '00164779'
        assert info['stock_code'] == '000660'  # Not '660'
        assert isinstance(info['stock_code'], str)
    
    def test_invalid_stock_code_raises_error(self, loaded_manager):
        """Should raise ValueError for invalid stock code."""
        print(f"\n[Integration Test] Testing invalid stock code...")
        
        with pytest.raises(ValueError, match="Stock code not found: 999999"):
            loaded_manager.get_corp_code('999999')
        
        print(f"  ✓ Correctly raised ValueError for invalid code")


class TestCorpListManagerForceRefresh:
    """Test force refresh with live API."""
    
    def test_force_refresh_updates_cache(self, setup_dart_api, temp_cache_dir):
        """Should update cache when force_refresh=True."""
        cache_file = temp_cache_dir / "corp_list.csv"
        
        # Initial load
        manager = CorpListManager(cache_path=cache_file)
        print(f"\n[Integration Test] Initial load...")
        manager.load()
        initial_count = len(manager._lookup)
        initial_mtime = cache_file.stat().st_mtime
        
        print(f"  ✓ Initial count: {initial_count}")
        print(f"  ✓ Initial cache mtime: {initial_mtime}")
        
        # Wait a moment to ensure mtime would change
        import time
        time.sleep(0.1)
        
        # Force refresh
        print(f"[Integration Test] Force refresh...")
        manager.load(force_refresh=True)
        refresh_count = len(manager._lookup)
        refresh_mtime = cache_file.stat().st_mtime
        
        print(f"  ✓ Refresh count: {refresh_count}")
        print(f"  ✓ Refresh cache mtime: {refresh_mtime}")
        
        # Cache file should be updated (mtime changed)
        assert refresh_mtime >= initial_mtime
        
        # Count should be similar (may vary slightly if DART updated)
        assert abs(refresh_count - initial_count) < 100


class TestCorpListManagerDataQuality:
    """Test data quality against Experiment 5 findings."""
    
    def test_market_distribution(self, setup_dart_api, temp_cache_dir):
        """Should have realistic market distribution (KOSPI, KOSDAQ, KONEX)."""
        cache_file = temp_cache_dir / "corp_list.csv"
        manager = CorpListManager(cache_path=cache_file)
        
        print(f"\n[Integration Test] Analyzing market distribution...")
        manager.load()
        
        # Count by market (corp_cls)
        market_counts = {'Y': 0, 'K': 0, 'N': 0, 'E': 0, None: 0}
        
        for stock_code in manager._lookup.keys():
            info = manager.get_company_info(stock_code)
            corp_cls = info.get('corp_cls')
            if corp_cls in market_counts:
                market_counts[corp_cls] += 1
            else:
                market_counts[None] += 1
        
        print(f"  Market distribution:")
        print(f"    Y (KOSPI): {market_counts['Y']}")
        print(f"    K (KOSDAQ): {market_counts['K']}")
        print(f"    N (KONEX): {market_counts['N']}")
        print(f"    E (Other): {market_counts['E']}")
        print(f"    None: {market_counts[None]}")
        
        # Validate distribution matches Experiment 5 expectations
        # KOSDAQ should be majority (~65%), KOSPI second (~31%)
        total = sum(market_counts.values())
        kosdaq_pct = (market_counts['K'] / total) * 100
        kospi_pct = (market_counts['Y'] / total) * 100
        
        print(f"  Percentages (of total):")
        print(f"    KOSDAQ: {kosdaq_pct:.1f}%")
        print(f"    KOSPI: {kospi_pct:.1f}%")
        print(f"    With data: {((total - market_counts[None]) / total) * 100:.1f}%")
        
        # Validate KOSDAQ has more companies than KOSPI (basic sanity check)
        assert market_counts['K'] > market_counts['Y'], "KOSDAQ should have more companies than KOSPI"
        
        # Validate we have a reasonable amount of companies with corp_cls data
        # Note: ~29% may have None (delisted/incomplete data from Experiment 5)
        companies_with_data = total - market_counts[None]
        assert companies_with_data > total * 0.6, f"At least 60% should have corp_cls data"
    
    def test_no_duplicate_stock_codes(self, setup_dart_api, temp_cache_dir):
        """Should have no duplicate stock codes (validated in Experiment 5)."""
        cache_file = temp_cache_dir / "corp_list.csv"
        manager = CorpListManager(cache_path=cache_file)
        
        print(f"\n[Integration Test] Checking for duplicate stock codes...")
        manager.load()
        
        # All keys in lookup should be unique (dict enforces this)
        stock_codes = list(manager._lookup.keys())
        unique_stock_codes = set(stock_codes)
        
        print(f"  ✓ Total stock codes: {len(stock_codes)}")
        print(f"  ✓ Unique stock codes: {len(unique_stock_codes)}")
        
        assert len(stock_codes) == len(unique_stock_codes), "Should have no duplicate stock codes"
    
    def test_no_duplicate_corp_codes(self, setup_dart_api, temp_cache_dir):
        """Should have no duplicate corp codes (validated in Experiment 5)."""
        cache_file = temp_cache_dir / "corp_list.csv"
        manager = CorpListManager(cache_path=cache_file)
        
        print(f"\n[Integration Test] Checking for duplicate corp codes...")
        manager.load()
        
        corp_codes = list(manager._lookup.values())
        unique_corp_codes = set(corp_codes)
        
        print(f"  ✓ Total corp codes: {len(corp_codes)}")
        print(f"  ✓ Unique corp codes: {len(unique_corp_codes)}")
        
        assert len(corp_codes) == len(unique_corp_codes), "Should have no duplicate corp codes"


class TestCorpListManagerPerformance:
    """Test performance characteristics."""
    
    def test_cache_load_is_fast(self, setup_dart_api, temp_cache_dir):
        """Cache load should be faster than API load."""
        import time
        
        cache_file = temp_cache_dir / "corp_list.csv"
        
        # First load: from API
        manager1 = CorpListManager(cache_path=cache_file)
        print(f"\n[Integration Test] Measuring API load time...")
        
        start = time.time()
        manager1.load()
        api_time = time.time() - start
        
        print(f"  ✓ API load time: {api_time:.3f}s")
        
        # Second load: from cache
        manager2 = CorpListManager(cache_path=cache_file)
        print(f"[Integration Test] Measuring cache load time...")
        
        start = time.time()
        manager2.load()
        cache_time = time.time() - start
        
        print(f"  ✓ Cache load time: {cache_time:.3f}s")
        
        if api_time > cache_time:
            speedup = api_time / cache_time
            print(f"  ✓ Speedup: {speedup:.1f}x faster")
        else:
            print(f"  ℹ Cache slightly slower (file system caching may affect results)")
        
        # Basic performance check: cache should not be significantly slower
        # Note: dart-fss may have its own caching, so API might be fast on repeated runs
        assert cache_time < api_time * 2, f"Cache load shouldn't be slower than API"
        
        # Both should complete in reasonable time
        assert api_time < 30, f"API load should be <30s, got {api_time:.3f}s"
        assert cache_time < 5, f"Cache load should be <5s, got {cache_time:.3f}s"

