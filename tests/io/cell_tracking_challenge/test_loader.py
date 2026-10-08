#!/usr/bin/env python3

"""Unit tests for the CTC loader from pycellin.io.cell_tracking_challenge."""

import logging

import numpy as np
import pytest
import tifffile

from pycellin.io.cell_tracking_challenge.loader import _extract_seg_data

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
