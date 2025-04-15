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


def safekeep_original_lineage_IDs(model: Model) -> None:
    """
    Add original lineage IDs to the nodes of the model.

    We want to safekeep them since we are going to renumber
    the lineages later on.

    Parameters
    ----------
    model : Model
        The Pycellin model to modify.
    """
    for lin_ID, lin in model.data.cell_data.items():
        for node in lin.nodes():
            lin.nodes[node]["lineage_ID_Pycellin"] = lin_ID


def remove_division_events(model: Model) -> None:
    """
    Remove division events by deleting edges involved in divisions.

    Parameters
    ----------
    model : Model
        The Pycellin model to modify.
    """
    for lin in model.get_cell_lineages():
        divs = lin.get_divisions()
        div_edges = [edge for div in divs for edge in lin.out_edges(div)]
        for edge in div_edges:
            model.remove_link(*edge, lin.graph["lineage_ID"])
    model.update()


def renumber_negative_lineage_IDs(model: Model) -> None:
    """
    Ensure lineage IDs are positive.

    Trackpy might not support negative lineage IDs so it is safer to
    renumber them to positive ones.

    Parameters
    ----------
    model : Model
        The Pycellin model to modify.
    """
    one_node_lin_IDs = [
        lin.graph["lineage_ID"]
        for lin in model.get_cell_lineages()
        if lin.graph["lineage_ID"] < 0
    ]
    for lin_ID in one_node_lin_IDs:
        lin = model.get_cell_lineage_from_ID(lin_ID)
        assert lin is not None
        new_lin_ID = model.get_next_available_lineage_ID()
        # Update the lineage ID in the graph.
        lin.graph["lineage_ID"] = new_lin_ID
        # Update the lineage ID in the cell data.
        model.data.cell_data.pop(lin_ID)
        model.data.cell_data[new_lin_ID] = lin


def rename_columns_if_exist(df, columns_map):
    """
    Helper function to rename columns if they exist in the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to modify.
    columns_map : dict
        A dictionary mapping old column names to new column names.
    """
    for old_name, new_name in columns_map.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)


def drop_columns_if_exist(df, columns):
    """
    Helper function to drop columns if they exist in the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to modify.
    columns : list
        The names of the columns to drop.
    """
    for column in columns:
        if column in df.columns:
            df.drop(columns=[column], inplace=True)


def format_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Format the DataFrame to be compatible with trackpy.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to format.

    Returns
    -------
    pd.DataFrame
        The formatted DataFrame.
    """
    # Drop unnecessary columns.
    drop_columns_if_exist(df, ["ROI_coords", "particle"])
    # If we already have the "particle" column, it means the data is coming from
    # trackpy, but it might not be up to date. Safer to remove it then recreate
    # it from "lineage_ID".

    # Rename columns to match trackpy format.
    rename_columns_if_exist(
        df,
        {
            "cell_x": "x",
            "cell_y": "y",
            "cell_z": "z",
            "lineage_ID": "particle",
        },
    )

    # Reorder columns to match trackpy format
    dim_columns = ["z", "y", "x"] if "z" in df.columns else ["y", "x"]
    df = df[
        dim_columns
        + [col for col in df.columns if col not in dim_columns + ["frame", "particle"]]
        + ["frame", "particle"]
    ]

    # Sort the rows.
    df.sort_values(by=["particle", "frame"], inplace=True)

    return df


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
    # Prepare the model for export.
    model_copy = copy.deepcopy(model)  # Don't want to modify the original model.
    safekeep_original_lineage_IDs(model_copy)
    remove_division_events(model_copy)  # Trackpy does not support division events.
    renumber_negative_lineage_IDs(model_copy)

    # Creation of the trackpy DataFrame.
    df = model_copy.to_cell_dataframe()
    df = format_dataframe(df)

    return df


if __name__ == "__main__":

    # # Test with a sample TrackMate XML file.
    # from pycellin import load_TrackMate_XML

    # xml = "sample_data/Ecoli_growth_on_agar_pad.xml"

    # model = load_TrackMate_XML(xml)
    # for lin in model.get_cell_lineages():
    #     print(lin)

    # df = export_trackpy_dataframe(model)
    # print(df.head())

    # Test with a sample trackpy DataFrame.
    from pycellin import load_trackpy_dataframe

    folder = "/mnt/data/Code/trackpy-examples-master/sample_data/"
    tracks = "FakeTracks_trackpy.pkl"

    df = pd.read_pickle(folder + tracks)
    print(df.head())
    print(df.shape)

    model = load_trackpy_dataframe(df)
    for lin in model.get_cell_lineages():
        print(lin)
    model.add_link(
        source_cell_ID=8, source_lineage_ID=0, target_cell_ID=10, target_lineage_ID=1
    )
    model.update()

    df = export_trackpy_dataframe(model)
    print(df.head())
    print(df.shape)
