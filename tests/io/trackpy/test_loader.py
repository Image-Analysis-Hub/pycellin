#!/usr/bin/env python3

"""Unit tests for the trackpy loader from pycellin.io.trackpy."""

import pandas as pd
import pytest

from pycellin.io.trackmate.exporter import export_TrackMate_XML
from pycellin.io.trackmate.loader import load_TrackMate_XML
from pycellin.io.trackpy.loader import load_trackpy_dataframe

# Fixtures ####################################################################


@pytest.fixture
def trackpy_df():
    """A trackpy DataFrame with one particle followed over two frames."""
    return pd.DataFrame(
        {"frame": [0, 1], "particle": [0, 0], "x": [1.0, 2.0], "y": [3.0, 4.0]}
    )


@pytest.fixture
def trackpy_full_df(trackpy_df):
    """The same DataFrame with the other columns written by trackpy."""
    return trackpy_df.assign(
        mass=[100.0, 110.0],
        size=[2.0, 2.1],
        ecc=[0.1, 0.2],
        signal=[20.0, 22.0],
        raw_mass=[300.0, 310.0],
        ep=[0.05, 0.06],
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

    def test_trackpy_columns_declared(self, trackpy_full_df):
        """The columns written by trackpy are declared, with a description, and the
        sizes and static errors in the unit of the coordinates."""
        model = load_trackpy_dataframe(trackpy_full_df, space_unit="micrometer")

        for column in ("particle", "mass", "size", "ecc", "signal", "raw_mass", "ep"):
            prop = model.get_property(column)
            assert prop is not None, column
            assert prop.provenance == "trackpy"
            assert prop.description != "Column of the trackpy DataFrame"
        assert model.get_property("particle").dtype == "int"
        assert model.get_property("mass").dtype == "float"
        assert model.get_property("size").unit == "micrometer"
        assert model.get_property("ep").unit == "micrometer"
        assert model.get_property("mass").unit is None

    def test_integer_column_stays_integer(self, trackpy_df):
        """In a DataFrame of numbers only, an integer column stays integer."""
        trackpy_df["label"] = [5, 6]
        model = load_trackpy_dataframe(trackpy_df)

        assert model.get_property("label").dtype == "int"
        (lin,) = model.data.cell_data.values()
        labels = [lin.nodes[n]["label"] for n in sorted(lin.nodes)]
        assert labels == [5, 6]
        assert all(type(label) is int for label in labels)

    def test_other_columns_declared_with_their_dtype(self, trackpy_df):
        """Text and boolean columns are declared with their data type."""
        trackpy_df["condition"] = ["control", None]
        trackpy_df["selected"] = [True, False]
        model = load_trackpy_dataframe(trackpy_df)

        assert model.get_property("condition").dtype == "str"
        assert model.get_property("selected").dtype == "bool"

    def test_cells_linked_by_particle_and_frame(self):
        """Cells of a particle are linked by ascending frame, across gaps, whatever
        the order of the rows."""
        df = pd.DataFrame(
            {
                "frame": [3, 0, 0, 1, 1],
                "particle": [0, 1, 0, 0, 1],
                "x": [0.0, 1.0, 2.0, 3.0, 4.0],
                "y": [0.0, 1.0, 2.0, 3.0, 4.0],
            }
        )
        model = load_trackpy_dataframe(df)

        edges = {
            edge for lin in model.data.cell_data.values() for edge in lin.edges
        }
        # Rows 2 -> 3 -> 0 for particle 0, rows 1 -> 4 for particle 1.
        assert edges == {(2, 3), (3, 0), (1, 4)}

    def test_TrackMate_round_trip(self, trackpy_full_df, tmp_path):
        """A trackpy model exported to TrackMate can be loaded back, with its
        trackpy columns."""
        model = load_trackpy_dataframe(trackpy_full_df)
        xml_path = tmp_path / "trackpy.xml"
        export_TrackMate_XML(model, xml_path, units={"space": "pixel", "time": "frame"})

        reloaded = load_TrackMate_XML(xml_path)

        assert reloaded.get_property("particle").dtype == "int"
        (lin,) = reloaded.data.cell_data.values()
        masses = sorted(attrs["mass"] for _, attrs in lin.nodes(data=True))
        assert masses == [100.0, 110.0]
