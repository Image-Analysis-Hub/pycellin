#!/usr/bin/env python3

import numbers
import re
from collections.abc import Iterable
from typing import Any, Literal, get_args, get_origin

from plotly.colors import hex_to_rgb, unlabel_rgb


def _check_literal_type(value, literal_type) -> bool:
    if get_origin(literal_type) is Literal:
        return value in get_args(literal_type)
    raise TypeError(f"{literal_type} is not a Literal type")


def _check_integer(value: Any, name: str) -> None:
    """
    Check that a value is an integer.

    NumPy integers are accepted, since they are what the integers of a DataFrame are.
    Booleans are rejected, although bool is a subclass of int.

    Parameters
    ----------
    value : Any
        The value to check.
    name : str
        The name of the value, for the error message.

    Raises
    ------
    TypeError
        If the value is not an integer.
    """
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise TypeError(f"'{name}' must be an integer, not {type(value).__name__}.")


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


def _infer_dtype(values: Iterable[Any]) -> str | None:
    """
    Infer the data type of values, in Python type hint syntax.

    Booleans, integers (numpy integers included), real numbers and strings give "bool",
    "int", "float" and "str" respectively. Integers mixed with real numbers give
    "float". Values of other types give their class name, prefixed by their module
    unless built in (e.g. "dict", "numpy.ndarray"). Values of several types give a
    union of their data types (e.g. "int | str"). None values are ignored.

    Parameters
    ----------
    values : Iterable[Any]
        The values whose data type to infer.

    Returns
    -------
    str | None
        The inferred data type, or None if all values are None.
    """
    names = set()
    for value in values:
        if value is None:
            continue
        # bool is checked first since it is a subclass of int.
        if isinstance(value, bool):
            names.add("bool")
        elif isinstance(value, numbers.Integral):
            names.add("int")
        elif isinstance(value, numbers.Real):
            names.add("float")
        elif isinstance(value, str):
            names.add("str")
        else:
            cls = type(value)
            if cls.__module__ == "builtins":
                names.add(cls.__qualname__)
            else:
                names.add(f"{cls.__module__}.{cls.__qualname__}")
    if not names:
        return None
    if {"int", "float"} <= names:
        names.discard("int")
    return " | ".join(sorted(names))


def _unit_uses(unit: str, base_unit: str) -> bool:
    """
    Check if a unit is written with another unit, e.g. "micrometer/minute" with
    "minute".

    Units are compared word by word, a word being a run of letters: "min" is found in
    "1/min" but not in "minute", and "m" in "m^2" but not in "mm".

    Parameters
    ----------
    unit : str
        The unit to search, e.g. "micrometer/minute".
    base_unit : str
        The unit to look for, e.g. "minute".

    Returns
    -------
    bool
        True if the words of `base_unit` appear in `unit`, in a row.
    """

    def words(text: str) -> list[str]:
        return "".join(char if char.isalpha() else " " for char in text).split()

    unit_words, base_words = words(unit), words(base_unit)
    n = len(base_words)
    return n > 0 and any(
        unit_words[i : i + n] == base_words for i in range(len(unit_words) - n + 1)
    )
