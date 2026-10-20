#!/usr/bin/env python3

"""Unit tests for Model class from model.py module."""

import warnings
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock

import numpy as np
import pytest
import tifffile
from shapely.geometry import MultiPolygon, Polygon

from pycellin.classes import CellLineage, Data, Model, Property, PropsMetadata
from pycellin.classes.exceptions import MissingPropertyError
from pycellin.classes.property_calculator import (
    EdgeLocalPropCalculator,
    NodeLocalPropCalculator,
)
from pycellin.custom_types import PropertyType
from pycellin.properties.core import (
    Time,
    create_cell_coord_property,
    create_frame_property,
    create_lineage_coord_property,
    create_link_coord_property,
    create_time_property,
)
from pycellin.properties.morphology import (
    CycleMeanArea,
    create_cycle_mean_area_property,
)
from pycellin.properties.tracking import (
    create_absolute_age_property,
    create_division_time_property,
)


@pytest.fixture()
def props_dict():
    """
    Create a dictionary of properties for testing using predefined property creators.
    """
    division_time_prop = create_division_time_property()
    absolute_age_prop = create_absolute_age_property()

    edge_prop = Property(
        identifier="edge_prop",
        name="Edge property",
        description="Edge property for testing",
        provenance="test",
        prop_type=PropertyType.EDGE,
        lin_type="CycleLineage",
        dtype="float",
    )

    lin_prop = Property(
        identifier="lineage_prop",
        name="Lineage property",
        description="Lineage property for testing",
        provenance="test",
        prop_type=PropertyType.LINEAGE,
        lin_type="CycleLineage",
        dtype="bool",
    )

    mixed_prop = Property(
        identifier="mixed_prop",
        name="Mixed property",
        description="Multi-type property for testing",
        provenance="test",
        prop_type=PropertyType.NODE | PropertyType.EDGE,
        lin_type="CycleLineage",
        dtype="float",
    )

    return {
        "division_time": division_time_prop,
        "absolute_age": absolute_age_prop,
        "edge_prop": edge_prop,
        "lineage_prop": lin_prop,
        "mixed_prop": mixed_prop,
    }


class TestCategorizePropsMockModel:
    """Test cases for Model._categorize_props() method using mocked Model."""

    def test_categorize_props_specific_subset(self, props_dict):
        """Test that only requested properties are categorized, not all available ones."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = props_dict
        model.get_node_properties.return_value = {
            k: v for k, v in props_dict.items() if PropertyType.NODE in v.prop_type
        }
        model.get_edge_properties.return_value = {
            k: v for k, v in props_dict.items() if PropertyType.EDGE in v.prop_type
        }
        model.get_lineage_properties.return_value = {
            k: v for k, v in props_dict.items() if PropertyType.LINEAGE in v.prop_type
        }

        props_to_categorize = ["division_time", "edge_prop"]  # only a subset
        node_props, edge_props, lin_props = Model._categorize_props(
            model, props_to_categorize
        )

        assert node_props == ["division_time"]
        assert edge_props == ["edge_prop"]
        assert lin_props == []

    def test_categorize_props_none_all_properties(self, props_dict):
        """Test categorization when props=None (should categorize all properties)."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = props_dict
        node_props, edge_props, lin_props = Model._categorize_props(model, None)

        expected_node_props = {"division_time", "absolute_age", "mixed_prop"}
        expected_edge_props = {"edge_prop", "mixed_prop"}

        assert set(node_props) == expected_node_props
        assert set(edge_props) == expected_edge_props
        assert lin_props == ["lineage_prop"]

    def test_categorize_props_invalid_properties(self, props_dict):
        """Test that multiple invalid properties are reported in the error."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = props_dict

        invalid_props = ["invalid1", "invalid2", "division_time"]

        with pytest.raises(
            ValueError,
            match="'invalid1', 'invalid2' are either not cycle lineage properties",
        ):
            Model._categorize_props(model, invalid_props)

    def test_categorize_props_empty_list(self, props_dict):
        """Test categorization with an empty list of properties."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = props_dict
        node_props, edge_props, lin_props = Model._categorize_props(model, [])

        assert node_props == []
        assert edge_props == []
        assert lin_props == []

    def test_categorize_props_no_cycle_properties(self):
        """Test categorization when there are no cycle lineage properties."""
        model = MagicMock(spec=Model)
        model.get_cycle_lineage_properties.return_value = {}
        node_props, edge_props, lin_props = Model._categorize_props(model, None)

        assert node_props == []
        assert edge_props == []
        assert lin_props == []

    def test_categorize_props_mixed_type_property(self, props_dict):
        """Test that properties with multiple types appear in multiple categories."""
        model = MagicMock(spec=Model)
        single_mixed_prop = {"mixed_prop": props_dict["mixed_prop"]}
        model.get_cycle_lineage_properties.return_value = single_mixed_prop
        node_props, edge_props, lin_props = Model._categorize_props(model, None)

        assert "mixed_prop" in node_props
        assert "mixed_prop" in edge_props
        assert "mixed_prop" not in lin_props


@pytest.fixture()
def lineage_props_model():
    """
    Create a model with a dividing lineage and a single-cell lineage, and properties
    of lineage, node and node-and-lineage types.
    """
    lin = CellLineage(lid=1)
    lin.add_node(1, cell_id=1, frame=0, node_prop=10, mixed_prop="node1")
    lin.add_node(2, cell_id=2, frame=1, node_prop=20, mixed_prop="node2")
    lin.add_node(3, cell_id=3, frame=1, node_prop=30, mixed_prop="node3")
    lin.add_edge(1, 2)
    lin.add_edge(1, 3)
    lin.graph["lin_prop"] = 1.5
    lin.graph["shared_prop"] = "a"
    lin.graph["mixed_prop"] = "lineage1"
    single_lin = CellLineage(lid=-4)
    single_lin.add_node(4, cell_id=4, frame=0, node_prop=40, mixed_prop="node4")
    single_lin.graph["lin_prop"] = 2.5
    single_lin.graph["mixed_prop"] = "lineage-4"

    def make_prop(identifier, prop_type, lin_type):
        return Property(
            identifier=identifier,
            name=identifier,
            description=f"{identifier} for testing",
            provenance="test",
            prop_type=prop_type,
            lin_type=lin_type,
            dtype="float",
        )

    props_md = PropsMetadata(
        props={
            "lin_prop": make_prop("lin_prop", PropertyType.LINEAGE, "CellLineage"),
            "shared_prop": make_prop("shared_prop", PropertyType.LINEAGE, "Lineage"),
            "node_prop": make_prop("node_prop", PropertyType.NODE, "CellLineage"),
            "mixed_prop": make_prop(
                "mixed_prop", PropertyType.NODE | PropertyType.LINEAGE, "CellLineage"
            ),
            "cycle_prop": make_prop("cycle_prop", PropertyType.LINEAGE, "CycleLineage"),
        }
    )
    return Model(
        model_metadata={"time_step": 1},
        props_metadata=props_md,
        data=Data({1: lin, -4: single_lin}),
        reference_time_property="frame",
    )


class TestToCellDataframe:
    """Test cases for Model.to_cell_dataframe() method."""

    def test_lineage_props_added_as_columns(self, lineage_props_model):
        df = lineage_props_model.to_cell_dataframe(
            lineage_props=["lin_prop", "shared_prop"]
        )

        lin_rows = df[df["lineage_id"] == 1]
        single_rows = df[df["lineage_id"] == -4]
        assert len(lin_rows) == 3
        assert (lin_rows["lin_prop"] == 1.5).all()
        assert (lin_rows["shared_prop"] == "a").all()
        assert single_rows["lin_prop"].tolist() == [2.5]
        assert single_rows["shared_prop"].isna().all()

    def test_lineage_props_none_adds_no_column(self, lineage_props_model):
        df = lineage_props_model.to_cell_dataframe()

        assert "lin_prop" not in df.columns
        assert "shared_prop" not in df.columns

    def test_lineage_id_lineage_prop_is_skipped(self, lineage_props_model):
        df = lineage_props_model.to_cell_dataframe(lineage_props=["lineage_id"])

        assert df.equals(lineage_props_model.to_cell_dataframe())

    def test_lineage_props_restricted_to_lids(self, lineage_props_model):
        df = lineage_props_model.to_cell_dataframe(
            lids=[-4], lineage_props=["lin_prop"]
        )

        assert df["lin_prop"].tolist() == [2.5]

    def test_lineage_prop_clashing_with_column_raises(self, lineage_props_model):
        with pytest.raises(ValueError, match="existing columns.*'mixed_prop'"):
            lineage_props_model.to_cell_dataframe(lineage_props=["mixed_prop"])

    def test_invalid_lineage_props_raise(self, lineage_props_model):
        with pytest.raises(
            ValueError,
            match="declared in the model: 'node_prop', 'cycle_prop', 'unknown'",
        ):
            lineage_props_model.to_cell_dataframe(
                lineage_props=["node_prop", "cycle_prop", "unknown", "lin_prop"]
            )

    def test_missing_mandatory_cell_prop_raises(self, lineage_props_model):
        for lin in lineage_props_model.data.cell_data.values():
            for nid in lin.nodes:
                del lin.nodes[nid]["cell_id"]
        with pytest.raises(ValueError, match="not found in the model: 'cell_id'"):
            lineage_props_model.to_cell_dataframe()

    def test_no_matching_lineage_raises(self, lineage_props_model):
        with pytest.raises(ValueError, match="No cells to export"):
            lineage_props_model.to_cell_dataframe(lids=[99])

    def test_column_all_none_in_a_lineage_does_not_warn(self, lineage_props_model):
        # Like a propagated mother_cycle: None on root cells, so on all the cells
        # of the single-cell lineage -4.
        for lid, nid in [(1, 1), (-4, 4)]:
            lineage_props_model.data.cell_data[lid].nodes[nid]["node_prop"] = None
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            df = lineage_props_model.to_cell_dataframe()
        assert df["node_prop"].isna().tolist() == [True, True, False, False]


