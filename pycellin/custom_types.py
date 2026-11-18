#!/usr/bin/env python3

"""Types shared by Pycellin's modules: property and lineage types, cells and links."""

from enum import Flag, auto
from typing import Literal, NamedTuple

#: Lineages a property applies to: cell lineages, cycle lineages, or both.
LineageType = Literal["cell", "cycle", "both"]


class PropertyType(Flag):
    """
    Where the values of a property are stored: on nodes, edges or lineages.

    A property can have several types, combined with ``|``, for example
    ``PropertyType.NODE | PropertyType.LINEAGE``.
    """

    #: On nodes: cells in cell lineages, cell cycles in cycle lineages.
    NODE = auto()
    #: On edges: links between cells, or between cell cycles.
    EDGE = auto()
    #: On lineages, one value per lineage.
    LINEAGE = auto()

    def __str__(self) -> str:
        """
        Return a string representation of the PropertyType.

        Returns
        -------
        str
            The types, separated by ``" | "``, e.g. ``"node | lineage"``.
        """
        result = _property_type_to_strings(self)
        if isinstance(result, list):
            return " | ".join(result)
        return result


def _property_type_from_string(value: str | list[str]) -> PropertyType:
    """
    Convert string or list of strings to PropertyType Flag.

    Parameters
    ----------
    value : str | list[str]
        Property type as string (``"node"``, ``"edge"``, ``"lineage"``) or list of
        strings for multi-type properties (e.g., ``["node", "lineage"]``).

    Returns
    -------
    PropertyType
        The corresponding PropertyType Flag value.

    Raises
    ------
    KeyError
        If an invalid property type string is provided.
    ValueError
        If `value` is an empty list.
    TypeError
        If `value` is neither a string nor a list.

    Examples
    --------
    >>> _property_type_from_string("node")
    <PropertyType.NODE: 1>
    >>> _property_type_from_string(["node", "lineage"])
    <PropertyType.NODE|LINEAGE: 5>
    """
    mapping = {
        "node": PropertyType.NODE,
        "edge": PropertyType.EDGE,
        "lineage": PropertyType.LINEAGE,
    }

    if isinstance(value, str):
        return mapping[value]
    elif isinstance(value, list):
        if not value:
            raise ValueError("Property type list cannot be empty.")
        result = mapping[value[0]]
        for v in value[1:]:
            result |= mapping[v]
        return result
    else:
        raise TypeError(f"Expected str or list[str], got {type(value).__name__}")


def _property_type_to_strings(value: PropertyType) -> str | list[str]:
    """
    Convert PropertyType Flag to string or list of strings.

    Returns a string for monotype properties and a list for multitype properties.
    This mirrors the input format accepted by ``_property_type_from_string()``.

    Parameters
    ----------
    value : PropertyType
        The PropertyType Flag to convert.

    Returns
    -------
    str | list[str]
        String for single type (e.g., ``"node"``) or list for multiple types
        (e.g., ``["node", "lineage"]``).

    Examples
    --------
    >>> _property_type_to_strings(PropertyType.NODE)
    'node'
    >>> _property_type_to_strings(PropertyType.NODE | PropertyType.LINEAGE)
    ['node', 'lineage']
    """
    mapping = {
        PropertyType.NODE: "node",
        PropertyType.EDGE: "edge",
        PropertyType.LINEAGE: "lineage",
    }
    strings = [mapping[flag] for flag in PropertyType if flag in value]

    if len(strings) == 1:
        return strings[0]
    else:
        return strings


# TODO: should I force the user to use the Cell and Link named tuples?
# Would impact the signature of a lot of methods, but would make these
# signatures more structured and consistent (looking at you, add_cell()).
class Cell(NamedTuple):
    """
    A cell, identified by its ID and the ID of its lineage.

    Cell IDs can repeat across lineages, so both IDs are needed to identify a cell.

    Parameters
    ----------
    cell_id : int
        The ID of the cell.
    lineage_id : int
        The ID of the lineage of the cell.
    """

    #: The ID of the cell.
    cell_id: int
    #: The ID of the lineage of the cell.
    lineage_id: int


class Link(NamedTuple):
    """
    A link between two cells, identified by their IDs and the ID of their lineage.

    Parameters
    ----------
    source_cell_id : int
        The ID of the source cell of the link: the parent.
    target_cell_id : int
        The ID of the target cell of the link: the child.
    lineage_id : int
        The ID of the lineage of the two cells.
    """

    #: The ID of the source cell of the link: the parent.
    source_cell_id: int
    #: The ID of the target cell of the link: the child.
    target_cell_id: int
    #: The ID of the lineage of the two cells.
    lineage_id: int
