"""Unit test for IO utilities functions."""

import networkx as nx
import pytest

from pycellin.classes import CellLineage, Data, Model, Property, PropsMetadata
from pycellin.graph.properties.core import (
    create_cell_coord_property,
    create_lineage_id_property,
    create_link_coord_property,
    create_timepoint_property,
)
from pycellin.io.utils import (
    _add_lineage_props,
    _get_props_from_data,
    _graph_has_node_prop,
    _remove_orphaned_metadata,
    _split_graph_into_lineages,
    _update_lineage_prop_key,
    _update_lineages_IDs_key,
    _update_node_prop_key,
)
from pycellin.utils import is_equal

# Fixtures ####################################################################


@pytest.fixture
def graph():
    g = nx.DiGraph()
    g.add_node(1, all_val=0, one_none_val=None, all_none_val=None, missing_val="a")
    g.add_node(2, all_val=1, one_none_val=15.0, all_none_val=None, missing_val="b")
    g.add_node(3, all_val=2, one_none_val=20.0, all_none_val=None)
    return g


@pytest.fixture
def lin_with_old_key():
    """Lineage with nodes that all have old_key property."""
    lin = CellLineage()
    lin.add_node(1, old_key="value1")
    lin.add_node(2, old_key="value2")
    lin.add_node(3, old_key="value3")
    return lin


@pytest.fixture
def lin_with_mixed_keys():
    """Lineage with some nodes having old_key and some without."""
    lin = CellLineage()
    lin.add_node(1, old_key="value1")
    lin.add_node(2)  # No old_key
    lin.add_node(3, old_key="value3")
    return lin


@pytest.fixture
def two_lin_graph():
    """Standard 2-lineage graph: [1-2] and [3-4] with lineage_ID."""
    g = nx.DiGraph()
    g.add_node(1, lineage_ID=0)
    g.add_node(2, lineage_ID=0)
    g.add_edge(1, 2)
    g.add_node(3, lineage_ID=1)
    g.add_node(4, lineage_ID=1)
    g.add_edge(3, 4)
    return g


@pytest.fixture
def expected_two_lins():
    """Expected CellLineages resulting from splitting two_lineage_graph."""
    lin0 = CellLineage()
    lin0.add_node(1, lineage_ID=0)
    lin0.add_node(2, lineage_ID=0)
    lin0.add_edge(1, 2)
    lin0.graph["lineage_ID"] = 0

    lin1 = CellLineage()
    lin1.add_node(3, lineage_ID=1)
    lin1.add_node(4, lineage_ID=1)
    lin1.add_edge(3, 4)
    lin1.graph["lineage_ID"] = 1

    return [lin0, lin1]


@pytest.fixture
def two_lin_graph_with_track_id():
    """Standard 2-lineage graph using TRACK_ID key instead of lineage_ID."""
    g = nx.DiGraph()
    g.add_node(1, TRACK_ID=0)
    g.add_node(2, TRACK_ID=0)
    g.add_edge(1, 2)
    g.add_node(3, TRACK_ID=1)
    g.add_node(4, TRACK_ID=1)
    g.add_edge(3, 4)
    return g


@pytest.fixture
def expected_two_lins_with_track_id():
    """Expected CellLineages resulting from splitting two_lineage_graph_with_track_id."""
    lin0 = CellLineage()
    lin0.add_node(1, TRACK_ID=0)
    lin0.add_node(2, TRACK_ID=0)
    lin0.add_edge(1, 2)
    lin0.graph["TRACK_ID"] = 0

    lin1 = CellLineage()
    lin1.add_node(3, TRACK_ID=1)
    lin1.add_node(4, TRACK_ID=1)
    lin1.add_edge(3, 4)
    lin1.graph["TRACK_ID"] = 1

    return [lin0, lin1]


@pytest.fixture
def graph_with_props():
    """2-lineage graph with various node and edge properties including falsy values."""
    g = nx.DiGraph()
    # Lineage 0: nodes with various property types
    g.add_node(1, lineage_ID=0, custom_prop="value1", x=10.5, count=0, flag=False)
    g.add_node(2, lineage_ID=0, custom_prop="value2", x=20.5, count=5, flag=True)
    g.add_edge(
        1, 2, weight=1.5, edge_data="test", empty_str="", empty_list=[], none_val=None
    )
    # Lineage 1: nodes with different properties
    g.add_node(3, lineage_ID=1, custom_prop="value3", x=30.5, count=0)
    g.add_node(4, lineage_ID=1, custom_prop="value4", x=40.5, count=10)
    g.add_edge(3, 4, weight=2.5, edge_data="other")
    return g


