#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for tracking feature classe from graph.features."""

import pytest

import networkx as nx

from pycellin.graph.features.tracking import (
    AbsoluteAge,
    RelativeAge,
    CellCycleCompleteness,
    DivisionTime,
    DivisionRate,
)
from pycellin.classes import Feature, Data, CellLineage, CycleLineage


# Fixtures ####################################################################


@pytest.fixture(scope="module")
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
        provenance="Pycellin",
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
        unit="um",
    )
    return Feature


@pytest.fixture
def cycle_lin(cell_lin):
    # Nothing special
    # , just a lineage.
    lineage = CycleLineage(cell_lin)
    return lineage


@pytest.fixture
def feat_cycle_lin():
    Feature(
        name="test_feature",
        description="test feature",
        provenance="Pycellin",
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
    assert calculator.compute(Data({}), cell_lin, noi=1) == 0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, noi=2) == 1
    assert calculator.compute(Data({}), cell_lin, noi=4) == 3
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, noi=6) == 5
    assert calculator.compute(Data({}), cell_lin, noi=10) == 6
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, noi=3) == 2
    assert calculator.compute(Data({}), cell_lin, noi=13) == 4
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(Data({}), cell_lin, noi=99)


def test_absolute_age_custom_time_step(cell_lin, feat_cell_lin):
    """Test AbsoluteAge with a custom time step."""
    calculator = AbsoluteAge(feat_cell_lin, time_step=2.5)
    # Root.
    assert calculator.compute(Data({}), cell_lin, noi=1) == 0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, noi=2) == 2.5
    assert calculator.compute(Data({}), cell_lin, noi=4) == 7.5
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, noi=6) == 12.5
    assert calculator.compute(Data({}), cell_lin, noi=10) == 15.0
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, noi=3) == 5.0
    assert calculator.compute(Data({}), cell_lin, noi=13) == 10.0
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(Data({}), cell_lin, noi=99)


# RelativeAge #################################################################


def test_relative_age_default_time_step(cell_lin, feat_cell_lin):
    """Test RelativeAge with default time step."""
    calculator = RelativeAge(feat_cell_lin)
    # Root.
    assert calculator.compute(Data({}), cell_lin, noi=1) == 0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, noi=2) == 1
    assert calculator.compute(Data({}), cell_lin, noi=4) == 1
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, noi=6) == 1
    assert calculator.compute(Data({}), cell_lin, noi=10) == 0
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, noi=3) == 0
    assert calculator.compute(Data({}), cell_lin, noi=13) == 2
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(Data({}), cell_lin, noi=99)


def test_relative_age_custom_time_step(cell_lin, feat_cell_lin):
    """Test RelativeAge with a custom time step."""
    calculator = RelativeAge(feat_cell_lin, time_step=2.5)
    # Root.
    assert calculator.compute(Data({}), cell_lin, noi=1) == 0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, noi=2) == 2.5
    assert calculator.compute(Data({}), cell_lin, noi=4) == 2.5
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, noi=6) == 2.5
    assert calculator.compute(Data({}), cell_lin, noi=10) == 0
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, noi=3) == 0
    assert calculator.compute(Data({}), cell_lin, noi=13) == 5.0
    # Non-existent node.
    with pytest.raises(KeyError):
        calculator.compute(Data({}), cell_lin, noi=99)


# CellCycleCompleteness #######################################################


def test_cell_cycle_completeness_cell_lin(cell_lin, feat_cell_lin):
    calculator = CellCycleCompleteness(feat_cell_lin)
    # Complete cell cycles.
    assert calculator.compute(Data({}), cell_lin, noi=4) is True  # division
    assert calculator.compute(Data({}), cell_lin, noi=14) is True  # division
    assert calculator.compute(Data({}), cell_lin, noi=7) is True  # intermediate
    assert calculator.compute(Data({}), cell_lin, noi=13) is True  # intermediate
    # Incomplete cell cycles.
    assert calculator.compute(Data({}), cell_lin, noi=1) is False  # root
    assert calculator.compute(Data({}), cell_lin, noi=6) is False  # leaf
    assert calculator.compute(Data({}), cell_lin, noi=10) is False  # leaf
    assert calculator.compute(Data({}), cell_lin, noi=2) is False  # division
    assert calculator.compute(Data({}), cell_lin, noi=5) is False  # intermediate
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, noi=99)


def test_cell_cycle_completeness_cycle_lin(cycle_lin, feat_cycle_lin):
    calculator = CellCycleCompleteness(feat_cycle_lin)
    # Complete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=4) is True  # division
    assert calculator.compute(Data({}), cycle_lin, noi=8) is True  # division
    assert calculator.compute(Data({}), cycle_lin, noi=14) is True  # division
    # Incomplete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=2) is False  # division
    assert calculator.compute(Data({}), cycle_lin, noi=6) is False  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=10) is False  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=15) is False  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(Data({}), cycle_lin, noi=99)


# DivisionTime ################################################################


def test_division_time_default_time_step(cell_lin, feat_cell_lin):
    """Test DivisionTime with default time step."""
    calculator = DivisionTime(feat_cell_lin)
    # Root.
    assert calculator.compute(Data({}), cell_lin, noi=1) == 2
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, noi=2) == 2
    assert calculator.compute(Data({}), cell_lin, noi=4) == 2
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, noi=6) == 2
    assert calculator.compute(Data({}), cell_lin, noi=10) == 1
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, noi=3) == 2
    assert calculator.compute(Data({}), cell_lin, noi=13) == 4
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, noi=99)


