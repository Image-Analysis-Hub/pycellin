#!/usr/bin/env python3

"""
loader.py

This module is part of the pycellin package.
It provides functionality to load a GEFF file into a pycellin model.

References:
- geff GitHub: https://github.com/live-image-tracking-tools/geff
- geff Documentation: https://live-image-tracking-tools.github.io/geff/latest/
"""

from datetime import datetime
import importlib.metadata
from pathlib import Path
from typing import Any

import geff
from geff.metadata_schema import GeffMetadata

from pycellin.classes import Data, Model, Property, PropsMetadata
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
    """
    Extract properties metadata from a given dictionary and update the props_dict.

    Parameters
    ----------
    md : dict[str, geff.metadata_schema.PropMetadata]
        The dictionary containing properties metadata.
    props_dict : dict[str, Property]
        The dictionary to update with extracted properties metadata.
    prop_type : PropertyType
        The type of property being extracted ('node' or 'edge').

    Raises
    ------
    ValueError
        If an unsupported property type is provided.
    KeyError
        If a property identifier already exists in props_dict for the same property
        type.
    """
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
    """
    Extract lineage properties metadata from a given dictionary and update the props_dict.

    Parameters
    ----------
    md : dict[str, Any]
        The dictionary containing lineage properties metadata.
    props_dict : dict[str, Property]
        The dictionary to update with extracted lineage properties metadata.

    Raises
    ------
    KeyError
        If a property identifier already exists in props_dict for lineages.
    """
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


def _extract_units_from_axes(geff_md: GeffMetadata) -> dict[str, Any]:
    """
    Extract and validate space and time units from geff metadata axes.

    Parameters
    ----------
    geff_md : geff.metadata_schema.GeffMetadata
        The geff metadata object containing axes information.

    Returns
    -------
    dict[str, Any]
        Dictionary containing space_unit and time_unit keys.

    Raises
    ------
    ValueError
        If multiple space units or time units are found in axes.
    """
    units_metadata = {}

    if geff_md.axes is not None:
        # Check unicity of space and time units
        space_units = {
            axis.unit for axis in geff_md.axes if axis.type == "space" and axis.unit is not None
        }
        units_metadata["space_unit"] = space_units.pop() if space_units else None
        time_units = {
            axis.unit for axis in geff_md.axes if axis.type == "time" and axis.unit is not None
        }
        units_metadata["time_unit"] = time_units.pop() if time_units else None
        if len(space_units) > 1:
            raise ValueError(
                f"Multiple space units found in axes: {space_units}. "
                f"Pycellin assumes a single space unit."
            )
        if len(time_units) > 1:
            raise ValueError(
                f"Multiple time units found in axes: {time_units}. "
                f"Pycellin assumes a single time unit."
            )
    else:
        units_metadata["space_unit"] = None
        units_metadata["time_unit"] = None

    return units_metadata


def _set_generic_metadata(
    geff_file: Path | str, geff_md: geff.metadata_schema.GeffMetadata
) -> dict[str, Any]:
    """
    Set generic metadata for the model based on the geff file and its metadata.

    Parameters
    ----------
    geff_file : Path | str
        Path to the geff file.
    geff_md : geff.metadata_schema.GeffMetadata
        The geff metadata object.

    Returns
    -------
    dict[str, Any]
        Dictionary containing generic metadata.

    Raises
    ------
    importlib.metadata.PackageNotFoundError
        If the pycellin package is not found when trying to get its version.
    """
    metadata = {}  # type: dict[str, Any]
    metadata["name"] = Path(geff_file).stem
    metadata["file_location"] = geff_file
    metadata["provenance"] = "geff"
    metadata["date"] = str(datetime.now())
    try:
        version = importlib.metadata.version("pycellin")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    metadata["pycellin_version"] = version
    metadata["geff_version"] = geff_md.geff_version
    if geff_md.extra is not None:
        metadata["geff_extra"] = geff_md.extra

    return metadata


