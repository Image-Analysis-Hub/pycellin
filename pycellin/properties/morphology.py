#!/usr/bin/env python3

"""
A collection of diverse morphology properties that can be added to
lineage graphs.
"""

import logging
import warnings
from abc import abstractmethod
from itertools import combinations, product
from operator import itemgetter
from typing import ClassVar

import networkx as nx
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely import get_parts, make_valid
from shapely.affinity import affine_transform
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry
from skimage.measure import find_contours
from skimage.morphology import skeletonize

from pycellin.classes.data import Data
from pycellin.classes.lineage import CellLineage, CycleLineage
from pycellin.classes.property import Property
from pycellin.classes.property_calculator import (
    NodeGlobalPropCalculator,
    NodeLocalPropCalculator,
)
from pycellin.properties.utils import _get_cycle_node_property_values, _nanmean

logger = logging.getLogger(__name__)


def create_cell_polygon_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    custom_provenance: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cell_polygon",
        name=custom_name or "Cell polygon",
        description=custom_description or "Cell shape as a shapely.Polygon",
        provenance=custom_provenance or "pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="shapely.Polygon",
        unit=unit,
    )


def create_cell_multipolygon_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    custom_provenance: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cell_multipolygon",
        name=custom_name or "Cell multipolygon",
        description=custom_description
        or "Cell shape as a shapely.MultiPolygon, with all the pieces and holes "
        "of the cell label, computed from a label image",
        provenance=custom_provenance or "pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="shapely.MultiPolygon",
        unit=unit,
    )


def _trace_region(region: np.ndarray, fully_connected: str) -> np.ndarray:
    """
    Trace the contour of a 2D region without holes.

    The region is padded before tracing, so that a region touching the border
    of the array gets a closed contour.

    Parameters
    ----------
    region : np.ndarray
        2D binary array holding a single region without holes.
    fully_connected : {"high", "low"}
        "high" if the region is 8-connected, "low" if it is 4-connected
        (see skimage.measure.find_contours).

    Returns
    -------
    np.ndarray
        Contour of the region, as (x, y) pixel coordinates of the array.
    """
    padded = np.pad(region, 1)
    # A region without holes has a single contour.
    contour = find_contours(padded, 0.5, fully_connected=fully_connected)[0]
    # Undo the padding and switch from (row, col) to (x, y).
    return contour[:, ::-1] - 1


def _mask_to_polygons(mask: np.ndarray, fill_holes: bool = True) -> list[Polygon]:
    """
    Convert a 2D binary mask into one polygon per piece of the mask.

    Pieces are 8-connected: pixels that touch only by a corner belong to the same
    piece. Holes are 4-connected regions of background enclosed by a piece.
    Pieces touching the border of the mask get closed outlines.

    Parameters
    ----------
    mask : np.ndarray
        2D binary mask.
    fill_holes : bool, optional
        If True (default), holes are filled and each polygon is the outline of its
        piece. If False, holes become interior rings of the polygons.

    Returns
    -------
    list[Polygon]
        Polygons in (x, y) pixel coordinates of the mask, sorted by decreasing area.
        Empty if the mask is empty.
    """
    eight_connectivity = np.ones((3, 3), dtype=bool)
    pieces, n_pieces = ndi.label(mask, structure=eight_connectivity)
    polygons = []
    for piece_id in range(1, n_pieces + 1):
        piece = pieces == piece_id
        # binary_fill_holes() treats the background as 4-connected by default,
        # which matches the 8-connectivity of the pieces.
        filled = ndi.binary_fill_holes(piece)
        shell = _trace_region(filled, fully_connected="high")
        holes = []
        if not fill_holes:
            hole_regions, n_holes = ndi.label(filled & ~piece)
            for hole_id in range(1, n_holes + 1):
                # A hole can enclose other pieces: its ring is its filled outline.
                hole = ndi.binary_fill_holes(
                    hole_regions == hole_id, structure=eight_connectivity
                )
                holes.append(_trace_region(hole, fully_connected="low"))
        polygons.append(Polygon(shell, holes))
    return sorted(polygons, key=lambda polygon: polygon.area, reverse=True)


class _LabelImgShapeCalculator(NodeLocalPropCalculator):
    """
    Base class of the calculators computing the shape of cells from a label image.

    Subclasses implement `_shape_from_mask()`, which converts the mask of a cell
    label into a shapely geometry.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    label_prop : str
        Name of the property that stores cell labels.
    label_img : np.ndarray
        The label image.
    pixel_size : float
        The size of each pixel. Must be in the same unit as the property unit.
    force_recompute : bool, optional
        Whether to force recomputation of the property when it has already been
        computed, by default False.
    """

    # The label image belongs to the model the calculator was created for.
    _USES_EXTERNAL_DATA = True
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "label_prop": ("node", "CellLineage")
    }

    def __init__(
        self,
        property: Property,
        label_prop: str,
        label_img: np.ndarray,
        pixel_size: float,
        force_recompute: bool = False,
    ):
        super().__init__(property)
        self.label_prop = label_prop
        self.label_img = label_img
        self.pixel_size = pixel_size
        self.force_recompute = force_recompute
        # Bounding boxes of the labels of each timepoint, computed on first use.
        self._label_slices: dict[int, list[tuple[slice, slice] | None]] = {}

    @abstractmethod
    def _shape_from_mask(self, mask: np.ndarray, lineage, nid: int) -> BaseGeometry:
        """
        Convert the mask of a cell label into a shapely geometry.

        Parameters
        ----------
        mask : np.ndarray
            Binary mask of the cell label, cropped to its bounding box.
        lineage : CellLineage
            Lineage graph containing the cell.
        nid : int
            Node ID of the cell.

        Returns
        -------
        BaseGeometry
            Shape of the cell, in (x, y) pixel coordinates of the mask.
        """

    def compute(self, lineage, nid: int) -> BaseGeometry:
        if not self.force_recompute and self.prop.identifier in lineage.nodes[nid]:
            return lineage.nodes[nid][self.prop.identifier]

        _, (rows, cols), mask = _find_label(
            self.label_img, self._label_slices, lineage, nid, self.label_prop
        )
        shape = self._shape_from_mask(mask, lineage, nid)
        # Move the shape from the bounding box to the frame, then scale it.
        size = self.pixel_size
        return affine_transform(
            shape, [size, 0, 0, size, size * cols.start, size * rows.start]
        )


