#!/usr/bin/env python3

"""Unit test for TrackMate XML file exporter."""

import copy
import io
import logging
from pathlib import Path

import pytest
from lxml import etree as ET

from pycellin.classes import CellLineage, Data, Model, Property, PropsMetadata
from pycellin.exceptions import UpdateRequiredError
from pycellin.io.trackmate.reader import read_trackmate_xml
from pycellin.io.trackmate.writer import (
    _relabel_nodes,
    _remove_non_numeric_props,
    _transform_name,
    _value_to_str,
    _write_FeatureDeclarations,
    write_trackmate_xml,
)
from pycellin.properties.core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_lineage_id_property,
    create_timepoint_property,
)

# Fixtures ####################################################################


@pytest.fixture
def simple_model():
    """Create a simple model for testing."""
    lin = CellLineage()
    lin.add_node(1, timepoint=0, cell_x=1.0, cell_y=1.5, lineage_id=0, cell_id=1)
    lin.add_node(2, timepoint=1, cell_x=2.0, cell_y=2.5, lineage_id=0, cell_id=2)
    lin.add_edge(1, 2, SPOT_SOURCE_ID=1, SPOT_TARGET_ID=2)
    lin.graph["lineage_id"] = 0

    cell_lineages = {0: lin}
    data = Data(cell_lineages)
    props_metadata = PropsMetadata()
    props_metadata._add_prop(create_timepoint_property())
    props_metadata._add_prop(create_cell_coord_property(axis="x", unit="pixel"))
    props_metadata._add_prop(create_cell_coord_property(axis="y", unit="pixel"))
    props_metadata._add_prop(create_lineage_id_property())
    props_metadata._add_prop(create_cell_id_property())

    model = Model(
        data=data,
        props_metadata=props_metadata,
        reference_time_prop="timepoint",
    )
    return model


@pytest.fixture
def model_unique_ids(simple_model):
    """Create a model with all unique node IDs across lineages."""
    lin = CellLineage()
    lin.add_node(3, timepoint=0, cell_x=1.0, cell_y=1.5, lineage_id=1, cell_id=3)
    lin.add_node(4, timepoint=1, cell_x=2.0, cell_y=2.5, lineage_id=1, cell_id=4)
    lin.add_node(5, timepoint=2, cell_x=3.0, cell_y=3.5, lineage_id=1, cell_id=5)
    lin.add_node(6, timepoint=3, cell_x=4.0, cell_y=4.5, lineage_id=1, cell_id=6)
    lin.add_node(8, timepoint=3, cell_x=6.0, cell_y=6.5, lineage_id=1, cell_id=8)
    lin.add_edges_from(
        [
            (3, 4, {"SPOT_SOURCE_ID": 3, "SPOT_TARGET_ID": 4}),
            (4, 5, {"SPOT_SOURCE_ID": 4, "SPOT_TARGET_ID": 5}),
            (4, 6, {"SPOT_SOURCE_ID": 4, "SPOT_TARGET_ID": 6}),
            (6, 8, {"SPOT_SOURCE_ID": 6, "SPOT_TARGET_ID": 8}),
        ]
    )
    lin.graph["lineage_id"] = 1
    simple_model.data.cell_lineages[1] = lin
    return simple_model


@pytest.fixture
def model_non_unique_ids(simple_model):
    """Create a model with duplicate node IDs across lineages."""
    lin = CellLineage()
    lin.add_node(1, timepoint=0, cell_x=1.0, cell_y=1.5, lineage_id=1, cell_id=1)
    lin.add_node(2, timepoint=1, cell_x=2.0, cell_y=2.5, lineage_id=1, cell_id=2)
    lin.add_node(3, timepoint=2, cell_x=3.0, cell_y=3.5, lineage_id=1, cell_id=3)
    lin.add_node(4, timepoint=3, cell_x=4.0, cell_y=4.5, lineage_id=1, cell_id=4)
    lin.add_node(6, timepoint=3, cell_x=6.0, cell_y=6.5, lineage_id=1, cell_id=6)
    lin.add_edges_from(
        [
            (1, 2, {"SPOT_SOURCE_ID": 1, "SPOT_TARGET_ID": 2}),
            (2, 3, {"SPOT_SOURCE_ID": 2, "SPOT_TARGET_ID": 3}),
            (2, 4, {"SPOT_SOURCE_ID": 2, "SPOT_TARGET_ID": 4}),
            (4, 6, {"SPOT_SOURCE_ID": 4, "SPOT_TARGET_ID": 6}),
        ]
    )
    lin.graph["lineage_id"] = 1
    simple_model.data.cell_lineages[1] = lin

    cell_name_prop = Property(
        identifier="cell_name",
        name="Cell name",
        description="Cell name from TrackMate",
        provenance="TrackMate",
        prop_type="node",
        lineage_type="cell",
        dtype="str",
        unit=None,
    )
    simple_model.props_metadata._add_prop(cell_name_prop)

    return simple_model


