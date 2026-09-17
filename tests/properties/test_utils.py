#!/usr/bin/env python3

"""Unit test for helper functions from pycellin.properties.utils."""

import networkx as nx
import pytest

from pycellin.classes import CellLineage, Data
from pycellin.properties.utils import (
    _get_cycle_edge_property_values,
    _get_cycle_node_property_values,
)

# Fixtures ####################################################################


@pytest.fixture
def data():
    # Cycles: 4 = [1, 2, 3, 4], 6 = [5, 6], 7 = [7].
    lineage = CellLineage()
    lineage.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (4, 7)])
    for n in lineage.nodes:
        lineage.nodes[n]["frame"] = nx.shortest_path_length(lineage, 1, n)
        lineage.nodes[n]["cell_ID"] = n
        lineage.nodes[n]["cell_area"] = float(n)
    for u, v in lineage.edges:
        lineage.edges[u, v]["cell_speed"] = float(v)
    lineage.graph["lineage_ID"] = 1
    data = Data({1: lineage})
    data._add_cycle_lineages(time_prop="frame", time_step=1)
    return data


# _get_cycle_node_property_values #############################################


class TestGetCycleNodePropertyValues:
    def test_several_cells(self, data):
        cycle_lin = data.cycle_data[1]
        values = _get_cycle_node_property_values("cell_area", data, cycle_lin, 4)
        assert values == [1.0, 2.0, 3.0, 4.0]

    def test_single_cell(self, data):
        cycle_lin = data.cycle_data[1]
        values = _get_cycle_node_property_values("cell_area", data, cycle_lin, 7)
        assert values == [7.0]

    def test_missing_property(self, data):
        cycle_lin = data.cycle_data[1]
        with pytest.raises(KeyError, match="'cell_perimeter' does not exist"):
            _get_cycle_node_property_values("cell_perimeter", data, cycle_lin, 4)


# _get_cycle_edge_property_values #############################################


class TestGetCycleEdgePropertyValues:
    def test_several_links(self, data):
        cycle_lin = data.cycle_data[1]
        values = _get_cycle_edge_property_values(
            "cell_speed", data, cycle_lin, 4, include_incoming_edge=False
        )
        assert values == [2.0, 3.0, 4.0]

    def test_no_link(self, data):
        cycle_lin = data.cycle_data[1]
        values = _get_cycle_edge_property_values(
            "cell_speed", data, cycle_lin, 7, include_incoming_edge=False
        )
        assert values == []

    def test_include_incoming_edge(self, data):
        cycle_lin = data.cycle_data[1]
        values = _get_cycle_edge_property_values(
            "cell_speed", data, cycle_lin, 6, include_incoming_edge=True
        )
        assert values == [6.0, 5.0]

    def test_include_incoming_edge_on_root(self, data):
        cycle_lin = data.cycle_data[1]
        values = _get_cycle_edge_property_values(
            "cell_speed", data, cycle_lin, 4, include_incoming_edge=True
        )
        assert values == [2.0, 3.0, 4.0]

    def test_missing_property(self, data):
        cycle_lin = data.cycle_data[1]
        with pytest.raises(KeyError, match="'cell_displacement' does not exist"):
            _get_cycle_edge_property_values(
                "cell_displacement", data, cycle_lin, 4, include_incoming_edge=False
            )
