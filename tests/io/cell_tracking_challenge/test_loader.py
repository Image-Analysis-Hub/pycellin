#!/usr/bin/env python3

"""Unit tests for the CTC loader from pycellin.io.cell_tracking_challenge."""

import logging
import warnings

import numpy as np
import pytest
import tifffile

from pycellin.io.cell_tracking_challenge.loader import (
    _extract_seg_data,
    _get_label_img_paths,
    _integrate_label_imgs_metadata,
    load_CTC_file,
)

# Fixtures ####################################################################


@pytest.fixture
def label_img_path(tmp_path):
    # Label 1 is a 2x3 rectangle (rows 2-3, columns 5-7). Label 2 is made of
    # a 3x3 square (rows 6-8, columns 1-3) and of a single pixel (row 9, column 10).
    img = np.zeros((10, 12), dtype=np.uint16)
    img[2:4, 5:8] = 1
    img[6:9, 1:4] = 2
    img[9, 10] = 2
    path = tmp_path / "man_seg000.tif"
    tifffile.imwrite(path, img)
    return str(path)


def _write_label_imgs(labels_path, **imwrite_kwargs):
    # Label 1 is a 2x3 rectangle (rows 2-3) that moves one column to the right
    # between frames 0 and 1. Label 2 is a 3x3 square (rows 6-8, columns 1-3).
    for frame in range(2):
        img = np.zeros((10, 12), dtype=np.uint16)
        img[2:4, 5 + frame : 8 + frame] = 1
        img[6:9, 1:4] = 2
        tifffile.imwrite(labels_path / f"mask{frame:03d}.tif", img, **imwrite_kwargs)


@pytest.fixture
def ctc_data(tmp_path):
    # Tracks 1 and 2 over frames 0 and 1: cells 0 and 1, then cells 2 and 3.
    ctc_path = tmp_path / "res_track.txt"
    ctc_path.write_text("1 0 1 0\n2 0 1 0\n")
    labels_path = tmp_path / "labels"
    labels_path.mkdir()
    _write_label_imgs(labels_path)
    return ctc_path, labels_path


def _get_cells(model):
    return {
        attrs["cell_id"]: attrs
        for lin in model.data.cell_data.values()
        for _, attrs in lin.nodes(data=True)
    }


# _get_label_img_paths ########################################################


class TestGetLabelImgPaths:
    def test_label_imgs_sorted_by_name(self, ctc_data):
        _, labels_path = ctc_data
        paths = _get_label_img_paths(labels_path)
        assert [path.name for path in paths] == ["mask000.tif", "mask001.tif"]

    def test_file_raises(self, ctc_data):
        _, labels_path = ctc_data
        with pytest.raises(ValueError, match="is not a folder"):
            _get_label_img_paths(labels_path / "mask000.tif")

    def test_missing_folder_raises(self, tmp_path):
        with pytest.raises(ValueError, match="is not a folder"):
            _get_label_img_paths(tmp_path / "missing")

    def test_folder_without_tif_raises(self, tmp_path):
        with pytest.raises(ValueError, match="No label images found"):
            _get_label_img_paths(tmp_path)


# _integrate_label_imgs_metadata ##############################################


