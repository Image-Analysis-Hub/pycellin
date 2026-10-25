"""Unit test for GEFF file exporter."""

import logging

import geff
import geff_spec
import pytest

from pycellin.classes import CellLineage, Data, Model, Property, PropsMetadata
from pycellin.classes.exceptions import UpdateRequiredError
from pycellin.properties.core import (
    create_cell_coord_property,
    create_frame_property,
    create_lineage_id_property,
    create_link_coord_property,
    create_timepoint_property,
)
from pycellin.properties.motion import create_cell_displacement_property
from pycellin.properties.tracking import (
    create_absolute_age_property,
)
from pycellin.io.geff.exporter import (
    _build_axes,
    _build_display_hints,
    _build_geff_metadata,
    _build_props_metadata,
    _find_node_overlaps,
    _get_default_space_axes,
    _get_next_available_id,
    _relabel_nodes,
    _remove_none_values,
    _remove_unsupported_props,
    _solve_node_overlaps,
    _to_geff_dtype,
    export_GEFF,
)
from pycellin.io.geff.loader import load_GEFF

# Fixtures ####################################################################


@pytest.fixture
def lineage1():
    lin = CellLineage()
    lin.add_nodes_from([1, 2, 3, 4, 5])
    lin.add_edges_from([(1, 2), (2, 3), (3, 4), (3, 5)])
    lin.graph["lineage_id"] = 0
    return lin


@pytest.fixture
def lineage2():
    lin = CellLineage()
    lin.add_nodes_from([10, 11, 12, 13])
    lin.add_edges_from([(10, 11), (11, 12), (12, 13)])
    lin.graph["lineage_id"] = 1
    return lin


@pytest.fixture
def lineage3():
    lin = CellLineage()
    lin.add_nodes_from([20, 21, 22])
    lin.add_edges_from([(20, 21), (21, 22)])
    lin.graph["lineage_id"] = 2
    return lin


@pytest.fixture
def node_props():
    """Create a dictionary of node properties for testing."""
    return {
        "timepoint": create_timepoint_property(),
        "cell_x": create_cell_coord_property(axis="x", unit="micrometer"),
        "cell_y": create_cell_coord_property(axis="y", unit="micrometer"),
        "cell_z": create_cell_coord_property(axis="z", unit="micrometer"),
        "POSITION_T": Property(
            identifier="POSITION_T",
            name="Position T",
            description="Time in seconds",
            provenance="Test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
            unit="second",
        ),
        "channel_1": Property(
            identifier="channel_1",
            name="Channel 1",
            description="Channel 1 intensity",
            provenance="Test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
            unit=None,
        ),
        "channel_2": Property(
            identifier="channel_2",
            name="Channel 2",
            description="Channel 2 intensity",
            provenance="Test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
            unit=None,
        ),
    }


@pytest.fixture
def mixed_props():
    """Create a dictionary of mixed property types for testing."""
    return {
        # Node properties.
        "timepoint": create_timepoint_property(),
        "cell_x": create_cell_coord_property(axis="x", unit="micrometer"),
        "absolute_age": create_absolute_age_property(unit="timepoint"),
        "label": Property(
            identifier="label",
            name="Label",
            description="Cell label",
            provenance="Test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="string",
            unit=None,
        ),
        # Edges properties.
        "link_x": create_link_coord_property(axis="x", unit="micrometer"),
        "cell_displacement": create_cell_displacement_property(unit="micrometer"),
        # Lineage property.
        "lineage_id": create_lineage_id_property(),
    }


@pytest.fixture
def var_length_prop():
    """Create a variable length property for testing."""
    return Property(
        identifier="cell_contours",
        name="Cell contours",
        description="List of coordinates of the cell contours",
        provenance="Test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit="micrometer",
    )


@pytest.fixture
def list_prop():
    """Create a node property whose data type GEFF cannot store."""
    return Property(
        identifier="daughter_ids",
        name="Daughter IDs",
        description="IDs of the daughter cells",
        provenance="Test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="list[int]",
    )


