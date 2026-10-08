#!/usr/bin/env python3

"""Unit test for morphology property classes from pycellin.properties."""

import math
import warnings

import networkx as nx
import numpy as np
import pytest
from shapely.geometry import Polygon

from pycellin.classes import CellLineage, Data, Property
from pycellin.properties.morphology import (
    BirthArea,
    CellArea,
    CellContour,
    CellPerimeter,
    CellPolygonFromLabelImg,
    CycleMeanArea,
    DivisionArea,
)

# Fixtures ####################################################################


@pytest.fixture
def data():
    # Cycles: 4 = [1, 2, 3, 4] (root), 6 = [5, 6] (complete),
    # 7 = [7], 8 = [8] and 9 = [9] (leaves).
    lineage = CellLineage()
    lineage.add_edges_from(
        [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (4, 7), (6, 8), (6, 9)]
    )
    for n in lineage.nodes:
        lineage.nodes[n]["frame"] = nx.shortest_path_length(lineage, 1, n)
        lineage.nodes[n]["cell_ID"] = n
        lineage.nodes[n]["cell_area"] = float(n)
    lineage.graph["lineage_ID"] = 1
    data = Data({1: lineage})
    data._add_cycle_lineages(time_prop="frame", time_step=1)
    return data


@pytest.fixture
def prop_cycle_lin():
    return Property(
        identifier="test_property",
        name="test property",
        description="test property",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit="um^2",
    )


@pytest.fixture
def polygon_lineage():
    # Cell 1 is a 2x1 rectangle stored in both "cell_polygon" and "my_polygon",
    # cell 2 is a 3x1 rectangle stored in "my_polygon" only.
    lineage = CellLineage()
    lineage.add_edge(1, 2)
    lineage.nodes[1]["cell_polygon"] = Polygon([(0, 0), (2, 0), (2, 1), (0, 1)])
    lineage.nodes[1]["my_polygon"] = Polygon([(0, 0), (2, 0), (2, 1), (0, 1)])
    lineage.nodes[2]["my_polygon"] = Polygon([(0, 0), (3, 0), (3, 1), (0, 1)])
    lineage.graph["lineage_ID"] = 1
    return lineage


@pytest.fixture
def prop_cell_lin():
    return Property(
        identifier="test_property",
        name="test property",
        description="test property",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
    )


# CellPolygonFromLabelImg #####################################################


class TestCellPolygonFromLabelImg:
    def test_existing_value_kept_with_custom_identifier(self, prop_cell_lin):
        lineage = CellLineage()
        lineage.add_node(1, label=1, timepoint=0, test_property="existing")
        label_img = np.zeros((1, 5, 5), dtype=np.uint32)
        calculator = CellPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=1.0
        )
        assert calculator.compute(lineage, nid=1) == "existing"

    def test_get_input_props(self, prop_cell_lin):
        calculator = CellPolygonFromLabelImg(
            prop_cell_lin,
            label_prop="my_label",
            label_img=np.zeros((1, 5, 5), dtype=np.uint32),
            pixel_size=1.0,
        )
        assert calculator.get_input_props() == {
            "label_prop": ("my_label", "node", "CellLineage")
        }


# CellArea ####################################################################


class TestCellArea:
    def test_compute_default_polygon_prop(self, polygon_lineage, prop_cell_lin):
        calculator = CellArea(prop_cell_lin)
        assert calculator.compute(polygon_lineage, nid=1) == 2.0

    def test_compute_custom_polygon_prop(self, polygon_lineage, prop_cell_lin):
        calculator = CellArea(prop_cell_lin, polygon_prop="my_polygon")
        assert calculator.compute(polygon_lineage, nid=2) == 3.0

    def test_compute_missing_polygon(self, polygon_lineage, prop_cell_lin):
        calculator = CellArea(prop_cell_lin)
        with pytest.raises(KeyError, match="missing 'cell_polygon' property"):
            calculator.compute(polygon_lineage, nid=2)

    def test_get_input_props(self, prop_cell_lin):
        calculator = CellArea(prop_cell_lin, polygon_prop="my_polygon")
        assert calculator.get_input_props() == {
            "polygon_prop": ("my_polygon", "node", "CellLineage")
        }


# CellPerimeter ###############################################################


class TestCellPerimeter:
    def test_compute_default_polygon_prop(self, polygon_lineage, prop_cell_lin):
        calculator = CellPerimeter(prop_cell_lin)
        assert calculator.compute(polygon_lineage, nid=1) == 6.0

    def test_compute_custom_polygon_prop(self, polygon_lineage, prop_cell_lin):
        calculator = CellPerimeter(prop_cell_lin, polygon_prop="my_polygon")
        assert calculator.compute(polygon_lineage, nid=2) == 8.0


# CellContour #################################################################


