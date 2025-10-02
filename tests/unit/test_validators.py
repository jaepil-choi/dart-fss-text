"""
Unit tests for validation functions.

Tests reusable field validators that will be used with Pydantic models
for input validation against config/types.yaml specifications.
"""

import pytest
from pydantic import BaseModel, field_validator, ValidationError


class TestValidateReportTypes:
    """Test suite for validate_report_types() validator."""
    
    def test_validate_report_types_accepts_valid_single_code(self):
        """Should accept single valid report type code."""
        from dart_fss_text.validators import validate_report_types
        
        result = validate_report_types(['A001'])
        
        assert result == ['A001']
    
    def test_validate_report_types_accepts_multiple_valid_codes(self):
        """Should accept multiple valid report type codes."""
        from dart_fss_text.validators import validate_report_types
        
        codes = ['A001', 'A002', 'A003']
        result = validate_report_types(codes)
        
        assert result == codes
    
    def test_validate_report_types_accepts_all_periodic_reports(self):
        """Should accept all periodic report types from experiments."""
        from dart_fss_text.validators import validate_report_types
        
        # These are validated in exp_04
        periodic_codes = ['A001', 'A002', 'A003']
        result = validate_report_types(periodic_codes)
        
        assert result == periodic_codes
    
    def test_validate_report_types_accepts_other_valid_categories(self):
        """Should accept valid codes from other categories."""
        from dart_fss_text.validators import validate_report_types
        
        # Mix of categories
        codes = ['A001', 'B001', 'F001', 'I001']
        result = validate_report_types(codes)
        
        assert result == codes
    
    def test_validate_report_types_raises_for_invalid_code(self):
        """Should raise ValueError for invalid report type code."""
        from dart_fss_text.validators import validate_report_types
        
        with pytest.raises(ValueError, match="Invalid report type codes"):
            validate_report_types(['Z999'])
    
    def test_validate_report_types_raises_for_mixed_valid_invalid(self):
        """Should raise ValueError if any code is invalid, listing all invalid codes."""
        from dart_fss_text.validators import validate_report_types
        
        with pytest.raises(ValueError, match="Invalid report type codes"):
            validate_report_types(['A001', 'INVALID', 'A002', 'BAD'])
    
    def test_validate_report_types_error_message_includes_invalid_codes(self):
        """Error message should clearly list which codes are invalid."""
        from dart_fss_text.validators import validate_report_types
        
        try:
            validate_report_types(['A001', 'Z999', 'BAD'])
        except ValueError as e:
            error_msg = str(e)
            assert 'Z999' in error_msg
            assert 'BAD' in error_msg
            assert 'A001' not in error_msg  # Valid code should not be in error
    
    def test_validate_report_types_error_message_includes_help(self):
        """Error message should provide helpful guidance."""
        from dart_fss_text.validators import validate_report_types
        
        try:
            validate_report_types(['INVALID'])
        except ValueError as e:
            error_msg = str(e)
            # Should mention how to see available options
            assert 'ReportTypes.list_available()' in error_msg or 'valid' in error_msg.lower()
    
    def test_validate_report_types_accepts_empty_list(self):
        """Should accept empty list (no codes to validate)."""
        from dart_fss_text.validators import validate_report_types
        
        result = validate_report_types([])
        
        assert result == []
    
    def test_validate_report_types_case_sensitive(self):
        """Report type codes are case-sensitive (uppercase required)."""
        from dart_fss_text.validators import validate_report_types
        
        # Lowercase should be invalid
        with pytest.raises(ValueError):
            validate_report_types(['a001'])


