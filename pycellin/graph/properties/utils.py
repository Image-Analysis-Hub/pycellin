#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
from pathlib import Path
from typing import Dict, Optional


class PropertyExtractor(ast.NodeVisitor):
    """AST visitor to extract property information from create_xxxxx_property functions."""

    def __init__(self):
        self.properties = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """
        Visit function definitions looking for create_xxxxx_property pattern.

        Parameters
        ----------
        node : ast.FunctionDef
            The AST FunctionDef node representing the function definition.
        """
        if (
            node.name.startswith("create_") or node.name.startswith("_create_")
        ) and node.name.endswith("_property"):
            for stmt in node.body:
                if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
                    prop_info = self._extract_from_call(stmt.value)
                    if prop_info:
                        self.properties[node.name] = prop_info
        self.generic_visit(node)

    def _extract_from_call(self, call: ast.Call) -> Optional[Dict[str, str]]:
        """
        Extract property info from Property constructor call.

        Parameters
        ----------
        call : ast.Call
            The AST Call node representing the Property constructor.

        Returns
        -------
        Optional[Dict[str, str]]
            Dictionary with property information if found, else None.
        """
        is_property = isinstance(call.func, ast.Name) and call.func.id == "Property"
        if not is_property:
            return None

        info = {}
        for kw in call.keywords:
            fields = ["identifier", "description", "lin_type"]
            if kw.arg in fields:
                value = self._extract_value(kw.value)
                if value is not None:
                    info[kw.arg] = value

        return info if info else None

    def _extract_value(self, node: ast.AST) -> Optional[str]:
        """
        Extract string value from AST node, handling constants and BoolOp expressions.

        Parameters
        ----------
        node : ast.AST
            The AST node to extract the string value from.

        Returns
        -------
        Optional[str]
            The extracted string value, or None if not found.

        Notes
        -----
        This method cannot handle f-strings with variables (like f"cell_{axis}")
        since variable values are only known at runtime. Such properties will be
        skipped during discovery. To solve this issue, fake properties have been
        created for cell, link and lineage coordinates in core.py.
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
            # Handle "custom_identifier or 'default_value'" patterns
            # by returning the rightmost constant string value.
            for value in reversed(node.values):
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
        return None


def _discover_props_via_ast(include_core: bool) -> Dict[str, Dict[str, str]]:
    """
    Discover properties by parsing Python files with AST.

    Parameters
    ----------
    include_core : bool
        Whether to include core properties.

    Returns
    -------
    dict[str, dict[str, str]]
        Dictionary of all discovered properties with their information.
    """
    props_dir = Path(__file__).parent
    ignore = ["utils.py"] if include_core else ["utils.py", "core.py"]
    all_props = {}

    for py_file in props_dir.glob("*.py"):
        if py_file.name.startswith("__") or py_file.name in ignore:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            extractor = PropertyExtractor()
            extractor.visit(tree)
            all_props.update(extractor.properties)
        except (FileNotFoundError, OSError, SyntaxError, UnicodeDecodeError):
            continue

    return all_props


def _get_pycellin_props_by_lin_type(
    include_core: bool,
    lin_type_filter: list[str],
) -> dict[str, str]:
    """
    Return the pycellin properties that can be computed on a given lineage type.

    Parameters
    ----------
    include_core : bool
        Whether to include core properties.
    lin_type_filter : list[str]
        The lineage type to filter properties by ('Lineage', 'CellLineage', 'CycleLineage')

    Returns
    -------
    dict[str, str]
        Dictionary of properties of the specified lineage type,
        with properties name as keys and properties description as values.
    """
    all_properties = _discover_props_via_ast(include_core)
    filtered_props = {}

    for _, prop_info in all_properties.items():
        lin_type = prop_info.get("lin_type")
        if lin_type in lin_type_filter:
            identifier = prop_info.get("identifier")
            description = prop_info.get("description")
            if identifier and description:
                filtered_props[identifier] = description

    return filtered_props


def get_pycellin_cell_lineage_properties(
    include_core_properties: bool = True,
    include_Lineage_properties: bool = True,
) -> dict[str, str]:
    """
    Return the pycellin properties that can be computed on cell lineages.

    Automatically discovers properties by parsing create_xxxxx_property functions using AST.

    Parameters
    ----------
    include_core_properties : bool, optional
        Whether to include core properties, i.e. properties automatically computed by pycellin.
        True by default.
    include_Lineage_properties : bool, optional
        Whether to include Lineage properties. True by default.

    Returns
    -------
    dict[str, str]
        Dictionary of properties of the cell lineages,
        with properties name as keys and properties description as values.
    """
    lin_types = ["CellLineage", "Lineage"] if include_Lineage_properties else ["CellLineage"]
    props = _get_pycellin_props_by_lin_type(include_core_properties, lin_types)
    return props


def get_pycellin_cycle_lineage_properties(
    include_core_properties: bool = True,
    include_Lineage_properties: bool = True,
) -> dict[str, str]:
    """
    Return the pycellin properties that can be computed on cycle lineages.

    Automatically discovers properties by parsing create_xxxxx_property functions using AST.

    Parameters
    ----------
    include_core_properties : bool, optional
        Whether to include core properties, i.e. properties automatically computed by pycellin.
        True by default.
    include_Lineage_properties : bool, optional
        Whether to include Lineage properties. True by default.

    Returns
    -------
    dict[str, str]
        Dictionary of properties of the cycle lineages,
        with properties name as keys and properties description as values.
    """
    lin_types = ["CycleLineage", "Lineage"] if include_Lineage_properties else ["CycleLineage"]
    return _get_pycellin_props_by_lin_type(include_core_properties, lin_types)