@pytest.fixture
def model_with_cycle_lineages(model_unique_ids):
    """Create a model with cycle lineages and their mother_cycle property."""
    model_unique_ids.add_cycle_lineages()
    model_unique_ids.add_mother_cycle()
    model_unique_ids.update()
    return model_unique_ids


@pytest.fixture
def numeric_float64_prop():
    """Numeric property with numpy-style dtype."""
    return Property(
        identifier="intensity",
        name="Intensity",
        description="Cell intensity",
        provenance="test",
        prop_type="node",
        lineage_type="cell",
        dtype="float64",
        unit=None,
    )


@pytest.fixture
def numeric_float32_prop():
    """Numeric property with unit."""
    return Property(
        identifier="area",
        name="Area",
        description="Cell area",
        provenance="test",
        prop_type="node",
        lineage_type="cell",
        dtype="float32",
        unit="pixel",
    )


@pytest.fixture
def bool_prop():
    """Boolean property."""
    return Property(
        identifier="is_division",
        name="Is division",
        description="Whether the cell is dividing",
        provenance="test",
        prop_type="node",
        lineage_type="cell",
        dtype="bool",
        unit=None,
    )


@pytest.fixture
def string_prop():
    """Non-numeric string property."""
    return Property(
        identifier="label",
        name="Label",
        description="Cell label",
        provenance="test",
        prop_type="node",
        lineage_type="cell",
        dtype="string",
        unit=None,
    )


@pytest.fixture
def trackmate_string_prop():
    """Non-numeric string property with TrackMate provenance."""
    return Property(
        identifier="name",
        name="Name",
        description="Spot name",
        provenance="TrackMate",
        prop_type="node",
        lineage_type="cell",
        dtype="string",
        unit=None,
    )


@pytest.fixture
def object_prop():
    """Non-numeric object property."""
    return Property(
        identifier="category",
        name="Category",
        description="Cell category",
        provenance="test",
        prop_type="node",
        lineage_type="cell",
        dtype="object",
        unit=None,
    )


@pytest.fixture
def dict_prop():
    """Non-numeric dict property."""
    return Property(
        identifier="metadata",
        name="Metadata",
        description="Cell metadata",
        provenance="test",
        prop_type="node",
        lineage_type="cell",
        dtype="dict",
        unit=None,
    )


@pytest.fixture
def list_prop():
    """Non-numeric list property."""
    return Property(
        identifier="tags",
        name="Tags",
        description="Cell tags",
        provenance="test",
        prop_type="node",
        lineage_type="cell",
        dtype="list",
        unit=None,
    )


# Test Classes ################################################################


class TestTransformName:
    """Test cases for _transform_name function."""

    def test_pycellin_id_is_uppercase(self):
        """Test that 'id' in a pycellin identifier is displayed as 'ID'."""
        assert _transform_name("cycle_id") == "Cycle ID"
        assert _transform_name("pycellin_cell_id") == "Pycellin cell ID"

    def test_trackmate_id_is_kept(self):
        """Test that 'ID' in a TrackMate feature name stays uppercase."""
        assert _transform_name("TRACK_ID") == "Track ID"


class TestValueToStr:
    """Test cases for _value_to_str function."""

    def test_none_is_nan(self):
        """Test that a missing value is written as NaN, which TrackMate can read."""
        assert _value_to_str(None) == "NaN"


