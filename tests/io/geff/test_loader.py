"""Unit test for GEFF file loader."""

import importlib.metadata
import logging

import geff
import geff_spec
import networkx as nx
import pytest

from pycellin.classes import CellLineage, Property
from pycellin.custom_types import PropertyType
from pycellin.properties.core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_lineage_id_property,
)
from pycellin.io.geff.loader import (
    _build_generic_metadata,
    _build_props_metadata,
    _ensure_valid_cell_id,
    _extract_axes_metadata,
    _extract_generic_metadata,
    _extract_lin_props_metadata,
    _extract_props_metadata,
    _fallback_to_node_keys,
    _get_cell_id_problem,
    _get_prop_unit,
    _identify_lin_id_prop,
    _identify_space_props,
    _identify_time_prop,
    _lin_ids_match_components,
    _rename_reserved_prop,
    _resolve_prop_key,
    _standardize_properties_data,
    _standardize_props_metadata,
    load_GEFF,
)

# Fixtures ####################################################################


@pytest.fixture
def geff_node_props_md():
    """Geff node properties metadata where the target prop has a unit."""
    return {
        "frame": geff_spec.PropMetadata(identifier="frame", dtype="int64", unit=None),
        "position_x": geff_spec.PropMetadata(
            identifier="position_x", dtype="float64", unit="um"
        ),
    }


@pytest.fixture
def geff_edge_props_md():
    """Geff edge properties metadata where the target prop has a unit."""
    return {
        "speed": geff_spec.PropMetadata(
            identifier="speed", dtype="float64", unit="um/second"
        ),
        "cost": geff_spec.PropMetadata(identifier="cost", dtype="float64", unit=None),
    }


@pytest.fixture
def geff_axes():
    """A list of geff axes containing time and space axes."""
    return [
        geff_spec.Axis(name="frame", type="time", unit="second"),
        geff_spec.Axis(name="position_x", type="space", unit="um"),
        geff_spec.Axis(name="position_y", type="space", unit="um"),
    ]


@pytest.fixture
def duplicate_time_axes():
    """A list of geff axes with two matching time entries for the same prop."""
    return [
        geff_spec.Axis(name="frame", type="time", unit="second"),
        geff_spec.Axis(name="frame", type="time", unit="millisecond"),
    ]


@pytest.fixture
def geff_md_axes(geff_axes, geff_node_props_md):
    """GeffMetadata with axes and node properties metadata."""
    return geff.GeffMetadata(
        directed=True,
        axes=geff_axes,
        node_props_metadata=geff_node_props_md,
        edge_props_metadata={},
    )


@pytest.fixture
def geff_md_display_hints(geff_node_props_md):
    """GeffMetadata with display hints pointing to a valid time property."""
    return geff.GeffMetadata(
        directed=True,
        display_hints=geff_spec.DisplayHint(
            display_horizontal="position_x",
            display_vertical="position_y",
            display_depth=None,
            display_time="frame",
        ),
        node_props_metadata=geff_node_props_md,
        edge_props_metadata={},
    )


@pytest.fixture
def geff_md_3d_axes(geff_node_props_md):
    """GeffMetadata with 3D spatial axes."""
    return geff.GeffMetadata(
        directed=True,
        axes=[
            geff_spec.Axis(name="frame", type="time", unit="second"),
            geff_spec.Axis(name="position_x", type="space", unit="um"),
            geff_spec.Axis(name="position_y", type="space", unit="um"),
            geff_spec.Axis(name="position_z", type="space", unit="um"),
        ],
        node_props_metadata=geff_node_props_md,
        edge_props_metadata={},
    )


@pytest.fixture
def graph_lin_id():
    """Graph with standard and custom lineage ID properties."""
    g = nx.Graph()
    g.add_node(0, frame=0, lineage_id=0, my_lin_id=0)
    g.add_node(1, frame=1, lineage_id=1, my_lin_id=1)
    return g


@pytest.fixture
def graph_no_lin_id():
    """Graph with no lineage ID property."""
    g = nx.Graph()
    g.add_node(0, frame=0)
    g.add_node(1, frame=1)
    return g


@pytest.fixture
def graph_with_coords():
    """Graph with 2D spatial coordinate properties."""
    g = nx.Graph()
    g.add_node(0, frame=0, position_x=1.0, position_y=2.0)
    g.add_node(1, frame=1, position_x=3.0, position_y=4.0)
    return g


@pytest.fixture
def graph_with_3d_coords():
    """Graph with 3D spatial coordinate properties."""
    g = nx.Graph()
    g.add_node(0, frame=0, position_x=1.0, position_y=2.0, position_z=3.0)
    g.add_node(1, frame=1, position_x=4.0, position_y=5.0, position_z=6.0)
    return g


@pytest.fixture
def prop_geff_cell_id():
    """A Property for a 'cell_id' node property declared in a GEFF file."""
    return Property(
        identifier="cell_id",
        name="cell_id",
        description="cell_id",
        provenance="geff",
        prop_type="node",
        lin_type="CellLineage",
        dtype="int64",
    )


@pytest.fixture
def prop_cell_position_x():
    """A Property for 'cell_position_x' with prop_type='node'."""
    return Property(
        identifier="cell_position_x",
        name="cell_position_x",
        description="cell_position_x",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
    )


@pytest.fixture
def prop_lin_position_x():
    """A Property for 'lin_position_x' with prop_type='lineage'."""
    return Property(
        identifier="lin_position_x",
        name="lin_position_x",
        description="lin_position_x",
        provenance="test",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="float",
    )


@pytest.fixture
def prop_position_x_node():
    """A Property for 'position_x' with prop_type='node'."""
    return Property(
        identifier="position_x",
        name="position_x",
        description="position_x",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit="um",
    )


@pytest.fixture
def prop_position_x_edge():
    """A Property for 'position_x' with prop_type='edge'."""
    return Property(
        identifier="position_x",
        name="position_x",
        description="position_x",
        provenance="test",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="float",
    )


@pytest.fixture
def prop_position_x_lineage():
    """A Property for 'position_x' with prop_type='lineage'."""
    return Property(
        identifier="position_x",
        name="position_x",
        description="position_x",
        provenance="test",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="float",
    )


@pytest.fixture
def prop_pycellin_cell_position_x():
    """A Property for 'pycellin_cell_position_x' with prop_type='node'."""
    return Property(
        identifier="pycellin_cell_position_x",
        name="pycellin_cell_position_x",
        description="pycellin_cell_position_x",
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
    )


@pytest.fixture
def prop_pycellin_lin_position_x():
    """A Property for 'pycellin_lin_position_x' with prop_type='lineage'."""
    return Property(
        identifier="pycellin_lin_position_x",
        name="pycellin_lin_position_x",
        description="pycellin_lin_position_x",
        provenance="test",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="float",
    )


@pytest.fixture
def prop_speed():
    """A Property for 'speed' with prop_type='edge'."""
    return Property(
        identifier="speed",
        name="speed",
        description="speed",
        provenance="test",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="float",
    )


@pytest.fixture
def pycellin_standard_md():
    """"""
    props_md = {
        "lineage_id": create_lineage_id_property(provenance="test"),
        "cell_id": create_cell_id_property(provenance="test"),
        "cell_x": create_cell_coord_property(unit="um", axis="x", provenance="test"),
    }
    return props_md


@pytest.fixture
def pycellin_non_standard_md(prop_position_x_node):
    """"""
    props_md = {
        "track_id": Property(
            identifier="track_id",
            name="track ID",
            description="Unique identifier of the track",
            provenance="test",
            prop_type="lineage",
            lin_type="Lineage",
            dtype="int",
        ),
        "node_id": Property(
            identifier="node_id",
            name="cell ID",
            description="Unique identifier of the cell",
            provenance="test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="int",
        ),
        "position_x": prop_position_x_node,
    }
    return props_md


@pytest.fixture
def lin_props_md():
    """A dict of lineage properties metadata with expected fields."""
    return {
        "n_divisions": {"name": None, "dtype": "int", "unit": None},
        "displacement": {
            "name": "Lineage displacement",
            "dtype": "float",
            "unit": "um",
        },
    }


@pytest.fixture
def rename_map():
    """A fresh, empty rename map accumulator for property collision tracking."""
    return {PropertyType.NODE: {}, PropertyType.EDGE: {}, PropertyType.LINEAGE: {}}


@pytest.fixture
def standardize_rename_map():
    """Rename map containing one key per property type."""
    return {
        PropertyType.NODE: {"old_node_key": "new_node_key"},
        PropertyType.EDGE: {"old_edge_key": "new_edge_key"},
        PropertyType.LINEAGE: {"old_lin_key": "new_lin_key"},
    }


@pytest.fixture
def lineages_with_nonstandard_keys() -> list[CellLineage]:
    """Two lineages carrying non-standard node and lineage property keys."""
    lin_a = CellLineage(nx.DiGraph(), lid=None)
    lin_a.add_node(
        0,
        custom_lin_id=11,
        custom_cell_id=100,
        pos_x=1.0,
        pos_y=2.0,
        pos_z=3.0,
        old_node_key="node-a0",
    )
    lin_a.add_node(
        1,
        custom_lin_id=11,
        custom_cell_id=101,
        pos_x=4.0,
        pos_y=5.0,
        pos_z=6.0,
        old_node_key="node-a1",
    )
    lin_a.add_edge(0, 1, old_edge_key=0.5)
    lin_a.graph["custom_lin_id"] = 11
    lin_a.graph["old_lin_key"] = "lin-a"

    lin_b = CellLineage(nx.DiGraph(), lid=None)
    lin_b.add_node(
        2,
        custom_lin_id=12,
        custom_cell_id=102,
        pos_x=7.0,
        pos_y=8.0,
        pos_z=9.0,
        old_node_key="node-b2",
    )
    lin_b.graph["custom_lin_id"] = 12
    lin_b.graph["old_lin_key"] = "lin-b"

    return [lin_a, lin_b]


@pytest.fixture
def geff_valid_ids(tmp_path):
    """GEFF file whose 'cell_id' and 'lineage_id' properties can identify cells
    and lineages, without track_node_props."""
    g = nx.DiGraph()
    g.add_node(0, t=0, cell_id=10, lineage_id=1)
    g.add_node(1, t=1, cell_id=11, lineage_id=1)
    g.add_node(2, t=0, cell_id=20, lineage_id=2)
    g.add_node(3, t=1, cell_id=21, lineage_id=2)
    g.add_edges_from([(0, 1), (2, 3)])
    path = tmp_path / "valid_ids.geff"
    geff.write(g, path, axis_names=["t"], axis_types=["time"])
    return path


@pytest.fixture
def geff_clashing_ids(tmp_path):
    """GEFF file whose 'cell_id' and 'lineage_id' properties cannot identify cells
    and lineages: duplicate cell IDs, and one lineage ID for two tracks."""
    g = nx.DiGraph()
    g.add_node(0, t=0, cell_id=1, lineage_id=5)
    g.add_node(1, t=1, cell_id=1, lineage_id=5)
    g.add_node(2, t=0, cell_id=2, lineage_id=5)
    g.add_node(3, t=1, cell_id=3, lineage_id=5)
    g.add_edges_from([(0, 1), (2, 3)])
    path = tmp_path / "clashing_ids.geff"
    geff.write(g, path, axis_names=["t"], axis_types=["time"])
    return path


# Test Classes ################################################################