class TestCellContour:
    def test_compute_custom_polygon_prop(self, polygon_lineage, prop_cell_lin):
        calculator = CellContour(prop_cell_lin, polygon_prop="my_polygon")
        contour = calculator.compute(polygon_lineage, nid=2)
        assert contour[:4] == [(-1.5, -0.5), (1.5, -0.5), (1.5, 0.5), (-1.5, 0.5)]

    def test_existing_value_kept_with_custom_identifier(
        self, polygon_lineage, prop_cell_lin
    ):
        polygon_lineage.nodes[2]["test_property"] = "existing"
        calculator = CellContour(prop_cell_lin, polygon_prop="my_polygon")
        assert calculator.compute(polygon_lineage, nid=2) == "existing"


# CycleMeanArea ###############################################################


class TestCycleMeanArea:
    def test_compute(self, data, prop_cycle_lin):
        calculator = CycleMeanArea(prop_cycle_lin)
        cycle_lin = data.cycle_data[1]
        assert calculator.compute(data, cycle_lin, nid=4) == 2.5
        assert calculator.compute(data, cycle_lin, nid=6) == 5.5
        assert calculator.compute(data, cycle_lin, nid=7) == 7.0

    def test_compute_ignores_nan(self, data, prop_cycle_lin):
        data.cell_data[1].nodes[3]["cell_area"] = math.nan
        calculator = CycleMeanArea(prop_cycle_lin)
        result = calculator.compute(data, data.cycle_data[1], nid=4)
        assert result == pytest.approx(7 / 3)

    def test_compute_only_nan(self, data, prop_cycle_lin):
        data.cell_data[1].nodes[7]["cell_area"] = math.nan
        calculator = CycleMeanArea(prop_cycle_lin)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            result = calculator.compute(data, data.cycle_data[1], nid=7)
        assert math.isnan(result)

    def test_compute_custom_area_prop(self, data, prop_cycle_lin):
        for n in data.cell_data[1].nodes:
            data.cell_data[1].nodes[n]["my_area"] = 10.0 * n
        calculator = CycleMeanArea(prop_cycle_lin, area_prop="my_area")
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 55.0

    def test_enrich(self, data, prop_cycle_lin):
        calculator = CycleMeanArea(prop_cycle_lin)
        calculator.enrich(data)
        cycle_lin = data.cycle_data[1]
        assert cycle_lin.nodes[4]["test_property"] == 2.5
        assert cycle_lin.nodes[6]["test_property"] == 5.5
        assert cycle_lin.nodes[7]["test_property"] == 7.0


# BirthArea ###################################################################


class TestBirthArea:
    def test_compute_complete_cycle(self, data, prop_cycle_lin):
        calculator = BirthArea(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 5.0

    def test_compute_leaf_cycle(self, data, prop_cycle_lin):
        calculator = BirthArea(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=7) == 7.0

    def test_compute_root_cycle(self, data, prop_cycle_lin):
        calculator = BirthArea(prop_cycle_lin)
        assert math.isnan(calculator.compute(data, data.cycle_data[1], nid=4))

    def test_compute_missing_cell_area(self, data, prop_cycle_lin):
        del data.cell_data[1].nodes[5]["cell_area"]
        calculator = BirthArea(prop_cycle_lin)
        with pytest.raises(KeyError, match="'cell_area' does not exist"):
            calculator.compute(data, data.cycle_data[1], nid=6)

    def test_compute_custom_area_prop(self, data, prop_cycle_lin):
        for n in data.cell_data[1].nodes:
            data.cell_data[1].nodes[n]["my_area"] = 10.0 * n
        calculator = BirthArea(prop_cycle_lin, area_prop="my_area")
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 50.0


# DivisionArea ################################################################


class TestDivisionArea:
    def test_compute_complete_cycle(self, data, prop_cycle_lin):
        calculator = DivisionArea(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 6.0

    def test_compute_root_cycle(self, data, prop_cycle_lin):
        calculator = DivisionArea(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=4) == 4.0

    def test_compute_leaf_cycle(self, data, prop_cycle_lin):
        calculator = DivisionArea(prop_cycle_lin)
        assert math.isnan(calculator.compute(data, data.cycle_data[1], nid=7))

    def test_compute_missing_cell_area(self, data, prop_cycle_lin):
        del data.cell_data[1].nodes[6]["cell_area"]
        calculator = DivisionArea(prop_cycle_lin)
        with pytest.raises(KeyError, match="'cell_area' does not exist"):
            calculator.compute(data, data.cycle_data[1], nid=6)

    def test_compute_custom_area_prop(self, data, prop_cycle_lin):
        for n in data.cell_data[1].nodes:
            data.cell_data[1].nodes[n]["my_area"] = 10.0 * n
        calculator = DivisionArea(prop_cycle_lin, area_prop="my_area")
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 60.0
