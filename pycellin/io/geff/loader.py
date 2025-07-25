#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

from pycellin.classes import Model


def load_geff_file(geff_file: Path | str) -> Model:
    """
    Load a geff file and return a pycellin model containing the data.

    Parameters
    ----------
    geff_file : Path | str
        Path to the geff file to load.

    Returns
    -------
    Model
        A pycellin model containing the data from the geff file.
    """
    pass

    # Read the geff file
    # Check for fusions
    # Extract and dispatch metadata
    # Rename features to match pycellin conventions
    # Split the graph into lineages
    # Return the model


if __name__ == "__main__":
    geff_file = (
        "C:/Users/lxenard/Documents/Janelia_Cell_Trackathon/mouse-20250719.zarr/tracks"
    )
    # geff_file = "C:/Users/lxenard/Documents/Janelia_Cell_Trackathon/test_pycellin_geff/test.zarr"

    geff_graph, geff_md = geff.read_nx(geff_file, validate=True)
    print(geff_graph)
    # Check how many weakly connected components there are.
    print(
        f"Number of weakly connected components: {len(list(nx.weakly_connected_components(geff_graph)))}"
    )
    for k, v in geff_graph.graph.items():
        print(f"{k}: {v}")
    # print(graph.graph["axes"][0].unit)

    if geff_md.directed:
        print("The graph is directed.")

    metadata = {}  # type: dict[str, Any]
    metadata["name"] = Path(geff_file).stem
    metadata["file_location"] = geff_file
    metadata["provenance"] = "geff"
    metadata["date"] = str(datetime.now())
    # metadata["space_unit"] =
    # metadata["time_unit"] =
    metadata["pycellin_version"] = version("pycellin")
    metadata["geff_version"] = geff_md.geff_version
    for md in geff_md:
        print(md)
