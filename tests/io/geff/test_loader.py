"""Unit test for GEFF file loader."""

import importlib.metadata

import geff
import geff_spec
import networkx as nx
import pytest

from pycellin.classes import CellLineage, Property
from pycellin.custom_types import PropertyType
from pycellin.graph.properties.core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_lineage_id_property,
)
from pycellin.io.geff.loader import (
    _build_generic_metadata,
    _build_props_metadata,
    _extract_axes_metadata,
    _extract_generic_metadata,
    _extract_lin_props_metadata,
    _extract_props_metadata,
    _fallback_to_node_keys,
    _ensure_valid_cell_ID,
    _get_prop_unit,
    _identify_lin_id_prop,
    _identify_space_props,
    _identify_time_prop,
    _resolve_prop_key,
    _standardize_properties_data,
    _standardize_props_metadata,
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
    g.add_node(0, frame=0, lineage_ID=0, my_lin_id=0)
    g.add_node(1, frame=1, lineage_ID=1, my_lin_id=1)
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
        "lineage_ID": create_lineage_id_property(provenance="test"),
        "cell_ID": create_cell_id_property(provenance="test"),
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
    return {"node": {}, "edge": {}, "lineage": {}}


@pytest.fixture
def standardize_rename_map():
    """Rename map containing one key per property type."""
    return {
        "node": {"old_node_key": "new_node_key"},
        "edge": {"old_edge_key": "new_edge_key"},
        "lineage": {"old_lin_key": "new_lin_key"},
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


# Test Classes ################################################################


class TestIdentifyLinIdProp:
    """Test cases for _identify_lin_id_prop function."""

    def test_provided_key_exists_in_graph(self, graph_lin_id):
        """When lin_id_prop is provided and the property exists, return it."""
        result = _identify_lin_id_prop("my_lin_id", None, graph_lin_id)
        assert result == "my_lin_id"

    def test_provided_key_not_in_graph_falls_back_to_track_node_props(self, graph_lin_id):
        """When lin_id_prop is not in graph but geff_track_node_props has 'lineage',
        return the value from track_node_props and warn."""
        with pytest.warns(UserWarning, match="not present in the graph"):
            result = _identify_lin_id_prop(
                "missing_key",
                {"lineage": "track_id"},
                graph_lin_id,
            )
        assert result == "track_id"

    def test_provided_key_not_in_graph_falls_back_to_lineage_id(self, graph_lin_id):
        """When lin_id_prop is not in graph and geff_track_node_props is None,
        fall back to 'lineage_ID' if present in graph and warn."""
        with pytest.warns(UserWarning, match="not present in the graph"):
            result = _identify_lin_id_prop("missing_key", None, graph_lin_id)
        assert result == "lineage_ID"

    def test_provided_key_not_in_graph_no_fallback(self, graph_no_lin_id):
        """When lin_id_prop is not in graph, geff_track_node_props is None,
        and graph has no 'lineage_ID', warn twice and return None."""
        with pytest.warns(UserWarning):
            result = _identify_lin_id_prop("missing_key", None, graph_no_lin_id)
        assert result is None

    def test_none_prop_with_track_node_props_lineage(self, graph_lin_id):
        """When lin_id_prop is None and geff_track_node_props has 'lineage',
        return the value from track_node_props."""
        result = _identify_lin_id_prop(None, {"lineage": "my_lin_id"}, graph_lin_id)
        assert result == "my_lin_id"

    def test_none_prop_with_track_node_props_no_lineage_key(self, graph_lin_id):
        """When lin_id_prop is None and geff_track_node_props has no 'lineage' key,
        return None (dict.get default)."""
        result = _identify_lin_id_prop(None, {"tracklet": "tracklet_id"}, graph_lin_id)
        assert result is None

    def test_none_prop_no_track_node_props_graph_has_lineage_id(self, graph_lin_id):
        """When lin_id_prop is None, geff_track_node_props is None,
        and graph has 'lineage_ID', return 'lineage_ID'."""
        result = _identify_lin_id_prop(None, None, graph_lin_id)
        assert result == "lineage_ID"

    def test_none_prop_no_track_node_props_no_lineage_id_in_graph(self, graph_no_lin_id):
        """When lin_id_prop is None, geff_track_node_props is None,
        and graph has no 'lineage_ID', warn and return None."""
        with pytest.warns(UserWarning, match="No lineage identifier found"):
            result = _identify_lin_id_prop(None, None, graph_no_lin_id)
        assert result is None


class TestIdentifyTimeProp:
    """Test cases for _identify_time_prop function."""

    def test_provided_key_exists_in_graph(self, graph_lin_id):
        """When time_key is provided and exists in the graph, return it."""
        result = _identify_time_prop("frame", None, graph_lin_id)
        assert result == "frame"

    def test_provided_key_not_in_graph_falls_back_to_display_hints(
        self, graph_lin_id, geff_md_display_hints
    ):
        """When time_key is not in the graph but display hints have a valid time prop,
        warn twice and return the hint key."""
        with pytest.warns(UserWarning, match="not present in the graph"):
            with pytest.warns(UserWarning, match="inferred from display hints"):
                result = _identify_time_prop(
                    "missing_key", geff_md_display_hints, graph_lin_id
                )
        assert result == "frame"

    def test_provided_key_not_in_graph_falls_back_to_axes(
        self, graph_lin_id, geff_md_axes
    ):
        """When time_key is not in the graph, no display hints are available,
        and the axes have a matching time prop, warn twice and return the axis key."""
        with pytest.warns(UserWarning, match="not present in the graph"):
            with pytest.warns(UserWarning, match="inferred from axes"):
                result = _identify_time_prop("missing_key", geff_md_axes, graph_lin_id)
        assert result == "frame"

    def test_provided_key_not_in_graph_no_geff_md_raises(self, graph_lin_id):
        """When time_key is not in the graph and geff_md is None,
        warn and raise ValueError."""
        with pytest.warns(UserWarning, match="not present in the graph"):
            with pytest.raises(ValueError):
                _identify_time_prop("missing_key", None, graph_lin_id)

    def test_none_key_inferred_from_display_hints(
        self, graph_lin_id, geff_md_display_hints
    ):
        """When time_key is None and display hints have a valid time prop,
        warn and return the hint key."""
        with pytest.warns(UserWarning, match="inferred from display hints"):
            result = _identify_time_prop(None, geff_md_display_hints, graph_lin_id)
        assert result == "frame"

    def test_none_key_inferred_from_axes(self, graph_lin_id, geff_md_axes):
        """When time_key is None, no display hints are available, and the axes
        have a matching time prop, warn and return the axis key."""
        with pytest.warns(UserWarning, match="inferred from axes"):
            result = _identify_time_prop(None, geff_md_axes, graph_lin_id)
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
        """When provided keys exist in the graph, return them unchanged with no warning."""
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

    def test_provided_key_not_in_graph_warns_becomes_none(self, graph_with_coords):
        """When a provided key is absent from the graph, warn and set it to None."""
        with pytest.warns(UserWarning, match="not present in the graph"):
            result = _identify_space_props(
                "missing_x", None, None, None, graph_with_coords
            )
        assert result == (None, None, None)

    def test_all_none_no_geff_md_returns_none_tuple(self, graph_with_coords):
        """When all keys are None and geff_md is None, return (None, None, None) with no warning."""
        result = _identify_space_props(None, None, None, None, graph_with_coords)
        assert result == (None, None, None)

    def test_none_keys_inferred_from_display_hints(
        self, graph_with_coords, geff_md_display_hints
    ):
        """When keys are None and display hints have valid space props,
        infer x and y and warn for each."""
        with pytest.warns(UserWarning, match="inferred from display hints"):
            result = _identify_space_props(
                None, None, None, geff_md_display_hints, graph_with_coords
            )
        assert result == ("position_x", "position_y", None)

    def test_none_keys_inferred_from_axes(self, graph_with_coords, geff_md_axes):
        """When keys are None and axes have space props, infer x and y from axes and warn."""
        with pytest.warns(UserWarning, match="inferred from axes"):
            result = _identify_space_props(
                None, None, None, geff_md_axes, graph_with_coords
            )
        assert result == ("position_x", "position_y", None)

    def test_none_keys_all_three_inferred_from_axes(
        self, graph_with_3d_coords, geff_md_3d_axes
    ):
        """When all keys are None and 3D axes are present, infer x, y, and z from axes."""
        with pytest.warns(UserWarning, match="inferred from axes"):
            result = _identify_space_props(
                None, None, None, geff_md_3d_axes, graph_with_3d_coords
            )
        assert result == ("position_x", "position_y", "position_z")

    def test_provided_key_not_in_graph_falls_back_to_display_hints(
        self, graph_with_coords, geff_md_display_hints
    ):
        """When x key is absent from the graph, warn and infer it from display hints."""
        with pytest.warns(UserWarning, match="not present in the graph"):
            with pytest.warns(UserWarning, match="inferred from display hints"):
                result = _identify_space_props(
                    "missing_x", None, None, geff_md_display_hints, graph_with_coords
                )
        assert result == ("position_x", "position_y", None)

    def test_provided_key_not_in_graph_falls_back_to_axes(
        self, graph_with_coords, geff_md_axes
    ):
        """When x key is absent from the graph, warn and infer it from axes."""
        with pytest.warns(UserWarning, match="not present in the graph"):
            with pytest.warns(UserWarning, match="inferred from axes"):
                result = _identify_space_props(
                    "missing_x", None, None, geff_md_axes, graph_with_coords
                )
        assert result == ("position_x", "position_y", None)

    def test_display_hint_not_in_graph_silently_stays_none(
        self, graph_no_lin_id, geff_md_display_hints
    ):
        """When display hints point to props absent from the graph (and no axes),
        the slots stay None without any warning."""
        result = _identify_space_props(
            None, None, None, geff_md_display_hints, graph_no_lin_id
        )
        assert result == (None, None, None)


class TestResolvePropKey:
    """Test cases for _resolve_prop_key function."""

    def test_new_name_free(self):
        """When new_name is not taken, return it and warn."""
        with pytest.warns(
            UserWarning, match="'x' \\(node\\) has been renamed to 'cell_x'"
        ):
            result = _resolve_prop_key("cell_x", "fallback_x", {}, "x", "node")
        assert result == "cell_x"

    def test_fallback_free_returns_fallback(self, prop_position_x_edge):
        """When new_name is taken but fallback is free, return fallback."""
        props_dict = {"link_x": prop_position_x_edge}
        with pytest.warns(
            UserWarning,
            match="'x' \\(edge\\) has been renamed to 'fallback_x' \\('link_x'",
        ):
            result = _resolve_prop_key("link_x", "fallback_x", props_dict, "x", "edge")
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
            _resolve_prop_key("cell_x", "pycellin_cell_x", props_dict, "x", "node")


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
        _extract_props_metadata({}, props_dict, "node", rename_map)
        assert list(props_dict.keys()) == ["node_prop", "edge_prop"]
        assert rename_map == {"node": {}, "edge": {}, "lineage": {}}

    def test_new_key_is_all_fields_added(self, geff_node_props_md, rename_map):
        """A key not yet in props_dict is added with the given prop_type."""
        props_dict = {}
        _extract_props_metadata(geff_node_props_md, props_dict, "node", rename_map)
        assert "position_x" in props_dict
        assert props_dict["position_x"].identifier == "position_x"
        assert props_dict["position_x"].prop_type == PropertyType.NODE
        assert props_dict["position_x"].dtype == "float64"
        assert props_dict["position_x"].unit == "um"
        assert rename_map == {"node": {}, "edge": {}, "lineage": {}}

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
                {"frame": geff_node_props_md["frame"]}, props_dict, "node", rename_map
            )

    def test_node_collides_with_existing_edge_renames_both(
        self, geff_node_props_md, prop_position_x_edge, rename_map
    ):
        """When a node prop collides with an existing edge prop, both are renamed:
        the new node prop becomes 'cell_<key>' and the edge prop becomes 'link_<key>'."""
        props_dict = {"position_x": prop_position_x_edge}
        with pytest.warns(UserWarning):
            _extract_props_metadata(geff_node_props_md, props_dict, "node", rename_map)
        assert "position_x" not in props_dict
        assert "cell_position_x" in props_dict
        assert props_dict["cell_position_x"].identifier == "cell_position_x"
        assert props_dict["cell_position_x"].prop_type == PropertyType.NODE
        assert "link_position_x" in props_dict
        assert props_dict["link_position_x"].identifier == "link_position_x"
        assert props_dict["link_position_x"].prop_type == PropertyType.EDGE
        assert rename_map["node"] == {"position_x": "cell_position_x"}
        assert rename_map["edge"] == {"position_x": "link_position_x"}
        assert rename_map["lineage"] == {}

    def test_edge_collides_with_existing_node_renames_both(
        self, geff_node_props_md, prop_position_x_node, rename_map
    ):
        """When an edge key collides with an existing node prop, both are renamed:
        the new edge prop becomes 'link_<key>' and the node prop becomes 'cell_<key>'."""
        props_dict = {"position_x": prop_position_x_node}
        with pytest.warns(UserWarning):
            _extract_props_metadata(geff_node_props_md, props_dict, "edge", rename_map)
        assert "position_x" not in props_dict
        assert "link_position_x" in props_dict
        assert props_dict["link_position_x"].identifier == "link_position_x"
        assert props_dict["link_position_x"].prop_type == PropertyType.EDGE
        assert "cell_position_x" in props_dict
        assert props_dict["cell_position_x"].identifier == "cell_position_x"
        assert props_dict["cell_position_x"].prop_type == PropertyType.NODE
        assert rename_map["edge"] == {"position_x": "link_position_x"}
        assert rename_map["node"] == {"position_x": "cell_position_x"}
        assert rename_map["lineage"] == {}

    def test_node_collision_primary_new_key_taken_uses_fallback(
        self, geff_node_props_md, prop_position_x_edge, prop_cell_position_x, rename_map
    ):
        """When 'cell_<key>' is already in props_dict, the new node prop falls back
        to 'pycellin_cell_<key>'."""
        props_dict = {
            "position_x": prop_position_x_edge,
            "cell_position_x": prop_cell_position_x,  # primary rename taken
        }
        with pytest.warns(UserWarning):
            _extract_props_metadata(geff_node_props_md, props_dict, "node", rename_map)
        assert "position_x" not in props_dict
        assert "pycellin_cell_position_x" in props_dict
        assert props_dict["pycellin_cell_position_x"].prop_type == PropertyType.NODE
        assert "link_position_x" in props_dict
        assert props_dict["link_position_x"].prop_type == PropertyType.EDGE
        assert "cell_position_x" in props_dict  # original unaffected
        assert rename_map["node"] == {"position_x": "pycellin_cell_position_x"}
        assert rename_map["edge"] == {"position_x": "link_position_x"}
        assert rename_map["lineage"] == {}

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
            _extract_props_metadata(geff_node_props_md, props_dict, "node", rename_map)


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
        assert rename_map == {"node": {}, "edge": {}, "lineage": {}}

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
        self, prop_position_x_node, rename_map
    ):
        """When a lineage prop collides with an existing node prop, both are renamed:
        the new lineage prop becomes 'lin_<key>' and the node prop becomes 'cell_<key>'."""
        props_dict = {"position_x": prop_position_x_node}
        with pytest.warns(UserWarning):
            _extract_lin_props_metadata(
                {"position_x": {"dtype": "float"}}, props_dict, rename_map
            )
        assert "position_x" not in props_dict
        assert "lin_position_x" in props_dict
        assert props_dict["lin_position_x"].identifier == "lin_position_x"
        assert props_dict["lin_position_x"].prop_type == PropertyType.LINEAGE
        assert "cell_position_x" in props_dict
        assert props_dict["cell_position_x"].identifier == "cell_position_x"
        assert props_dict["cell_position_x"].prop_type == PropertyType.NODE
        assert rename_map["lineage"] == {"position_x": "lin_position_x"}
        assert rename_map["node"] == {"position_x": "cell_position_x"}
        assert rename_map["edge"] == {}

    def test_lineage_collides_with_existing_edge_renames_both(
        self, prop_position_x_edge, rename_map
    ):
        """When a lineage prop collides with an existing edge prop, both are renamed:
        the new lineage prop becomes 'lin_<key>' and the edge prop becomes 'link_<key>'."""
        props_dict = {"position_x": prop_position_x_edge}
        with pytest.warns(UserWarning):
            _extract_lin_props_metadata(
                {"position_x": {"dtype": "float"}}, props_dict, rename_map
            )
        assert "position_x" not in props_dict
        assert "lin_position_x" in props_dict
        assert props_dict["lin_position_x"].identifier == "lin_position_x"
        assert props_dict["lin_position_x"].prop_type == PropertyType.LINEAGE
        assert "link_position_x" in props_dict
        assert props_dict["link_position_x"].identifier == "link_position_x"
        assert props_dict["link_position_x"].prop_type == PropertyType.EDGE
        assert rename_map["lineage"] == {"position_x": "lin_position_x"}
        assert rename_map["edge"] == {"position_x": "link_position_x"}
        assert rename_map["node"] == {}

    def test_lineage_collision_primary_new_key_taken_uses_fallback(
        self, prop_position_x_node, prop_lin_position_x, rename_map
    ):
        """When 'lin_<key>' is already in props_dict, the new lineage prop falls back
        to 'pycellin_lin_<key>'."""
        props_dict = {
            "position_x": prop_position_x_node,
            "lin_position_x": prop_lin_position_x,  # primary rename taken
        }
        with pytest.warns(UserWarning):
            _extract_lin_props_metadata(
                {"position_x": {"dtype": "float"}}, props_dict, rename_map
            )
        assert "position_x" not in props_dict
        assert "pycellin_lin_position_x" in props_dict
        assert props_dict["pycellin_lin_position_x"].prop_type == PropertyType.LINEAGE
        assert "cell_position_x" in props_dict
        assert props_dict["cell_position_x"].prop_type == PropertyType.NODE
        assert "lin_position_x" in props_dict  # original unaffected
        assert rename_map["lineage"] == {"position_x": "pycellin_lin_position_x"}
        assert rename_map["node"] == {"position_x": "cell_position_x"}
        assert rename_map["edge"] == {}

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
        assert rename_map == {"node": {}, "edge": {}, "lineage": {}}

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
        assert rename_map == {"node": {}, "edge": {}, "lineage": {}}

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
        assert rename_map == {"node": {}, "edge": {}, "lineage": {}}

    def test_node_and_edge_collision_both_renamed(self, geff_node_props_md, rename_map):
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
        with pytest.warns(UserWarning):
            result = _build_props_metadata(geff_md, rename_map)
        assert "position_x" not in result
        assert "cell_position_x" in result
        assert result["cell_position_x"].prop_type == PropertyType.NODE
        assert "link_position_x" in result
        assert result["link_position_x"].prop_type == PropertyType.EDGE
        assert rename_map["node"] == {"position_x": "cell_position_x"}
        assert rename_map["edge"] == {"position_x": "link_position_x"}
        assert rename_map["lineage"] == {}

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
        assert rename_map == {"node": {}, "edge": {}, "lineage": {}}

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
        assert rename_map == {"node": {}, "edge": {}, "lineage": {}}


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

    def test_no_time_unit_warns_and_absent_from_result(self, geff_axes):
        """When no unit is found for the time property, warn and omit time_unit."""
        geff_md = self._make_geff_md(axes=geff_axes)
        with pytest.warns(UserWarning, match="No unit found for time property"):
            result = _extract_axes_metadata(
                geff_md, "unknown_time", "position_x", None, None
            )
        assert "time_unit" not in result
        assert result["space_unit"] == "um"

    def test_all_space_props_none_warns(self, geff_axes):
        """When all space props are None, warn and omit space_unit."""
        geff_md = self._make_geff_md(axes=geff_axes)
        with pytest.warns(UserWarning, match="No coordinate properties found"):
            result = _extract_axes_metadata(geff_md, "frame", None, None, None)
        assert result["time_unit"] == "second"
        assert "space_unit" not in result

    def test_no_space_unit_found_warns(self, geff_axes):
        """When space props are provided but no unit found, warn and omit space_unit."""
        geff_md = self._make_geff_md(axes=geff_axes)
        with pytest.warns(UserWarning, match="No unit found for space properties"):
            result = _extract_axes_metadata(geff_md, "frame", "unknown_x", None, None)
        assert "space_unit" not in result

    def test_multiple_space_units_warns(self):
        """When x and y props have different units, warn and omit space_unit."""
        mixed_axes = [
            geff_spec.Axis(name="frame", type="time", unit="second"),
            geff_spec.Axis(name="position_x", type="space", unit="um"),
            geff_spec.Axis(name="position_y", type="space", unit="millimeter"),
        ]
        geff_md = self._make_geff_md(axes=mixed_axes)
        with pytest.warns(UserWarning, match="Multiple space units found"):
            result = _extract_axes_metadata(
                geff_md, "frame", "position_x", "position_y", None
            )
        assert "space_unit" not in result

    def test_partial_space_props_single_unit(self, geff_axes):
        """When only x_prop is provided and has a unit, space_unit is set."""
        geff_md = self._make_geff_md(axes=geff_axes)
        result = _extract_axes_metadata(geff_md, "frame", "position_x", None, None)
        assert result["space_unit"] == "um"

    def test_space_unit_from_node_props_md(self, geff_node_props_md):
        """When unit comes from node_props_md (no axes), space_unit is set correctly."""
        geff_md = self._make_geff_md(axes=None, node_props_md=geff_node_props_md)
        with pytest.warns(UserWarning, match="No unit found for time property"):
            result = _extract_axes_metadata(geff_md, "frame", "position_x", None, None)
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

    def test_missing_units_produce_warnings_and_absent_from_result(self):
        """When no units are found, appropriate warnings are raised and
        time_unit / space_unit are absent from the result."""
        geff_md_no_units = geff.GeffMetadata(
            directed=True,
            axes=[],
            node_props_metadata={},
            edge_props_metadata={},
        )
        with pytest.warns(UserWarning, match="No unit found for time property"):
            with pytest.warns(UserWarning, match="No unit found for space properties"):
                result = _build_generic_metadata(
                    "/some/tracks.geff",
                    geff_md_no_units,
                    "frame",
                    "position_x",
                    None,
                    None,
                )
        assert "time_unit" not in result
        assert "space_unit" not in result