@pytest.fixture
def expected_props_lins():
    """Expected CellLineages resulting from splitting graph_with_properties."""
    lin0_exp = CellLineage()
    lin0_exp.add_node(1, lineage_ID=0, custom_prop="value1", x=10.5, count=0, flag=False)
    lin0_exp.add_node(2, lineage_ID=0, custom_prop="value2", x=20.5, count=5, flag=True)
    lin0_exp.add_edge(
        1, 2, weight=1.5, edge_data="test", empty_str="", empty_list=[], none_val=None
    )
    lin0_exp.graph["lineage_ID"] = 0

    lin1_exp = CellLineage()
    lin1_exp.add_node(3, lineage_ID=1, custom_prop="value3", x=30.5, count=0)
    lin1_exp.add_node(4, lineage_ID=1, custom_prop="value4", x=40.5, count=10)
    lin1_exp.add_edge(3, 4, weight=2.5, edge_data="other")
    lin1_exp.graph["lineage_ID"] = 1

    return [lin0_exp, lin1_exp]


@pytest.fixture
def lin_props():
    """Common lineage property dictionaries for testing."""
    return [
        {"name": "blob", "lineage_ID": 0},
        {"name": "blub", "lineage_ID": 1},
    ]


@pytest.fixture
def lin_props_with_track_id():
    """Lineage property dictionaries using TRACK_ID."""
    return [
        {"name": "blob", "TRACK_ID": 0},
        {"name": "blub", "TRACK_ID": 1},
    ]


@pytest.fixture
def model():
    """Model with metadata."""
    lin1 = CellLineage()
    lin1.add_node(1, timepoint=0, cell_x=10.0, lineage_ID=0)
    lin1.add_node(2, timepoint=1, cell_x=12.0, lineage_ID=0)
    lin1.add_edge(1, 2, link_x=2.0)
    lin1.graph["lineage_ID"] = 0

    lin2 = CellLineage()
    lin2.add_node(3, timepoint=0, cell_x=20.0, lineage_ID=1)
    lin2.add_node(4, timepoint=1, cell_x=22.0, lineage_ID=1)
    lin2.add_edge(3, 4, link_x=2.0)
    lin2.graph["lineage_ID"] = 1

    cell_data = {0: lin1, 1: lin2}
    data = Data(cell_data)
    props_metadata = PropsMetadata()
    props_metadata._add_prop(create_timepoint_property(provenance="Test"))
    props_metadata._add_prop(
        create_cell_coord_property(provenance="Test", axis="x", unit="µm")
    )
    props_metadata._add_prop(
        create_link_coord_property(provenance="Test", axis="x", unit="µm")
    )
    props_metadata._add_prop(create_lineage_id_property(provenance="Test"))

    model = Model(
        data=data,
        props_metadata=props_metadata,
        reference_time_property="timepoint",
    )
    return model


@pytest.fixture
def model_with_orphaned_metadata(model):
    """Model with some metadata properties that have no corresponding data."""
    model.props_metadata._add_prop(
        Property(
            identifier="orphaned_node_prop",
            name="Orphaned node property",
            description="This doesn't exist in data",
            provenance="Test",
            prop_type="node",
            lin_type="Lineage",
            dtype="string",
        )
    )
    model.props_metadata._add_prop(
        Property(
            identifier="orphaned_edge_prop",
            name="Orphaned edge property",
            description="This doesn't exist in data",
            provenance="Test",
            prop_type="edge",
            lin_type="Lineage",
            dtype="string",
        )
    )
    model.props_metadata._add_prop(
        Property(
            identifier="orphaned_lineage_prop",
            name="Orphaned lineage property",
            description="This doesn't exist in data",
            provenance="Test",
            prop_type="lineage",
            lin_type="Lineage",
            dtype="string",
        )
    )
    return model


@pytest.fixture
def model_with_orphaned_data(model):
    """Model with some data properties that have no corresponding metadata."""
    model.data.cell_data[0].nodes[1]["node_prop_no_metadata"] = "value"
    model.data.cell_data[0].edges[1, 2]["edge_prop_no_metadata"] = 100
    model.data.cell_data[0].graph["lineage_prop_no_metadata"] = False
    return model


