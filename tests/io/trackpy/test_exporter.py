#!/usr/bin/env python3

"""Unit test for trackpy DataFrame exporter."""

import pytest

from pycellin.classes import CellLineage, Data, Model, Property, PropsMetadata
from pycellin.classes.exceptions import UpdateRequiredError
from pycellin.io.trackpy.exporter import export_trackpy_dataframe
from pycellin.properties.core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_lineage_id_property,
    create_timepoint_property,
)
from pycellin.properties.morphology import create_cell_contour_property

# Fixtures ####################################################################


@pytest.fixture
def simple_model():
    """Create a model with a lineage of two cells."""
    lin = CellLineage()
    lin.add_node(1, timepoint=0, cell_id=1, lineage_id=1)
    lin.add_node(2, timepoint=1, cell_id=2, lineage_id=1)
    lin.add_edge(1, 2)
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


@pytest.fixture
def model_with_positions():
    """Create a model with two lineages of two cells each, with 2D positions.

    The cells also have a contour and an outdated trackpy `particle` value, which the
    export must not keep.
    """
    lineages = {}
    for lin_id, cell_ids in [(1, [1, 2]), (2, [3, 4])]:
        lin = CellLineage()
        for timepoint, cell_id in enumerate(cell_ids):
            lin.add_node(
                cell_id,
                timepoint=timepoint,
                cell_id=cell_id,
                lineage_id=lin_id,
                cell_x=float(cell_id),
                cell_y=10.0 * cell_id,
                cell_contour=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],
                particle=99,
            )
        lin.add_edge(*cell_ids)
        lin.graph["lineage_id"] = lin_id
        lineages[lin_id] = lin

    props_metadata = PropsMetadata()
    for prop in [
        create_timepoint_property(),
        create_cell_id_property(),
        create_lineage_id_property(),
        create_cell_coord_property(unit=None, axis="x"),
        create_cell_coord_property(unit=None, axis="y"),
        create_cell_contour_property(),
        Property(
            identifier="particle",
            name="Particle",
            description="Identifier of the particle, given by trackpy linking",
            provenance="trackpy",
            prop_type="node",
            lin_type="CellLineage",
            dtype="int",
        ),
    ]:
        props_metadata._add_prop(prop)
    return Model(
        data=Data(lineages),
        props_metadata=props_metadata,
        reference_time_property="timepoint",
    )


# Test classes ###############################################################


# The export calls update() on its copy of the model, which warns that the model is
# already up to date when there is no division to remove.
@pytest.mark.filterwarnings("ignore:Model is already up to date")
# pandas 3.1 deprecates the `inplace` argument, removed in pandas 4.
@pytest.mark.filterwarnings("error:The inplace keyword")
class TestExportTrackpyDataframe:
    """Test cases for export_trackpy_dataframe function."""

    def test_model_requiring_update_raises(self, simple_model):
        """Test that a model requiring an update is not exported."""
        simple_model.prepare_full_data_update()
        with pytest.raises(UpdateRequiredError, match="before exporting"):
            export_trackpy_dataframe(simple_model)

    def test_columns_follow_trackpy_format(self, model_with_positions):
        """Test that positions come first and frame and particle last, renamed."""
        df = export_trackpy_dataframe(model_with_positions)
        assert list(df.columns[:2]) == ["y", "x"]
        assert list(df.columns[-2:]) == ["frame", "particle"]
        for column in ["cell_x", "cell_y", "timepoint", "lineage_id", "cell_contour"]:
            assert column not in df.columns
        assert list(df.columns).count("particle") == 1

    def test_values_kept_under_trackpy_names(self, model_with_positions):
        """Test that the renamed columns keep their values."""
        df = export_trackpy_dataframe(model_with_positions)
        assert df["x"].tolist() == [1.0, 2.0, 3.0, 4.0]
        assert df["y"].tolist() == [10.0, 20.0, 30.0, 40.0]
        assert df["frame"].tolist() == [0, 1, 0, 1]
        # "particle" comes from the lineage IDs, not from the outdated values.
        assert df["particle"].tolist() == [1, 1, 2, 2]

    def test_rows_sorted_by_particle_then_frame(self, model_with_positions):
        """Test that the rows are sorted by particle, then by frame."""
        df = export_trackpy_dataframe(model_with_positions)
        keys = list(zip(df["particle"], df["frame"]))
        assert keys == sorted(keys)

    def test_3d_positions_put_z_first(self, model_with_positions):
        """Test that the z position comes before y and x."""
        for lin in model_with_positions.data.cell_data.values():
            for cell_id in lin.nodes:
                lin.nodes[cell_id]["cell_z"] = 0.5
        model_with_positions.props_metadata._add_prop(
            create_cell_coord_property(unit=None, axis="z")
        )
        df = export_trackpy_dataframe(model_with_positions)
        assert list(df.columns[:3]) == ["z", "y", "x"]
        assert df["z"].tolist() == [0.5] * 4