class TestValidateStockCode:
    """Test suite for validate_stock_code() validator."""
    
    def test_validate_stock_code_accepts_valid_6_digit_code(self):
        """Should accept valid 6-digit stock code."""
        from dart_fss_text.validators import validate_stock_code
        
        result = validate_stock_code('005930')
        
        assert result == '005930'
    
    def test_validate_stock_code_accepts_samsung_code(self):
        """Should accept Samsung Electronics stock code from experiments."""
        from dart_fss_text.validators import validate_stock_code
        
        # Validated in exp_04
        result = validate_stock_code('005930')
        
        assert result == '005930'
    
    def test_validate_stock_code_preserves_leading_zeros(self):
        """Should preserve leading zeros in stock code."""
        from dart_fss_text.validators import validate_stock_code
        
        result = validate_stock_code('000660')  # SK Hynix
        
        assert result == '000660'
        assert len(result) == 6
    
    def test_validate_stock_code_accepts_all_numeric_codes(self):
        """Should accept any 6-digit numeric code."""
        from dart_fss_text.validators import validate_stock_code
        
        codes = ['000000', '123456', '999999']
        for code in codes:
            result = validate_stock_code(code)
            assert result == code
    
    def test_validate_stock_code_rejects_non_6_digit(self):
        """Should reject stock codes that are not 6 digits."""
        from dart_fss_text.validators import validate_stock_code
        
        # Too short
        with pytest.raises(ValueError, match="6 digits"):
            validate_stock_code('12345')
        
        # Too long
        with pytest.raises(ValueError, match="6 digits"):
            validate_stock_code('1234567')
    
    def test_validate_stock_code_rejects_non_numeric(self):
        """Should reject stock codes with non-numeric characters."""
        from dart_fss_text.validators import validate_stock_code
        
        with pytest.raises(ValueError, match="6 digits"):
            validate_stock_code('00593A')
        
        with pytest.raises(ValueError):
            validate_stock_code('ABC123')
    
    def test_validate_stock_code_rejects_empty_string(self):
        """Should reject empty string."""
        from dart_fss_text.validators import validate_stock_code
        
        with pytest.raises(ValueError):
            validate_stock_code('')
    
    def test_validate_stock_code_error_message_includes_example(self):
        """Error message should include example stock code."""
        from dart_fss_text.validators import validate_stock_code
        
        try:
            validate_stock_code('BAD')
        except ValueError as e:
            error_msg = str(e)
            # Should provide example
            assert '005930' in error_msg or 'Example' in error_msg


class TestValidateDateYYYYMMDD:
    """Test suite for validate_date_yyyymmdd() validator."""
    
    def test_validate_date_accepts_valid_yyyymmdd(self):
        """Should accept valid YYYYMMDD date string."""
        from dart_fss_text.validators import validate_date_yyyymmdd
        
        result = validate_date_yyyymmdd('20240101')
        
        assert result == '20240101'
    
    def test_validate_date_accepts_dates_from_experiments(self):
        """Should accept date formats used in experiments."""
        from dart_fss_text.validators import validate_date_yyyymmdd
        
        # Dates from exp_04
        dates = ['20240101', '20241231']
        for date in dates:
            result = validate_date_yyyymmdd(date)
            assert result == date
    
    def test_validate_date_accepts_various_valid_dates(self):
        """Should accept various valid date formats."""
        from dart_fss_text.validators import validate_date_yyyymmdd
        
        valid_dates = [
            '20200101',  # Jan 1
            '20201231',  # Dec 31
            '20150630',  # Mid-year
            '19990101',  # Old date
            '20991231'   # Future date
        ]
        
        for date in valid_dates:
            result = validate_date_yyyymmdd(date)
            assert result == date
    
    def test_validate_date_rejects_non_8_characters(self):
        """Should reject dates that are not 8 characters."""
        from dart_fss_text.validators import validate_date_yyyymmdd
        
        with pytest.raises(ValueError, match="YYYYMMDD"):
            validate_date_yyyymmdd('2024010')  # 7 chars
        
        with pytest.raises(ValueError, match="YYYYMMDD"):
            validate_date_yyyymmdd('202401011')  # 9 chars
    
    def test_validate_date_rejects_non_numeric(self):
        """Should reject dates with non-numeric characters."""
        from dart_fss_text.validators import validate_date_yyyymmdd
        
        with pytest.raises(ValueError):
            validate_date_yyyymmdd('2024-01-01')  # Dashes
        
        with pytest.raises(ValueError):
            validate_date_yyyymmdd('20240A01')  # Letter
    
    def test_validate_date_rejects_invalid_year_range(self):
        """Should reject years outside valid range (1980-2100)."""
        from dart_fss_text.validators import validate_date_yyyymmdd
        
        # Too old
        with pytest.raises(ValueError, match="out of valid range"):
            validate_date_yyyymmdd('19790101')
        
        # Too far in future
        with pytest.raises(ValueError, match="out of valid range"):
            validate_date_yyyymmdd('21010101')
    
    def test_validate_date_rejects_empty_string(self):
        """Should reject empty string."""
        from dart_fss_text.validators import validate_date_yyyymmdd
        
        with pytest.raises(ValueError):
            validate_date_yyyymmdd('')
    
    def test_validate_date_error_message_includes_format(self):
        """Error message should explain expected format."""
        from dart_fss_text.validators import validate_date_yyyymmdd
        
        try:
            validate_date_yyyymmdd('2024-01-01')
        except ValueError as e:
            error_msg = str(e)
            assert 'YYYYMMDD' in error_msg
            assert '20240101' in error_msg or 'Example' in error_msg