class TestFallbackToNodeKeys:
    """Test cases for _fallback_to_node_keys function."""

    def test_sets_cell_id_from_node_keys(self, graph_no_lin_id):
        """When falling back, each node gets a cell_ID equal to its node key."""
        with pytest.warns(UserWarning, match="fallback"):
            _fallback_to_node_keys(graph_no_lin_id, "fallback reason")
        assert graph_no_lin_id.nodes[0]["cell_ID"] == 0
        assert graph_no_lin_id.nodes[1]["cell_ID"] == 1
        assert graph_no_lin_id.nodes[0]["frame"] == 0
        assert graph_no_lin_id.nodes[1]["frame"] == 1


class TestEnsureValidCellID:
    """Test cases for _ensure_valid_cell_ID function."""

    def test_none_key_falls_back_to_node_keys(self, graph_no_lin_id):
        """When cell_id_key is None, create cell_ID from node keys and warn."""
        with pytest.warns(UserWarning, match="No cell identifier property provided"):
            result = _ensure_valid_cell_ID(graph_no_lin_id, None)
        assert result == "cell_ID"
        assert graph_no_lin_id.nodes[0]["cell_ID"] == 0
        assert graph_no_lin_id.nodes[1]["cell_ID"] == 1
        assert graph_no_lin_id.nodes[0]["frame"] == 0
        assert graph_no_lin_id.nodes[1]["frame"] == 1

    def test_missing_prop_falls_back(self):
        """When cell_id_key is missing on some nodes, fall back and warn."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1)
        with pytest.warns(UserWarning, match="not present on all nodes"):
            result = _ensure_valid_cell_ID(g, "id")
        assert result == "cell_ID"
        assert g.nodes[0]["cell_ID"] == 0
        assert g.nodes[1]["cell_ID"] == 1

    def test_negative_value_fall_back(self):
        """When cell_id_key has a negative value, fall back and warn."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1, id=-1)
        with pytest.warns(UserWarning, match="not all positive integers"):
            result = _ensure_valid_cell_ID(g, "id")
        assert result == "cell_ID"
        assert g.nodes[0]["cell_ID"] == 0
        assert g.nodes[1]["cell_ID"] == 1

    def test_string_value_fall_back(self):
        """When cell_id_key has a string value, fall back and warn."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1, id="1")
        with pytest.warns(UserWarning, match="not all positive integers"):
            result = _ensure_valid_cell_ID(g, "id")
        assert result == "cell_ID"
        assert g.nodes[0]["cell_ID"] == 0
        assert g.nodes[1]["cell_ID"] == 1

    def test_bool_value_fall_back(self):
        """When cell_id_key has a boolean value, fall back and warn."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1, id=True)
        with pytest.warns(UserWarning, match="not all positive integers"):
            result = _ensure_valid_cell_ID(g, "id")
        assert result == "cell_ID"
        assert g.nodes[0]["cell_ID"] == 0
        assert g.nodes[1]["cell_ID"] == 1

    def test_none_value_fall_back(self):
        """When cell_id_key has a None value, fall back and warn."""
        g = nx.Graph()
        g.add_node(0, id=0)
        g.add_node(1, id=None)
        with pytest.warns(UserWarning, match="not all positive integers"):
            result = _ensure_valid_cell_ID(g, "id")
        assert result == "cell_ID"
        assert g.nodes[0]["cell_ID"] == 0
        assert g.nodes[1]["cell_ID"] == 1

    def test_duplicate_prop_values_fall_back(self):
        """When cell_id_key has duplicate values, fall back and warn."""
        g = nx.Graph()
        g.add_node(0, id=1)
        g.add_node(1, id=1)
        with pytest.warns(UserWarning, match="Duplicate values found"):
            result = _ensure_valid_cell_ID(g, "id")
        assert result == "cell_ID"
        assert g.nodes[0]["cell_ID"] == 0
        assert g.nodes[1]["cell_ID"] == 1

    def test_valid_prop_relabels_nodes(self):
        """When cell_id_key is valid, relabel nodes to match property values."""
        g = nx.Graph()
        g.add_node(1, id=10)
        g.add_node(2, id=11)
        result = _ensure_valid_cell_ID(g, "id")
        assert result == "id"
        assert set(g.nodes) == {10, 11}
        assert g.nodes[10]["id"] == 10
        assert g.nodes[11]["id"] == 11
        assert "cell_ID" not in g.nodes[10]
        assert "cell_ID" not in g.nodes[11]

    def test_empty_graph(self):
        """When graph is empty, return the cell_id_key without modification."""
        g = nx.Graph()

        result = _ensure_valid_cell_ID(g, "id")
        assert result == "id"
        assert len(g.nodes) == 0

        result = _ensure_valid_cell_ID(g, None)
        assert result == "cell_ID"
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
            assert "lineage_ID" in data
            assert "cell_ID" in data
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
            assert "lineage_ID" in data
            assert "cell_ID" in data
            assert "cell_x" in data
            assert "cell_y" in data
            assert "cell_z" in data
            assert "new_node_key" in data

        # Edge-level updates.
        assert "old_edge_key" not in lin_a.edges[(0, 1)]
        assert lin_a.edges[(0, 1)]["new_edge_key"] == 0.5

        # Lineage-level updates.
        assert lin_a.graph["lineage_ID"] == 11
        assert lin_b.graph["lineage_ID"] == 12
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
            rename_map={"node": {}, "edge": {}, "lineage": {}},
        )

        lin_a, _ = lineages_with_nonstandard_keys
        assert lin_a.nodes[0]["cell_ID"] == 100
        assert lin_a.nodes[0]["lineage_ID"] == 11
        assert "pos_x" in lin_a.nodes[0]
        assert "pos_y" in lin_a.nodes[0]
        assert "pos_z" in lin_a.nodes[0]
        assert "cell_x" not in lin_a.nodes[0]
        assert "cell_y" not in lin_a.nodes[0]
        assert "cell_z" not in lin_a.nodes[0]

    def test_keeps_graph_lin_id_when_already_standard(self, standardize_rename_map):
        """When lin_id_key is already 'lineage_ID', lineage graph IDs are preserved."""
        lin = CellLineage()
        lin.add_node(
            1,
            lineage_ID=0,
            custom_cell_id=11,
            pos_x=2.0,
            old_node_key="node",
        )
        lin.graph["lineage_ID"] = 0
        lin.graph["old_lin_key"] = "lineage"

        _standardize_properties_data(
            [lin],
            lin_id_key="lineage_ID",
            cell_id_key="custom_cell_id",
            cell_x_key="pos_x",
            cell_y_key=None,
            cell_z_key=None,
            rename_map=standardize_rename_map,
        )

        assert lin.graph["lineage_ID"] == 0
        assert lin.nodes[1]["lineage_ID"] == 0

    def test_skips_standard_cell_id_rename(self):
        """When cell_id_key is already 'cell_ID', node cell IDs are preserved."""
        lin = CellLineage()
        lin.add_node(1, lineage_ID=0, cell_ID=11)
        lin.graph["lineage_ID"] = 0

        _standardize_properties_data(
            [lin],
            lin_id_key="lineage_ID",
            cell_id_key="cell_ID",
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            rename_map={"node": {}, "edge": {}, "lineage": {}},
        )

        assert lin.nodes[1]["cell_ID"] == 11

    def test_skips_standard_coordinate_renames(self):
        """When x/y/z keys are already 'cell_x', 'cell_y', 'cell_z', they are left unchanged."""
        lin = CellLineage()
        lin.add_node(1, lineage_ID=0, cell_ID=11, cell_x=1.0, cell_y=2.0, cell_z=3.0)
        lin.graph["lineage_ID"] = 0

        _standardize_properties_data(
            [lin],
            lin_id_key="lineage_ID",
            cell_id_key="cell_ID",
            cell_x_key="cell_x",
            cell_y_key="cell_y",
            cell_z_key="cell_z",
            rename_map={"node": {}, "edge": {}, "lineage": {}},
        )

        assert lin.nodes[1]["cell_x"] == 1.0
        assert lin.nodes[1]["cell_y"] == 2.0
        assert lin.nodes[1]["cell_z"] == 3.0

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
            rename_map={"node": {}, "edge": {}, "lineage": {}},
        )

        assert lin.graph["lineage_ID"] == -1

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
            rename_map={"node": {}, "edge": {}, "lineage": {}},
        )

        assert lin_with_id.graph["lineage_ID"] == 10
        assert lin_without_id.graph["lineage_ID"] == 11