class TestToLinkDataframe:
    """Test cases for Model.to_link_dataframe() method."""

    def test_lineage_props_added_as_columns(self, lineage_props_model):
        df = lineage_props_model.to_link_dataframe(lineage_props=["lin_prop"])

        assert df["lin_prop"].tolist() == [1.5, 1.5]

    def test_node_and_lineage_prop_added_when_not_a_column(self, lineage_props_model):
        df = lineage_props_model.to_link_dataframe(lineage_props=["mixed_prop"])

        assert df["mixed_prop"].tolist() == ["lineage1", "lineage1"]

    def test_invalid_lineage_props_raise(self, lineage_props_model):
        with pytest.raises(ValueError, match="declared in the model: 'node_prop'"):
            lineage_props_model.to_link_dataframe(lineage_props=["node_prop"])

    def test_columns_follow_link_props_order(self, lineage_props_model):
        props = ["speed", "angle", "time", "cost", "distance"]
        lin = lineage_props_model.data.cell_data[1]
        for source, target in lin.edges:
            lin.edges[source, target].update({prop: 1.0 for prop in props})
        df = lineage_props_model.to_link_dataframe()

        expected = ["lineage_id", "source_cell_id", "target_cell_id", *props]
        assert df.columns.tolist() == expected

    def test_lineages_without_links_give_empty_dataframe(self, lineage_props_model):
        df = lineage_props_model.to_link_dataframe(lids=[-4])

        assert df.empty
        assert df.columns.tolist() == ["lineage_id", "source_cell_id", "target_cell_id"]

    def test_no_matching_lineage_raises(self, lineage_props_model):
        with pytest.raises(ValueError, match="No links to export"):
            lineage_props_model.to_link_dataframe(lids=[99])


class TestToLineageDataframe:
    """Test cases for Model.to_lineage_dataframe() method."""

    def test_missing_lineage_id_raises(self, lineage_props_model):
        for lin in lineage_props_model.data.cell_data.values():
            del lin.graph["lineage_id"]
        with pytest.raises(ValueError, match="not found in the model: 'lineage_id'"):
            lineage_props_model.to_lineage_dataframe()

    def test_no_matching_lineage_raises(self, lineage_props_model):
        with pytest.raises(ValueError, match="No lineages to export"):
            lineage_props_model.to_lineage_dataframe(lids=[99])

    def test_prop_none_in_a_lineage_does_not_warn(self, lineage_props_model):
        lineage_props_model.data.cell_data[-4].graph["lin_prop"] = None
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            df = lineage_props_model.to_lineage_dataframe()
        assert df["lin_prop"].isna().tolist() == [True, False]


class TestAddCycleData:
    """Test cases for Model.add_cycle_data() method."""

    def test_first_and_last_cell_declared_and_protected(self, lineage_props_model):
        model = lineage_props_model
        model.add_cycle_data()
        protected_props = model.props_metadata._get_protected_props()
        for prop_id in ["first_cell", "last_cell"]:
            prop = model.get_property(prop_id)
            assert prop.prop_type == PropertyType.NODE
            assert prop.lin_type == "CycleLineage"
            assert prop.dtype == "int"
            assert prop_id in protected_props

    def test_first_and_last_cell_bound_the_cycle(self, relatives_model):
        df = relatives_model.to_cycle_dataframe()
        assert df["first_cell"].tolist() == df["cells"].str[0].tolist()
        assert df["last_cell"].tolist() == df["cells"].str[-1].tolist()
        assert df["last_cell"].tolist() == df["cycle_id"].tolist()

    def test_prop_declared_otherwise_with_values_raises(self, lineage_props_model):
        model = lineage_props_model
        # E.g. a cycle property propagated to cell lineages, loaded from a file.
        model.props_metadata._add_prop(_create_test_property("level", "node"))
        for _, cell in model.data.cell_data[1].nodes(data=True):
            cell["level"] = 0
        with pytest.raises(ValueError, match="calculator: 'level'") as exc_info:
            model.add_cycle_data()
        assert "model.remove_property()" in str(exc_info.value)
        assert model.get_property("level").lin_type == "CellLineage"
        assert not model.has_cycle_data()

    def test_prop_declared_otherwise_with_calculator_raises(self, lineage_props_model):
        # Not computed yet, so without values.
        prop = _create_test_property("level", "node", dtype="list[int]")
        lineage_props_model.add_custom_property(RootRelation(prop, []))
        with pytest.raises(ValueError, match="calculator: 'level'"):
            lineage_props_model.add_cycle_data()

    def test_unused_prop_declared_otherwise_replaced(self, lineage_props_model):
        model = lineage_props_model
        # E.g. declared in a file without values.
        model.props_metadata._add_prop(_create_test_property("level", "node"))
        model.add_cycle_data()
        assert model.get_property("level").lin_type == "CycleLineage"
        assert "level" in model.props_metadata._get_protected_props()

    def test_propagated_prop_kept(self, lineage_props_model):
        model = lineage_props_model
        model.add_cycle_data()
        model.propagate_cycle_properties(["level"])
        model.add_cycle_data()
        assert model.get_property("level").lin_type == "Lineage"


class TestToCycleDataframe:
    """Test cases for Model.to_cycle_dataframe() method."""

    def test_lineage_props_added_as_columns(self, lineage_props_model):
        model = lineage_props_model
        model.add_cycle_data()
        df = model.to_cycle_dataframe(lineage_props=["lin_prop"])

        lin_rows = df[df["lineage_id"] == 1]
        assert len(lin_rows) == 3
        assert (lin_rows["lin_prop"] == 1.5).all()
        assert df.loc[df["lineage_id"] == -4, "lin_prop"].tolist() == [2.5]

    def test_no_matching_lineage_raises(self, lineage_props_model):
        lineage_props_model.add_cycle_data()
        with pytest.raises(ValueError, match="No cell cycles to export"):
            lineage_props_model.to_cycle_dataframe(lids=[99])

    def test_column_all_none_in_a_lineage_does_not_warn(self, lineage_props_model):
        # Lineage -4 has a single cell cycle, which has no mother cycle.
        model = lineage_props_model
        model.add_cycle_data()
        model.add_mother_cycle()
        model.update()
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            df = model.to_cycle_dataframe()
        assert df["mother_cycle"].isna().tolist() == [True, True, False, False]


@pytest.fixture()
def relatives_model():
    """
    Create a model with a lineage of three generations of cell cycles, a single-cell
    lineage, and the mother, daughter, sister and cousin cycles of each cell cycle.

    Cell cycles of lineage 1 (ID = last cell): 2 (cells 1-2) divides into 5 (cells 3
    and 5) and 8 (cells 4 and 8); 5 divides into 6 and 7, 8 into 9 and 10.
    """
    lin = CellLineage(lid=1)
    for cell_id, frame in [(1, 0), (2, 1), (3, 2), (4, 2), (5, 3), (8, 3)]:
        lin.add_node(cell_id, cell_id=cell_id, frame=frame)
    for cell_id in [6, 7, 9, 10]:
        lin.add_node(cell_id, cell_id=cell_id, frame=4)
    for source, target in [(1, 2), (2, 3), (2, 4), (3, 5), (4, 8)]:
        lin.add_edge(source, target)
    for source, target in [(5, 6), (5, 7), (8, 9), (8, 10)]:
        lin.add_edge(source, target)
    lin.graph["lin_prop"] = 1.5
    single_lin = CellLineage(lid=-11)
    single_lin.add_node(11, cell_id=11, frame=0)
    single_lin.graph["lin_prop"] = 2.5

    lin_prop = Property(
        identifier="lin_prop",
        name="lin_prop",
        description="lin_prop for testing",
        provenance="test",
        prop_type=PropertyType.LINEAGE,
        lin_type="CellLineage",
        dtype="float",
    )
    model = Model(
        model_metadata={"time_step": 1},
        props_metadata=PropsMetadata(props={"lin_prop": lin_prop}),
        data=Data({1: lin, -11: single_lin}),
        reference_time_property="frame",
    )
    model.add_cycle_data()
    model.add_mother_cycle()
    model.add_daughter_cycles()
    model.add_sister_cycles()
    model.add_cousin_cycles()
    model.update()
    return model


class RootRelation(NodeLocalPropCalculator):
    """
    User-defined relation: the root cell cycle of lineage 1 lists the given cell
    cycle IDs.
    """

    def __init__(self, property, cycle_ids):
        super().__init__(property)
        self.cycle_ids = cycle_ids

    def compute(self, lineage, nid):
        is_root = lineage.in_degree(nid) == 0
        return self.cycle_ids if is_root and lineage.graph["lineage_id"] == 1 else []


def root_relation_property():
    """Declaration of the RootRelation property, as "root_relation"."""
    return Property(
        identifier="root_relation",
        name="root relation",
        description="Cell cycles listed by the root cell cycle, for testing",
        provenance="test",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="list[int]",
    )


