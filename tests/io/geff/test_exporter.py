#!/usr/bin/env python3

"""Unit test for GEFF file exporter."""

import pytest
import geff_spec

from pycellin.classes import CellLineage
from pycellin.io.geff.exporter import (
    _find_node_overlaps,
    _get_next_available_id,
    _relabel_nodes,
    _solve_node_overlaps,
    _build_axes,
    _build_display_hints,
    _build_props_metadata,
    _build_geff_metadata,
    export_GEFF,
)


# Fixtures ####################################################################


@pytest.fixture
def lineage1():
    lin = CellLineage()
    lin.add_nodes_from([1, 2, 3, 4, 5])
    lin.add_edges_from([(1, 2), (2, 3), (3, 4), (3, 5)])
    lin.graph["lineage_ID"] = 0
    return lin


@pytest.fixture
def lineage2():
    lin = CellLineage()
    lin.add_nodes_from([10, 11, 12, 13])
    lin.add_edges_from([(10, 11), (11, 12), (12, 13)])
    lin.graph["lineage_ID"] = 1
    return lin


@pytest.fixture
def lineage3():
    lin = CellLineage()
    lin.add_nodes_from([20, 21, 22])
    lin.add_edges_from([(20, 21), (21, 22)])
    lin.graph["lineage_ID"] = 2
    return lin


# Test Classes ################################################################


class TestFindNodeOverlaps:
    """Test cases for _find_node_overlaps function."""

    def test_empty_lineages(self):
        """Test with empty list of lineages."""
        overlaps = _find_node_overlaps([])
        assert overlaps == {}

    def test_single_lineage(self, lineage1):
        """Test with single lineage with no overlaps."""
        overlaps = _find_node_overlaps([lineage1])
        assert overlaps == {}

    def test_no_overlaps(self, lineage1, lineage2, lineage3):
        """Test multiple lineages with no overlapping node IDs."""
        overlaps = _find_node_overlaps([lineage1, lineage2, lineage3])
        assert overlaps == {}

    def test_single_overlap(self, lineage1, lineage2):
        """Test lineages with a single overlapping node ID."""
        lineage2.add_node(3)
        overlaps = _find_node_overlaps([lineage1, lineage2])
        assert overlaps == {3: [0, 1]}  # node 3 appears in lineages 0 and 1

    def test_multiple_overlaps(self, lineage1, lineage2, lineage3):
        """Test lineages with multiple overlapping node IDs."""
        lineage2.add_nodes_from([3, 5])
        lineage3.add_nodes_from([4, 5])
        overlaps = _find_node_overlaps([lineage1, lineage2, lineage3])
        assert overlaps == {3: [0, 1], 4: [0, 2], 5: [0, 1, 2]}


class TestGetNextAvailableId:
    """Test cases for _get_next_available_id function."""

    def test_empty_lineages(self):
        """Test with empty list of lineages."""
        next_id = _get_next_available_id([])
        assert next_id == 0

    def test_single_empty_lineage(self):
        """Test with a single empty lineage."""
        lineage = CellLineage()
        lineage.graph["lineage_ID"] = 0
        next_id = _get_next_available_id([lineage])
        assert next_id == 0

    def test_single_lineage(self, lineage1):
        """Test with single lineage."""
        next_id = _get_next_available_id([lineage1])
        assert next_id == 6

    def test_multiple_lineages_with_overlap(self, lineage1, lineage2, lineage3):
        """Test with lineages that have overlaps."""
        lineage2.add_nodes_from([3, 5])
        next_id = _get_next_available_id([lineage1, lineage2, lineage3])
        assert next_id == 23

    def test_negative_node_ids(self):
        """Test with lineages that have negative node IDs."""
        lin = CellLineage()
        lin.add_nodes_from([-1, -2, -3, -4, -5])
        next_id = _get_next_available_id([lin])
        assert next_id == 0


class TestRelabelNodes:
    """Test cases for _relabel_nodes function."""

    def test_no_overlaps(self, lineage1, lineage2):
        """Test relabeling with no overlapping node IDs."""
        overlaps = {}
        _relabel_nodes([lineage1, lineage2], overlaps)
        assert set(lineage1.nodes()) == {1, 2, 3, 4, 5}
        assert set(lineage2.nodes()) == {10, 11, 12, 13}

    def test_single_overlap(self, lineage1, lineage2):
        """Test relabeling with a single overlapping node ID."""
        lineage2.add_node(3)
        overlaps = {3: [0, 1]}
        _relabel_nodes([lineage1, lineage2], overlaps)
        assert set(lineage1.nodes()) == {1, 2, 3, 4, 5}
        assert set(lineage2.nodes()) == {10, 11, 12, 13, 14}

    def test_multiple_overlaps(self, lineage1, lineage2, lineage3):
        """Test relabeling with multiple overlapping node IDs."""
        lineage2.add_nodes_from([3, 5])
        lineage3.add_nodes_from([4, 5])
        overlaps = {3: [0, 1], 4: [0, 2], 5: [0, 1, 2]}
        _relabel_nodes([lineage1, lineage2, lineage3], overlaps)
        assert set(lineage1.nodes()) == {1, 2, 3, 4, 5}
        assert set(lineage2.nodes()) == {10, 11, 12, 13, 23, 25}
        assert set(lineage3.nodes()) == {20, 21, 22, 24, 26}


