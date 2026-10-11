#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for tracking property classes from pycellin.properties."""

import math

import pytest

import networkx as nx

from pycellin.properties.tracking import (
    AbsoluteAge,
    RelativeAge,
    NormalizedAge,
    CycleCompleteness,
    DivisionTime,
    DivisionRate,
)
from pycellin.classes import Property, Data, CellLineage, CycleLineage


# Fixtures ####################################################################


@pytest.fixture
def cell_lin():
    # Nothing special, just a lineage.
    lineage = CellLineage()
    lineage.add_edges_from(
        [
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (4, 7),
            (7, 8),
            (8, 9),
            (8, 10),
            (2, 11),
            (11, 12),
            (12, 13),
            (13, 14),
            (14, 15),
            (14, 16),
        ]
    )
    for n in lineage.nodes:
        lineage.nodes[n]["frame"] = nx.shortest_path_length(lineage, 1, n)
        lineage.nodes[n]["cell_ID"] = n
    lineage.graph["lineage_ID"] = 1
    return lineage


@pytest.fixture
def prop_cell_lin():
    return Property(
        identifier="test_property",
        name="test property",
        description="test property",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
        unit="um",
    )


@pytest.fixture
def cycle_lin(cell_lin):
    # Nothing special, just a lineage.
    lineage = CycleLineage(
        time_prop="frame",
        time_step=1,
        cell_lineage=cell_lin,
    )
    return lineage


@pytest.fixture
def prop_cycle_lin():
    return Property(
        identifier="test_property",
        name="test property",
        description="test property",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
        unit="um",
    )


# AbsoluteAge #################################################################


def test_absolute_age(cell_lin, prop_cell_lin):
    """Test AbsoluteAge Calculator."""
    calculator = AbsoluteAge(prop_cell_lin, time_prop="frame")
    # Root.
    assert calculator.compute(cell_lin, nid=1) == 0
    # Divisions.
    assert calculator.compute(cell_lin, nid=2) == 1
    assert calculator.compute(cell_lin, nid=4) == 3
    # Leaves.
    assert calculator.compute(cell_lin, nid=6) == 5
    assert calculator.compute(cell_lin, nid=10) == 6
    # Intermediate nodes.
    assert calculator.compute(cell_lin, nid=3) == 2
    assert calculator.compute(cell_lin, nid=13) == 4
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(cell_lin, nid=99)


# RelativeAge #################################################################


def test_relative_age(cell_lin, prop_cell_lin):
    """Test RelativeAge Calculator."""
    calculator = RelativeAge(prop_cell_lin, time_prop="frame")
    # Root.
    assert calculator.compute(cell_lin, nid=1) == 0
    # Divisions.
    assert calculator.compute(cell_lin, nid=2) == 1
    assert calculator.compute(cell_lin, nid=4) == 1
    # Leaves.
    assert calculator.compute(cell_lin, nid=6) == 1
    assert calculator.compute(cell_lin, nid=10) == 0
    # Intermediate nodes.
    assert calculator.compute(cell_lin, nid=3) == 0
    assert calculator.compute(cell_lin, nid=13) == 2
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(cell_lin, nid=99)


# NormalizedAge ###############################################################