@pytest.fixture
def simple_model():
    """Create a simple model for testing."""
    lin1 = CellLineage()
    lin1.add_node(1, timepoint=0, cell_x=10.0, lineage_id=0)
    lin1.add_node(2, timepoint=1, cell_x=12.0, lineage_id=0)
    lin1.add_edge(1, 2, link_x=2.0)
    lin1.graph["lineage_id"] = 0

    lin2 = CellLineage()
    lin2.add_node(3, timepoint=0, cell_x=20.0, lineage_id=1)
    lin2.add_node(4, timepoint=1, cell_x=22.0, lineage_id=1)
    lin2.add_edge(3, 4, link_x=2.0)
    lin2.graph["lineage_id"] = 1

    cell_data = {0: lin1, 1: lin2}
    data = Data(cell_data)
    props_metadata = PropsMetadata()
    props_metadata._add_prop(create_timepoint_property())
    props_metadata._add_prop(create_cell_coord_property(axis="x", unit="micrometer"))
    props_metadata._add_prop(create_link_coord_property(axis="x", unit="micrometer"))
    props_metadata._add_prop(create_lineage_id_property())

    model = Model(
        data=data,
        props_metadata=props_metadata,
        reference_time_property="timepoint",
    )
    return model


@pytest.fixture
def model_with_xyz(simple_model):
    """Create a model with x, y, z coordinates."""
    for lin in simple_model.data.cell_data.values():
        for node in lin.nodes():
            lin.nodes[node]["cell_y"] = 5.0
            lin.nodes[node]["cell_z"] = 1.0
        for edge in lin.edges():
            lin.edges[edge]["link_y"] = 0.5
            lin.edges[edge]["link_z"] = 0.1

    simple_model.props_metadata._add_prop(
        create_cell_coord_property(axis="y", unit="micrometer")
    )
    simple_model.props_metadata._add_prop(
        create_cell_coord_property(axis="z", unit="micrometer")
    )
    simple_model.props_metadata._add_prop(
        create_link_coord_property(axis="y", unit="micrometer")
    )
    simple_model.props_metadata._add_prop(
        create_link_coord_property(axis="z", unit="micrometer")
    )
    return simple_model


# Test Classes ################################################################


class TestFindNodeOverlaps:
    """Test cases for _find_node_overlaps function."""

    def test_empty_lineages(self):
        """Test with empty list of lineages."""
        overlaps = _find_node_overlaps([])
        assert overlaps == {}

    def test_single_lineage(self, lineage1):
        """Test with single lineage with no overlaps."""
        overlaps = _find_node_overlaps([lineage1])
        assert overlaps == {}

    def test_no_overlaps(self, lineage1, lineage2, lineage3):
        """Test multiple lineages with no overlapping node IDs."""
        overlaps = _find_node_overlaps([lineage1, lineage2, lineage3])
        assert overlaps == {}

    def test_single_overlap(self, lineage1, lineage2):
        """Test lineages with a single overlapping node ID."""
        lineage2.add_node(3)
        overlaps = _find_node_overlaps([lineage1, lineage2])
        assert overlaps == {3: [0, 1]}

    def test_multiple_overlaps(self, lineage1, lineage2, lineage3):
        """Test lineages with multiple overlapping node IDs."""
        lineage2.add_nodes_from([3, 5])
        lineage3.add_nodes_from([4, 5])
        overlaps = _find_node_overlaps([lineage1, lineage2, lineage3])
        assert overlaps == {3: [0, 1], 4: [0, 2], 5: [0, 1, 2]}


class TestGetNextAvailableId:
    """Test cases for _get_next_available_id function."""

    def test_empty_lineages(self):
        """Test with empty list of lineages."""
        next_id = _get_next_available_id([])
        assert next_id == 0

    def test_single_empty_lineage(self):
        """Test with a single empty lineage."""
        lineage = CellLineage()
        lineage.graph["lineage_id"] = 0
        next_id = _get_next_available_id([lineage])
        assert next_id == 0

    def test_single_lineage(self, lineage1):
        """Test with single lineage."""
        next_id = _get_next_available_id([lineage1])
        assert next_id == 6

    def test_multiple_lineages_with_overlap(self, lineage1, lineage2, lineage3):
        """Test with lineages that have overlaps."""
        lineage2.add_nodes_from([3, 5])
        next_id = _get_next_available_id([lineage1, lineage2, lineage3])
        assert next_id == 23

    def test_negative_node_ids(self):
        """Test with lineages that have negative node IDs."""
        lin = CellLineage()
        lin.add_nodes_from([-1, -2, -3, -4, -5])
        next_id = _get_next_available_id([lin])
        assert next_id == 0


