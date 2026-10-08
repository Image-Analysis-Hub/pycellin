#!/usr/bin/env python3

"""
A collection of intensity properties that can be added to lineage graphs:
the intensity of each cell in an intensity image, and summaries of it
over cell cycles.
"""

from abc import abstractmethod
from math import ceil, floor
from typing import ClassVar, Literal

import numpy as np
from shapely import get_parts
from shapely.geometry.base import BaseGeometry

from pycellin.classes.data import Data
from pycellin.classes.lineage import CellLineage, CycleLineage
from pycellin.classes.property import Property
from pycellin.classes.property_calculator import (
    NodeGlobalPropCalculator,
    NodeLocalPropCalculator,
)
from pycellin.properties.morphology import _find_label
from pycellin.properties.utils import _get_cycle_node_property_values, _nanmean


def create_cell_total_intensity_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    custom_provenance: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cell_total_intensity",
        name=custom_name or "Cell total intensity",
        description=custom_description
        or "Sum of the pixel values of the cell in an intensity image",
        provenance=custom_provenance or "pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


def create_cell_mean_intensity_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    custom_provenance: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cell_mean_intensity",
        name=custom_name or "Cell mean intensity",
        description=custom_description
        or "Mean of the pixel values of the cell in an intensity image",
        provenance=custom_provenance or "pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


