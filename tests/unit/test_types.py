"""
Unit tests for discovery helper classes (types.py).

Tests user-facing helpers for discovering available report types,
corporation classes, and other DART specifications.
"""

import pytest


class TestReportTypes:
    """Test suite for ReportTypes discovery helper."""
    
    def test_list_available_returns_all_report_types(self):
        """Should return all report types from config."""
        from dart_fss_text.types import ReportTypes
        
        types = ReportTypes.list_available()
        
        assert isinstance(types, dict)
        assert len(types) > 50  # Should have 60+ types
        
        # Check key periodic types
        assert 'A001' in types
        assert 'A002' in types
        assert 'A003' in types
    
    def test_list_available_includes_korean_descriptions(self):
        """Returned dict should have Korean descriptions as values."""
        from dart_fss_text.types import ReportTypes
        
        types = ReportTypes.list_available()
        
        assert types['A001'] == '사업보고서'
        assert types['A002'] == '반기보고서'
        assert types['A003'] == '분기보고서'
    
    def test_list_available_returns_copy_not_reference(self):
        """Should return a copy to prevent mutation of config."""
        from dart_fss_text.types import ReportTypes
        
        types1 = ReportTypes.list_available()
        types1['TEST'] = 'Modified'
        
        types2 = ReportTypes.list_available()
        
        assert 'TEST' not in types2  # Modification didn't affect original
    
    def test_list_by_category_filters_by_prefix(self):
        """Should return only report types matching category prefix."""
        from dart_fss_text.types import ReportTypes
        
        # Periodic reports (A category)
        a_types = ReportTypes.list_by_category('A')
        
        assert len(a_types) >= 3
        assert all(k.startswith('A') for k in a_types.keys())
        assert 'A001' in a_types
        assert 'B001' not in a_types
    
    def test_list_by_category_returns_empty_for_invalid_category(self):
        """Should return empty dict for non-existent category."""
        from dart_fss_text.types import ReportTypes
        
        result = ReportTypes.list_by_category('Z')
        
        assert isinstance(result, dict)
        assert len(result) == 0
    
    def test_list_by_category_case_sensitive(self):
        """Category prefix should be case-sensitive (uppercase)."""
        from dart_fss_text.types import ReportTypes
        
        upper = ReportTypes.list_by_category('A')
        lower = ReportTypes.list_by_category('a')
        
        assert len(upper) > 0
        assert len(lower) == 0  # Lowercase should return nothing
    
    def test_get_description_returns_korean_name(self):
        """Should return Korean description for valid code."""
        from dart_fss_text.types import ReportTypes
        
        desc = ReportTypes.get_description('A001')
        
        assert desc == '사업보고서'
    
    def test_get_description_raises_for_invalid_code(self):
        """Should raise ValueError for invalid report type code."""
        from dart_fss_text.types import ReportTypes
        
        with pytest.raises(ValueError, match="Unknown report type"):
            ReportTypes.get_description('Z999')
    
    def test_is_valid_returns_true_for_valid_codes(self):
        """Should return True for valid report type codes."""
        from dart_fss_text.types import ReportTypes
        
        assert ReportTypes.is_valid('A001') is True
        assert ReportTypes.is_valid('A002') is True
        assert ReportTypes.is_valid('B001') is True
    
    def test_is_valid_returns_false_for_invalid_codes(self):
        """Should return False for invalid codes."""
        from dart_fss_text.types import ReportTypes
        
        assert ReportTypes.is_valid('Z999') is False
        assert ReportTypes.is_valid('INVALID') is False
        assert ReportTypes.is_valid('') is False
    
    def test_list_periodic_returns_only_periodic_reports(self):
        """Should return A001, A002, A003 (periodic reports)."""
        from dart_fss_text.types import ReportTypes
        
        periodic = ReportTypes.list_periodic()
        
        assert len(periodic) == 3
        assert 'A001' in periodic
        assert 'A002' in periodic
        assert 'A003' in periodic
        assert periodic['A001'] == '사업보고서'