class TestNormalizedAge:
    def test_compute_first_cell_of_cycle(self, cell_lin, prop_cell_lin):
        calculator = NormalizedAge(prop_cell_lin, time_prop="frame")
        # Root, then a cell born from a division.
        assert calculator.compute(cell_lin, nid=1) == 0
        assert calculator.compute(cell_lin, nid=11) == 0

    def test_compute_last_cell_of_cycle(self, cell_lin, prop_cell_lin):
        calculator = NormalizedAge(prop_cell_lin, time_prop="frame")
        # Division, then leaf.
        assert calculator.compute(cell_lin, nid=14) == 1
        assert calculator.compute(cell_lin, nid=6) == 1

    def test_compute_intermediate_cells(self, cell_lin, prop_cell_lin):
        calculator = NormalizedAge(prop_cell_lin, time_prop="frame")
        # Cycle [11, 12, 13, 14], from frame 2 to frame 5.
        assert calculator.compute(cell_lin, nid=12) == pytest.approx(1 / 3)
        assert calculator.compute(cell_lin, nid=13) == pytest.approx(2 / 3)

    def test_compute_gap(self, cell_lin, prop_cell_lin):
        cell_lin.remove_node(12)
        cell_lin.add_edge(11, 13)
        calculator = NormalizedAge(prop_cell_lin, time_prop="frame")
        # Cycle [11, 13, 14], from frame 2 to frame 5: normalized by time, not by
        # position in the cycle.
        assert calculator.compute(cell_lin, nid=13) == pytest.approx(2 / 3)

    def test_compute_single_cell_cycle(self, cell_lin, prop_cell_lin):
        calculator = NormalizedAge(prop_cell_lin, time_prop="frame")
        assert math.isnan(calculator.compute(cell_lin, nid=9))

    def test_compute_ignored_cycle_starting_at_root(self, cell_lin, prop_cell_lin):
        calculator = NormalizedAge(
            prop_cell_lin, time_prop="frame", ignore_incomplete_cycles=True
        )
        # Cycle [1, 2].
        assert math.isnan(calculator.compute(cell_lin, nid=1))

    def test_compute_ignored_cycle_ending_with_leaf(self, cell_lin, prop_cell_lin):
        calculator = NormalizedAge(
            prop_cell_lin, time_prop="frame", ignore_incomplete_cycles=True
        )
        # Cycle [5, 6].
        assert math.isnan(calculator.compute(cell_lin, nid=5))

    def test_compute_complete_cycle_not_ignored(self, cell_lin, prop_cell_lin):
        calculator = NormalizedAge(
            prop_cell_lin, time_prop="frame", ignore_incomplete_cycles=True
        )
        # Cycle [11, 12, 13, 14], from a division to a division.
        assert calculator.compute(cell_lin, nid=12) == pytest.approx(1 / 3)

    def test_compute_missing_cell(self, cell_lin, prop_cell_lin):
        calculator = NormalizedAge(prop_cell_lin, time_prop="frame")
        with pytest.raises(KeyError):
            calculator.compute(cell_lin, nid=99)

    def test_get_input_props(self, prop_cell_lin):
        calculator = NormalizedAge(prop_cell_lin, time_prop="frame")
        assert calculator.get_input_props() == {
            "time_prop": ("frame", "node", "CellLineage")
        }


# CellCycleCompleteness #######################################################


def test_cell_cycle_completeness_cell_lin(cell_lin, prop_cell_lin):
    """Test CycleCompleteness Calculator with CellLineage."""
    calculator = CycleCompleteness(prop_cell_lin)
    # Complete cell cycles.
    assert calculator.compute(cell_lin, nid=4) is True  # division
    assert calculator.compute(cell_lin, nid=14) is True  # division
    assert calculator.compute(cell_lin, nid=7) is True  # intermediate
    assert calculator.compute(cell_lin, nid=13) is True  # intermediate
    # Incomplete cell cycles.
    assert calculator.compute(cell_lin, nid=1) is False  # root
    assert calculator.compute(cell_lin, nid=6) is False  # leaf
    assert calculator.compute(cell_lin, nid=10) is False  # leaf
    assert calculator.compute(cell_lin, nid=2) is False  # division
    assert calculator.compute(cell_lin, nid=5) is False  # intermediate
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(cell_lin, nid=99)


def test_cell_cycle_completeness_cycle_lin(cycle_lin, prop_cycle_lin):
    """Test CycleCompleteness Calculator with CycleLineage."""
    calculator = CycleCompleteness(prop_cycle_lin)
    # Complete cell cycles.
    assert calculator.compute(cycle_lin, nid=4) is True  # division
    assert calculator.compute(cycle_lin, nid=8) is True  # division
    assert calculator.compute(cycle_lin, nid=14) is True  # division
    # Incomplete cell cycles.
    assert calculator.compute(cycle_lin, nid=2) is False  # division
    assert calculator.compute(cycle_lin, nid=6) is False  # leaf
    assert calculator.compute(cycle_lin, nid=10) is False  # leaf
    assert calculator.compute(cycle_lin, nid=15) is False  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(cycle_lin, nid=99)


# DivisionTime ################################################################