class TestToCyclePairDataframe:
    """Test cases for Model.to_cycle_pair_dataframe() method."""

    def test_mother_pairs(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe("mother_cycle", props=[])
        pairs = list(zip(df["cycle_id_1"], df["cycle_id_2"]))
        assert pairs == [(5, 2), (6, 5), (7, 5), (8, 2), (9, 8), (10, 8)]
        assert (df["lineage_id"] == 1).all()

    def test_daughter_pairs(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe("daughter_cycles", props=[])
        pairs = list(zip(df["cycle_id_1"], df["cycle_id_2"]))
        assert pairs == [(2, 5), (2, 8), (5, 6), (5, 7), (8, 9), (8, 10)]

    def test_sister_pairs_in_both_orders(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe("sister_cycles", props=[])
        pairs = list(zip(df["cycle_id_1"], df["cycle_id_2"]))
        assert pairs == [(5, 8), (6, 7), (7, 6), (8, 5), (9, 10), (10, 9)]

    def test_cousin_pairs(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe("cousin_cycles", props=[])
        pairs = list(zip(df["cycle_id_1"], df["cycle_id_2"]))
        assert pairs == [
            (6, 9), (6, 10), (7, 9), (7, 10), (9, 6), (9, 7), (10, 6), (10, 7)
        ]  # fmt: skip

    def test_unique_pairs_keep_lower_id_first(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe(
            "sister_cycles", props=[], unique_pairs=True
        )
        pairs = list(zip(df["cycle_id_1"], df["cycle_id_2"]))
        assert pairs == [(5, 8), (6, 7), (9, 10)]

    def test_unique_pairs_keep_pairs_listed_from_one_side(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe(
            "mother_cycle", props=[], unique_pairs=True
        )
        pairs = list(zip(df["cycle_id_1"], df["cycle_id_2"]))
        assert pairs == [(5, 2), (6, 5), (7, 5), (8, 2), (9, 8), (10, 8)]

    def test_unique_pairs_keep_cycle_listed_by_itself(self, relatives_model):
        prop = root_relation_property()
        relatives_model.add_custom_property(RootRelation(prop, [2, 5]))
        relatives_model.update()
        df = relatives_model.to_cycle_pair_dataframe(
            "root_relation", props=[], unique_pairs=True
        )
        pairs = list(zip(df["cycle_id_1"], df["cycle_id_2"]))
        assert pairs == [(2, 2), (2, 5)]

    def test_props_of_both_cycles(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe(
            "mother_cycle", props=["cycle_length", "level"]
        )
        assert df.columns.tolist() == [
            "lineage_id",
            "cycle_id_1",
            "cycle_id_2",
            "cycle_length_1",
            "cycle_length_2",
            "level_1",
            "level_2",
        ]
        row = df[df["cycle_id_1"] == 6].iloc[0]
        assert (row["cycle_length_1"], row["cycle_length_2"]) == (1, 2)
        assert (row["level_1"], row["level_2"]) == (2, 1)

    def test_all_props_by_default(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe("mother_cycle")
        cycle_columns = relatives_model.to_cycle_dataframe().columns
        props = [col for col in cycle_columns if col not in ["lineage_id", "cycle_id"]]
        expected = [f"{prop}{suffix}" for prop in props for suffix in ["_1", "_2"]]
        assert df.columns.tolist()[3:] == expected

    def test_list_values_kept(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe("mother_cycle", props=["cells"])
        row = df[df["cycle_id_1"] == 5].iloc[0]
        assert row["cells_1"] == [3, 5]
        assert row["cells_2"] == [1, 2]

    def test_custom_suffixes(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe(
            "mother_cycle", props=["cycle_length"], suffixes=("", "_mother")
        )
        assert df.columns.tolist() == [
            "lineage_id",
            "cycle_id",
            "cycle_id_mother",
            "cycle_length",
            "cycle_length_mother",
        ]

    def test_id_props_not_repeated(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe(
            "mother_cycle", props=["lineage_id", "cycle_id", "level"]
        )
        assert df.columns.tolist() == [
            "lineage_id",
            "cycle_id_1",
            "cycle_id_2",
            "level_1",
            "level_2",
        ]

    def test_lineage_without_pairs_gives_empty_dataframe(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe(
            "mother_cycle", props=["level"], lids=[-11]
        )
        assert df.empty
        assert df.columns.tolist() == [
            "lineage_id",
            "cycle_id_1",
            "cycle_id_2",
            "level_1",
            "level_2",
        ]

    def test_lids(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe("sister_cycles", lids=[1])
        assert (df["lineage_id"] == 1).all()
        assert len(df) == 6

    def test_lineage_props_added_as_columns(self, relatives_model):
        df = relatives_model.to_cycle_pair_dataframe(
            "mother_cycle", props=[], lineage_props=["lin_prop"]
        )
        assert df.columns.tolist()[-1] == "lin_prop"
        assert (df["lin_prop"] == 1.5).all()

    def test_user_defined_relation(self, relatives_model):
        prop = root_relation_property()
        relatives_model.add_custom_property(RootRelation(prop, [6, 10]))
        relatives_model.update()
        df = relatives_model.to_cycle_pair_dataframe("root_relation", props=[])
        pairs = list(zip(df["lineage_id"], df["cycle_id_1"], df["cycle_id_2"]))
        assert pairs == [(1, 2, 6), (1, 2, 10)]

    def test_related_cycle_not_in_lineage_raises(self, relatives_model):
        prop = root_relation_property()
        relatives_model.add_custom_property(RootRelation(prop, [99]))
        relatives_model.update()
        with pytest.raises(ValueError, match="Cell cycle 99, listed in property"):
            relatives_model.to_cycle_pair_dataframe("root_relation")

    def test_relation_without_values_raises(self, relatives_model):
        # Declared, but not computed: no update since.
        prop = root_relation_property()
        relatives_model.add_custom_property(RootRelation(prop, [6]))
        with pytest.raises(ValueError, match="No cell cycle has a value"):
            relatives_model.to_cycle_pair_dataframe("root_relation")

    def test_undeclared_relation_prop_raises(self, relatives_model):
        with pytest.raises(ValueError, match="'grandmother_cycle'"):
            relatives_model.to_cycle_pair_dataframe("grandmother_cycle")

    def test_relation_prop_of_cell_lineages_raises(self, relatives_model):
        with pytest.raises(ValueError, match="'lin_prop'"):
            relatives_model.to_cycle_pair_dataframe("lin_prop")

    def test_undeclared_prop_raises(self, relatives_model):
        with pytest.raises(ValueError, match="'cell_area'"):
            relatives_model.to_cycle_pair_dataframe(
                "mother_cycle", props=["level", "cell_area"]
            )

    def test_same_suffixes_raise(self, relatives_model):
        with pytest.raises(ValueError, match="The two suffixes must differ"):
            relatives_model.to_cycle_pair_dataframe(
                "mother_cycle", suffixes=("_a", "_a")
            )

    def test_suffixes_giving_same_column_name_raise(self, relatives_model):
        # "cycle_length" with the suffix "_mother" is named like this property.
        clashing = Property(
            identifier="cycle_length_mother",
            name="clashing",
            description="Named like a suffixed column",
            provenance="test",
            prop_type="node",
            lin_type="CycleLineage",
            dtype="int",
        )
        relatives_model.props_metadata._add_prop(clashing)
        with pytest.raises(ValueError, match="give the same name to two columns"):
            relatives_model.to_cycle_pair_dataframe(
                "mother_cycle",
                props=["cycle_length", "cycle_length_mother"],
                suffixes=("", "_mother"),
            )

    def test_no_cycle_data_raises(self, lineage_props_model):
        with pytest.raises(ValueError, match="Cycle lineages have not been computed"):
            lineage_props_model.to_cycle_pair_dataframe("mother_cycle")


@pytest.fixture()
def frame_time_model():
    """
    Create a model with a dividing lineage whose reference time property "time" is
    given in frames, with a time origin different from 0.
    """
    lin = CellLineage(lid=1)
    lin.add_node(1, cell_id=1, time=3)
    lin.add_node(2, cell_id=2, time=4)
    lin.add_node(3, cell_id=3, time=5)
    lin.add_node(4, cell_id=4, time=5)
    lin.add_edge(1, 2)
    lin.add_edge(2, 3)
    lin.add_edge(2, 4)

    time_prop = create_time_property(unit="frame")
    time_prop.dtype = "int"
    return Model(
        model_metadata={"time_step": 1, "time_unit": "frame"},
        props_metadata=PropsMetadata(props={"time": time_prop}),
        data=Data({1: lin}),
        reference_time_property="time",
    )


class TestRescaleTime:
    """Test cases for Model.rescale_time() method."""

    def test_time_values_multiplied(self, frame_time_model):
        frame_time_model.rescale_time(5)
        lin = frame_time_model.data.cell_data[1]
        assert dict(lin.nodes(data="time")) == {1: 15, 2: 20, 3: 25, 4: 25}

    def test_time_step_multiplied(self, frame_time_model):
        frame_time_model.rescale_time(5)
        assert frame_time_model.get_time_step() == 5

    def test_update_required(self, frame_time_model):
        frame_time_model.rescale_time(5)
        assert frame_time_model.is_update_required()

    def test_timepoints_unchanged_after_update(self, frame_time_model):
        lin = frame_time_model.data.cell_data[1]
        timepoints = dict(lin.nodes(data="timepoint"))
        frame_time_model.rescale_time(5)
        frame_time_model.update()
        lin = frame_time_model.data.cell_data[1]
        assert dict(lin.nodes(data="timepoint")) == timepoints

    def test_timepoints_unchanged_after_partial_update(self, frame_time_model):
        lin = frame_time_model.data.cell_data[1]
        timepoints = dict(lin.nodes(data="timepoint"))
        frame_time_model.rescale_time(5)
        time_copy_prop = create_time_property(unit=None, custom_identifier="time_copy")
        calc = Time(time_copy_prop, time_prop="time", factor=1)
        frame_time_model.add_custom_property(calc)
        frame_time_model.update(["time_copy"])
        lin = frame_time_model.data.cell_data[1]
        assert dict(lin.nodes(data="timepoint")) == timepoints
        assert dict(lin.nodes(data="time_copy")) == {1: 15, 2: 20, 3: 25, 4: 25}

    def test_time_unit_set(self, frame_time_model):
        frame_time_model.rescale_time(5, time_unit="min")
        assert frame_time_model.get_time_unit() == "min"
        assert frame_time_model.get_property("time").unit == "min"

    def test_no_time_unit_keeps_units(self, frame_time_model):
        frame_time_model.rescale_time(5)
        assert frame_time_model.get_time_unit() == "frame"
        assert frame_time_model.get_property("time").unit == "frame"

    def test_float_factor_sets_float_dtype(self, frame_time_model):
        frame_time_model.rescale_time(0.5)
        assert frame_time_model.get_property("time").dtype == "float"

    def test_int_factor_keeps_int_dtype(self, frame_time_model):
        frame_time_model.rescale_time(5)
        assert frame_time_model.get_property("time").dtype == "int"

    def test_cycle_duration_rescaled(self, frame_time_model):
        frame_time_model.add_cycle_data()
        durations = dict(frame_time_model.data.cycle_data[1].nodes(data="cycle_duration"))
        frame_time_model.rescale_time(5, time_unit="min")
        frame_time_model.update()
        cycle_lin = frame_time_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="cycle_duration")) == {
            cid: duration * 5 for cid, duration in durations.items()
        }
        assert frame_time_model.get_property("cycle_duration").unit == "min"

    def test_cycle_start_time_rescaled(self, frame_time_model):
        frame_time_model.add_cycle_data()
        cycle_lin = frame_time_model.data.cycle_data[1]
        start_times = dict(cycle_lin.nodes(data="cycle_start_time"))
        frame_time_model.rescale_time(5, time_unit="min")
        frame_time_model.update()
        cycle_lin = frame_time_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="cycle_start_time")) == {
            cid: start_time * 5 for cid, start_time in start_times.items()
        }
        assert frame_time_model.get_property("cycle_start_time").unit == "min"

    def test_cycle_end_time_rescaled(self, frame_time_model):
        frame_time_model.add_cycle_data()
        cycle_lin = frame_time_model.data.cycle_data[1]
        end_times = dict(cycle_lin.nodes(data="cycle_end_time"))
        frame_time_model.rescale_time(5, time_unit="min")
        frame_time_model.update()
        cycle_lin = frame_time_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="cycle_end_time")) == {
            cid: end_time * 5 for cid, end_time in end_times.items()
        }
        assert frame_time_model.get_property("cycle_end_time").unit == "min"

    def test_zero_factor_raises(self, frame_time_model):
        with pytest.raises(ValueError, match="strictly positive"):
            frame_time_model.rescale_time(0)

    def test_negative_factor_raises(self, frame_time_model):
        with pytest.raises(ValueError, match="strictly positive"):
            frame_time_model.rescale_time(-5)

    def test_timepoint_reference_time_raises(self):
        model = MagicMock()
        model.reference_time_property = "timepoint"
        with pytest.raises(ValueError, match="Cannot rescale the 'timepoint'"):
            Model.rescale_time(model, 5)

    def test_reference_time_calculator_warns(self, frame_time_model):
        calc = Time(create_time_property(unit=None), time_prop="timepoint", factor=5)
        frame_time_model._updater.register_calculator(calc)
        with pytest.warns(UserWarning, match="has a calculator"):
            frame_time_model.rescale_time(5)


@pytest.fixture()
def two_times_model():
    """
    Create a model with a dividing lineage and two time properties: "time" in
    minutes, the reference time property, and "frame".

    Cell cycles (ID = last cell): 2 (cells 1-2) divides into 4 (cell 4) and 5
    (cells 3 and 5).
    """
    lin = CellLineage(lid=1)
    for cell_id, frame in [(1, 0), (2, 1), (3, 2), (4, 2), (5, 3)]:
        lin.add_node(cell_id, cell_id=cell_id, frame=frame, time=5 * frame)
    for source, target in [(1, 2), (2, 3), (2, 4), (3, 5)]:
        lin.add_edge(source, target)

    props = {
        "time": create_time_property(unit="min"),
        "frame": create_frame_property(),
    }
    return Model(
        model_metadata={"time_step": 5, "time_unit": "min"},
        props_metadata=PropsMetadata(props=props),
        data=Data({1: lin}),
        reference_time_property="time",
    )


class TestSetReferenceTimeProperty:
    """Test cases for Model.set_reference_time_property() method."""

    def test_cycle_duration_in_new_reference(self, two_times_model):
        two_times_model.add_cycle_data()
        two_times_model.set_reference_time_property("frame")
        two_times_model.update()
        cycle_lin = two_times_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="cycle_duration")) == {2: 1, 4: 0, 5: 1}
        assert two_times_model.get_property("cycle_duration").unit == "frame"

    def test_cycle_start_time_in_new_reference(self, two_times_model):
        two_times_model.add_cycle_data()
        two_times_model.set_reference_time_property("frame")
        two_times_model.update()
        cycle_lin = two_times_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="cycle_start_time")) == {2: 0, 4: 2, 5: 2}
        assert two_times_model.get_property("cycle_start_time").unit == "frame"

    def test_cycle_end_time_in_new_reference(self, two_times_model):
        two_times_model.add_cycle_data()
        two_times_model.set_reference_time_property("frame")
        two_times_model.update()
        cycle_lin = two_times_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="cycle_end_time")) == {2: 1, 4: 2, 5: 3}
        assert two_times_model.get_property("cycle_end_time").unit == "frame"

    def test_without_cycle_data(self, two_times_model):
        two_times_model.set_reference_time_property("frame")
        assert two_times_model.get_time_unit() == "frame"
        assert two_times_model.get_property("cycle_duration") is None


@pytest.fixture()
def pixel_space_model():
    """
    Create a 3D model with a two-cell lineage whose cell, link and lineage coordinates
    are given in pixels.
    """
    lin = CellLineage(lid=1)
    lin.add_node(1, cell_id=1, frame=0, cell_x=10, cell_y=20, cell_z=2)
    lin.add_node(2, cell_id=2, frame=1, cell_x=30, cell_y=40, cell_z=4)
    lin.add_edge(1, 2, link_x=20, link_y=30, link_z=3)
    lin.graph.update(lineage_x=20, lineage_y=30, lineage_z=3)

    props = {}
    for axis in ("x", "y", "z"):
        for create_prop in (
            create_cell_coord_property,
            create_link_coord_property,
            create_lineage_coord_property,
        ):
            prop = create_prop(unit="pixel", axis=axis)
            props[prop.identifier] = prop
    props["cell_x"].dtype = "int"
    return Model(
        model_metadata={
            "time_step": 1,
            "space_unit": "pixel",
            "pixel_width": 1.0,
            "pixel_height": 1.0,
            "pixel_depth": 2.0,
        },
        props_metadata=PropsMetadata(props=props),
        data=Data({1: lin}),
        reference_time_property="frame",
    )


class TestRescaleSpace:
    """Test cases for Model.rescale_space() method."""

    def test_cell_coordinates_multiplied(self, pixel_space_model):
        pixel_space_model.rescale_space(2)
        lin = pixel_space_model.data.cell_data[1]
        assert lin.nodes[1]["cell_x"] == 20
        assert lin.nodes[1]["cell_y"] == 40
        assert lin.nodes[1]["cell_z"] == 4

    def test_z_factor_applied_to_z_only(self, pixel_space_model):
        pixel_space_model.rescale_space(2, z_factor=10)
        lin = pixel_space_model.data.cell_data[1]
        assert lin.nodes[2]["cell_x"] == 60
        assert lin.nodes[2]["cell_z"] == 40
        assert lin.edges[1, 2]["link_z"] == 30
        assert lin.graph["lineage_z"] == 30

    def test_link_coordinates_multiplied(self, pixel_space_model):
        pixel_space_model.rescale_space(2)
        lin = pixel_space_model.data.cell_data[1]
        assert lin.edges[1, 2]["link_x"] == 40
        assert lin.edges[1, 2]["link_y"] == 60

    def test_lineage_coordinates_multiplied(self, pixel_space_model):
        pixel_space_model.rescale_space(2)
        lin = pixel_space_model.data.cell_data[1]
        assert lin.graph["lineage_x"] == 40
        assert lin.graph["lineage_y"] == 60

    def test_pixel_size_multiplied(self, pixel_space_model):
        pixel_space_model.rescale_space(0.5, z_factor=3)
        assert pixel_space_model.get_pixel_width() == 0.5
        assert pixel_space_model.get_pixel_height() == 0.5
        assert pixel_space_model.get_pixel_depth() == 6.0

    def test_undefined_pixel_size_stays_undefined(self, pixel_space_model):
        pixel_space_model.model_metadata.pixel_depth = None
        pixel_space_model.rescale_space(2)
        assert pixel_space_model.get_pixel_depth() is None

    def test_space_unit_set(self, pixel_space_model):
        pixel_space_model.rescale_space(0.5, space_unit="um")
        assert pixel_space_model.get_space_unit() == "um"
        for prop_id in ("cell_x", "link_y", "lineage_z"):
            assert pixel_space_model.get_property(prop_id).unit == "um"

    def test_no_space_unit_keeps_units(self, pixel_space_model):
        pixel_space_model.rescale_space(0.5)
        assert pixel_space_model.get_space_unit() == "pixel"
        assert pixel_space_model.get_property("cell_x").unit == "pixel"

    def test_float_factor_sets_float_dtype(self, pixel_space_model):
        pixel_space_model.rescale_space(0.5)
        assert pixel_space_model.get_property("cell_x").dtype == "float"

    def test_update_required(self, pixel_space_model):
        pixel_space_model.rescale_space(2)
        assert pixel_space_model.is_update_required()

    def test_zero_factor_raises(self, pixel_space_model):
        with pytest.raises(ValueError, match="'factor' must be strictly positive"):
            pixel_space_model.rescale_space(0)

    def test_negative_z_factor_raises(self, pixel_space_model):
        with pytest.raises(ValueError, match="'z_factor' must be strictly positive"):
            pixel_space_model.rescale_space(2, z_factor=-1)

    def test_coordinate_calculator_warns(self, pixel_space_model):
        prop = create_cell_coord_property(unit=None, axis="x")
        calc = Time(prop, time_prop="frame", factor=1)
        pixel_space_model._updater.register_calculator(calc)
        with pytest.warns(UserWarning, match="'cell_x' has a calculator"):
            pixel_space_model.rescale_space(2)


class TestAddLocationTag:
    """Test cases for Model.add_location_tag() method."""

    def test_int_dtype_without_tag_names(self, pixel_space_model, tmp_path):
        mask_path = tmp_path / "mask.tif"
        tifffile.imwrite(mask_path, np.zeros((2, 50, 50), dtype=np.uint8))
        pixel_space_model.add_location_tag(mask_path=str(mask_path))
        assert pixel_space_model.get_property("location_tag").dtype == "int"

    def test_str_dtype_with_tag_names(self, pixel_space_model, tmp_path):
        mask_path = tmp_path / "mask.tif"
        tifffile.imwrite(mask_path, np.zeros((2, 50, 50), dtype=np.uint8))
        pixel_space_model.add_location_tag(
            mask_path=str(mask_path), tag_names={0: "a"}
        )
        assert pixel_space_model.get_property("location_tag").dtype == "str"

    def test_missing_tag_name_value_warns_at_caller(self, pixel_space_model, tmp_path):
        mask_path = tmp_path / "mask.tif"
        tifffile.imwrite(mask_path, np.zeros((2, 50, 50), dtype=np.uint8))
        with pytest.warns(UserWarning, match=r"\[1\] are not in the mask") as record:
            pixel_space_model.add_location_tag(
                mask_path=str(mask_path), tag_names={0: "a", 1: "b"}
            )
        assert Path(record[0].filename).samefile(__file__)


def _create_test_property(
    identifier: str,
    prop_type: str | list[str],
    lin_type: str = "CellLineage",
    dtype: str = "float",
    unit: str | None = None,
) -> Property:
    """Create a property declared by the user, for testing input properties."""
    return Property(
        identifier=identifier,
        name=identifier,
        description=identifier,
        provenance="test",
        prop_type=prop_type,
        lin_type=lin_type,
        dtype=dtype,
        unit=unit,
    )


@pytest.fixture()
def input_props_model():
    """
    Create a model with cycle lineages and user-declared properties that can be used
    as inputs of predefined properties: a cell area, a cell polygon and a cell speed.
    Cycles: 2 = [1, 2], 3 = [3] and 4 = [4].
    """
    lin = CellLineage(lid=1)
    for nid, time in [(1, 0), (2, 1), (3, 2), (4, 2)]:
        lin.add_node(
            nid,
            cell_id=nid,
            time=time,
            my_area=float(nid),
            my_polygon=Polygon([(0, 0), (nid, 0), (nid, 1), (0, 1)]),
        )
    for source, target, speed in [(1, 2, 1.0), (2, 3, 2.0), (2, 4, 3.0)]:
        lin.add_edge(source, target, my_speed=speed)

    time_prop = create_time_property(unit="frame")
    time_prop.dtype = "int"
    props = [
        time_prop,
        _create_test_property("my_area", "node", unit="um^2"),
        _create_test_property("my_polygon", "node", dtype="shapely.Polygon", unit="um"),
        _create_test_property("my_speed", "edge", unit="um/frame"),
    ]
    model = Model(
        model_metadata={"time_step": 1, "time_unit": "frame"},
        props_metadata=PropsMetadata(props={prop.identifier: prop for prop in props}),
        data=Data({1: lin}),
        reference_time_property="time",
    )
    model.add_cycle_data()
    return model


class TestCheckInputProps:
    """Test cases for Model._check_input_props() method."""

    def test_declared_input_passes(self, input_props_model):
        calc = CycleMeanArea(create_cycle_mean_area_property(), area_prop="my_area")
        input_props_model._check_input_props(calc)

    def test_missing_pycellin_input_suggests_add_method(self, input_props_model):
        calc = CycleMeanArea(create_cycle_mean_area_property())
        with pytest.raises(MissingPropertyError, match=r"model\.add_cell_area\(\)"):
            input_props_model._check_input_props(calc)

    def test_missing_input_suggests_parameter(self, input_props_model):
        calc = CycleMeanArea(create_cycle_mean_area_property(), area_prop="unknown")
        with pytest.raises(MissingPropertyError, match="set 'area_prop'") as exc_info:
            input_props_model._check_input_props(calc)
        assert "add_" not in str(exc_info.value)

    def test_wrong_prop_type_raises(self, input_props_model):
        calc = CycleMeanArea(create_cycle_mean_area_property(), area_prop="my_speed")
        with pytest.raises(ValueError, match="prop_type 'node'"):
            input_props_model._check_input_props(calc)

    def test_wrong_lin_type_raises(self, input_props_model):
        calc = CycleMeanArea(
            create_cycle_mean_area_property(), area_prop="cycle_length"
        )
        with pytest.raises(ValueError, match="lin_type 'CellLineage'"):
            input_props_model._check_input_props(calc)

    def test_lineage_lin_type_accepted(self, input_props_model):
        input_props_model.props_metadata._add_prop(
            _create_test_property("any_lin_area", "node", lin_type="Lineage")
        )
        calc = CycleMeanArea(
            create_cycle_mean_area_property(), area_prop="any_lin_area"
        )
        input_props_model._check_input_props(calc)

    def test_multi_type_prop_accepted(self, input_props_model):
        input_props_model.props_metadata._add_prop(
            _create_test_property("node_lin_area", ["node", "lineage"])
        )
        calc = CycleMeanArea(
            create_cycle_mean_area_property(), area_prop="node_lin_area"
        )
        input_props_model._check_input_props(calc)

    def test_property_object_raises(self, input_props_model):
        area_prop = input_props_model.get_property("my_area")
        calc = CycleMeanArea(create_cycle_mean_area_property(), area_prop=area_prop)
        with pytest.raises(TypeError, match="Pass its identifier instead: 'my_area'"):
            input_props_model._check_input_props(calc)

    def test_non_string_input_raises(self, input_props_model):
        calc = CycleMeanArea(create_cycle_mean_area_property(), area_prop=1)
        with pytest.raises(TypeError, match="'area_prop' must be the identifier"):
            input_props_model._check_input_props(calc)


class TestGetInputProp:
    """Test cases for Model._get_input_prop() method."""

    def test_declared_prop(self, input_props_model):
        assert input_props_model._get_input_prop("my_area").identifier == "my_area"

    def test_undeclared_prop_returns_none(self, input_props_model):
        assert input_props_model._get_input_prop("unknown") is None

    def test_property_object_returns_none(self, input_props_model):
        area_prop = input_props_model.get_property("my_area")
        assert input_props_model._get_input_prop(area_prop) is None


class TestAddCustomProperty:
    """Test cases for Model.add_custom_property() method."""

    def test_missing_input_prop_not_added(self, input_props_model):
        calc = CycleMeanArea(create_cycle_mean_area_property())
        with pytest.raises(MissingPropertyError):
            input_props_model.add_custom_property(calc)
        assert input_props_model.get_property("cycle_mean_area") is None

    def test_readding_replaces_declaration(self, two_times_model):
        two_times_model.add_absolute_age()
        with pytest.warns(UserWarning, match="Overwriting the old Property"):
            two_times_model.add_absolute_age(time_prop="frame")
        prop = two_times_model.get_property("absolute_age")
        assert (prop.dtype, prop.unit) == ("int", "frame")

    def test_prop_declared_otherwise_with_values_raises(self, input_props_model):
        # E.g. a cycle property propagated to cell lineages, loaded from a file.
        prop = _create_test_property("mother_cycle", "node", dtype="int")
        input_props_model.props_metadata._add_prop(prop)
        for _, cell in input_props_model.data.cell_data[1].nodes(data=True):
            cell["mother_cycle"] = 2
        with pytest.raises(ValueError, match="declared as a node property of cell"):
            input_props_model.add_mother_cycle()
        assert input_props_model.get_property("mother_cycle") is prop
        assert "mother_cycle" not in input_props_model._updater._calculators

    def test_unused_prop_declared_otherwise_replaced(self, input_props_model):
        # E.g. declared in a file without values.
        prop = _create_test_property("mother_cycle", "node", dtype="int")
        input_props_model.props_metadata._add_prop(prop)
        input_props_model.add_mother_cycle()
        input_props_model.update()
        assert input_props_model.get_property("mother_cycle").lin_type == "CycleLineage"
        assert input_props_model.data.cycle_data[1].nodes[3]["mother_cycle"] == 2

    def test_readding_propagated_prop_keeps_lineage_type(self, input_props_model):
        input_props_model.add_mother_cycle()
        input_props_model.propagate_cycle_properties(["mother_cycle"])
        with pytest.warns(UserWarning, match="Overwriting the old Property"):
            input_props_model.add_mother_cycle()
        assert input_props_model.get_property("mother_cycle").lin_type == "Lineage"


class InputCopy(NodeLocalPropCalculator):
    """User-defined property copying another node property of cell lineages."""

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "input_prop": ("node", "CellLineage")
    }

    def __init__(self, property, input_prop):
        super().__init__(property)
        self.input_prop = input_prop

    def compute(self, lineage, nid):
        return lineage.nodes[nid][self.input_prop]