class TestStandardizePropsMetadata:
    """Test cases for _standardize_props_metadata function."""

    def test_lin_id_standard_key_preserved(self, pycellin_standard_md, rename_map):
        """When lineage_id_key is already 'lineage_ID', key and metadata are preserved."""
        nb_props = len(pycellin_standard_md)
        _standardize_props_metadata(
            pycellin_standard_md,
            lin_id_key="lineage_ID",
            cell_id_key=None,
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert len(pycellin_standard_md) == nb_props
        assert "lineage_ID" in pycellin_standard_md
        assert pycellin_standard_md["lineage_ID"].identifier == "lineage_ID"
        assert pycellin_standard_md["lineage_ID"].provenance == "test"

    def test_lin_id_nonstandard_renamed(self, pycellin_non_standard_md, rename_map):
        """When lineage_id_key is present but not 'lineage_ID', it is renamed to 'lineage_ID',
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
        assert "lineage_ID" in pycellin_non_standard_md
        assert pycellin_non_standard_md["lineage_ID"].identifier == "lineage_ID"
        assert pycellin_non_standard_md["lineage_ID"].provenance == "test"

    def test_lin_id_absent_creates_default(self, rename_map):
        """When lineage_id_key is None, a default 'lineage_ID' property with provenance
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
        assert "lineage_ID" in props_md
        assert props_md["lineage_ID"].identifier == "lineage_ID"
        assert props_md["lineage_ID"].provenance == "geff"

    def test_cell_id_standard_key_preserved(self, pycellin_standard_md, rename_map):
        """When cell_id_key is already 'cell_ID', key and metadata are preserved."""
        nb_props = len(pycellin_standard_md)
        _standardize_props_metadata(
            pycellin_standard_md,
            lin_id_key=None,
            cell_id_key="cell_ID",
            cell_x_key=None,
            cell_y_key=None,
            cell_z_key=None,
            space_unit=None,
            rename_map=rename_map,
        )
        assert len(pycellin_standard_md) == nb_props
        assert "cell_ID" in pycellin_standard_md
        assert pycellin_standard_md["cell_ID"].identifier == "cell_ID"
        assert pycellin_standard_md["cell_ID"].provenance == "test"

    def test_cell_id_nonstandard_renamed(self, pycellin_non_standard_md, rename_map):
        """When cell_id_key is present but not 'cell_ID', it is renamed to 'cell_ID',
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
        assert "cell_ID" in pycellin_non_standard_md
        assert pycellin_non_standard_md["cell_ID"].identifier == "cell_ID"
        assert pycellin_non_standard_md["cell_ID"].provenance == "test"

    def test_cell_id_absent_creates_default(self, rename_map):
        """When cell_id_key is None, a default 'cell_ID' property with provenance
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
        assert "cell_ID" in props_md
        assert props_md["cell_ID"].identifier == "cell_ID"
        assert props_md["cell_ID"].provenance == "geff"

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
        assert "lineage_ID" in props_md
        assert props_md["lineage_ID"].identifier == "lineage_ID"
        assert props_md["lineage_ID"].provenance == "geff"

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
        assert "cell_ID" in props_md
        assert props_md["cell_ID"].identifier == "cell_ID"
        assert props_md["cell_ID"].provenance == "geff"

    def test_coord_with_rename_map_transformation(self, prop_position_x_node, rename_map):
        """When a coordinate key is transformed by rename_map, the transformed key
        is looked up in props_md, renamed to pycellin convention, and identifier updated."""
        props_md = {"old_pos_x": prop_position_x_node}
        rename_map["node"]["old_pos_x"] = "position_x"
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
