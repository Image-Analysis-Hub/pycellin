#!/usr/bin/env python3

"""
loader.py

References:
- geff GitHub: https://github.com/live-image-tracking-tools/geff
- geff Documentation: https://live-image-tracking-tools.github.io/geff/latest/
"""

from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from tkinter import N
from typing import Any

import geff
import networkx as nx

from pycellin.classes import Data, Property, PropsMetadata, Model
from pycellin.custom_types import PropertyType
from pycellin.io.utils import (
    _split_graph_into_lineages,
    _update_lineages_IDs_key,
    _update_node_prop_key,
    check_fusions,
)


def _recursive_dict_search(data: dict[str, Any], target_key: str) -> dict[str, Any] | None:
    """
    Recursively search for a target key in a nested dictionary structure.

    Parameters
    ----------
    data : dict
        The dictionary to search through.
    target_key : str
        The key to search for.

    Returns
    -------
    dict[str, Any] | None
        The dict associated with the target key if found, None otherwise.
    """
    if not isinstance(data, dict):
        return None
    if target_key in data:  # does the current level contain the target key?
        return data[target_key]
    for value in data.values():  # recursive search in nested dictionaries
        if isinstance(value, dict):
            result = _recursive_dict_search(value, target_key)
            if result is not None:
                return result
    return None


def _extract_props_metadata(
    md: dict[str, geff.metadata_schema.PropMetadata],
    props_dict: dict[str, Property],
    prop_type: PropertyType,
) -> None:
    for key, prop in md.items():
        if key not in props_dict:
            props_dict[key] = Property(
                identifier=key,
                name=prop.name or key,
                description=prop.description or prop.name or key,
                provenance="geff",
                prop_type=prop_type,
                lin_type="CellLineage",
                dtype=prop.dtype,
                unit=prop.unit or None,
            )
        else:
            if props_dict[key].prop_type != prop_type:
                # The key must be unique but it already exists for nodes or edges,
                # so it needs to be renamed.
                if prop_type == "node":
                    current_prefix = "cell"
                    other_prefix = "link"
                elif prop_type == "edge":
                    current_prefix = "link"
                    other_prefix = "cell"
                else:
                    raise ValueError(
                        f"Unsupported property type: {prop_type}. Expected 'node' or 'edge'."
                    )
                # Rename the new property to be added.
                new_key = f"{current_prefix}_{key}"
                props_dict[new_key] = Property(
                    identifier=new_key,
                    name=prop.name or key,
                    description=prop.description or prop.name or key,
                    provenance="geff",
                    prop_type=prop_type,
                    lin_type="CellLineage",
                    dtype=prop.dtype,
                    unit=prop.unit or None,
                )
                # Rename the other property as well for clarity.
                other_key = f"{other_prefix}_{key}"
                other_prop = props_dict.pop(key)
                other_prop.identifier = other_key
                props_dict[other_key] = other_prop
            else:
                # GEFF ensure uniqueness of property keys for nodes and edges separately,
                # so this should never happen.
                raise KeyError(
                    f"Property '{key}' already exists in props_dict for {prop_type}s. "
                    "Please ensure unique property identifiers."
                )


def _extract_lin_props_metadata(
    md: dict[str, Any],
    props_dict: dict[str, Property],
) -> None:
    for key, prop in md.items():
        if key not in props_dict:
            props_dict[key] = Property(
                identifier=key,
                name=prop.get("name") or key,
                description=prop.get("description") or prop.get("name") or key,
                provenance="geff",
                prop_type="lineage",
                lin_type="CellLineage",
                dtype=prop.get("dtype"),
                unit=prop.get("unit") or None,
            )
        else:
            if props_dict[key].prop_type != "lineage":
                # The key must be unique but it already exists for nodes or edges,
                # so it needs to be renamed.
                new_key = f"lin_{key}"
                props_dict[new_key] = Property(
                    identifier=new_key,
                    name=prop.name or key,
                    description=prop.description or prop.get("name") or key,
                    provenance="geff",
                    prop_type="lineage",
                    lin_type="CellLineage",
                    dtype=prop.dtype,
                    unit=prop.unit or None,
                )
            else:
                raise KeyError(
                    f"Property '{key}' already exists in props_dict for lineages. "
                    "Please ensure unique property identifiers."
                )


def _read_props_metadata(geff_md: geff.metadata_schema.GeffMetadata) -> dict[str, Property]:
    """
    Read and extract properties metadata from geff metadata.

    Parameters
    ----------
    geff_md : geff.metadata_schema.GeffMetadata
        The geff metadata object containing properties metadata.

    Returns
    -------
    dict[str, Property]
        Dictionary mapping property identifiers to Property objects.
    """
    props_dict: dict[str, Property] = {}
    if geff_md.node_props_metadata is not None:
        _extract_props_metadata(geff_md.node_props_metadata, props_dict, "node")
    if geff_md.edge_props_metadata is not None:
        _extract_props_metadata(geff_md.edge_props_metadata, props_dict, "edge")

    # TODO: for now lineage properties are not associated to a specific tag but stored
    # somewhere in the "extra" field. We need to check recurrently if there is a dict
    # key called "lineage_props_metadata" in the "extra" field.
    if geff_md.extra is not None:
        # Recursive search for the "lineage_props_metadata" key through the "extra"
        # field dict of dicts of dicts...
        lin_props_metadata = _recursive_dict_search(geff_md.extra, "lineage_props_metadata")
        if lin_props_metadata is not None:
            _extract_lin_props_metadata(lin_props_metadata, props_dict)

    return props_dict


