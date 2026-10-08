#!/usr/bin/env python3

"""Unit test for morphology property classes from pycellin.properties."""

import math
import warnings

import networkx as nx
import numpy as np
import pytest
from shapely.geometry import MultiPolygon, Polygon

from pycellin.classes import CellLineage, Data, Property
from pycellin.properties.morphology import (
    BirthArea,
    CellArea,
    CellContour,
    CellMultiPolygonFromLabelImg,
    CellPerimeter,
    CellPolygonFromLabelImg,
    CycleMeanArea,
    DivisionArea,
    _mask_to_polygons,
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


@pytest.fixture
def label_img():
    # Timepoint 0: label 3 is a 2x3 rectangle (rows 2-3, columns 5-7). Label 4 is
    # made of a 3x3 square (rows 6-8, columns 1-3) and of a single pixel. Label 5
    # is a 3x3 square with a hole at its center (rows 6-8, columns 6-8).
    img = np.zeros((1, 10, 12), dtype=np.uint32)
    img[0, 2:4, 5:8] = 3
    img[0, 6:9, 1:4] = 4
    img[0, 9, 10] = 4
    img[0, 6:9, 6:9] = 5
    img[0, 7, 7] = 0
    return img


# _mask_to_polygons ###########################################################


class TestMaskToPolygons:
    def test_single_piece(self):
        mask = np.zeros((6, 7), dtype=bool)
        mask[1:4, 2:6] = True
        polygons = _mask_to_polygons(mask)
        assert len(polygons) == 1
        assert polygons[0].area == 11.5

    def test_pieces_sorted_by_decreasing_area(self):
        mask = np.zeros((8, 8), dtype=bool)
        mask[0, 0] = True
        mask[4:7, 4:7] = True
        assert [polygon.area for polygon in _mask_to_polygons(mask)] == [8.5, 0.5]

    def test_corner_connected_pixels_are_one_piece(self):
        mask = np.zeros((5, 5), dtype=bool)
        mask[1, 1] = mask[2, 2] = mask[3, 3] = True
        assert len(_mask_to_polygons(mask)) == 1

    def test_holes_filled(self):
        mask = np.zeros((7, 7), dtype=bool)
        mask[1:6, 1:6] = True
        mask[3, 3] = False
        assert _mask_to_polygons(mask)[0].area == 24.5

    def test_piece_on_mask_border_is_closed(self):
        polygon = _mask_to_polygons(np.ones((3, 3), dtype=bool))[0]
        assert polygon.area == 8.5
        assert polygon.bounds == (-0.5, -0.5, 2.5, 2.5)

    def test_empty_mask(self):
        assert _mask_to_polygons(np.zeros((3, 3), dtype=bool)) == []

    def test_holes_kept_as_interior_rings(self):
        mask = np.zeros((7, 7), dtype=bool)
        mask[1:6, 1:6] = True
        mask[3, 3] = False
        polygon = _mask_to_polygons(mask, fill_holes=False)[0]
        assert len(polygon.interiors) == 1
        assert polygon.area == 24.0

    def test_piece_inside_hole(self):
        # A ring of 40 pixels around a 3x3 hole, with a 1-pixel piece at its center.
        mask = np.zeros((9, 9), dtype=bool)
        mask[1:8, 1:8] = True
        mask[3:6, 3:6] = False
        mask[4, 4] = True
        polygons = _mask_to_polygons(mask, fill_holes=False)
        assert [polygon.area for polygon in polygons] == [40.0, 0.5]
        assert MultiPolygon(polygons).is_valid


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

    def test_compute_position_and_pixel_size(self, label_img, prop_cell_lin):
        lineage = CellLineage()
        lineage.add_node(1, label=3, timepoint=0)
        calculator = CellPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=2.0
        )
        polygon = calculator.compute(lineage, nid=1)
        assert polygon.bounds == (9.0, 3.0, 15.0, 7.0)
        assert polygon.area == 22.0

    def test_compute_keeps_largest_piece(self, label_img, prop_cell_lin):
        lineage = CellLineage()
        lineage.add_node(1, label=4, timepoint=0)
        lineage.graph["lineage_ID"] = 1
        calculator = CellPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=1.0
        )
        polygon = calculator.compute(lineage, nid=1)
        assert polygon.area == 8.5
        assert polygon.bounds == (0.5, 5.5, 3.5, 8.5)

    def test_compute_missing_label_raises(self, label_img, prop_cell_lin):
        lineage = CellLineage()
        lineage.add_node(1, label=7, timepoint=0)
        lineage.graph["lineage_ID"] = 1
        calculator = CellPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=1.0
        )
        with pytest.raises(ValueError, match="Label 7 of cell 1"):
            calculator.compute(lineage, nid=1)

    def test_enrich_warns_once_for_fragmented_labels(self, label_img, prop_cell_lin):
        lineage = CellLineage()
        lineage.add_node(1, label=3, timepoint=0)
        lineage.add_node(2, label=4, timepoint=0)
        lineage.graph["lineage_ID"] = 1
        calculator = CellPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=1.0
        )
        with pytest.warns(UserWarning, match="1 cell has a label") as record:
            calculator.enrich(Data({1: lineage}), [(1, 1), (2, 1)])
        assert len(record) == 1
        assert "cell 2 of lineage 1" in str(record[0].message)
        assert "model.add_cell_multipolygon()" in str(record[0].message)

    def test_enrich_warns_for_holes(self, label_img, prop_cell_lin):
        lineage = CellLineage()
        lineage.add_node(1, label=5, timepoint=0)
        lineage.graph["lineage_ID"] = 1
        calculator = CellPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=1.0
        )
        with pytest.warns(UserWarning, match=r"1 cell has a label with holes \(cell 1"):
            calculator.enrich(Data({1: lineage}), [(1, 1)])
        assert lineage.nodes[1]["test_property"].area == 8.5

    def test_enrich_single_warning_for_pieces_and_holes(
        self, label_img, prop_cell_lin
    ):
        lineage = CellLineage()
        lineage.add_node(1, label=4, timepoint=0)
        lineage.add_node(2, label=5, timepoint=0)
        lineage.graph["lineage_ID"] = 1
        calculator = CellPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=1.0
        )
        with pytest.warns(UserWarning) as record:
            calculator.enrich(Data({1: lineage}), [(1, 1), (2, 1)])
        assert len(record) == 1
        message = str(record[0].message)
        assert "a label made of several pieces (cell 1 of lineage 1)" in message
        assert "a label with holes (cell 2 of lineage 1)" in message

    def test_enrich_no_warning_without_fragmented_label(
        self, label_img, prop_cell_lin
    ):
        lineage = CellLineage()
        lineage.add_node(1, label=3, timepoint=0)
        lineage.graph["lineage_ID"] = 1
        calculator = CellPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=1.0
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            calculator.enrich(Data({1: lineage}), [(1, 1)])

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