class ConstantValue(NodeLocalPropCalculator):
    """User-defined property with the same value on every cell."""

    def __init__(self, property, value):
        super().__init__(property)
        self.value = value

    def compute(self, lineage, nid):
        return self.value


class DoubledAreaCopy(NodeLocalPropCalculator):
    """User-defined property doubling 'area_copy', which it reads without declaring
    it."""

    def compute(self, lineage, nid):
        return 2 * lineage.nodes[nid]["area_copy"]


class ConstantLinkValue(EdgeLocalPropCalculator):
    """User-defined property with the same value on every link."""

    def __init__(self, property, value):
        super().__init__(property)
        self.value = value

    def compute(self, lineage, edge):
        return self.value


@pytest.fixture()
def two_lineages_model():
    """
    Create an updated model with cycle lineages, a cell property and a link property.
    Lineage 1: 1 -> 2 -> 3 and 1 -> 4 -> 5. Lineage 2: 10 -> 11.
    """
    lin1 = CellLineage(lid=1)
    for nid, time in [(1, 0), (2, 1), (3, 2), (4, 1), (5, 2)]:
        lin1.add_node(nid, cell_id=nid, time=time)
    for source, target in [(1, 2), (2, 3), (1, 4), (4, 5)]:
        lin1.add_edge(source, target)
    lin2 = CellLineage(lid=2)
    for nid, time in [(10, 0), (11, 1)]:
        lin2.add_node(nid, cell_id=nid, time=time)
    lin2.add_edge(10, 11)

    time_prop = create_time_property(unit="frame")
    time_prop.dtype = "int"
    model = Model(
        model_metadata={"time_step": 1, "time_unit": "frame"},
        props_metadata=PropsMetadata(props={"time": time_prop}),
        data=Data({1: lin1, 2: lin2}),
        reference_time_property="time",
    )
    model.add_custom_property(
        ConstantValue(_create_test_property("cell_value", "node"), 1.0)
    )
    model.add_custom_property(
        ConstantLinkValue(_create_test_property("link_value", "edge"), 1.0)
    )
    model.add_cycle_data()
    model.update()
    return model


