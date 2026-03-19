#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit tests for custom_types.py module."""

import pytest

from pycellin.custom_types import (
    PropertyType,
    property_type_from_string,
    property_type_to_strings,
)


class TestPropertyType:
    """Tests for PropertyType Flag enum."""

    def test_property_type_node(self):
        """Test PropertyType.NODE flag."""
        assert PropertyType.NODE.value == 1
        assert PropertyType.NODE.name == "NODE"

    def test_property_type_edge(self):
        """Test PropertyType.EDGE flag."""
        assert PropertyType.EDGE.value == 2
        assert PropertyType.EDGE.name == "EDGE"

    def test_property_type_lineage(self):
        """Test PropertyType.LINEAGE flag."""
        assert PropertyType.LINEAGE.value == 4
        assert PropertyType.LINEAGE.name == "LINEAGE"

    def test_property_type_combination(self):
        """Test combining PropertyType flags with bitwise OR."""
        combined = PropertyType.NODE | PropertyType.EDGE
        assert PropertyType.NODE in combined
        assert PropertyType.EDGE in combined
        assert PropertyType.LINEAGE not in combined

    def test_property_type_all_combination(self):
        """Test combining all PropertyType flags."""
        combined = PropertyType.NODE | PropertyType.EDGE | PropertyType.LINEAGE
        assert PropertyType.NODE in combined
        assert PropertyType.EDGE in combined
        assert PropertyType.LINEAGE in combined

    def test_property_type_empty_flag(self):
        """Test empty/zero PropertyType flag."""
        empty = PropertyType(0)
        assert PropertyType.NODE not in empty
        assert PropertyType.EDGE not in empty
        assert PropertyType.LINEAGE not in empty
        assert not bool(empty)


class TestPropertyTypeFromString:
    """Tests for property_type_from_string() function."""

    def test_from_string_node(self):
        """Test converting 'node' string to PropertyType.NODE."""
        result = property_type_from_string("node")
        assert result == PropertyType.NODE

    def test_from_string_edge(self):
        """Test converting 'edge' string to PropertyType.EDGE."""
        result = property_type_from_string("edge")
        assert result == PropertyType.EDGE

    def test_from_string_lineage(self):
        """Test converting 'lineage' string to PropertyType.LINEAGE."""
        result = property_type_from_string("lineage")
        assert result == PropertyType.LINEAGE

    def test_from_string_list_single_type(self):
        """Test converting list with single type string."""
        result = property_type_from_string(["node"])
        assert result == PropertyType.NODE

    def test_from_string_list_two_types(self):
        """Test converting list with two type strings."""
        result = property_type_from_string(["node", "edge"])
        assert result == (PropertyType.NODE | PropertyType.EDGE)

    def test_from_string_list_all_types(self):
        """Test converting list with all type strings."""
        result = property_type_from_string(["node", "edge", "lineage"])
        assert result == (PropertyType.NODE | PropertyType.EDGE | PropertyType.LINEAGE)

    def test_from_string_list_different_order(self):
        """Test that order doesn't matter in list conversion."""
        result1 = property_type_from_string(["node", "lineage"])
        result2 = property_type_from_string(["lineage", "node"])
        assert result1 == result2

    def test_from_string_invalid_string(self):
        """Test that invalid string raises KeyError."""
        with pytest.raises(KeyError):
            property_type_from_string("invalid")

    def test_from_string_invalid_string_in_list(self):
        """Test that invalid string in list raises KeyError."""
        with pytest.raises(KeyError):
            property_type_from_string(["node", "invalid"])

    def test_from_string_empty_list(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="Property type list cannot be empty"):
            property_type_from_string([])

    def test_from_string_invalid_type(self):
        """Test that invalid input type raises TypeError."""
        with pytest.raises(TypeError, match="Expected str or list\\[str\\]"):
            property_type_from_string(123)

    def test_from_string_none_input(self):
        """Test that None input raises TypeError."""
        with pytest.raises(TypeError, match="Expected str or list\\[str\\]"):
            property_type_from_string(None)


class TestPropertyTypeToStrings:
    """Tests for property_type_to_strings() function."""

    def test_to_strings_node(self):
        """Test converting PropertyType.NODE to 'node' string."""
        result = property_type_to_strings(PropertyType.NODE)
        assert result == "node"
        assert isinstance(result, str)

    def test_to_strings_edge(self):
        """Test converting PropertyType.EDGE to 'edge' string."""
        result = property_type_to_strings(PropertyType.EDGE)
        assert result == "edge"

    def test_to_strings_lineage(self):
        """Test converting PropertyType.LINEAGE to 'lineage' string."""
        result = property_type_to_strings(PropertyType.LINEAGE)
        assert result == "lineage"

    def test_to_strings_combined_two_types(self):
        """Test converting combined PropertyType to list of strings."""
        combined = PropertyType.NODE | PropertyType.EDGE
        result = property_type_to_strings(combined)
        assert isinstance(result, list)
        assert "node" in result
        assert "edge" in result
        assert "lineage" not in result

    def test_to_strings_combined_all_types(self):
        """Test converting all combined types to list."""
        combined = PropertyType.NODE | PropertyType.EDGE | PropertyType.LINEAGE
        result = property_type_to_strings(combined)
        assert isinstance(result, list)
        assert len(result) == 3
        assert set(result) == {"node", "edge", "lineage"}


class TestRoundTripConversion:
    """Tests for round-trip conversion between strings and PropertyType."""

    def test_round_trip_single_string(self):
        """Test converting string -> PropertyType -> string."""
        original = "node"
        prop_type = property_type_from_string(original)
        result = property_type_to_strings(prop_type)
        assert result == original

    def test_round_trip_single_type_list(self):
        """Test converting list -> PropertyType -> list."""
        original = ["edge"]
        prop_type = property_type_from_string(original)
        result = property_type_to_strings(prop_type)
        assert result == "edge"

    def test_round_trip_multi_type_list(self):
        """Test converting multi-type list -> PropertyType -> list."""
        original = ["node", "lineage"]
        prop_type = property_type_from_string(original)
        result = property_type_to_strings(prop_type)
        assert isinstance(result, list)
        assert set(result) == set(original)