class TestLinIdsMatchComponents:
    """Test cases for _lin_ids_match_components function."""

    def test_one_id_per_component(self):
        """When each connected component has its own ID, return True."""
        g = nx.DiGraph()
        g.add_node(0, lin=1)
        g.add_node(1, lin=1)
        g.add_node(2, lin=2)
        g.add_edge(0, 1)
        assert _lin_ids_match_components(g, "lin")

    def test_id_shared_by_components(self):
        """When two connected components have the same ID, return False."""
        g = nx.DiGraph()
        g.add_node(0, lin=1)
        g.add_node(1, lin=1)
        g.add_node(2, lin=1)
        g.add_edge(0, 1)
        assert not _lin_ids_match_components(g, "lin")

    def test_ids_differ_within_component(self):
        """When the nodes of a connected component have different IDs, return False."""
        g = nx.DiGraph()
        g.add_node(0, lin=1)
        g.add_node(1, lin=2)
        g.add_edge(0, 1)
        assert not _lin_ids_match_components(g, "lin")

    def test_missing_ids_are_ignored(self):
        """Nodes without an ID or with a None ID don't make the IDs invalid."""
        g = nx.DiGraph()
        g.add_node(0, lin=1)
        g.add_node(1)
        g.add_node(2, lin=None)
        g.add_edges_from([(0, 1), (1, 2)])
        assert _lin_ids_match_components(g, "lin")


class TestIdentifyLinIdProp:
    """Test cases for _identify_lin_id_prop function."""

    def test_provided_key_exists_in_graph(self, graph_lin_id):
        """When lin_id_prop is provided and the property exists, return it."""
        result = _identify_lin_id_prop("my_lin_id", None, graph_lin_id)
        assert result == "my_lin_id"

    def test_provided_key_not_in_graph_falls_back_to_track_node_props(
        self, caplog, graph_lin_id
    ):
        """When lin_id_prop is not in graph but geff_track_node_props has 'lineage',
        return the value from track_node_props and log."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_lin_id_prop(
                "missing_key",
                {"lineage": "track_id"},
                graph_lin_id,
            )
        assert len(caplog.records) == 2
        assert caplog.records[0].levelname == "INFO"
        assert "infered from GEFF metadata" in caplog.records[0].message
        assert caplog.records[1].levelname == "INFO"
        assert "inferred from GEFF track_node_props" in caplog.records[1].message

        assert result == "track_id"

    def test_provided_key_not_in_graph_falls_back_to_lineage_id(
        self, caplog, graph_lin_id
    ):
        """When lin_id_prop is not in graph and geff_track_node_props is None,
        fall back to 'lineage_id' if present in graph and log."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_lin_id_prop("missing_key", None, graph_lin_id)
        assert len(caplog.records) == 2
        assert caplog.records[0].levelname == "INFO"
        assert "infered from GEFF metadata" in caplog.records[0].message
        assert caplog.records[1].levelname == "INFO"
        assert "inferred from existing graph property" in caplog.records[1].message

        assert result == "lineage_id"

    def test_provided_key_not_in_graph_no_fallback(self, caplog, graph_no_lin_id):
        """When lin_id_prop is not in graph, geff_track_node_props is None,
        and graph has no 'lineage_id', log and return None."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_lin_id_prop("missing_key", None, graph_no_lin_id)
        assert len(caplog.records) == 2
        assert caplog.records[0].levelname == "INFO"
        assert "infered from GEFF metadata" in caplog.records[0].message
        assert caplog.records[1].levelname == "WARNING"
        assert "No lineage identifier found" in caplog.records[1].message

        assert result is None

    def test_none_prop_with_track_node_props_lineage(self, caplog, graph_lin_id):
        """When lin_id_prop is None and geff_track_node_props has 'lineage',
        return the value from track_node_props and log."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_lin_id_prop(None, {"lineage": "my_lin_id"}, graph_lin_id)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "inferred from GEFF track_node_props" in caplog.records[0].message

        assert result == "my_lin_id"

    def test_none_prop_with_track_node_props_no_lineage_key(
        self, caplog, graph_lin_id
    ):
        """When lin_id_prop is None and geff_track_node_props has no 'lineage' key,
        fall back to 'lineage_id' if present in graph and log."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_lin_id_prop(
                None, {"tracklet": "tracklet_id"}, graph_lin_id
            )
        assert len(caplog.records) == 1
        assert "inferred from existing graph property" in caplog.records[0].message

        assert result == "lineage_id"

    def test_none_prop_no_track_node_props_graph_has_lineage_id(
        self, caplog, graph_lin_id
    ):
        """When lin_id_prop is None, geff_track_node_props is None,
        and graph has 'lineage_id', return 'lineage_id' and log."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_lin_id_prop(None, None, graph_lin_id)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "inferred from existing graph property" in caplog.records[0].message

        assert result == "lineage_id"

    def test_none_prop_lineage_id_not_matching_components(self, caplog):
        """When lin_id_prop is None, geff_track_node_props is None, and the graph
        'lineage_id' doesn't match its connected components, log and return None."""
        g = nx.DiGraph()
        g.add_node(0, lineage_id=1)
        g.add_node(1, lineage_id=1)
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_lin_id_prop(None, None, g)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "cannot be used as lineage identifier" in caplog.records[0].message

        assert result is None

    def test_none_prop_no_track_node_props_no_lineage_id_in_graph(
        self, caplog, graph_no_lin_id
    ):
        """When lin_id_prop is None, geff_track_node_props is None,
        and graph has no 'lineage_id', log and return None."""
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _identify_lin_id_prop(None, None, graph_no_lin_id)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "No lineage identifier found" in caplog.records[0].message

        assert result is None