class TestRelabelNodes:
    """Test cases for _relabel_nodes function."""

    def test_no_overlaps(self, lineage1, lineage2):
        """Test relabeling with no overlapping node IDs."""
        overlaps = {}
        _relabel_nodes([lineage1, lineage2], overlaps)
        assert set(lineage1.nodes()) == {1, 2, 3, 4, 5}
        assert set(lineage2.nodes()) == {10, 11, 12, 13}

    def test_single_overlap(self, lineage1, lineage2):
        """Test relabeling with a single overlapping node ID."""
        lineage2.add_node(3)
        overlaps = {3: [0, 1]}
        _relabel_nodes([lineage1, lineage2], overlaps)
        assert set(lineage1.nodes()) == {1, 2, 3, 4, 5}
        assert set(lineage2.nodes()) == {10, 11, 12, 13, 14}

    def test_multiple_overlaps(self, lineage1, lineage2, lineage3):
        """Test relabeling with multiple overlapping node IDs."""
        lineage2.add_nodes_from([3, 5])
        lineage3.add_nodes_from([4, 5])
        overlaps = {3: [0, 1], 4: [0, 2], 5: [0, 1, 2]}
        _relabel_nodes([lineage1, lineage2, lineage3], overlaps)
        assert set(lineage1.nodes()) == {1, 2, 3, 4, 5}
        assert set(lineage2.nodes()) == {10, 11, 12, 13, 23, 25}
        assert set(lineage3.nodes()) == {20, 21, 22, 24, 26}


class TestSolveNodeOverlaps:
    """Test cases for _solve_node_overlaps function."""

    def test_empty_lineages(self):
        """Test with empty list of lineages."""
        _solve_node_overlaps([])

    def test_no_overlaps(self, lineage1, lineage2):
        """Test with lineages that have no overlapping node IDs."""
        lin1_nodes = set(lineage1.nodes())
        lin2_nodes = set(lineage2.nodes())
        _solve_node_overlaps([lineage1, lineage2])
        assert set(lineage1.nodes()) == lin1_nodes
        assert set(lineage2.nodes()) == lin2_nodes

    def test_overlaps(self, lineage1, lineage2, lineage3):
        """Test with lineages that have overlapping node IDs."""
        lineage2.add_nodes_from([3, 5])
        lineage3.add_nodes_from([4, 5])
        _solve_node_overlaps([lineage1, lineage2, lineage3])
        assert set(lineage1.nodes()) == {1, 2, 3, 4, 5}
        assert set(lineage2.nodes()) == {10, 11, 12, 13, 23, 25}
        assert set(lineage3.nodes()) == {20, 21, 22, 24, 26}


class TestToGeffDtype:
    """Test cases for _to_geff_dtype function."""

    def test_string_dtype(self):
        """Test that the string data type is spelled 'str'."""
        assert _to_geff_dtype("string") == "str"
        assert _to_geff_dtype("str") == "str"

    def test_other_dtypes_unchanged(self):
        """Test that other data types are returned unchanged."""
        assert _to_geff_dtype("int") == "int"
        assert _to_geff_dtype("float64") == "float64"
        assert _to_geff_dtype("list[int]") == "list[int]"


class TestRemoveUnsupportedProps:
    """Test cases for _remove_unsupported_props function."""

    def test_supported_props_kept(self, caplog, simple_model):
        """Test that properties GEFF can store are kept, without warning."""
        props = simple_model.get_properties()

        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.exporter"):
            _remove_unsupported_props(simple_model)

        assert simple_model.get_properties() == props
        assert not caplog.records

    def test_unsupported_props_removed(self, caplog, simple_model, list_prop):
        """Test that cell and link properties GEFF cannot store are removed."""
        simple_model.props_metadata._add_prop(list_prop)
        simple_model.props_metadata._add_prop(
            Property(
                identifier="LINK_FEATURE",
                name="LINK_FEATURE",
                description="Link feature not declared in a TrackMate file",
                provenance="TrackMate",
                prop_type="edge",
                lin_type="CellLineage",
                dtype="unknown",
            )
        )
        lin = simple_model.data.cell_data[0]
        lin.nodes[1]["daughter_ids"] = [2]
        lin.edges[1, 2]["LINK_FEATURE"] = 1.5

        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.exporter"):
            _remove_unsupported_props(simple_model)

        assert "daughter_ids" not in simple_model.get_properties()
        assert "LINK_FEATURE" not in simple_model.get_properties()
        assert "daughter_ids" not in lin.nodes[1]
        assert "LINK_FEATURE" not in lin.edges[1, 2]
        assert len(caplog.records) == 1
        message = caplog.records[0].message
        assert message.startswith("Ignoring properties with a data type that GEFF")
        assert "'daughter_ids' (dtype 'list[int]')" in message
        assert "'LINK_FEATURE' (dtype 'unknown')" in message

    def test_lineage_props_kept(self, caplog, simple_model):
        """Test that lineage properties are kept, since they are not exported."""
        simple_model.props_metadata._add_prop(
            Property(
                identifier="lineage_tags",
                name="Lineage tags",
                description="Tags of the lineage",
                provenance="Test",
                prop_type="lineage",
                lin_type="CellLineage",
                dtype="list[str]",
            )
        )
        simple_model.data.cell_data[0].graph["lineage_tags"] = ["a", "b"]

        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.exporter"):
            _remove_unsupported_props(simple_model)

        assert "lineage_tags" in simple_model.get_properties()
        assert simple_model.data.cell_data[0].graph["lineage_tags"] == ["a", "b"]
        assert not caplog.records

    def test_protected_prop_removed(self, simple_model, list_prop):
        """Test that protected properties GEFF cannot store are removed too."""
        simple_model.props_metadata._add_prop(list_prop)
        simple_model.props_metadata._protect_prop("daughter_ids")

        _remove_unsupported_props(simple_model)

        assert "daughter_ids" not in simple_model.get_properties()


