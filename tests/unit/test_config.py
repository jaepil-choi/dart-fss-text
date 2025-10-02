"""
Unit tests for configuration management using Pydantic Settings.

Tests the ReportTypesConfig class that auto-loads config/types.yaml
and provides validation methods.
"""

import pytest
from typing import Dict


class TestReportTypesConfig:
    """Test suite for ReportTypesConfig pydantic-settings class."""
    
    def test_config_loads_yaml_automatically(self):
        """Config should automatically load types.yaml on instantiation."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Should have loaded all three sections from types.yaml
        assert hasattr(config, 'pblntf_detail_ty')
        assert hasattr(config, 'corp_cls')
        assert hasattr(config, 'rm')
        
        # Should be dictionaries
        assert isinstance(config.pblntf_detail_ty, dict)
        assert isinstance(config.corp_cls, dict)
        assert isinstance(config.rm, dict)
    
    def test_config_contains_expected_report_types(self):
        """Config should contain all periodic report types."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Check for periodic report types (A001, A002, A003)
        assert 'A001' in config.pblntf_detail_ty
        assert 'A002' in config.pblntf_detail_ty
        assert 'A003' in config.pblntf_detail_ty
        
        # Verify Korean descriptions
        assert config.pblntf_detail_ty['A001'] == '사업보고서'
        assert config.pblntf_detail_ty['A002'] == '반기보고서'
        assert config.pblntf_detail_ty['A003'] == '분기보고서'
    
    def test_config_contains_corp_classifications(self):
        """Config should contain corporation classification codes."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Check for all corp classes
        assert 'Y' in config.corp_cls  # KOSPI
        assert 'K' in config.corp_cls  # KOSDAQ
        assert 'N' in config.corp_cls  # KONEX
        assert 'E' in config.corp_cls  # Others
        
        assert config.corp_cls['Y'] == '유가증권'
        assert config.corp_cls['K'] == '코스닥'
    
    def test_config_contains_remark_codes(self):
        """Config should contain remark codes."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Check for key remark codes
        assert '연' in config.rm  # Consolidated
        assert '정' in config.rm  # Amended
        
        assert '연결부분' in config.rm['연']
    
    def test_is_valid_report_type_returns_true_for_valid_codes(self):
        """is_valid_report_type() should return True for valid codes."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Periodic reports
        assert config.is_valid_report_type('A001') is True
        assert config.is_valid_report_type('A002') is True
        assert config.is_valid_report_type('A003') is True
        
        # Other valid types
        assert config.is_valid_report_type('B001') is True
        assert config.is_valid_report_type('F001') is True
    
    def test_is_valid_report_type_returns_false_for_invalid_codes(self):
        """is_valid_report_type() should return False for invalid codes."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Invalid codes
        assert config.is_valid_report_type('Z999') is False
        assert config.is_valid_report_type('INVALID') is False
        assert config.is_valid_report_type('') is False
        assert config.is_valid_report_type('a001') is False  # Lowercase
    
    def test_get_report_description_returns_correct_description(self):
        """get_report_description() should return Korean description."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        assert config.get_report_description('A001') == '사업보고서'
        assert config.get_report_description('A002') == '반기보고서'
        assert config.get_report_description('A003') == '분기보고서'
        assert config.get_report_description('B001') == '주요사항보고서'
    
    def test_get_report_description_raises_for_invalid_code(self):
        """get_report_description() should raise KeyError for invalid code."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        with pytest.raises(KeyError, match="Unknown report type"):
            config.get_report_description('Z999')
        
        with pytest.raises(KeyError):
            config.get_report_description('INVALID')
    
    def test_config_has_all_expected_report_types(self):
        """Config should have 60+ report types from spec."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Should have substantial number of report types
        assert len(config.pblntf_detail_ty) > 50
        
        # Check coverage across categories
        a_types = [k for k in config.pblntf_detail_ty if k.startswith('A')]
        b_types = [k for k in config.pblntf_detail_ty if k.startswith('B')]
        f_types = [k for k in config.pblntf_detail_ty if k.startswith('F')]
        
        assert len(a_types) >= 3  # A001, A002, A003, etc.
        assert len(b_types) >= 1  # B001, etc.
        assert len(f_types) >= 1  # F001, etc.
    
    def test_pydantic_field_validation(self):
        """Pydantic should validate field types."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Fields should be of correct type
        assert isinstance(config.pblntf_detail_ty, dict)
        assert all(isinstance(k, str) for k in config.pblntf_detail_ty.keys())
        assert all(isinstance(v, str) for v in config.pblntf_detail_ty.values())


