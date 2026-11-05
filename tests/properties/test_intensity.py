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
    CellIntensityFromLabelImage,
    CellIntensityFromPolygon,
    CycleMeanIntensity,
    DivisionIntensity,
    _inside_even_odd,
    _shape_pixels,
)
from pycellin.properties.morphology import (
    CellMultiPolygonFromLabelImage,
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
        lineage_type="cell",
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
        lineage_type="cycle",
        dtype="float",
    )


@pytest.fixture
def label_image():
    # Timepoint 0: label 3 is a 2x3 rectangle (rows 1-2, columns 1-3). Label 4 is
    # made of a 2x2 square (rows 3-4, columns 5-6) and of the pixel (0, 7).
    img = np.zeros((1, 6, 8), dtype=np.uint32)
    img[0, 1:3, 1:4] = 3
    img[0, 3:5, 5:7] = 4
    img[0, 0, 7] = 4
    return img


@pytest.fixture
def intensity_image():
    # The value of each pixel is 8 * row + column.
    return np.arange(48, dtype=np.uint16).reshape(1, 6, 8)


@pytest.fixture
def cell_lineage():
    # Cell 1 has label 3, cell 2 has label 4, both at timepoint 0.
    lineage = CellLineage()
    lineage.add_node(1, label=3, timepoint=0)
    lineage.add_node(2, label=4, timepoint=0)
    lineage.graph["lineage_id"] = 1
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
        lineage.nodes[n]["cell_id"] = n
        lineage.nodes[n]["cell_mean_intensity"] = float(n)
        lineage.nodes[n]["cell_total_intensity"] = 10.0 * n
    lineage.graph["lineage_id"] = 1
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
    def test_pixel_centers_inside(self, intensity_image):
        # Contains the centers of the pixels (1, 1) and (1, 2), of values 9 and 10.
        shape = Polygon([(0.5, 0.5), (2.5, 0.5), (2.5, 1.5), (0.5, 1.5)])
        assert sorted(_shape_pixels(shape, intensity_image[0], 1.0)) == [9, 10]

    def test_pixel_center_on_left_or_top_edge_counted(self, intensity_image):
        # The centers of the pixels (1, 1), (1, 2), (2, 1) and (2, 2) are the
        # corners of the square: only (1, 1), on its left and top edges, counts.
        shape = Polygon([(1, 1), (2, 1), (2, 2), (1, 2)])
        assert list(_shape_pixels(shape, intensity_image[0], 1.0)) == [9]

    def test_touching_shapes_count_shared_edge_pixels_once(self, intensity_image):
        # Two shapes touching along a diagonal that goes through 5 pixel centers,
        # one of them with its ring in the other direction.
        cell_a = Polygon([(0.5, 0.5), (1.5, 0.5), (6.5, 5.5), (0.5, 5.5)])
        cell_b = Polygon([(6.5, 5.5), (7.5, 5.5), (7.5, 0.5), (1.5, 0.5)])
        pixels_a = set(_shape_pixels(cell_a, intensity_image[0], 1.0))
        pixels_b = set(_shape_pixels(cell_b, intensity_image[0], 1.0))
        assert not pixels_a & pixels_b
        # Together, they cover all the pixels of rows 1-5 and columns 1-7.
        assert pixels_a | pixels_b == set(intensity_image[0, 1:6, 1:8].ravel())

    def test_multipolygon_same_pixels_as_mask(self, intensity_image):
        # A ring with a hole, and a piece inside the hole.
        mask = np.zeros((6, 8), dtype=bool)
        mask[0:6, 1:7] = True
        mask[1:5, 2:6] = False
        mask[2:4, 3:5] = True
        shape = MultiPolygon(_mask_to_polygons(mask, fill_holes=False))
        pixels = _shape_pixels(shape, intensity_image[0], 1.0)
        assert sorted(pixels) == sorted(intensity_image[0][mask])

    def test_pixel_size(self, intensity_image):
        # With pixels of size 2, the pixel (1, 2) has its center at (4, 2).
        shape = Polygon([(3, 1), (5, 1), (5, 3), (3, 3)])
        assert list(_shape_pixels(shape, intensity_image[0], 2.0)) == [10]

    def test_shape_partly_outside_frame(self, intensity_image):
        shape = Polygon([(-5, -5), (0.5, -5), (0.5, 0.5), (-5, 0.5)])
        assert list(_shape_pixels(shape, intensity_image[0], 1.0)) == [0]

    def test_shape_outside_frame(self, intensity_image):
        shape = Polygon([(20, 20), (22, 20), (22, 22), (20, 22)])
        assert _shape_pixels(shape, intensity_image[0], 1.0).size == 0


# CellIntensityFromLabelImage ###################################################


