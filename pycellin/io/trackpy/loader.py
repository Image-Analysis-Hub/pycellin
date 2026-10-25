#!/usr/bin/env python3

"""
loader.py

This module is part of the pycellin package.

This module provides functions to load and process trackpy data into pycellin models.
It includes a function to load a trackpy DataFrame into a pycellin model and helper
functions to build the lineage graphs and to create metadata and properties.

References:
- trackpy: D. B. Allan, T. Caswell, N. C. Keim, C. M. van der Wel and R. W. Verweij,
“soft-matter/trackpy: v0.6.4”. Zenodo, Jul. 10, 2024. doi: 10.5281/zenodo.12708864.
- trackpy GitHub: https://github.com/soft-matter/trackpy
"""

from itertools import pairwise
from typing import Any

import networkx as nx
import pandas as pd

from pycellin.classes import (
    Data,
    Model,
    Property,
    PropsMetadata,
)
from pycellin.io.utils import _split_graph_into_lineages
from pycellin.properties.core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_frame_property,
    create_lineage_id_property,
    create_time_property,
)
from pycellin.utils import _infer_dtype

# Columns written by trackpy: name, description, and whether the values are in the
# unit of the coordinates. With a diameter that differs between axes, trackpy writes
# a size and a static error per axis instead of 'size' and 'ep'.
_TRACKPY_COLUMNS: dict[str, tuple[str, str, bool]] = {
    "particle": (
        "Particle",
        "Identifier of the particle, given by trackpy linking",
        False,
    ),
    "mass": ("Mass", "Total integrated brightness of the particle", False),
    "size": (
        "Size",
        "Radius of gyration of the brightness profile of the particle",
        True,
    ),
    "ecc": ("Eccentricity", "Eccentricity of the particle, 0 when circular", False),
    "signal": (
        "Signal",
        "Maximum brightness of the particle in the preprocessed image",
        False,
    ),
    "raw_mass": (
        "Raw mass",
        "Total integrated brightness of the particle in the raw image",
        False,
    ),
    "ep": (
        "Static error",
        "Estimated uncertainty of the position of the particle",
        True,
    ),
    **{
        f"size_{axis}": (
            f"Size {axis}",
            (
                "Radius of gyration of the brightness profile of the particle "
                f"along {axis}"
            ),
            True,
        )
        for axis in ("x", "y", "z")
    },
    **{
        f"ep_{axis}": (
            f"Static error {axis}",
            f"Estimated uncertainty of the {axis} position of the particle",
            True,
        )
        for axis in ("x", "y", "z")
    },
}


def _add_nodes(graph: nx.DiGraph, df: pd.DataFrame) -> None:
    """
    Add nodes to the graph from the DataFrame.

    One node is created per row of the DataFrame. Its attributes are the row values,
    with their data type, 'frame' and 'particle' cast to int and the trackpy
    coordinates 'x', 'y' and 'z' renamed to 'cell_x', 'cell_y' and 'cell_z'. A
    'cell_id' equal to the position of the row in the DataFrame is added, and also
    used as node ID.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which nodes will be added.
    df : pd.DataFrame
        The DataFrame containing trackpy data.
    """
    # Unlike iterrows(), to_dict() keeps the integers of a row whose values are all
    # numbers, instead of turning them into floats.
    for i, row_dict in enumerate(df.to_dict("records")):
        row_dict["frame"] = int(row_dict["frame"])
        row_dict["particle"] = int(row_dict["particle"])
        for axis in ("x", "y", "z"):
            if axis in row_dict:
                row_dict[f"cell_{axis}"] = row_dict.pop(axis)
        row_dict["cell_id"] = i
        graph.add_node(i, **row_dict)


def _add_edges(graph: nx.DiGraph) -> None:
    """
    Add edges to the graph based on particle trajectories.

    The nodes of each particle are sorted by frame and each node is linked to the
    next one. Frames do not need to be consecutive, so trajectories with gaps are
    supported.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which edges will be added.
    """
    # Grouping the nodes by particle first keeps the linking time linear in the
    # number of nodes.
    trajectories: dict[int, list[tuple[int, int]]] = {}
    for node, attrs in graph.nodes(data=True):
        trajectories.setdefault(attrs["particle"], []).append((attrs["frame"], node))
    for trajectory in trajectories.values():
        trajectory.sort()
        for (_, n1), (_, n2) in pairwise(trajectory):
            graph.add_edge(n1, n2)


def _get_column_dtype(column: pd.Series) -> str:
    """
    Return the data type of a DataFrame column, in Python type hint syntax.

    Boolean, integer and float columns give "bool", "int" and "float". For other
    columns, the data type is inferred from the values, missing values ignored,
    e.g. "str". A column without any value gives its pandas data type, e.g.
    "object".

    Parameters
    ----------
    column : pd.Series
        The column whose data type to return.

    Returns
    -------
    str
        The data type of the column.
    """
    if pd.api.types.is_bool_dtype(column):
        return "bool"
    if pd.api.types.is_integer_dtype(column):
        return "int"
    if pd.api.types.is_float_dtype(column):
        return "float"
    return _infer_dtype(column.dropna().tolist()) or str(column.dtype)


