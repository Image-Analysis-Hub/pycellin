#!/usr/bin/env python3

"""Unit test for GEFF file exporter."""

import pytest
import geff_spec

from pycellin.classes import CellLineage, Property
from pycellin.graph.properties.core import (
    create_cell_coord_property,
    create_timepoint_property,
)
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


@pytest.fixture
def node_props():
    """Create a dictionary of node properties for testing."""
    return {
        "timepoint": create_timepoint_property(provenance="Test"),
        "cell_x": create_cell_coord_property(
            axis="x", unit="micrometer", provenance="Test"
        ),
        "cell_y": create_cell_coord_property(
            axis="y", unit="micrometer", provenance="Test"
        ),
        "cell_z": create_cell_coord_property(
            axis="z", unit="micrometer", provenance="Test"
        ),
        "POSITION_T": Property(
            identifier="POSITION_T",
            name="Position T",
            description="Time in seconds",
            provenance="Test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
            unit="second",
        ),
        "channel_1": Property(
            identifier="channel_1",
            name="Channel 1",
            description="Channel 1 intensity",
            provenance="Test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
            unit=None,
        ),
        "channel_2": Property(
            identifier="channel_2",
            name="Channel 2",
            description="Channel 2 intensity",
            provenance="Test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
            unit=None,
        ),
    }


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

    def test_one_time_axis(self, node_props):
        """Test building axes with only time axis (no spatial or channel axes)."""
        axes = _build_axes(
            node_props=node_props,
            time_axes=["timepoint"],
            space_axes=None,
            channel_axes=None,
        )
        assert len(axes) == 1
        assert axes[0] == geff_spec.Axis(name="timepoint", type="time", unit=None)

    def test_multiple_time_axes(self, node_props):
        """Test building axes with multiple time axes."""
        axes = _build_axes(
            node_props=node_props,
            time_axes=["timepoint", "POSITION_T"],
            space_axes=None,
            channel_axes=None,
        )
        assert len(axes) == 2
        assert axes[0] == geff_spec.Axis(name="timepoint", type="time", unit=None)
        assert axes[1] == geff_spec.Axis(name="POSITION_T", type="time", unit="second")

    def test_time_and_space_axes(self, node_props):
        """Test building axes with time and X, Y, Z spatial axes."""
        axes = _build_axes(
            node_props=node_props,
            time_axes=["POSITION_T"],
            space_axes=["cell_x", "cell_y", "cell_z"],
            channel_axes=None,
        )
        assert len(axes) == 4
        assert axes[0] == geff_spec.Axis(name="POSITION_T", type="time", unit="second")
        assert axes[1] == geff_spec.Axis(name="cell_x", type="space", unit="micrometer")
        assert axes[2] == geff_spec.Axis(name="cell_y", type="space", unit="micrometer")
        assert axes[3] == geff_spec.Axis(name="cell_z", type="space", unit="micrometer")

    def test_time_space_and_channel_axes(self, node_props):
        """Test building axes with time, space, and channel axes."""
        axes = _build_axes(
            node_props=node_props,
            time_axes=["timepoint"],
            space_axes=["cell_x", "cell_y"],
            channel_axes=["channel_1", "channel_2"],
        )
        assert len(axes) == 5
        assert axes[0] == geff_spec.Axis(name="timepoint", type="time", unit=None)
        assert axes[1] == geff_spec.Axis(name="cell_x", type="space", unit="micrometer")
        assert axes[2] == geff_spec.Axis(name="cell_y", type="space", unit="micrometer")
        assert axes[3] == geff_spec.Axis(name="channel_1", type="channel")
        assert axes[4] == geff_spec.Axis(name="channel_2", type="channel")

    def test_unknown_time_property_raises_error(self, node_props):
        """Test that unknown time property raises ValueError."""
        with pytest.raises(ValueError, match="Unknown node property 'unknown_time'"):
            _build_axes(
                node_props=node_props,
                time_axes=["unknown_time"],
                space_axes=None,
                channel_axes=None,
            )

    def test_unknown_space_property_raises_error(self, node_props):
        """Test that unknown space property raises ValueError."""
        with pytest.raises(ValueError, match="Unknown node property 'unknown_space'"):
            _build_axes(
                node_props=node_props,
                time_axes=["timepoint"],
                space_axes=["cell_x", "unknown_space"],
                channel_axes=None,
            )

    def test_unknown_channel_property_raises_error(self, node_props):
        """Test that unknown channel property raises ValueError."""
        with pytest.raises(ValueError, match="Unknown node property 'unknown_channel'"):
            _build_axes(
                node_props=node_props,
                time_axes=["timepoint"],
                space_axes=None,
                channel_axes=["unknown_channel"],
            )


class TestBuildDisplayHints:
    """Test cases for _build_display_hints function."""

    def test_no_space_axes_returns_none(self):
        """Test that None is returned when space_axes is None."""
        hints = _build_display_hints(
            time_axis="timepoint",
            space_axes=None,
        )
        assert hints is None

    def test_single_space_axis_returns_none(self):
        """Test that None is returned when there's only one space axis."""
        hints = _build_display_hints(
            time_axis="timepoint",
            space_axes=["cell_x"],
        )
        assert hints is None

    def test_two_space_axes(self):
        """Test display hints with two space axes (horizontal and vertical)."""
        hints_obtained = _build_display_hints(
            time_axis="POSITION_T",
            space_axes=["cell_x", "cell_y"],
        )
        hints_expected = geff_spec.DisplayHint(
            display_horizontal="cell_x",
            display_vertical="cell_y",
            display_depth=None,
            display_time="POSITION_T",
        )
        assert hints_obtained == hints_expected

    def test_three_space_axes(self):
        """Test display hints with three space axes (horizontal, vertical, and depth)."""
        hints_obtained = _build_display_hints(
            time_axis="timepoint",
            space_axes=["cell_x", "cell_y", "cell_z"],
        )
        hints_expected = geff_spec.DisplayHint(
            display_horizontal="cell_x",
            display_vertical="cell_y",
            display_depth="cell_z",
            display_time="timepoint",
        )
        assert hints_obtained == hints_expected

    def test_more_than_three_space_axes(self):
        """Test display hints with more than three space axes (only first three used)."""
        hints_obtained = _build_display_hints(
            time_axis="time",
            space_axes=["x", "y", "z", "w"],
        )
        hints_expected = geff_spec.DisplayHint(
            display_horizontal="x",
            display_vertical="y",
            display_depth="z",
            display_time="time",
        )
        assert hints_obtained == hints_expected