@pytest.fixture
def model_with_lineage_id_config():
    """Factory fixture for creating models with flexible lineage_ID property configurations.

    Returns a callable that creates a model with specified lineage_ID properties.
    Parameters control whether lineage_ID exists in node or graph properties.
    """

    def _create_model(
        lin1_node_lin_id=True,
        lin1_graph_lin_id=True,
        lin2_node_lin_id=True,
        lin2_graph_lin_id=True,
    ):
        lin1 = CellLineage()
        lin1.add_node(1, timepoint=0, cell_x=10.0)
        if lin1_node_lin_id:
            lin1.nodes[1]["lineage_ID"] = 0
        lin1.add_node(2, timepoint=1, cell_x=12.0)
        if lin1_node_lin_id:
            lin1.nodes[2]["lineage_ID"] = 0
        lin1.add_edge(1, 2, link_x=2.0)
        if lin1_graph_lin_id:
            lin1.graph["lineage_ID"] = 0

        lin2 = CellLineage()
        lin2.add_node(3, timepoint=0, cell_x=20.0)
        if lin2_node_lin_id:
            lin2.nodes[3]["lineage_ID"] = 1
        lin2.add_node(4, timepoint=1, cell_x=22.0)
        if lin2_node_lin_id:
            lin2.nodes[4]["lineage_ID"] = 1
        lin2.add_edge(3, 4, link_x=2.0)
        if lin2_graph_lin_id:
            lin2.graph["lineage_ID"] = 1

        cell_data = {0: lin1, 1: lin2}
        data = Data(cell_data)
        props_metadata = PropsMetadata()
        props_metadata._add_prop(create_timepoint_property(provenance="Test"))
        props_metadata._add_prop(
            create_cell_coord_property(provenance="Test", axis="x", unit="µm")
        )
        props_metadata._add_prop(
            create_link_coord_property(provenance="Test", axis="x", unit="µm")
        )
        props_metadata._add_prop(create_lineage_id_property(provenance="Test"))

        return Model(
            data=data,
            props_metadata=props_metadata,
            reference_time_property="timepoint",
        )

    return _create_model


# Test classes ###############################################################


class TestAddLineagesProps:
    """Test cases for _add_lineage_props function."""

    def test_add_lins_props(self, lin_props):
        """Test adding lineage properties to graphs."""
        g1_attr, g2_attr = lin_props

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1, lineage_ID=0)
        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr])

        g1_exp = nx.DiGraph()
        g1_exp.graph["name"] = "blob"
        g1_exp.graph["lineage_ID"] = 0
        g1_exp.add_node(1, lineage_ID=0)
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["lineage_ID"] = 1
        g2_exp.add_node(2, lineage_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)

    def test_different_lin_ID_key(self, lin_props_with_track_id):
        """Test adding lineage properties with different lineage ID key."""
        g1_attr, g2_attr = lin_props_with_track_id

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1, TRACK_ID=0)
        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, TRACK_ID=1)
        _add_lineage_props(
            [g1_obt, g2_obt], [g1_attr, g2_attr], lineage_ID_key="TRACK_ID"
        )

        g1_exp = nx.DiGraph()
        g1_exp.graph["name"] = "blob"
        g1_exp.graph["TRACK_ID"] = 0
        g1_exp.add_node(1, TRACK_ID=0)
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["TRACK_ID"] = 1
        g2_exp.add_node(2, TRACK_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)

    def test_no_lin_ID_on_all_nodes(self, lin_props):
        """Test adding lineage properties when no nodes have lineage ID."""
        g1_attr, g2_attr = lin_props

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1)
        g1_obt.add_node(3)
        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        _add_lineage_props(
            [g1_obt, g2_obt], [g1_attr, g2_attr], lineage_ID_key="lineage_ID"
        )

        g1_exp = nx.DiGraph()
        g1_exp.add_node(1)
        g1_exp.add_node(3)
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["lineage_ID"] = 1
        g2_exp.add_node(2, lineage_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)

    def test_no_lin_ID_on_one_node(self, lin_props):
        """Test adding lineage properties when some nodes lack lineage ID."""
        g1_attr, g2_attr = lin_props

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1)
        g1_obt.add_node(3)
        g1_obt.add_node(4, lineage_ID=0)

        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr])

        g1_exp = nx.DiGraph()
        g1_exp.graph["name"] = "blob"
        g1_exp.graph["lineage_ID"] = 0
        g1_exp.add_node(1)
        g1_exp.add_node(3)
        g1_exp.add_node(4, lineage_ID=0)
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["lineage_ID"] = 1
        g2_exp.add_node(2, lineage_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)

    def test_different_ID_for_one_track(self, lin_props):
        """Test that different lineage IDs within one graph raises error."""
        g1_attr, g2_attr = lin_props

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1, lineage_ID=0)
        g1_obt.add_node(3, lineage_ID=2)
        g1_obt.add_node(4, lineage_ID=0)

        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        with pytest.raises(ValueError):
            _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr])

    def test_no_nodes(self, lin_props):
        """Test adding lineage properties to graph with no nodes."""
        g1_attr, g2_attr = lin_props

        g1_obt = nx.DiGraph()
        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr])

        g1_exp = nx.DiGraph()
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["lineage_ID"] = 1
        g2_exp.add_node(2, lineage_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)

    def test_no_matching_lin_ID(self, lin_props):
        """Test that an unmatched lineage ID issues a warning and skips."""
        g1_attr, g2_attr = lin_props

        # Node has lineage_ID=99, which is not present in lin_props (0 and 1).
        g1_obt = nx.DiGraph()
        g1_obt.add_node(1, lineage_ID=99)
        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)

        with pytest.warns(UserWarning, match="No lineage properties found"):
            _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr])

        # g1_obt should not have graph-level properties added (skipped with warning)
        assert len(g1_obt.graph) == 0
        # g2_obt should have properties added normally
        assert g2_obt.graph["name"] == "blub"
        assert g2_obt.graph["lineage_ID"] == 1


