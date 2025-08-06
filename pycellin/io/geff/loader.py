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
from typing import Any

import geff
import networkx as nx

from pycellin.classes import Data, Feature, Model
from pycellin.custom_types import FeatureType
from pycellin.io.utils import (
    _split_graph_into_lineages,
    _update_lineages_IDs_key,
    _update_node_feature_key,
    check_fusions,
)


def _extract_feats_metadata(
    md: dict[str, geff.metadata_schema.PropMetadata],
    feats_dict: dict[str, Feature],
    feat_type: FeatureType,
) -> None:
    for key, prop in md.items():
        if key not in feats_dict:
            feats_dict[key] = Feature(
                name=key,
                description=prop.description if prop.description else key,
                provenance="geff",
                feat_type=feat_type,
                lin_type="CellLineage",
                data_type=prop.dtype,
                unit=prop.unit,
            )
        else:
            if feats_dict[key].feat_type != feat_type:
                # If the key is already taken, we rename with prefix.
                if feat_type == "node":
                    prefix = "cell"
                elif feat_type == "edge":
                    prefix = "link"
                else:
                    raise ValueError(
                        f"Unsupported feature type: {feat_type}. Expected 'node' or 'edge'."
                    )
                # TODO: should we rename both features?
                new_key = f"{prefix}_{key}"
                feats_dict[new_key] = Feature(
                    name=new_key,
                    description=prop.description if prop.description else new_key,
                    provenance="geff",
                    feat_type=feat_type,
                    lin_type="CellLineage",
                    data_type=prop.dtype,
                    unit=prop.unit,
                )
            else:
                raise KeyError(
                    f"Feature '{key}' already exists in feats_dict for nodes and edges. "
                    "Please ensure unique feature names."
                )
                # TODO: but then, what does the user do? They might not be able to rename
                # the feature from the tool that generated the geff file.
                # Directly ask the user how to rename?


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
    # TODO: but for now we wait for the change in geff metadata specs
    feats_dict = {}
    if geff_md.node_props_metadata is not None:
        # print(geff_md.node_props_metadata)
        _extract_feats_metadata(geff_md.node_props_metadata, feats_dict, "node")

    # Split the graph into lineages
    lineages = _split_graph_into_lineages(geff_graph, lineage_ID_key=lin_id_key)
    print(f"Number of lineages: {len(lineages)}")

    # Rename features to match pycellin conventions
    _update_lineages_IDs_key(lineages, lin_id_key)
    for lin in lineages:
        if cell_id_key is None:
            for node in lin.nodes:
                lin.nodes[node]["cell_ID"] = node
        else:
            _update_node_feature_key(lin, old_key=cell_id_key, new_key="cell_ID")
    # TODO: cells positions and edges positions (keys from axes)
    # Time?

    # Check for fusions
    data = Data({lin.graph["lineage_ID"]: lin for lin in lineages})
    model = Model(data=data)
    # print(model.data)
    # print(model.data.cell_data)
    check_fusions(model)  # pycellin DOES NOT support fusion events

    return model


if __name__ == "__main__":
    geff_file = "C:/Users/lxenard/Documents/Janelia_Cell_Trackathon/reader_test_graph.geff"
    # geff_file = "C:/Users/lxenard/Documents/Janelia_Cell_Trackathon/mouse-20250719.zarr/tracks"
    # geff_file = "C:/Users/lxenard/Documents/Janelia_Cell_Trackathon/test_pycellin_geff/test.zarr"
    geff_file = (
        "C:/Users/lxenard/Documents/Janelia_Cell_Trackathon/test_trackmate_to_geff/FakeTracks.geff"
    )
    geff_file = "/mnt/data/Janelia_Cell_Trackathon/test_trackmate_to_geff/FakeTracks.geff"

    print(geff_file)
    model = load_geff_file(geff_file)
    # print(model)
    print("feats_dict", model.feat_declaration.feats_dict)
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