class TestRemoveNoneValues:
    """Test cases for _remove_none_values function."""

    def test_none_values_removed(self, simple_model):
        """Test that None values of cells and links are removed, not other values."""
        lin = simple_model.data.cell_data[0]
        lin.nodes[1]["cell_x"] = None
        lin.edges[1, 2]["link_x"] = None

        _remove_none_values(simple_model)

        assert "cell_x" not in lin.nodes[1]
        assert lin.nodes[2]["cell_x"] == 12.0
        assert "link_x" not in lin.edges[1, 2]
        assert simple_model.data.cell_data[1].edges[3, 4]["link_x"] == 2.0


class TestGetDefaultSpaceAxes:
    """Test cases for _get_default_space_axes function."""

    def test_xyz_declared(self, model_with_xyz):
        """cell_x, cell_y and cell_z are used when every cell has them."""
        assert _get_default_space_axes(model_with_xyz) == ["cell_x", "cell_y", "cell_z"]

    def test_no_y_declared(self, simple_model):
        """Without cell_y, no space axis is exported."""
        assert _get_default_space_axes(simple_model) == []

    def test_missing_z_value(self, model_with_xyz, caplog):
        """A cell without cell_z drops the z axis, with a warning."""
        del model_with_xyz.data.cell_data[0].nodes[1]["cell_z"]
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.exporter"):
            space_axes = _get_default_space_axes(model_with_xyz)
        assert space_axes == ["cell_x", "cell_y"]
        assert len(caplog.records) == 1
        assert "'cell_z' (1)" in caplog.records[0].message
        assert "no z axis" in caplog.records[0].message

    def test_missing_y_value(self, model_with_xyz, caplog):
        """A cell without cell_y drops all the space axes, with a warning."""
        del model_with_xyz.data.cell_data[0].nodes[1]["cell_y"]
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.exporter"):
            space_axes = _get_default_space_axes(model_with_xyz)
        assert space_axes == []
        assert len(caplog.records) == 1
        assert "'cell_y' (1)" in caplog.records[0].message
        assert "no space axes" in caplog.records[0].message


