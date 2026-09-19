#!/usr/bin/env python3

"""Unit test for topology property classes from pycellin.properties."""

import logging

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

    def test_compute_with_tag_names(self, prop, mask):
        calculator = LocationTag(
            prop, mask_img=mask, pixel_size=1.0, tag_names={1: "a", 112: "b"}
        )
        assert calculator.compute(make_lineage(1.0, 0.0, 0), 1) == "a"
        assert calculator.compute(make_lineage(2.0, 1.0, 1), 1) == "b"

    def test_compute_value_missing_from_tag_names_is_none(self, prop, mask):
        calculator = LocationTag(prop, mask_img=mask, pixel_size=1.0, tag_names={1: "a"})
        assert calculator.compute(make_lineage(0.0, 0.0, 0), 1) is None

    def test_compute_with_tag_names_out_of_bounds_raises(self, prop, mask):
        calculator = LocationTag(prop, mask_img=mask, pixel_size=1.0, tag_names={1: "a"})
        with pytest.raises(ValueError, match="x index 4"):
            calculator.compute(make_lineage(4.0, 0.0, 0), 1)

    def test_numpy_int_keys_accepted(self, prop, mask):
        calculator = LocationTag(
            prop, mask_img=mask, pixel_size=1.0, tag_names={np.uint32(1): "a"}
        )
        assert calculator.compute(make_lineage(1.0, 0.0, 0), 1) == "a"

    def test_empty_tag_names_raises(self, prop, mask):
        with pytest.raises(ValueError, match="must not be empty"):
            LocationTag(prop, mask_img=mask, pixel_size=1.0, tag_names={})

    def test_non_int_key_raises(self, prop, mask):
        with pytest.raises(TypeError, match="keys must be int"):
            LocationTag(prop, mask_img=mask, pixel_size=1.0, tag_names={1.0: "a"})

    def test_bool_key_raises(self, prop, mask):
        with pytest.raises(TypeError, match="keys must be int"):
            LocationTag(prop, mask_img=mask, pixel_size=1.0, tag_names={True: "a"})

    def test_non_str_value_raises(self, prop, mask):
        with pytest.raises(TypeError, match="values must be str"):
            LocationTag(prop, mask_img=mask, pixel_size=1.0, tag_names={1: 1})

    def test_tag_name_value_missing_from_mask_warns(self, prop, mask):
        with pytest.warns(UserWarning, match=r"\[7, 999\] are not in the mask"):
            LocationTag(
                prop,
                mask_img=mask,
                pixel_size=1.0,
                tag_names={1: "a", 7: "b", 999: "c"},
            )

    def test_unmapped_mask_values_logged_as_info(self, prop, caplog):
        mask = np.array([[[0, 1], [2, 2]]], dtype=np.uint32)
        with caplog.at_level(logging.INFO, logger="pycellin.properties.topology"):
            LocationTag(prop, mask_img=mask, pixel_size=1.0, tag_names={1: "a"})
        assert "Mask values [0, 2] have no tag name" in caplog.text

    def test_full_coverage_neither_warns_nor_logs(self, prop, recwarn, caplog):
        mask = np.array([[[0, 1], [2, 2]]], dtype=np.uint32)
        with caplog.at_level(logging.INFO, logger="pycellin.properties.topology"):
            LocationTag(
                prop, mask_img=mask, pixel_size=1.0, tag_names={0: "", 1: "a", 2: "b"}
            )
        assert len(recwarn) == 0
        assert caplog.text == ""