class TestRemoveNonNumericProps:
    """Test cases for _remove_non_numeric_props function."""

    def test_preserves_numeric_properties(self, simple_model, numeric_float64_prop):
        """Test that numeric properties are preserved, numpy-style or not."""
        simple_model.props_metadata._add_prop(numeric_float64_prop)
        assert "intensity" in simple_model.get_properties()

        _remove_non_numeric_props(simple_model)

        assert "timepoint" in simple_model.get_properties()
        assert "cell_x" in simple_model.get_properties()
        assert "cell_y" in simple_model.get_properties()
        assert "intensity" in simple_model.get_properties()

    def test_removes_string_properties(self, simple_model, string_prop):
        """Test that string properties are removed."""
        simple_model.props_metadata._add_prop(string_prop)
        assert "label" in simple_model.get_properties()

        _remove_non_numeric_props(simple_model)

        assert "label" not in simple_model.get_properties()

    def test_preserves_properties_coming_from_trackmate(
        self, simple_model, trackmate_string_prop
    ):
        """Test that properties coming from TrackMate are never removed."""
        simple_model.props_metadata._add_prop(trackmate_string_prop)
        assert "name" in simple_model.get_properties()

        _remove_non_numeric_props(simple_model)

        assert "name" in simple_model.get_properties()

    def test_mixed_numeric_and_non_numeric(
        self, simple_model, numeric_float32_prop, object_prop
    ):
        """Test with a mix of numeric and non-numeric properties."""
        simple_model.props_metadata._add_prop(numeric_float32_prop)
        simple_model.props_metadata._add_prop(object_prop)

        _remove_non_numeric_props(simple_model)

        assert "area" in simple_model.get_properties()
        assert "category" not in simple_model.get_properties()

    def test_handles_protected_properties(self, simple_model, dict_prop):
        """Test that protected properties can still be removed if non-numeric."""
        simple_model.props_metadata._add_prop(dict_prop)
        simple_model.props_metadata._protect_prop("metadata")

        _remove_non_numeric_props(simple_model)

        assert "metadata" not in simple_model.get_properties()

    def test_warns_about_removed_properties(
        self, caplog, simple_model, string_prop, list_prop
    ):
        """Test that warnings are issued for removed properties."""
        simple_model.props_metadata._add_prop(string_prop)
        simple_model.props_metadata._add_prop(list_prop)

        with caplog.at_level(logging.WARNING, logger="pycellin.io.trackmate.writer"):
            _remove_non_numeric_props(simple_model)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "Ignoring properties: label, tags" in caplog.records[0].message

    def test_bool_dtype_preserved(self, simple_model, bool_prop):
        """Test that boolean dtypes are preserved as numeric."""
        simple_model.props_metadata._add_prop(bool_prop)

        _remove_non_numeric_props(simple_model)

        assert "is_division" in simple_model.get_properties()