class TestCorpClass:
    """Test suite for CorpClass discovery helper."""
    
    def test_list_available_returns_all_corp_classes(self):
        """Should return all corporation classifications."""
        from dart_fss_text.types import CorpClass
        
        classes = CorpClass.list_available()
        
        assert isinstance(classes, dict)
        assert len(classes) == 4  # Y, K, N, E
        
        assert 'Y' in classes  # KOSPI
        assert 'K' in classes  # KOSDAQ
        assert 'N' in classes  # KONEX
        assert 'E' in classes  # Others
    
    def test_list_available_includes_korean_descriptions(self):
        """Should have Korean descriptions for each class."""
        from dart_fss_text.types import CorpClass
        
        classes = CorpClass.list_available()
        
        assert classes['Y'] == '유가증권'
        assert classes['K'] == '코스닥'
        assert classes['N'] == '코넥스'
        assert classes['E'] == '기타'
    
    def test_get_description_returns_korean_name(self):
        """Should return Korean description for valid code."""
        from dart_fss_text.types import CorpClass
        
        assert CorpClass.get_description('Y') == '유가증권'
        assert CorpClass.get_description('K') == '코스닥'
    
    def test_get_description_raises_for_invalid_code(self):
        """Should raise ValueError for invalid corp class code."""
        from dart_fss_text.types import CorpClass
        
        with pytest.raises(ValueError, match="Unknown corporation class"):
            CorpClass.get_description('Z')
    
    def test_is_valid_returns_true_for_valid_codes(self):
        """Should return True for valid corp class codes."""
        from dart_fss_text.types import CorpClass
        
        assert CorpClass.is_valid('Y') is True
        assert CorpClass.is_valid('K') is True
        assert CorpClass.is_valid('N') is True
        assert CorpClass.is_valid('E') is True
    
    def test_is_valid_returns_false_for_invalid_codes(self):
        """Should return False for invalid codes."""
        from dart_fss_text.types import CorpClass
        
        assert CorpClass.is_valid('Z') is False
        assert CorpClass.is_valid('INVALID') is False
        assert CorpClass.is_valid('') is False


class TestRemarkCodes:
    """Test suite for RemarkCodes discovery helper."""
    
    def test_list_available_returns_all_remark_codes(self):
        """Should return all remark codes."""
        from dart_fss_text.types import RemarkCodes
        
        remarks = RemarkCodes.list_available()
        
        assert isinstance(remarks, dict)
        assert len(remarks) >= 5
        
        # Key remark codes
        assert '연' in remarks  # Consolidated
        assert '정' in remarks  # Amended
    
    def test_list_available_includes_korean_descriptions(self):
        """Should have Korean descriptions explaining each code."""
        from dart_fss_text.types import RemarkCodes
        
        remarks = RemarkCodes.list_available()
        
        assert '연결' in remarks['연']
        assert '정정' in remarks['정']
    
    def test_get_description_returns_explanation(self):
        """Should return explanation for remark code."""
        from dart_fss_text.types import RemarkCodes
        
        desc = RemarkCodes.get_description('연')
        
        assert '연결' in desc
    
    def test_get_description_raises_for_invalid_code(self):
        """Should raise ValueError for invalid remark code."""
        from dart_fss_text.types import RemarkCodes
        
        with pytest.raises(ValueError, match="Unknown remark code"):
            RemarkCodes.get_description('INVALID')
    
    def test_is_valid_returns_true_for_valid_codes(self):
        """Should return True for valid remark codes."""
        from dart_fss_text.types import RemarkCodes
        
        assert RemarkCodes.is_valid('연') is True
        assert RemarkCodes.is_valid('정') is True
    
    def test_is_valid_returns_false_for_invalid_codes(self):
        """Should return False for invalid codes."""
        from dart_fss_text.types import RemarkCodes
        
        assert RemarkCodes.is_valid('INVALID') is False
        assert RemarkCodes.is_valid('') is False


class TestDiscoveryIntegration:
    """Integration tests for discovery helpers."""
    
    def test_all_helpers_use_same_config(self):
        """All helpers should use the same underlying config singleton."""
        from dart_fss_text.types import ReportTypes, CorpClass, RemarkCodes
        from dart_fss_text.config import get_config
        
        # All should use the same config instance
        config = get_config()
        
        # Verify consistency
        report_types = ReportTypes.list_available()
        assert report_types == config.pblntf_detail_ty
        
        corp_classes = CorpClass.list_available()
        assert corp_classes == config.corp_cls
        
        remark_codes = RemarkCodes.list_available()
        assert remark_codes == config.rm
    
    def test_helpers_return_immutable_views(self):
        """Helpers should return copies, not mutable references."""
        from dart_fss_text.types import ReportTypes, CorpClass
        
        types1 = ReportTypes.list_available()
        types1['MUTATED'] = 'Should not persist'
        
        types2 = ReportTypes.list_available()
        assert 'MUTATED' not in types2
        
        classes1 = CorpClass.list_available()
        classes1['X'] = 'Mutated'
        
        classes2 = CorpClass.list_available()
        assert 'X' not in classes2