class TestCellIntensityFromLabelImage:
    def test_compute_total(
        self, cell_lineage, label_image, intensity_image, prop_cell_lin
    ):
        calculator = CellIntensityFromLabelImage(
            prop_cell_lin, "total", intensity_image, "label", label_image
        )
        # Rows 1-2, columns 1-3: 9 + 10 + 11 + 17 + 18 + 19.
        assert calculator.compute(cell_lineage, node_id=1) == 84.0

    def test_compute_mean(
        self, cell_lineage, label_image, intensity_image, prop_cell_lin
    ):
        calculator = CellIntensityFromLabelImage(
            prop_cell_lin, "mean", intensity_image, "label", label_image
        )
        assert calculator.compute(cell_lineage, node_id=1) == 14.0

    def test_compute_all_pieces(
        self, cell_lineage, label_image, intensity_image, prop_cell_lin
    ):
        calculator = CellIntensityFromLabelImage(
            prop_cell_lin, "total", intensity_image, "label", label_image
        )
        # The 2x2 square (29 + 30 + 37 + 38) and the pixel (0, 7) of value 7.
        assert calculator.compute(cell_lineage, node_id=2) == 141.0

    def test_compute_hole_left_out(self, prop_cell_lin):
        label_image = np.ones((1, 3, 3), dtype=np.uint32)
        label_image[0, 1, 1] = 0
        lineage = CellLineage()
        lineage.add_node(1, label=1, timepoint=0)
        calculator = CellIntensityFromLabelImage(
            prop_cell_lin, "total", np.ones((1, 3, 3)), "label", label_image
        )
        assert calculator.compute(lineage, node_id=1) == 8.0

    def test_compute_background(
        self, cell_lineage, label_image, intensity_image, prop_cell_lin
    ):
        total = CellIntensityFromLabelImage(
            prop_cell_lin,
            "total",
            intensity_image,
            "label",
            label_image,
            background=4.0,
        )
        mean = CellIntensityFromLabelImage(
            prop_cell_lin, "mean", intensity_image, "label", label_image, background=4.0
        )
        assert total.compute(cell_lineage, node_id=1) == 84.0 - 6 * 4.0
        assert mean.compute(cell_lineage, node_id=1) == 10.0

    def test_compute_background_above_pixel_values(
        self, cell_lineage, label_image, prop_cell_lin
    ):
        # Subtracting the background from unsigned integers must not wrap around.
        intensity_image = np.full((1, 6, 8), 50, dtype=np.uint16)
        calculator = CellIntensityFromLabelImage(
            prop_cell_lin, "mean", intensity_image, "label", label_image, background=100
        )
        assert calculator.compute(cell_lineage, node_id=1) == -50.0

    def test_compute_3d(self, prop_cell_lin):
        label_image = np.zeros((1, 2, 3, 3), dtype=np.uint32)
        label_image[0, :, 1:, 1:] = 1
        intensity_image = np.zeros((1, 2, 3, 3))
        intensity_image[0, 1] = 2.0
        lineage = CellLineage()
        lineage.add_node(1, label=1, timepoint=0)
        calculator = CellIntensityFromLabelImage(
            prop_cell_lin, "total", intensity_image, "label", label_image
        )
        # 4 pixels in each of the 2 planes, of values 0 and 2.
        assert calculator.compute(lineage, node_id=1) == 8.0

    def test_compute_missing_label_raises(
        self, cell_lineage, label_image, intensity_image, prop_cell_lin
    ):
        cell_lineage.nodes[1]["label"] = 7
        calculator = CellIntensityFromLabelImage(
            prop_cell_lin, "total", intensity_image, "label", label_image
        )
        with pytest.raises(ValueError, match="Label 7 of cell 1"):
            calculator.compute(cell_lineage, node_id=1)

    def test_invalid_statistic_raises(
        self, label_image, intensity_image, prop_cell_lin
    ):
        with pytest.raises(ValueError, match="'statistic' must be one of"):
            CellIntensityFromLabelImage(
                prop_cell_lin, "median", intensity_image, "label", label_image
            )

    def test_get_input_props(self, label_image, intensity_image, prop_cell_lin):
        calculator = CellIntensityFromLabelImage(
            prop_cell_lin, "total", intensity_image, "my_label", label_image
        )
        assert calculator.get_input_props() == {
            "label_prop": ("my_label", "node", "cell")
        }

    def test_uses_external_data(self):
        assert CellIntensityFromLabelImage.uses_external_data()


# CellIntensityFromPolygon ####################################################


