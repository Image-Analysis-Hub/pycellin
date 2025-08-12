#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for tracking feature classe from graph.features."""

import pytest

import networkx as nx

from pycellin.graph.features.tracking import (
    AbsoluteAge,
    RelativeAge,
    CycleCompleteness,
    DivisionTime,
    DivisionRate,
)
from pycellin.classes import Feature, Data, CellLineage, CycleLineage


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
def feat_cell_lin():
    Feature(
        name="test_feature",
        description="test feature",
        provenance="pycellin",
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
        unit="um",
    )
    return Feature


@pytest.fixture
def cycle_lin(cell_lin):
    # Nothing special, just a lineage.
    lineage = CycleLineage(cell_lin)
    return lineage


@pytest.fixture
def feat_cycle_lin():
    Feature(
        name="test_feature",
        description="test feature",
        provenance="pycellin",
        feat_type="node",
        lin_type="CycleLineage",
        data_type="int",
        unit="um",
    )
    return Feature


# AbsoluteAge #################################################################


def test_absolute_age_default_time_step(cell_lin, feat_cell_lin):
    """Test AbsoluteAge with default time step."""
    calculator = AbsoluteAge(feat_cell_lin)
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 1
    assert calculator.compute(Data({}), cell_lin, nid=4) == 3
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 5
    assert calculator.compute(Data({}), cell_lin, nid=10) == 6
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=3) == 2
    assert calculator.compute(Data({}), cell_lin, nid=13) == 4
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_absolute_age_custom_time_step(cell_lin, feat_cell_lin):
    """Test AbsoluteAge with a custom time step."""
    calculator = AbsoluteAge(feat_cell_lin, time_step=2.5)
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 2.5
    assert calculator.compute(Data({}), cell_lin, nid=4) == 7.5
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 12.5
    assert calculator.compute(Data({}), cell_lin, nid=10) == 15.0
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=3) == 5.0
    assert calculator.compute(Data({}), cell_lin, nid=13) == 10.0
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(Data({}), cell_lin, nid=99)


# RelativeAge #################################################################


def test_relative_age_default_time_step(cell_lin, feat_cell_lin):
    """Test RelativeAge with default time step."""
    calculator = RelativeAge(feat_cell_lin)
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 1
    assert calculator.compute(Data({}), cell_lin, nid=4) == 1
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 1
    assert calculator.compute(Data({}), cell_lin, nid=10) == 0
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=3) == 0
    assert calculator.compute(Data({}), cell_lin, nid=13) == 2
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_relative_age_custom_time_step(cell_lin, feat_cell_lin):
    """Test RelativeAge with a custom time step."""
    calculator = RelativeAge(feat_cell_lin, time_step=2.5)
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 2.5
    assert calculator.compute(Data({}), cell_lin, nid=4) == 2.5
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 2.5
    assert calculator.compute(Data({}), cell_lin, nid=10) == 0
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=3) == 0
    assert calculator.compute(Data({}), cell_lin, nid=13) == 5.0
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(Data({}), cell_lin, nid=99)


# CellCycleCompleteness #######################################################


def test_cell_cycle_completeness_cell_lin(cell_lin, feat_cell_lin):
    calculator = CycleCompleteness(feat_cell_lin)
    # Complete cell cycles.
    assert calculator.compute(Data({}), cell_lin, nid=4) is True  # division
    assert calculator.compute(Data({}), cell_lin, nid=14) is True  # division
    assert calculator.compute(Data({}), cell_lin, nid=7) is True  # intermediate
    assert calculator.compute(Data({}), cell_lin, nid=13) is True  # intermediate
    # Incomplete cell cycles.
    assert calculator.compute(Data({}), cell_lin, nid=1) is False  # root
    assert calculator.compute(Data({}), cell_lin, nid=6) is False  # leaf
    assert calculator.compute(Data({}), cell_lin, nid=10) is False  # leaf
    assert calculator.compute(Data({}), cell_lin, nid=2) is False  # division
    assert calculator.compute(Data({}), cell_lin, nid=5) is False  # intermediate
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_cell_cycle_completeness_cycle_lin(cycle_lin, feat_cycle_lin):
    calculator = CycleCompleteness(feat_cycle_lin)
    # Complete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, nid=4) is True  # division
    assert calculator.compute(Data({}), cycle_lin, nid=8) is True  # division
    assert calculator.compute(Data({}), cycle_lin, nid=14) is True  # division
    # Incomplete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, nid=2) is False  # division
    assert calculator.compute(Data({}), cycle_lin, nid=6) is False  # leaf
    assert calculator.compute(Data({}), cycle_lin, nid=10) is False  # leaf
    assert calculator.compute(Data({}), cycle_lin, nid=15) is False  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(Data({}), cycle_lin, nid=99)


# DivisionTime ################################################################


def test_division_time_default_time_step(cell_lin, feat_cell_lin):
    """Test DivisionTime with default time step."""
    calculator = DivisionTime(feat_cell_lin)
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


def test_division_time_custom_time_step(cell_lin, feat_cell_lin):
    """Test DivisionTime with a custom time step."""
    calculator = DivisionTime(feat_cell_lin, time_step=2.5)
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 2.5
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 2.5
    assert calculator.compute(Data({}), cell_lin, nid=4) == 5.0
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 5.0
    assert calculator.compute(Data({}), cell_lin, nid=10) == 2.5
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=3) == 5.0
    assert calculator.compute(Data({}), cell_lin, nid=13) == 10.0
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_division_time_gap(cell_lin, feat_cell_lin):
    """Test DivisionTime with a gap in the lineage."""
    # Create a lineage with a gap.
    cell_lin.remove_nodes_from([3, 12, 13])
    cell_lin.add_edges_from([(2, 4), (11, 14)])
    calculator = DivisionTime(feat_cell_lin)
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


