#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
exporter.py

This module is part of the Pycellin package.

This module provides functions to export Pycellin models to trackpy tracking files.
It includes a function to export a Pycellin model to a trackpy file and helper functions
to build trackpy tracks from a lineage.

References:
- trackpy: D. B. Allan, T. Caswell, N. C. Keim, C. M. van der Weland R. W. Verweij,
“soft-matter/trackpy: v0.6.4”. Zenodo, Jul. 10, 2024. doi: 10.5281/zenodo.12708864.
- trackpy GitHub: https://github.com/soft-matter/trackpy
"""


import copy

import pandas as pd

from pycellin.classes.model import Model


def export_trackpy_dataframe(model: Model) -> pd.DataFrame:
    """
    Export a Pycellin model to a trackpy DataFrame.

    Trackpy does not support division events. They will be removed for
    the export so each cell cycle will be reprensented by a single
    trackpy track in the dataframe.

    Parameters
    ----------
    model : Model
        The Pycellin model to export.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing trackpy formatted data.
    """
    model_copy = copy.deepcopy(model)  # Don't want to modify the original model.

    # We want to safekeep the original lineage IDs in the nodes of the model since
    # we are going to rename and/or renumber them.
    for lin_ID, lin in model_copy.data.cell_data.items():
        for node in lin.nodes():
            lin.nodes[node]["lineage_ID_Pycellin"] = lin_ID

    # Removal of division events.
    # We simply remove the edges involved in the divisions.
    for lin in model_copy.get_cell_lineages():
        divs = lin.get_divisions()
        div_edges = [edge for div in divs for edge in lin.out_edges(div)]
        for edge in div_edges:
            model_copy.remove_link(*edge, lin.graph["lineage_ID"])
    model_copy.update()

    # Trackpy might not like negative lineage IDs so we change them to positive ones.
    one_node_lin_IDs = [
        lin.graph["lineage_ID"]
        for lin in model_copy.get_cell_lineages()
        if lin.graph["lineage_ID"] < 0
    ]
    for lin_ID in one_node_lin_IDs:
        lin = model_copy.get_cell_lineage_from_ID(lin_ID)
        assert lin is not None
        new_lin_ID = model_copy.get_next_available_lineage_ID()
        # Update the lineage ID in the graph.
        lin.graph["lineage_ID"] = new_lin_ID
        # Update the lineage ID in the cell data.
        model_copy.data.cell_data.pop(lin_ID)
        model_copy.data.cell_data[new_lin_ID] = lin

    # Creation of the trackpy DataFrame.
    df = model_copy.to_cell_dataframe()
    # We have to rename some columns to be compatible with trackpy.
    if "particle" in df.columns:
        # If we already have this column, it means the data is coming from
        # trackpy, but it might not be up to date. Safer to remove it and
        # rename it from "lineage_ID".
        df.drop(columns=["particle"], inplace=True)
    df.rename(columns={"lineage_ID": "particle"}, inplace=True)
    df.rename(columns={"cell_x": "x"}, inplace=True)
    df.rename(columns={"cell_y": "y"}, inplace=True)
    if "cell_z" in df.columns:
        df.rename(columns={"cell_z": "z"}, inplace=True)
    if "ROI_coords" in df.columns:
        # We need to remove the ROI_coords column.
        df.drop(columns=["ROI_coords"], inplace=True)
    # Reorder the columns to match trackpy format.
    if "z" in df.columns:
        dim_columns = ["z", "y", "x"]
    else:
        dim_columns = ["y", "x"]
    df = df[
        dim_columns
        + [col for col in df.columns if col not in ["z", "y", "x", "frame", "particle"]]
        + ["frame", "particle"]
    ]
    # Sort the rows.
    df.sort_values(by=["particle", "frame"], inplace=True)

    return df


if __name__ == "__main__":
    folder = "/mnt/data/Code/trackpy-examples-master/sample_data/"
    tracks = "FakeTracks_trackpy.pkl"
    xml = "sample_data/Ecoli_growth_on_agar_pad.xml"

    df = pd.read_pickle(folder + tracks)
    print(df.head())

    from pycellin import load_trackpy_dataframe, load_TrackMate_XML

    # model = load_TrackMate_XML(xml)
    model = load_trackpy_dataframe(df)
    for lin in model.get_cell_lineages():
        print(lin)
    model.add_link(
        source_cell_ID=8, source_lineage_ID=0, target_cell_ID=10, target_lineage_ID=1
    )
    model.update()

    df = export_trackpy_dataframe(model)
    print(df.head())
