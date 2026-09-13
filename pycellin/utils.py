#!/usr/bin/env python3

import importlib.metadata
import re
from typing import Literal, get_args, get_origin

import networkx as nx
import networkx.algorithms.isomorphism as iso
from plotly.colors import hex_to_rgb, unlabel_rgb


def check_literal_type(value, literal_type) -> bool:
    if get_origin(literal_type) is Literal:
        return value in get_args(literal_type)
    raise TypeError(f"{literal_type} is not a Literal type")


# TODO: this function should move into a tests/utils.py file
def is_equal(obt: nx.DiGraph, exp: nx.DiGraph) -> bool:
    """Check if two graphs are perfectly identical.

    It checks that the graphs are isomorphic, and that their graph,
    nodes and edges attributes are all identical.

    Parameters
    ----------
    obt : nx.DiGraph
        The obtained graph, built from XML_reader.py.
    exp : nx.DiGraph
        The expected graph, built from here.

    Returns
    -------
    bool : True if the graphs are identical, False otherwise.
    """
    edges_attr = list(set([k for (n1, n2, d) in exp.edges.data() for k in d]))
    edges_default = len(edges_attr) * [0]
    em = iso.categorical_edge_match(edges_attr, edges_default)
    nodes_attr = list(set([k for (n, d) in exp.nodes.data() for k in d]))
    nodes_default = len(nodes_attr) * [0]
    nm = iso.categorical_node_match(nodes_attr, nodes_default)

    if not obt.nodes.data() and not exp.nodes.data():
        same_nodes = True
    elif len(obt.nodes.data()) != len(exp.nodes.data()):
        same_nodes = False
    else:
        for data1, data2 in zip(sorted(obt.nodes.data()), sorted(exp.nodes.data())):
            n1, attr1 = data1
            n2, attr2 = data2
            if sorted(attr1) == sorted(attr2) and n1 == n2:
                same_nodes = True
            else:
                same_nodes = False

    if not obt.edges.data() and not exp.edges.data():
        same_edges = True
    elif len(obt.edges.data()) != len(exp.edges.data()):
        same_edges = False
    else:
        for data1, data2 in zip(sorted(obt.edges.data()), sorted(exp.edges.data())):
            n11, n12, attr1 = data1
            n21, n22, attr2 = data2
            if sorted(attr1) == sorted(attr2) and sorted((n11, n12)) == sorted(
                (n21, n22)
            ):
                same_edges = True
            else:
                same_edges = False

    if (
        nx.is_isomorphic(obt, exp, edge_match=em, node_match=nm)
        and obt.graph == exp.graph
        and same_nodes
        and same_edges
    ):
        return True
    else:
        return False


def get_pycellin_version() -> str:
    """Get pycellin version from package metadata"""
    try:
        return importlib.metadata.version("pycellin")
    except importlib.metadata.PackageNotFoundError:
        return "development"


def _color_to_rgba(color: str, alpha: float) -> str:
    """
    Convert an 'rgb(r,g,b)' or '#rrggbb' color to an 'rgba(r,g,b,a)' string.
    """
    if not 0.0 <= alpha <= 1.0:
        raise ValueError(f"Argument 'alpha' must be in [0, 1], got {alpha}.")
    if color.startswith("#"):
        r, g, b = hex_to_rgb(color)
    elif color.startswith("rgb("):
        r, g, b = (int(round(c)) for c in unlabel_rgb(color))
    else:
        raise ValueError(
            f"Unsupported color format: {color!r}. Expected 'rgb(r,g,b)' or '#rrggbb'."
        )
    return f"rgba({r},{g},{b},{alpha})"


# Spellings of the data types of properties, grouped by canonical pycellin data type.
# Loaders and libraries spell them differently (e.g. GEFF uses numpy names).
_DTYPE_SPELLINGS = {
    "int": (
        "int",
        "integer",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
    ),
    "float": ("float", "double", "float16", "float32", "float64", "float128"),
    "string": ("string", "str"),
    "bool": ("bool", "bool_", "boolean"),
}
_DTYPE_ALIASES = {
    spelling: canonical
    for canonical, spellings in _DTYPE_SPELLINGS.items()
    for spelling in spellings
}


def _normalize_dtype(dtype: str | None) -> str | None:
    """
    Return the canonical spelling of a property data type.

    Spellings of integers, floats, strings and booleans (e.g. "int64", "float32",
    "str", "bool_") are mapped, case-insensitively, to "int", "float", "string" and
    "bool". Other data types, such as containers or class names, are returned
    unchanged since they cannot be normalized reliably.

    Parameters
    ----------
    dtype : str | None
        The data type to normalize.

    Returns
    -------
    str | None
        The canonical data type, or the input unchanged if its spelling is unknown.
    """
    if not isinstance(dtype, str):
        return dtype
    return _DTYPE_ALIASES.get(dtype.lower(), dtype)


def _is_numeric_dtype(dtype: str | None) -> bool:
    """
    Check if a dtype string represents a numeric type.

    Parameters
    ----------
    dtype : str | None
        The dtype string to check.

    Returns
    -------
    bool
        True if the dtype represents a numeric type, False otherwise.
    """
    if dtype is None:
        return False

    dtype_lower = dtype.lower()

    # Reject collection and container types that are not numeric.
    non_numeric_keywords = [
        "array",
        "bytes",
        "dict",
        "dictionary",
        "iterable",
        "list",
        "matrix",
        "object",
        "sequence",
        "set",
        "str",
        "string",
        "tuple",
    ]
    if any(keyword in dtype_lower for keyword in non_numeric_keywords):
        return False

    # Check for numeric types using regex with word boundaries
    # to avoid false positives (e.g., "point" containing "int").
    numeric_pattern = (
        r"\b(?:"
        r"int|integer|"
        r"uint|uint8|uint16|uint32|uint64|"
        r"int8|int16|int32|int64|"
        r"float|double|float16|float32|float64|float128|"
        r"complex|"
        r"bool|bool_|boolean|"
        r"fraction|decimal|"
        r"number|numeric|"
        r"real|rational"
        r")\b"
    )
    return bool(re.search(numeric_pattern, dtype_lower))
