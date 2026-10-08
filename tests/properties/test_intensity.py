#!/usr/bin/env python3

"""Unit test for intensity property classes from pycellin.properties."""

import math

import networkx as nx
import numpy as np
import pytest
from shapely.geometry import MultiPolygon, Polygon

from pycellin.classes import CellLineage, Data, Property
from pycellin.properties.intensity import (
    BirthIntensity,
    CellIntensityFromLabelImg,
    CellIntensityFromPolygon,
    CycleMeanIntensity,
    DivisionIntensity,
    _inside_even_odd,
    _shape_pixels,
)
from pycellin.properties.morphology import (
    CellMultiPolygonFromLabelImg,
    _mask_to_polygons,
)

# Fixtures ####################################################################


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
def prop_cycle_lin():
    return Property(
        identifier="test_property",
        name="test property",
        description="test property",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
    )


@pytest.fixture
def label_img():
    # Timepoint 0: label 3 is a 2x3 rectangle (rows 1-2, columns 1-3). Label 4 is
    # made of a 2x2 square (rows 3-4, columns 5-6) and of the pixel (0, 7).
    img = np.zeros((1, 6, 8), dtype=np.uint32)
    img[0, 1:3, 1:4] = 3
    img[0, 3:5, 5:7] = 4
    img[0, 0, 7] = 4
    return img


@pytest.fixture
def intensity_img():
    # The value of each pixel is 8 * row + column.
    return np.arange(48, dtype=np.uint16).reshape(1, 6, 8)


@pytest.fixture
def cell_lineage():
    # Cell 1 has label 3, cell 2 has label 4, both at timepoint 0.
    lineage = CellLineage()
    lineage.add_node(1, label=3, timepoint=0)
    lineage.add_node(2, label=4, timepoint=0)
    lineage.graph["lineage_ID"] = 1
    return lineage


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
        lineage.nodes[n]["cell_mean_intensity"] = float(n)
        lineage.nodes[n]["cell_total_intensity"] = 10.0 * n
    lineage.graph["lineage_ID"] = 1
    data = Data({1: lineage})
    data._add_cycle_lineages(time_prop="frame", time_step=1)
    return data


# _inside_even_odd ############################################################


def _ring_edges(ring):
    """Edges (x1, y1, x2, y2) of a closed ring given as a list of points."""
    points = np.asarray(ring + ring[:1], dtype=float)
    return np.hstack([points[:-1], points[1:]])


class TestInsideEvenOdd:
    def test_points_on_left_and_top_edges_inside(self):
        edges = _ring_edges([(1, 1), (3, 1), (3, 3), (1, 3)])
        grid = np.arange(1.0, 4.0)
        inside = _inside_even_odd(edges, grid, grid)
        # Rows 1 and 2 (top edge and interior) and columns 1 and 2 (left edge
        # and interior) are inside; the right and bottom edges are not.
        expected = np.array([[1, 1, 0], [1, 1, 0], [0, 0, 0]], dtype=bool)
        assert np.array_equal(inside, expected)

    def test_ring_direction_does_not_matter(self):
        ring = [(0.5, 0.5), (4.5, 2.5), (2.5, 4.5)]
        grid = np.arange(0.0, 6.0)
        assert np.array_equal(
            _inside_even_odd(_ring_edges(ring), grid, grid),
            _inside_even_odd(_ring_edges(ring[::-1]), grid, grid),
        )

    def test_hole(self):
        outer = _ring_edges([(0.5, 0.5), (3.5, 0.5), (3.5, 3.5), (0.5, 3.5)])
        hole = _ring_edges([(1.5, 1.5), (2.5, 1.5), (2.5, 2.5), (1.5, 2.5)])
        grid = np.arange(0.0, 5.0)
        inside = _inside_even_odd(np.vstack([outer, hole]), grid, grid)
        assert inside.sum() == 8
        assert not inside[2, 2]


# _shape_pixels ###############################################################