class TestGetPropsFromData:
    """Test cases for _get_props_from_data function."""

    def test_get_props_from_data(self, model):
        """Test extracting properties from model data."""
        node_props, edge_props, lineage_props = _get_props_from_data(model)

        assert "timepoint" in node_props
        assert "cell_x" in node_props
        assert "lineage_ID" in node_props
        assert len(node_props) == 3

        assert "link_x" in edge_props
        assert len(edge_props) == 1

        assert "lineage_ID" in lineage_props
        assert len(lineage_props) == 1

    def test_get_props_from_empty_data(self):
        """Test with empty data."""
        data = Data({})
        model = Model(data=data, reference_time_property="timepoint")

        node_props, edge_props, lineage_props = _get_props_from_data(model)

        assert len(node_props) == 0
        assert len(edge_props) == 0
        assert len(lineage_props) == 0


class TestGraphHasNodeProp:
    """Test cases for _graph_has_node_prop function."""

    def test_empty_graph_returns_true(self):
        """Vacuously true: all (zero) nodes have the property."""
        assert _graph_has_node_prop(nx.DiGraph(), "frame") is True

    def test_all_nodes_have_prop(self, graph):
        assert _graph_has_node_prop(graph, "all_val") is True

    def test_some_nodes_missing_prop(self, graph):
        assert _graph_has_node_prop(graph, "missing_val") is False

    def test_nonexistent_key(self, graph):
        assert _graph_has_node_prop(graph, "value") is False

    def test_prop_with_none_value(self, graph):
        """Key presence is checked, not value truthiness."""
        assert _graph_has_node_prop(graph, "one_none_val") is True

    def test_prop_with_only_none_value(self, graph):
        """Key presence is checked, not value truthiness."""
        assert _graph_has_node_prop(graph, "all_none_val") is True


