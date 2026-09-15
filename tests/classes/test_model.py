#!/usr/bin/env python3

"""Unit tests for Model class from model.py module."""

from unittest.mock import MagicMock

import pytest

from pycellin.classes import CellLineage, Data, Model, Property, PropsMetadata
from pycellin.custom_types import PropertyType
from pycellin.graph.properties.core import (
    Time,
    create_cell_coord_property,
    create_lineage_coord_property,
    create_link_coord_property,
    create_time_property,
)
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


@pytest.fixture()
def lineage_props_model():
    """
    Create a model with a dividing lineage and a single-cell lineage, and properties
    of lineage, node and node-and-lineage types.
    """
    lin = CellLineage(lid=1)
    lin.add_node(1, cell_ID=1, frame=0, node_prop=10, mixed_prop="node1")
    lin.add_node(2, cell_ID=2, frame=1, node_prop=20, mixed_prop="node2")
    lin.add_node(3, cell_ID=3, frame=1, node_prop=30, mixed_prop="node3")
    lin.add_edge(1, 2)
    lin.add_edge(1, 3)
    lin.graph["lin_prop"] = 1.5
    lin.graph["shared_prop"] = "a"
    lin.graph["mixed_prop"] = "lineage1"
    single_lin = CellLineage(lid=-4)
    single_lin.add_node(4, cell_ID=4, frame=0, node_prop=40, mixed_prop="node4")
    single_lin.graph["lin_prop"] = 2.5
    single_lin.graph["mixed_prop"] = "lineage-4"

    def make_prop(identifier, prop_type, lin_type):
        return Property(
            identifier=identifier,
            name=identifier,
            description=f"{identifier} for testing",
            provenance="test",
            prop_type=prop_type,
            lin_type=lin_type,
            dtype="float",
        )

    props_md = PropsMetadata(
        props={
            "lin_prop": make_prop("lin_prop", PropertyType.LINEAGE, "CellLineage"),
            "shared_prop": make_prop("shared_prop", PropertyType.LINEAGE, "Lineage"),
            "node_prop": make_prop("node_prop", PropertyType.NODE, "CellLineage"),
            "mixed_prop": make_prop(
                "mixed_prop", PropertyType.NODE | PropertyType.LINEAGE, "CellLineage"
            ),
            "cycle_prop": make_prop("cycle_prop", PropertyType.LINEAGE, "CycleLineage"),
        }
    )
    return Model(
        model_metadata={"time_step": 1},
        props_metadata=props_md,
        data=Data({1: lin, -4: single_lin}),
        reference_time_property="frame",
    )


class TestToCellDataframe:
    """Test cases for Model.to_cell_dataframe() method."""

    def test_lineage_props_added_as_columns(self, lineage_props_model):
        df = lineage_props_model.to_cell_dataframe(
            lineage_props=["lin_prop", "shared_prop"]
        )

        lin_rows = df[df["lineage_ID"] == 1]
        single_rows = df[df["lineage_ID"] == -4]
        assert len(lin_rows) == 3
        assert (lin_rows["lin_prop"] == 1.5).all()
        assert (lin_rows["shared_prop"] == "a").all()
        assert single_rows["lin_prop"].tolist() == [2.5]
        assert single_rows["shared_prop"].isna().all()

    def test_lineage_props_none_adds_no_column(self, lineage_props_model):
        df = lineage_props_model.to_cell_dataframe()

        assert "lin_prop" not in df.columns
        assert "shared_prop" not in df.columns

    def test_lineage_ID_lineage_prop_is_skipped(self, lineage_props_model):
        df = lineage_props_model.to_cell_dataframe(lineage_props=["lineage_ID"])

        assert df.equals(lineage_props_model.to_cell_dataframe())

    def test_lineage_props_restricted_to_lids(self, lineage_props_model):
        df = lineage_props_model.to_cell_dataframe(
            lids=[-4], lineage_props=["lin_prop"]
        )

        assert df["lin_prop"].tolist() == [2.5]

    def test_lineage_prop_clashing_with_column_raises(self, lineage_props_model):
        with pytest.raises(ValueError, match="existing columns.*'mixed_prop'"):
            lineage_props_model.to_cell_dataframe(lineage_props=["mixed_prop"])

    def test_invalid_lineage_props_raise(self, lineage_props_model):
        with pytest.raises(
            ValueError,
            match="declared in the model: 'node_prop', 'cycle_prop', 'unknown'",
        ):
            lineage_props_model.to_cell_dataframe(
                lineage_props=["node_prop", "cycle_prop", "unknown", "lin_prop"]
            )

    def test_missing_mandatory_cell_prop_raises(self, lineage_props_model):
        for lin in lineage_props_model.data.cell_data.values():
            for nid in lin.nodes:
                del lin.nodes[nid]["cell_ID"]
        with pytest.raises(ValueError, match="not found in the model: 'cell_ID'"):
            lineage_props_model.to_cell_dataframe()


