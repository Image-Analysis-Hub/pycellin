#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import namedtuple
from enum import Flag, auto
from typing import Literal


LineageType = Literal["CellLineage", "CycleLineage", "Lineage"]


class PropertyType(Flag):
    """
    Flag enum for property types.

    Properties can have one or more types (NODE, EDGE, LINEAGE).
    Use bitwise OR to combine types: PropertyType.NODE | PropertyType.LINEAGE
    """

    NODE = auto()
    EDGE = auto()
    LINEAGE = auto()

    def __str__(self) -> str:
        """Return a string representation of the PropertyType."""
        result = property_type_to_strings(self)
        if isinstance(result, list):
            return " | ".join(result)
        return result


def property_type_from_string(value: str | list[str]) -> PropertyType:
    """
    Convert string or list of strings to PropertyType Flag.

    Parameters
    ----------
    value : str or list[str]
        Property type as string ("node", "edge", "lineage") or list of strings
        for multi-type properties (e.g., ["node", "lineage"]).

    Returns
    -------
    PropertyType
        The corresponding PropertyType Flag value.

    Raises
    ------
    KeyError
        If an invalid property type string is provided.

    Examples
    --------
    >>> property_type_from_string("node")
    <PropertyType.NODE: 1>
    >>> property_type_from_string(["node", "lineage"])
    <PropertyType.LINEAGE|NODE: 5>
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


def property_type_to_strings(value: PropertyType) -> str | list[str]:
    """
    Convert PropertyType Flag to string or list of strings.

    Returns a string for monotype properties and a list for multitype properties.
    This mirrors the input format accepted by property_type_from_string().

    Parameters
    ----------
    value : PropertyType
        The PropertyType Flag to convert.

    Returns
    -------
    str or list[str]
        String for single type (e.g., "node") or list for multiple types
        (e.g., ["node", "lineage"]).

    Examples
    --------
    >>> property_type_to_strings(PropertyType.NODE)
    'node'
    >>> property_type_to_strings(PropertyType.NODE | PropertyType.LINEAGE)
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
Cell = namedtuple("Cell", ["cell_ID", "lineage_ID"])
Link = namedtuple(
    "Link",
    ["source_cell_ID", "target_cell_ID", "lineage_ID"],
)
