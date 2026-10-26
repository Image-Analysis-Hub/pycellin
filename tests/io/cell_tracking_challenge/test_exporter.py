#!/usr/bin/env python3

"""Unit test for Cell Tracking Challenge file exporter."""

import numpy as np
import pytest

from pycellin.classes import CellLineage, Data, Model, PropsMetadata
from pycellin.classes.exceptions import UpdateRequiredError
from pycellin.io.cell_tracking_challenge.exporter import export_CTC_file
from pycellin.io.cell_tracking_challenge.loader import load_CTC_file
from pycellin.properties.core import (
    create_cell_id_property,
    create_lineage_id_property,
    create_timepoint_property,
)

# Helpers #####################################################################


def _create_model(timepoints: list[int]) -> Model:
    """Create a model with a lineage of linked cells, one per timepoint given."""
    lin = CellLineage()
    for cid, timepoint in enumerate(timepoints, start=1):
        lin.add_node(cid, timepoint=timepoint, cell_id=cid, lineage_id=1)
        if cid > 1:
            lin.add_edge(cid - 1, cid)
    lin.graph["lineage_id"] = 1

    props_metadata = PropsMetadata()
    props_metadata._add_prop(create_timepoint_property())
    props_metadata._add_prop(create_cell_id_property())
    props_metadata._add_prop(create_lineage_id_property())
    return Model(
        data=Data({1: lin}),
        props_metadata=props_metadata,
        reference_time_property="timepoint",
    )


# Fixtures ####################################################################


@pytest.fixture
def simple_model():
    """Create a model with a lineage of two cells."""
    return _create_model([0, 1])


# Test classes ###############################################################


class TestExportCTCFile:
    """Test cases for export_CTC_file function."""

    def test_model_requiring_update_raises(self, simple_model, tmp_path):
        """Test that a model requiring an update is not exported."""
        simple_model.prepare_full_data_update()
        with pytest.raises(UpdateRequiredError, match="before exporting"):
            export_CTC_file(simple_model, tmp_path / "tracks.txt")
        assert not (tmp_path / "tracks.txt").exists()

    def test_frames_are_timepoints_by_default(self, simple_model, tmp_path):
        """Test that without frame offset, the frames are the timepoints."""
        export_CTC_file(simple_model, tmp_path / "tracks.txt")
        assert (tmp_path / "tracks.txt").read_text() == "1 0 1 0\n"

    @pytest.mark.parametrize("frame_offset", [5, np.int64(5)])
    def test_frame_offset(self, simple_model, tmp_path, frame_offset):
        """Test that a frame offset, Python or NumPy integer, shifts the frames."""
        export_CTC_file(
            simple_model, tmp_path / "tracks.txt", frame_offset=frame_offset
        )
        assert (tmp_path / "tracks.txt").read_text() == "1 5 6 0\n"

    def test_frame_offset_with_gap(self, tmp_path):
        """Test that a gap still splits the track when the frames are shifted."""
        model = _create_model([0, 1, 3])
        export_CTC_file(model, tmp_path / "tracks.txt", frame_offset=5)
        assert (tmp_path / "tracks.txt").read_text() == "1 5 6 0\n2 8 8 1\n"

    def test_frame_offset_for_negative_timepoints(self, tmp_path):
        """Test that a frame offset can bring negative timepoints to frame 0."""
        model = _create_model([-2, -1])
        export_CTC_file(model, tmp_path / "tracks.txt", frame_offset=2)
        assert (tmp_path / "tracks.txt").read_text() == "1 0 1 0\n"

    @pytest.mark.parametrize(
        "timepoints, frame_offset", [([0, 1], -1), ([-2, -1], 0), ([-2, -1], 1)]
    )
    def test_negative_frames_raise(self, tmp_path, timepoints, frame_offset):
        """Test that negative frames raise, giving the smallest valid frame offset."""
        model = _create_model(timepoints)
        min_offset = -timepoints[0]
        with pytest.raises(ValueError, match=f"frame_offset of at least {min_offset}"):
            export_CTC_file(model, tmp_path / "tracks.txt", frame_offset=frame_offset)
        assert not (tmp_path / "tracks.txt").exists()

    @pytest.mark.parametrize("frame_offset", [5.0, "5", True, None])
    def test_non_integer_frame_offset_raises(
        self, simple_model, tmp_path, frame_offset
    ):
        """Test that a frame offset that isn't an integer raises."""
        with pytest.raises(TypeError, match="'frame_offset' must be an integer"):
            export_CTC_file(
                simple_model, tmp_path / "tracks.txt", frame_offset=frame_offset
            )
        assert not (tmp_path / "tracks.txt").exists()

    def test_CTC_round_trip_with_frame_offset(self, tmp_path):
        """Test that a CTC file starting after frame 0 is written back unchanged."""
        tracks = "1 5 9 0\n2 10 12 1\n3 10 12 1\n"
        (tmp_path / "in.txt").write_text(tracks)
        model = load_CTC_file(tmp_path / "in.txt")
        # Frame offset as the docstring gives it: the frame of a cell minus its
        # timepoint.
        df = model.to_cell_dataframe()
        frame_offset = (df["frame"] - df["timepoint"]).iloc[0]
        export_CTC_file(model, tmp_path / "out.txt", frame_offset=frame_offset)
        assert (tmp_path / "out.txt").read_text() == tracks