class TestToLinkDataframe:
    """Test cases for Model.to_link_dataframe() method."""

    def test_lineage_props_added_as_columns(self, lineage_props_model):
        df = lineage_props_model.to_link_dataframe(lineage_props=["lin_prop"])

        assert df["lin_prop"].tolist() == [1.5, 1.5]

    def test_node_and_lineage_prop_added_when_not_a_column(self, lineage_props_model):
        df = lineage_props_model.to_link_dataframe(lineage_props=["mixed_prop"])

        assert df["mixed_prop"].tolist() == ["lineage1", "lineage1"]

    def test_invalid_lineage_props_raise(self, lineage_props_model):
        with pytest.raises(ValueError, match="declared in the model: 'node_prop'"):
            lineage_props_model.to_link_dataframe(lineage_props=["node_prop"])


class TestToLineageDataframe:
    """Test cases for Model.to_lineage_dataframe() method."""

    def test_missing_lineage_ID_raises(self, lineage_props_model):
        for lin in lineage_props_model.data.cell_data.values():
            del lin.graph["lineage_ID"]
        with pytest.raises(ValueError, match="not found in the model: 'lineage_ID'"):
            lineage_props_model.to_lineage_dataframe()


class TestToCycleDataframe:
    """Test cases for Model.to_cycle_dataframe() method."""

    def test_lineage_props_added_as_columns(self, lineage_props_model):
        model = lineage_props_model
        model.add_cycle_data()
        df = model.to_cycle_dataframe(lineage_props=["lin_prop"])

        lin_rows = df[df["lineage_ID"] == 1]
        assert len(lin_rows) == 3
        assert (lin_rows["lin_prop"] == 1.5).all()
        assert df.loc[df["lineage_ID"] == -4, "lin_prop"].tolist() == [2.5]


@pytest.fixture()
def frame_time_model():
    """
    Create a model with a dividing lineage whose reference time property "time" is
    given in frames, with a time origin different from 0.
    """
    lin = CellLineage(lid=1)
    lin.add_node(1, cell_ID=1, time=3)
    lin.add_node(2, cell_ID=2, time=4)
    lin.add_node(3, cell_ID=3, time=5)
    lin.add_node(4, cell_ID=4, time=5)
    lin.add_edge(1, 2)
    lin.add_edge(2, 3)
    lin.add_edge(2, 4)

    time_prop = create_time_property(unit="frame")
    time_prop.dtype = "int"
    return Model(
        model_metadata={"time_step": 1, "time_unit": "frame"},
        props_metadata=PropsMetadata(props={"time": time_prop}),
        data=Data({1: lin}),
        reference_time_property="time",
    )


