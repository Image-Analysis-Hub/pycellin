"""Unit test for GEFF file loader."""

import geff
import geff_spec
import networkx as nx
import pytest

from pycellin.io.geff.loader import _identify_lin_id_prop

# Fixtures ####################################################################


@pytest.fixture
def graph_lin_id():
    """Graph with standard and custom lineage ID properties."""
    graph = nx.Graph()
    graph.add_node(0, frame=0, lineage_ID=0, my_lin_id=0)
    graph.add_node(1, frame=1, lineage_ID=1, my_lin_id=1)
    return graph


@pytest.fixture
def graph_no_lin_id():
    """Graph with nolineage ID property."""
    graph = nx.Graph()
    graph.add_node(0, frame=0)
    graph.add_node(1, frame=1)
    return graph


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

    pass


class TestIdentifySpaceProps:
    """Test cases for _identify_space_props function."""

    pass