def _create_metadata(
    space_unit: str | None = None,
    pixel_width: float | None = None,
    pixel_height: float | None = None,
    pixel_depth: float | None = None,
    time_unit: str | None = None,
    time_step: float | None = None,
) -> dict[str, Any]:
    """
    Create a dictionary of basic pycellin metadata for trackpy data.

    Parameters
    ----------
    space_unit : str, optional
        The spatial unit of the data. If not provided, it will be set to 'pixel'
        by default.
    pixel_width : float, optional
        The pixel width in the spatial unit. If not provided, it will be set to 1.0
        by default.
    pixel_height : float, optional
        The pixel height in the spatial unit. If not provided, it will be set to 1.0
        by default.
    pixel_depth : float, optional
        The pixel depth in the spatial unit. If not provided, it will be set to 1.0
        by default.
    time_unit : str, optional
        The temporal unit of the data. If not provided, it will be set to 'frame'
        by default.
    time_step : float, optional
        The time step in the temporal unit. If not provided, it will be set to 1.0
        by default.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the generated metadata.
    """
    metadata: dict[str, Any] = {}
    metadata["provenance"] = "trackpy"

    # Units.
    metadata["space_unit"] = space_unit if space_unit is not None else "pixel"
    metadata["pixel_width"] = pixel_width if pixel_width is not None else 1.0
    metadata["pixel_height"] = pixel_height if pixel_height is not None else 1.0
    metadata["pixel_depth"] = pixel_depth if pixel_depth is not None else 1.0
    metadata["time_unit"] = time_unit if time_unit is not None else "frame"
    metadata["time_step"] = time_step if time_step is not None else 1.0

    return metadata


def _create_PropsMetadata(
    dtypes: dict[str, str], metadata: dict[str, Any], time_prop: str
) -> PropsMetadata:
    """
    Return a PropsMetadata object populated with the needed properties.

    Every column of the trackpy DataFrame is declared. The coordinate columns
    ('x', 'y', 'z') are declared as 'cell_x', 'cell_y' and 'cell_z', and the
    other columns under their own name, with their data type. The columns written
    by trackpy get a name and a description, and the sizes and static errors the
    unit of the coordinates.

    Parameters
    ----------
    dtypes : dict[str, str]
        Data types of the columns of the trackpy DataFrame, by column name.
    metadata : dict[str, Any]
        Metadata dictionary containing information about the data, as created
        by `_create_metadata()`. Its 'space_unit' and 'time_unit' are used as
        property units.
    time_prop : str
        Identifier of the time property computed by the loader.

    Returns
    -------
    PropsMetadata
        An instance of PropsMetadata populated with pycellin and trackpy properties.
    """
    props_md = PropsMetadata()

    # Pycellin mandatory properties.
    cell_id_prop = create_cell_id_property()
    frame_prop = create_frame_property(provenance="trackpy")
    time_prop_md = create_time_property(
        unit=metadata["time_unit"], provenance="trackpy", custom_identifier=time_prop
    )
    lin_id_prop = create_lineage_id_property()
    for prop in [cell_id_prop, frame_prop, time_prop_md, lin_id_prop]:
        props_md._add_prop(prop)

    # Trackpy coordinates.
    for axis in ["x", "y", "z"]:
        if axis in dtypes:
            prop = create_cell_coord_property(
                unit=metadata["space_unit"], axis=axis, provenance="trackpy"
            )
            props_md._add_prop(prop)

    # Other columns, from trackpy or not.
    for column, dtype in dtypes.items():
        if column in ("frame", "x", "y", "z"):
            continue  # Already declared.
        name, description, is_length = _TRACKPY_COLUMNS.get(
            column, (column, "Column of the trackpy DataFrame", False)
        )
        prop = Property(
            identifier=column,
            name=name,
            description=description,
            provenance="trackpy",
            prop_type="node",
            lin_type="CellLineage",
            # The loader casts the particle IDs to int.
            dtype="int" if column == "particle" else dtype,
            unit=metadata["space_unit"] if is_length else None,
        )
        props_md._add_prop(prop)

    return props_md