class TestUpdate:
    """Test cases for Model.update() method."""

    def test_partial_update_keeps_other_cycle_props(self, input_props_model):
        input_props_model.add_division_time()
        input_props_model.update()
        division_times = dict(
            input_props_model.data.cycle_data[1].nodes(data="division_time")
        )
        # The cycle lineages are rebuilt at the first update after adding a property.
        input_props_model.add_mother_cycle()
        input_props_model.update(["mother_cycle"])
        cycle_lin = input_props_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="division_time")) == pytest.approx(
            division_times, nan_ok=True
        )
        assert cycle_lin.nodes[3]["mother_cycle"] == 2

    def test_props_left_out_computed_by_next_update(self, input_props_model):
        input_props_model.add_absolute_age()
        input_props_model.add_relative_age()
        input_props_model.update(["absolute_age"])
        assert input_props_model.is_update_required()
        input_props_model.update()
        lin = input_props_model.data.cell_data[1]
        assert dict(lin.nodes(data="relative_age")) == {1: 0, 2: 1, 3: 0, 4: 0}

    def test_partial_update_of_all_props_completes(self, input_props_model):
        input_props_model.add_absolute_age()
        input_props_model.update(["absolute_age"])
        assert not input_props_model.is_update_required()

    def test_partial_update_after_edit(self, input_props_model):
        input_props_model.add_absolute_age()
        input_props_model.add_division_time()
        input_props_model.update()
        input_props_model.add_cell(lid=1, cid=5, time_value=3)
        input_props_model.add_link(source_cid=3, source_lid=1, target_cid=5)
        input_props_model.update(["absolute_age"])
        assert input_props_model.data.cell_data[1].nodes[5]["absolute_age"] == 3
        cycle_lin = input_props_model.data.cycle_data[1]
        assert all("division_time" in cycle for _, cycle in cycle_lin.nodes(data=True))

    def test_undeclared_prop_ignored(self, input_props_model):
        input_props_model.add_absolute_age()
        with pytest.warns(UserWarning, match="not been declared and will be ignored"):
            input_props_model.update(["unknown", "absolute_age"])
        assert input_props_model.data.cell_data[1].nodes[3]["absolute_age"] == 2

    def test_prop_without_calculator_ignored(self, input_props_model):
        input_props_model.add_absolute_age()
        with pytest.warns(UserWarning, match="no calculator and will be ignored"):
            input_props_model.update(["my_area", "absolute_age"])
        assert input_props_model.data.cell_data[1].nodes[3]["absolute_age"] == 2

    def test_only_props_without_calculator_no_update(self, input_props_model):
        input_props_model.add_absolute_age()
        with pytest.warns(UserWarning) as record:
            input_props_model.update(["my_area"])
        messages = [str(warning.message) for warning in record]
        assert any("no calculator" in message for message in messages)
        assert any("No properties to update" in message for message in messages)
        assert input_props_model.is_update_required()
        assert "absolute_age" not in input_props_model.data.cell_data[1].nodes[3]

    def test_input_computed_before_its_reader(self, input_props_model):
        # 'my_area' has values but no calculator, as if loaded from a file.
        copy_prop = _create_test_property("area_copy", "node")
        input_props_model.add_custom_property(InputCopy(copy_prop, "my_area"))
        input_props_model.update()
        area_prop = _create_test_property("my_area", "node", unit="um^2")
        with pytest.warns(UserWarning, match="Overwriting the old Property"):
            input_props_model.add_custom_property(ConstantValue(area_prop, 10.0))
        input_props_model.update()
        lin = input_props_model.data.cell_data[1]
        assert set(dict(lin.nodes(data="area_copy")).values()) == {10.0}

    def test_undeclared_reader_kept_after_what_it_reads(self, input_props_model):
        copy_prop = _create_test_property("area_copy", "node")
        input_props_model.add_custom_property(InputCopy(copy_prop, "my_area"))
        doubled_prop = _create_test_property("doubled_area", "node")
        input_props_model.add_custom_property(DoubledAreaCopy(doubled_prop))
        input_props_model.update()
        area_prop = _create_test_property("my_area", "node", unit="um^2")
        with pytest.warns(UserWarning, match="Overwriting the old Property"):
            input_props_model.add_custom_property(ConstantValue(area_prop, 10.0))
        input_props_model.update()
        lin = input_props_model.data.cell_data[1]
        assert set(dict(lin.nodes(data="doubled_area")).values()) == {20.0}

    def test_split_off_lineage_with_removed_id_computed(self, two_lineages_model):
        # Removing link 2 -> 3 splits lineage 1 at the update, and the split-off
        # lineage, with the new cell 6, gets ID 2, the ID of the removed lineage.
        two_lineages_model.remove_lineage(2)
        two_lineages_model.remove_link(source_cid=2, target_cid=3, lid=1)
        two_lineages_model.add_cell(lid=1, cid=6, time_value=3)
        two_lineages_model.add_link(source_cid=3, source_lid=1, target_cid=6)
        two_lineages_model.update()
        assert set(two_lineages_model.data.cell_data[2].nodes) == {3, 6}
        assert two_lineages_model.data.cell_data[2].nodes[6]["cell_value"] == 1.0
        assert 2 in two_lineages_model.data.cycle_data