class TestValidatorsWithPydantic:
    """Integration tests: validators used with Pydantic models."""
    
    def test_validators_work_with_pydantic_field_validator(self):
        """Validators should work seamlessly with Pydantic @field_validator."""
        from dart_fss_text.validators import (
            validate_report_types,
            validate_stock_code,
            validate_date_yyyymmdd
        )
        
        class TestModel(BaseModel):
            stock_code: str
            start_date: str
            end_date: str
            report_types: list[str]
            
            _validate_stock = field_validator('stock_code')(validate_stock_code)
            _validate_start = field_validator('start_date')(validate_date_yyyymmdd)
            _validate_end = field_validator('end_date')(validate_date_yyyymmdd)
            _validate_types = field_validator('report_types')(validate_report_types)
        
        # Valid input should work
        model = TestModel(
            stock_code='005930',
            start_date='20240101',
            end_date='20241231',
            report_types=['A001', 'A002']
        )
        
        assert model.stock_code == '005930'
        assert model.report_types == ['A001', 'A002']
    
    def test_validators_raise_pydantic_validation_error_on_invalid_input(self):
        """Invalid input should raise Pydantic ValidationError."""
        from dart_fss_text.validators import (
            validate_report_types,
            validate_stock_code,
            validate_date_yyyymmdd
        )
        
        class TestModel(BaseModel):
            stock_code: str
            start_date: str
            report_types: list[str]
            
            _validate_stock = field_validator('stock_code')(validate_stock_code)
            _validate_start = field_validator('start_date')(validate_date_yyyymmdd)
            _validate_types = field_validator('report_types')(validate_report_types)
        
        # Invalid stock code
        with pytest.raises(ValidationError) as exc_info:
            TestModel(
                stock_code='BAD',
                start_date='20240101',
                report_types=['A001']
            )
        
        # Check error contains field info
        error_dict = exc_info.value.errors()
        assert any(e['loc'] == ('stock_code',) for e in error_dict)
    
    def test_validators_provide_helpful_error_messages_through_pydantic(self):
        """Pydantic should preserve our custom error messages."""
        from dart_fss_text.validators import validate_report_types
        
        class TestModel(BaseModel):
            report_types: list[str]
            _validate_types = field_validator('report_types')(validate_report_types)
        
        try:
            TestModel(report_types=['Z999'])
        except ValidationError as e:
            error_msg = str(e)
            # Our custom error message should be preserved
            assert 'Invalid report type codes' in error_msg or 'Z999' in error_msg


class TestValidatorsEdgeCases:
    """Edge case tests for validators."""
    
    def test_validate_report_types_with_duplicates(self):
        """Should handle duplicate codes (allowed, but pass through)."""
        from dart_fss_text.validators import validate_report_types
        
        # Duplicates are valid - just pass through
        result = validate_report_types(['A001', 'A001', 'A002'])
        
        assert result == ['A001', 'A001', 'A002']
    
    def test_validate_stock_code_with_whitespace(self):
        """Should reject stock codes with whitespace."""
        from dart_fss_text.validators import validate_stock_code
        
        with pytest.raises(ValueError):
            validate_stock_code('005 930')
        
        with pytest.raises(ValueError):
            validate_stock_code(' 005930')
    
    def test_validate_date_with_whitespace(self):
        """Should reject dates with whitespace."""
        from dart_fss_text.validators import validate_date_yyyymmdd
        
        with pytest.raises(ValueError):
            validate_date_yyyymmdd('2024 0101')
        
        with pytest.raises(ValueError):
            validate_date_yyyymmdd(' 20240101')

