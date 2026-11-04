#!/usr/bin/env python3

"""Unit tests for the pickle reader and writer."""

import pandas as pd
import pytest

from pycellin.classes import CellLineage, Data, Model, PropsMetadata
from pycellin.io.pickle.reader import read_pickle
from pycellin.io.pickle.writer import write_pickle
from pycellin.properties.core import (
    create_cell_id_property,
    create_lineage_id_property,
    create_timepoint_property,
)

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


# Test classes ###############################################################


class TestPickle:
    """Test cases for write_pickle and read_pickle functions."""

    def test_round_trip(self, tmp_path, simple_model):
        """Test that the model read back has the same data, properties and
        metadata."""
        path = tmp_path / "model.pickle"
        write_pickle(simple_model, path)
        model = read_pickle(path)

        assert isinstance(model, Model)
        pd.testing.assert_frame_equal(
            model.to_cell_dataframe(), simple_model.to_cell_dataframe()
        )
        assert model.get_properties() == simple_model.get_properties()
        assert model.model_metadata.to_dict() == simple_model.model_metadata.to_dict()
        assert model.reference_time_prop == "timepoint"

    def test_read_model_can_be_updated(self, tmp_path, simple_model):
        """Test that the model read back can still be edited and updated."""
        path = tmp_path / "model.pickle"
        write_pickle(simple_model, path)
        model = read_pickle(path)

        model.remove_link(1, 2, lineage_id=1)
        model.update()
        assert sorted(len(lin) for lin in model.data.cell_data.values()) == [1, 1]

    def test_protocol(self, tmp_path, simple_model):
        """Test that the file is written with the given pickle protocol."""
        path = tmp_path / "model.pickle"
        write_pickle(simple_model, path, protocol=2)
        # A pickle starts with the PROTO opcode (0x80), then the protocol number.
        assert path.read_bytes()[:2] == bytes([0x80, 2])
        assert read_pickle(path).reference_time_prop == "timepoint"

    def test_protocol_by_position_raises(self, tmp_path, simple_model):
        """Test that the protocol can't be given by position."""
        path = tmp_path / "model.pickle"
        with pytest.raises(TypeError):
            write_pickle(simple_model, path, 2)
        assert not path.exists()
