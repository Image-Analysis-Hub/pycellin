#!/usr/bin/env python3

"""Unit tests for utils.py module."""

from pycellin.utils import _is_numeric_dtype


class TestIsNumericDtype:
    """Test cases for _is_numeric_dtype function."""

    def test_none_returns_false(self):
        """Test that None dtype returns False."""
        assert _is_numeric_dtype(None) is False

    def test_basic_integer_types(self):
        """Test basic integer type strings."""
        assert _is_numeric_dtype("int") is True
        assert _is_numeric_dtype("integer") is True
        assert _is_numeric_dtype("Int") is True
        assert _is_numeric_dtype("INTEGER") is True

    def test_basic_float_types(self):
        """Test basic float type strings."""
        assert _is_numeric_dtype("float") is True
        assert _is_numeric_dtype("Float") is True
        assert _is_numeric_dtype("FLOAT") is True
        assert _is_numeric_dtype("real") is True
        assert _is_numeric_dtype("number") is True
        assert _is_numeric_dtype("numeric") is True

    def test_basic_bool_types(self):
        """Test basic boolean type strings."""
        assert _is_numeric_dtype("bool") is True
        assert _is_numeric_dtype("boolean") is True
        assert _is_numeric_dtype("Bool") is True
        assert _is_numeric_dtype("BOOLEAN") is True

    def test_complex_and_special_types(self):
        """Test complex and special numeric types."""
        assert _is_numeric_dtype("complex") is True
        assert _is_numeric_dtype("fraction") is True
        assert _is_numeric_dtype("decimal") is True
        assert _is_numeric_dtype("rational") is True

    def test_numpy_integer_types(self):
        """Test numpy integer dtypes."""
        assert _is_numeric_dtype("int8") is True
        assert _is_numeric_dtype("int16") is True
        assert _is_numeric_dtype("int32") is True
        assert _is_numeric_dtype("int64") is True
        assert _is_numeric_dtype("uint") is True
        assert _is_numeric_dtype("uint8") is True
        assert _is_numeric_dtype("uint16") is True
        assert _is_numeric_dtype("uint32") is True
        assert _is_numeric_dtype("uint64") is True

    def test_numpy_float_types(self):
        """Test numpy float dtypes."""
        assert _is_numeric_dtype("float16") is True
        assert _is_numeric_dtype("float32") is True
        assert _is_numeric_dtype("float64") is True
        assert _is_numeric_dtype("float128") is True

    def test_mixed_case_numpy_types(self):
        """Test numpy dtypes with mixed case."""
        assert _is_numeric_dtype("Float64") is True
        assert _is_numeric_dtype("INT32") is True
        assert _is_numeric_dtype("UInt8") is True

    def test_non_numeric_types(self):
        """Test non-numeric type strings."""
        assert _is_numeric_dtype("string") is False
        assert _is_numeric_dtype("str") is False
        assert _is_numeric_dtype("object") is False
        assert _is_numeric_dtype("list") is False
        assert _is_numeric_dtype("dict") is False
        assert _is_numeric_dtype("array") is False
        assert _is_numeric_dtype("shapely.Polygon") is False

    def test_empty_string(self):
        """Test empty string returns False."""
        assert _is_numeric_dtype("") is False
