#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for Data class from data.py module."""

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
    """Test cases for Data._get_next_available_lineage_ID method."""

    def test_empty_data_positive_id(self):
        """Test that empty data returns 1 for positive ID."""
        data = Data({})
        result = data._get_next_available_lineage_ID(positive=True)
        assert result == 1

    def test_empty_data_negative_id(self):
        """Test that empty data returns -1 for negative ID."""
        data = Data({})
        result = data._get_next_available_lineage_ID(positive=False)
        assert result == -1

    def test_positive_id_with_positive_lineages(self):
        """Test positive ID generation with existing positive lineage IDs."""
        data = Data({1: CellLineage(lid=1), 5: CellLineage(lid=5), 3: CellLineage(lid=3)})
        result = data._get_next_available_lineage_ID(positive=True)
        assert result == 6  # max(1, 5, 3) + 1

    def test_negative_id_with_negative_lineages(self):
        """Test negative ID generation with existing negative lineage IDs."""
        data = Data({-1: CellLineage(lid=-1), -5: CellLineage(lid=-5), -3: CellLineage(lid=-3)})
        result = data._get_next_available_lineage_ID(positive=False)
        assert result == -6  # min(-1, -5, -3) - 1

    def test_positive_id_with_mixed_lineages(self):
        """Test positive ID generation with mixed positive and negative lineage IDs."""
        data = Data(
            {
                2: CellLineage(lid=2),
                -3: CellLineage(lid=-3),
                7: CellLineage(lid=7),
                -1: CellLineage(lid=-1),
            }
        )
        result = data._get_next_available_lineage_ID(positive=True)
        assert result == 8  # max(2, -3, 7, -1) + 1

    def test_negative_id_with_mixed_lineages(self):
        """Test negative ID generation with mixed positive and negative lineage IDs."""
        data = Data(
            {
                2: CellLineage(lid=2),
                -3: CellLineage(lid=-3),
                7: CellLineage(lid=7),
                -1: CellLineage(lid=-1),
            }
        )
        result = data._get_next_available_lineage_ID(positive=False)
        assert result == -4  # min(2, -3, 7, -1) - 1

    def test_positive_id_ensures_minimum_value(self):
        """Test that positive ID is at least 1, even with negative max."""
        data = Data({-5: CellLineage(lid=-5), -2: CellLineage(lid=-2)})
        result = data._get_next_available_lineage_ID(positive=True)
        assert result == 1  # max(-5, -2) + 1 = -1, but should be at least 1

    def test_negative_id_ensures_maximum_value(self):
        """Test that negative ID is at most -1, even with positive min."""
        data = Data({5: CellLineage(lid=5), 2: CellLineage(lid=2)})
        result = data._get_next_available_lineage_ID(positive=False)
        assert result == -1  # min(5, 2) - 1 = 1, but should be at most -1

    def test_single_positive_lineage(self):
        """Test with a single positive lineage."""
        data = Data({10: CellLineage(lid=10)})

        positive_result = data._get_next_available_lineage_ID(positive=True)
        assert positive_result == 11

        negative_result = data._get_next_available_lineage_ID(positive=False)
        assert negative_result == -1  # min(10) - 1 = 9, but should be at most -1

    def test_single_negative_lineage(self):
        """Test with a single negative lineage."""
        data = Data({-10: CellLineage(lid=-10)})

        positive_result = data._get_next_available_lineage_ID(positive=True)
        assert positive_result == 1  # max(-10) + 1 = -9, but should be at least 1

        negative_result = data._get_next_available_lineage_ID(positive=False)
        assert negative_result == -11
