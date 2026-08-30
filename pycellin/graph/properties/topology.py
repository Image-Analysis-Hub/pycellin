#!/usr/bin/env python3

"""Lineage topology property functions to create standard Property instances."""

from pycellin.classes.property import Property
from pycellin.classes.property_calculator import (
    LineageLocalPropCalculator,
    NodeLocalPropCalculator,
)


def create_is_division_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "is_division",
        name=custom_name or "Is division",
        description=custom_description
        or "Whether the cell is a division event, i.e. has more than one daughter cell",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="bool",
    )


class IsDivision(NodeLocalPropCalculator):
    """Calculator for the is_division property."""

    def compute(self, lineage, nid: int) -> bool:
        """
        Compute whether a given node is a division event.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cell_ID) of the cell of interest.

        Returns
        -------
        bool
            True if the cell is a division event, i.e. has more than one daughter cell,
            False otherwise.
        """
        return lineage.is_division(nid)  # type: ignore


def create_is_leaf_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "is_leaf",
        name=custom_name or "Is leaf",
        description=custom_description
        or "Whether the cell is a leaf cell, i.e. has no daughter cells",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="bool",
    )


class IsLeaf(NodeLocalPropCalculator):
    """Calculator for the is_leaf property."""

    def compute(self, lineage, nid: int) -> bool:
        """
        Compute whether a given node is a leaf cell.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cell_ID) of the cell of interest.

        Returns
        -------
        bool
            True if the cell is a leaf cell, i.e. has no daughter cells,
            False otherwise.
        """
        return lineage.is_leaf(nid)  # type: ignore


def create_is_root_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "is_root",
        name=custom_name or "Is root",
        description=custom_description
        or "Whether the cell is a root cell, i.e. has no parent cell",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="bool",
    )


class IsRoot(NodeLocalPropCalculator):
    """Calculator for the is_root property."""

    def compute(self, lineage, nid: int) -> bool:
        """
        Compute whether a given node is a root cell.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cell_ID) of the cell of interest.

        Returns
        -------
        bool
            True if the cell is a root cell, i.e. has no parent cell,
            False otherwise.
        """
        return lineage.is_root(nid)  # type: ignore


# TODO: should be named num_cells or lineage_length?
def create_num_cells_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "num_cells",
        name=custom_name or "Number of cells",
        description=custom_description or "Number of cells in the lineage",
        provenance="pycellin",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="int",
    )


class NumCells(LineageLocalPropCalculator):
    """Calculator for the num_cells property."""

    def compute(self, lineage) -> int:
        """
        Compute the number of cells in the lineage.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.

        Returns
        -------
        int
            The number of cells in the lineage.
        """
        return len(lineage)


# TODO: should be named num_cycles or lineage_length?
# TODO: turn into a Lineage prop instead of just CycleLineage
def create_num_cycles_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "num_cycles",
        name=custom_name or "Number of cell cycles",
        description=custom_description or "Number of cell cycles in the lineage",
        provenance="pycellin",
        prop_type="lineage",
        lin_type="CycleLineage",
        dtype="int",
    )


class NumCycles(LineageLocalPropCalculator):
    """Calculator for the num_cycles property."""

    def compute(self, lineage) -> int:
        """
        Compute the number of cell cycles in the lineage.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.

        Returns
        -------
        int
            The number of cell cycles in the lineage.
        """
        return len(lineage)


def create_num_divs_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "num_divs",
        name=custom_name or "Number of divisions",
        description=custom_description or "Number of cell divisions in the lineage",
        provenance="pycellin",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="int",
    )


class NumDivs(LineageLocalPropCalculator):
    """Calculator for the num_divs property."""

    def compute(self, lineage) -> int:
        """
        Compute the number of cell divisions in the lineage.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.

        Returns
        -------
        int
            The number of cell divisions in the lineage.
        """
        return len(lineage.get_divisions())


# TODO: turn into a cell+cycle prop
def create_num_gaps_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "num_gaps",
        name=custom_name or "Number of gaps",
        description=custom_description
        or "Number of gaps (missing detections) in the lineage",
        provenance="pycellin",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="int",
    )


class NumGaps(LineageLocalPropCalculator):
    """Calculator for the num_gaps property."""

    def compute(self, lineage) -> int:
        """
        Compute the number of gaps in the lineage.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.

        Returns
        -------
        int
            The number of gaps in the lineage.
        """
        return len(lineage.get_gaps())


def create_lineage_cell_depth_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "lineage_cell_depth",
        name=custom_name or "Lineage cell depth",
        description=custom_description
        or "Number of cells from the founding cell (root) to the most recent "
        "descendant (leaf)",
        provenance="pycellin",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="int",
    )


class LineageCellDepth(LineageLocalPropCalculator):
    """Calculator for the lineage_cell_depth property."""

    def compute(self, lineage) -> int:
        """
        Compute the number of cells from the root to the most recent leaf.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.

        Returns
        -------
        int
            The lineage depth given in number of cells.
        """
        return lineage.get_depth()


# TODO: turn into a Lineage prop instead of just CycleLineage
def create_lineage_cycle_depth_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "lineage_cycle_depth",
        name=custom_name or "Lineage cycle depth",
        description=custom_description
        or "Maximum number of cell cycles along any path from founding cell (root) to terminal cell (leaf)",
        provenance="pycellin",
        prop_type="lineage",
        lin_type="CycleLineage",
        dtype="int",
    )


class LineageCycleDepth(LineageLocalPropCalculator):
    """Calculator for the lineage_cell_depth property."""

    def compute(self, lineage) -> int:
        """
        Compute the maximum number of cell cycles along any path from root to leaf.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.

        Returns
        -------
        int
            The lineage depth given in number of cell cycles.
        """
        return lineage.get_depth()


def create_lineage_duration_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "lineage_duration",
        name=custom_name or "Lineage duration",
        description=custom_description
        or "Total lifespan of the lineage, from the founding cell (root) to the most "
        "recent descendant (leaf)",
        provenance="pycellin",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="float",
    )


class LineageDuration(LineageLocalPropCalculator):
    """Calculator for the lineage_duration property."""

    def __init__(self, property: Property, time_prop_name: str):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        time_prop_name : str
            The name of the time property (e.g. "frame", "time", etc.) to use
            for calculation.)
        """
        super().__init__(property)
        self.time_prop_name = time_prop_name

    def compute(self, lineage) -> float:
        """
        Compute the total lifespan of the lineage.

        Parameters
        ----------
        lineage : Lineage
            Lineage graph containing the node of interest.

        Returns
        -------
        float
            The total lifespan of the lineage.
        """
        return lineage.get_duration(time_prop=self.time_prop_name)
