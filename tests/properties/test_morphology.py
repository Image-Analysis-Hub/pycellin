#!/usr/bin/env python3

"""Unit test for morphology property classes from pycellin.properties."""

import math

import networkx as nx
import pytest

from pycellin.classes import CellLineage, Data, Property
from pycellin.properties.morphology import (
    BirthArea,
    CycleMeanArea,
    DivisionArea,
)

# Fixtures ####################################################################


@pytest.fixture
def data():
    # Cycles: 4 = [1, 2, 3, 4] (root), 6 = [5, 6] (complete),
    # 7 = [7], 8 = [8] and 9 = [9] (leaves).
    lineage = CellLineage()
    lineage.add_edges_from(
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (4, 7), (6, 8), (6, 9)]
    )
    for n in lineage.nodes:
        lineage.nodes[n]["frame"] = nx.shortest_path_length(lineage, 1, n)
        lineage.nodes[n]["cell_ID"] = n
        lineage.nodes[n]["cell_area"] = float(n)
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
        unit="um^2",
    )


# CycleMeanArea ###############################################################


class TestCycleMeanArea:
    def test_compute(self, data, prop_cycle_lin):
        calculator = CycleMeanArea(prop_cycle_lin)
        cycle_lin = data.cycle_data[1]
        assert calculator.compute(data, cycle_lin, nid=4) == 2.5
        assert calculator.compute(data, cycle_lin, nid=6) == 5.5
        assert calculator.compute(data, cycle_lin, nid=7) == 7.0

    def test_compute_ignores_nan(self, data, prop_cycle_lin):
        data.cell_data[1].nodes[3]["cell_area"] = math.nan
        calculator = CycleMeanArea(prop_cycle_lin)
        result = calculator.compute(data, data.cycle_data[1], nid=4)
        assert result == pytest.approx(7 / 3)

    def test_enrich(self, data, prop_cycle_lin):
        calculator = CycleMeanArea(prop_cycle_lin)
        calculator.enrich(data)
        cycle_lin = data.cycle_data[1]
        assert cycle_lin.nodes[4]["test_property"] == 2.5
        assert cycle_lin.nodes[6]["test_property"] == 5.5
        assert cycle_lin.nodes[7]["test_property"] == 7.0


# BirthArea ###################################################################


class TestBirthArea:
    def test_compute_complete_cycle(self, data, prop_cycle_lin):
        calculator = BirthArea(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 5.0

    def test_compute_leaf_cycle(self, data, prop_cycle_lin):
        calculator = BirthArea(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=7) == 7.0

    def test_compute_root_cycle(self, data, prop_cycle_lin):
        calculator = BirthArea(prop_cycle_lin)
        assert math.isnan(calculator.compute(data, data.cycle_data[1], nid=4))

    def test_compute_missing_cell_area(self, data, prop_cycle_lin):
        del data.cell_data[1].nodes[5]["cell_area"]
        calculator = BirthArea(prop_cycle_lin)
        with pytest.raises(KeyError, match="'cell_area' does not exist"):
            calculator.compute(data, data.cycle_data[1], nid=6)


# DivisionArea ################################################################


class TestDivisionArea:
    def test_compute_complete_cycle(self, data, prop_cycle_lin):
        calculator = DivisionArea(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 6.0

    def test_compute_root_cycle(self, data, prop_cycle_lin):
        calculator = DivisionArea(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=4) == 4.0

    def test_compute_leaf_cycle(self, data, prop_cycle_lin):
        calculator = DivisionArea(prop_cycle_lin)
        assert math.isnan(calculator.compute(data, data.cycle_data[1], nid=7))

    def test_compute_missing_cell_area(self, data, prop_cycle_lin):
        del data.cell_data[1].nodes[6]["cell_area"]
        calculator = DivisionArea(prop_cycle_lin)
        with pytest.raises(KeyError, match="'cell_area' does not exist"):
            calculator.compute(data, data.cycle_data[1], nid=6)