class TestIdentifyTimeProp:
    """Test cases for _identify_time_prop function."""

    def test_provided_key_exists_in_graph(self, graph_lin_id):
        """When time_key is provided and exists in the graph, return it."""
        result = _identify_time_prop("frame", None, graph_lin_id)
        assert result == "frame"

    def test_provided_key_not_in_graph_falls_back_to_display_hints(
        self, caplog, graph_lin_id, geff_md_display_hints
    ):
        """When time_key is not in the graph but display hints have a valid time prop,
        warn and return the hint key."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_time_prop(
                "missing_key", geff_md_display_hints, graph_lin_id
            )
        assert len(caplog.records) == 2
        assert caplog.records[0].levelname == "WARNING"
        assert "'missing_key' given as time_prop" in caplog.records[0].message
        assert caplog.records[1].levelname == "INFO"
        assert "inferred from display hints" in caplog.records[1].message

        assert result == "frame"

    def test_provided_key_not_in_graph_falls_back_to_axes(
        self, caplog, graph_lin_id, geff_md_axes
    ):
        """When time_key is not in the graph, no display hints are available,
        and the axes have a matching time prop, warn and return the axis key."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_time_prop("missing_key", geff_md_axes, graph_lin_id)
        assert len(caplog.records) == 2
        assert caplog.records[0].levelname == "WARNING"
        assert "is not on every node" in caplog.records[0].message
        assert caplog.records[1].levelname == "INFO"
        assert "inferred from axes" in caplog.records[1].message

        assert result == "frame"

    def test_provided_key_not_in_graph_no_geff_md_raises(self, caplog, graph_lin_id):
        """When time_key is not in the graph and geff_md is None,
        warn and raise ValueError."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            with pytest.raises(ValueError):
                _identify_time_prop("missing_key", None, graph_lin_id)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "'missing_key' given as time_prop" in caplog.records[0].message

    def test_none_key_inferred_from_display_hints(
        self, caplog, graph_lin_id, geff_md_display_hints
    ):
        """When time_key is None and display hints have a valid time prop,
        log and return the hint key."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_time_prop(None, geff_md_display_hints, graph_lin_id)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "inferred from display hints" in caplog.records[0].message

        assert result == "frame"

    def test_none_key_inferred_from_axes(self, caplog, graph_lin_id, geff_md_axes):
        """When time_key is None, no display hints are available, and the axes
        have a matching time prop, log and return the axis key."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_time_prop(None, geff_md_axes, graph_lin_id)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "inferred from axes" in caplog.records[0].message

        assert result == "frame"

    def test_none_key_no_geff_md_raises(self, graph_lin_id):
        """When time_key is None and geff_md is None, raise ValueError."""
        with pytest.raises(ValueError):
            _identify_time_prop(None, None, graph_lin_id)

    def test_none_key_no_time_info_in_geff_md_raises(self, graph_lin_id):
        """When time_key is None and geff_md has no usable time axes or display hints,
        raise ValueError."""
        geff_md_no_time = geff.GeffMetadata(
            directed=True,
            axes=[],
            node_props_metadata={},
            edge_props_metadata={},
        )
        with pytest.raises(ValueError):
            _identify_time_prop(None, geff_md_no_time, graph_lin_id)


class TestIdentifySpaceProps:
    """Test cases for _identify_space_props function."""

    def test_provided_keys_returned_as_is(self, graph_with_coords):
        """When provided keys exist in the graph, return them unchanged with no logging."""
        result = _identify_space_props(
            "position_x", "position_y", None, None, graph_with_coords
        )
        assert result == ("position_x", "position_y", None)

    def test_provided_z_key_returned(self, graph_with_3d_coords):
        """When all three coordinate keys are provided and in the graph, return all three."""
        result = _identify_space_props(
            "position_x", "position_y", "position_z", None, graph_with_3d_coords
        )
        assert result == ("position_x", "position_y", "position_z")

    def test_invalid_partial_coordinate_specification_raises(self, graph_with_coords):
        """A lone coordinate key is invalid even when that key is absent."""
        with pytest.raises(ValueError, match="both x and y"):
            _identify_space_props("missing_x", None, None, None, graph_with_coords)

    def test_single_provided_key_raises(self, graph_with_coords):
        """A partial coordinate specification is invalid."""
        with pytest.raises(ValueError, match="both x and y"):
            _identify_space_props("position_x", None, None, None, graph_with_coords)

    def test_all_none_no_geff_md_returns_none_tuple(self, graph_with_coords):
        """When all keys are None and geff_md is None, return (None, None, None) with no logging."""
        result = _identify_space_props(None, None, None, None, graph_with_coords)
        assert result == (None, None, None)

    def test_none_keys_inferred_from_display_hints(
        self, caplog, graph_with_coords, geff_md_display_hints
    ):
        """When keys are None and display hints have valid space props,
        infer x and y and log for each."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_space_props(
                None, None, None, geff_md_display_hints, graph_with_coords
            )
        assert len(caplog.records) == 2
        assert all(record.levelname == "INFO" for record in caplog.records)
        assert all(
            "inferred from display hints" in record.message for record in caplog.records
        )

        assert result == ("position_x", "position_y", None)

    def test_none_keys_inferred_from_axis_names(
        self, caplog, graph_with_coords, geff_md_axes
    ):
        """When keys are None and the space axes are named after coordinates, infer x
        and y from the axis names and log."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_space_props(
                None, None, None, geff_md_axes, graph_with_coords
            )
        assert len(caplog.records) == 2
        assert all(record.levelname == "INFO" for record in caplog.records)
        assert all(
            "inferred from axis name" in record.message for record in caplog.records
        )

        assert result == ("position_x", "position_y", None)

    def test_none_keys_all_three_inferred_from_axis_names(
        self, caplog, graph_with_3d_coords, geff_md_3d_axes
    ):
        """When all keys are None and 3D axes are present, infer x, y, and z from the
        axis names."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_space_props(
                None, None, None, geff_md_3d_axes, graph_with_3d_coords
            )
        assert len(caplog.records) == 3
        assert all(record.levelname == "INFO" for record in caplog.records)
        assert all(
            "inferred from axis name" in record.message for record in caplog.records
        )

        assert result == ("position_x", "position_y", "position_z")

    def test_provided_key_not_in_graph_falls_back_to_display_hints(
        self, caplog, graph_with_coords, geff_md_display_hints
    ):
        """When x and y keys are absent from the graph, warn and infer them from
        display hints."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_space_props(
                "missing_x", "missing_y", None, geff_md_display_hints, graph_with_coords
            )
        assert len(caplog.records) == 4
        assert caplog.records[0].levelname == "WARNING"
        assert caplog.records[1].levelname == "WARNING"
        assert "'missing_x' given as cell_x_prop" in caplog.records[0].message
        assert "'missing_y' given as cell_y_prop" in caplog.records[1].message
        assert "inferred from display hints" in caplog.records[2].message
        assert "inferred from display hints" in caplog.records[3].message

        assert result == ("position_x", "position_y", None)

    def test_provided_key_not_in_graph_falls_back_to_axes(
        self, caplog, graph_with_coords, geff_md_axes
    ):
        """When x and y keys are absent from the graph, warn and infer them from the
        axis names."""
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _identify_space_props(
                "missing_x", "missing_y", None, geff_md_axes, graph_with_coords
            )
        assert len(caplog.records) == 4
        assert caplog.records[0].levelname == "WARNING"
        assert caplog.records[1].levelname == "WARNING"
        assert "is not on every node" in caplog.records[0].message
        assert "is not on every node" in caplog.records[1].message
        assert "inferred from axis name" in caplog.records[2].message
        assert "inferred from axis name" in caplog.records[3].message

        assert result == ("position_x", "position_y", None)

    def test_display_hint_not_in_graph_silently_stays_none(
        self, graph_no_lin_id, geff_md_display_hints
    ):
        """When display hints point to props absent from the graph (and no axes),
        the slots stay None without any logging."""
        result = _identify_space_props(
            None, None, None, geff_md_display_hints, graph_no_lin_id
        )
        assert result == (None, None, None)

    @staticmethod
    def _md_and_graph(space_names, hints=None):
        """GEFF metadata with a time axis 't' then the given space axes, in that
        order, and a graph whose nodes have all these properties."""
        graph = nx.DiGraph()
        for node in range(2):
            graph.add_node(node, t=node, **{name: float(node) for name in space_names})
        geff_md = geff.GeffMetadata(
            directed=True,
            axes=[geff_spec.Axis(name="t", type="time")]
            + [geff_spec.Axis(name=name, type="space") for name in space_names],
            display_hints=hints,
            node_props_metadata={},
            edge_props_metadata={},
        )
        return geff_md, graph

    @pytest.mark.parametrize(
        "space_names, expected",
        [
            (["y", "x"], ("x", "y", None)),  # geff's CTC converter, 2D
            (["z", "y", "x"], ("x", "y", "z")),  # geff's CTC converter 3D, ultrack
            (
                ["POSITION_Z", "POSITION_Y", "POSITION_X"],
                ("POSITION_X", "POSITION_Y", "POSITION_Z"),
            ),
            (["X", "Y"], ("X", "Y", None)),
            (["cell_y", "cell_x"], ("cell_x", "cell_y", None)),
        ],
    )
    def test_axes_matched_by_name_whatever_their_position(self, space_names, expected):
        """Axes named after a coordinate are used for it, whatever their position:
        GEFF orders the axes like OME-Zarr, where x comes last."""
        geff_md, graph = self._md_and_graph(space_names)
        assert _identify_space_props(None, None, None, geff_md, graph) == expected

    def test_display_hints_take_precedence_over_axis_names(self):
        """Display hints decide before axis names, e.g. for a transposed display."""
        hints = geff_spec.DisplayHint(display_horizontal="y", display_vertical="x")
        geff_md, graph = self._md_and_graph(["y", "x"], hints=hints)
        result = _identify_space_props(None, None, None, geff_md, graph)
        assert result == ("y", "x", None)

    def test_unnamed_axes_assigned_by_position_with_warning(self, caplog):
        """Axes whose names don't stand for a coordinate are assigned by position as
        in OME-Zarr, x last, with a warning naming the assignments."""
        geff_md, graph = self._md_and_graph(["u", "v"])
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _identify_space_props(None, None, None, geff_md, graph)
        assert result == ("v", "u", None)
        assert len(caplog.records) == 1
        assert "'v' as cell_x, 'u' as cell_y" in caplog.records[0].message

    def test_three_unnamed_axes_assigned_z_y_x(self):
        """Three unnamed space axes are read as z, y, x, as in OME-Zarr."""
        geff_md, graph = self._md_and_graph(["u", "v", "w"])
        result = _identify_space_props(None, None, None, geff_md, graph)
        assert result == ("w", "v", "u")

    def test_unnamed_axes_after_names_taken_from_the_end(self):
        """When names give some coordinates, the others take the remaining unnamed
        axes from the end."""
        geff_md, graph = self._md_and_graph(["u", "v", "x"])
        result = _identify_space_props(None, None, None, geff_md, graph)
        assert result == ("x", "v", "u")

    def test_names_first_then_position_for_the_rest(self, caplog):
        """Named axes are matched first, then the remaining coordinates take the
        unnamed axes by position."""
        geff_md, graph = self._md_and_graph(["depth", "y", "x"])
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _identify_space_props(None, None, None, geff_md, graph)
        assert result == ("x", "y", "depth")
        assert len(caplog.records) == 1
        assert "'depth' as cell_z" in caplog.records[0].message

    def test_axis_named_for_another_coordinate_not_assigned_by_position(self, caplog):
        """An axis named after a coordinate that is already assigned is not used for
        another coordinate."""
        geff_md, graph = self._md_and_graph(["x", "y"])
        for node in graph.nodes:
            graph.nodes[node].update(col=1.0, row=2.0)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _identify_space_props("col", "row", None, geff_md, graph)
        assert result == ("col", "row", None)
        assert not caplog.records

    def test_several_axes_named_for_the_same_coordinate_raises(self):
        """Axis names that stand for the same coordinate are ambiguous."""
        geff_md, graph = self._md_and_graph(["cell_x", "nucleus_x", "cell_y"])
        with pytest.raises(ValueError, match="'cell_x', 'nucleus_x'"):
            _identify_space_props(None, None, None, geff_md, graph)

    def test_x_and_z_without_y_raises(self, graph_with_3d_coords):
        """Explicit coordinates must include x and y."""
        with pytest.raises(ValueError, match="both x and y"):
            _identify_space_props(
                "position_x", None, "position_z", None, graph_with_3d_coords
            )


class TestResolvePropKey:
    """Test cases for _resolve_prop_key function."""

    def test_new_name_free(self, caplog):
        """When new_name is not taken, return it and log."""
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _resolve_prop_key("cell_x", "fallback_x", {}, "x", PropertyType.NODE)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "'x' (node) has been renamed to 'cell_x'" in caplog.records[0].message

        assert result == "cell_x"

    def test_fallback_free_returns_fallback(self, caplog, prop_position_x_edge):
        """When new_name is taken but fallback is free, return fallback."""
        props_dict = {"link_x": prop_position_x_edge}
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _resolve_prop_key(
                "link_x", "fallback_x", props_dict, "x", PropertyType.EDGE
            )
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "'x' (edge) has been renamed to 'fallback_x'" in caplog.records[0].message
        assert "'link_x' was already taken" in caplog.records[0].message

        assert result == "fallback_x"

    def test_both_taken_raises_key_error(
        self, prop_cell_position_x, prop_pycellin_cell_position_x
    ):
        """When both new_name and fallback are taken, raise KeyError."""
        props_dict = {
            "cell_x": prop_cell_position_x,
            "pycellin_cell_x": prop_pycellin_cell_position_x,
        }
        with pytest.raises(
            KeyError,
            match="property 'x' \\(node\\): both 'cell_x' and 'pycellin_cell_x'",
        ):
            _resolve_prop_key(
                "cell_x", "pycellin_cell_x", props_dict, "x", PropertyType.NODE
            )


class TestExtractPropsMetadata:
    """Test cases for _extract_props_metadata function."""

    def test_empty_md_leaves_props_dict_unchanged(
        self, prop_position_x_node, prop_position_x_edge, rename_map
    ):
        """When md is empty, props_dict is not modified."""
        props_dict = {
            "node_prop": prop_position_x_node,
            "edge_prop": prop_position_x_edge,
        }
        _extract_props_metadata({}, props_dict, PropertyType.NODE, rename_map)
        assert list(props_dict.keys()) == ["node_prop", "edge_prop"]
        assert rename_map == {
            PropertyType.NODE: {},
            PropertyType.EDGE: {},
            PropertyType.LINEAGE: {},
        }

    def test_new_key_is_all_fields_added(self, geff_node_props_md, rename_map):
        """A key not yet in props_dict is added with the given prop_type."""
        props_dict = {}
        _extract_props_metadata(
            geff_node_props_md, props_dict, PropertyType.NODE, rename_map
        )
        assert "position_x" in props_dict
        assert props_dict["position_x"].identifier == "position_x"
        assert props_dict["position_x"].prop_type == PropertyType.NODE
        assert props_dict["position_x"].dtype == "float64"
        assert props_dict["position_x"].unit == "um"
        assert rename_map == {
            PropertyType.NODE: {},
            PropertyType.EDGE: {},
            PropertyType.LINEAGE: {},
        }

    def test_new_key_name_defaults_to_key_when_prop_name_is_none(
        self, geff_node_props_md, rename_map
    ):
        """When PropMetadata.name is None, Property.name falls back to the key."""
        props_dict = {}
        _extract_props_metadata(geff_node_props_md, props_dict, "node", rename_map)
        assert props_dict["frame"].name == "frame"

    def test_new_key_unit_is_none_when_prop_has_no_unit(
        self, geff_node_props_md, rename_map
    ):
        """When PropMetadata.unit is None, Property.unit is also None."""
        props_dict = {}
        _extract_props_metadata(geff_node_props_md, props_dict, "node", rename_map)
        assert props_dict["frame"].unit is None

    def test_multiple_new_keys_all_added(self, geff_node_props_md, rename_map):
        """When md contains multiple new keys, all are added to props_dict."""
        props_dict = {}
        _extract_props_metadata(geff_node_props_md, props_dict, "node", rename_map)
        assert "frame" in props_dict
        assert "position_x" in props_dict

    def test_duplicate_key_same_prop_type_raises_key_error(
        self, geff_node_props_md, prop_cell_position_x, rename_map
    ):
        """When a key already exists in props_dict with the same prop_type,
        raise KeyError."""
        props_dict = {"frame": prop_cell_position_x}
        with pytest.raises(
            KeyError,
            match="'frame': an identical identifier already exists in properties "
            "dictionary for nodes",
        ):
            _extract_props_metadata(
                {"frame": geff_node_props_md["frame"]},
                props_dict,
                PropertyType.NODE,
                rename_map,
            )

    def test_node_collides_with_existing_edge_renames_both(
        self, caplog, geff_node_props_md, prop_position_x_edge, rename_map
    ):
        """When a node prop collides with an existing edge prop, both are renamed:
        the new node prop becomes 'cell_<key>' and the edge prop becomes 'link_<key>'."""
        props_dict = {"position_x": prop_position_x_edge}
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            _extract_props_metadata(
                geff_node_props_md, props_dict, PropertyType.NODE, rename_map
            )
        assert len(caplog.records) == 2
        assert all(record.levelname == "WARNING" for record in caplog.records)
        assert "renamed to 'cell_position_x'" in caplog.records[0].message
        assert "renamed to 'link_position_x'" in caplog.records[1].message

        assert "position_x" not in props_dict
        assert "cell_position_x" in props_dict
        assert props_dict["cell_position_x"].identifier == "cell_position_x"
        assert props_dict["cell_position_x"].prop_type == PropertyType.NODE
        assert "link_position_x" in props_dict
        assert props_dict["link_position_x"].identifier == "link_position_x"
        assert props_dict["link_position_x"].prop_type == PropertyType.EDGE
        assert rename_map[PropertyType.NODE] == {"position_x": "cell_position_x"}
        assert rename_map[PropertyType.EDGE] == {"position_x": "link_position_x"}
        assert rename_map[PropertyType.LINEAGE] == {}

    def test_edge_collides_with_existing_node_renames_both(
        self, caplog, geff_node_props_md, prop_position_x_node, rename_map
    ):
        """When an edge key collides with an existing node prop, both are renamed:
        the new edge prop becomes 'link_<key>' and the node prop becomes 'cell_<key>'."""
        props_dict = {"position_x": prop_position_x_node}
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            _extract_props_metadata(
                geff_node_props_md, props_dict, PropertyType.EDGE, rename_map
            )
        assert len(caplog.records) == 2
        assert all(record.levelname == "WARNING" for record in caplog.records)
        assert "renamed to 'link_position_x'" in caplog.records[0].message
        assert "renamed to 'cell_position_x'" in caplog.records[1].message

        assert "position_x" not in props_dict
        assert "link_position_x" in props_dict
        assert props_dict["link_position_x"].identifier == "link_position_x"
        assert props_dict["link_position_x"].prop_type == PropertyType.EDGE
        assert "cell_position_x" in props_dict
        assert props_dict["cell_position_x"].identifier == "cell_position_x"
        assert props_dict["cell_position_x"].prop_type == PropertyType.NODE
        assert rename_map[PropertyType.EDGE] == {"position_x": "link_position_x"}
        assert rename_map[PropertyType.NODE] == {"position_x": "cell_position_x"}
        assert rename_map[PropertyType.LINEAGE] == {}

    def test_node_collision_primary_new_key_taken_uses_fallback(
        self,
        caplog,
        geff_node_props_md,
        prop_position_x_edge,
        prop_cell_position_x,
        rename_map,
    ):
        """When 'cell_<key>' is already in props_dict, the new node prop falls back
        to 'pycellin_cell_<key>'."""
        props_dict = {
            "position_x": prop_position_x_edge,
            "cell_position_x": prop_cell_position_x,  # primary rename taken
        }
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            _extract_props_metadata(
                geff_node_props_md, props_dict, PropertyType.NODE, rename_map
            )
        assert len(caplog.records) == 2
        assert all(record.levelname == "WARNING" for record in caplog.records)
        assert "renamed to 'pycellin_cell_position_x'" in caplog.records[0].message
        assert "renamed to 'link_position_x'" in caplog.records[1].message

        assert "position_x" not in props_dict
        assert "pycellin_cell_position_x" in props_dict
        assert props_dict["pycellin_cell_position_x"].prop_type == PropertyType.NODE
        assert "link_position_x" in props_dict
        assert props_dict["link_position_x"].prop_type == PropertyType.EDGE
        assert "cell_position_x" in props_dict  # original unaffected
        assert rename_map[PropertyType.NODE] == {"position_x": "pycellin_cell_position_x"}
        assert rename_map[PropertyType.EDGE] == {"position_x": "link_position_x"}
        assert rename_map[PropertyType.LINEAGE] == {}

    def test_both_rename_candidates_taken_raises_key_error(
        self,
        geff_node_props_md,
        prop_position_x_edge,
        prop_cell_position_x,
        prop_pycellin_cell_position_x,
        rename_map,
    ):
        """When both 'cell_<key>' and 'pycellin_cell_<key>' are already in props_dict,
        raise KeyError."""
        props_dict = {
            "position_x": prop_position_x_edge,
            "cell_position_x": prop_cell_position_x,
            "pycellin_cell_position_x": prop_pycellin_cell_position_x,
        }
        with pytest.raises(KeyError, match="Cannot register property 'position_x'"):
            _extract_props_metadata(
                geff_node_props_md, props_dict, PropertyType.NODE, rename_map
            )


class TestExtractLinPropsMetadata:
    """Test cases for _extract_lin_props_metadata function."""

    def test_empty_md_leaves_props_dict_unchanged(self, prop_position_x_node, rename_map):
        """When md is empty, props_dict is not modified."""
        props_dict = {"position_x": prop_position_x_node}
        _extract_lin_props_metadata({}, props_dict, rename_map)
        assert list(props_dict.keys()) == ["position_x"]

    def test_new_key_all_fields_added(self, lin_props_md, rename_map):
        """A key not yet in props_dict is added with all correct fields."""
        props_dict = {}
        _extract_lin_props_metadata(lin_props_md, props_dict, rename_map)
        assert "displacement" in props_dict
        assert props_dict["displacement"].identifier == "displacement"
        assert props_dict["displacement"].prop_type == PropertyType.LINEAGE
        assert props_dict["displacement"].dtype == "float"
        assert props_dict["displacement"].unit == "um"
        assert rename_map == {
            PropertyType.NODE: {},
            PropertyType.EDGE: {},
            PropertyType.LINEAGE: {},
        }

    def test_new_key_name_defaults_to_key_when_name_is_none(
        self, lin_props_md, rename_map
    ):
        """When prop dict has name=None, Property.name falls back to the key."""
        props_dict = {}
        _extract_lin_props_metadata(lin_props_md, props_dict, rename_map)
        assert props_dict["n_divisions"].name == "n_divisions"

    def test_new_key_unit_is_none_when_not_set(self, lin_props_md, rename_map):
        """When prop dict has unit=None, Property.unit is None."""
        props_dict = {}
        _extract_lin_props_metadata(lin_props_md, props_dict, rename_map)
        assert props_dict["n_divisions"].unit is None

    def test_multiple_new_keys_all_added(self, lin_props_md, rename_map):
        """When md contains multiple new keys, all are added to props_dict."""
        props_dict = {}
        _extract_lin_props_metadata(lin_props_md, props_dict, rename_map)
        assert "n_divisions" in props_dict
        assert "displacement" in props_dict

    def test_duplicate_key_same_prop_type_raises_key_error(
        self, prop_position_x_lineage, rename_map
    ):
        """When a key already exists in props_dict with prop_type='lineage',
        raise KeyError."""
        props_dict = {"position_x": prop_position_x_lineage}
        with pytest.raises(KeyError, match="Cannot register property 'position_x'"):
            _extract_lin_props_metadata(
                {"position_x": {"dtype": "float"}}, props_dict, rename_map
            )

    def test_lineage_collides_with_existing_node_renames_both(
        self, caplog, prop_position_x_node, rename_map
    ):
        """When a lineage prop collides with an existing node prop, both are renamed:
        the new lineage prop becomes 'lin_<key>' and the node prop becomes 'cell_<key>'."""
        props_dict = {"position_x": prop_position_x_node}
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            _extract_lin_props_metadata(
                {"position_x": {"dtype": "float"}}, props_dict, rename_map
            )
        assert len(caplog.records) == 2
        assert all(record.levelname == "WARNING" for record in caplog.records)
        assert "renamed to 'lin_position_x'" in caplog.records[0].message
        assert "renamed to 'cell_position_x'" in caplog.records[1].message

        assert "position_x" not in props_dict
        assert "lin_position_x" in props_dict
        assert props_dict["lin_position_x"].identifier == "lin_position_x"
        assert props_dict["lin_position_x"].prop_type == PropertyType.LINEAGE
        assert "cell_position_x" in props_dict
        assert props_dict["cell_position_x"].identifier == "cell_position_x"
        assert props_dict["cell_position_x"].prop_type == PropertyType.NODE
        assert rename_map[PropertyType.LINEAGE] == {"position_x": "lin_position_x"}
        assert rename_map[PropertyType.NODE] == {"position_x": "cell_position_x"}
        assert rename_map[PropertyType.EDGE] == {}

    def test_lineage_collides_with_existing_edge_renames_both(
        self, caplog, prop_position_x_edge, rename_map
    ):
        """When a lineage prop collides with an existing edge prop, both are renamed:
        the new lineage prop becomes 'lin_<key>' and the edge prop becomes 'link_<key>'."""
        props_dict = {"position_x": prop_position_x_edge}
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            _extract_lin_props_metadata(
                {"position_x": {"dtype": "float"}}, props_dict, rename_map
            )
        assert len(caplog.records) == 2
        assert all(record.levelname == "WARNING" for record in caplog.records)
        assert "renamed to 'lin_position_x'" in caplog.records[0].message
        assert "renamed to 'link_position_x'" in caplog.records[1].message

        assert "position_x" not in props_dict
        assert "lin_position_x" in props_dict
        assert props_dict["lin_position_x"].identifier == "lin_position_x"
        assert props_dict["lin_position_x"].prop_type == PropertyType.LINEAGE
        assert "link_position_x" in props_dict
        assert props_dict["link_position_x"].identifier == "link_position_x"
        assert props_dict["link_position_x"].prop_type == PropertyType.EDGE
        assert rename_map[PropertyType.LINEAGE] == {"position_x": "lin_position_x"}
        assert rename_map[PropertyType.EDGE] == {"position_x": "link_position_x"}
        assert rename_map[PropertyType.NODE] == {}

    def test_lineage_collision_primary_new_key_taken_uses_fallback(
        self, caplog, prop_position_x_node, prop_lin_position_x, rename_map
    ):
        """When 'lin_<key>' is already in props_dict, the new lineage prop falls back
        to 'pycellin_lin_<key>'."""
        props_dict = {
            "position_x": prop_position_x_node,
            "lin_position_x": prop_lin_position_x,  # primary rename taken
        }
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            _extract_lin_props_metadata(
                {"position_x": {"dtype": "float"}}, props_dict, rename_map
            )
        assert len(caplog.records) == 2
        assert all(record.levelname == "WARNING" for record in caplog.records)
        assert "renamed to 'pycellin_lin_position_x'" in caplog.records[0].message
        assert "renamed to 'cell_position_x'" in caplog.records[1].message

        assert "position_x" not in props_dict
        assert "pycellin_lin_position_x" in props_dict
        assert props_dict["pycellin_lin_position_x"].prop_type == PropertyType.LINEAGE
        assert "cell_position_x" in props_dict
        assert props_dict["cell_position_x"].prop_type == PropertyType.NODE
        assert "lin_position_x" in props_dict  # original unaffected
        assert rename_map[PropertyType.LINEAGE] == {
            "position_x": "pycellin_lin_position_x"
        }
        assert rename_map[PropertyType.NODE] == {"position_x": "cell_position_x"}
        assert rename_map[PropertyType.EDGE] == {}

    def test_both_rename_candidates_taken_raises_key_error(
        self,
        prop_position_x_node,
        prop_lin_position_x,
        prop_pycellin_lin_position_x,
        rename_map,
    ):
        """When both 'lin_<key>' and 'pycellin_lin_<key>' are already in props_dict,
        raise KeyError."""
        props_dict = {
            "position_x": prop_position_x_node,
            "lin_position_x": prop_lin_position_x,
            "pycellin_lin_position_x": prop_pycellin_lin_position_x,
        }
        with pytest.raises(KeyError, match="Cannot register property 'position_x'"):
            _extract_lin_props_metadata(
                {"position_x": {"dtype": "float"}}, props_dict, rename_map
            )


class TestBuildPropsMetadata:
    """Test cases for _build_props_metadata function."""

    def test_empty_node_and_edge_props_returns_empty_dict(self, rename_map):
        """When node and edge props metadata are empty dicts and extra is None,
        return an empty props_dict."""
        geff_md = geff.GeffMetadata(
            directed=True, node_props_metadata={}, edge_props_metadata={}
        )
        result = _build_props_metadata(geff_md, rename_map)
        assert result == {}

    def test_node_props_only_all_added_as_node(self, geff_node_props_md, rename_map):
        """When only node_props_metadata is provided, all keys are added with
        prop_type='node'."""
        geff_md = geff.GeffMetadata(
            directed=True,
            node_props_metadata=geff_node_props_md,
            edge_props_metadata={},
        )
        result = _build_props_metadata(geff_md, rename_map)
        assert "frame" in result
        assert result["frame"].prop_type == PropertyType.NODE
        assert result["frame"].dtype == "int64"
        assert "position_x" in result
        assert result["position_x"].prop_type == PropertyType.NODE
        assert result["position_x"].unit == "um"
        assert rename_map == {
            PropertyType.NODE: {},
            PropertyType.EDGE: {},
            PropertyType.LINEAGE: {},
        }

    def test_edge_props_only_all_added_as_edge(self, geff_edge_props_md, rename_map):
        """When only edge_props_metadata is provided, all keys are added with
        prop_type='edge'."""
        geff_md = geff.GeffMetadata(
            directed=True,
            node_props_metadata={},
            edge_props_metadata=geff_edge_props_md,
        )
        result = _build_props_metadata(geff_md, rename_map)
        assert "speed" in result
        assert result["speed"].prop_type == PropertyType.EDGE
        assert result["speed"].dtype == "float64"
        assert "cost" in result
        assert result["cost"].prop_type == PropertyType.EDGE
        assert result["cost"].unit is None
        assert rename_map == {
            PropertyType.NODE: {},
            PropertyType.EDGE: {},
            PropertyType.LINEAGE: {},
        }

    def test_node_and_edge_props_no_collision_both_added(
        self, geff_node_props_md, geff_edge_props_md, rename_map
    ):
        """When node and edge metadata have different keys, all props are added."""
        geff_md = geff.GeffMetadata(
            directed=True,
            node_props_metadata=geff_node_props_md,
            edge_props_metadata=geff_edge_props_md,
        )
        result = _build_props_metadata(geff_md, rename_map)
        assert "frame" in result
        assert result["frame"].prop_type == PropertyType.NODE
        assert "position_x" in result
        assert result["position_x"].prop_type == PropertyType.NODE
        assert "speed" in result
        assert result["speed"].prop_type == PropertyType.EDGE
        assert "cost" in result
        assert result["cost"].prop_type == PropertyType.EDGE
        assert rename_map == {
            PropertyType.NODE: {},
            PropertyType.EDGE: {},
            PropertyType.LINEAGE: {},
        }

    def test_node_and_edge_collision_both_renamed(
        self, caplog, geff_node_props_md, rename_map
    ):
        """When a key appears in both node and edge metadata, both props are renamed
        with appropriate prefixes."""
        geff_md = geff.GeffMetadata(
            directed=True,
            node_props_metadata=geff_node_props_md,
            edge_props_metadata={
                "position_x": geff_spec.PropMetadata(
                    identifier="position_x",
                    dtype="float64",
                    unit="um",
                )
            },
        )
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _build_props_metadata(geff_md, rename_map)
        assert len(caplog.records) == 2
        assert all(record.levelname == "WARNING" for record in caplog.records)
        assert "renamed to 'link_position_x'" in caplog.records[0].message
        assert "renamed to 'cell_position_x'" in caplog.records[1].message

        assert "position_x" not in result
        assert "cell_position_x" in result
        assert result["cell_position_x"].prop_type == PropertyType.NODE
        assert "link_position_x" in result
        assert result["link_position_x"].prop_type == PropertyType.EDGE
        assert rename_map[PropertyType.NODE] == {"position_x": "cell_position_x"}
        assert rename_map[PropertyType.EDGE] == {"position_x": "link_position_x"}
        assert rename_map[PropertyType.LINEAGE] == {}

    def test_lineage_props_in_extra_direct_key(self, lin_props_md, rename_map):
        """When extra contains 'lineage_props_metadata' at the top level, lineage
        props are extracted and added with prop_type='lineage'."""
        geff_md = geff.GeffMetadata(
            directed=True,
            node_props_metadata={},
            edge_props_metadata={},
            extra={"lineage_props_metadata": lin_props_md},
        )
        result = _build_props_metadata(geff_md, rename_map)
        assert "n_divisions" in result
        assert result["n_divisions"].prop_type == PropertyType.LINEAGE
        assert result["n_divisions"].dtype == "int"
        assert "displacement" in result
        assert result["displacement"].prop_type == PropertyType.LINEAGE
        assert result["displacement"].unit == "um"
        assert rename_map == {
            PropertyType.NODE: {},
            PropertyType.EDGE: {},
            PropertyType.LINEAGE: {},
        }

    def test_lineage_props_nested_in_extra(self, lin_props_md, rename_map):
        """When 'lineage_props_metadata' is nested inside extra, it is still found
        and extracted."""
        geff_md = geff.GeffMetadata(
            directed=True,
            node_props_metadata={},
            edge_props_metadata={},
            extra={"some_section": {"lineage_props_metadata": lin_props_md}},
        )
        result = _build_props_metadata(geff_md, rename_map)
        assert result["n_divisions"].prop_type == PropertyType.LINEAGE
        assert result["displacement"].prop_type == PropertyType.LINEAGE

    def test_extra_without_lineage_props_metadata_no_lineage_added(self, rename_map):
        """When extra exists but contains no 'lineage_props_metadata' key, no
        lineage props are added."""
        geff_md = geff.GeffMetadata(
            directed=True,
            node_props_metadata={},
            edge_props_metadata={},
            extra={"some_other_key": {"unrelated": "data"}},
        )
        result = _build_props_metadata(geff_md, rename_map)
        assert result == {}

    def test_node_edge_and_lineage_props_all_combined(
        self, geff_node_props_md, geff_edge_props_md, lin_props_md, rename_map
    ):
        """When node, edge, and lineage props are all present without collisions,
        all are added to the result."""
        geff_md = geff.GeffMetadata(
            directed=True,
            node_props_metadata=geff_node_props_md,
            edge_props_metadata=geff_edge_props_md,
            extra={"lineage_props_metadata": lin_props_md},
        )
        result = _build_props_metadata(geff_md, rename_map)
        assert result["frame"].prop_type == PropertyType.NODE
        assert result["position_x"].prop_type == PropertyType.NODE
        assert result["speed"].prop_type == PropertyType.EDGE
        assert result["cost"].prop_type == PropertyType.EDGE
        assert result["n_divisions"].prop_type == PropertyType.LINEAGE
        assert result["displacement"].prop_type == PropertyType.LINEAGE
        assert rename_map == {
            PropertyType.NODE: {},
            PropertyType.EDGE: {},
            PropertyType.LINEAGE: {},
        }


class TestGetPropUnit:
    """Test cases for _get_prop_unit function."""

    def test_unit_from_node_props_md(self, geff_node_props_md):
        """When node_props_md contains the prop with a unit, return it directly."""
        result = _get_prop_unit("position_x", "space", geff_node_props_md, [])
        assert result == "um"

    def test_node_props_md_unit_takes_priority_over_axes(self, geff_node_props_md):
        """When the prop is in node_props_md with a unit, axes are not consulted
        even if the axis lists a different unit for the same prop."""
        conflicting_axes = [
            geff_spec.Axis(name="position_x", type="space", unit="millimeter")
        ]
        result = _get_prop_unit(
            "position_x", "space", geff_node_props_md, conflicting_axes
        )
        assert result == "um"

    def test_fallback_to_axes_when_prop_unit_is_none(self, geff_node_props_md, geff_axes):
        """When node_props_md has the prop but unit is None, fall back to axes."""
        result = _get_prop_unit("frame", "time", geff_node_props_md, geff_axes)
        assert result == "second"

    def test_fallback_to_axes_when_node_props_md_is_none(self, geff_axes):
        """When node_props_md is None, fall back to axes."""
        result = _get_prop_unit("position_x", "space", None, geff_axes)
        assert result == "um"

    def test_fallback_to_axes_when_prop_not_in_node_props_md(
        self, geff_node_props_md, geff_axes
    ):
        """When prop is absent from node_props_md, fall back to axes."""
        result = _get_prop_unit("position_y", "space", geff_node_props_md, geff_axes)
        assert result == "um"

    def test_returns_none_when_no_unit_found_anywhere(self, geff_node_props_md):
        """When unit is None in node_props_md and the prop has no matching axis, return None."""
        result = _get_prop_unit("frame", "time", geff_node_props_md, [])
        assert result is None

    def test_returns_none_when_node_props_md_is_none_and_no_axes(self):
        """When both node_props_md and axes are empty/None, return None."""
        result = _get_prop_unit("position_x", "space", None, [])
        assert result is None

    def test_returns_none_when_axis_type_does_not_match(self, geff_axes):
        """When the prop exists in axes but with a different type, return None."""
        result = _get_prop_unit("frame", "space", None, geff_axes)
        assert result is None

    def test_assertion_error_on_duplicate_axes(self, duplicate_time_axes):
        """When multiple axes match the prop name and axis type, raise AssertionError."""
        with pytest.raises(AssertionError):
            _get_prop_unit("frame", "time", None, duplicate_time_axes)


class TestExtractAxesMetadata:
    """Test cases for _extract_axes_metadata function."""

    def _make_geff_md(
        self,
        axes=None,
        node_props_md=None,
    ) -> geff.GeffMetadata:
        """Helper to build a minimal GeffMetadata."""
        return geff.GeffMetadata(
            directed=True,
            axes=axes,
            node_props_metadata=node_props_md or {},
            edge_props_metadata={},
        )

    def test_returns_both_time_and_space_unit(self, geff_axes):
        """When axes carry time and uniform space units, both are in the result."""
        geff_md = self._make_geff_md(axes=geff_axes)
        result = _extract_axes_metadata(
            geff_md, "frame", "position_x", "position_y", None
        )
        assert result["time_unit"] == "second"
        assert result["space_unit"] == "um"

    def test_no_time_unit_warns_and_absent_from_result(self, caplog, geff_axes):
        """When no unit is found for the time property, log and omit time_unit."""
        geff_md = self._make_geff_md(axes=geff_axes)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _extract_axes_metadata(
                geff_md, "unknown_time", "position_x", None, None
            )
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "No unit found for time property" in caplog.records[0].message

        assert "time_unit" not in result
        assert result["space_unit"] == "um"

    def test_all_space_props_none_warns(self, caplog, geff_axes):
        """When all space props are None, log and omit space_unit."""
        geff_md = self._make_geff_md(axes=geff_axes)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _extract_axes_metadata(geff_md, "frame", None, None, None)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "No coordinate properties found" in caplog.records[0].message

        assert result["time_unit"] == "second"
        assert "space_unit" not in result

    def test_no_space_unit_found_warns(self, caplog, geff_axes):
        """When space props are provided but no unit found, log and omit space_unit."""
        geff_md = self._make_geff_md(axes=geff_axes)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _extract_axes_metadata(geff_md, "frame", "unknown_x", None, None)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "No unit found for space properties" in caplog.records[0].message

        assert "space_unit" not in result

    def test_multiple_space_units_warns(self, caplog):
        """When x and y props have different units, log and omit space_unit."""
        mixed_axes = [
            geff_spec.Axis(name="frame", type="time", unit="second"),
            geff_spec.Axis(name="position_x", type="space", unit="um"),
            geff_spec.Axis(name="position_y", type="space", unit="millimeter"),
        ]
        geff_md = self._make_geff_md(axes=mixed_axes)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _extract_axes_metadata(
                geff_md, "frame", "position_x", "position_y", None
            )
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "Multiple space units found" in caplog.records[0].message

        assert "space_unit" not in result

    def test_partial_space_props_single_unit(self, geff_axes):
        """When only x_prop is provided and has a unit, space_unit is set."""
        geff_md = self._make_geff_md(axes=geff_axes)
        result = _extract_axes_metadata(geff_md, "frame", "position_x", None, None)
        assert result["space_unit"] == "um"

    def test_space_unit_from_node_props_md(self, caplog, geff_node_props_md):
        """When unit comes from node_props_md (no axes), space_unit is set correctly."""
        geff_md = self._make_geff_md(axes=None, node_props_md=geff_node_props_md)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _extract_axes_metadata(geff_md, "frame", "position_x", None, None)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "No unit found for time property" in caplog.records[0].message

        assert result["space_unit"] == "um"
        assert "time_unit" not in result


class TestExtractGenericMetadata:
    """Test cases for _extract_generic_metadata function."""

    def test_name_is_stem_of_file_path(self, geff_md_axes):
        """The 'name' key is the stem of the provided file path."""
        result = _extract_generic_metadata("/some/path/my_tracking.geff", geff_md_axes)
        assert result["name"] == "my_tracking"

    def test_file_location_matches_input(self, geff_md_axes):
        """The 'file_location' key equals the geff_file argument exactly."""
        path = "/some/path/my_tracking.geff"
        result = _extract_generic_metadata(path, geff_md_axes)
        assert result["file_location"] == path

    def test_provenance_is_geff(self, geff_md_axes):
        """The 'provenance' key is always 'geff'."""
        result = _extract_generic_metadata("/some/tracks.geff", geff_md_axes)
        assert result["provenance"] == "geff"

    def test_date_is_non_empty_string(self, geff_md_axes):
        """The 'date' key is a non-empty string."""
        result = _extract_generic_metadata("/some/tracks.geff", geff_md_axes)
        assert isinstance(result["date"], str)
        assert len(result["date"]) > 0

    def test_pycellin_version_matches_installed_package(self, geff_md_axes):
        """The 'pycellin_version' key matches the installed pycellin version."""
        expected = importlib.metadata.version("pycellin")
        result = _extract_generic_metadata("/some/tracks.geff", geff_md_axes)
        assert result["pycellin_version"] == expected

    def test_geff_version_matches_metadata(self, geff_md_axes):
        """The 'geff_version' key matches geff_md.geff_version."""
        result = _extract_generic_metadata("/some/tracks.geff", geff_md_axes)
        assert result["geff_version"] == geff_md_axes.geff_version

    def test_geff_extra_included_when_extra_has_content(self, geff_node_props_md):
        """When geff_md.extra has content, 'geff_extra' is included in the result."""
        geff_md_with_extra = geff.GeffMetadata(
            directed=True,
            node_props_metadata=geff_node_props_md,
            edge_props_metadata={},
            extra={"custom_key": "custom_value"},
        )
        result = _extract_generic_metadata("/some/tracks.geff", geff_md_with_extra)
        assert result["geff_extra"] == {"custom_key": "custom_value"}

    def test_geff_extra_is_empty_dict_when_no_extra_provided(self, geff_md_axes):
        """When geff_md.extra is the default empty dict, 'geff_extra' is included but empty."""
        result = _extract_generic_metadata("/some/tracks.geff", geff_md_axes)
        assert result["geff_extra"] == {}


class TestBuildGenericMetadata:
    """Test cases for _build_generic_metadata function."""

    def test_reference_time_property_is_set(self, geff_md_axes):
        """The 'reference_time_property' key equals the time_prop argument."""
        result = _build_generic_metadata(
            "/some/tracks.geff", geff_md_axes, "frame", "position_x", None, None
        )
        assert result["reference_time_property"] == "frame"

    def test_includes_all_generic_metadata_keys(self, geff_md_axes):
        """All keys from _extract_generic_metadata are present in the result."""
        result = _build_generic_metadata(
            "/some/tracks.geff", geff_md_axes, "frame", "position_x", None, None
        )
        for key in (
            "name",
            "file_location",
            "provenance",
            "date",
            "pycellin_version",
            "geff_version",
        ):
            assert key in result

    def test_units_merged_from_axes(self, geff_md_axes):
        """When a unit is found in axes, xxx_unit is merged into the result."""
        result = _build_generic_metadata(
            "/some/tracks.geff", geff_md_axes, "frame", "position_x", None, None
        )
        assert result["time_unit"] == "second"
        assert result["space_unit"] == "um"

    def test_missing_units_produce_logs_and_absent_from_result(self, caplog):
        """When no units are found, appropriate logs are created and
        time_unit / space_unit are absent from the result."""
        geff_md_no_units = geff.GeffMetadata(
            directed=True,
            axes=[],
            node_props_metadata={},
            edge_props_metadata={},
        )
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _build_generic_metadata(
                "/some/tracks.geff",
                geff_md_no_units,
                "frame",
                "position_x",
                None,
                None,
            )
        assert len(caplog.records) == 2
        assert all(record.levelname == "WARNING" for record in caplog.records)
        assert "No unit found for time property 'frame'" in caplog.records[0].message
        assert "No unit found for space properties" in caplog.records[1].message

        assert "time_unit" not in result
        assert "space_unit" not in result


class TestRenameReservedProp:
    """Test cases for _rename_reserved_prop function."""

    def test_missing_prop_does_nothing(self, graph_no_lin_id, prop_cell_position_x):
        """When no node has the property, the graph and metadata are unchanged."""
        props_md = {"cell_position_x": prop_cell_position_x}
        _rename_reserved_prop(graph_no_lin_id, props_md, "cell_id")
        assert graph_no_lin_id.nodes[0] == {"frame": 0}
        assert list(props_md) == ["cell_position_x"]

    def test_renames_values_and_metadata(self, caplog, prop_geff_cell_id):
        """The values and the declaration of the property get the 'geff_' prefix."""
        g = nx.DiGraph()
        g.add_node(0, cell_id=5)
        g.add_node(1)
        props_md = {"cell_id": prop_geff_cell_id}
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            _rename_reserved_prop(g, props_md, "cell_id")
        assert len(caplog.records) == 1
        assert "renamed to 'geff_cell_id'" in caplog.records[0].message

        assert g.nodes[0] == {"geff_cell_id": 5}
        assert g.nodes[1] == {}
        assert list(props_md) == ["geff_cell_id"]
        assert props_md["geff_cell_id"].identifier == "geff_cell_id"

    def test_new_name_already_exists_raises(self):
        """When the GEFF file already has a 'geff_<key>' property, raise."""
        g = nx.DiGraph()
        g.add_node(0, lineage_id=1, geff_lineage_id=2)
        with pytest.raises(ValueError, match="'geff_lineage_id' already exists"):
            _rename_reserved_prop(g, {}, "lineage_id")


class TestGetCellIdProblem:
    """Test cases for _get_cell_id_problem function."""

    def test_valid_ids(self):
        """When the values are unique non-negative integers, return None."""
        g = nx.DiGraph()
        g.add_node(0, id=0)
        g.add_node(1, id=7)
        assert _get_cell_id_problem(g, "id") is None

    def test_not_integers(self):
        """When a value is not an integer, explain it."""
        g = nx.DiGraph()
        g.add_node(0, id=0)
        g.add_node(1, id=1.5)
        assert "not all positive integers" in _get_cell_id_problem(g, "id")

    def test_duplicates(self):
        """When two nodes have the same value, explain it."""
        g = nx.DiGraph()
        g.add_node(0, id=3)
        g.add_node(1, id=3)
        assert "Duplicate values found" in _get_cell_id_problem(g, "id")


class TestFallbackToNodeKeys:
    """Test cases for _fallback_to_node_keys function."""

    def test_sets_cell_id_from_node_keys(self, caplog, graph_no_lin_id):
        """When falling back, each node gets a cell_id equal to its node key."""
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            _fallback_to_node_keys(graph_no_lin_id, "fallback reason", {})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "fallback" in caplog.records[0].message

        assert graph_no_lin_id.nodes[0]["cell_id"] == 0
        assert graph_no_lin_id.nodes[1]["cell_id"] == 1
        assert graph_no_lin_id.nodes[0]["frame"] == 0
        assert graph_no_lin_id.nodes[1]["frame"] == 1

    def test_existing_cell_id_is_renamed(self):
        """A 'cell_id' property of the graph is kept as 'geff_cell_id'."""
        g = nx.DiGraph()
        g.add_node(0, cell_id=7)
        g.add_node(1, cell_id=7)
        _fallback_to_node_keys(g, "fallback reason", {})
        assert g.nodes[0] == {"geff_cell_id": 7, "cell_id": 0}
        assert g.nodes[1] == {"geff_cell_id": 7, "cell_id": 1}


class TestEnsureValidCellID:
    """Test cases for _ensure_valid_cell_id function."""

    def test_none_key_falls_back_to_node_keys(self, caplog, graph_no_lin_id):
        """When cell_id_key is None, create cell_id from node keys and log."""
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(graph_no_lin_id, None, {})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "No cell identifier property provided" in caplog.records[0].message

        assert result == "cell_id"
        assert graph_no_lin_id.nodes[0]["cell_id"] == 0
        assert graph_no_lin_id.nodes[1]["cell_id"] == 1
        assert graph_no_lin_id.nodes[0]["frame"] == 0
        assert graph_no_lin_id.nodes[1]["frame"] == 1

    def test_missing_prop_falls_back(self, caplog):
        """When cell_id_key is missing on some nodes, fall back and log."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(g, "id", {})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "not present on all nodes" in caplog.records[0].message

        assert result == "cell_id"
        assert g.nodes[0]["cell_id"] == 0
        assert g.nodes[1]["cell_id"] == 1

    def test_negative_value_fall_back(self, caplog):
        """When cell_id_key has a negative value, fall back and log."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1, id=-1)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(g, "id", {})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "not all positive integers" in caplog.records[0].message

        assert result == "cell_id"
        assert g.nodes[0]["cell_id"] == 0
        assert g.nodes[1]["cell_id"] == 1

    def test_string_value_fall_back(self, caplog):
        """When cell_id_key has a string value, fall back and log."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1, id="1")
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(g, "id", {})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "not all positive integers" in caplog.records[0].message

        assert result == "cell_id"
        assert g.nodes[0]["cell_id"] == 0
        assert g.nodes[1]["cell_id"] == 1

    def test_bool_value_fall_back(self, caplog):
        """When cell_id_key has a boolean value, fall back and log."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1, id=True)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(g, "id", {})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "not all positive integers" in caplog.records[0].message

        assert result == "cell_id"
        assert g.nodes[0]["cell_id"] == 0
        assert g.nodes[1]["cell_id"] == 1

    def test_none_value_fall_back(self, caplog):
        """When cell_id_key has a None value, fall back and log."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1, id=None)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(g, "id", {})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "not all positive integers" in caplog.records[0].message

        assert result == "cell_id"
        assert g.nodes[0]["cell_id"] == 0
        assert g.nodes[1]["cell_id"] == 1

    def test_duplicate_prop_values_fall_back(self, caplog):
        """When cell_id_key has duplicate values, fall back and log."""
        g = nx.Graph()
        g.add_node(0, id=1)
        g.add_node(1, id=1)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(g, "id", {})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "Duplicate values found" in caplog.records[0].message

        assert result == "cell_id"
        assert g.nodes[0]["cell_id"] == 0
        assert g.nodes[1]["cell_id"] == 1

    def test_valid_prop_relabels_nodes(self):
        """When cell_id_key is valid, relabel nodes to match property values."""
        g = nx.Graph()
        g.add_node(1, id=10)
        g.add_node(2, id=11)
        result = _ensure_valid_cell_id(g, "id", {})
        assert result == "id"
        assert set(g.nodes) == {10, 11}
        assert g.nodes[10]["id"] == 10
        assert g.nodes[11]["id"] == 11
        assert "cell_id" not in g.nodes[10]
        assert "cell_id" not in g.nodes[11]

    def test_none_key_uses_valid_cell_id(self, caplog):
        """When cell_id_key is None and the graph 'cell_id' is valid, use it to
        relabel nodes and log."""
        g = nx.DiGraph()
        g.add_node(1, cell_id=10)
        g.add_node(2, cell_id=11)
        with caplog.at_level(logging.INFO, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(g, None, {})
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        assert "inferred from existing graph property" in caplog.records[0].message

        assert result == "cell_id"
        assert set(g.nodes) == {10, 11}
        assert g.nodes[10] == {"cell_id": 10}

    def test_none_key_invalid_cell_id_is_renamed(self, caplog, prop_geff_cell_id):
        """When cell_id_key is None and the graph 'cell_id' is invalid, keep it as
        'geff_cell_id' and create cell_id from node keys."""
        g = nx.DiGraph()
        g.add_node(0, cell_id=1)
        g.add_node(1, cell_id=1)
        props_md = {"cell_id": prop_geff_cell_id}
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(g, None, props_md)
        assert len(caplog.records) == 2
        assert "Duplicate values found" in caplog.records[0].message
        assert "renamed to 'geff_cell_id'" in caplog.records[1].message

        assert result == "cell_id"
        assert g.nodes[0] == {"geff_cell_id": 1, "cell_id": 0}
        assert g.nodes[1] == {"geff_cell_id": 1, "cell_id": 1}
        assert list(props_md) == ["geff_cell_id"]

    def test_provided_key_renames_cell_id(self, caplog):
        """When cell_id_key is valid and the graph also has a 'cell_id', keep the
        latter as 'geff_cell_id'."""
        g = nx.DiGraph()
        g.add_node(1, id=10, cell_id=0)
        g.add_node(2, id=11, cell_id=0)
        with caplog.at_level(logging.WARNING, logger="pycellin.io.geff.loader"):
            result = _ensure_valid_cell_id(g, "id", {})
        assert len(caplog.records) == 1
        assert "renamed to 'geff_cell_id'" in caplog.records[0].message

        assert result == "id"
        assert g.nodes[10] == {"id": 10, "geff_cell_id": 0}
        assert g.nodes[11] == {"id": 11, "geff_cell_id": 0}

    def test_empty_graph(self):
        """When graph is empty, return the cell_id_key without modification."""
        g = nx.Graph()

        result = _ensure_valid_cell_id(g, "id", {})
        assert result == "id"
        assert len(g.nodes) == 0

        result = _ensure_valid_cell_id(g, None, {})
        assert result == "cell_id"
        assert len(g.nodes) == 0


class TestStandardizePropertiesData:
    """Test cases for _standardize_properties_data function."""

    def test_applies_collision_renames_and_standard_keys(
        self, lineages_with_nonstandard_keys, standardize_rename_map
    ):
        """Rename-map keys and pycellin standard keys are applied on nodes, edges,
        and lineage graph attributes."""
        _standardize_properties_data(
            lineages_with_nonstandard_keys,
            lin_id_key="custom_lin_id",
            cell_id_key="custom_cell_id",
            cell_x_key="pos_x",
            cell_y_key="pos_y",
            cell_z_key="pos_z",
            rename_map=standardize_rename_map,
        )

        lin_a, lin_b = lineages_with_nonstandard_keys

        # Node-level updates.
        for node in lin_a.nodes:
            data = lin_a.nodes[node]
            assert "custom_lin_id" not in data
            assert "custom_cell_id" not in data
            assert "pos_x" not in data
            assert "pos_y" not in data
            assert "pos_z" not in data
            assert "old_node_key" not in data
            assert "lineage_id" in data
            assert "cell_id" in data
            assert "cell_x" in data
            assert "cell_y" in data
            assert "cell_z" in data
            assert "new_node_key" in data

        for node in lin_b.nodes:
            data = lin_b.nodes[node]
            assert "custom_lin_id" not in data
            assert "custom_cell_id" not in data
            assert "pos_x" not in data
            assert "pos_y" not in data
            assert "pos_z" not in data
            assert "old_node_key" not in data
            assert "lineage_id" in data
            assert "cell_id" in data
            assert "cell_x" in data
            assert "cell_y" in data
            assert "cell_z" in data
            assert "new_node_key" in data

        # Edge-level updates.
        assert "old_edge_key" not in lin_a.edges[(0, 1)]
        assert lin_a.edges[(0, 1)]["new_edge_key"] == 0.5

        # Lineage-level updates.
        assert lin_a.graph["lineage_id"] == 11
        assert lin_b.graph["lineage_id"] == 12
        assert "custom_lin_id" not in lin_a.graph
        assert "custom_lin_id" not in lin_b.graph
        assert "old_lin_key" not in lin_a.graph
        assert "old_lin_key" not in lin_b.graph
        assert lin_a.graph["new_lin_key"] == "lin-a"
        assert lin_b.graph["new_lin_key"] == "lin-b"

    def test_skips_optional_coordinate_renames_when_none(
        self, lineages_with_nonstandard_keys
    ):
        """When x/y/z keys are None, coordinate properties are left unchanged."""
        _standardize_properties_data(
            lineages_with_nonstandard_keys,
            lin_id_key="custom_lin_id",
            cell_id_key="custom_cell_id",
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            rename_map={
                PropertyType.NODE: {},
                PropertyType.EDGE: {},
                PropertyType.LINEAGE: {},
            },
        )

        lin_a, _ = lineages_with_nonstandard_keys
        assert lin_a.nodes[0]["cell_id"] == 100
        assert lin_a.nodes[0]["lineage_id"] == 11
        assert "pos_x" in lin_a.nodes[0]
        assert "pos_y" in lin_a.nodes[0]
        assert "pos_z" in lin_a.nodes[0]
        assert "cell_x" not in lin_a.nodes[0]
        assert "cell_y" not in lin_a.nodes[0]
        assert "cell_z" not in lin_a.nodes[0]

    def test_keeps_graph_lin_id_when_already_standard(self, standardize_rename_map):
        """When lin_id_key is already 'lineage_id', lineage graph IDs are preserved."""
        lin = CellLineage()
        lin.add_node(
            1,
            lineage_id=0,
            custom_cell_id=11,
            pos_x=2.0,
            old_node_key="node",
        )
        lin.graph["lineage_id"] = 0
        lin.graph["old_lin_key"] = "lineage"

        _standardize_properties_data(
            [lin],
            lin_id_key="lineage_id",
            cell_id_key="custom_cell_id",
            cell_x_key="pos_x",
            cell_y_key=None,
            cell_z_key=None,
            rename_map=standardize_rename_map,
        )

        assert lin.graph["lineage_id"] == 0
        assert lin.nodes[1]["lineage_id"] == 0

    def test_skips_standard_cell_id_rename(self):
        """When cell_id_key is already 'cell_id', node cell IDs are preserved."""
        lin = CellLineage()
        lin.add_node(1, lineage_id=0, cell_id=11)
        lin.graph["lineage_id"] = 0

        _standardize_properties_data(
            [lin],
            lin_id_key="lineage_id",
            cell_id_key="cell_id",
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            rename_map={
                PropertyType.NODE: {},
                PropertyType.EDGE: {},
                PropertyType.LINEAGE: {},
            },
        )

        assert lin.nodes[1]["cell_id"] == 11

    def test_skips_standard_coordinate_renames(self):
        """When x/y/z keys are already 'cell_x', 'cell_y', 'cell_z', they are left unchanged."""
        lin = CellLineage()
        lin.add_node(1, lineage_id=0, cell_id=11, cell_x=1.0, cell_y=2.0, cell_z=3.0)
        lin.graph["lineage_id"] = 0

        _standardize_properties_data(
            [lin],
            lin_id_key="lineage_id",
            cell_id_key="cell_id",
            cell_x_key="cell_x",
            cell_y_key="cell_y",
            cell_z_key="cell_z",
            rename_map={
                PropertyType.NODE: {},
                PropertyType.EDGE: {},
                PropertyType.LINEAGE: {},
            },
        )

        assert lin.nodes[1]["cell_x"] == 1.0
        assert lin.nodes[1]["cell_y"] == 2.0
        assert lin.nodes[1]["cell_z"] == 3.0

    def test_coordinates_renamed_all_at_once(self):
        """A coordinate whose current name is the pycellin name of another one keeps
        its values, e.g. when the axes are permuted."""
        lin = CellLineage()
        lin.add_node(1, lineage_id=0, cell_id=11, cell_x=1.0, cell_y=2.0, cell_z=3.0)
        lin.graph["lineage_id"] = 0

        _standardize_properties_data(
            [lin],
            lin_id_key="lineage_id",
            cell_id_key="cell_id",
            cell_x_key="cell_z",
            cell_y_key="cell_x",
            cell_z_key="cell_y",
            rename_map={
                PropertyType.NODE: {},
                PropertyType.EDGE: {},
                PropertyType.LINEAGE: {},
            },
        )

        assert lin.nodes[1]["cell_x"] == 3.0
        assert lin.nodes[1]["cell_y"] == 1.0
        assert lin.nodes[1]["cell_z"] == 2.0

    def test_coordinate_renamed_from_its_collision_name(self):
        """A coordinate already renamed because of a node/edge name collision is
        renamed from that new name."""
        lin = CellLineage()
        lin.add_node(1, lineage_id=0, cell_id=11, x=1.0, y=2.0, z=3.0)
        lin.graph["lineage_id"] = 0

        _standardize_properties_data(
            [lin],
            lin_id_key="lineage_id",
            cell_id_key="cell_id",
            cell_x_key="z",
            cell_y_key="y",
            cell_z_key="x",
            rename_map={
                PropertyType.NODE: {"z": "cell_z"},
                PropertyType.EDGE: {},
                PropertyType.LINEAGE: {},
            },
        )

        assert lin.nodes[1]["cell_x"] == 3.0
        assert lin.nodes[1]["cell_y"] == 2.0
        assert lin.nodes[1]["cell_z"] == 1.0
        assert not {"x", "y", "z"} & set(lin.nodes[1])

    def test_assigns_fallback_lineage_id_for_single_node_lineage_without_key(self):
        """When lin_id_key is absent from a single-node lineage graph, -node_id is used."""
        lin = CellLineage()
        lin.add_node(1, custom_lin_id=0, custom_cell_id=10)

        _standardize_properties_data(
            [lin],
            lin_id_key="custom_lin_id",
            cell_id_key="custom_cell_id",
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            rename_map={
                PropertyType.NODE: {},
                PropertyType.EDGE: {},
                PropertyType.LINEAGE: {},
            },
        )

        assert lin.graph["lineage_id"] == -1

    def test_assigns_fallback_lineage_id_for_multi_node_lineage_without_key(self):
        """When lin_id_key is absent from a multi-node lineage graph, next available id is used."""
        lin_with_id = CellLineage()
        lin_with_id.add_node(0, custom_lin_id=10, custom_cell_id=100)
        lin_with_id.add_node(1, custom_lin_id=10, custom_cell_id=101)
        lin_with_id.graph["custom_lin_id"] = 10

        lin_without_id = CellLineage()
        lin_without_id.add_node(2, custom_lin_id=99, custom_cell_id=102)
        lin_without_id.add_node(3, custom_lin_id=99, custom_cell_id=103)

        _standardize_properties_data(
            [lin_with_id, lin_without_id],
            lin_id_key="custom_lin_id",
            cell_id_key="custom_cell_id",
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            rename_map={
                PropertyType.NODE: {},
                PropertyType.EDGE: {},
                PropertyType.LINEAGE: {},
            },
        )

        assert lin_with_id.graph["lineage_id"] == 10
        assert lin_without_id.graph["lineage_id"] == 11


class TestStandardizePropsMetadata:
    """Test cases for _standardize_props_metadata function."""

    def test_coordinate_declarations_renamed_all_at_once(self, rename_map):
        """Permuted coordinates keep their own declarations."""
        props_md = {
            "cell_x": create_cell_coord_property(unit="um", axis="x", provenance="a"),
            "cell_y": create_cell_coord_property(unit="um", axis="y", provenance="b"),
        }
        _standardize_props_metadata(
            props_md,
            lin_id_key=None,
            cell_id_key=None,
            cell_x_key="cell_y",
            cell_y_key="cell_x",
            cell_z_key=None,
            space_unit="um",
            rename_map=rename_map,
        )
        assert props_md["cell_x"].provenance == "b"
        assert props_md["cell_y"].provenance == "a"
        assert props_md["cell_x"].identifier == "cell_x"
        assert props_md["cell_y"].identifier == "cell_y"

    def test_lin_id_standard_key_preserved(self, pycellin_standard_md, rename_map):
        """When lineage_id_key is already 'lineage_id', key and metadata are preserved."""
        nb_props = len(pycellin_standard_md)
        _standardize_props_metadata(
            pycellin_standard_md,
            lin_id_key="lineage_id",
            cell_id_key=None,
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert len(pycellin_standard_md) == nb_props
        assert "lineage_id" in pycellin_standard_md
        assert pycellin_standard_md["lineage_id"].identifier == "lineage_id"
        assert pycellin_standard_md["lineage_id"].provenance == "test"

    def test_lin_id_nonstandard_renamed(self, pycellin_non_standard_md, rename_map):
        """When lineage_id_key is present but not 'lineage_id', it is renamed to 'lineage_id',
        and its identifier is updated but metadata is preserved."""
        _standardize_props_metadata(
            pycellin_non_standard_md,
            lin_id_key="track_id",
            cell_id_key=None,
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert "track_id" not in pycellin_non_standard_md
        assert "lineage_id" in pycellin_non_standard_md
        assert pycellin_non_standard_md["lineage_id"].identifier == "lineage_id"
        assert pycellin_non_standard_md["lineage_id"].provenance == "test"

    def test_lin_id_absent_creates_default(self, rename_map):
        """When lineage_id_key is None, a default 'lineage_id' property with provenance
        'geff' is created."""
        props_md = {}
        _standardize_props_metadata(
            props_md,
            lin_id_key=None,
            cell_id_key=None,
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert "lineage_id" in props_md
        assert props_md["lineage_id"].identifier == "lineage_id"
        assert props_md["lineage_id"].provenance == "geff"

    def test_cell_id_standard_key_preserved(self, pycellin_standard_md, rename_map):
        """When cell_id_key is already 'cell_id', key and metadata are preserved."""
        nb_props = len(pycellin_standard_md)
        _standardize_props_metadata(
            pycellin_standard_md,
            lin_id_key=None,
            cell_id_key="cell_id",
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert len(pycellin_standard_md) == nb_props
        assert "cell_id" in pycellin_standard_md
        assert pycellin_standard_md["cell_id"].identifier == "cell_id"
        assert pycellin_standard_md["cell_id"].provenance == "test"

    def test_cell_id_nonstandard_renamed(self, pycellin_non_standard_md, rename_map):
        """When cell_id_key is present but not 'cell_id', it is renamed to 'cell_id',
        and its identifier is updated but metadata is preserved."""
        _standardize_props_metadata(
            pycellin_non_standard_md,
            lin_id_key=None,
            cell_id_key="node_id",
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert "node_id" not in pycellin_non_standard_md
        assert "cell_id" in pycellin_non_standard_md
        assert pycellin_non_standard_md["cell_id"].identifier == "cell_id"
        assert pycellin_non_standard_md["cell_id"].provenance == "test"

    def test_cell_id_absent_creates_default(self, rename_map):
        """When cell_id_key is None, a default 'cell_id' property with provenance
        'geff' is created."""
        props_md = {}
        _standardize_props_metadata(
            props_md,
            lin_id_key=None,
            cell_id_key=None,
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert "cell_id" in props_md
        assert props_md["cell_id"].identifier == "cell_id"
        assert props_md["cell_id"].provenance == "geff"

    def test_coord_none_skips_all_coord_keys(self, rename_map):
        """When all coord props are None, no standard coordinate key is added to props_md."""
        props_md = {}
        _standardize_props_metadata(
            props_md,
            lin_id_key=None,
            cell_id_key=None,
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert "cell_x" not in props_md
        assert "cell_y" not in props_md
        assert "cell_z" not in props_md

    def test_coord_standard_key_preserved(self, pycellin_standard_md, rename_map):
        """When a coord prop is already standard, key and metadata are preserved."""
        nb_props = len(pycellin_standard_md)
        _standardize_props_metadata(
            pycellin_standard_md,
            lin_id_key=None,
            cell_id_key=None,
            cell_x_key="cell_x",
            cell_y_key=None,
            cell_z_key=None,
            space_unit="mm",
            rename_map=rename_map,
        )
        assert len(pycellin_standard_md) == nb_props
        assert "cell_x" in pycellin_standard_md
        assert pycellin_standard_md["cell_x"].identifier == "cell_x"
        assert pycellin_standard_md["cell_x"].unit == "um"
        assert pycellin_standard_md["cell_x"].provenance == "test"

    def test_coord_nonstandard_renamed(self, pycellin_non_standard_md, rename_map):
        """When a coord prop key differs from the pycellin convention, it is renamed
        and its identifier is updated but metadata is preserved."""
        _standardize_props_metadata(
            pycellin_non_standard_md,
            lin_id_key=None,
            cell_id_key=None,
            cell_x_key="position_x",
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert "position_x" not in pycellin_non_standard_md
        assert "cell_x" in pycellin_non_standard_md
        assert pycellin_non_standard_md["cell_x"].identifier == "cell_x"
        assert pycellin_non_standard_md["cell_x"].unit == "um"
        assert pycellin_non_standard_md["cell_x"].provenance == "test"

    def test_coord_absent_creates_default_with_unit(self, rename_map):
        """When the coord key is not in props_md, a default property is created
        using space_unit."""
        props_md = {}
        _standardize_props_metadata(
            props_md,
            lin_id_key=None,
            cell_id_key=None,
            cell_x_key="position_x",
            cell_y_key=None,
            cell_z_key=None,
            space_unit="um",
            rename_map=rename_map,
        )
        assert "cell_x" in props_md
        assert props_md["cell_x"].identifier == "cell_x"
        assert props_md["cell_x"].unit == "um"
        assert props_md["cell_x"].provenance == "geff"

    def test_lin_id_not_none_but_not_in_props_md_creates_default(self, rename_map):
        """When lin_id_key is provided but not in props_md, a default should be created
        (since it was not in metadata)."""
        props_md = {}
        _standardize_props_metadata(
            props_md,
            lin_id_key="custom_lineage_id",
            cell_id_key=None,
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert "custom_lineage_id" not in props_md
        assert "lineage_id" in props_md
        assert props_md["lineage_id"].identifier == "lineage_id"
        assert props_md["lineage_id"].provenance == "geff"

    def test_cell_id_not_none_but_not_in_props_md_creates_default(self, rename_map):
        """When cell_id_key is provided but not in props_md, a default should be created
        (since it was not in metadata)."""
        props_md = {}
        _standardize_props_metadata(
            props_md,
            lin_id_key=None,
            cell_id_key="custom_cell_id",
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert "custom_cell_id" not in props_md
        assert "cell_id" in props_md
        assert props_md["cell_id"].identifier == "cell_id"
        assert props_md["cell_id"].provenance == "geff"

    def test_coord_with_rename_map_transformation(self, prop_position_x_node, rename_map):
        """When a coordinate key is transformed by rename_map, the transformed key
        is looked up in props_md, renamed to pycellin convention, and identifier updated."""
        props_md = {"old_pos_x": prop_position_x_node}
        rename_map[PropertyType.NODE]["old_pos_x"] = "position_x"
        props_md["position_x"] = Property(
            identifier="position_x",
            name="position_x",
            description="position_x",
            provenance="test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
            unit="um",
        )
        _standardize_props_metadata(
            props_md,
            lin_id_key=None,
            cell_id_key=None,
            cell_x_key="old_pos_x",
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert "position_x" not in props_md
        assert "old_pos_x" not in props_md
        assert "cell_x" in props_md
        assert props_md["cell_x"].identifier == "cell_x"
        assert props_md["cell_x"].unit == "um"


class TestLoadGEFF:
    """Test cases for load_GEFF function."""

    def test_valid_ids_are_used(self, geff_valid_ids):
        """The 'cell_id' and 'lineage_id' properties of the file identify cells and
        lineages when they can."""
        model = load_GEFF(geff_valid_ids)

        assert set(model.data.cell_data) == {1, 2}
        lin = model.data.cell_data[1]
        assert set(lin.nodes) == {10, 11}
        assert all(lin.nodes[n]["cell_id"] == n for n in lin.nodes)
        assert all(lin.nodes[n]["lineage_id"] == 1 for n in lin.nodes)
        assert not any(prop.startswith("geff_") for prop in model.props_metadata.props)

    def test_clashing_ids_are_kept(self, geff_clashing_ids):
        """The 'cell_id' and 'lineage_id' properties of the file that cannot
        identify cells and lineages are kept as 'geff_cell_id' and 'geff_lineage_id'."""
        model = load_GEFF(geff_clashing_ids)

        assert len(model.data.cell_data) == 2
        nodes = {
            n: data
            for lin in model.data.cell_data.values()
            for n, data in lin.nodes(data=True)
        }
        assert {n: data["geff_cell_id"] for n, data in nodes.items()} == {
            0: 1,
            1: 1,
            2: 2,
            3: 3,
        }
        assert all(data["geff_lineage_id"] == 5 for data in nodes.values())
        assert all(data["cell_id"] == n for n, data in nodes.items())
        assert nodes[0]["lineage_id"] == nodes[1]["lineage_id"]
        assert nodes[0]["lineage_id"] != nodes[2]["lineage_id"]
        props = model.props_metadata.props
        assert props["geff_cell_id"].identifier == "geff_cell_id"
        assert props["geff_lineage_id"].identifier == "geff_lineage_id"
        assert props["cell_id"].provenance == "geff"
