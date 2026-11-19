#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for Data class from data.py module."""

import pytest

from pycellin.classes import CellLineage
from pycellin.classes.data import Data


class TestNumberOfLineages:
    """Test cases for Data.number_of_lineages property."""

    def test_empty_data(self):
        """Test that empty data returns 0 lineages."""
        data = Data({})
        assert data.number_of_lineages() == 0

    def test_single_lineage(self):
        """Test that data with one lineage returns 1."""
        data = Data({1: CellLineage()})
        assert data.number_of_lineages() == 1

    def test_multiple_lineages(self):
        """Test that data with multiple lineages returns correct count."""
        data = Data({1: CellLineage(), 2: CellLineage(), -3: CellLineage()})
        assert data.number_of_lineages() == 3


class TestDataGetNextAvailableLineageID:
    """Test cases for Data._get_next_available_lineage_id method."""

    def test_empty_data_positive_id(self):
        """Test that empty data returns 1 for positive ID."""
        data = Data({})
        result = data._get_next_available_lineage_id(positive=True)
        assert result == 1

    def test_empty_data_negative_id(self):
        """Test that empty data returns -1 for negative ID."""
        data = Data({})
        result = data._get_next_available_lineage_id(positive=False)
        assert result == -1

    def test_positive_id_with_positive_lineages(self):
        """Test positive ID generation with existing positive lineage IDs."""
        data = Data(
            {
                1: CellLineage(lineage_id=1),
                5: CellLineage(lineage_id=5),
                3: CellLineage(lineage_id=3),
            }
        )
        result = data._get_next_available_lineage_id(positive=True)
        assert result == 6  # max(1, 5, 3) + 1

    def test_negative_id_with_negative_lineages(self):
        """Test negative ID generation with existing negative lineage IDs."""
        data = Data(
            {
                -1: CellLineage(lineage_id=-1),
                -5: CellLineage(lineage_id=-5),
                -3: CellLineage(lineage_id=-3),
            }
        )
        result = data._get_next_available_lineage_id(positive=False)
        assert result == -6  # min(-1, -5, -3) - 1

    def test_positive_id_with_mixed_lineages(self):
        """Test positive ID generation with mixed positive and negative lineage IDs."""
        data = Data(
            {
                2: CellLineage(lineage_id=2),
                -3: CellLineage(lineage_id=-3),
                7: CellLineage(lineage_id=7),
                -1: CellLineage(lineage_id=-1),
            }
        )
        result = data._get_next_available_lineage_id(positive=True)
        assert result == 8  # max(2, -3, 7, -1) + 1

    def test_negative_id_with_mixed_lineages(self):
        """Test negative ID generation with mixed positive and negative lineage IDs."""
        data = Data(
            {
                2: CellLineage(lineage_id=2),
                -3: CellLineage(lineage_id=-3),
                7: CellLineage(lineage_id=7),
                -1: CellLineage(lineage_id=-1),
            }
        )
        result = data._get_next_available_lineage_id(positive=False)
        assert result == -4  # min(2, -3, 7, -1) - 1

    def test_positive_id_ensures_minimum_value(self):
        """Test that positive ID is at least 1, even with negative max."""
        data = Data({-5: CellLineage(lineage_id=-5), -2: CellLineage(lineage_id=-2)})
        result = data._get_next_available_lineage_id(positive=True)
        assert result == 1  # max(-5, -2) + 1 = -1, but should be at least 1

    def test_negative_id_ensures_maximum_value(self):
        """Test that negative ID is at most -1, even with positive min."""
        data = Data({5: CellLineage(lineage_id=5), 2: CellLineage(lineage_id=2)})
        result = data._get_next_available_lineage_id(positive=False)
        assert result == -1  # min(5, 2) - 1 = 1, but should be at most -1

    def test_single_positive_lineage(self):
        """Test with a single positive lineage."""
        data = Data({10: CellLineage(lineage_id=10)})

        positive_result = data._get_next_available_lineage_id(positive=True)
        assert positive_result == 11

        negative_result = data._get_next_available_lineage_id(positive=False)
        assert negative_result == -1  # min(10) - 1 = 9, but should be at most -1

    def test_single_negative_lineage(self):
        """Test with a single negative lineage."""
        data = Data({-10: CellLineage(lineage_id=-10)})

        positive_result = data._get_next_available_lineage_id(positive=True)
        assert positive_result == 1  # max(-10) + 1 = -9, but should be at least 1

        negative_result = data._get_next_available_lineage_id(positive=False)
        assert negative_result == -11


class TestGetClosestCells:
    """Test cases for Data.get_closest_cell() and Data.get_closest_cells()."""

    @pytest.fixture()
    def data(self):
        # At timepoint 0: cell 1 at (0, 0), cell 2 at (3, 4) and cell 10 at (6, 8),
        # at distances 5 and 10 from cell 1. At timepoint 1: cell 3 at (1, 0).
        lin1 = CellLineage(lineage_id=1)
        lin1.add_node(1, timepoint=0, cell_x=0.0, cell_y=0.0)
        lin1.add_node(2, timepoint=0, cell_x=3.0, cell_y=4.0)
        lin1.add_node(3, timepoint=1, cell_x=1.0, cell_y=0.0)
        lin2 = CellLineage(lineage_id=2)
        lin2.add_node(10, timepoint=0, cell_x=6.0, cell_y=8.0)
        return Data({1: lin1, 2: lin2})

    def test_sorted_by_distance(self, data):
        """Test that the cells at the same timepoint come by increasing distance."""
        lin1, lin2 = data.cell_lineages[1], data.cell_lineages[2]
        assert data.get_closest_cells(1, lin1) == [(2, lin1), (10, lin2)]
        assert data.get_closest_cell(1, lin1) == (2, lin1)

    def test_radius_time_window_and_lineages(self, data):
        """Test that the radius, time window and lineages to search are applied."""
        lin1, lin2 = data.cell_lineages[1], data.cell_lineages[2]
        assert data.get_closest_cells(1, lin1, radius=6) == [(2, lin1)]
        after = data.get_closest_cells(1, lin1, time_window=1, time_window_type="after")
        assert after == [(3, lin1), (2, lin1), (10, lin2)]
        assert data.get_closest_cells(1, lin1, lineages_to_search=[lin2]) == [
            (10, lin2)
        ]
        assert data.get_closest_cell(3, lin1) is None

    def test_3d_positions(self):
        """Test that cell_z counts in the distances when the cells have it."""
        lineage = CellLineage(lineage_id=1)
        lineage.add_node(1, timepoint=0, cell_x=0.0, cell_y=0.0, cell_z=0.0)
        lineage.add_node(2, timepoint=0, cell_x=0.0, cell_y=3.0, cell_z=0.0)
        lineage.add_node(3, timepoint=0, cell_x=0.0, cell_y=1.0, cell_z=5.0)
        data = Data({1: lineage})
        assert data.get_closest_cells(1, lineage) == [(2, lineage), (3, lineage)]

    def test_border_reference_not_implemented(self, data):
        """Test that the border reference raises instead of being ignored."""
        with pytest.raises(NotImplementedError):
            data.get_closest_cells(1, data.cell_lineages[1], reference="border")