def _find_label(
    label_img: np.ndarray,
    label_slices: dict[int, list[tuple[slice, ...] | None]],
    lineage: CellLineage,
    nid: int,
    label_prop: str,
) -> tuple[int, tuple[slice, ...], np.ndarray]:
    """
    Find the pixels of the label of a cell in a label image.

    Parameters
    ----------
    label_img : np.ndarray
        The label image, with time as first axis.
    label_slices : dict[int, list[tuple[slice, ...] | None]]
        Bounding boxes of the labels of each timepoint, as returned by
        scipy.ndimage.find_objects(). The bounding boxes of a timepoint are
        computed and added on its first use.
    lineage : CellLineage
        Lineage graph containing the cell.
    nid : int
        Node ID of the cell.
    label_prop : str
        Name of the property that stores cell labels.

    Returns
    -------
    tuple[int, tuple[slice, ...], np.ndarray]
        The timepoint of the cell, the bounding box of its label in that
        timepoint, and the binary mask of the label in the bounding box.

    Raises
    ------
    ValueError
        If the label of the cell is not in its timepoint of the label image.
    """
    label = int(lineage.nodes[nid][label_prop])
    t = lineage.nodes[nid]["timepoint"]
    frame = label_img[t]
    if t not in label_slices:
        label_slices[t] = ndi.find_objects(frame)
    slices = label_slices[t]
    if not 0 < label <= len(slices) or slices[label - 1] is None:
        raise ValueError(
            f"Label {label} of cell {nid} (lineage "
            f"{lineage.graph['lineage_ID']}) is not in timepoint {t} "
            "of the label image."
        )
    bbox = slices[label - 1]
    return t, bbox, frame[bbox] == label


class CellPolygonFromLabelImg(_LabelImgShapeCalculator):
    """
    A calculator for the cell polygon property, which computes the cell shape as a
    shapely.Polygon from a label image.

    The polygon is the outline of the cell label: holes are filled and, when the
    label is made of several pieces, only the largest one is kept. At the end of
    each update, a single warning lists the cells whose label is made of several
    pieces or has holes. Pixels that touch only by a corner belong to the same piece.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    label_prop : str
        Name of the property that stores cell labels.
    label_img : np.ndarray
        The label image.
    pixel_size : float
        The size of each pixel. Must be in the same unit as the property unit.
    force_recompute : bool, optional
        Whether to force recomputation of the property when it has already been
        computed, by default False.
    """

    def __init__(
        self,
        property: Property,
        label_prop: str,
        label_img: np.ndarray,
        pixel_size: float,
        force_recompute: bool = False,
    ):
        super().__init__(property, label_prop, label_img, pixel_size, force_recompute)
        # (cell ID, lineage ID) of the cells whose label is in several pieces,
        # and of the cells whose label has holes.
        self._fragmented_cells: list[tuple[int, int]] = []
        self._cells_with_holes: list[tuple[int, int]] = []

    def enrich(
        self, data: Data, nodes_to_enrich: list[tuple[int, int]], **kwargs
    ) -> None:
        """
        Enrich the data with the cell polygons of a list of nodes.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        nodes_to_enrich : list of tuple[int, int]
            List of tuples containing the node ID and the lineage ID of the nodes
            to enrich with the property value.

        Warns
        -----
        UserWarning
            If the label of some cells is made of several pieces or has holes.
        """
        self._fragmented_cells = []
        self._cells_with_holes = []
        super().enrich(data, nodes_to_enrich, **kwargs)
        issues = []
        if self._fragmented_cells:
            issues.append(
                _describe_cells(
                    self._fragmented_cells, "a label made of several pieces"
                )
            )
        if self._cells_with_holes:
            issues.append(_describe_cells(self._cells_with_holes, "a label with holes"))
        if issues:
            warnings.warn(
                f"In the label image, {' and '.join(issues)}. "
                f"'{self.prop.identifier}' only keeps the largest piece of each label "
                "and fills its holes. To keep all the pieces and holes, use the cell "
                "multipolygon property instead: model.add_cell_multipolygon()."
            )

    def _shape_from_mask(self, mask: np.ndarray, lineage, nid: int) -> Polygon:
        polygons = _mask_to_polygons(mask)
        if len(polygons) > 1:
            self._fragmented_cells.append((nid, lineage.graph["lineage_ID"]))
        if (ndi.binary_fill_holes(mask) & ~mask).any():
            self._cells_with_holes.append((nid, lineage.graph["lineage_ID"]))
        return polygons[0]


def _describe_cells(cells: list[tuple[int, int]], what: str) -> str:
    """
    Describe a list of cells for a warning, naming the first five.

    Parameters
    ----------
    cells : list of tuple[int, int]
        (cell ID, lineage ID) of the cells.
    what : str
        What the cells have, e.g. "a label with holes".

    Returns
    -------
    str
        Description such as "2 cells have a label with holes (cell 3 of lineage 1,
        cell 8 of lineage 2)".
    """
    examples = ", ".join(f"cell {nid} of lineage {lin_ID}" for nid, lin_ID in cells[:5])
    if len(cells) > 5:
        examples += ", ..."
    cells_txt = "1 cell has" if len(cells) == 1 else f"{len(cells)} cells have"
    return f"{cells_txt} {what} ({examples})"