class TestBuildAxes:
    """Test cases for _build_axes function."""

    def test_one_time_axis(self, node_props):
        """Test building axes with only time axis (no spatial or channel axes)."""
        axes = _build_axes(
            node_props=node_props,
            time_axes=["timepoint"],
            space_axes=None,
            channel_axes=None,
        )
        assert len(axes) == 1
        assert axes[0] == geff_spec.Axis(name="timepoint", type="time", unit=None)

    def test_multiple_time_axes(self, node_props):
        """Test building axes with multiple time axes."""
        axes = _build_axes(
            node_props=node_props,
            time_axes=["timepoint", "POSITION_T"],
            space_axes=None,
            channel_axes=None,
        )
        assert len(axes) == 2
        assert axes[0] == geff_spec.Axis(name="timepoint", type="time", unit=None)
        assert axes[1] == geff_spec.Axis(name="POSITION_T", type="time", unit="second")

    def test_time_and_space_axes(self, node_props):
        """Test building axes with time and X, Y, Z spatial axes: the space axes are
        written in OME-Zarr order, z, y, x."""
        axes = _build_axes(
            node_props=node_props,
            time_axes=["POSITION_T"],
            space_axes=["cell_x", "cell_y", "cell_z"],
            channel_axes=None,
        )
        assert len(axes) == 4
        assert axes[0] == geff_spec.Axis(name="POSITION_T", type="time", unit="second")
        assert axes[1] == geff_spec.Axis(name="cell_z", type="space", unit="micrometer")
        assert axes[2] == geff_spec.Axis(name="cell_y", type="space", unit="micrometer")
        assert axes[3] == geff_spec.Axis(name="cell_x", type="space", unit="micrometer")

    def test_time_space_and_channel_axes(self, node_props):
        """Test building axes with time, space, and channel axes: OME-Zarr order is
        time, channel, then space (y, x)."""
        axes = _build_axes(
            node_props=node_props,
            time_axes=["timepoint"],
            space_axes=["cell_x", "cell_y"],
            channel_axes=["channel_1", "channel_2"],
        )
        assert len(axes) == 5
        assert axes[0] == geff_spec.Axis(name="timepoint", type="time", unit=None)
        assert axes[1] == geff_spec.Axis(name="channel_1", type="channel")
        assert axes[2] == geff_spec.Axis(name="channel_2", type="channel")
        assert axes[3] == geff_spec.Axis(name="cell_y", type="space", unit="micrometer")
        assert axes[4] == geff_spec.Axis(name="cell_x", type="space", unit="micrometer")

    def test_empty_space_axes(self, node_props):
        """An empty list of space axes writes none."""
        axes = _build_axes(
            node_props=node_props,
            time_axes=["timepoint"],
            space_axes=[],
            channel_axes=None,
        )
        assert [axis.type for axis in axes] == ["time"]

    def test_unknown_time_property_raises_error(self, node_props):
        """Test that unknown time property raises ValueError."""
        with pytest.raises(ValueError, match="Unknown node property 'unknown_time'"):
            _build_axes(
                node_props=node_props,
                time_axes=["unknown_time"],
                space_axes=None,
                channel_axes=None,
            )

    def test_unknown_space_property_raises_error(self, node_props):
        """Test that unknown space property raises ValueError."""
        with pytest.raises(ValueError, match="Unknown node property 'unknown_space'"):
            _build_axes(
                node_props=node_props,
                time_axes=["timepoint"],
                space_axes=["cell_x", "unknown_space"],
                channel_axes=None,
            )

    def test_unknown_channel_property_raises_error(self, node_props):
        """Test that unknown channel property raises ValueError."""
        with pytest.raises(ValueError, match="Unknown node property 'unknown_channel'"):
            _build_axes(
                node_props=node_props,
                time_axes=["timepoint"],
                space_axes=None,
                channel_axes=["unknown_channel"],
            )


class TestBuildDisplayHints:
    """Test cases for _build_display_hints function."""

    def test_no_space_axes_returns_none(self):
        """Test that None is returned when space_axes is None."""
        hints = _build_display_hints(
            time_axis="timepoint",
            space_axes=None,
        )
        assert hints is None

    def test_single_space_axis_returns_none(self):
        """Test that None is returned when there's only one space axis."""
        hints = _build_display_hints(
            time_axis="timepoint",
            space_axes=["cell_x"],
        )
        assert hints is None

    def test_two_space_axes(self):
        """Test display hints with 2 space axes (horizontal and vertical)."""
        hints_obtained = _build_display_hints(
            time_axis="POSITION_T",
            space_axes=["cell_x", "cell_y"],
        )
        hints_expected = geff_spec.DisplayHint(
            display_horizontal="cell_x",
            display_vertical="cell_y",
            display_depth=None,
            display_time="POSITION_T",
        )
        assert hints_obtained == hints_expected

    def test_three_space_axes(self):
        """Test display hints with 3 space axes (horizontal, vertical, and depth)."""
        hints_obtained = _build_display_hints(
            time_axis="timepoint",
            space_axes=["cell_x", "cell_y", "cell_z"],
        )
        hints_expected = geff_spec.DisplayHint(
            display_horizontal="cell_x",
            display_vertical="cell_y",
            display_depth="cell_z",
            display_time="timepoint",
        )
        assert hints_obtained == hints_expected

    def test_more_than_three_space_axes(self):
        """Test display hints with more than three space axes."""
        hints_obtained = _build_display_hints(
            time_axis="time",
            space_axes=["x", "y", "z", "w"],
        )
        hints_expected = geff_spec.DisplayHint(
            display_horizontal="x",
            display_vertical="y",
            display_depth="z",
            display_time="time",
        )
        assert hints_obtained == hints_expected


