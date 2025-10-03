"""
Pytest configuration for unit tests.

Provides fixtures and mocks that apply to all unit tests.
"""

import pytest
from unittest.mock import Mock, patch


@pytest.fixture(autouse=True, scope="function")
def mock_dart_get_corp_list_globally():
    """
    Globally mock dart.get_corp_list() for ALL unit tests.
    
    This prevents unit tests from:
    - Making live API calls to DART
    - Loading 114K companies (takes 7+ seconds)
    - Requiring valid API keys
    
    The mock is applied at module import time, before any test code runs.
    """
    # Mock at multiple possible import paths to ensure it's caught
    with patch('dart_fss.corp.get_corp_list') as mock1, \
         patch('dart_fss.get_corp_list') as mock2:
        
        # Setup a basic mock corp_list that works for most tests
        mock_corp_list = Mock()
        mock_corp = Mock()
        mock_corp.corp_code = "00126380"
        mock_corp.corp_name = "삼성전자"
        mock_corp.stock_code = "005930"
        mock_corp.search_filings = Mock(return_value=[])
        
        mock_corp_list.find_by_stock_code = Mock(return_value=mock_corp)
        mock_corp_list.corps = [mock_corp]  # Minimal corps list
        
        mock1.return_value = mock_corp_list
        mock2.return_value = mock_corp_list
        
        yield mock1