class TestRemoveOrphanedMetadata:
    """Test cases for _remove_orphaned_metadata function."""

    def test_no_orphaned_metadata(self, model):
        """Test when there are no orphaned properties."""
        before_node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
        before_edge_props = model.props_metadata._get_prop_dict_from_prop_type("edge")
        before_lineage_props = model.props_metadata._get_prop_dict_from_prop_type(
            "lineage"
        )
        _remove_orphaned_metadata(model)
        after_node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
        after_edge_props = model.props_metadata._get_prop_dict_from_prop_type("edge")
        after_lineage_props = model.props_metadata._get_prop_dict_from_prop_type(
            "lineage"
        )

        assert before_node_props == after_node_props
        assert before_edge_props == after_edge_props
        assert before_lineage_props == after_lineage_props

    def test_remove_orphaned_metadata(self, model_with_orphaned_metadata):
        """Test removing orphaned properties from metadata."""
        with pytest.warns(UserWarning, match="Node metadata with no corresponding data"):
            with pytest.warns(
                UserWarning, match="Edge metadata with no corresponding data"
            ):
                with pytest.warns(
                    UserWarning, match="Lineage metadata with no corresponding data"
                ):
                    _remove_orphaned_metadata(model_with_orphaned_metadata)
        node_props = (
            model_with_orphaned_metadata.props_metadata._get_prop_dict_from_prop_type(
                "node"
            )
        )
        edge_props = (
            model_with_orphaned_metadata.props_metadata._get_prop_dict_from_prop_type(
                "edge"
            )
        )
        lineage_props = (
            model_with_orphaned_metadata.props_metadata._get_prop_dict_from_prop_type(
                "lineage"
            )
        )

        # Check that orphaned properties are removed.
        assert "orphaned_node_prop" not in node_props
        assert "orphaned_edge_prop" not in edge_props
        assert "orphaned_lineage_prop" not in lineage_props

        # Check that non-orphaned properties are preserved.
        assert "timepoint" in node_props
        assert "cell_x" in node_props
        assert "link_x" in edge_props
        assert "lineage_ID" in lineage_props

    def test_orphaned_data(self, model_with_orphaned_data):
        """Test that metadata are unchanged when orphaned data properties are present."""
        before_node_props = (
            model_with_orphaned_data.props_metadata._get_prop_dict_from_prop_type("node")
        )
        before_edge_props = (
            model_with_orphaned_data.props_metadata._get_prop_dict_from_prop_type("edge")
        )
        before_lineage_props = (
            model_with_orphaned_data.props_metadata._get_prop_dict_from_prop_type(
                "lineage"
            )
        )
        _remove_orphaned_metadata(model_with_orphaned_data)
        after_node_props = (
            model_with_orphaned_data.props_metadata._get_prop_dict_from_prop_type("node")
        )
        after_edge_props = (
            model_with_orphaned_data.props_metadata._get_prop_dict_from_prop_type("edge")
        )
        after_lineage_props = (
            model_with_orphaned_data.props_metadata._get_prop_dict_from_prop_type(
                "lineage"
            )
        )

        assert before_node_props == after_node_props
        assert before_edge_props == after_edge_props
        assert before_lineage_props == after_lineage_props

    def test_empty_metadata(self, model):
        """Test with empty metadata."""
        model.props_metadata = PropsMetadata()
        _remove_orphaned_metadata(model)

        # Metadata should still be empty.
        node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
        edge_props = model.props_metadata._get_prop_dict_from_prop_type("edge")
        lineage_props = model.props_metadata._get_prop_dict_from_prop_type("lineage")
        assert len(node_props) == 0
        assert len(edge_props) == 0
        assert len(lineage_props) == 0

    # TODO: review the tests below (until the end of the class)

    def test_multitype_property_in_both_node_and_lineage(self, model):
        """Test multi-type property found in both nodes and lineage graph is NOT removed."""
        before_node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
        before_lineage_props = model.props_metadata._get_prop_dict_from_prop_type(
            "lineage"
        )
        _remove_orphaned_metadata(model)
        after_node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
        after_lineage_props = model.props_metadata._get_prop_dict_from_prop_type(
            "lineage"
        )

        assert "lineage_ID" in after_node_props
        assert "lineage_ID" in after_lineage_props
        assert len(before_node_props) == len(after_node_props)
        assert len(before_lineage_props) == len(after_lineage_props)

    def test_multitype_property_missing_from_nodes_but_in_lineage(
        self, model_with_lineage_id_config
    ):
        """Test multi-type property missing from nodes but present in lineage."""
        model = model_with_lineage_id_config(
            lin1_node_lin_id=False,
            lin1_graph_lin_id=True,
            lin2_node_lin_id=False,
            lin2_graph_lin_id=True,
        )
        with pytest.warns(UserWarning, match="Node metadata with no corresponding data"):
            _remove_orphaned_metadata(model)

        node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
        lineage_props = model.props_metadata._get_prop_dict_from_prop_type("lineage")

        assert "lineage_ID" not in node_props
        assert "lineage_ID" in lineage_props

    def test_multitype_property_missing_from_lineage_but_in_nodes(
        self, model_with_lineage_id_config
    ):
        """Test multi-type property missing from lineage but present in nodes."""
        model = model_with_lineage_id_config(
            lin1_node_lin_id=True,
            lin1_graph_lin_id=False,
            lin2_node_lin_id=True,
            lin2_graph_lin_id=False,
        )

        with pytest.warns(
            UserWarning, match="Lineage metadata with no corresponding data"
        ):
            _remove_orphaned_metadata(model)

        node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
        lineage_props = model.props_metadata._get_prop_dict_from_prop_type("lineage")

        assert "lineage_ID" in node_props
        assert "lineage_ID" not in lineage_props

    def test_multitype_property_missing_from_both(self, model_with_lineage_id_config):
        """Test multi-type property missing from both nodes and lineage graph."""
        model = model_with_lineage_id_config(
            lin1_node_lin_id=False,
            lin1_graph_lin_id=False,
            lin2_node_lin_id=False,
            lin2_graph_lin_id=False,
        )
        with pytest.warns(UserWarning, match="Node metadata with no corresponding data"):
            with pytest.warns(UserWarning, match="Lineage metadata with no corresponding data"):
                _remove_orphaned_metadata(model)