# CellMultiPolygonFromLabelImg ################################################


class TestCellMultiPolygonFromLabelImg:
    def test_compute_keeps_all_pieces(self, label_img, prop_cell_lin):
        lineage = CellLineage()
        lineage.add_node(1, label=4, timepoint=0)
        calculator = CellMultiPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=1.0
        )
        multipolygon = calculator.compute(lineage, nid=1)
        assert [polygon.area for polygon in multipolygon.geoms] == [8.5, 0.5]

    def test_compute_single_piece(self, label_img, prop_cell_lin):
        lineage = CellLineage()
        lineage.add_node(1, label=3, timepoint=0)
        calculator = CellMultiPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=2.0
        )
        multipolygon = calculator.compute(lineage, nid=1)
        assert isinstance(multipolygon, MultiPolygon)
        assert len(multipolygon.geoms) == 1
        assert multipolygon.bounds == (9.0, 3.0, 15.0, 7.0)

    def test_enrich_no_warning_for_fragmented_labels(self, label_img, prop_cell_lin):
        lineage = CellLineage()
        lineage.add_node(1, label=4, timepoint=0)
        lineage.graph["lineage_ID"] = 1
        calculator = CellMultiPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=1.0
        )
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            calculator.enrich(Data({1: lineage}), [(1, 1)])


# CellArea ####################################################################


class TestCellArea:
    def test_compute_default_polygon_prop(self, polygon_lineage, prop_cell_lin):
        calculator = CellArea(prop_cell_lin)
        assert calculator.compute(polygon_lineage, nid=1) == 2.0

    def test_compute_custom_polygon_prop(self, polygon_lineage, prop_cell_lin):
        calculator = CellArea(prop_cell_lin, polygon_prop="my_polygon")
        assert calculator.compute(polygon_lineage, nid=2) == 3.0

    def test_compute_multipolygon(self, polygon_lineage, prop_cell_lin):
        polygon_lineage.nodes[1]["my_multipolygon"] = MultiPolygon(
            [
                Polygon([(0, 0), (2, 0), (2, 1), (0, 1)]),
                Polygon([(5, 5), (6, 5), (6, 6), (5, 6)]),
            ]
        )
        calculator = CellArea(prop_cell_lin, polygon_prop="my_multipolygon")
        assert calculator.compute(polygon_lineage, nid=1) == 3.0

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

    def test_compute_multipolygon_raises(self, polygon_lineage, prop_cell_lin):
        polygon_lineage.nodes[1]["my_multipolygon"] = MultiPolygon(
            [polygon_lineage.nodes[1]["cell_polygon"]]
        )
        calculator = CellContour(prop_cell_lin, polygon_prop="my_multipolygon")
        with pytest.raises(TypeError, match="a contour needs a Polygon"):
            calculator.compute(polygon_lineage, nid=1)

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