class TestShapePixels:
    def test_pixel_centers_inside(self, intensity_img):
        # Contains the centers of the pixels (1, 1) and (1, 2), of values 9 and 10.
        shape = Polygon([(0.5, 0.5), (2.5, 0.5), (2.5, 1.5), (0.5, 1.5)])
        assert sorted(_shape_pixels(shape, intensity_img[0], 1.0)) == [9, 10]

    def test_pixel_center_on_left_or_top_edge_counted(self, intensity_img):
        # The centers of the pixels (1, 1), (1, 2), (2, 1) and (2, 2) are the
        # corners of the square: only (1, 1), on its left and top edges, counts.
        shape = Polygon([(1, 1), (2, 1), (2, 2), (1, 2)])
        assert list(_shape_pixels(shape, intensity_img[0], 1.0)) == [9]

    def test_touching_shapes_count_shared_edge_pixels_once(self, intensity_img):
        # Two shapes touching along a diagonal that goes through 5 pixel centers,
        # one of them with its ring in the other direction.
        cell_a = Polygon([(0.5, 0.5), (1.5, 0.5), (6.5, 5.5), (0.5, 5.5)])
        cell_b = Polygon([(6.5, 5.5), (7.5, 5.5), (7.5, 0.5), (1.5, 0.5)])
        pixels_a = set(_shape_pixels(cell_a, intensity_img[0], 1.0))
        pixels_b = set(_shape_pixels(cell_b, intensity_img[0], 1.0))
        assert not pixels_a & pixels_b
        # Together, they cover all the pixels of rows 1-5 and columns 1-7.
        assert pixels_a | pixels_b == set(intensity_img[0, 1:6, 1:8].ravel())

    def test_multipolygon_same_pixels_as_mask(self, intensity_img):
        # A ring with a hole, and a piece inside the hole.
        mask = np.zeros((6, 8), dtype=bool)
        mask[0:6, 1:7] = True
        mask[1:5, 2:6] = False
        mask[2:4, 3:5] = True
        shape = MultiPolygon(_mask_to_polygons(mask, fill_holes=False))
        pixels = _shape_pixels(shape, intensity_img[0], 1.0)
        assert sorted(pixels) == sorted(intensity_img[0][mask])

    def test_pixel_size(self, intensity_img):
        # With pixels of size 2, the pixel (1, 2) has its center at (4, 2).
        shape = Polygon([(3, 1), (5, 1), (5, 3), (3, 3)])
        assert list(_shape_pixels(shape, intensity_img[0], 2.0)) == [10]

    def test_shape_partly_outside_frame(self, intensity_img):
        shape = Polygon([(-5, -5), (0.5, -5), (0.5, 0.5), (-5, 0.5)])
        assert list(_shape_pixels(shape, intensity_img[0], 1.0)) == [0]

    def test_shape_outside_frame(self, intensity_img):
        shape = Polygon([(20, 20), (22, 20), (22, 22), (20, 22)])
        assert _shape_pixels(shape, intensity_img[0], 1.0).size == 0


# CellIntensityFromLabelImg ###################################################