class TestGetConfigSingleton:
    """Test suite for get_config() singleton pattern."""
    
    def test_get_config_returns_config_instance(self):
        """get_config() should return ReportTypesConfig instance."""
        from dart_fss_text.config import get_config, ReportTypesConfig
        
        config = get_config()
        
        assert isinstance(config, ReportTypesConfig)
        assert hasattr(config, 'pblntf_detail_ty')
    
    def test_get_config_returns_same_instance_on_multiple_calls(self):
        """get_config() should return the same instance (singleton)."""
        from dart_fss_text.config import get_config
        
        config1 = get_config()
        config2 = get_config()
        
        # Should be the exact same object
        assert config1 is config2
    
    def test_config_is_lazy_loaded(self):
        """Config should only be loaded when first accessed."""
        # This is implicit in singleton pattern - first call loads,
        # subsequent calls return cached instance
        from dart_fss_text.config import get_config
        
        # First call - loads config
        config = get_config()
        assert config is not None
        
        # Second call - returns same instance (no reload)
        config2 = get_config()
        assert config is config2


class TestConfigIntegration:
    """Integration tests for config with types.yaml file."""
    
    def test_config_loads_from_actual_yaml_file(self):
        """Config should load from actual config/types.yaml file."""
        from dart_fss_text.config import ReportTypesConfig
        from pathlib import Path
        
        config = ReportTypesConfig()
        
        # Verify it loaded from the actual file by checking known values
        # These values are in our actual config/types.yaml
        assert config.pblntf_detail_ty['A001'] == '사업보고서'
        assert config.corp_cls['Y'] == '유가증권'
        assert '연' in config.rm
    
    def test_config_handles_all_categories_from_yaml(self):
        """Config should successfully load all major categories."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Check each major category has entries
        categories = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        
        for category in categories:
            category_codes = [k for k in config.pblntf_detail_ty 
                            if k.startswith(category)]
            assert len(category_codes) > 0, f"Category {category} should have entries"
    
    def test_config_yaml_file_path_resolution(self):
        """Pydantic Settings should resolve config/types.yaml path correctly."""
        from dart_fss_text.config import ReportTypesConfig
        
        # Should not raise FileNotFoundError
        config = ReportTypesConfig()
        
        # Should have loaded data successfully
        assert len(config.pblntf_detail_ty) > 0
        assert len(config.corp_cls) > 0
        assert len(config.rm) > 0


class TestConfigErrorHandling:
    """Test error handling in config module."""
    
    def test_invalid_report_code_in_validation(self):
        """Validation should handle invalid codes gracefully."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # Should return False, not raise exception
        assert config.is_valid_report_type('INVALID') is False
        assert config.is_valid_report_type(None) is False
        assert config.is_valid_report_type('') is False
    
    def test_none_values_handled_correctly(self):
        """Config methods should handle None values appropriately."""
        from dart_fss_text.config import ReportTypesConfig
        
        config = ReportTypesConfig()
        
        # is_valid_report_type with None
        assert config.is_valid_report_type(None) is False
        
        # get_report_description with None should raise KeyError
        with pytest.raises(KeyError):
            config.get_report_description(None)


class TestConfigCoverage:
    """Test that config covers all required report types from experiments."""
    
    def test_config_has_periodic_report_types_from_exp04(self):
        """Config should have all report types used in exp_04."""
        from dart_fss_text.config import get_config
        
        config = get_config()
        
        # These are the report types we validated in exp_04
        required_types = ['A001', 'A002', 'A003']
        
        for code in required_types:
            assert code in config.pblntf_detail_ty, \
                f"Report type {code} should be in config"
            assert config.is_valid_report_type(code), \
                f"Report type {code} should be valid"
    
    def test_config_descriptions_match_exp04_findings(self):
        """Config descriptions should match what we found in experiments."""
        from dart_fss_text.config import get_config
        
        config = get_config()
        
        # These descriptions were validated in exp_04
        expected = {
            'A001': '사업보고서',      # Annual
            'A002': '반기보고서',      # Semi-Annual
            'A003': '분기보고서'       # Quarterly
        }
        
        for code, description in expected.items():
            assert config.get_report_description(code) == description

