#!/usr/bin/env python3

"""Unit test for topology property classes from pycellin.properties."""

import numpy as np
import pytest

from pycellin.classes import CellLineage, Property
from pycellin.properties.topology import LocationTag

# Fixtures ####################################################################


@pytest.fixture
def prop():
    return Property(
        identifier="location_tag",
        name="Location tag",
        description="test property",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
    )


@pytest.fixture
def mask():
    # 2 timepoints, 3 rows, 4 columns: value = 100 * t + 10 * y + x.
    t, y, x = np.indices((2, 3, 4))
    return (100 * t + 10 * y + x).astype(np.uint32)


def make_lineage(x: float, y: float, t: int) -> CellLineage:
    lineage = CellLineage()
    lineage.add_node(1, cell_x=x, cell_y=y, timepoint=t)
    return lineage


# LocationTag #################################################################


class TestLocationTag:
    def test_compute_on_pixel_center(self, prop, mask):
        calculator = LocationTag(prop, mask_img=mask, pixel_size=1.0)
        assert calculator.compute(make_lineage(2.0, 1.0, 1), 1) == 112

    def test_compute_rounds_to_nearest_pixel(self, prop, mask):
        calculator = LocationTag(prop, mask_img=mask, pixel_size=1.0)
        assert calculator.compute(make_lineage(1.6, 0.7, 0), 1) == 12
        assert calculator.compute(make_lineage(1.4, 0.3, 0), 1) == 1

    def test_compute_with_pixel_size(self, prop, mask):
        calculator = LocationTag(prop, mask_img=mask, pixel_size=0.5)
        assert calculator.compute(make_lineage(1.5, 1.0, 0), 1) == 23

    def test_compute_near_zero_is_inside(self, prop, mask):
        calculator = LocationTag(prop, mask_img=mask, pixel_size=1.0)
        assert calculator.compute(make_lineage(-0.4, -0.4, 0), 1) == 0

    def test_compute_negative_coordinate_raises(self, prop, mask):
        calculator = LocationTag(prop, mask_img=mask, pixel_size=1.0)
        with pytest.raises(ValueError, match="x index -1"):
            calculator.compute(make_lineage(-1.0, 0.0, 0), 1)

    def test_compute_coordinate_past_edge_raises(self, prop, mask):
        calculator = LocationTag(prop, mask_img=mask, pixel_size=1.0)
        with pytest.raises(ValueError, match="y index 3"):
            calculator.compute(make_lineage(0.0, 2.6, 0), 1)

    def test_compute_timepoint_out_of_range_raises(self, prop, mask):
        calculator = LocationTag(prop, mask_img=mask, pixel_size=1.0)
        with pytest.raises(ValueError, match="t index 2"):
            calculator.compute(make_lineage(0.0, 0.0, 2), 1)