class TestAddLineage:
    """Test cases for Model.add_lineage() method."""

    def test_lineage_removed_then_added_back_kept(self, two_lineages_model):
        lineage = two_lineages_model.remove_lineage(2)
        two_lineages_model.add_lineage(lineage)
        two_lineages_model.update()
        assert set(two_lineages_model.data.cell_data[2].nodes) == {10, 11}
        assert 2 in two_lineages_model.data.cycle_data

    def test_cell_removed_before_lineage_added_back_computed(
        self, two_lineages_model
    ):
        two_lineages_model.remove_cell(cid=11, lid=2)
        lineage = two_lineages_model.remove_lineage(2)
        lineage.add_node(11, cell_id=11, time=1)
        lineage.add_edge(10, 11)
        two_lineages_model.add_lineage(lineage)
        two_lineages_model.update()
        assert two_lineages_model.data.cell_data[2].nodes[11]["cell_value"] == 1.0

    def test_link_removed_before_lineage_added_back_computed(
        self, two_lineages_model
    ):
        two_lineages_model.remove_link(source_cid=10, target_cid=11, lid=2)
        lineage = two_lineages_model.remove_lineage(2)
        lineage.add_edge(10, 11)
        two_lineages_model.add_lineage(lineage)
        two_lineages_model.update()
        assert two_lineages_model.data.cell_data[2].edges[10, 11]["link_value"] == 1.0


class TestSplitLineageFromCell:
    """Test cases for Model.split_lineage_from_cell() method."""

    def test_split_off_lineage_with_removed_id_kept(self, two_lineages_model):
        # The split-off lineage gets ID 2, the ID of the removed lineage.
        two_lineages_model.remove_lineage(2)
        two_lineages_model.split_lineage_from_cell(cid=4, lid=1)
        two_lineages_model.update()
        assert set(two_lineages_model.data.cell_data[2].nodes) == {4, 5}
        assert 2 in two_lineages_model.data.cycle_data


class TestAddCell:
    """Test cases for Model.add_cell() method."""

    def test_cell_removed_then_added_back_computed(self, two_lineages_model):
        two_lineages_model.remove_cell(cid=5, lid=1)
        two_lineages_model.add_cell(lid=1, cid=5, time_value=2)
        two_lineages_model.add_link(source_cid=4, source_lid=1, target_cid=5)
        two_lineages_model.update()
        cell = two_lineages_model.data.cell_data[1].nodes[5]
        assert cell["timepoint"] == 2
        assert cell["cell_value"] == 1.0


class TestAddLink:
    """Test cases for Model.add_link() method."""

    def test_link_removed_then_added_back_computed(self, two_lineages_model):
        two_lineages_model.remove_link(source_cid=4, target_cid=5, lid=1)
        two_lineages_model.add_link(source_cid=4, source_lid=1, target_cid=5)
        two_lineages_model.update()
        assert two_lineages_model.data.cell_data[1].edges[4, 5]["link_value"] == 1.0


class TestAddCellArea:
    """Test cases for Model.add_cell_area() method."""

    def test_missing_default_polygon_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="add_cell_polygon"):
            input_props_model.add_cell_area()

    def test_custom_polygon_prop(self, input_props_model):
        input_props_model.add_cell_area(polygon_prop="my_polygon")
        input_props_model.update()
        assert input_props_model.data.cell_data[1].nodes[3]["cell_area"] == 3.0

    def test_unit_from_polygon_prop(self, input_props_model):
        input_props_model.add_cell_area(polygon_prop="my_polygon")
        assert input_props_model.get_property("cell_area").unit == "um^2"


class TestAddCellCircularity:
    """Test cases for Model.add_cell_circularity() method."""

    def test_missing_default_polygon_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="add_cell_polygon"):
            input_props_model.add_cell_circularity()

    def test_custom_polygon_prop(self, input_props_model):
        input_props_model.add_cell_circularity(polygon_prop="my_polygon")
        input_props_model.update()
        circularity = input_props_model.data.cell_data[1].nodes[3]["cell_circularity"]
        # 3x1 rectangle: area 3, perimeter 8.
        assert circularity == pytest.approx(4 * np.pi * 3 / 8**2)

    def test_no_unit(self, input_props_model):
        input_props_model.add_cell_circularity(polygon_prop="my_polygon")
        assert input_props_model.get_property("cell_circularity").unit is None


class TestAddCellSolidity:
    """Test cases for Model.add_cell_solidity() method."""

    def test_missing_default_polygon_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="add_cell_polygon"):
            input_props_model.add_cell_solidity()

    def test_custom_polygon_prop(self, input_props_model):
        input_props_model.add_cell_solidity(polygon_prop="my_polygon")
        input_props_model.update()
        assert input_props_model.data.cell_data[1].nodes[3]["cell_solidity"] == 1.0

    def test_no_unit(self, input_props_model):
        input_props_model.add_cell_solidity(polygon_prop="my_polygon")
        assert input_props_model.get_property("cell_solidity").unit is None


class TestAddCycleMeanArea:
    """Test cases for Model.add_cycle_mean_area() method."""

    def test_missing_default_area_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="add_cell_area"):
            input_props_model.add_cycle_mean_area()

    def test_default_area_prop(self, input_props_model):
        input_props_model.add_cell_area(polygon_prop="my_polygon")
        input_props_model.add_cycle_mean_area()
        input_props_model.update()
        assert input_props_model.data.cycle_data[1].nodes[2]["cycle_mean_area"] == 1.5

    def test_custom_area_prop(self, input_props_model):
        input_props_model.add_cycle_mean_area(area_prop="my_area")
        input_props_model.update()
        assert input_props_model.data.cycle_data[1].nodes[2]["cycle_mean_area"] == 1.5

    def test_unit_from_area_prop(self, input_props_model):
        input_props_model.add_cycle_mean_area(area_prop="my_area")
        assert input_props_model.get_property("cycle_mean_area").unit == "um^2"


class TestAddCycleMeanSpeed:
    """Test cases for Model.add_cycle_mean_speed() method."""

    def test_missing_default_speed_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="add_cell_speed"):
            input_props_model.add_cycle_mean_speed()

    def test_custom_speed_prop(self, input_props_model):
        input_props_model.add_cycle_mean_speed(
            speed_prop="my_speed", include_incoming_edge=True
        )
        input_props_model.update()
        cycle_lin = input_props_model.data.cycle_data[1]
        assert cycle_lin.nodes[2]["cycle_mean_speed"] == 1.0
        assert cycle_lin.nodes[4]["cycle_mean_speed"] == 3.0

    def test_unit_from_speed_prop(self, input_props_model):
        input_props_model.add_cycle_mean_speed(speed_prop="my_speed")
        assert input_props_model.get_property("cycle_mean_speed").unit == "um/frame"


@pytest.fixture()
def contour_model(input_props_model):
    """
    Add cell positions and contours to input_props_model. Each cell is a 2x1
    rectangle centered on (cell_id, 0).
    """
    for identifier, dtype in [
        ("cell_x", "float"),
        ("cell_y", "float"),
        ("cell_contour", "list[tuple[float, float]]"),
    ]:
        input_props_model.props_metadata._add_prop(
            _create_test_property(identifier, "node", dtype=dtype, unit="um")
        )
    for nid, cell in input_props_model.data.cell_data[1].nodes(data=True):
        cell["cell_x"] = float(nid)
        cell["cell_y"] = 0.0
        cell["cell_contour"] = [(-1, -0.5), (1, -0.5), (1, 0.5), (-1, 0.5)]
    return input_props_model