class TestRelabelNodes:
    """Test cases for _relabel_nodes function."""

    def test_unique_ids_no_relabel(self, model_unique_ids):
        """Test that nodes with unique IDs are not relabeled."""
        lin = model_unique_ids.data.cell_lineages[0]
        original_nodes = set(lin.nodes())
        original_cell_ids = {node: lin.nodes[node]["cell_id"] for node in lin.nodes()}

        _relabel_nodes(model_unique_ids)

        # Nodes should remain unchanged
        assert set(lin.nodes()) == original_nodes
        for node in lin.nodes():
            assert lin.nodes[node]["cell_id"] == original_cell_ids[node]

    def test_non_unique_ids_across_lineages(self, model_non_unique_ids):
        """Test that nodes with duplicate IDs across lineages are relabeled uniquely."""
        original_ids = []
        for lin in model_non_unique_ids.data.cell_lineages.values():
            original_ids.extend(lin.nodes())
        _relabel_nodes(model_non_unique_ids)

        new_ids = []
        for lin in model_non_unique_ids.data.cell_lineages.values():
            new_ids.extend(lin.nodes())

        assert len(original_ids) != len(set(original_ids))
        assert len(original_ids) == len(new_ids)
        assert len(new_ids) == len(set(new_ids))

    def test_original_cell_id_preserved(self, model_non_unique_ids):
        """Test that original cell_id is preserved in pycellin_cell_id."""
        # Collect original cell_ids for each lineage before relabeling
        original_cell_ids_by_lin = {}
        for lin_id, lin in model_non_unique_ids.data.cell_lineages.items():
            # Store the cell_ids in the order nodes appear
            original_cell_ids_by_lin[lin_id] = [
                lin.nodes[node]["cell_id"] for node in lin.nodes()
            ]

        _relabel_nodes(model_non_unique_ids)

        # After relabeling, verify that pycellin_cell_id matches original cell_ids
        for lin_id, lin in model_non_unique_ids.data.cell_lineages.items():
            for node in lin.nodes():
                assert "pycellin_cell_id" in lin.nodes[node]
                # The pycellin_cell_id should be one of the original cell_ids
                assert (
                    lin.nodes[node]["pycellin_cell_id"]
                    in original_cell_ids_by_lin[lin_id]
                )

    def test_new_cell_id_updated(self, model_non_unique_ids):
        """Test that cell_id is updated to the new node ID after relabeling."""
        _relabel_nodes(model_non_unique_ids)

        # After relabeling, cell_id should match the new node ID
        for lin in model_non_unique_ids.data.cell_lineages.values():
            for node in lin.nodes():
                assert lin.nodes[node]["cell_id"] == node

    def test_with_cycle_lins(self, model_non_unique_ids):
        """Test that cycle lineage nodes are also relabeled.."""
        model_non_unique_ids.add_cycle_lineages()
        original_ids = []
        for lin in model_non_unique_ids.data.cycle_lineages.values():
            original_ids.extend(lin.nodes())

        _relabel_nodes(model_non_unique_ids)

        new_ids = []
        for lin in model_non_unique_ids.data.cycle_lineages.values():
            new_ids.extend(lin.nodes())

        assert len(original_ids) != len(set(original_ids))
        assert len(original_ids) == len(new_ids)
        assert len(new_ids) == len(set(new_ids))

    def test_ids_forming_a_loop(self, model_non_unique_ids):
        """Test old and new IDs forming a loop, which NetworkX refuses in place."""
        lin = CellLineage()
        lin.add_node(1, timepoint=1, cell_x=1.0, cell_y=1.5, lineage_id=0, cell_id=1)
        lin.add_node(0, timepoint=0, cell_x=0.0, cell_y=0.5, lineage_id=0, cell_id=0)
        lin.add_edge(0, 1)
        lin.graph["lineage_id"] = 0
        model_non_unique_ids.data.cell_lineages[0] = lin

        mapping = _relabel_nodes(model_non_unique_ids)

        # New IDs follow the order of the nodes: cells 0 and 1 swap their IDs.
        assert mapping[0] == {1: 0, 0: 1}
        relabeled = model_non_unique_ids.data.cell_lineages[0]
        assert list(relabeled.edges) == [(1, 0)]
        for node, old_id, cell_x in ((0, 1, 1.0), (1, 0, 0.0)):
            assert relabeled.nodes[node]["cell_id"] == node
            assert relabeled.nodes[node]["pycellin_cell_id"] == old_id
            assert relabeled.nodes[node]["cell_x"] == cell_x

    def test_cell_name_updated(self, model_non_unique_ids):
        """Test that cell_name property is updated to "ID{node}"."""
        for lin in model_non_unique_ids.data.cell_lineages.values():
            for node in lin.nodes():
                lin.nodes[node]["cell_name"] = f"ID{node}"

        _relabel_nodes(model_non_unique_ids)

        for lin in model_non_unique_ids.data.cell_lineages.values():
            for node in lin.nodes():
                assert "cell_name" in lin.nodes[node]
                assert lin.nodes[node]["cell_name"] == f"ID{node}"

    def test_cell_name_partially_updated(self, model_non_unique_ids):
        """Test that cell_name property is updated only for nodes with TrackMate
        syntax."""
        for lin in model_non_unique_ids.data.cell_lineages.values():
            for node in lin.nodes():
                if node % 2 == 0:
                    lin.nodes[node]["cell_name"] = f"ID{node}"  # TrackMate syntax
                else:
                    lin.nodes[node]["cell_name"] = f"Cell{node}"  # non-TrackMate syntax

        mapping = _relabel_nodes(model_non_unique_ids)
        inv_mapping = {
            new_id: old_id
            for nodes in mapping.values()
            for old_id, new_id in nodes.items()
        }

        for lin in model_non_unique_ids.data.cell_lineages.values():
            for node in lin.nodes():
                if "ID" in lin.nodes[node]["cell_name"]:
                    assert lin.nodes[node]["cell_name"] == f"ID{node}"
                else:
                    assert lin.nodes[node]["cell_name"] == f"Cell{inv_mapping[node]}"