def test_division_time_cycle_lin_default_time_step(cell_lin, feat_cycle_lin):
    """Test DivisionTime with CycleLineage and default time step."""
    calculator = DivisionTime(feat_cycle_lin)
    data = Data({1: cell_lin}, add_cycle_data=True)
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


def test_division_time_cycle_lin_custom_time_step(cell_lin, feat_cycle_lin):
    """Test DivisionTime with CycleLineage and custom time step."""
    calculator = DivisionTime(feat_cycle_lin, time_step=2.5)
    data = Data({1: cell_lin}, add_cycle_data=True)
    cycle_lin = data.cycle_data[1]
    # Complete cell cycles.
    assert calculator.compute(data, cycle_lin, nid=4) == 5.0  # division
    assert calculator.compute(data, cycle_lin, nid=8) == 5.0  # division
    assert calculator.compute(data, cycle_lin, nid=14) == 10.0  # division
    # Incomplete cell cycles.
    assert calculator.compute(data, cycle_lin, nid=2) == 2.5  # division
    assert calculator.compute(data, cycle_lin, nid=6) == 5.0  # leaf
    assert calculator.compute(data, cycle_lin, nid=10) == 2.5  # leaf
    assert calculator.compute(data, cycle_lin, nid=15) == 2.5  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(data, cycle_lin, nid=99)


# DivisionRate ################################################################


def test_division_rate_default_time_step(cell_lin, feat_cell_lin):
    """Test DivisionRate with default time step."""
    calculator = DivisionRate(feat_cell_lin)
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


def test_division_rate_custom_time_step(cell_lin, feat_cell_lin):
    """Test DivisionRate with a custom time step."""
    calculator = DivisionRate(feat_cell_lin, time_step=2.5)
    # Root.
    assert calculator.compute(Data({}), cell_lin, nid=1) == 1 / 2.5
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, nid=2) == 1 / 2.5
    assert calculator.compute(Data({}), cell_lin, nid=4) == 1 / 5.0
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, nid=6) == 1 / 5.0
    assert calculator.compute(Data({}), cell_lin, nid=10) == 1 / 2.5
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, nid=3) == 1 / 5.0
    assert calculator.compute(Data({}), cell_lin, nid=13) == 1 / 10.0
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_division_rate_gap(cell_lin, feat_cell_lin):
    """Test DivisionRate with a gap in the lineage."""
    # Create a lineage with a gap.
    cell_lin.remove_nodes_from([3, 12, 13])
    cell_lin.add_edges_from([(2, 4), (11, 14)])
    calculator = DivisionRate(feat_cell_lin)
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


def test_division_rate_from_division_time(cell_lin, feat_cell_lin):
    """Test DivisionRate from DivisionTime."""
    calculator = DivisionRate(feat_cell_lin, use_div_time=True)
    # Root.
    nid = 1
    cell_lin.nodes[nid]["division_time"] = 10
    assert calculator.compute(Data({}), cell_lin, nid) == 1 / 10
    # Divisions.
    nid = 2
    cell_lin.nodes[nid]["division_time"] = 20
    assert calculator.compute(Data({}), cell_lin, nid) == 1 / 20
    nid = 4
    cell_lin.nodes[nid]["division_time"] = 40
    assert calculator.compute(Data({}), cell_lin, nid) == 1 / 40
    nid = 14
    cell_lin.nodes[nid]["division_time"] = 140
    assert calculator.compute(Data({}), cell_lin, nid) == 1 / 140
    # Leaves.
    nid = 6
    cell_lin.nodes[nid]["division_time"] = 60
    assert calculator.compute(Data({}), cell_lin, nid) == 1 / 60
    nid = 10
    cell_lin.nodes[nid]["division_time"] = 100
    assert calculator.compute(Data({}), cell_lin, nid) == 1 / 100
    # Intermediate nodes.
    nid = 11
    cell_lin.nodes[nid]["division_time"] = 110
    assert calculator.compute(Data({}), cell_lin, nid) == 1 / 110
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, nid=99)


def test_division_rate_cycle_lin_default_time_step(cell_lin, feat_cycle_lin):
    """Test DivisionRate with CycleLineage and default time step."""
    calculator = DivisionRate(feat_cycle_lin)
    data = Data({1: cell_lin}, add_cycle_data=True)
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


def test_division_rate_cycle_lin_custom_time_step(cell_lin, feat_cycle_lin):
    """Test DivisionRate with CycleLineage and custom time step."""
    calculator = DivisionRate(feat_cycle_lin, time_step=2.5)
    data = Data({1: cell_lin}, add_cycle_data=True)
    cycle_lin = data.cycle_data[1]
    # Complete cell cycles.
    assert calculator.compute(data, cycle_lin, nid=4) == 1 / 5.0  # division
    assert calculator.compute(data, cycle_lin, nid=8) == 1 / 5.0  # division
    assert calculator.compute(data, cycle_lin, nid=14) == 1 / 10.0  # division
    # Incomplete cell cycles.
    assert calculator.compute(data, cycle_lin, nid=2) == 1 / 2.5  # division
    assert calculator.compute(data, cycle_lin, nid=6) == 1 / 5.0  # leaf
    assert calculator.compute(data, cycle_lin, nid=10) == 1 / 2.5  # leaf
    assert calculator.compute(data, cycle_lin, nid=15) == 1 / 2.5  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(data, cycle_lin, nid=99)