class TestAddCellPolygon:
    """Test cases for Model.add_cell_polygon() method."""

    def test_label_img_source(self, input_props_model):
        input_props_model.props_metadata._add_prop(
            _create_test_property("label", "node", dtype="int")
        )
        lin = input_props_model.data.cell_data[1]
        for nid in lin.nodes:
            lin.nodes[nid]["label"] = 1
        label_img = np.zeros((3, 6, 6), dtype=np.uint32)
        label_img[:, 1:3, 1:4] = 1
        input_props_model.add_cell_polygon(label_img=label_img)
        input_props_model.update()
        assert lin.nodes[1]["cell_polygon"].bounds == (0.5, 0.5, 3.5, 2.5)
        description = input_props_model.get_property("cell_polygon").description
        assert description.endswith("computed from a label image")

    def test_contour_source(self, contour_model):
        contour_model.add_cell_polygon(source="contour")
        contour_model.update()
        polygon = contour_model.data.cell_data[1].nodes[3]["cell_polygon"]
        assert polygon.bounds == (2.0, -0.5, 4.0, 0.5)
        prop = contour_model.get_property("cell_polygon")
        assert prop.unit == "um"
        assert "computed from the cell contour ('cell_contour')" in prop.description

    def test_contour_source_feeds_cell_area(self, contour_model):
        contour_model.add_cell_polygon(source="contour")
        contour_model.add_cell_area()
        contour_model.update()
        assert contour_model.data.cell_data[1].nodes[3]["cell_area"] == 2.0

    def test_contour_source_through_add_pycellin_property(self, contour_model):
        contour_model.add_pycellin_property("cell_polygon", source="contour")
        contour_model.update()
        polygon = contour_model.data.cell_data[1].nodes[1]["cell_polygon"]
        assert polygon.area == 2.0

    def test_contour_source_missing_contour_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="set 'contour_prop'") as exc:
            input_props_model.add_cell_polygon(source="contour")
        # add_cell_contour() computes contours from cell polygons.
        assert "add_cell_contour" not in str(exc.value)

    def test_contour_source_unit_mismatch_raises(self, contour_model):
        contour_model.get_property("cell_x").unit = "pixel"
        with pytest.raises(ValueError, match="'cell_x' is in 'pixel'"):
            contour_model.add_cell_polygon(source="contour")

    def test_contour_source_unknown_unit_not_checked(self, contour_model):
        contour_model.get_property("cell_contour").unit = None
        contour_model.get_property("cell_y").unit = "unknown"
        contour_model.add_cell_polygon(source="contour")
        assert contour_model.get_property("cell_polygon").unit == "um"

    def test_unknown_source_raises(self, contour_model):
        with pytest.raises(ValueError, match="'source' must be one of"):
            contour_model.add_cell_polygon(source="contours")

    def test_label_img_param_with_contour_source_raises(self, contour_model):
        with pytest.raises(
            ValueError,
            match="'label_prop', 'label_img_path' are not used with source='contour'",
        ):
            contour_model.add_cell_polygon(
                source="contour", label_prop="label", label_img_path="labels.tif"
            )

    def test_contour_param_with_label_img_source_raises(self, contour_model):
        with pytest.raises(
            ValueError, match="'contour_prop' is not used with source='label_img'"
        ):
            contour_model.add_cell_polygon(contour_prop="cell_contour")


class TestAddCellMultipolygon:
    """Test cases for Model.add_cell_multipolygon() method."""

    def test_values(self, input_props_model):
        # Cells 1 and 2 are at timepoints 0 and 1, cells 3 and 4 at timepoint 2.
        input_props_model.props_metadata._add_prop(
            _create_test_property("label", "node", dtype="int")
        )
        lin = input_props_model.data.cell_data[1]
        for nid, label in [(1, 1), (2, 1), (3, 1), (4, 2)]:
            lin.nodes[nid]["label"] = label
        label_img = np.zeros((3, 6, 6), dtype=np.uint32)
        label_img[0, 0:2, 0:2] = label_img[0, 4, 4] = 1
        label_img[1, 1:3, 1:3] = 1
        label_img[2, 0:2, 0:2] = 1
        label_img[2, 3:5, 3:5] = 2
        input_props_model.add_cell_multipolygon(label_img=label_img)
        input_props_model.update()
        multipolygon = lin.nodes[1]["cell_multipolygon"]
        assert isinstance(multipolygon, MultiPolygon)
        assert len(multipolygon.geoms) == 2

    def test_missing_label_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="set 'label_prop'"):
            input_props_model.add_cell_multipolygon(
                label_img=np.zeros((3, 6, 6), dtype=np.uint32)
            )

    def test_no_label_image_raises(self, input_props_model):
        with pytest.raises(ValueError, match="No label image provided"):
            input_props_model.add_cell_multipolygon()


@pytest.fixture()
def intensity_model(input_props_model):
    """
    Add cell labels to input_props_model, and return it with a label image and an
    intensity image. Cells 1, 2 and 3 have label 1, cell 4 has label 2. The value of
    each pixel of the intensity image is 36 * t + 6 * row + column.
    """
    input_props_model.props_metadata._add_prop(
        _create_test_property("label", "node", dtype="int")
    )
    lin = input_props_model.data.cell_data[1]
    for nid, label in [(1, 1), (2, 1), (3, 1), (4, 2)]:
        lin.nodes[nid]["label"] = label
    # Cells 1 and 2 are at timepoints 0 and 1, cells 3 and 4 at timepoint 2.
    label_img = np.zeros((3, 6, 6), dtype=np.uint32)
    label_img[0, 0:2, 0:2] = 1
    label_img[1, 1:3, 1:3] = 1
    label_img[2, 0:2, 0:2] = 1
    label_img[2, 3:5, 3:5] = 2
    intensity_img = np.arange(108, dtype=np.float64).reshape(3, 6, 6)
    return input_props_model, label_img, intensity_img


class TestAddCellTotalIntensity:
    """Test cases for Model.add_cell_total_intensity() method."""

    def test_label_img_source(self, intensity_model):
        model, label_img, intensity_img = intensity_model
        model.add_cell_total_intensity(intensity_img, label_img=label_img)
        model.update()
        lin = model.data.cell_data[1]
        # Cell 1: pixels of values 0, 1, 6 and 7.
        assert lin.nodes[1]["cell_total_intensity"] == 14.0
        # Cell 4: pixels of values 93, 94, 99 and 100.
        assert lin.nodes[4]["cell_total_intensity"] == 386.0

    def test_polygon_source_same_as_label_img(self, intensity_model):
        model, label_img, intensity_img = intensity_model
        model.model_metadata.space_unit = "um"
        model.model_metadata.pixel_width = model.model_metadata.pixel_height = 2.0
        model.add_cell_multipolygon(label_img=label_img)
        model.add_cell_total_intensity(intensity_img, label_img=label_img)
        model.add_cell_total_intensity(
            intensity_img,
            source="polygon",
            polygon_prop="cell_multipolygon",
            custom_identifier="total_from_shapes",
        )
        model.update()
        for _, cell in model.data.cell_data[1].nodes(data=True):
            assert cell["total_from_shapes"] == cell["cell_total_intensity"]

    def test_polygon_source_in_pixels(self, intensity_model):
        """Test that shapes in pixels are not scaled by the pixel size."""
        model, _, intensity_img = intensity_model
        model.model_metadata.pixel_width = model.model_metadata.pixel_height = 2.0
        model.props_metadata._add_prop(
            _create_test_property(
                "pixel_shape", "node", dtype="shapely.Polygon", unit="pixel"
            )
        )
        lin = model.data.cell_data[1]
        for nid in lin.nodes:
            # Contains the centers of the pixels (1, 1) and (1, 2).
            lin.nodes[nid]["pixel_shape"] = Polygon(
                [(0.5, 0.5), (2.5, 0.5), (2.5, 1.5), (0.5, 1.5)]
            )
        model.add_cell_total_intensity(
            intensity_img, source="polygon", polygon_prop="pixel_shape"
        )
        model.update()
        assert lin.nodes[1]["cell_total_intensity"] == 7.0 + 8.0

    def test_intensity_img_path(self, intensity_model, tmp_path):
        model, label_img, intensity_img = intensity_model
        path = tmp_path / "intensity.tif"
        tifffile.imwrite(path, intensity_img, photometric="minisblack")
        model.add_cell_total_intensity(
            intensity_img_path=str(path), label_img=label_img
        )
        model.update()
        assert model.data.cell_data[1].nodes[1]["cell_total_intensity"] == 14.0

    def test_description_says_where_pixels_come_from(self, intensity_model):
        model, label_img, intensity_img = intensity_model
        model.add_cell_total_intensity(
            intensity_img, label_img=label_img, background=10
        )
        description = model.get_property("cell_total_intensity").description
        assert description.endswith(
            "from a label image, minus a background of 10 per pixel"
        )

    def test_no_intensity_image_raises(self, intensity_model):
        model, label_img, _ = intensity_model
        with pytest.raises(ValueError, match="No intensity image provided"):
            model.add_cell_total_intensity(label_img=label_img)

    def test_image_shape_mismatch_raises(self, intensity_model):
        model, label_img, intensity_img = intensity_model
        with pytest.raises(ValueError, match="must have the same shape"):
            model.add_cell_total_intensity(intensity_img[:, :5], label_img=label_img)

    def test_polygon_source_needs_3_axes(self, intensity_model):
        model, _, intensity_img = intensity_model
        with pytest.raises(ValueError, match="must have 3 axes"):
            model.add_cell_total_intensity(
                intensity_img[:, np.newaxis], source="polygon"
            )

    def test_label_img_param_with_polygon_source_raises(self, intensity_model):
        model, label_img, intensity_img = intensity_model
        with pytest.raises(
            ValueError, match="'label_img' is not used with source='polygon'"
        ):
            model.add_cell_total_intensity(
                intensity_img, source="polygon", label_img=label_img
            )

    def test_missing_polygon_prop_suggests_add_cell_polygon(self, intensity_model):
        model, _, intensity_img = intensity_model
        with pytest.raises(MissingPropertyError, match=r"model\.add_cell_polygon\(\)"):
            model.add_cell_total_intensity(intensity_img, source="polygon")