class TestIntegrateLabelImgsMetadata:
    def test_resolution_with_unit(self, tmp_path):
        path = tmp_path / "mask000.tif"
        tifffile.imwrite(
            path,
            np.zeros((4, 4), dtype=np.uint16),
            resolution=(2.0, 0.5),
            resolutionunit="CENTIMETER",
        )
        metadata = {}
        _integrate_label_imgs_metadata(metadata, path)
        assert metadata == {
            "space_unit": "cm",
            "pixel_width": 0.5,
            "pixel_height": 2.0,
            "pixel_depth": 1.0,
        }

    def test_imagej_unit_and_spacing(self, tmp_path):
        path = tmp_path / "mask000.tif"
        tifffile.imwrite(
            path,
            np.zeros((4, 4), dtype=np.uint16),
            imagej=True,
            resolution=(4.0, 4.0),
            metadata={"unit": "micron", "spacing": 2.0},
        )
        metadata = {}
        _integrate_label_imgs_metadata(metadata, path)
        assert metadata == {
            "space_unit": "micron",
            "pixel_width": 0.25,
            "pixel_height": 0.25,
            "pixel_depth": 2.0,
        }

    def test_imagej_escaped_unit(self, tmp_path):
        # Fiji writes non-ASCII characters as escapes: "µm" becomes "\u00B5m".
        path = tmp_path / "mask000.tif"
        tifffile.imwrite(
            path,
            np.zeros((4, 4), dtype=np.uint16),
            description="ImageJ=1.54f\nunit=\\u00B5m\n",
            resolution=(4.0, 4.0),
            resolutionunit="NONE",
            metadata=None,
        )
        metadata = {}
        _integrate_label_imgs_metadata(metadata, path)
        assert metadata["space_unit"] == "µm"

    def test_resolution_without_unit_ignored(self, tmp_path):
        # ImageJ images without unit have a resolution but no ResolutionUnit.
        path = tmp_path / "mask000.tif"
        tifffile.imwrite(
            path, np.zeros((4, 4), dtype=np.uint16), imagej=True, resolution=(4.0, 4.0)
        )
        metadata = {}
        _integrate_label_imgs_metadata(metadata, path)
        assert metadata == {
            "space_unit": "pixel",
            "pixel_width": 1.0,
            "pixel_height": 1.0,
            "pixel_depth": 1.0,
        }

    def test_resolution_in_inches_ignored(self, tmp_path):
        path = tmp_path / "mask000.tif"
        tifffile.imwrite(
            path,
            np.zeros((4, 4), dtype=np.uint16),
            resolution=(72.0, 72.0),
            resolutionunit="INCH",
        )
        metadata = {}
        with pytest.warns(UserWarning, match="given in inches"):
            _integrate_label_imgs_metadata(metadata, path)
        assert metadata == {
            "space_unit": "pixel",
            "pixel_width": 1.0,
            "pixel_height": 1.0,
            "pixel_depth": 1.0,
        }

    def test_resolution_in_inches_no_warning_when_calibrated(self, tmp_path):
        path = tmp_path / "mask000.tif"
        tifffile.imwrite(
            path,
            np.zeros((4, 4), dtype=np.uint16),
            resolution=(72.0, 72.0),
            resolutionunit="INCH",
        )
        metadata = {"space_unit": "um", "pixel_width": 0.1, "pixel_height": 0.1}
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _integrate_label_imgs_metadata(metadata, path)
        assert metadata["pixel_depth"] == 1.0

    def test_given_values_kept(self, tmp_path):
        path = tmp_path / "mask000.tif"
        tifffile.imwrite(
            path,
            np.zeros((4, 4), dtype=np.uint16),
            resolution=(2.0, 0.5),
            resolutionunit="CENTIMETER",
        )
        metadata = {"space_unit": "um", "pixel_width": 0.1, "pixel_height": 0.1}
        _integrate_label_imgs_metadata(metadata, path)
        assert metadata == {
            "space_unit": "um",
            "pixel_width": 0.1,
            "pixel_height": 0.1,
            "pixel_depth": 1.0,
        }


# _extract_seg_data ###########################################################


class TestExtractSegData:
    def test_labels_and_centroids(self, label_img_path):
        labels, centroids, _ = _extract_seg_data(label_img_path)
        assert labels == [1, 2]
        assert centroids[0] == pytest.approx([6.0, 2.5])

    def test_contour_relative_to_centroid(self, label_img_path):
        _, _, contours = _extract_seg_data(label_img_path)
        xs, ys = zip(*contours[0])
        assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx(
            (-1.5, 1.5, -1.0, 1.0)
        )

    def test_label_in_several_pieces_keeps_largest(self, label_img_path):
        _, centroids, contours = _extract_seg_data(label_img_path)
        x0 = centroids[1][0]
        xs, _ = zip(*contours[1])
        # The single pixel at column 10 is not part of the contour.
        assert max(xs) + x0 == pytest.approx(3.5)

    def test_label_in_several_pieces_logs_warning(self, label_img_path, caplog):
        with caplog.at_level(logging.WARNING):
            _extract_seg_data(label_img_path)
        assert "Labels [2]" in caplog.text

    def test_pixel_size(self, label_img_path):
        _, centroids, contours = _extract_seg_data(
            label_img_path, pixel_width=0.5, pixel_height=2.0
        )
        assert centroids[0] == pytest.approx([3.0, 5.0])
        xs, ys = zip(*contours[0])
        assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx(
            (-0.75, 0.75, -2.0, 2.0)
        )

    def test_3d_label_image_raises(self, tmp_path):
        path = tmp_path / "mask000.tif"
        tifffile.imwrite(
            path, np.zeros((3, 10, 12), dtype=np.uint16), photometric="minisblack"
        )
        with pytest.raises(ValueError, match="only 2D label images"):
            _extract_seg_data(str(path))