class TestRescaleTime:
    """Test cases for Model.rescale_time() method."""

    def test_time_values_multiplied(self, frame_time_model):
        frame_time_model.rescale_time(5)
        lin = frame_time_model.data.cell_data[1]
        assert dict(lin.nodes(data="time")) == {1: 15, 2: 20, 3: 25, 4: 25}

    def test_time_step_multiplied(self, frame_time_model):
        frame_time_model.rescale_time(5)
        assert frame_time_model.get_time_step() == 5

    def test_update_required(self, frame_time_model):
        frame_time_model.rescale_time(5)
        assert frame_time_model.is_update_required()

    def test_timepoints_unchanged_after_update(self, frame_time_model):
        lin = frame_time_model.data.cell_data[1]
        timepoints = dict(lin.nodes(data="timepoint"))
        frame_time_model.rescale_time(5)
        frame_time_model.update()
        lin = frame_time_model.data.cell_data[1]
        assert dict(lin.nodes(data="timepoint")) == timepoints

    def test_timepoints_unchanged_after_partial_update(self, frame_time_model):
        lin = frame_time_model.data.cell_data[1]
        timepoints = dict(lin.nodes(data="timepoint"))
        frame_time_model.rescale_time(5)
        time_copy_prop = create_time_property(unit=None, custom_identifier="time_copy")
        calc = Time(time_copy_prop, base_time_prop="time", factor=1)
        frame_time_model.add_custom_property(calc)
        frame_time_model.update(["time_copy"])
        lin = frame_time_model.data.cell_data[1]
        assert dict(lin.nodes(data="timepoint")) == timepoints
        assert dict(lin.nodes(data="time_copy")) == {1: 15, 2: 20, 3: 25, 4: 25}

    def test_time_unit_set(self, frame_time_model):
        frame_time_model.rescale_time(5, time_unit="min")
        assert frame_time_model.get_time_unit() == "min"
        assert frame_time_model.get_property("time").unit == "min"

    def test_no_time_unit_keeps_units(self, frame_time_model):
        frame_time_model.rescale_time(5)
        assert frame_time_model.get_time_unit() == "frame"
        assert frame_time_model.get_property("time").unit == "frame"

    def test_float_factor_sets_float_dtype(self, frame_time_model):
        frame_time_model.rescale_time(0.5)
        assert frame_time_model.get_property("time").dtype == "float"

    def test_int_factor_keeps_int_dtype(self, frame_time_model):
        frame_time_model.rescale_time(5)
        assert frame_time_model.get_property("time").dtype == "int"

    def test_cycle_duration_rescaled(self, frame_time_model):
        frame_time_model.add_cycle_data()
        durations = dict(frame_time_model.data.cycle_data[1].nodes(data="cycle_duration"))
        frame_time_model.rescale_time(5, time_unit="min")
        frame_time_model.update()
        cycle_lin = frame_time_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="cycle_duration")) == {
            cid: duration * 5 for cid, duration in durations.items()
        }
        assert frame_time_model.get_property("cycle_duration").unit == "min"

    def test_zero_factor_raises(self, frame_time_model):
        with pytest.raises(ValueError, match="strictly positive"):
            frame_time_model.rescale_time(0)

    def test_negative_factor_raises(self, frame_time_model):
        with pytest.raises(ValueError, match="strictly positive"):
            frame_time_model.rescale_time(-5)

    def test_timepoint_reference_time_raises(self):
        model = MagicMock()
        model.reference_time_property = "timepoint"
        with pytest.raises(ValueError, match="Cannot rescale the 'timepoint'"):
            Model.rescale_time(model, 5)

    def test_reference_time_calculator_warns(self, frame_time_model):
        calc = Time(create_time_property(unit=None), base_time_prop="timepoint", factor=5)
        frame_time_model._updater.register_calculator(calc)
        with pytest.warns(UserWarning, match="has a calculator"):
            frame_time_model.rescale_time(5)


@pytest.fixture()
def pixel_space_model():
    """
    Create a 3D model with a two-cell lineage whose cell, link and lineage coordinates
    are given in pixels.
    """
    lin = CellLineage(lid=1)
    lin.add_node(1, cell_ID=1, frame=0, cell_x=10, cell_y=20, cell_z=2)
    lin.add_node(2, cell_ID=2, frame=1, cell_x=30, cell_y=40, cell_z=4)
    lin.add_edge(1, 2, link_x=20, link_y=30, link_z=3)
    lin.graph.update(lineage_x=20, lineage_y=30, lineage_z=3)

    props = {}
    for axis in ("x", "y", "z"):
        for create_prop in (
            create_cell_coord_property,
            create_link_coord_property,
            create_lineage_coord_property,
        ):
            prop = create_prop(unit="pixel", axis=axis)
            props[prop.identifier] = prop
    props["cell_x"].dtype = "int"
    return Model(
        model_metadata={
            "time_step": 1,
            "space_unit": "pixel",
            "pixel_width": 1.0,
            "pixel_height": 1.0,
            "pixel_depth": 2.0,
        },
        props_metadata=PropsMetadata(props=props),
        data=Data({1: lin}),
        reference_time_property="frame",
    )