class TestCellIntensityFromPolygon:
    def test_compute_same_as_label_image_with_multipolygon(
        self, cell_lineage, label_image, intensity_image, prop_cell_lin
    ):
        # Shapes computed from the label image, with pixels of size 2.
        shape_calculator = CellMultiPolygonFromLabelImage(
            prop_cell_lin, label_prop="label", label_image=label_image, pixel_size=2.0
        )
        for nid in cell_lineage.nodes:
            shape = shape_calculator.compute(cell_lineage, nid)
            cell_lineage.nodes[nid]["cell_multipolygon"] = shape
        from_polygon = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_image, "cell_multipolygon", 2.0
        )
        from_label_image = CellIntensityFromLabelImage(
            prop_cell_lin, "total", intensity_image, "label", label_image
        )
        for nid in cell_lineage.nodes:
            assert from_polygon.compute(cell_lineage, nid) == from_label_image.compute(
                cell_lineage, nid
            )

    def test_compute_mean(self, cell_lineage, intensity_image, prop_cell_lin):
        cell_lineage.nodes[1]["cell_polygon"] = Polygon(
            [(0.5, 0.5), (2.5, 0.5), (2.5, 1.5), (0.5, 1.5)]
        )
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "mean", intensity_image, "cell_polygon", 1.0
        )
        assert calculator.compute(cell_lineage, node_id=1) == 9.5

    def test_compute_none_shape(self, cell_lineage, intensity_image, prop_cell_lin):
        cell_lineage.nodes[1]["cell_polygon"] = None
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_image, "cell_polygon", 1.0
        )
        assert math.isnan(calculator.compute(cell_lineage, node_id=1))

    def test_compute_no_pixel_center(
        self, cell_lineage, intensity_image, prop_cell_lin
    ):
        cell_lineage.nodes[1]["cell_polygon"] = MultiPolygon(
            [Polygon([(20, 20), (22, 20), (22, 22), (20, 22)])]
        )
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_image, "cell_polygon", 1.0
        )
        assert math.isnan(calculator.compute(cell_lineage, node_id=1))

    def test_compute_missing_shape_raises(
        self, cell_lineage, intensity_image, prop_cell_lin
    ):
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_image, "cell_polygon", 1.0
        )
        with pytest.raises(KeyError, match="missing 'cell_polygon' property"):
            calculator.compute(cell_lineage, node_id=1)

    def test_get_input_props(self, intensity_image, prop_cell_lin):
        calculator = CellIntensityFromPolygon(
            prop_cell_lin, "total", intensity_image, "my_polygon", 1.0
        )
        assert calculator.get_input_props() == {
            "polygon_prop": ("my_polygon", "node", "cell")
        }


# CycleMeanIntensity ##########################################################


class TestCycleMeanIntensity:
    def test_compute(self, data, prop_cycle_lin):
        calculator = CycleMeanIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_lineages[1], node_id=4) == 2.5

    def test_compute_ignores_nan(self, data, prop_cycle_lin):
        data.cell_lineages[1].nodes[1]["cell_mean_intensity"] = np.nan
        calculator = CycleMeanIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_lineages[1], node_id=4) == 3.0

    def test_compute_custom_intensity_prop(self, data, prop_cycle_lin):
        calculator = CycleMeanIntensity(
            prop_cycle_lin, intensity_prop="cell_total_intensity"
        )
        assert calculator.compute(data, data.cycle_lineages[1], node_id=6) == 55.0

    def test_get_input_props(self, prop_cycle_lin):
        calculator = CycleMeanIntensity(prop_cycle_lin)
        assert calculator.get_input_props() == {
            "intensity_prop": ("cell_mean_intensity", "node", "cell")
        }


# BirthIntensity ##############################################################


class TestBirthIntensity:
    def test_compute_complete_cycle(self, data, prop_cycle_lin):
        calculator = BirthIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_lineages[1], node_id=6) == 50.0

    def test_compute_leaf_cycle(self, data, prop_cycle_lin):
        calculator = BirthIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_lineages[1], node_id=7) == 70.0

    def test_compute_root_cycle(self, data, prop_cycle_lin):
        calculator = BirthIntensity(prop_cycle_lin)
        assert math.isnan(calculator.compute(data, data.cycle_lineages[1], node_id=4))

    def test_compute_custom_intensity_prop(self, data, prop_cycle_lin):
        calculator = BirthIntensity(
            prop_cycle_lin, intensity_prop="cell_mean_intensity"
        )
        assert calculator.compute(data, data.cycle_lineages[1], node_id=6) == 5.0


# DivisionIntensity ###########################################################


class TestDivisionIntensity:
    def test_compute_complete_cycle(self, data, prop_cycle_lin):
        calculator = DivisionIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_lineages[1], node_id=6) == 60.0

    def test_compute_root_cycle(self, data, prop_cycle_lin):
        calculator = DivisionIntensity(prop_cycle_lin)
        assert calculator.compute(data, data.cycle_lineages[1], node_id=4) == 40.0

    def test_compute_leaf_cycle(self, data, prop_cycle_lin):
        calculator = DivisionIntensity(prop_cycle_lin)
        assert math.isnan(calculator.compute(data, data.cycle_lineages[1], node_id=7))

    def test_compute_custom_intensity_prop(self, data, prop_cycle_lin):
        calculator = DivisionIntensity(
            prop_cycle_lin, intensity_prop="cell_mean_intensity"
        )
        assert calculator.compute(data, data.cycle_lineages[1], node_id=6) == 6.0