class TestWriteFeatureDeclarations:
    """Test cases for _write_FeatureDeclarations function."""

    @staticmethod
    def _get_declared_features(model):
        """Write the declarations of `model` and return the features of each part."""
        buffer = io.BytesIO()
        with ET.xmlfile(buffer, encoding="utf-8") as xf:
            with xf.element("Model"):
                _write_FeatureDeclarations(xf, model)
        declarations = ET.fromstring(buffer.getvalue()).find("FeatureDeclarations")
        return {
            part.tag: [feat.get("feature") for feat in part] for part in declarations
        }

    def test_cell_lineage_properties_are_declared(self, model_with_cycle_lineages):
        """Test that the properties of cell lineages are declared."""
        features = self._get_declared_features(model_with_cycle_lineages)

        assert {"cell_x", "cell_y", "lineage_id"} <= set(features["SpotFeatures"])
        assert "lineage_id" in features["TrackFeatures"]

    def test_cycle_lineage_properties_are_not_declared(self, model_with_cycle_lineages):
        """Test that cycle properties are not declared, as cells have no values."""
        for prop_type in ["edge", "lineage"]:
            model_with_cycle_lineages.props_metadata._add_prop(
                Property(
                    identifier=f"cycle_{prop_type}_prop",
                    name=f"Cycle {prop_type} property",
                    description=f"Cycle {prop_type} property",
                    provenance="test",
                    prop_type=prop_type,
                    lineage_type="cycle",
                    dtype="float",
                )
            )

        features = self._get_declared_features(model_with_cycle_lineages)

        declared = {feat for part in features.values() for feat in part}
        cycle_props = {
            "cycle_id",
            "generation",
            "cycle_duration",
            "mother_cycle",
            "cycle_edge_prop",
            "cycle_lineage_prop",
        }
        assert not declared & cycle_props

    def test_propagated_cycle_properties_are_declared(self, model_with_cycle_lineages):
        """Test that cycle properties propagated to cell lineages are declared."""
        model_with_cycle_lineages.propagate_cycle_properties(["generation"])

        features = self._get_declared_features(model_with_cycle_lineages)

        assert "generation" in features["SpotFeatures"]
        assert "cycle_duration" not in features["SpotFeatures"]