class TestBuildPropsMetadata:
    """Test cases for _build_props_metadata function."""

    def test_node_and_edge_properties(self, mixed_props):
        """Test building metadata with node and edge properties."""
        node_props_md, edge_props_md = _build_props_metadata(mixed_props)

        # Node properties, including the node and lineage property lineage_id.
        assert len(node_props_md) == 5
        assert "timepoint" in node_props_md
        assert "cell_x" in node_props_md
        assert "absolute_age" in node_props_md
        assert "label" in node_props_md
        assert "lineage_id" in node_props_md

        # Edge properties.
        assert len(edge_props_md) == 2
        assert "link_x" in edge_props_md
        assert "cell_displacement" in edge_props_md
        assert "lineage_id" not in edge_props_md

    def test_lineage_only_property_excluded(self, mixed_props):
        """Test that lineage-only properties are excluded (requires geffception)."""
        mixed_props["lineage_name"] = Property(
            identifier="lineage_name",
            name="Lineage name",
            description="Name of the lineage",
            provenance="Test",
            prop_type="lineage",
            lin_type="CellLineage",
            dtype="string",
        )
        node_props_md, edge_props_md = _build_props_metadata(mixed_props)

        assert "lineage_name" not in node_props_md
        assert "lineage_name" not in edge_props_md

    def test_node_and_lineage_property_exported_as_node(self, mixed_props):
        """Test that a property propagated from lineages to nodes is exported."""
        mixed_props["lineage_name"] = Property(
            identifier="lineage_name",
            name="Lineage name",
            description="Name of the lineage",
            provenance="Test",
            prop_type=["node", "lineage"],
            lin_type="CellLineage",
            dtype="string",
        )
        node_props_md, edge_props_md = _build_props_metadata(mixed_props)

        assert node_props_md["lineage_name"].dtype == "str"
        assert "lineage_name" not in edge_props_md

    def test_string_dtype_conversion(self, mixed_props):
        """Test that string dtype is converted to str."""
        node_props_md, _ = _build_props_metadata(mixed_props)

        assert node_props_md["label"].dtype == "str"

    def test_variable_length_properties(self, node_props, var_length_prop):
        """Test marking properties as variable length."""
        props = {
            "cell_contours": var_length_prop,
            "timepoint": node_props["timepoint"],
        }

        node_props_md, _ = _build_props_metadata(
            props, var_length_props=["cell_contours"]
        )

        assert node_props_md["cell_contours"].varlength is True
        assert node_props_md["timepoint"].varlength is False

    def test_metadata_attributes(self, mixed_props):
        """Test that all metadata attributes are correctly set."""
        node_props_md, _ = _build_props_metadata(mixed_props)

        absolute_age_md = node_props_md["absolute_age"]
        assert absolute_age_md.identifier == "absolute_age"
        assert absolute_age_md.dtype in ["float", "float32", "float64"]
        assert absolute_age_md.unit == "timepoint"
        assert absolute_age_md.name == "Absolute age"
        assert (
            absolute_age_md.description
            == "Age of the cell since the start of the lineage"
        )
        assert absolute_age_md.varlength is False


class TestBuildGeffMetadata:
    """Test cases for _build_geff_metadata function."""

    def test_default_time_axis(self, simple_model):
        """Test that default time axis uses model's reference_time_property."""
        metadata = _build_geff_metadata(simple_model)

        assert len(metadata.axes) == 1
        assert metadata.axes[0].name == "timepoint"
        assert metadata.axes[0].type == "time"
        # Display hints should be None without space axes.
        assert metadata.display_hints is None

    def test_string_time_axis_conversion(self, simple_model):
        """Test that string time_axes is converted to list."""
        metadata = _build_geff_metadata(simple_model, time_axes="timepoint")

        assert len(metadata.axes) == 1
        assert metadata.axes[0].name == "timepoint"

    def test_with_space_axes(self, model_with_xyz):
        """Test metadata with space axes."""
        metadata = _build_geff_metadata(
            model_with_xyz,
            space_axes=["cell_x", "cell_y", "cell_z"],
        )

        assert len(metadata.axes) == 4
        time_axes = [ax for ax in metadata.axes if ax.type == "time"]
        space_axes = [ax for ax in metadata.axes if ax.type == "space"]
        assert len(time_axes) == 1
        assert len(space_axes) == 3

        hints_expected = geff_spec.DisplayHint(
            display_horizontal="cell_x",
            display_vertical="cell_y",
            display_depth="cell_z",
            display_time="timepoint",
        )
        assert metadata.display_hints == hints_expected

    def test_default_space_axes(self, model_with_xyz):
        """Without space_axes, the cell coordinates are written as space axes in
        OME-Zarr order, and the display hints map them to x, y and z."""
        metadata = _build_geff_metadata(model_with_xyz)

        assert [ax.name for ax in metadata.axes] == [
            "timepoint",
            "cell_z",
            "cell_y",
            "cell_x",
        ]
        assert metadata.display_hints == geff_spec.DisplayHint(
            display_horizontal="cell_x",
            display_vertical="cell_y",
            display_depth="cell_z",
            display_time="timepoint",
        )

    def test_empty_space_axes(self, model_with_xyz):
        """An empty space_axes list writes neither space axes nor display hints."""
        metadata = _build_geff_metadata(model_with_xyz, space_axes=[])

        assert [ax.type for ax in metadata.axes] == ["time"]
        assert metadata.display_hints is None

    def test_track_node_props_without_cycle(self, simple_model):
        """Test track_node_props when model has no cycle data."""
        metadata = _build_geff_metadata(simple_model)

        assert "lineage" in metadata.track_node_props
        assert metadata.track_node_props["lineage"] == "lineage_id"
        assert "tracklet" not in metadata.track_node_props

    def test_node_and_edge_props_metadata(self, simple_model):
        """Test that node and edge properties metadata are correctly built."""
        metadata = _build_geff_metadata(simple_model)

        # Node properties metadata.
        assert "timepoint" in metadata.node_props_metadata
        assert "cell_x" in metadata.node_props_metadata

        # Edge properties metadata.
        assert "link_x" in metadata.edge_props_metadata

    def test_directed_graph(self, simple_model):
        """Test that metadata specifies directed graph."""
        metadata = _build_geff_metadata(simple_model)

        assert metadata.directed is True

    def test_multiple_time_and_space_axes(self, model_with_xyz):
        """Test with multiple time and space axes."""
        model_with_xyz.props_metadata._add_prop(create_frame_property())

        for lin in model_with_xyz.data.cell_data.values():
            for node in lin.nodes():
                lin.nodes[node]["frame"] = lin.nodes[node]["timepoint"] + 10

        metadata = _build_geff_metadata(
            model_with_xyz,
            time_axes=["timepoint", "frame"],
            space_axes=["cell_x", "cell_y"],
        )

        time_axes = [ax for ax in metadata.axes if ax.type == "time"]
        space_axes = [ax for ax in metadata.axes if ax.type == "space"]
        assert len(time_axes) == 2
        assert len(space_axes) == 2

        # Display hints should use first time axis.
        assert metadata.display_hints.display_time == "timepoint"