class TestRescaleSpace:
    """Test cases for Model.rescale_space() method."""

    def test_cell_coordinates_multiplied(self, pixel_space_model):
        pixel_space_model.rescale_space(2)
        lin = pixel_space_model.data.cell_data[1]
        assert lin.nodes[1]["cell_x"] == 20
        assert lin.nodes[1]["cell_y"] == 40
        assert lin.nodes[1]["cell_z"] == 4

    def test_z_factor_applied_to_z_only(self, pixel_space_model):
        pixel_space_model.rescale_space(2, z_factor=10)
        lin = pixel_space_model.data.cell_data[1]
        assert lin.nodes[2]["cell_x"] == 60
        assert lin.nodes[2]["cell_z"] == 40
        assert lin.edges[1, 2]["link_z"] == 30
        assert lin.graph["lineage_z"] == 30

    def test_link_coordinates_multiplied(self, pixel_space_model):
        pixel_space_model.rescale_space(2)
        lin = pixel_space_model.data.cell_data[1]
        assert lin.edges[1, 2]["link_x"] == 40
        assert lin.edges[1, 2]["link_y"] == 60

    def test_lineage_coordinates_multiplied(self, pixel_space_model):
        pixel_space_model.rescale_space(2)
        lin = pixel_space_model.data.cell_data[1]
        assert lin.graph["lineage_x"] == 40
        assert lin.graph["lineage_y"] == 60

    def test_pixel_size_multiplied(self, pixel_space_model):
        pixel_space_model.rescale_space(0.5, z_factor=3)
        assert pixel_space_model.get_pixel_width() == 0.5
        assert pixel_space_model.get_pixel_height() == 0.5
        assert pixel_space_model.get_pixel_depth() == 6.0

    def test_undefined_pixel_size_stays_undefined(self, pixel_space_model):
        pixel_space_model.model_metadata.pixel_depth = None
        pixel_space_model.rescale_space(2)
        assert pixel_space_model.get_pixel_depth() is None

    def test_space_unit_set(self, pixel_space_model):
        pixel_space_model.rescale_space(0.5, space_unit="um")
        assert pixel_space_model.get_space_unit() == "um"
        for prop_id in ("cell_x", "link_y", "lineage_z"):
            assert pixel_space_model.get_property(prop_id).unit == "um"

    def test_no_space_unit_keeps_units(self, pixel_space_model):
        pixel_space_model.rescale_space(0.5)
        assert pixel_space_model.get_space_unit() == "pixel"
        assert pixel_space_model.get_property("cell_x").unit == "pixel"

    def test_float_factor_sets_float_dtype(self, pixel_space_model):
        pixel_space_model.rescale_space(0.5)
        assert pixel_space_model.get_property("cell_x").dtype == "float"

    def test_update_required(self, pixel_space_model):
        pixel_space_model.rescale_space(2)
        assert pixel_space_model.is_update_required()

    def test_zero_factor_raises(self, pixel_space_model):
        with pytest.raises(ValueError, match="`factor` must be strictly positive"):
            pixel_space_model.rescale_space(0)

    def test_negative_z_factor_raises(self, pixel_space_model):
        with pytest.raises(ValueError, match="`z_factor` must be strictly positive"):
            pixel_space_model.rescale_space(2, z_factor=-1)

    def test_coordinate_calculator_warns(self, pixel_space_model):
        prop = create_cell_coord_property(unit=None, axis="x")
        calc = Time(prop, base_time_prop="frame", factor=1)
        pixel_space_model._updater.register_calculator(calc)
        with pytest.warns(UserWarning, match="'cell_x' has a calculator"):
            pixel_space_model.rescale_space(2)