def _inside_even_odd(
    edges: np.ndarray, cols: np.ndarray, rows: np.ndarray
) -> np.ndarray:
    """
    Test which points of a grid are inside a shape, with the even-odd rule.

    A point is inside when a ray from it towards increasing x crosses the edges of
    the shape an odd number of times. A point exactly on an edge is inside when the
    edge is a left or top edge of the shape (smallest x or y), and outside otherwise,
    as in the top-left rule of GPU rasterization. So a point on an edge shared by two
    touching shapes is inside exactly one of them.

    Parameters
    ----------
    edges : np.ndarray
        Edges of all the rings of the shape (exterior and interior rings of all its
        polygons), as an array of shape (n_edges, 4) of (x1, y1, x2, y2).
    cols : np.ndarray
        1D array of the x coordinates of the grid columns.
    rows : np.ndarray
        1D array of the y coordinates of the grid rows.

    Returns
    -------
    np.ndarray
        Boolean array of shape (len(rows), len(cols)), True for points inside.
    """
    # Orient each edge from its smaller y to its larger y, so that two shapes sharing
    # an edge compute exactly the same crossings whatever the direction of their rings.
    x1, y1, x2, y2 = edges.T
    upward = y1 < y2
    xa, ya = np.where(upward, x1, x2), np.where(upward, y1, y2)
    xb, yb = np.where(upward, x2, x1), np.where(upward, y2, y1)
    sloped = ya != yb  # Horizontal edges are never crossed.
    xa, ya, xb, yb = xa[sloped], ya[sloped], xb[sloped], yb[sloped]

    # x of the crossing of each row with each edge, or -inf if the edge doesn't
    # cross the row.
    y = rows[:, np.newaxis]
    x_cross = np.where(
        (ya <= y) & (y < yb), xa + (xb - xa) * (y - ya) / (yb - ya), -np.inf
    )
    # Count the crossings strictly to the right of each point, by blocks of rows
    # so that the comparison array stays under about a million values.
    inside = np.empty((len(rows), len(cols)), dtype=bool)
    block = max(1, 1_000_000 // max(x_cross.shape[1] * len(cols), 1))
    for start in range(0, len(rows), block):
        n_right = (x_cross[start : start + block, :, np.newaxis] > cols).sum(axis=1)
        inside[start : start + block] = n_right % 2 == 1
    return inside


def _shape_pixels(
    shape: BaseGeometry, frame: np.ndarray, pixel_size: float
) -> np.ndarray:
    """
    Return the values of the pixels of a 2D frame whose center is inside a shape.

    The center of the pixel at row r and column c is at (x, y) = (c, r) times the
    pixel size. A pixel whose center is exactly on an edge of the shape is counted
    when the edge is a left or top edge of the shape (see `_inside_even_odd()`), so
    that a pixel on an edge shared by two touching shapes is counted in exactly one
    of them.

    Parameters
    ----------
    shape : BaseGeometry
        The shape, a shapely Polygon or MultiPolygon, in the coordinates of the
        frame scaled by the pixel size.
    frame : np.ndarray
        2D image.
    pixel_size : float
        The size of each pixel, in the unit of the shape coordinates.

    Returns
    -------
    np.ndarray
        1D array of the values of the pixels inside the shape. Empty if no pixel
        center is inside the shape.
    """
    # Rings in pixel coordinates, so that pixel centers have integer coordinates.
    rings = [
        np.asarray(ring.coords) / pixel_size
        for polygon in get_parts(shape)
        for ring in (polygon.exterior, *polygon.interiors)
    ]
    if not rings:
        return frame[:0, :0].ravel()
    edges = np.vstack([np.hstack([ring[:-1], ring[1:]]) for ring in rings])
    xs, ys = edges[:, [0, 2]], edges[:, [1, 3]]
    first_col = max(ceil(xs.min()), 0)
    last_col = min(floor(xs.max()), frame.shape[1] - 1)
    first_row = max(ceil(ys.min()), 0)
    last_row = min(floor(ys.max()), frame.shape[0] - 1)
    if first_col > last_col or first_row > last_row:
        return frame[:0, :0].ravel()
    inside = _inside_even_odd(
        edges,
        np.arange(first_col, last_col + 1, dtype=float),
        np.arange(first_row, last_row + 1, dtype=float),
    )
    return frame[first_row : last_row + 1, first_col : last_col + 1][inside]


class _CellIntensityCalculator(NodeLocalPropCalculator):
    """
    Base class of the calculators computing the intensity of cells in an
    intensity image.

    Subclasses implement `_cell_pixels()`, which returns the values of the pixels
    of a cell.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    statistic : {"total", "mean"}
        Statistic computed on the pixel values of each cell: their sum or their mean.
    intensity_img : np.ndarray
        The intensity image, with time as first axis.
    background : float, optional
        Value subtracted from each pixel value before computing the statistic.
        Defaults to 0.

    Raises
    ------
    ValueError
        If `statistic` is not "total" or "mean".
    """

    # The intensity image belongs to the model the calculator was created for.
    _USES_EXTERNAL_DATA = True

    def __init__(
        self,
        property: Property,
        statistic: Literal["total", "mean"],
        intensity_img: np.ndarray,
        background: float = 0.0,
    ):
        super().__init__(property)
        if statistic not in ("total", "mean"):
            raise ValueError(
                f"'statistic' must be one of 'total', 'mean', got {statistic!r}."
            )
        self.statistic = statistic
        self.intensity_img = intensity_img
        self.background = background

    @abstractmethod
    def _cell_pixels(self, lineage: CellLineage, nid: int) -> np.ndarray | None:
        """
        Return the values of the pixels of a cell in the intensity image.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the cell.
        nid : int
            Node ID of the cell.

        Returns
        -------
        np.ndarray | None
            1D array of the values of the pixels of the cell, or None if the cell
            has no shape.
        """

    def compute(  # type: ignore[override]
        self, lineage: CellLineage, nid: int
    ) -> float:
        """
        Compute the intensity of a cell.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the cell.
        nid : int
            Node ID of the cell.

        Returns
        -------
        float
            Sum or mean of the background-subtracted pixel values of the cell,
            or NaN if the cell has no pixel.
        """
        values = self._cell_pixels(lineage, nid)
        if values is None or values.size == 0:
            return np.nan
        values = values.astype(np.float64) - self.background
        return float(values.sum() if self.statistic == "total" else values.mean())


class CellIntensityFromLabelImg(_CellIntensityCalculator):
    """
    A calculator for the cell intensity properties, which takes the pixels of each
    cell from a label image.

    The pixels of a cell are all the pixels of its label: all its pieces, without
    its holes. Images can be 2D or 3D, with time as first axis.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    statistic : {"total", "mean"}
        Statistic computed on the pixel values of each cell: their sum or their mean.
    intensity_img : np.ndarray
        The intensity image, with the same shape as the label image.
    label_prop : str
        Name of the property that stores cell labels.
    label_img : np.ndarray
        The label image.
    background : float, optional
        Value subtracted from each pixel value before computing the statistic.
        Defaults to 0.

    Raises
    ------
    ValueError
        If `statistic` is not "total" or "mean".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "label_prop": ("node", "CellLineage")
    }

    def __init__(
        self,
        property: Property,
        statistic: Literal["total", "mean"],
        intensity_img: np.ndarray,
        label_prop: str,
        label_img: np.ndarray,
        background: float = 0.0,
    ):
        super().__init__(property, statistic, intensity_img, background)
        self.label_prop = label_prop
        self.label_img = label_img
        # Bounding boxes of the labels of each timepoint, computed on first use.
        self._label_slices: dict[int, list[tuple[slice, ...] | None]] = {}

    def _cell_pixels(self, lineage: CellLineage, nid: int) -> np.ndarray:
        t, bbox, mask = _find_label(
            self.label_img, self._label_slices, lineage, nid, self.label_prop
        )
        return self.intensity_img[t][bbox][mask]


class CellIntensityFromPolygon(_CellIntensityCalculator):
    """
    A calculator for the cell intensity properties, which takes the pixels of each
    cell from its shape.

    The pixels of a cell are the pixels whose center is inside its shape, a
    shapely Polygon or MultiPolygon. A pixel whose center is exactly on an edge is
    counted only if the edge is a left or top edge of the shape, so that a pixel on
    the edge shared by two touching cells is counted in exactly one of them. The
    intensity is NaN for cells whose shape is None, or that contain no pixel center.
    Images are 2D, with time as first axis.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    statistic : {"total", "mean"}
        Statistic computed on the pixel values of each cell: their sum or their mean.
    intensity_img : np.ndarray
        The intensity image, with axes (t, y, x).
    polygon_prop : str
        Identifier of the node property holding the cell shapes as
        shapely.Polygon or shapely.MultiPolygon.
    pixel_size : float
        The size of each pixel, in the unit of the shape coordinates.
    background : float, optional
        Value subtracted from each pixel value before computing the statistic.
        Defaults to 0.

    Raises
    ------
    ValueError
        If `statistic` is not "total" or "mean".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "polygon_prop": ("node", "CellLineage")
    }

    def __init__(
        self,
        property: Property,
        statistic: Literal["total", "mean"],
        intensity_img: np.ndarray,
        polygon_prop: str,
        pixel_size: float,
        background: float = 0.0,
    ):
        super().__init__(property, statistic, intensity_img, background)
        self.polygon_prop = polygon_prop
        self.pixel_size = pixel_size

    def _cell_pixels(self, lineage: CellLineage, nid: int) -> np.ndarray | None:
        try:
            shape = lineage.nodes[nid][self.polygon_prop]
        except KeyError:
            raise KeyError(
                f"Cannot compute '{self.prop.identifier}': missing "
                f"'{self.polygon_prop}' property for cell {nid}, "
                f"lineage {lineage.graph['lineage_ID']}. "
                f"Please compute the '{self.polygon_prop}' property first."
            )
        if shape is None:
            return None
        frame = self.intensity_img[lineage.nodes[nid]["timepoint"]]
        return _shape_pixels(shape, frame, self.pixel_size)