def load_GEFF(
    geff_file: Path | str,
    cell_id_key: str | None = None,
    cell_x_key: str | None = None,
    cell_y_key: str | None = None,
    cell_z_key: str | None = None,
    time_key: str | None = None,
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
    cell_x_key : str | None, optional
        The key used to identify the x-coordinate of cells in the geff file.
    cell_y_key : str | None, optional
        The key used to identify the y-coordinate of cells in the geff file.
    cell_z_key : str | None, optional
        The key used to identify the z-coordinate of cells in the geff file.
    time_key : str | None, optional
        The key used to identify the time point of cells in the geff file.

    Returns
    -------
    Model
        A pycellin model containing the data from the geff file.
    """

    # Read the geff file
    geff_graph, geff_md = geff.read_nx(geff_file, validate=True)
    if not geff_md.directed:
        raise ValueError(
            "The geff graph is undirected: pycellin does not support undirected graphs."
        )
    # for node in geff_graph.nodes:
    #     print(f"Node {node}: {geff_graph.nodes[node]}")
    #     break
    print(geff_md)

    # Extract and dispatch metadata
    metadata = _set_generic_metadata(geff_file, geff_md)
    units_metadata = _extract_units_from_axes(geff_md)
    metadata.update(units_metadata)
    # print("Metadata:")
    # for k, v in metadata.items():
    #     print(f"  {k}: {v}")
    props_md = _read_props_metadata(geff_md)
    if geff_md.track_node_props is not None:
        lin_id_key = geff_md.track_node_props.get("lineage")
    else:
        lin_id_key = None
    print("lin_id_key:", lin_id_key)

    # Determine properties for x, y, z, t
    # For now we assume that both display hints and axes are filled...
    if geff_md.display_hints is not None:
        prop_mapping = {
            "cell_x": getattr(geff_md.display_hints, "display_horizontal", None),
            "cell_y": getattr(geff_md.display_hints, "display_vertical", None),
            "cell_z": getattr(geff_md.display_hints, "display_depth", None),
            "time": getattr(geff_md.display_hints, "display_time", None),
        }
        print(prop_mapping)
    else:
        # We need to rely on axes only, or on inputs from the user.
        pass

    # Identify the axes corresponding to the values of the prop_mapping.
    # axes_mapping = {axis.name: axis for axis in geff_md.axes if axis.name is not None}
    # print(axes_mapping)

    # Do we have axis related properties in props_md?
    for axis in geff_md.axes:
        if axis.name not in props_md:
            print("Axis", axis.name, "not in props_md")
            pass

    # Split the graph into lineages
    lineages = _split_graph_into_lineages(geff_graph, lineage_ID_key=lin_id_key)
    print(f"Number of lineages: {len(lineages)}")

    # Rename properties to match pycellin conventions
    # In the properties metadata
    pass
    # In the actual data
    _update_lineages_IDs_key(lineages, lin_id_key)
    for lin in lineages:
        if cell_id_key is None:
            for node in lin.nodes:
                lin.nodes[node]["cell_ID"] = node
        else:
            _update_node_prop_key(lin, old_key=cell_id_key, new_key="cell_ID")
    # TODO: cells positions and edges positions (keys from axes)
    # Time?

    model = Model(
        model_metadata=metadata,
        props_metadata=PropsMetadata(props=props_md),
        data=Data({lin.graph["lineage_ID"]: lin for lin in lineages}),
    )
    check_fusions(model)  # pycellin DOES NOT support fusion events
    # print(model.data)
    # print(model.data.cell_data)

    return model


if __name__ == "__main__":
    geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/reader_test_graph.geff"
    # geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/mouse-20250719.zarr/tracks"
    # geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/test_pycellin_geff/test.zarr"
    # geff_file = (
    #     "/media/lxenard/data/Janelia_Cell_Trackathon/test_pycellin_geff/pycellin_to_geff.geff"
    # )
    # geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/test_trackmate_to_geff/FakeTracks.geff"
    # Yohsuke's file for geffception
    # geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/cell_segmentation.zarr/tree.geff"
    geff_file = "/media/lxenard/data/Janelia_Cell_Trackathon/cell_segmentation.zarr/tree.geff/linage_tree.geff"

    print(geff_file)
    model = load_GEFF(geff_file)
    # print(model)
    # print("props_dict", model.props_metadata.props)
    lineages = model.get_cell_lineages()
    # print(f"Number of lineages: {len(lineages)}")
    # for lin in lineages:
    #     print(lin)
    lin0 = lineages[0]
    # print(lin0.nodes(data=True))
    lin0.plot()

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