# load_CTC_file ###############################################################


class TestLoadCTCFile:
    def test_labels_give_positions_and_contours(self, ctc_data):
        ctc_path, labels_path = ctc_data
        model = load_CTC_file(ctc_path, labels_path=labels_path)

        cells = _get_cells(model)
        assert (cells[0]["cell_x"], cells[0]["cell_y"]) == pytest.approx((6.0, 2.5))
        assert (cells[1]["cell_x"], cells[1]["cell_y"]) == pytest.approx((7.0, 2.5))
        assert (cells[2]["cell_x"], cells[2]["cell_y"]) == pytest.approx((2.0, 7.0))
        assert all("cell_contour" in attrs for attrs in cells.values())
        assert model.get_space_unit() == "pixel"
        for prop_id in ("cell_x", "cell_y", "cell_contour"):
            assert model.get_property(prop_id).unit == "pixel"

    def test_positions_and_contours_in_space_unit(self, ctc_data):
        ctc_path, labels_path = ctc_data
        model = load_CTC_file(
            ctc_path,
            labels_path=labels_path,
            space_unit="um",
            pixel_width=0.5,
            pixel_height=2.0,
            pixel_depth=1.0,
        )

        cells = _get_cells(model)
        assert (cells[0]["cell_x"], cells[0]["cell_y"]) == pytest.approx((3.0, 5.0))
        xs, ys = zip(*cells[0]["cell_contour"])
        assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx(
            (-0.75, 0.75, -2.0, 2.0)
        )
        for prop_id in ("cell_x", "cell_y", "cell_contour"):
            assert model.get_property(prop_id).unit == "um"
        assert model.model_metadata.label_imgs_location == labels_path

    def test_pixel_size_read_from_label_imgs(self, ctc_data):
        ctc_path, labels_path = ctc_data
        _write_label_imgs(
            labels_path, resolution=(2.0, 0.5), resolutionunit="CENTIMETER"
        )
        model = load_CTC_file(ctc_path, labels_path=labels_path)

        assert model.get_space_unit() == "cm"
        assert (model.get_pixel_width(), model.get_pixel_height()) == (0.5, 2.0)
        cells = _get_cells(model)
        assert (cells[0]["cell_x"], cells[0]["cell_y"]) == pytest.approx((3.0, 5.0))
        assert model.get_property("cell_x").unit == "cm"

    def test_resolution_in_inches_ignored(self, ctc_data):
        ctc_path, labels_path = ctc_data
        _write_label_imgs(labels_path, resolution=(72.0, 72.0), resolutionunit="INCH")
        with pytest.warns(UserWarning, match="given in inches") as record:
            model = load_CTC_file(ctc_path, labels_path=labels_path)

        # The warning points to the call of load_CTC_file().
        assert record[0].filename == __file__
        assert model.get_space_unit() == "pixel"
        cells = _get_cells(model)
        assert (cells[0]["cell_x"], cells[0]["cell_y"]) == pytest.approx((6.0, 2.5))

    def test_stack_of_frames_raises(self, ctc_data):
        # A stack holding all the frames, whose name has no frame number.
        ctc_path, labels_path = ctc_data
        for path in labels_path.iterdir():
            path.unlink()
        tifffile.imwrite(
            labels_path / "labels.tif",
            np.zeros((2, 10, 12), dtype=np.uint16),
            photometric="minisblack",
        )
        with pytest.raises(ValueError, match="only 2D label images, one per frame"):
            load_CTC_file(ctc_path, labels_path=labels_path)

    def test_labels_path_not_a_folder_raises(self, ctc_data):
        # The folder is checked even when the label images are not read for the
        # space unit and pixel sizes, since they are given.
        ctc_path, labels_path = ctc_data
        with pytest.raises(ValueError, match="is not a folder"):
            load_CTC_file(
                ctc_path,
                labels_path=labels_path / "mask000.tif",
                space_unit="um",
                pixel_width=1.0,
                pixel_height=1.0,
                pixel_depth=1.0,
            )

    def test_label_without_cell_raises(self, ctc_data):
        ctc_path, labels_path = ctc_data
        img = tifffile.imread(labels_path / "mask001.tif")
        img[0, 0] = 9
        tifffile.imwrite(labels_path / "mask001.tif", img)
        with pytest.raises(ValueError, match="Label 9 not found"):
            load_CTC_file(ctc_path, labels_path=labels_path)