class TestSolveNodeOverlaps:
    """Test cases for _solve_node_overlaps function."""

    def test_empty_lineages(self):
        """Test with empty list of lineages."""
        _solve_node_overlaps([])

    def test_no_overlaps(self, lineage1, lineage2):
        """Test with lineages that have no overlapping node IDs."""
        lin1_nodes = set(lineage1.nodes())
        lin2_nodes = set(lineage2.nodes())
        _solve_node_overlaps([lineage1, lineage2])
        assert set(lineage1.nodes()) == lin1_nodes
        assert set(lineage2.nodes()) == lin2_nodes

    def test_overlaps(self, lineage1, lineage2, lineage3):
        """Test with lineages that have overlapping node IDs."""
        lineage2.add_nodes_from([3, 5])
        lineage3.add_nodes_from([4, 5])
        _solve_node_overlaps([lineage1, lineage2, lineage3])
        assert set(lineage1.nodes()) == {1, 2, 3, 4, 5}
        assert set(lineage2.nodes()) == {10, 11, 12, 13, 23, 25}
        assert set(lineage3.nodes()) == {20, 21, 22, 24, 26}


class TestBuildAxes:
    """Test cases for _build_axes function."""

    def test_only_time_axis(self):
        """Test building axes with only time axis (no spatial axes)."""
        axes = _build_axes(
            has_x=False,
            has_y=False,
            has_z=False,
            time_prop="Time",
            space_unit=None,
            time_unit=None,
        )
        assert len(axes) == 1
        assert axes[0] == geff_spec.Axis(name="Time", type="time", unit=None)

    def test_xy_axes(self):
        """Test building axes with X and Y spatial axes."""
        axes = _build_axes(
            has_x=True,
            has_y=True,
            has_z=False,
            time_prop="Time",
            space_unit="micrometer",
            time_unit="second",
        )
        assert len(axes) == 3
        assert axes[0] == geff_spec.Axis(name="cell_x", type="space", unit="micrometer")
        assert axes[1] == geff_spec.Axis(name="cell_y", type="space", unit="micrometer")
        assert axes[2] == geff_spec.Axis(name="Time", type="time", unit="second")

    def test_xyz_axes(self):
        """Test building axes with X, Y, and Z spatial axes."""
        axes = _build_axes(
            has_x=True,
            has_y=True,
            has_z=True,
            time_prop="Time",
            space_unit="pixel",
            time_unit="second",
        )
        assert len(axes) == 4
        assert axes[0] == geff_spec.Axis(name="cell_x", type="space", unit="pixel")
        assert axes[1] == geff_spec.Axis(name="cell_y", type="space", unit="pixel")
        assert axes[2] == geff_spec.Axis(name="cell_z", type="space", unit="pixel")
        assert axes[3] == geff_spec.Axis(name="Time", type="time", unit="second")


class TestBuildDisplayHints:
    """Test cases for _build_display_hints function."""

    def test_no_xy_axes_returns_none(self):
        """Test that None is returned when X or Y axis is missing."""
        # No X axis
        hints = _build_display_hints(
            has_x=False,
            has_y=True,
            has_z=False,
            time_prop="frame",
        )
        assert hints is None

        # No X and Y axes
        hints = _build_display_hints(
            has_x=False,
            has_y=False,
            has_z=False,
            time_prop="frame",
        )
        assert hints is None

    def test_xy_axes_without_z(self):
        """Test display hints with X and Y axes but no Z axis."""
        hints = _build_display_hints(
            has_x=True,
            has_y=True,
            has_z=False,
            time_prop="time",
        )
        assert hints is not None
        assert hints.display_horizontal == "cell_x"
        assert hints.display_vertical == "cell_y"
        assert hints.display_time == "time"
        assert not hasattr(hints, "display_depth") or hints.display_depth is None

    def test_xyz_axes(self):
        """Test display hints with X, Y, and Z axes."""
        hints = _build_display_hints(
            has_x=True,
            has_y=True,
            has_z=True,
            time_prop="frame_id",
        )
        assert hints is not None
        assert hints.display_horizontal == "cell_x"
        assert hints.display_vertical == "cell_y"
        assert hints.display_depth == "cell_z"
        assert hints.display_time == "frame_id"