class CellMultiPolygonFromLabelImg(_LabelImgShapeCalculator):
    """
    A calculator for the cell multipolygon property, which computes the cell shape
    as a shapely.MultiPolygon from a label image.

    The multipolygon holds one polygon per piece of the cell label, sorted by
    decreasing area, with the holes of each piece as interior rings. Pixels that
    touch only by a corner belong to the same piece.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    label_prop : str
        Name of the property that stores cell labels.
    label_img : np.ndarray
        The label image.
    pixel_size : float
        The size of each pixel. Must be in the same unit as the property unit.
    force_recompute : bool, optional
        Whether to force recomputation of the property when it has already been
        computed, by default False.
    """

    def _shape_from_mask(self, mask: np.ndarray, lineage, nid: int) -> MultiPolygon:
        return MultiPolygon(_mask_to_polygons(mask, fill_holes=False))


def _largest_polygon(geometry: BaseGeometry) -> Polygon | None:
    """
    Return the largest polygon of a geometry, with its holes filled.

    Parameters
    ----------
    geometry : BaseGeometry
        Geometry to search, such as the output of shapely.make_valid(): a Polygon,
        a MultiPolygon or a GeometryCollection.

    Returns
    -------
    Polygon | None
        Outline of the largest polygon of the geometry, or None if the geometry
        has no area.
    """
    # make_valid() can nest a MultiPolygon in a GeometryCollection.
    polygons = [
        part
        for part in get_parts(get_parts(geometry))
        if isinstance(part, Polygon) and part.area > 0
    ]
    if not polygons:
        return None
    return Polygon(max(polygons, key=lambda polygon: polygon.area).exterior)


class CellPolygonFromContour(NodeLocalPropCalculator):
    """
    A calculator for the cell polygon property, which computes the cell shape as a
    shapely.Polygon from the cell contour and position.

    The contour holds the (x, y) coordinates of the outline of the cell, relative
    to the cell position (`cell_x`, `cell_y`), like the contours loaded from
    TrackMate or Cell Tracking Challenge data. The polygon is None for cells without
    a contour. An invalid contour, such as a contour that crosses itself, is
    repaired with shapely.make_valid(): the polygon is its largest piece with holes
    filled, or None if the contour has no area. At the end of each update, a single
    log message lists the cells without a contour or with an invalid one.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    contour_prop : str, optional
        Identifier of the node property holding the cell contours.
        Defaults to "cell_contour".
    force_recompute : bool, optional
        Whether to force recomputation of the property when it has already been
        computed, by default False.
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "contour_prop": ("node", "CellLineage")
    }

    def __init__(
        self,
        property: Property,
        contour_prop: str = "cell_contour",
        force_recompute: bool = False,
    ):
        super().__init__(property)
        self.contour_prop = contour_prop
        self.force_recompute = force_recompute
        # (cell ID, lineage ID) of the cells without a contour,
        # and of the cells whose contour is invalid.
        self._cells_without_contour: list[tuple[int, int]] = []
        self._cells_with_invalid_contour: list[tuple[int, int]] = []

    def enrich(
        self, data: Data, nodes_to_enrich: list[tuple[int, int]], **kwargs
    ) -> None:
        """
        Enrich the data with the cell polygons of a list of nodes.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        nodes_to_enrich : list of tuple[int, int]
            List of tuples containing the node ID and the lineage ID of the nodes
            to enrich with the property value.
        """
        self._cells_without_contour = []
        self._cells_with_invalid_contour = []
        super().enrich(data, nodes_to_enrich, **kwargs)
        issues = []
        consequences = []
        if self._cells_without_contour:
            issues.append(_describe_cells(self._cells_without_contour, "no value"))
            consequences.append(
                f"'{self.prop.identifier}' is None for cells without a value."
            )
        if self._cells_with_invalid_contour:
            issues.append(
                _describe_cells(self._cells_with_invalid_contour, "an invalid contour")
            )
            consequences.append(
                "Invalid contours, such as contours crossing themselves, are repaired "
                f"and '{self.prop.identifier}' keeps their largest piece (None if "
                "they have no area)."
            )
        if issues:
            logger.warning(
                f"In '{self.contour_prop}', {' and '.join(issues)}. "
                f"{' '.join(consequences)}"
            )

    def compute(self, lineage, nid: int) -> Polygon | None:
        if not self.force_recompute and self.prop.identifier in lineage.nodes[nid]:
            return lineage.nodes[nid][self.prop.identifier]

        cell = lineage.nodes[nid]
        contour = cell.get(self.contour_prop)
        if contour is None:
            self._cells_without_contour.append((nid, lineage.graph["lineage_ID"]))
            return None
        x, y = cell["cell_x"], cell["cell_y"]
        try:
            polygon = Polygon([(x + dx, y + dy) for dx, dy in contour])
        except ValueError:  # Too few points to make a polygon.
            polygon = None
        if polygon is not None and polygon.is_valid and not polygon.is_empty:
            return polygon
        self._cells_with_invalid_contour.append((nid, lineage.graph["lineage_ID"]))
        return _largest_polygon(make_valid(polygon)) if polygon is not None else None


def create_cell_area_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    custom_provenance: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cell_area",
        name=custom_name or "Cell area",
        description=custom_description or "Area of the cell",
        provenance=custom_provenance or "pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


class CellArea(NodeLocalPropCalculator):
    """
    Calculator to compute the area of a cell from its polygon.

    The area of a shapely.MultiPolygon is the area of all its pieces, holes excluded.
    The area is NaN for cells whose polygon is None, such as cells without a contour.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    polygon_prop : str, optional
        Identifier of the node property holding the cell shapes as
        shapely.Polygon or shapely.MultiPolygon. Defaults to "cell_polygon".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "polygon_prop": ("node", "CellLineage")
    }

    def __init__(self, property: Property, polygon_prop: str = "cell_polygon"):
        super().__init__(property)
        self.polygon_prop = polygon_prop

    def compute(self, lineage, nid: int) -> float:
        try:
            polygon = lineage.nodes[nid][self.polygon_prop]
        except KeyError:
            msg = (
                f"Cannot compute '{self.prop.identifier}': missing "
                f"'{self.polygon_prop}' property for cell {nid}, "
                f"lineage {lineage.graph['lineage_ID']}. "
                f"Please compute the '{self.polygon_prop}' property first."
            )
            raise KeyError(msg)
        return np.nan if polygon is None else polygon.area