class TestWriteTrackmateXml:
    """Test cases for write_trackmate_xml function."""

    def test_cycle_lineages_can_be_computed_after_reload(
        self, tmp_path, model_with_cycle_lineages
    ):
        """Test that cycle properties can be computed again on the reloaded model."""
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(
            model_with_cycle_lineages, xml_path, space_unit="pixel", time_unit="frame"
        )
        model = read_trackmate_xml(xml_path)

        model.add_cycle_lineages()
        model.add_mother_cycle()
        model.update()

        assert model.get_property("generation").lineage_type == "cycle"
        assert model.get_property("mother_cycle").lineage_type == "cycle"
        pairs = model.to_cycle_pair_dataframe("mother_cycle")
        assert sorted(zip(pairs["cycle_id_1"], pairs["cycle_id_2"])) == [(5, 4), (8, 4)]

    def test_propagated_cycle_properties_must_be_removed_after_reload(
        self, tmp_path, model_with_cycle_lineages
    ):
        """Test that cycle properties propagated in the file must be removed first."""
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(
            model_with_cycle_lineages,
            xml_path,
            space_unit="pixel",
            time_unit="frame",
            propagate_cycle_props=True,
        )
        model = read_trackmate_xml(xml_path)
        with pytest.raises(ValueError, match="remove them first"):
            model.add_cycle_lineages()

        cycle_props = model_with_cycle_lineages.get_cycle_lineage_properties(
            single_type=True
        )
        for prop_id in cycle_props:
            if model.has_property(prop_id):
                model.remove_property(prop_id)
        model.add_cycle_lineages()
        model.add_mother_cycle()
        model.update()

        pairs = model.to_cycle_pair_dataframe("mother_cycle")
        assert sorted(zip(pairs["cycle_id_1"], pairs["cycle_id_2"])) == [(5, 4), (8, 4)]

    def test_model_requiring_update_raises(self, tmp_path, simple_model):
        """Test that a model requiring an update is not exported."""
        simple_model.prepare_full_data_update()
        with pytest.raises(UpdateRequiredError, match="before exporting"):
            write_trackmate_xml(
                simple_model,
                tmp_path / "model.xml",
                space_unit="pixel",
                time_unit="frame",
            )
        assert not (tmp_path / "model.xml").exists()

    def test_lineage_without_FilteredTrack_exported_as_visible(
        self, tmp_path, simple_model
    ):
        """Test that a lineage without the FilteredTrack flag, e.g. added in pycellin,
        is exported as a visible track."""
        # As loaded from TrackMate, with a hidden track.
        simple_model.props_metadata._add_prop(
            Property(
                identifier="FilteredTrack",
                name="FilteredTrack",
                description="True if the track was not filtered out in TrackMate",
                provenance="TrackMate",
                prop_type="lineage",
                lineage_type="cell",
                dtype="int",
            )
        )
        simple_model.data.cell_lineages[0].graph["FilteredTrack"] = False
        lid = simple_model.add_lineage()
        coords = {"cell_x": 0.0, "cell_y": 0.0}
        simple_model.add_cell(
            lineage_id=lid, cell_id=10, time_value=0, prop_values=coords
        )
        simple_model.add_cell(
            lineage_id=lid, cell_id=11, time_value=1, prop_values=coords
        )
        simple_model.add_link(
            source_cell_id=10, source_lineage_id=lid, target_cell_id=11
        )
        simple_model.update()
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(
            simple_model, xml_path, space_unit="pixel", time_unit="frame"
        )
        model = read_trackmate_xml(xml_path, tracks="all")
        assert model.data.cell_lineages[0].graph["FilteredTrack"] is False
        assert model.data.cell_lineages[lid].graph["FilteredTrack"] is True

    def test_reloaded_cells_without_contour_exported_again(
        self, tmp_path, simple_model
    ):
        """Test that cells without contour, loaded back with a None contour, can be
        exported again."""
        units = {"space_unit": "pixel", "time_unit": "frame"}
        write_trackmate_xml(simple_model, tmp_path / "first.xml", **units)
        model = read_trackmate_xml(tmp_path / "first.xml")
        write_trackmate_xml(model, tmp_path / "second.xml", **units)
        reloaded = read_trackmate_xml(tmp_path / "second.xml")
        contours = dict(reloaded.data.cell_lineages[0].nodes(data="cell_contour"))
        assert contours == {1: None, 2: None}

    def test_merged_model_can_be_reloaded(self, tmp_path, simple_model):
        """Test that the model names a merge stores on lineages become track names,
        without declaring 'name' as a feature, which the loader couldn't read."""
        simple_model.model_metadata.name = "model"
        merged = simple_model.merge(copy.deepcopy(simple_model))
        merged.update()
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(merged, xml_path, space_unit="pixel", time_unit="frame")

        tree = ET.parse(str(xml_path))
        assert all(feat.get("feature") != "name" for feat in tree.iter("Feature"))
        model = read_trackmate_xml(xml_path)
        names = [lin.graph["lineage_name"] for lin in model.get_cell_lineages()]
        assert names == ["model", "model"]

    def test_cell_property_called_name_can_be_reloaded(self, tmp_path, simple_model):
        """Test that a cell property called 'name' becomes the name of the spots,
        without being declared as a feature, which the loader couldn't read."""
        simple_model.props_metadata._add_prop(
            Property(
                identifier="name",
                name="Name",
                description="Name",
                provenance="test",
                prop_type="node",
                lineage_type="cell",
                dtype="str",
            )
        )
        lin = simple_model.data.cell_lineages[0]
        for cid, attrs in lin.nodes(data=True):
            attrs["name"] = f"cell{cid}"
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(
            simple_model, xml_path, space_unit="pixel", time_unit="frame"
        )

        tree = ET.parse(str(xml_path))
        assert all(feat.get("feature") != "name" for feat in tree.iter("Feature"))
        model = read_trackmate_xml(xml_path)
        lin = model.data.cell_lineages[0]
        assert dict(lin.nodes(data="cell_name")) == {1: "cell1", 2: "cell2"}

    @staticmethod
    def _add_link_property_called_name(model, dtype, value):
        """Add a link property called 'name', to a model with named spots."""
        model.props_metadata._add_prop(
            Property(
                identifier="name",
                name="Name",
                description="Name",
                provenance="test",
                prop_type="edge",
                lineage_type="cell",
                dtype=dtype,
            )
        )
        lin = model.data.cell_lineages[0]
        lin.edges[1, 2]["name"] = value
        for cid, attrs in lin.nodes(data=True):
            attrs["cell_name"] = f"ID{cid}"

    def test_numeric_link_property_called_name_is_a_feature(
        self, tmp_path, simple_model
    ):
        """Test that 'name' is an ordinary feature on links, which have no display name,
        and that it doesn't change how the names of the spots are read."""
        self._add_link_property_called_name(simple_model, "float", 0.5)
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(
            simple_model, xml_path, space_unit="pixel", time_unit="frame"
        )

        tree = ET.parse(str(xml_path))
        declared = {feat.get("feature") for feat in tree.find(".//EdgeFeatures")}
        assert "name" in declared
        model = read_trackmate_xml(xml_path)
        assert model.get_property("name").provenance == "TrackMate"
        lin = model.data.cell_lineages[0]
        assert lin.edges[1, 2]["name"] == 0.5
        assert dict(lin.nodes(data="cell_name")) == {1: "ID1", 2: "ID2"}

    def test_string_link_property_called_name_not_exported(
        self, tmp_path, simple_model, caplog
    ):
        """Test that a string 'name' on links is removed like any non-numeric property,
        with a warning, without removing the names of the spots."""
        self._add_link_property_called_name(simple_model, "str", "link")
        xml_path = tmp_path / "model.xml"
        with caplog.at_level(logging.WARNING, logger="pycellin.io.trackmate.writer"):
            write_trackmate_xml(
                simple_model, xml_path, space_unit="pixel", time_unit="frame"
            )

        assert "Ignoring property: name" in caplog.text
        tree = ET.parse(str(xml_path))
        assert all("name" not in edge.attrib for edge in tree.iter("Edge"))
        assert all(feat.get("feature") != "name" for feat in tree.iter("Feature"))
        lin = read_trackmate_xml(xml_path).data.cell_lineages[0]
        assert dict(lin.nodes(data="cell_name")) == {1: "ID1", 2: "ID2"}

    def test_undeclared_attributes_not_exported(self, tmp_path, simple_model, caplog):
        """Test that attributes without a property declaration are not exported,
        with a warning naming them, so that TrackMate can read the file."""
        lin = simple_model.data.cell_lineages[0]
        for _, attrs in lin.nodes(data=True):
            attrs["note"] = "text"
        lin.edges[1, 2]["link_note"] = 1.0
        lin.graph["lineage_note"] = 2
        xml_path = tmp_path / "model.xml"

        with caplog.at_level(logging.WARNING, logger="pycellin.io.trackmate.writer"):
            write_trackmate_xml(
                simple_model, xml_path, space_unit="pixel", time_unit="frame"
            )

        tree = ET.parse(str(xml_path))
        for tag, key in (
            ("Spot", "note"),
            ("Edge", "link_note"),
            ("Track", "lineage_note"),
        ):
            assert all(key not in element.attrib for element in tree.iter(tag))
        messages = [
            r.message for r in caplog.records if "no property declaration" in r.message
        ]
        assert len(messages) == 1
        assert "'note' (cells)" in messages[0]
        assert "'link_note' (links)" in messages[0]
        assert "'lineage_note' (lineages)" in messages[0]
        model = read_trackmate_xml(xml_path)
        assert model.get_property("note") is None

    def test_declared_attributes_exported_without_warning(
        self, tmp_path, simple_model, caplog
    ):
        """Test that a model whose attributes are all declared exports them all,
        without warning about undeclared attributes."""
        xml_path = tmp_path / "model.xml"

        with caplog.at_level(logging.WARNING, logger="pycellin.io.trackmate.writer"):
            write_trackmate_xml(
                simple_model, xml_path, space_unit="pixel", time_unit="frame"
            )

        assert not any("no property declaration" in r.message for r in caplog.records)
        spot = next(ET.parse(str(xml_path)).iter("Spot"))
        for key in ("ID", "FRAME", "POSITION_X", "POSITION_Y", "RADIUS"):
            assert key in spot.attrib

    def test_cells_without_visibility_exported_as_visible(self, tmp_path, simple_model):
        """Test that cells without VISIBILITY, e.g. not from TrackMate, are visible."""
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(
            simple_model, xml_path, space_unit="pixel", time_unit="frame"
        )
        spots = ET.parse(str(xml_path)).iter("Spot")
        assert [float(spot.get("VISIBILITY")) for spot in spots] == [1.0, 1.0]

    def test_hidden_spot_stays_hidden(self, tmp_path):
        """Test that a spot hidden by the spot filters of TrackMate is exported with
        its VISIBILITY of 0, so that it stays hidden."""
        xml_in = Path(__file__).resolve().parents[3] / "sample_data" / "FakeTracks.xml"
        model = read_trackmate_xml(xml_in, lone_spots="all", tracks="all")
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(
            model, xml_path, space_unit="micrometer", time_unit="second"
        )
        visibilities = [
            float(spot.get("VISIBILITY"))
            for spot in ET.parse(str(xml_path)).iter("Spot")
        ]
        assert visibilities.count(0.0) == 1
        assert visibilities.count(1.0) == 106