def test_division_time(cell_lin, prop_cell_lin):
    """Test DivisionTime Calculator."""
    calculator = DivisionTime(prop_cell_lin, time_prop="frame")
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 1
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 1
    assert calculator.compute(Data({}), cell_lin, nid=4) == 2
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 2
    assert calculator.compute(Data({}), cell_lin, nid=10) == 1
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=3) == 2
    assert calculator.compute(Data({}), cell_lin, nid=13) == 4
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_division_time_gap(cell_lin, prop_cell_lin):
    """Test DivisionTime Calculator and a gap in the lineage."""
    # Create a lineage with a gap.
    cell_lin.remove_nodes_from([3, 12, 13])
    cell_lin.add_edges_from([(2, 4), (11, 14)])
    calculator = DivisionTime(prop_cell_lin, time_prop="frame")
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 1
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 1
    assert calculator.compute(Data({}), cell_lin, nid=4) == 2
    assert calculator.compute(Data({}), cell_lin, nid=14) == 4
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 2
    assert calculator.compute(Data({}), cell_lin, nid=10) == 1
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=11) == 4
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_division_time_cycle_lin(cell_lin, prop_cycle_lin):
    """Test DivisionTime Calculator with CycleLineage."""
    calculator = DivisionTime(prop_cycle_lin, time_prop="frame")
    data = Data({1: cell_lin})
    data._add_cycle_lineages(time_prop="frame", time_step=1)
    cycle_lin = data.cycle_data[1]
    # Complete cell cycles.
    assert calculator.compute(data, cycle_lin, nid=4) == 2  # division
    assert calculator.compute(data, cycle_lin, nid=8) == 2  # division
    assert calculator.compute(data, cycle_lin, nid=14) == 4  # division
    # Incomplete cell cycles.
    assert calculator.compute(data, cycle_lin, nid=2) == 1  # division
    assert calculator.compute(data, cycle_lin, nid=6) == 2  # leaf
    assert calculator.compute(data, cycle_lin, nid=10) == 1  # leaf
    assert calculator.compute(data, cycle_lin, nid=15) == 1  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(data, cycle_lin, nid=99)


# DivisionRate ################################################################


def test_division_rate(cell_lin, prop_cell_lin):
    """Test DivisionRate Calculator."""
    calculator = DivisionRate(prop_cell_lin, time_prop="frame")
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 1 / 1
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 1 / 1
    assert calculator.compute(Data({}), cell_lin, nid=4) == 1 / 2
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 1 / 2
    assert calculator.compute(Data({}), cell_lin, nid=10) == 1 / 1
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=3) == 1 / 2
    assert calculator.compute(Data({}), cell_lin, nid=13) == 1 / 4
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_division_rate_gap(cell_lin, prop_cell_lin):
    """Test DivisionRate Calculator with a gap in the lineage."""
    # Create a lineage with a gap.
    cell_lin.remove_nodes_from([3, 12, 13])
    cell_lin.add_edges_from([(2, 4), (11, 14)])
    calculator = DivisionRate(prop_cell_lin, time_prop="frame")
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 1 / 1
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 1 / 1
    assert calculator.compute(Data({}), cell_lin, nid=4) == 1 / 2
    assert calculator.compute(Data({}), cell_lin, nid=14) == 1 / 4
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 1 / 2
    assert calculator.compute(Data({}), cell_lin, nid=10) == 1 / 1
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=11) == 1 / 4
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_division_rate_cycle_lin(cell_lin, prop_cycle_lin):
    """Test DivisionRate Calculator with CycleLineage."""
    calculator = DivisionRate(prop_cycle_lin, time_prop="frame")
    data = Data({1: cell_lin})
    data._add_cycle_lineages(time_prop="frame", time_step=1)
    cycle_lin = data.cycle_data[1]
    # Complete cell cycles.
    assert calculator.compute(data, cycle_lin, nid=4) == 1 / 2  # division
    assert calculator.compute(data, cycle_lin, nid=8) == 1 / 2  # division
    assert calculator.compute(data, cycle_lin, nid=14) == 1 / 4  # division
    # Incomplete cell cycles.
    assert calculator.compute(data, cycle_lin, nid=2) == 1 / 1  # division
    assert calculator.compute(data, cycle_lin, nid=6) == 1 / 2  # leaf
    assert calculator.compute(data, cycle_lin, nid=10) == 1 / 1  # leaf
    assert calculator.compute(data, cycle_lin, nid=15) == 1 / 1  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(data, cycle_lin, nid=99)