class TestCellIntensityFromLabelImg:
    def test_compute_total(self, cell_lineage, label_img, intensity_img, prop_cell_lin):
        calculator = CellIntensityFromLabelImg(
            prop_cell_lin, "total", intensity_img, "label", label_img
        )
        # Rows 1-2, columns 1-3: 9 + 10 + 11 + 17 + 18 + 19.
        assert calculator.compute(cell_lineage, nid=1) == 84.0

    def test_compute_mean(self, cell_lineage, label_img, intensity_img, prop_cell_lin):
        calculator = CellIntensityFromLabelImg(
            prop_cell_lin, "mean", intensity_img, "label", label_img
        )
        assert calculator.compute(cell_lineage, nid=1) == 14.0

    def test_compute_all_pieces(
        self, cell_lineage, label_img, intensity_img, prop_cell_lin
    ):
        calculator = CellIntensityFromLabelImg(
            prop_cell_lin, "total", intensity_img, "label", label_img
        )
        # The 2x2 square (29 + 30 + 37 + 38) and the pixel (0, 7) of value 7.
        assert calculator.compute(cell_lineage, nid=2) == 141.0

    def test_compute_hole_left_out(self, prop_cell_lin):
        label_img = np.ones((1, 3, 3), dtype=np.uint32)
        label_img[0, 1, 1] = 0
        lineage = CellLineage()
        lineage.add_node(1, label=1, timepoint=0)
        calculator = CellIntensityFromLabelImg(
            prop_cell_lin, "total", np.ones((1, 3, 3)), "label", label_img
        )
        assert calculator.compute(lineage, nid=1) == 8.0

    def test_compute_background(
        self, cell_lineage, label_img, intensity_img, prop_cell_lin
    ):
        total = CellIntensityFromLabelImg(
            prop_cell_lin, "total", intensity_img, "label", label_img, background=4.0
        )
        mean = CellIntensityFromLabelImg(
            prop_cell_lin, "mean", intensity_img, "label", label_img, background=4.0
        )
        assert total.compute(cell_lineage, nid=1) == 84.0 - 6 * 4.0
        assert mean.compute(cell_lineage, nid=1) == 10.0

    def test_compute_background_above_pixel_values(
        self, cell_lineage, label_img, prop_cell_lin
    ):
        # Subtracting the background from unsigned integers must not wrap around.
        intensity_img = np.full((1, 6, 8), 50, dtype=np.uint16)
        calculator = CellIntensityFromLabelImg(
            prop_cell_lin, "mean", intensity_img, "label", label_img, background=100
        )
        assert calculator.compute(cell_lineage, nid=1) == -50.0

    def test_compute_3d(self, prop_cell_lin):
        label_img = np.zeros((1, 2, 3, 3), dtype=np.uint32)
        label_img[0, :, 1:, 1:] = 1
        intensity_img = np.zeros((1, 2, 3, 3))
        intensity_img[0, 1] = 2.0
        lineage = CellLineage()
        lineage.add_node(1, label=1, timepoint=0)
        calculator = CellIntensityFromLabelImg(
            prop_cell_lin, "total", intensity_img, "label", label_img
        )
        # 4 pixels in each of the 2 planes, of values 0 and 2.
        assert calculator.compute(lineage, nid=1) == 8.0

    def test_compute_missing_label_raises(
        self, cell_lineage, label_img, intensity_img, prop_cell_lin
    ):
        cell_lineage.nodes[1]["label"] = 7
        calculator = CellIntensityFromLabelImg(
            prop_cell_lin, "total", intensity_img, "label", label_img
        )
        with pytest.raises(ValueError, match="Label 7 of cell 1"):
            calculator.compute(cell_lineage, nid=1)

    def test_invalid_statistic_raises(self, label_img, intensity_img, prop_cell_lin):
        with pytest.raises(ValueError, match="'statistic' must be one of"):
            CellIntensityFromLabelImg(
                prop_cell_lin, "median", intensity_img, "label", label_img
            )

    def test_get_input_props(self, label_img, intensity_img, prop_cell_lin):
        calculator = CellIntensityFromLabelImg(
            prop_cell_lin, "total", intensity_img, "my_label", label_img
        )
        assert calculator.get_input_props() == {
            "label_prop": ("my_label", "node", "CellLineage")
        }

    def test_uses_external_data(self):
        assert CellIntensityFromLabelImg.uses_external_data()


# CellIntensityFromPolygon ####################################################


