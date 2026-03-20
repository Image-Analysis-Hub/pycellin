#!/usr/bin/env python3

"""Unit test for TrackMate XML file exporter."""

import pytest

from pycellin.classes import CellLineage, Data, Model, Property, PropsMetadata
from pycellin.graph.properties.core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_lineage_id_property,
    create_timepoint_property,
)
from pycellin.io.trackmate.exporter import (
    _is_numeric_dtype,
    _remove_non_numeric_props,
)


# Fixtures ####################################################################


@pytest.fixture
def simple_model():
    """Create a simple model for testing."""
    lin1 = CellLineage()
    lin1.add_node(1, timepoint=0, cell_x=1.0, cell_y=1.5, lineage_ID=0, cell_ID=1)
    lin1.add_node(2, timepoint=1, cell_x=2.0, cell_y=2.5, lineage_ID=0, cell_ID=2)
    lin1.add_edge(1, 2)
    lin1.graph["lineage_ID"] = 0

    cell_data = {0: lin1}
    data = Data(cell_data)
    props_metadata = PropsMetadata()
    props_metadata._add_prop(create_timepoint_property())
    props_metadata._add_prop(create_cell_coord_property(axis="x", unit="pixel"))
    props_metadata._add_prop(create_cell_coord_property(axis="y", unit="pixel"))
    props_metadata._add_prop(create_lineage_id_property())
    props_metadata._add_prop(create_cell_id_property())

    model = Model(
        data=data,
        props_metadata=props_metadata,
        reference_time_property="timepoint",
    )
    return model


@pytest.fixture
def numeric_float64_prop():
    """Numeric property with numpy-style dtype."""
    return Property(
        identifier="intensity",
        name="Intensity",
        description="Cell intensity",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float64",
        unit=None,
    )


@pytest.fixture
def numeric_float32_prop():
    """Numeric property with unit."""
    return Property(
        identifier="area",
        name="Area",
        description="Cell area",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float32",
        unit="pixel",
    )


@pytest.fixture
def bool_prop():
    """Boolean property."""
    return Property(
        identifier="is_division",
        name="Is division",
        description="Whether the cell is dividing",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="bool",
        unit=None,
    )


@pytest.fixture
def string_prop():
    """Non-numeric string property."""
    return Property(
        identifier="label",
        name="Label",
        description="Cell label",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="string",
        unit=None,
    )


@pytest.fixture
def trackmate_string_prop():
    """Non-numeric string property with TrackMate provenance."""
    return Property(
        identifier="name",
        name="Name",
        description="Spot name",
        provenance="TrackMate",
        prop_type="node",
        lin_type="CellLineage",
        dtype="string",
        unit=None,
    )


@pytest.fixture
def object_prop():
    """Non-numeric object property."""
    return Property(
        identifier="category",
        name="Category",
        description="Cell category",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="object",
        unit=None,
    )


@pytest.fixture
def dict_prop():
    """Non-numeric dict property."""
    return Property(
        identifier="metadata",
        name="Metadata",
        description="Cell metadata",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="dict",
        unit=None,
    )


@pytest.fixture
def list_prop():
    """Non-numeric list property."""
    return Property(
        identifier="tags",
        name="Tags",
        description="Cell tags",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="list",
        unit=None,
    )


# Test Classes ################################################################


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

    def test_empty_string(self):
        """Test empty string returns False."""
        assert _is_numeric_dtype("") is False


class TestRemoveNonNumericProps:
    """Test cases for _remove_non_numeric_props function."""

    def test_preserves_numeric_properties(self, simple_model, numeric_float64_prop):
        """Test that numeric properties are preserved, numpy-style or not."""
        simple_model.props_metadata._add_prop(numeric_float64_prop)
        assert "intensity" in simple_model.get_properties()

        _remove_non_numeric_props(simple_model)

        assert "timepoint" in simple_model.get_properties()
        assert "cell_x" in simple_model.get_properties()
        assert "cell_y" in simple_model.get_properties()
        assert "intensity" in simple_model.get_properties()

    def test_removes_string_properties(self, simple_model, string_prop):
        """Test that string properties are removed."""
        simple_model.props_metadata._add_prop(string_prop)
        assert "label" in simple_model.get_properties()

        _remove_non_numeric_props(simple_model)

        assert "label" not in simple_model.get_properties()

    def test_preserves_properties_coming_from_trackmate(
        self, simple_model, trackmate_string_prop
    ):
        """Test that properties coming from TrackMate are never removed."""
        simple_model.props_metadata._add_prop(trackmate_string_prop)
        assert "name" in simple_model.get_properties()

        _remove_non_numeric_props(simple_model)

        assert "name" in simple_model.get_properties()

    def test_mixed_numeric_and_non_numeric(
        self, simple_model, numeric_float32_prop, object_prop
    ):
        """Test with a mix of numeric and non-numeric properties."""
        simple_model.props_metadata._add_prop(numeric_float32_prop)
        simple_model.props_metadata._add_prop(object_prop)

        _remove_non_numeric_props(simple_model)

        assert "area" in simple_model.get_properties()
        assert "category" not in simple_model.get_properties()

    def test_handles_protected_properties(self, simple_model, dict_prop):
        """Test that protected properties can still be removed if non-numeric."""
        simple_model.props_metadata._add_prop(dict_prop)
        simple_model.props_metadata._protect_prop("metadata")

        _remove_non_numeric_props(simple_model)

        assert "metadata" not in simple_model.get_properties()

    def test_warns_about_removed_properties(self, simple_model, string_prop, list_prop):
        """Test that warnings are issued for removed properties."""
        simple_model.props_metadata._add_prop(string_prop)
        simple_model.props_metadata._add_prop(list_prop)

        with pytest.warns(UserWarning, match="Ignoring propertys: label, tags"):
            _remove_non_numeric_props(simple_model)

    def test_bool_dtype_preserved(self, simple_model, bool_prop):
        """Test that boolean dtypes are preserved as numeric."""
        simple_model.props_metadata._add_prop(bool_prop)

        _remove_non_numeric_props(simple_model)

        assert "is_division" in simple_model.get_properties()
