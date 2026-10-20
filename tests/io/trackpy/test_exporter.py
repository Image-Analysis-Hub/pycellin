#!/usr/bin/env python3

"""Unit test for trackpy DataFrame exporter."""

import pytest

from pycellin.classes import CellLineage, Data, Model, PropsMetadata
from pycellin.classes.exceptions import UpdateRequiredError
from pycellin.io.trackpy.exporter import export_trackpy_dataframe
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
        reference_time_property="timepoint",
    )


# Test classes ###############################################################


class TestExportTrackpyDataframe:
    """Test cases for export_trackpy_dataframe function."""

    def test_model_requiring_update_raises(self, simple_model):
        """Test that a model requiring an update is not exported."""
        simple_model.prepare_full_data_update()
        with pytest.raises(UpdateRequiredError, match="before exporting"):
            export_trackpy_dataframe(simple_model)