class TestAddCellMeanIntensity:
    """Test cases for Model.add_cell_mean_intensity() method."""

    def test_label_img_source(self, intensity_model):
        model, label_img, intensity_img = intensity_model
        model.add_cell_mean_intensity(intensity_img, label_img=label_img)
        model.update()
        lin = model.data.cell_data[1]
        assert lin.nodes[1]["cell_mean_intensity"] == 3.5
        assert lin.nodes[4]["cell_mean_intensity"] == 96.5


class TestAddCycleMeanIntensity:
    """Test cases for Model.add_cycle_mean_intensity() method."""

    def test_missing_default_intensity_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="add_cell_mean_intensity"):
            input_props_model.add_cycle_mean_intensity()

    def test_custom_intensity_prop(self, input_props_model):
        input_props_model.add_cycle_mean_intensity(intensity_prop="my_area")
        input_props_model.update()
        cycle_lin = input_props_model.data.cycle_data[1]
        assert cycle_lin.nodes[2]["cycle_mean_intensity"] == 1.5

    def test_unit_from_intensity_prop(self, input_props_model):
        input_props_model.add_cycle_mean_intensity(intensity_prop="my_area")
        assert input_props_model.get_property("cycle_mean_intensity").unit == "um^2"


class TestAddBirthIntensity:
    """Test cases for Model.add_birth_intensity() method."""

    def test_missing_default_intensity_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="add_cell_total_intensity"):
            input_props_model.add_birth_intensity()

    def test_custom_intensity_prop(self, input_props_model):
        input_props_model.add_birth_intensity(intensity_prop="my_area")
        input_props_model.update()
        cycle_lin = input_props_model.data.cycle_data[1]
        assert cycle_lin.nodes[3]["birth_intensity"] == 3.0
        assert np.isnan(cycle_lin.nodes[2]["birth_intensity"])


class TestAddDivisionIntensity:
    """Test cases for Model.add_division_intensity() method."""

    def test_missing_default_intensity_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="add_cell_total_intensity"):
            input_props_model.add_division_intensity()

    def test_custom_intensity_prop(self, input_props_model):
        input_props_model.add_division_intensity(intensity_prop="my_area")
        input_props_model.update()
        cycle_lin = input_props_model.data.cycle_data[1]
        assert cycle_lin.nodes[2]["division_intensity"] == 2.0
        assert np.isnan(cycle_lin.nodes[3]["division_intensity"])


class TestAddAbsoluteAge:
    """Test cases for Model.add_absolute_age() method."""

    def test_default_time_prop_is_reference(self, input_props_model):
        input_props_model.add_absolute_age()
        input_props_model.update()
        assert input_props_model.data.cell_data[1].nodes[3]["absolute_age"] == 2

    def test_dtype_and_unit_from_time_prop(self, input_props_model):
        input_props_model.add_absolute_age()
        prop = input_props_model.get_property("absolute_age")
        assert (prop.dtype, prop.unit) == ("int", "frame")

    def test_new_root_updates_all_cells(self, input_props_model):
        input_props_model.add_absolute_age()
        input_props_model.update()
        input_props_model.add_cell(lid=1, cid=5, time_value=-1)
        input_props_model.add_link(source_cid=5, source_lid=1, target_cid=1)
        input_props_model.update()
        lin = input_props_model.data.cell_data[1]
        assert dict(lin.nodes(data="absolute_age")) == {1: 1, 2: 2, 3: 3, 4: 3, 5: 0}

    def test_missing_time_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="set 'time_prop'"):
            input_props_model.add_absolute_age(time_prop="unknown")

    def test_property_object_time_prop_raises(self, input_props_model):
        time_prop = input_props_model.get_property("time")
        with pytest.raises(TypeError, match="Pass its identifier instead: 'time'"):
            input_props_model.add_absolute_age(time_prop=time_prop)
        assert input_props_model.get_property("absolute_age") is None


class TestAddNormalizedAge:
    """Test cases for Model.add_normalized_age() method."""

    def test_default_time_prop_is_reference(self, input_props_model):
        input_props_model.add_normalized_age()
        input_props_model.update()
        lin = input_props_model.data.cell_data[1]
        # Cycle 2 = [1, 2] goes from time 0 to time 1, cycle 3 = [3] is a single cell.
        assert lin.nodes[1]["normalized_age"] == 0
        assert lin.nodes[2]["normalized_age"] == 1
        assert np.isnan(lin.nodes[3]["normalized_age"])

    def test_ignore_incomplete_cycles(self, input_props_model):
        input_props_model.add_normalized_age(ignore_incomplete_cycles=True)
        input_props_model.update()
        # Cycle 2 = [1, 2] starts at the root.
        assert np.isnan(input_props_model.data.cell_data[1].nodes[1]["normalized_age"])

    def test_float_dtype_and_no_unit(self, input_props_model):
        input_props_model.add_normalized_age()
        prop = input_props_model.get_property("normalized_age")
        assert (prop.dtype, prop.unit) == ("float", None)

    def test_missing_time_prop_raises(self, input_props_model):
        with pytest.raises(MissingPropertyError, match="set 'time_prop'"):
            input_props_model.add_normalized_age(time_prop="unknown")

    def test_property_object_time_prop_raises(self, input_props_model):
        time_prop = input_props_model.get_property("time")
        with pytest.raises(TypeError, match="Pass its identifier instead: 'time'"):
            input_props_model.add_normalized_age(time_prop=time_prop)
        assert input_props_model.get_property("normalized_age") is None


class TestAddRelativeAge:
    """Test cases for Model.add_relative_age() method."""

    def test_new_division_updates_its_cycle(self, input_props_model):
        input_props_model.add_relative_age()
        input_props_model.update()
        assert input_props_model.data.cell_data[1].nodes[2]["relative_age"] == 1
        # Cell 1 divides into cells 2 and 5: cycle [1, 2] becomes [1] and [2].
        input_props_model.add_cell(lid=1, cid=5, time_value=1)
        input_props_model.add_link(source_cid=1, source_lid=1, target_cid=5)
        input_props_model.update()
        assert input_props_model.data.cell_data[1].nodes[2]["relative_age"] == 0


class TestAddCellSpeed:
    """Test cases for Model.add_cell_speed() method."""

    def test_unit_from_time_prop(self, input_props_model):
        input_props_model.add_cell_speed()
        assert input_props_model.get_property("cell_speed").unit == "pixel/frame"

    def test_wrong_time_prop_type_raises(self, input_props_model):
        with pytest.raises(ValueError, match="prop_type 'node'"):
            input_props_model.add_cell_speed(time_prop="my_speed")

    def test_property_object_time_prop_raises(self, input_props_model):
        time_prop = input_props_model.get_property("time")
        with pytest.raises(TypeError, match="Pass its identifier instead: 'time'"):
            input_props_model.add_cell_speed(time_prop=time_prop)
        assert input_props_model.get_property("cell_speed") is None


class TestAddMotherCycle:
    """Test cases for Model.add_mother_cycle() method."""

    def test_values(self, input_props_model):
        input_props_model.add_mother_cycle()
        input_props_model.update()
        cycle_lin = input_props_model.data.cycle_data[1]
        assert cycle_lin.nodes[2]["mother_cycle"] is None
        assert cycle_lin.nodes[3]["mother_cycle"] == 2
        assert cycle_lin.nodes[4]["mother_cycle"] == 2


class TestAddDaughterCycles:
    """Test cases for Model.add_daughter_cycles() method."""

    def test_values(self, input_props_model):
        input_props_model.add_daughter_cycles()
        input_props_model.update()
        cycle_lin = input_props_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="daughter_cycles")) == {
            2: [3, 4],
            3: [],
            4: [],
        }


class TestAddSisterCycles:
    """Test cases for Model.add_sister_cycles() method."""

    def test_values(self, input_props_model):
        input_props_model.add_sister_cycles()
        input_props_model.update()
        cycle_lin = input_props_model.data.cycle_data[1]
        assert dict(cycle_lin.nodes(data="sister_cycles")) == {2: [], 3: [4], 4: [3]}


class TestAddCousinCycles:
    """Test cases for Model.add_cousin_cycles() method."""

    def test_degree(self, input_props_model):
        # Cells 3 and 4 divide into cells 5, 6 and 7, 8: cycles 5 and 7 are first
        # cousins, and there are no second cousins.
        for mother, daughter in [(3, 5), (3, 6), (4, 7), (4, 8)]:
            input_props_model.add_cell(lid=1, cid=daughter, time_value=3)
            input_props_model.add_link(
                source_cid=mother, source_lid=1, target_cid=daughter
            )
        input_props_model.add_cousin_cycles()
        input_props_model.add_cousin_cycles(
            degree=2, custom_identifier="second_cousin_cycles"
        )
        input_props_model.update()
        cycle_lin = input_props_model.data.cycle_data[1]
        assert cycle_lin.nodes[5]["cousin_cycles"] == [7, 8]
        assert cycle_lin.nodes[5]["second_cousin_cycles"] == []

    def test_degree_lower_than_1_raises(self, input_props_model):
        with pytest.raises(ValueError, match="at least 1 or None, got 0"):
            input_props_model.add_cousin_cycles(degree=0)
        assert input_props_model.get_property("cousin_cycles") is None


class TestAddLineageDuration:
    """Test cases for Model.add_lineage_duration() method."""

    def test_default_time_prop_is_reference(self, two_times_model):
        two_times_model.add_lineage_duration()
        two_times_model.update()
        assert two_times_model.data.cell_data[1].graph["lineage_duration"] == 15

    def test_custom_time_prop(self, two_times_model):
        two_times_model.add_lineage_duration(time_prop="frame")
        two_times_model.update()
        assert two_times_model.data.cell_data[1].graph["lineage_duration"] == 3

    def test_dtype_and_unit_from_time_prop(self, two_times_model):
        two_times_model.add_lineage_duration()
        prop = two_times_model.get_property("lineage_duration")
        assert (prop.dtype, prop.unit) == ("float", "min")

    def test_dtype_and_unit_from_custom_time_prop(self, two_times_model):
        two_times_model.add_lineage_duration(time_prop="frame")
        prop = two_times_model.get_property("lineage_duration")
        assert (prop.dtype, prop.unit) == ("int", "frame")

    def test_missing_time_prop_raises(self, two_times_model):
        with pytest.raises(MissingPropertyError, match="set 'time_prop'"):
            two_times_model.add_lineage_duration(time_prop="unknown")

    def test_property_object_time_prop_raises(self, two_times_model):
        time_prop = two_times_model.get_property("time")
        with pytest.raises(TypeError, match="Pass its identifier instead: 'time'"):
            two_times_model.add_lineage_duration(time_prop=time_prop)
        assert two_times_model.get_property("lineage_duration") is None
