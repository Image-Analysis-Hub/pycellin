#!/usr/bin/env python3

"""Unit test for motion property classes from pycellin.properties."""

import math
import warnings

import networkx as nx
import pytest

from pycellin.classes import CellLineage, Data, Property
from pycellin.properties.motion import (
    CellSpeed,
    CycleMeanDisplacement,
    CycleMeanSpeed,
    CycleTotalDisplacement,
)

# Fixtures ####################################################################


@pytest.fixture
def data():
    # Cycles: 3 = [1, 2, 3] (root), 4 = [4] and 5 = [5] (leaves).
    # Each link holds its target cell ID as "my_motion" value.
    lineage = CellLineage()
    lineage.add_edges_from([(1, 2), (2, 3), (3, 4), (3, 5)])
    for n in lineage.nodes:
        lineage.nodes[n]["frame"] = nx.shortest_path_length(lineage, 1, n)
        lineage.nodes[n]["cell_ID"] = n
    for source, target in lineage.edges:
        lineage.edges[source, target]["my_motion"] = float(target)
    lineage.graph["lineage_ID"] = 1
    data = Data({1: lineage})
    data._add_cycle_lineages(time_prop="frame", time_step=1)
    return data


@pytest.fixture
def prop_cycle_lin():
    return Property(
        identifier="test_property",
        name="test property",
        description="test property",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
    )


@pytest.fixture
def prop_cell_lin_edge():
    return Property(
        identifier="test_property",
        name="test property",
        description="test property",
        provenance="pycellin",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="float",
    )


# CellSpeed ###################################################################


class TestCellSpeed:
    def test_compute(self, prop_cell_lin_edge):
        lineage = CellLineage()
        lineage.add_node(1, frame=0, cell_x=0.0, cell_y=0.0, cell_z=0.0)
        lineage.add_node(2, frame=2, cell_x=3.0, cell_y=4.0, cell_z=0.0)
        lineage.add_edge(1, 2)
        calculator = CellSpeed(prop_cell_lin_edge, time_prop="frame")
        assert calculator.compute(lineage, (1, 2)) == 2.5

    def test_compute_ignores_cell_displacement(self, prop_cell_lin_edge):
        lineage = CellLineage()
        lineage.add_node(1, frame=0, cell_x=0.0, cell_y=0.0, cell_z=0.0)
        lineage.add_node(2, frame=2, cell_x=3.0, cell_y=4.0, cell_z=0.0)
        lineage.add_edge(1, 2, cell_displacement=100.0)
        calculator = CellSpeed(prop_cell_lin_edge, time_prop="frame")
        assert calculator.compute(lineage, (1, 2)) == 2.5


# CycleTotalDisplacement ######################################################


class TestCycleTotalDisplacement:
    def test_compute_custom_displacement_prop(self, data, prop_cycle_lin):
        calculator = CycleTotalDisplacement(
            prop_cycle_lin, displacement_prop="my_motion"
        )
        assert calculator.compute(data, data.cycle_data[1], nid=3) == 5.0

    def test_compute_cycle_without_link(self, data, prop_cycle_lin):
        calculator = CycleTotalDisplacement(
            prop_cycle_lin, displacement_prop="my_motion"
        )
        assert math.isnan(calculator.compute(data, data.cycle_data[1], nid=4))

    def test_get_input_props(self, prop_cycle_lin):
        calculator = CycleTotalDisplacement(prop_cycle_lin)
        assert calculator.get_input_props() == {
            "displacement_prop": ("cell_displacement", "edge", "CellLineage")
        }


# CycleMeanDisplacement #######################################################


class TestCycleMeanDisplacement:
    def test_compute_custom_displacement_prop(self, data, prop_cycle_lin):
        calculator = CycleMeanDisplacement(
            prop_cycle_lin, displacement_prop="my_motion"
        )
        assert calculator.compute(data, data.cycle_data[1], nid=3) == 2.5

    def test_compute_cycle_without_link(self, data, prop_cycle_lin):
        calculator = CycleMeanDisplacement(
            prop_cycle_lin, displacement_prop="my_motion"
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = calculator.compute(data, data.cycle_data[1], nid=4)
        assert math.isnan(result)


# CycleMeanSpeed ##############################################################


class TestCycleMeanSpeed:
    def test_compute_custom_speed_prop(self, data, prop_cycle_lin):
        calculator = CycleMeanSpeed(prop_cycle_lin, speed_prop="my_motion")
        assert calculator.compute(data, data.cycle_data[1], nid=3) == 2.5

    def test_compute_include_incoming_edge(self, data, prop_cycle_lin):
        calculator = CycleMeanSpeed(
            prop_cycle_lin, include_incoming_edge=True, speed_prop="my_motion"
        )
        assert calculator.compute(data, data.cycle_data[1], nid=4) == 4.0

    def test_compute_cycle_without_link(self, data, prop_cycle_lin):
        calculator = CycleMeanSpeed(prop_cycle_lin, speed_prop="my_motion")
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = calculator.compute(data, data.cycle_data[1], nid=4)
        assert math.isnan(result)
