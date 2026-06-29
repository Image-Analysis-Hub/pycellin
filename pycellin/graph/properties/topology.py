#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Lineage topology property functions to create standard Property instances."""

from pycellin.classes.property import Property
from pycellin.classes.property_calculator import NodeLocalPropCalculator


def create_is_division_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "is_division",
        name=custom_name or "is division",
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
        name=custom_name or "is leaf",
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
        name=custom_name or "is root",
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
