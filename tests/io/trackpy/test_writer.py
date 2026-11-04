#!/usr/bin/env python3

"""Unit test for trackpy DataFrame exporter."""

import warnings

import pytest

from pycellin.classes import CellLineage, Data, Model, Property, PropsMetadata
from pycellin.classes.exceptions import UpdateRequiredError
from pycellin.io.trackpy.writer import to_trackpy
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
        reference_time_prop="timepoint",
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
        reference_time_prop="timepoint",
    )


@pytest.fixture
def model_with_division():
    """Create a model with a lineage where cell 1 divides into cells 2 and 3."""
    lin = CellLineage()
    for cell_id, timepoint in [(1, 0), (2, 1), (3, 1), (4, 2)]:
        lin.add_node(
            cell_id,
            timepoint=timepoint,
            cell_id=cell_id,
            lineage_id=1,
            cell_x=float(cell_id),
            cell_y=float(cell_id),
        )
    lin.add_edges_from([(1, 2), (1, 3), (2, 4)])
    lin.graph["lineage_id"] = 1

    props_metadata = PropsMetadata()
    for prop in [
        create_timepoint_property(),
        create_cell_id_property(),
        create_lineage_id_property(),
        create_cell_coord_property(unit=None, axis="x"),
        create_cell_coord_property(unit=None, axis="y"),
    ]:
        props_metadata._add_prop(prop)
    return Model(
        data=Data({1: lin}),
        props_metadata=props_metadata,
        reference_time_prop="timepoint",
    )


# Test classes ###############################################################


# pandas 3.1 deprecates the `inplace` argument, removed in pandas 4.
@pytest.mark.filterwarnings("error:The inplace keyword")
class TestToTrackpy:
    """Test cases for to_trackpy function."""

    def test_model_requiring_update_raises(self, simple_model):
        """Test that a model requiring an update is not exported."""
        simple_model.prepare_full_data_update()
        with pytest.raises(UpdateRequiredError, match="before exporting"):
            to_trackpy(simple_model)

    def test_columns_follow_trackpy_format(self, model_with_positions):
        """Test that positions come first and frame and particle last, renamed."""
        df = to_trackpy(model_with_positions)
        assert list(df.columns[:2]) == ["y", "x"]
        assert list(df.columns[-2:]) == ["frame", "particle"]
        for column in ["cell_x", "cell_y", "timepoint", "lineage_id", "cell_contour"]:
            assert column not in df.columns
        assert list(df.columns).count("particle") == 1

    def test_values_kept_under_trackpy_names(self, model_with_positions):
        """Test that the renamed columns keep their values."""
        df = to_trackpy(model_with_positions)
        assert df["x"].tolist() == [1.0, 2.0, 3.0, 4.0]
        assert df["y"].tolist() == [10.0, 20.0, 30.0, 40.0]
        assert df["frame"].tolist() == [0, 1, 0, 1]
        # "particle" comes from the lineage IDs, not from the outdated values.
        assert df["particle"].tolist() == [1, 1, 2, 2]

    def test_rows_sorted_by_particle_then_frame(self, model_with_positions):
        """Test that the rows are sorted by particle, then by frame."""
        df = to_trackpy(model_with_positions)
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
        df = to_trackpy(model_with_positions)
        assert list(df.columns[:3]) == ["z", "y", "x"]
        assert df["z"].tolist() == [0.5] * 4

    def test_model_without_divisions_exported_without_warning(
        self, model_with_positions
    ):
        """Test that a model without divisions is exported without any warning."""
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            to_trackpy(model_with_positions)

    def test_divisions_split_into_particles(self, model_with_division):
        """Test that each cell cycle becomes a particle, from the same lineage."""
        df = to_trackpy(model_with_division)
        cells = sorted(df.groupby("particle")["cell_id"].apply(sorted).tolist())
        assert cells == [[1], [2, 4], [3]]
        assert df["lineage_id_pycellin"].tolist() == [1, 1, 1, 1]
        # The model given to the export keeps its division.
        assert sorted(model_with_division.data.cell_data[1].edges()) == [
            (1, 2),
            (1, 3),
            (2, 4),
        ]