class TestSplitGraphIntoLineages:
    """Test cases for _split_graph_into_lineages function."""

    def test_split_graph_into_lineages(self, two_lin_graph, lin_props, expected_two_lins):
        """Test splitting graph into lineages."""
        g1_attr, g2_attr = lin_props
        obtained = _split_graph_into_lineages(
            two_lin_graph, lineage_ID_key="lineage_ID", lin_props=[g1_attr, g2_attr]
        )

        g1_exp, g2_exp = expected_two_lins
        g1_exp.graph["name"] = "blob"
        g2_exp.graph["name"] = "blub"

        assert len(obtained) == 2
        assert is_equal(obtained[0], g1_exp)
        assert is_equal(obtained[1], g2_exp)

    def test_different_lin_ID_key(
        self,
        two_lin_graph_with_track_id,
        lin_props_with_track_id,
        expected_two_lins_with_track_id,
    ):
        """Test splitting graph with different lineage ID key."""
        g1_attr, g2_attr = lin_props_with_track_id
        obtained = _split_graph_into_lineages(
            two_lin_graph_with_track_id,
            lineage_ID_key="TRACK_ID",
            lin_props=[g1_attr, g2_attr],
        )

        g1_exp, g2_exp = expected_two_lins_with_track_id
        g1_exp.graph["name"] = "blob"
        g2_exp.graph["name"] = "blub"

        assert len(obtained) == 2
        assert is_equal(obtained[0], g1_exp)
        assert is_equal(obtained[1], g2_exp)

    def test_no_lin_props(self, two_lin_graph, expected_two_lins):
        """Test splitting graph with no lineage properties."""
        obtained = _split_graph_into_lineages(two_lin_graph, lineage_ID_key="lineage_ID")

        g1_exp, g2_exp = expected_two_lins

        assert len(obtained) == 2
        assert is_equal(obtained[0], g1_exp)
        assert is_equal(obtained[1], g2_exp)

    def test_different_ID(self, two_lin_graph, lin_props):
        """Test that different lineage IDs in nodes raises error."""
        g1_attr, g2_attr = lin_props
        g = two_lin_graph
        g.nodes[1]["lineage_ID"] = 2  # inconsistent with node 2 which has lineage_ID 0

        with pytest.raises(ValueError, match="inconsistent lineage ID values"):
            _split_graph_into_lineages(
                g, lineage_ID_key="lineage_ID", lin_props=[g1_attr, g2_attr]
            )

    def test_auto_generated_ids(self, expected_two_lins):
        """Test auto-generated IDs for single-node lineages (negative IDs)."""
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (3, 4)])  # positive IDs
        g.add_nodes_from([10, 20])  # negative IDs
        obtained = _split_graph_into_lineages(g, lineage_ID_key=None)

        lin10_exp = CellLineage()
        lin10_exp.add_node(10, lineage_ID=-10)
        lin10_exp.graph["lineage_ID"] = -10
        lin20_exp = CellLineage()
        lin20_exp.add_node(20, lineage_ID=-20)
        lin20_exp.graph["lineage_ID"] = -20
        expected_two_lins.extend([lin10_exp, lin20_exp])

        assert len(obtained) == 4
        for g1, g2 in zip(obtained, expected_two_lins):
            assert is_equal(g1, g2)

    def test_nodes_have_key_lin_dont(self, two_lin_graph, lin_props, expected_two_lins):
        """Test when all nodes have lineage_ID_key but the graph doesn't."""
        obtained = _split_graph_into_lineages(
            two_lin_graph, lineage_ID_key="lineage_ID", lin_props=lin_props
        )

        expected_two_lins[0].graph["name"] = "blob"
        expected_two_lins[1].graph["name"] = "blub"

        assert len(obtained) == 2
        for g1, g2 in zip(obtained, expected_two_lins):
            assert is_equal(g1, g2)

    def test_lin_has_key_nodes_dont(self):
        """Test when graph has klineage_ID_key but nodes don't.

        This can only happen when there is only one lineage in the graph.
        """
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (2, 3), (3, 4)])
        g.graph["lineage_ID"] = 0
        obtained = _split_graph_into_lineages(g, lineage_ID_key="lineage_ID")

        expected = CellLineage()
        expected.add_edges_from([(1, 2), (2, 3), (3, 4)])
        for node in expected.nodes:
            expected.nodes[node]["lineage_ID"] = 0
        expected.graph["lineage_ID"] = 0

        assert len(obtained) == 1
        assert is_equal(obtained[0], expected)

    def test_partial_nodes_with_agreement(
        self, two_lin_graph, lin_props, expected_two_lins
    ):
        """Test when some (not all) nodes have the ID key with same value."""
        # Remove lineage_ID from some nodes.
        two_lin_graph.nodes[1].pop("lineage_ID")
        two_lin_graph.nodes[2].pop("lineage_ID")
        obtained = _split_graph_into_lineages(
            two_lin_graph, lineage_ID_key="lineage_ID", lin_props=lin_props
        )

        expected_two_lins[0].graph["name"] = "blob"
        expected_two_lins[1].graph["name"] = "blub"

        assert len(obtained) == 2
        for g1, g2 in zip(obtained, expected_two_lins):
            assert is_equal(g1, g2)

    def test_empty_graph_with_lin_key(self):
        """Test with an empty graph (no nodes)."""
        g = nx.DiGraph()
        obt_1 = _split_graph_into_lineages(g, lineage_ID_key="lineage_ID")

        expected = CellLineage()
        expected.graph["lineage_ID"] = 0

        assert len(obt_1) == 1
        assert is_equal(obt_1[0], expected)

    def test_empty_graph_without_lin_key(self):
        """Test with an empty graph (no nodes) and no lineage_ID_key."""
        g = nx.DiGraph()
        obt_1 = _split_graph_into_lineages(g)

        expected = CellLineage()
        expected.graph["lineage_ID"] = 0

        assert len(obt_1) == 1
        assert is_equal(obt_1[0], expected)

    def test_mismatched_lin_props_warning(self, two_lin_graph):
        """Test that providing lin_props with unmatched lineage IDs issues warnings."""
        # lin_props with IDs 5 and 6, but graph has 0 and 1
        lin_props = [
            {"lineage_ID": 5, "name": "blob"},
            {"lineage_ID": 6, "name": "blub"},
        ]

        with pytest.warns(UserWarning, match="No lineage properties found"):
            result = _split_graph_into_lineages(
                two_lin_graph, lineage_ID_key="lineage_ID", lin_props=lin_props
            )

        # Lineages should still be created, just without the extra properties
        assert len(result) == 2
        for lin in result:
            # Graph-level properties should not be added (except lineage_ID from nodes)
            assert "name" not in lin.graph