def create_cycle_mean_area_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cycle_mean_area",
        name=custom_name or "Cycle mean area",
        description=custom_description or "Mean area of the cell during the cell cycle",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=unit,
    )


class CycleMeanArea(NodeGlobalPropCalculator):
    """
    Calculator to compute the mean area of a cell during a cell cycle.

    The cycle mean area is defined as the mean of the cell area values
    of all the cells of the cell cycle. NaN values are ignored.
    It is NaN when no cell of the cell cycle has an area value.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    area_prop : str, optional
        Identifier of the cell lineage node property holding the cell areas.
        Defaults to "cell_area".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "area_prop": ("node", "CellLineage")
    }

    def __init__(self, property: Property, area_prop: str = "cell_area"):
        super().__init__(property)
        self.area_prop = area_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CycleLineage, nid: int
    ) -> float:
        """
        Compute the mean area of a cell during the cell cycle.

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
            Mean area of the cell during the cell cycle, or NaN if no cell
            of the cell cycle has an area value.
        """
        areas = _get_cycle_node_property_values(self.area_prop, data, lineage, nid)
        return _nanmean(areas)


def create_birth_area_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "birth_area",
        name=custom_name or "Birth area",
        description=custom_description
        or "Area of the cell at the start of the cell cycle, right after division",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=unit,
    )


class BirthArea(NodeGlobalPropCalculator):
    """
    Calculator to compute the area of a cell at birth.

    The birth area is defined as the cell area value of the first cell
    of the cell cycle. It is NaN for cell cycles starting at a root,
    since their birth was not observed.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    area_prop : str, optional
        Identifier of the cell lineage node property holding the cell areas.
        Defaults to "cell_area".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "area_prop": ("node", "CellLineage")
    }

    def __init__(self, property: Property, area_prop: str = "cell_area"):
        super().__init__(property)
        self.area_prop = area_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CycleLineage, nid: int
    ) -> float:
        """
        Compute the area of a cell at birth.

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
            Area of the first cell of the cell cycle, or NaN if the cell cycle
            starts at a root.
        """
        if lineage.is_root(nid):
            return np.nan
        return _get_cycle_node_property_values(self.area_prop, data, lineage, nid)[0]


def create_division_area_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "division_area",
        name=custom_name or "Division area",
        description=custom_description
        or "Area of the cell at the end of the cell cycle, right before division",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=unit,
    )


class DivisionArea(NodeGlobalPropCalculator):
    """
    Calculator to compute the area of a cell at division.

    The division area is defined as the cell area value of the last cell
    of the cell cycle. It is NaN for cell cycles ending at a leaf,
    since their division was not observed.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    area_prop : str, optional
        Identifier of the cell lineage node property holding the cell areas.
        Defaults to "cell_area".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "area_prop": ("node", "CellLineage")
    }

    def __init__(self, property: Property, area_prop: str = "cell_area"):
        super().__init__(property)
        self.area_prop = area_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CycleLineage, nid: int
    ) -> float:
        """
        Compute the area of a cell at division.

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
            Area of the last cell of the cell cycle, or NaN if the cell cycle
            ends at a leaf.
        """
        if lineage.is_leaf(nid):
            return np.nan
        return _get_cycle_node_property_values(self.area_prop, data, lineage, nid)[-1]


def create_cell_contour_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    custom_provenance: str | None = None,
    unit: str | None = None,
):
    return Property(
        identifier=custom_identifier or "cell_contour",
        name=custom_name or "Cell contour",
        description=custom_description
        or "List of coordinates of the cell's contour, relative to its centroid",
        provenance=custom_provenance or "pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


class CellContour(NodeLocalPropCalculator):
    """
    Calculator to compute the contour of a cell from its polygon, as coordinates
    relative to the polygon centroid. The contour is None for cells whose polygon
    is None.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    force_recompute : bool, optional
        Whether to force recomputation of the property when it has already been
        computed, by default False.
    polygon_prop : str, optional
        Identifier of the node property holding the cell shapes as
        shapely.Polygon. Defaults to "cell_polygon".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "polygon_prop": ("node", "CellLineage")
    }

    def __init__(
        self,
        property: Property,
        force_recompute: bool = False,
        polygon_prop: str = "cell_polygon",
    ):
        super().__init__(property)
        self.force_recompute = force_recompute
        self.polygon_prop = polygon_prop

    def compute(self, lineage, nid: int) -> list[tuple[int, int]] | None:
        if not self.force_recompute and self.prop.identifier in lineage.nodes[nid]:
            return lineage.nodes[nid][self.prop.identifier]
        try:
            poly = lineage.nodes[nid][self.polygon_prop]
        except KeyError:
            msg = (
                f"Cannot compute '{self.prop.identifier}': missing "
                f"'{self.polygon_prop}' property for cell {nid}, "
                f"lineage {lineage.graph['lineage_ID']}. "
                f"Please compute the '{self.polygon_prop}' property first."
            )
            raise KeyError(msg)
        if poly is None:
            return None
        if not isinstance(poly, Polygon):
            raise TypeError(
                f"Cannot compute '{self.prop.identifier}' for cell {nid}, lineage "
                f"{lineage.graph['lineage_ID']}: '{self.polygon_prop}' holds a "
                f"{type(poly).__name__}, but a contour needs a Polygon."
            )
        return [
            (x - poly.centroid.x, y - poly.centroid.y) for (x, y) in poly.exterior.coords
        ]


