#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit tests for Model class from model.py module."""

from unittest.mock import MagicMock

import pytest

from pycellin.classes import Model, Property
from pycellin.custom_types import PropertyType
from pycellin.graph.properties.tracking import (
    create_absolute_age_property,
    create_division_time_property,
)


@pytest.fixture()
def props_dict():
    """
    Create a dictionary of properties for testing using predefined property creators.
    """
    division_time_prop = create_division_time_property()
    absolute_age_prop = create_absolute_age_property()

    edge_prop = Property(
        identifier="edge_prop",
        name="Edge property",
        description="Edge property for testing",
        provenance="test",
        prop_type=PropertyType.EDGE,
        lin_type="CycleLineage",
        dtype="float",
    )

    lin_prop = Property(
        identifier="lineage_prop",
        name="Lineage property",
        description="Lineage property for testing",
        provenance="test",
        prop_type=PropertyType.LINEAGE,
        lin_type="CycleLineage",
        dtype="bool",
    )

    mixed_prop = Property(
        identifier="mixed_prop",
        name="Mixed property",
        description="Multi-type property for testing",
        provenance="test",
        prop_type=PropertyType.NODE | PropertyType.EDGE,
        lin_type="CycleLineage",
        dtype="float",
    )

    return {
        "division_time": division_time_prop,
        "absolute_age": absolute_age_prop,
        "edge_prop": edge_prop,
        "lineage_prop": lin_prop,
        "mixed_prop": mixed_prop,
    }


class TestCategorizePropsMockModel:
    """Test cases for Model._categorize_props() method using mocked Model."""

    def test_categorize_props_specific_subset(self, props_dict):
        """Test that only requested properties are categorized, not all available ones."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = props_dict
        model.get_node_properties.return_value = {
            k: v for k, v in props_dict.items() if PropertyType.NODE in v.prop_type
        }
        model.get_edge_properties.return_value = {
            k: v for k, v in props_dict.items() if PropertyType.EDGE in v.prop_type
        }
        model.get_lineage_properties.return_value = {
            k: v for k, v in props_dict.items() if PropertyType.LINEAGE in v.prop_type
        }

        props_to_categorize = ["division_time", "edge_prop"]  # only a subset
        node_props, edge_props, lin_props = Model._categorize_props(
            model, props_to_categorize
        )

        assert node_props == ["division_time"]
        assert edge_props == ["edge_prop"]
        assert lin_props == []

    def test_categorize_props_none_all_properties(self, props_dict):
        """Test categorization when props=None (should categorize all properties)."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = props_dict
        node_props, edge_props, lin_props = Model._categorize_props(model, None)

        expected_node_props = {"division_time", "absolute_age", "mixed_prop"}
        expected_edge_props = {"edge_prop", "mixed_prop"}

        assert set(node_props) == expected_node_props
        assert set(edge_props) == expected_edge_props
        assert lin_props == ["lineage_prop"]

    def test_categorize_props_invalid_properties(self, props_dict):
        """Test that multiple invalid properties are reported in the error."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = props_dict

        invalid_props = ["invalid1", "invalid2", "division_time"]

        with pytest.raises(
            ValueError,
            match="'invalid1', 'invalid2' are either not cycle lineage properties",
        ):
            Model._categorize_props(model, invalid_props)

    def test_categorize_props_empty_list(self, props_dict):
        """Test categorization with an empty list of properties."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = props_dict
        node_props, edge_props, lin_props = Model._categorize_props(model, [])

        assert node_props == []
        assert edge_props == []
        assert lin_props == []

    def test_categorize_props_no_cycle_properties(self):
        """Test categorization when there are no cycle lineage properties."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = {}
        node_props, edge_props, lin_props = Model._categorize_props(model, None)

        assert node_props == []
        assert edge_props == []
        assert lin_props == []

    def test_categorize_props_mixed_type_property(self, props_dict):
        """Test that properties with multiple types appear in multiple categories."""
        model = MagicMock(spec=Model)
        single_mixed_prop = {"mixed_prop": props_dict["mixed_prop"]}
        model.get_cycle_lineage_properties.return_value = single_mixed_prop
        node_props, edge_props, lin_props = Model._categorize_props(model, None)

        assert "mixed_prop" in node_props
        assert "mixed_prop" in edge_props
        assert "mixed_prop" not in lin_props