def load_geff_file(
    geff_file: Path | str,
    cell_id_key: str | None = None,
) -> Model:
    """
    Load a geff file and return a pycellin model containing the data.

    Parameters
    ----------
    geff_file : Path | str
        Path to the geff file to load.
    cell_id_key : str | None, optional
        The key used to identify cells in the geff file. If None, the default
        key 'cell_ID' will be created and populated based on the node IDs.

    Returns
    -------
    Model
        A pycellin model containing the data from the geff file.
    """
    pass

    # Read the geff file
    geff_graph, geff_md = geff.read_nx(geff_file, validate=True)
    for node in geff_graph.nodes:
        print(f"Node {node}: {geff_graph.nodes[node]}")
        break

    print(type(geff_graph))
    print(geff_md.directed)
    if geff_md.track_node_props is not None and "lineage" in geff_md.track_node_props:
        lin_id_key = geff_md.track_node_props["lineage"]
    else:
        lin_id_key = None
    print("lin_id_key:", lin_id_key)

    # Determine axes
    # If no axes, need to have them as arguments...? Set a default to x, y, z, t...?
    print("Axes:", geff_md.axes)
    # display_hints=DisplayHint(
    #         display_horizontal="POSITION_X",
    #         display_vertical="POSITION_Y",
    #         display_depth="POSITION_Z",
    #         display_time="POSITION_T",
    #     ),

    # Is int ID ensured in geff? YES
    # int_graph = nx.relabel_nodes(geff_graph, {node: int(node) for node in geff_graph.nodes()})

    # Extract and dispatch metadata
    # Generic metadata
    metadata = {}  # type: dict[str, Any]

    # Property metadata
    props_dict = _read_props_metadata(geff_md)

    # Split the graph into lineages
    lineages = _split_graph_into_lineages(geff_graph, lineage_ID_key=lin_id_key)
    print(f"Number of lineages: {len(lineages)}")

    # Rename properties to match pycellin conventions
    _update_lineages_IDs_key(lineages, lin_id_key)
    for lin in lineages:
        if cell_id_key is None:
            for node in lin.nodes:
                lin.nodes[node]["cell_ID"] = node
        else:
            _update_node_prop_key(lin, old_key=cell_id_key, new_key="cell_ID")
    # TODO: cells positions and edges positions (keys from axes)
    # Time?

    # All the stuff in field extra is stored in the model meta

    # Check for fusions
    data = Data({lin.graph["lineage_ID"]: lin for lin in lineages})
    model = Model(data=data, props_metadata=PropsMetadata(props=props_dict))
    # print(model.data)
    # print(model.data.cell_data)
    check_fusions(model)  # pycellin DOES NOT support fusion events

    return model


if __name__ == "__main__":
    geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/reader_test_graph.geff"
    # geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/mouse-20250719.zarr/tracks"
    # geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/test_pycellin_geff/test.zarr"
    geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/test_trackmate_to_geff/FakeTracks.geff"
    geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/test_trackmate_to_geff/FakeTracks.geff"

    print(geff_file)
    model = load_geff_file(geff_file)
    # print(model)
    # print("props_dict", model.props_metadata.props)
    # lineages = model.get_cell_lineages()
    # print(f"Number of lineages: {len(lineages)}")
    # for lin in lineages:
    #     print(lin)
    # lin0 = lineages[0]
    # print(lin0.nodes(data=True))
    # lin0.plot()

    # cell_id_key
    # lineage_id_key
    # time_key
    # cell_x_key
    # cell_y_key
    # cell_z_key

    # geff_graph, geff_md = geff.read_nx(geff_file, validate=True)
    # print(geff_graph)
    # # Check how many weakly connected components there are.
    # print(
    #     f"Number of weakly connected components: {len(list(nx.weakly_connected_components(geff_graph)))}"
    # )
    # for k, v in geff_graph.graph.items():
    #     print(f"{k}: {v}")
    # # print(graph.graph["axes"][0].unit)

    # if geff_md.directed:
    #     print("The graph is directed.")

    # metadata = {}  # type: dict[str, Any]
    # metadata["name"] = Path(geff_file).stem
    # metadata["file_location"] = geff_file
    # metadata["provenance"] = "geff"
    # metadata["date"] = str(datetime.now())
    # # metadata["space_unit"] =
    # # metadata["time_unit"] =
    # metadata["pycellin_version"] = version("pycellin")
    # metadata["geff_version"] = geff_md.geff_version
    # for md in geff_md:
    #     print(md)