def create_cell_perimeter_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    custom_provenance: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cell_perimeter",
        name=custom_name or "Cell perimeter",
        description=custom_description or "Perimeter of the cell",
        provenance=custom_provenance or "pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


class CellPerimeter(NodeLocalPropCalculator):
    """
    Calculator to compute the perimeter of a cell from its polygon.

    The perimeter of a shapely.MultiPolygon is the length of the boundaries of all
    its pieces, including the edges of their holes. The perimeter is NaN for cells
    whose polygon is None, such as cells without a contour.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    polygon_prop : str, optional
        Identifier of the node property holding the cell shapes as
        shapely.Polygon or shapely.MultiPolygon. Defaults to "cell_polygon".
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "polygon_prop": ("node", "CellLineage")
    }

    def __init__(self, property: Property, polygon_prop: str = "cell_polygon"):
        super().__init__(property)
        self.polygon_prop = polygon_prop

    def compute(self, lineage, nid: int) -> float:
        try:
            polygon = lineage.nodes[nid][self.polygon_prop]
        except KeyError:
            msg = (
                f"Cannot compute '{self.prop.identifier}': missing "
                f"'{self.polygon_prop}' property for cell {nid}, "
                f"lineage {lineage.graph['lineage_ID']}. "
                f"Please compute the '{self.polygon_prop}' property first."
            )
            raise KeyError(msg)
        return np.nan if polygon is None else polygon.length


# TODO on rod length and width:
# - remove debug code
# - always return a value even if weird skeleton shape (but put a warning in that case)
# - separate width and length. Width only requires skeleton length and the distance
# transform so I should compute the skeleton in a separate function.
# - recode every thing and avoid drawing
# - move area_increment to a notebook as an example of custom property


def from_roi_to_array(roi, width, height):
    # Actual drawing of the object and conversion to a numpy array.
    img = Image.new("L", (width, height), "black")
    img_draw = ImageDraw.Draw(img)
    img_draw.polygon(roi, fill="white")
    img = np.asarray(img, dtype=np.uint8)
    # We need a binary array to correctly compute the length.
    if not img.flags["WRITEABLE"]:
        img = img.copy()
    img[img > 0] = 1
    return img


def adjacent_pixels(img, pixel):
    i, j = pixel
    adj_px = []
    for k, l in product(range(i - 1, i + 2), range(j - 1, j + 2)):
        if k == i and l == j:
            continue
        # if k >= img.shape[1] or l >= img.shape[0]:

        try:
            if img[k, l] != 0:
                adj_px.append((k, l))
        except IndexError:
            # If current pixel is on the border of the image, there can't be
            # adjacency on the border side.
            continue
    return adj_px


def prune_skel(adjacency_dict):
    # We only want to keep the main skeleton which is the longest path
    # of the graph. To find it, we are looking for the longest shortest
    # path between 2 extremities of the graph. For this, we switch to
    # a graph representation of the skeleton to ease the path research.
    skel_graph = nx.from_dict_of_lists(adjacency_dict)
    longest_path = []
    tip_px = [px for px, list_px in adjacency_dict.items() if len(list_px) == 1]
    for n1, n2 in combinations(tip_px, 2):
        tmp_path = nx.shortest_path(skel_graph, n1, n2)
        if len(tmp_path) > len(longest_path):
            longest_path = tmp_path
    # Returning the adjacency_dict: now it contains only main skeleton pix.
    return nx.to_dict_of_lists(skel_graph, nodelist=longest_path)


def from_skel_to_path(adjacency_dict, first_px):
    # Ordering the skeleton pixels by following along the skeleton,
    # from one tip to another.
    path = [first_px]
    current_px = adjacency_dict[first_px][0]
    path.append(current_px)
    # print(current_px)
    while current_px in adjacency_dict:
        candidates = adjacency_dict[current_px]
        candidates.remove(path[-2])  # The pixel we're coming from.
        # print(candidates)
        if not candidates:  # There is no more pixel: we've reached a tip.
            break
        assert len(candidates) == 1
        current_px = candidates[0]
        path.append(current_px)
    return path


def from_path_to_line(path, tol):
    # Creation of a geometrical line out of the skeleton path.
    line = LineString([Point((x, y)) for (y, x) in path])
    # To get a better approximation of the object lenght, we simplify
    # the skeleton line.
    simplified_line = line.simplify(tol, preserve_topology=True)
    return simplified_line


def get_width_and_length(
    nid: int,
    lineage: CellLineage,
    pixel_size: float,
    skel_algo: str = "zhang",
    tolerance: float = 0.5,
    method_width: str = "mean",
    width_ignore_tips: bool = False,
    debug: bool = False,
    debug_folder: str | None = None,
) -> tuple[float, float]:
    """
    Compute the width and length of the ROI associated with a node.

    Parameters
    ----------
    nid : int
        Node ID (cell_ID) of the cell of interest.
    lineage : CellLineage
        Lineage graph containing the node of interest.
    pixel_size : float
        Pixel size in micrometer.
    skel_algo : str, optional
        'zhang' or 'lee', by default 'zhang'.
    tolerance : float, optional
        Tolerance distance for shape simplification (0-1).
        The higher the tolerance, the more simplified the line will be.
        By default 0.5.
    method_width : str, optional
        Method to compute width along skeleton: min, max, mean or median.
        By default mean.
    width_ignore_tips : bool, optional
        True to ignore the skeleton tips while computing width, by default False.
    debug : bool, optional
        True to activate debug behavior, by default False.
        Requires matplotlib, which pycellin does not install.
    debug_folder : Optional[str], optional
        Folder in which to save the debug graphs, by default None.

    Returns
    -------
    tuple[float, float]
        Width and length of the ROI.
    """
    if debug:
        print("NODE", nid)
        if skel_algo == "zhang":
            not_skel_algo = "lee"
        elif skel_algo == "lee":
            not_skel_algo = "zhang"

    # First we need to reconstruct the image of the object we are working on.
    # This is done by drawing and filling a polygon defined by the points
    # in the ROI list.
    roi = lineage.nodes[nid]["cell_contour"]
    # The coordinates extracted from the graph are in microns, not in pixels.
    # roi = [(int(x * x_resolution), int(y * x_resolution)) for (x, y) in roi]
    roi = [(int(x * 1 / pixel_size), int(y * 1 / pixel_size)) for (x, y) in roi]

    # Here, ROIs coordinates are given in relation to each ROI center,
    # not to the top left corner of the image.
    # But we don't care about the position of the pixels in the image,
    # we only care about their relative position to each other.
    # So we create an image just small enough to hold the object.
    x_min = min(roi, key=itemgetter(0))[0]
    x_max = max(roi, key=itemgetter(0))[0]
    y_min = min(roi, key=itemgetter(1))[1]
    y_max = max(roi, key=itemgetter(1))[1]
    # We add 4 pixels so that the object does not touch the border of
    # the image (otherwise it might create skeleton artefacts).
    img_width = x_max - x_min + 1 + 4
    img_height = y_max - y_min + 1 + 4
    # Placing the object in the center of the image.
    roi = [(x - x_min + 2, y - y_min + 2) for (x, y) in roi]
    img = from_roi_to_array(roi, img_width, img_height)

    if debug:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(nrows=2, ncols=3, sharex=True, sharey=True, dpi=400)
        ax[0, 0].imshow(img, cmap="gray")
        ax[0, 0].set_aspect("equal")
        ax[0, 0].axis("off")
        ax[0, 0].set_title(f"ROI node {nid}", fontsize=6)

    # Now that we have a numpy array modelling our object, we can compute
    # its distance transform and its skeleton.
    distance = ndi.distance_transform_edt(img)
    skel = skeletonize(img, method=skel_algo)
    # Distance transform but only for the pixels of the skeleton.
    dist_on_skel = distance * skel
    if debug:
        ax[0, 1].imshow(dist_on_skel, cmap="magma")
        ax[0, 1].contour(img, [0.5], colors="w")
        ax[0, 1].axis("off")
        ax[0, 1].set_title(f"Skeleton {skel_algo.capitalize()}", fontsize=6)

        skel2 = skeletonize(img, method=not_skel_algo)
        dist_on_skel2 = distance * skel2
        ax[1, 1].imshow(dist_on_skel2, cmap="magma")
        ax[1, 1].contour(img, [0.5], colors="w")
        ax[1, 1].axis("off")
        ax[1, 1].set_title(f"Skeleton {not_skel_algo.capitalize()}", fontsize=6)

    # The next step is to create a simple path out of the skeleton, then to
    # simplify the associated curve to compute an approximation of the
    # width and length of the object.
    # Building a pixel adjacency dictionary in which keys are the coordinates
    # of non zero pixels, and values are the coordinates of pixels adjacent
    # to the key pixel (using an 8-connectivity).
    adjacency_dict = {}
    pixels_i, pixels_j = np.nonzero(skel)
    pruning = False
    for i, j in zip(pixels_i, pixels_j):
        adj_px = adjacent_pixels(skel, (i, j))
        connectivity = len(adj_px)
        if connectivity > 2:
            # There is a side branching so we will need to prune it later
            # so as to only keep the main skeleton.
            pruning = True
        adjacency_dict[(i, j)] = adj_px

    if pruning:
        # We only want to keep the main skeleton which is the longest path
        # of the graph so we need to prune the side branches.
        if debug:
            print("PRUNING")
            print(adjacency_dict)
            # print(len(adjacency_dict))
        adjacency_dict = prune_skel(adjacency_dict)
        if debug:
            print(adjacency_dict)
            # print(len(adjacency_dict))

    # Tips of the skeleton = pixels connected to only 1 pixel.
    tip_px = [px for px, list_px in adjacency_dict.items() if len(list_px) == 1]
    if len(adjacency_dict) == 1:
        # There is only one pixel in the skeleton. The object being processed
        # is probably roundish. The method for mesuring length is not
        # adapted to this kind of morphology.
        try:
            track_ID = lineage.nodes[nid]["TRACK_ID"]
        except KeyError:
            print(
                f"WARNING: One pixel skeleton on node {nid}! "
                f"The object is probably roundish and the radius "
                f"is a better metric in that case. Setting the length and "
                f"width to NaN."
            )
        else:
            print(
                f"WARNING: One pixel skeleton on node {nid} of track "
                f"{track_ID}! The object is probably roundish and the radius"
                f" is a better metric in that case. Setting the length and "
                f"width to NaN."
            )
        length = np.nan
        width = np.nan
    elif len(adjacency_dict) == 0 or len(tip_px) == 0:
        # The skeleton is a loop!! The object being processed is
        # probably roundish. The method for mesuring length is not adapted to
        # this kind of morphology.
        try:
            track_ID = lineage.nodes[nid]["TRACK_ID"]
        except KeyError:
            print(
                f"WARNING: One pixel skeleton on node {nid}! "
                f"The object is probably roundish and the radius "
                f"is a better metric in that case. Setting the length and "
                f"width to NaN."
            )
        else:
            print(
                f"WARNING: Circular skeleton on node {nid} of track "
                f"{track_ID}! The object is probably roundish and the radius "
                f"is a better metric in that case. Setting the length and "
                f"width to NaN."
            )
        length = np.nan
        width = np.nan
    else:
        # Ordering the skeleton pixels by following along the skeleton,
        # from one tip to another.
        # The skeleton has been pruned so there should be only 2 tips.
        assert len(tip_px) == 2
        path = from_skel_to_path(adjacency_dict, tip_px[0])
        if debug:
            points = [Point((x, y)) for (y, x) in path]
            xs = [point.x for point in points]
            ys = [point.y for point in points]
            ax[0, 2].scatter(xs, ys, color="red", s=20)
            ax[0, 2].invert_yaxis()
            ax[0, 2].set_aspect("equal")
            ax[0, 2].axis("off")

        # Simplification of the path.
        line = from_path_to_line(path, tolerance)
        if debug:
            ax[0, 2].scatter(*line.xy, color="purple", marker="x", s=10)
            ax[0, 2].plot(*line.xy, color="purple")
            ax[0, 2].contour(img, [0.5], colors="b")
            ax[0, 2].set_title(
                f"Pruned skeleton {skel_algo.capitalize()}\n+ simplified line",
                fontsize=6,
            )

        length = line.length
        for px in tip_px:
            # We need to add the distance from each tip of the skeleton to the
            # object border, as given by the distance map.
            # print(dist_on_skel[px])
            length += dist_on_skel[px]

        if debug:
            # Doing the same steps as above but for the other skeleton algo.
            adjacency_dict2 = {}
            pixels_i2, pixels_j2 = np.nonzero(skel2)
            pruning2 = False
            for i, j in zip(pixels_i2, pixels_j2):
                adj_px2 = adjacent_pixels(skel2, (i, j))
                connectivity2 = len(adj_px2)
                if connectivity2 > 2:
                    pruning2 = True
                adjacency_dict2[(i, j)] = adj_px2
            if pruning2:
                adjacency_dict2 = prune_skel(adjacency_dict2)
            tip_px2 = [px for px, list_px in adjacency_dict2.items() if len(list_px) == 1]
            path2 = from_skel_to_path(adjacency_dict2, tip_px2[0])
            points2 = [Point((x, y)) for (y, x) in path2]
            xs = [point.x for point in points2]
            ys = [point.y for point in points2]
            ax[1, 2].scatter(xs, ys, color="red", s=20)
            ax[1, 2].invert_yaxis()
            ax[1, 2].set_aspect("equal")
            ax[1, 2].axis("off")
            line2 = from_path_to_line(path2, tolerance)
            ax[1, 2].scatter(*line2.xy, color="purple", marker="x", s=10)
            ax[1, 2].plot(*line2.xy, color="purple")
            ax[1, 2].contour(img, [0.5], colors="b")
            ax[1, 2].set_title(
                f"Pruned skeleton {not_skel_algo.capitalize()}\n+ simplified line",
                fontsize=6,
            )
            length2 = line2.length
            for px in tip_px2:
                length2 += dist_on_skel2[px]

        if width_ignore_tips:
            if len(dist_on_skel[dist_on_skel > 0]) >= 3:
                # We remove the tips of the skeleton only when there are
                # at least 3 pixels in the skeleton.
                for px in tip_px:
                    dist_on_skel[px] = 0
        # We are only interested in the distance map of the skeleton
        # so we discard the rest.
        dist_on_skel = dist_on_skel[dist_on_skel > 0]

        if method_width == "mean":
            # Width: averaging the distance transform along skeleton.
            width = (np.sum(dist_on_skel) / len(dist_on_skel)) * 2 - 1
        elif method_width == "median":
            # Width: median distance transform along skeleton.
            width = np.median(dist_on_skel) * 2 - 1
        elif method_width == "max":
            # Width: max distance transform along skeleton.
            # TODO: see how to deal with this case, maybe put it in the ignore_tips?
            if len(dist_on_skel) == 0:
                width = np.nan
            else:
                width = np.max(dist_on_skel) * 2 - 1
        elif method_width == "min":
            # Width: min distance transform along skeleton.
            if len(dist_on_skel) == 0:
                width = np.nan
            else:
                width = np.min(dist_on_skel) * 2 - 1
        else:
            print("Wrong width method. Should be one of: min, max, mean, median.")
            # TODO: raise an error when method is not supported

        if debug:
            print(f"Width: {width:.2f} px i.e. {width * pixel_size:.2f} μm.")
            print(f"Length: {length:.2f} px i.e. {length * pixel_size:.2f} μm.\n")

            txt = (
                f"Length: {length * pixel_size:.2f} μm\n{' ' * 10}i.e. {length:.2f} px"
                f"\nWidth: {width * pixel_size:.2f} μm\n{' ' * 10}i.e. {width:.2f} px"
            )
            ax[0, 2].annotate(
                txt,
                xy=(0, 0),
                xycoords="figure fraction",
                xytext=(1, 0.5),
                textcoords="axes fraction",
                size=4,
                horizontalalignment="left",
                verticalalignment="top",
            )

            width2 = (np.sum(dist_on_skel2) / len(pixels_i2)) * 2 - 1
            txt2 = (
                f"Length: {length2 * pixel_size:.2f} μm\n{' ' * 10}i.e. {length2:.2f} px"
                f"\nWidth: {width2 * pixel_size:.2f} μm\n{' ' * 10}i.e. {width2:.2f} px"
            )
            ax[1, 2].annotate(
                txt2,
                xy=(0, 0),
                xycoords="figure fraction",
                xytext=(1, 0.4),
                textcoords="axes fraction",
                size=4,
                horizontalalignment="left",
                verticalalignment="top",
            )

            ax[1, 0].remove()
            plt.show()
            lin_id = lineage.nodes[nid]["lineage_ID"]
            file = f"{debug_folder}/Lineage{lin_id}_Node{nid}_{skel_algo}"
            plt.savefig(file)
            plt.close()

    length *= pixel_size
    width *= pixel_size

    return width, length


def create_rod_width_property(
    custom_identifier: str | None,
    unit: str,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "rod_width",
        name=custom_name or "Rod width",
        description=custom_description or "Width of the cell, for rod-shaped cells only",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


class RodWidth(NodeLocalPropCalculator):
    def __init__(
        self,
        property,
        pixel_size: float,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
        debug: bool = False,
        debug_folder: str | None = None,
    ):
        super().__init__(property)
        self.pixel_size = pixel_size
        self.skel_algo = skel_algo
        self.tolerance = tolerance
        self.method_width = method_width
        self.width_ignore_tips = width_ignore_tips
        self.debug = debug
        self.debug_folder = debug_folder

    def compute(  # type: ignore[override]
        self, lineage: CellLineage, nid: int
    ) -> float:
        return get_width_and_length(
            nid,
            lineage,
            self.pixel_size,
            self.skel_algo,
            self.tolerance,
            self.method_width,
            self.width_ignore_tips,
            self.debug,
            self.debug_folder,
        )[0]


def create_rod_length_property(
    custom_identifier: str | None,
    unit: str,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "rod_length",
        name=custom_name or "Rod length",
        description=custom_description or "Length of the cell, for rod-shaped cells only",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


class RodLength(NodeLocalPropCalculator):
    def __init__(
        self,
        property,
        pixel_size: float,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
        debug: bool = False,
        debug_folder: str | None = None,
    ):
        super().__init__(property)
        self.pixel_size = pixel_size
        self.skel_algo = skel_algo
        self.tolerance = tolerance
        self.method_width = method_width
        self.width_ignore_tips = width_ignore_tips
        self.debug = debug
        self.debug_folder = debug_folder

    def compute(  # type: ignore[override]
        self, lineage: CellLineage, nid: int
    ) -> float:
        return get_width_and_length(
            nid,
            lineage,
            self.pixel_size,
            self.skel_algo,
            self.tolerance,
            self.method_width,
            self.width_ignore_tips,
            self.debug,
            self.debug_folder,
        )[1]


# TODO: this is a property that should not be in pycellin, too many ways to define
# the area increment. Since it is user dependent, I should put it in a notebook
# as an example of custom property.

# def get_area_increment(nid: int, lineage: CellLineage) -> float:
#     """
#     Compute the area increment of a node.