def load_trackpy_dataframe(
    df: pd.DataFrame,
    space_unit: str | None = None,
    pixel_width: float | None = None,
    pixel_height: float | None = None,
    pixel_depth: float | None = None,
    time_unit: str | None = None,
    time_step: float | None = None,
    computed_time_prop: str = "time",
) -> Model:
    """
    Load a trackpy DataFrame into a pycellin model.

    The DataFrame must contain the 'frame' and 'particle' columns produced by
    trackpy linking. Each row becomes a cell, and the cells of a same particle
    are linked by ascending frame. Each connected component becomes a lineage.
    The DataFrame is not modified.

    Cell times are stored in two node properties: 'frame', read from the DataFrame,
    and a time property computed by the loader (named by `computed_time_prop`),
    equal to frame * time_step and expressed in time_unit. The computed time
    property is the reference time property of the model.

    The other columns of the DataFrame become cell properties too, declared with
    the data type of the column. The columns written by trackpy ('mass', 'size',
    'ecc', 'signal', 'raw_mass', 'ep'...) get a description, and the sizes and
    static errors the unit of the coordinates.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing trackpy data.
    space_unit : str, optional
        The spatial unit of the data. If not provided, it will be set to 'pixel'
        by default.
    pixel_width : float, optional
        The pixel width in the spatial unit. If not provided, it will be set to 1.0
        by default.
    pixel_height : float, optional
        The pixel height in the spatial unit. If not provided, it will be set to 1.0
        by default.
    pixel_depth : float, optional
        The pixel depth in the spatial unit. If not provided, it will be set to 1.0
        by default.
    time_unit : str, optional
        The temporal unit of the data. If not provided, it will be set to 'frame'
        by default.
    time_step : float, optional
        The time between two consecutive frames, in the temporal unit. If not
        provided, it will be set to 1.0 by default.
    computed_time_prop : str, optional
        Identifier of the time property built by the loader from the 'frame'
        column. Defaults to "time". It must not be the name of a column of `df`.

    Returns
    -------
    Model
        A pycellin model populated with the trackpy data.

    Raises
    ------
    ValueError
        If `df` has both a trackpy coordinate column and its pycellin counterpart
        (e.g. 'x' and 'cell_x'), if it has a 'cell_id', 'lineage_id' or
        'timepoint' column, which pycellin creates, or if `computed_time_prop` is
        already a column of `df` or is a property written by pycellin ('cell_id',
        'lineage_id', 'timepoint' or a renamed coordinate).
    """
    coord_props = {f"cell_{axis}" for axis in ("x", "y", "z") if axis in df.columns}
    conflicting_columns = sorted(coord_props & set(df.columns))
    if conflicting_columns:
        raise ValueError(
            f"Cannot rename the trackpy coordinates: the DataFrame already has the "
            f"column(s) {conflicting_columns}. Rename or drop them before loading."
        )
    pycellin_props = {"cell_id", "lineage_id", "timepoint"}
    conflicting_columns = sorted(pycellin_props & set(df.columns))
    if conflicting_columns:
        raise ValueError(
            f"The DataFrame has the column(s) {conflicting_columns}, but pycellin "
            "creates its own properties with these names. Rename or drop them "
            "before loading."
        )
    reserved_props = pycellin_props | coord_props
    if computed_time_prop in df.columns or computed_time_prop in reserved_props:
        raise ValueError(
            f"Cannot build the time property '{computed_time_prop}': a column or "
            f"a pycellin property with this name already exists. Use the "
            f"'computed_time_prop' argument to choose another name."
        )

    # Build the lineages.
    graph = nx.DiGraph()
    _add_nodes(graph, df)
    dtypes = {column: _get_column_dtype(df[column]) for column in df.columns}
    del df  # Free memory.
    _add_edges(graph)

    md = _create_metadata(
        space_unit, pixel_width, pixel_height, pixel_depth, time_unit, time_step
    )
    # The reference time property is the physical time, so that the time step and
    # time unit apply to it. Timepoints are then derived from it by the model.
    for _, node_data in graph.nodes(data=True):
        node_data[computed_time_prop] = float(node_data["frame"] * md["time_step"])

    # Split the graph into lineages.
    lineages = _split_graph_into_lineages(graph)
    del graph  # Redundant with the subgraphs.
    data = {lin.graph["lineage_id"]: lin for lin in lineages if len(lin) > 0}

    # Create a pycellin model.
    props_md = _create_PropsMetadata(dtypes, md, computed_time_prop)
    model = Model(md, props_md, Data(data), computed_time_prop)

    return model


if __name__ == "__main__":
    """
    Quick demo with sample data.
    """
    from pathlib import Path

    trackpy_file = (
        Path(__file__).resolve().parents[3] / "sample_data" / "FakeTracks_trackpy.pkl"
    )
    df = pd.read_pickle(trackpy_file)
    print(df.shape)
    print(df.head(), "\n")

    model = load_trackpy_dataframe(df)
    print(model)
    print("\nModel metadata:")
    print(model.model_metadata)
    print("\nProperties and their types:")
    for prop_id, prop in model.props_metadata.props.items():
        print(f"  - {prop_id}  -> {prop.prop_type}")