class TestUpdateNodePropKey:
    """Test cases for _update_node_prop_key function."""

    def test_update_node_prop_key(self, lin_with_old_key):
        """Test basic update of node property key."""
        old_key_values = ["value1", "value2", "value3"]
        _update_node_prop_key(lin_with_old_key, "old_key", "new_key")

        for i, node in enumerate(lin_with_old_key.nodes):
            assert "new_key" in lin_with_old_key.nodes[node]
            assert "old_key" not in lin_with_old_key.nodes[node]
            assert lin_with_old_key.nodes[node]["new_key"] == old_key_values[i]

    def test_missing_old_key_skip(self, lin_with_mixed_keys):
        """Test that nodes without old_key are skipped when enforce_old_key_existence=False."""
        _update_node_prop_key(lin_with_mixed_keys, "old_key", "new_key")

        assert lin_with_mixed_keys.nodes[1]["new_key"] == "value1"
        assert "old_key" not in lin_with_mixed_keys.nodes[1]
        assert "new_key" not in lin_with_mixed_keys.nodes[2]
        assert "old_key" not in lin_with_mixed_keys.nodes[2]
        assert lin_with_mixed_keys.nodes[3]["new_key"] == "value3"
        assert "old_key" not in lin_with_mixed_keys.nodes[3]

    def test_enforce_old_key_existence(self, lin_with_mixed_keys):
        """Test that missing old_key raises error when enforce_old_key_existence=True."""
        err_msg = "Node 2 does not have the required key 'old_key'"
        with pytest.raises(ValueError, match=err_msg):
            _update_node_prop_key(
                lin_with_mixed_keys,
                "old_key",
                "new_key",
                enforce_old_key_existence=True,
            )

    def test_set_default_if_missing(self, lin_with_mixed_keys):
        """Test setting default value when old_key is missing and set_default_if_missing=True."""
        _update_node_prop_key(
            lin_with_mixed_keys,
            "old_key",
            "new_key",
            set_default_if_missing=True,
            default_value="default",
        )

        assert lin_with_mixed_keys.nodes[1]["new_key"] == "value1"
        assert "old_key" not in lin_with_mixed_keys.nodes[1]
        assert lin_with_mixed_keys.nodes[2]["new_key"] == "default"
        assert "old_key" not in lin_with_mixed_keys.nodes[2]
        assert lin_with_mixed_keys.nodes[3]["new_key"] == "value3"
        assert "old_key" not in lin_with_mixed_keys.nodes[3]

    def test_set_default_none(self, lin_with_mixed_keys):
        """Test setting None as default value when old_key is missing."""
        _update_node_prop_key(
            lin_with_mixed_keys, "old_key", "new_key", set_default_if_missing=True
        )

        assert lin_with_mixed_keys.nodes[1]["new_key"] == "value1"
        assert lin_with_mixed_keys.nodes[2]["new_key"] is None

    def test_empty_lineage(self):
        """Test function with empty lineage (no nodes)."""
        lin = CellLineage()
        # Should not raise an error and do nothing
        _update_node_prop_key(lin, "old_key", "new_key")
        assert len(lin.nodes) == 0

    def test_same_key_name(self):
        """Test updating a key to itself (should work without issues)."""
        lin = CellLineage()
        lin.add_node(1, test_key="value1")
        lin.add_node(2, test_key="value2")

        _update_node_prop_key(lin, "test_key", "test_key")

        assert lin.nodes[1]["test_key"] == "value1"
        assert lin.nodes[2]["test_key"] == "value2"


