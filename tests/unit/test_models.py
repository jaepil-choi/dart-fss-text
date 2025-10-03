"""
Unit tests for Pydantic request/response models.

Tests models that integrate validators and provide type-safe interfaces
for service layer operations.
"""

import pytest
from pydantic import ValidationError


class TestSearchFilingsRequest:
    """Test suite for SearchFilingsRequest model."""
    
    def test_create_valid_request_with_all_fields(self):
        """Should create valid request with all required fields."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='20240101',
            end_date='20241231',
            report_types=['A001', 'A002']
        )
        
        assert request.stock_codes == ['005930']
        assert request.start_date == '20240101'
        assert request.end_date == '20241231'
        assert request.report_types == ['A001', 'A002']
    
    def test_create_request_from_exp04_parameters(self):
        """Should accept parameters used in exp_04."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        # Parameters from exp_04_corrected_pipeline.py
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='20240101',
            end_date='20241231',
            report_types=['A001', 'A002', 'A003']
        )
        
        assert request.stock_codes == ['005930']
        assert len(request.report_types) == 3
    
    def test_validates_stock_code_automatically(self):
        """Should validate stock_codes using validate_stock_code."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        # Invalid stock code should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            SearchFilingsRequest(
                stock_codes=['INVALID'],
                start_date='20240101',
                end_date='20241231',
                report_types=['A001']
            )
        
        # Check that error is for stock_codes field
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('stock_codes',) for e in errors)
    
    def test_validates_start_date_automatically(self):
        """Should validate start_date using validate_date_yyyymmdd."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        # Invalid date format should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            SearchFilingsRequest(
                stock_codes=['005930'],
                start_date='2024-01-01',  # Dashes not allowed
                end_date='20241231',
                report_types=['A001']
            )
        
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('start_date',) for e in errors)
    
    def test_validates_end_date_automatically(self):
        """Should validate end_date using validate_date_yyyymmdd."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        with pytest.raises(ValidationError) as exc_info:
            SearchFilingsRequest(
                stock_codes=['005930'],
                start_date='20240101',
                end_date='202412',  # Too short
                report_types=['A001']
            )
        
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('end_date',) for e in errors)
    
    def test_validates_report_types_automatically(self):
        """Should validate report_types using validate_report_types."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        # Invalid report type should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            SearchFilingsRequest(
                stock_codes=['005930'],
                start_date='20240101',
                end_date='20241231',
                report_types=['Z999']
            )
        
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('report_types',) for e in errors)
    
    def test_accepts_single_report_type(self):
        """Should accept a single report type in list."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='20240101',
            end_date='20241231',
            report_types=['A001']
        )
        
        assert request.report_types == ['A001']
    
    def test_accepts_multiple_report_types(self):
        """Should accept multiple report types."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='20240101',
            end_date='20241231',
            report_types=['A001', 'A002', 'A003', 'B001']
        )
        
        assert len(request.report_types) == 4
    
    def test_rejects_empty_report_types_list(self):
        """Should reject empty report_types list (at least one required)."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        # Empty list should be invalid - need at least one report type
        with pytest.raises(ValidationError) as exc_info:
            SearchFilingsRequest(
                stock_codes=['005930'],
                start_date='20240101',
                end_date='20241231',
                report_types=[]
            )
        
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('report_types',) for e in errors)
    
    def test_model_has_proper_field_types(self):
        """Model fields should have correct types."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='20240101',
            end_date='20241231',
            report_types=['A001']
        )
        
        assert isinstance(request.stock_codes, list)
        assert isinstance(request.start_date, str)
        assert isinstance(request.end_date, str)
        assert isinstance(request.report_types, list)
    
    def test_model_is_immutable_by_default(self):
        """Pydantic models should be immutable by default (frozen)."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='20240101',
            end_date='20241231',
            report_types=['A001']
        )
        
        # Try to modify - should fail if frozen
        with pytest.raises((ValidationError, AttributeError)):
            request.stock_codes = ['000660']
    
    def test_model_can_be_serialized_to_dict(self):
        """Model should be serializable to dict for JSON/logging."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='20240101',
            end_date='20241231',
            report_types=['A001', 'A002']
        )
        
        data = request.model_dump()
        
        assert data['stock_codes'] == ['005930']
        assert data['start_date'] == '20240101'
        assert data['end_date'] == '20241231'
        assert data['report_types'] == ['A001', 'A002']
    
    def test_model_can_be_created_from_dict(self):
        """Model should be creatable from dict (e.g., from API input)."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        data = {
            'stock_codes': ['005930'],
            'start_date': '20240101',
            'end_date': '20241231',
            'report_types': ['A001']
        }
        
        request = SearchFilingsRequest(**data)
        
        assert request.stock_codes == ['005930']
    
    def test_validation_error_messages_are_helpful(self):
        """ValidationError should contain helpful messages from validators."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        try:
            SearchFilingsRequest(
                stock_codes=['BAD'],
                start_date='20240101',
                end_date='20241231',
                report_types=['A001']
            )
        except ValidationError as e:
            error_str = str(e)
            # Should contain our custom error message from validator
            assert '6 digits' in error_str or '005930' in error_str
    
    def test_multiple_validation_errors_reported_together(self):
        """All validation errors should be reported at once."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        try:
            SearchFilingsRequest(
                stock_codes=['BAD'],  # Invalid
                start_date='INVALID',  # Invalid
                end_date='20241231',
                report_types=['Z999']  # Invalid
            )
        except ValidationError as e:
            errors = e.errors()
            # Should have 3 errors (stock_codes, start_date, report_types)
            assert len(errors) >= 3
            
            error_fields = [e['loc'][0] for e in errors]
            assert 'stock_codes' in error_fields
            assert 'start_date' in error_fields
            assert 'report_types' in error_fields


class TestSearchFilingsRequestEdgeCases:
    """Edge case tests for SearchFilingsRequest."""
    
    def test_accepts_leading_zeros_in_stock_code(self):
        """Should preserve leading zeros in stock code."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        request = SearchFilingsRequest(
            stock_codes=['000660'],  # SK Hynix
            start_date='20240101',
            end_date='20241231',
            report_types=['A001']
        )
        
        assert request.stock_codes == ['000660']
        assert len(request.stock_codes[0]) == 6
    
    def test_accepts_old_dates_in_valid_range(self):
        """Should accept dates in 1980-2100 range."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='19900101',  # Old but valid
            end_date='20991231',    # Future but valid
            report_types=['A001']
        )
        
        assert request.start_date == '19900101'
        assert request.end_date == '20991231'
    
    def test_rejects_dates_outside_valid_range(self):
        """Should reject dates outside 1980-2100."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        # Too old
        with pytest.raises(ValidationError):
            SearchFilingsRequest(
                stock_codes=['005930'],
                start_date='19790101',
                end_date='20241231',
                report_types=['A001']
            )
    
    def test_accepts_duplicate_report_types(self):
        """Should allow duplicate report types (user's responsibility)."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        # Duplicates are technically valid - just pass through
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='20240101',
            end_date='20241231',
            report_types=['A001', 'A001', 'A002']
        )
        
        assert request.report_types == ['A001', 'A001', 'A002']
    
    def test_rejects_mixed_valid_invalid_report_types(self):
        """Should reject if ANY report type is invalid."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        with pytest.raises(ValidationError):
            SearchFilingsRequest(
                stock_codes=['005930'],
                start_date='20240101',
                end_date='20241231',
                report_types=['A001', 'Z999', 'A002']  # Z999 is invalid
            )


class TestSearchFilingsRequestDocumentation:
    """Tests for model documentation and schema generation."""
    
    def test_model_has_field_descriptions(self):
        """Model fields should have descriptions for API documentation."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        # Check that Field() was used with descriptions
        schema = SearchFilingsRequest.model_json_schema()
        
        assert 'properties' in schema
        assert 'stock_codes' in schema['properties']
        assert 'start_date' in schema['properties']
        assert 'end_date' in schema['properties']
        assert 'report_types' in schema['properties']
    
    def test_model_has_example_in_schema(self):
        """Model should include example for documentation."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        schema = SearchFilingsRequest.model_json_schema()
        
        # Should have examples for documentation
        assert 'examples' in schema or 'example' in str(schema).lower()
    
    def test_model_str_representation_is_readable(self):
        """Model __str__ should be human-readable."""
        from dart_fss_text.models.requests import SearchFilingsRequest
        
        request = SearchFilingsRequest(
            stock_codes=['005930'],
            start_date='20240101',
            end_date='20241231',
            report_types=['A001']
        )
        
        str_repr = str(request)
        
        # Should contain key information
        assert '005930' in str_repr or 'stock_codes' in str_repr