def create_cycle_mean_intensity_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cycle_mean_intensity",
        name=custom_name or "Cycle mean intensity",
        description=custom_description
        or "Mean intensity of the cell during the cell cycle",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=unit,
    )


class CycleMeanIntensity(NodeGlobalPropCalculator):
    """
    Calculator to compute the mean intensity of a cell during a cell cycle.

    The cycle mean intensity is defined as the mean of the cell intensity values
    of all the cells of the cell cycle. NaN values are ignored.
    It is NaN when no cell of the cell cycle has an intensity value.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    intensity_prop : str, optional
        Identifier of the cell lineage node property holding the cell intensities.
        Defaults to "cell_mean_intensity".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "intensity_prop": ("node", "CellLineage")
    }

    def __init__(
        self, property: Property, intensity_prop: str = "cell_mean_intensity"
    ):
        super().__init__(property)
        self.intensity_prop = intensity_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CycleLineage, nid: int
    ) -> float:
        """
        Compute the mean intensity of a cell during the cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cycle_ID) of the cell cycle of interest.

        Returns
        -------
        float
            Mean intensity of the cell during the cell cycle, or NaN if no cell
            of the cell cycle has an intensity value.
        """
        intensities = _get_cycle_node_property_values(
            self.intensity_prop, data, lineage, nid
        )
        return _nanmean(intensities)


def create_birth_intensity_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "birth_intensity",
        name=custom_name or "Birth intensity",
        description=custom_description
        or "Intensity of the cell at the start of the cell cycle, right after division",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=unit,
    )


class BirthIntensity(NodeGlobalPropCalculator):
    """
    Calculator to compute the intensity of a cell at birth.

    The birth intensity is defined as the cell intensity value of the first cell
    of the cell cycle. It is NaN for cell cycles starting at a root,
    since their birth was not observed.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    intensity_prop : str, optional
        Identifier of the cell lineage node property holding the cell intensities.
        Defaults to "cell_total_intensity".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "intensity_prop": ("node", "CellLineage")
    }

    def __init__(
        self, property: Property, intensity_prop: str = "cell_total_intensity"
    ):
        super().__init__(property)
        self.intensity_prop = intensity_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CycleLineage, nid: int
    ) -> float:
        """
        Compute the intensity of a cell at birth.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cycle_ID) of the cell cycle of interest.

        Returns
        -------
        float
            Intensity of the first cell of the cell cycle, or NaN if the cell cycle
            starts at a root.
        """
        if lineage.is_root(nid):
            return np.nan
        return _get_cycle_node_property_values(
            self.intensity_prop, data, lineage, nid
        )[0]


def create_division_intensity_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "division_intensity",
        name=custom_name or "Division intensity",
        description=custom_description
        or "Intensity of the cell at the end of the cell cycle, right before division",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=unit,
    )


class DivisionIntensity(NodeGlobalPropCalculator):
    """
    Calculator to compute the intensity of a cell at division.

    The division intensity is defined as the cell intensity value of the last cell
    of the cell cycle. It is NaN for cell cycles ending at a leaf,
    since their division was not observed.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    intensity_prop : str, optional
        Identifier of the cell lineage node property holding the cell intensities.
        Defaults to "cell_total_intensity".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "intensity_prop": ("node", "CellLineage")
    }

    def __init__(
        self, property: Property, intensity_prop: str = "cell_total_intensity"
    ):
        super().__init__(property)
        self.intensity_prop = intensity_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CycleLineage, nid: int
    ) -> float:
        """
        Compute the intensity of a cell at division.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cycle_ID) of the cell cycle of interest.

        Returns
        -------
        float
            Intensity of the last cell of the cell cycle, or NaN if the cell cycle
            ends at a leaf.
        """
        if lineage.is_leaf(nid):
            return np.nan
        return _get_cycle_node_property_values(
            self.intensity_prop, data, lineage, nid
        )[-1]