class TestUpdateLineagePropKey:
    """Test cases for _update_lineage_prop_key function."""

    def test_update_lineage_prop_key(self):
        """Test updating a lineage property key."""
        lin = CellLineage()
        lin.graph["old_key"] = "old_value"
        _update_lineage_prop_key(lin, "old_key", "new_key")

        assert "new_key" in lin.graph
        assert lin.graph["new_key"] == "old_value"
        assert "old_key" not in lin.graph


class TestUpdateLineagesIDsKey:
    """Test cases for _update_lineages_IDs_key function."""

    def test_update_lineages_IDs_key(self):
        """Test updating lineage IDs key."""
        lin1 = CellLineage()
        lin1.add_nodes_from([1, 2, 3])
        lin1.graph["TRACK_ID"] = 10
        lin2 = CellLineage()
        lin2.add_nodes_from([4, 5])
        lin2.graph["TRACK_ID"] = 20

        _update_lineages_IDs_key([lin1, lin2], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == 10
        assert lin2.graph["lineage_ID"] == 20
        assert "TRACK_ID" not in lin1.graph
        assert "TRACK_ID" not in lin2.graph

    def test_no_key_multi_node(self):
        """Test updating lineage IDs key when no TRACK_ID key is present in a multi-node lineage."""
        lin1 = CellLineage()
        lin1.add_nodes_from([1, 2, 3])
        lin2 = CellLineage()
        lin2.add_nodes_from([4, 5])
        lin2.graph["TRACK_ID"] = 20

        _update_lineages_IDs_key([lin1, lin2], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == 21
        assert lin2.graph["lineage_ID"] == 20
        assert "TRACK_ID" not in lin1.graph
        assert "TRACK_ID" not in lin2.graph

    def test_no_key_one_node(self):
        """Test updating lineage IDs key when no TRACK_ID key is present in a one-node lineage."""
        lin1 = CellLineage()
        lin1.add_node(1)
        lin2 = CellLineage()
        lin2.add_nodes_from([4, 5])
        lin2.graph["TRACK_ID"] = 20

        _update_lineages_IDs_key([lin1, lin2], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == -1
        assert lin2.graph["lineage_ID"] == 20

    def test_all_lineages_no_key(self):
        """Test updating lineage IDs key when no lineages have the key."""
        lin1 = CellLineage()
        lin1.add_nodes_from([1, 2, 3])
        lin2 = CellLineage()
        lin2.add_nodes_from([4, 5])
        lin3 = CellLineage()
        lin3.add_node(6)

        _update_lineages_IDs_key([lin1, lin2, lin3], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == 0
        assert lin2.graph["lineage_ID"] == 1
        assert lin3.graph["lineage_ID"] == -6
        assert "TRACK_ID" not in lin1.graph
        assert "TRACK_ID" not in lin2.graph
        assert "TRACK_ID" not in lin3.graph

    def test_empty_list(self):
        """Test updating lineage IDs key with empty lineages list."""
        _update_lineages_IDs_key([], "TRACK_ID")

    def test_mixed_scenarios(self):
        """Test with mix of single-node, multi-node, and lineages with existing keys."""
        lin1 = CellLineage()  # single node, no key
        lin1.add_node(1)
        lin2 = CellLineage()  # multi-node, no key
        lin2.add_nodes_from([2, 3])
        lin3 = CellLineage()  # has key
        lin3.add_node(4)
        lin3.graph["TRACK_ID"] = 10
        lin4 = CellLineage()  # single node, no key
        lin4.add_node(5)

        _update_lineages_IDs_key([lin1, lin2, lin3, lin4], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == -1
        assert lin2.graph["lineage_ID"] == 11
        assert lin3.graph["lineage_ID"] == 10
        assert lin4.graph["lineage_ID"] == -5

    def test_preserves_other_graph_attributes(self):
        """Test that other graph attributes are preserved."""
        lin1 = CellLineage()
        lin1.add_node(1)
        lin1.graph["TRACK_ID"] = 10
        lin1.graph["other_attr"] = "value"

        _update_lineages_IDs_key([lin1], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == 10
        assert lin1.graph["other_attr"] == "value"
        assert "TRACK_ID" not in lin1.graph