#     Parameters
#     ----------
#     nid : int
#         Node ID (cell_ID) of the cell of interest.
#     lineage : CellLineage
#         Lineage graph containing the node of interest.

#     Returns
#     -------
#     float
#         Area increment of the node.
#     """
#     # TODO: rework: name/definition is not intuitive.
#     # Why specifically between t and t-1? And not t and t+1?
#     # Should give 2 nodes as input and compute the area increment between them.
#     # Or add a parameter to specify if t-1 or t+1.
#     # Area of node at t minus area at t-1.
#     predecessors = list(lineage.predecessors(nid))
#     if len(predecessors) == 0:
#         return np.nan
#     else:
#         err_mes = (
#             f'Node {nid} in track {lineage.graph["name"]} has multiple predecessors.'
#         )
#         assert len(predecessors) == 1, err_mes
#         # print(predecessors)
#         return lineage.nodes[nid]["AREA"] - lineage.nodes[predecessors[0]]["AREA"]


# def _add_area_increment(lineages: list[CellLineage]) -> None:
#     """
#     Add the area increment property to the nodes of the lineages.

#     Parameters
#     ----------
#     lineages : list[CellLineage]
#         Cell lineages to update with the area increment property.
#     """
#     for lin in lineages:
#         for node in lin.nodes:
#             lin.nodes[node]["AREA_INCREMENT"] = get_area_increment(node, lin)


if __name__ == "__main__":
    import itertools
    import math

    from shapely.geometry import Polygon

    from pycellin.io.trackmate import load_TrackMate_XML

    xml = "sample_data/FakeTracks.xml"

    model = load_TrackMate_XML(xml, keep_all_spots=True, keep_all_tracks=True)
    lineage = model.data.cell_data[0]
    # print(lineage.nodes[2004]["cell_contour"])
    node = 2035
    print(lineage.nodes[node]["area"])

    # Shapely
    roi = Polygon(lineage.nodes[node]["cell_contour"])
    print(roi.area)

    # Shoelace formula
    vertices = lineage.nodes[node]["cell_contour"]
    border = vertices + [vertices[0]]
    area = sum([p1[0] * p2[1] - p1[1] * p2[0] for (p1, p2) in itertools.pairwise(border)])
    print(abs(area) / 2)

    # Perimeter shapely vs by hand
    print(roi.length)
    print(sum([math.dist(p1, p2) for (p1, p2) in itertools.pairwise(border)]))

    # print(lineage.nodes[node]["location"])
    # print(roi.centroid)
