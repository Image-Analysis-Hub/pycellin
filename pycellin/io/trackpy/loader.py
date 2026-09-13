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
    PropsMetadata,
)
from pycellin.graph.properties.core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_frame_property,
    create_lineage_id_property,
    create_time_property,
)
from pycellin.io.utils import _split_graph_into_lineages


def _add_nodes(graph: nx.DiGraph, df: pd.DataFrame) -> None:
    """
    Add nodes to the graph from the DataFrame.

    One node is created per row of the DataFrame. Its attributes are the row values,
    with 'frame' and 'particle' cast to int and the trackpy coordinates 'x', 'y'
    and 'z' renamed to 'cell_x', 'cell_y' and 'cell_z'. A 'cell_ID' equal to the
    position of the row in the DataFrame is added, and also used as node ID.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which nodes will be added.
    df : pd.DataFrame
        The DataFrame containing trackpy data.
    """
    for i, (_, row) in enumerate(df.iterrows()):
        row_dict = row.to_dict()
        row_dict["frame"] = int(row_dict["frame"])
        row_dict["particle"] = int(row_dict["particle"])
        for axis in ("x", "y", "z"):
            if axis in row_dict:
                row_dict[f"cell_{axis}"] = row_dict.pop(axis)
        graph.add_node(i, **row_dict)
        graph.nodes[i]["cell_ID"] = i


def _add_edges(graph: nx.DiGraph, particles: list) -> None:
    """
    Add edges to the graph based on particle trajectories.

    For each particle, its nodes are sorted by frame and each node is linked
    to the next one. Frames do not need to be consecutive, so trajectories
    with gaps are supported.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which edges will be added.
    particles : list
        List of unique particle identifiers.
    """
    for particle in particles:
        # We need to link cells that have the same 'particle' value and are in frames
        # that follows each other. Since there can be gaps in trackpy trajectories,
        # we can't rely on the fact that frames will be truly consecutive.
        candidates = [
            (node, frame)
            for node, frame in graph.nodes(data="frame")
            if graph.nodes[node]["particle"] == particle
        ]
        candidates.sort(key=lambda x: x[1])
        for (n1, _), (n2, _) in pairwise(candidates):
            graph.add_edge(n1, n2)


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
    props: list[str], metadata: dict[str, Any], time_prop: str
) -> PropsMetadata:
    """
    Return a PropsMetadata object populated with the needed properties.

    Parameters
    ----------
    props : list[str]
        Column names of the trackpy DataFrame, used to detect the coordinate
        columns ('x', 'y', 'z').
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
    cell_ID_prop = create_cell_id_property()
    frame_prop = create_frame_property(provenance="trackpy")
    time_prop_md = create_time_property(
        unit=metadata["time_unit"], provenance="trackpy", custom_identifier=time_prop
    )
    lin_ID_prop = create_lineage_id_property()
    for prop in [cell_ID_prop, frame_prop, time_prop_md, lin_ID_prop]:
        props_md._add_prop(prop)

    # Trackpy properties.
    for axis in ["x", "y", "z"]:
        if axis in props:
            prop = create_cell_coord_property(
                unit=metadata["space_unit"], axis=axis, provenance="trackpy"
            )
            props_md._add_prop(prop)
    # TODO: add props for other trackpy properties

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
        (e.g. 'x' and 'cell_x'), or if `computed_time_prop` is already a column
        of `df` or is a property written by pycellin ('cell_ID', 'lineage_ID',
        'timepoint' or a renamed coordinate).
    """
    coord_props = {f"cell_{axis}" for axis in ("x", "y", "z") if axis in df.columns}
    conflicting_columns = sorted(coord_props & set(df.columns))
    if conflicting_columns:
        raise ValueError(
            f"Cannot rename the trackpy coordinates: the DataFrame already has the "
            f"column(s) {conflicting_columns}. Rename or drop them before loading."
        )
    reserved_props = {"cell_ID", "lineage_ID", "timepoint"} | coord_props
    if computed_time_prop in df.columns or computed_time_prop in reserved_props:
        raise ValueError(
            f"Cannot build the time property '{computed_time_prop}': a column or "
            f"a pycellin property with this name already exists. Use the "
            f"`computed_time_prop` argument to choose another name."
        )

    # Build the lineages.
    graph = nx.DiGraph()
    _add_nodes(graph, df)
    props = df.columns.to_list()
    particles = df["particle"].unique()
    del df  # Free memory.
    _add_edges(graph, particles)

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
    data = {lin.graph["lineage_ID"]: lin for lin in lineages if len(lin) > 0}

    # Create a pycellin model.
    props_md = _create_PropsMetadata(props, md, computed_time_prop)
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
