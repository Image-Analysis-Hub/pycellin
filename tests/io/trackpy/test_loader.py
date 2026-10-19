#!/usr/bin/env python3

"""Unit tests for the trackpy loader from pycellin.io.trackpy."""

import pandas as pd
import pytest

from pycellin.io.trackpy.loader import load_trackpy_dataframe

# Fixtures ####################################################################


@pytest.fixture
def trackpy_df():
    """A trackpy DataFrame with one particle followed over two frames."""
    return pd.DataFrame(
        {"frame": [0, 1], "particle": [0, 0], "x": [1.0, 2.0], "y": [3.0, 4.0]}
    )


# Test Classes ################################################################


class TestLoadTrackpyDataframe:
    """Test cases for load_trackpy_dataframe function."""

    def test_cell_id_column_raises(self, trackpy_df):
        """A 'cell_id' column would be overwritten by pycellin: raise."""
        trackpy_df["cell_id"] = [5, 6]
        with pytest.raises(ValueError, match=r"column\(s\) \['cell_id'\]"):
            load_trackpy_dataframe(trackpy_df)

    def test_lineage_id_column_raises(self, trackpy_df):
        """A 'lineage_id' column would be overwritten by pycellin: raise."""
        trackpy_df["lineage_id"] = [7, 7]
        with pytest.raises(ValueError, match=r"column\(s\) \['lineage_id'\]"):
            load_trackpy_dataframe(trackpy_df)

    def test_timepoint_column_raises(self, trackpy_df):
        """A 'timepoint' column would be overwritten by pycellin: raise."""
        trackpy_df["timepoint"] = [10, 11]
        with pytest.raises(ValueError, match=r"column\(s\) \['timepoint'\]"):
            load_trackpy_dataframe(trackpy_df)

    def test_no_reserved_column(self, trackpy_df):
        """Without reserved columns, pycellin creates its own properties."""
        model = load_trackpy_dataframe(trackpy_df)
        (lin,) = model.data.cell_data.values()
        assert [lin.nodes[n]["cell_id"] for n in sorted(lin.nodes)] == [0, 1]
        assert all(lin.nodes[n]["lineage_id"] == lin.graph["lineage_id"] for n in lin)