class TestWriteTrackmateXmlUnits:
    """Test cases for the units written by write_trackmate_xml function."""

    @staticmethod
    def _read_units(xml_path: Path) -> tuple[str, str]:
        model_tag = next(ET.parse(str(xml_path)).iter("Model"))
        return model_tag.get("spatialunits"), model_tag.get("timeunits")

    def test_model_units_by_default(self, tmp_path, simple_model):
        """Test that the units of the model are written when none are given."""
        simple_model.model_metadata.space_unit = "micrometer"
        simple_model.model_metadata.time_unit = "minute"
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(simple_model, xml_path)
        assert self._read_units(xml_path) == ("micrometer", "minute")

    def test_given_units_written(self, tmp_path, simple_model):
        """Test that the given units are written instead of those of the model."""
        simple_model.model_metadata.space_unit = "micrometer"
        simple_model.model_metadata.time_unit = "minute"
        xml_path = tmp_path / "model.xml"
        write_trackmate_xml(simple_model, xml_path, space_unit="pixel", time_unit="sec")
        assert self._read_units(xml_path) == ("pixel", "sec")

    def test_model_without_units_written_in_pixels_and_frames(
        self, tmp_path, simple_model, caplog, monkeypatch
    ):
        """Test that a model without units is written in pixels and frames, with a
        warning for each unit, without asking for them."""
        monkeypatch.setattr("builtins.input", lambda *args: pytest.fail("input()"))
        xml_path = tmp_path / "model.xml"
        with caplog.at_level(logging.WARNING, logger="pycellin.io.trackmate.writer"):
            write_trackmate_xml(simple_model, xml_path)
        assert self._read_units(xml_path) == ("pixel", "frame")
        messages = [record.message for record in caplog.records]
        assert any("no space unit" in m and "`space_unit`" in m for m in messages)
        assert any("no time unit" in m and "`time_unit`" in m for m in messages)

    def test_units_by_position_raise(self, tmp_path, simple_model):
        """Test that options passed by position, like the units dict of pycellin
        0.5.1, raise instead of landing in another argument."""
        xml_path = tmp_path / "model.xml"
        with pytest.raises(TypeError):
            write_trackmate_xml(simple_model, xml_path, {"space": "pixel", "time": "s"})
        assert not xml_path.exists()