def test_division_time_custom_time_step(cell_lin, feat_cell_lin):
    """Test DivisionTime with a custom time step."""
    calculator = DivisionTime(feat_cell_lin, time_step=2.5)
    # Root.
    assert calculator.compute(Data({}), cell_lin, noi=1) == 5.0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, noi=2) == 5.0
    assert calculator.compute(Data({}), cell_lin, noi=4) == 5.0
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, noi=6) == 5.0
    assert calculator.compute(Data({}), cell_lin, noi=10) == 2.5
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, noi=3) == 5.0
    assert calculator.compute(Data({}), cell_lin, noi=13) == 10.0
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, noi=99)


def test_division_time_cycle_lin_default_time_step(cycle_lin, feat_cycle_lin):
    """Test DivisionTime with CycleLineage and default time step."""
    calculator = DivisionTime(feat_cycle_lin)
    # Complete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=4) == 2  # division
    assert calculator.compute(Data({}), cycle_lin, noi=8) == 2  # division
    assert calculator.compute(Data({}), cycle_lin, noi=14) == 4  # division
    # Incomplete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=2) == 2  # division
    assert calculator.compute(Data({}), cycle_lin, noi=6) == 2  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=10) == 1  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=15) == 1  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(Data({}), cycle_lin, noi=99)


def test_division_time_cycle_lin_custom_time_step(cycle_lin, feat_cycle_lin):
    """Test DivisionTime with CycleLineage and custom time step."""
    calculator = DivisionTime(feat_cycle_lin, time_step=2.5)
    # Complete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=4) == 5.0  # division
    assert calculator.compute(Data({}), cycle_lin, noi=8) == 5.0  # division
    assert calculator.compute(Data({}), cycle_lin, noi=14) == 10.0  # division
    # Incomplete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=2) == 5.0  # division
    assert calculator.compute(Data({}), cycle_lin, noi=6) == 5.0  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=10) == 2.5  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=15) == 2.5  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(Data({}), cycle_lin, noi=99)


# DivisionRate ################################################################


def test_division_rate_default_time_step(cell_lin, feat_cell_lin):
    """Test DivisionRate with default time step."""
    calculator = DivisionRate(feat_cell_lin)
    # Root.
    assert calculator.compute(Data({}), cell_lin, noi=1) == 1 / 2
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, noi=2) == 1 / 2
    assert calculator.compute(Data({}), cell_lin, noi=4) == 1 / 2
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, noi=6) == 1 / 2
    assert calculator.compute(Data({}), cell_lin, noi=10) == 1 / 1
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, noi=3) == 1 / 2
    assert calculator.compute(Data({}), cell_lin, noi=13) == 1 / 4
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, noi=99)


def test_division_rate_custom_time_step(cell_lin, feat_cell_lin):
    """Test DivisionRate with a custom time step."""
    calculator = DivisionRate(feat_cell_lin, time_step=2.5)
    # Root.
    assert calculator.compute(Data({}), cell_lin, noi=1) == 1 / 5.0
    # Divisions.
    assert calculator.compute(Data({}), cell_lin, noi=2) == 1 / 5.0
    assert calculator.compute(Data({}), cell_lin, noi=4) == 1 / 5.0
    # Leaves.
    assert calculator.compute(Data({}), cell_lin, noi=6) == 1 / 5.0
    assert calculator.compute(Data({}), cell_lin, noi=10) == 1 / 2.5
    # Intermediate nodes.
    assert calculator.compute(Data({}), cell_lin, noi=3) == 1 / 5.0
    assert calculator.compute(Data({}), cell_lin, noi=13) == 1 / 10.0
    # Non-existent node.
    with pytest.raises(KeyError, match="Cell 99 not in the lineage."):
        calculator.compute(Data({}), cell_lin, noi=99)


def test_division_rate_cycle_lin_default_time_step(cycle_lin, feat_cycle_lin):
    """Test DivisionRate with CycleLineage and default time step."""
    calculator = DivisionRate(feat_cycle_lin)
    # Complete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=4) == 1 / 2  # division
    assert calculator.compute(Data({}), cycle_lin, noi=8) == 1 / 2  # division
    assert calculator.compute(Data({}), cycle_lin, noi=14) == 1 / 4  # division
    # Incomplete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=2) == 1 / 2  # division
    assert calculator.compute(Data({}), cycle_lin, noi=6) == 1 / 2  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=10) == 1 / 1  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=15) == 1 / 1  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(Data({}), cycle_lin, noi=99)


def test_division_rate_cycle_lin_custom_time_step(cycle_lin, feat_cycle_lin):
    """Test DivisionRate with CycleLineage and custom time step."""
    calculator = DivisionRate(feat_cycle_lin, time_step=2.5)
    # Complete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=4) == 1 / 5.0  # division
    assert calculator.compute(Data({}), cycle_lin, noi=8) == 1 / 5.0  # division
    assert calculator.compute(Data({}), cycle_lin, noi=14) == 1 / 10.0  # division
    # Incomplete cell cycles.
    assert calculator.compute(Data({}), cycle_lin, noi=2) == 1 / 5.0  # division
    assert calculator.compute(Data({}), cycle_lin, noi=6) == 1 / 5.0  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=10) == 1 / 2.5  # leaf
    assert calculator.compute(Data({}), cycle_lin, noi=15) == 1 / 2.5  # leaf
    # Non-existent node.
    with pytest.raises(KeyError, match="Cycle 99 not in the lineage."):
        calculator.compute(Data({}), cycle_lin, noi=99)