class TestExportGEFF:
    """Test cases for export_GEFF function."""

    def test_basic_export(self, simple_model, tmp_path):
        """Test basic GEFF export functionality."""
        geff_out = str(tmp_path / "test.geff")
        exported_model = export_GEFF(simple_model, geff_out)

        # Check that the GEFF file was created.
        assert (tmp_path / "test.geff").exists()

        # Check that a model is returned.
        assert isinstance(exported_model, Model)

        # Check that we can read it back.
        graph, metadata = geff.read(geff_out)
        assert graph is not None
        assert metadata is not None

    def test_export_returns_copy(self, simple_model, tmp_path):
        """Test that export_GEFF returns a copy and doesn't modify the original data.
        It's not an exhaustive check since we are only checking the number of nodes
        and edges.
        """
        geff_out = str(tmp_path / "test.geff")
        exported_model = export_GEFF(simple_model, geff_out)

        # Check that the original model's data is unchanged. It's not an exhaustive
        # check since we are only checking the number of nodes and edges.
        original_node_count = sum(
            len(lin.nodes) for lin in simple_model.data.cell_data.values()
        )
        export_node_count = sum(
            len(lin.nodes) for lin in exported_model.data.cell_data.values()
        )
        assert original_node_count == export_node_count
        original_edge_count = sum(
            len(lin.edges) for lin in simple_model.data.cell_data.values()
        )
        export_edge_count = sum(
            len(lin.edges) for lin in exported_model.data.cell_data.values()
        )
        assert original_edge_count == export_edge_count

        assert exported_model is not simple_model

    def test_export_cleans_metadata(self, simple_model, tmp_path):
        """Test that export_GEFF cleans metadata by removing orphaned properties.

        Also validates that multi-type properties (like lineage_id with NODE | LINEAGE)
        are preserved when they have actual data in the lineages.
        """
        geff_out = str(tmp_path / "test.geff")
        simple_model.props_metadata._add_prop(
            create_absolute_age_property(unit="timepoint")
        )
        exported_model = export_GEFF(simple_model, geff_out)

        # The absolute_age property is orphaned (no data in lineages), so it's removed.
        # All other properties are preserved, including multi-type ones (lineage_id).
        expected_props = {
            k: v for k, v in simple_model.get_properties().items() if k != "absolute_age"
        }
        assert expected_props == exported_model.get_properties()

    def test_empty_model_raises_error(self, tmp_path):
        """Test that exporting an empty model raises ValueError."""
        geff_out = str(tmp_path / "test.geff")
        empty_data = Data({})
        props_metadata = PropsMetadata()
        props_metadata._add_prop(create_timepoint_property())
        empty_model = Model(
            data=empty_data,
            props_metadata=props_metadata,
            reference_time_property="timepoint",
        )

        with pytest.raises(ValueError, match="Model contains no lineage data"):
            export_GEFF(empty_model, geff_out)

    def test_export_with_space_axes(self, model_with_xyz, tmp_path):
        """Test export with space axes specified."""
        geff_out = str(tmp_path / "test.geff")
        export_GEFF(model_with_xyz, geff_out, space_axes=["cell_x", "cell_y", "cell_z"])

        graph, metadata = geff.read(geff_out)
        space_axes = [ax for ax in metadata.axes if ax.type == "space"]
        assert len(space_axes) == 3

    def test_default_export_round_trip(self, model_with_xyz, tmp_path):
        """With the default space axes, coordinates and space unit come back."""
        geff_out = str(tmp_path / "test.geff")
        export_GEFF(model_with_xyz, geff_out)

        reloaded = load_GEFF(geff_out)

        assert reloaded.get_space_unit() == "micrometer"
        cells = [
            attrs
            for lin in reloaded.data.cell_data.values()
            for _, attrs in lin.nodes(data=True)
        ]
        assert sorted(attrs["cell_x"] for attrs in cells) == [10.0, 12.0, 20.0, 22.0]
        assert all(attrs["cell_y"] == 5.0 for attrs in cells)
        assert all(attrs["cell_z"] == 1.0 for attrs in cells)

    def test_export_with_custom_time_axes(self, simple_model, tmp_path):
        """Test export with custom time axes."""
        geff_out = str(tmp_path / "test.geff")
        export_GEFF(simple_model, geff_out, time_axes="timepoint")

        graph, metadata = geff.read(geff_out)
        time_axes = [ax for ax in metadata.axes if ax.type == "time"]
        assert len(time_axes) == 1
        assert time_axes[0].name == "timepoint"

    def test_export_with_variable_length_props(
        self, simple_model, var_length_prop, tmp_path
    ):
        """Test export with variable length properties."""
        geff_out = str(tmp_path / "test.geff")
        simple_model.props_metadata._add_prop(var_length_prop)
        for lin in simple_model.data.cell_data.values():
            for node in lin.nodes():
                lin.nodes[node][var_length_prop.identifier] = [
                    [0, 0],
                    [1, 0],
                    [1, 1],
                    [0, 1],
                ]
        export_GEFF(
            simple_model,
            geff_out,
            variable_length_props=[var_length_prop.identifier],
        )

        graph, metadata = geff.read(geff_out)
        assert var_length_prop.identifier in metadata.node_props_metadata

    def test_export_skips_unsupported_props(
        self, caplog, simple_model, list_prop, tmp_path
    ):
        """Test that properties GEFF cannot store are skipped, with a warning."""
        geff_out = str(tmp_path / "test.geff")
        simple_model.props_metadata._add_prop(list_prop)
        for lin in simple_model.data.cell_data.values():
            for node in lin.nodes:
                lin.nodes[node]["daughter_ids"] = list(lin.successors(node))

        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.exporter"):
            exported_model = export_GEFF(simple_model, geff_out)

        graph, metadata = geff.read(geff_out)
        assert "daughter_ids" not in metadata.node_props_metadata
        assert all("daughter_ids" not in attrs for _, attrs in graph.nodes(data=True))
        assert "'daughter_ids'" in caplog.text
        assert "daughter_ids" not in exported_model.get_properties()
        # The original model is not modified.
        assert "daughter_ids" in simple_model.get_properties()

    def test_export_writes_none_as_missing(self, simple_model, tmp_path):
        """Test that None values are written as missing values."""
        geff_out = str(tmp_path / "test.geff")
        simple_model.data.cell_data[0].nodes[1]["cell_x"] = None
        simple_model.data.cell_data[0].edges[1, 2]["link_x"] = None

        export_GEFF(simple_model, geff_out)

        graph, metadata = geff.read(geff_out)
        assert "cell_x" not in graph.nodes[1]
        assert graph.nodes[2]["cell_x"] == 12.0
        assert "link_x" not in graph.edges[1, 2]
        assert graph.edges[3, 4]["link_x"] == 2.0
        # The original model is not modified.
        assert simple_model.data.cell_data[0].nodes[1]["cell_x"] is None

    def test_model_requiring_update_raises(self, simple_model, tmp_path):
        """Test that a model requiring an update is not exported."""
        simple_model.prepare_full_data_update()
        with pytest.raises(UpdateRequiredError, match="before exporting"):
            export_GEFF(simple_model, str(tmp_path / "test.geff"))
        assert not (tmp_path / "test.geff").exists()