class TestCellIntensityFromPolygon:
    def test_compute_same_as_label_img_with_multipolygon(
        self, cell_lineage, label_img, intensity_img, prop_cell_lin
    ):
        # Shapes computed from the label image, with pixels of size 2.
        shape_calculator = CellMultiPolygonFromLabelImg(
            prop_cell_lin, label_prop="label", label_img=label_img, pixel_size=2.0
        )
        for nid in cell_lineage.nodes:
            shape = shape_calculator.compute(cell_lineage, nid)
            cell_lineage.nodes[nid]["cell_multipolygon"] = shape
        from_polygon = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_img, "cell_multipolygon", 2.0
        )
        from_label_img = CellIntensityFromLabelImg(
            prop_cell_lin, "total", intensity_img, "label", label_img
        )
        for nid in cell_lineage.nodes:
            assert from_polygon.compute(cell_lineage, nid) == from_label_img.compute(
                cell_lineage, nid
            )

    def test_compute_mean(self, cell_lineage, intensity_img, prop_cell_lin):
        cell_lineage.nodes[1]["cell_polygon"] = Polygon(
            [(0.5, 0.5), (2.5, 0.5), (2.5, 1.5), (0.5, 1.5)]
        )
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "mean", intensity_img, "cell_polygon", 1.0
        )
        assert calculator.compute(cell_lineage, nid=1) == 9.5

    def test_compute_none_shape(self, cell_lineage, intensity_img, prop_cell_lin):
        cell_lineage.nodes[1]["cell_polygon"] = None
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_img, "cell_polygon", 1.0
        )
        assert math.isnan(calculator.compute(cell_lineage, nid=1))

    def test_compute_no_pixel_center(self, cell_lineage, intensity_img, prop_cell_lin):
        cell_lineage.nodes[1]["cell_polygon"] = MultiPolygon(
            [Polygon([(20, 20), (22, 20), (22, 22), (20, 22)])]
        )
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_img, "cell_polygon", 1.0
        )
        assert math.isnan(calculator.compute(cell_lineage, nid=1))

    def test_compute_missing_shape_raises(
        self, cell_lineage, intensity_img, prop_cell_lin
    ):
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_img, "cell_polygon", 1.0
        )
        with pytest.raises(KeyError, match="missing 'cell_polygon' property"):
            calculator.compute(cell_lineage, nid=1)

    def test_get_input_props(self, intensity_img, prop_cell_lin):
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_img, "my_polygon", 1.0
        )
        assert calculator.get_input_props() == {
            "polygon_prop": ("my_polygon", "node", "CellLineage")
        }


# CycleMeanIntensity ##########################################################


class TestCycleMeanIntensity:
    def test_compute(self, data, prop_cycle_lin):
        calculator = CycleMeanIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=4) == 2.5

    def test_compute_ignores_nan(self, data, prop_cycle_lin):
        data.cell_data[1].nodes[1]["cell_mean_intensity"] = np.nan
        calculator = CycleMeanIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=4) == 3.0

    def test_compute_custom_intensity_prop(self, data, prop_cycle_lin):
        calculator = CycleMeanIntensity(
            prop_cycle_lin, intensity_prop="cell_total_intensity"
        )
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 55.0

    def test_get_input_props(self, prop_cycle_lin):
        calculator = CycleMeanIntensity(prop_cycle_lin)
        assert calculator.get_input_props() == {
            "intensity_prop": ("cell_mean_intensity", "node", "CellLineage")
        }


# BirthIntensity ##############################################################


class TestBirthIntensity:
    def test_compute_complete_cycle(self, data, prop_cycle_lin):
        calculator = BirthIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 50.0

    def test_compute_leaf_cycle(self, data, prop_cycle_lin):
        calculator = BirthIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=7) == 70.0

    def test_compute_root_cycle(self, data, prop_cycle_lin):
        calculator = BirthIntensity(prop_cycle_lin)
        assert math.isnan(calculator.compute(data, data.cycle_data[1], nid=4))

    def test_compute_custom_intensity_prop(self, data, prop_cycle_lin):
        calculator = BirthIntensity(
            prop_cycle_lin, intensity_prop="cell_mean_intensity"
        )
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 5.0


# DivisionIntensity ###########################################################


class TestDivisionIntensity:
    def test_compute_complete_cycle(self, data, prop_cycle_lin):
        calculator = DivisionIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 60.0

    def test_compute_root_cycle(self, data, prop_cycle_lin):
        calculator = DivisionIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_data[1], nid=4) == 40.0

    def test_compute_leaf_cycle(self, data, prop_cycle_lin):
        calculator = DivisionIntensity(prop_cycle_lin)
        assert math.isnan(calculator.compute(data, data.cycle_data[1], nid=7))

    def test_compute_custom_intensity_prop(self, data, prop_cycle_lin):
        calculator = DivisionIntensity(
            prop_cycle_lin, intensity_prop="cell_mean_intensity"
        )
        assert calculator.compute(data, data.cycle_data[1], nid=6) == 6.0
