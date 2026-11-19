#!/usr/bin/env python3

"""
Writer for trackpy DataFrames.

References
----------
- trackpy: D. B. Allan, T. Caswell, N. C. Keim, C. M. van der Wel and R. W. Verweij,
  “soft-matter/trackpy: v0.6.4”. Zenodo, Jul. 10, 2024. doi: 10.5281/zenodo.12708864.
- trackpy GitHub: https://github.com/soft-matter/trackpy
"""

import copy

import pandas as pd

from pycellin.classes.model import Model
from pycellin.io.utils import _check_up_to_date, _identify_frame_prop


def _safekeep_original_lineage_ids(model: Model) -> None:
    """
    Add original lineage IDs to the nodes of the model.

    We want to safekeep them since we are going to renumber
    the lineages later on. They are stored in the ``lineage_id_pycellin`` property.

    Parameters
    ----------
    model : Model
        The Pycellin model to modify.
    """
    for lin_id, lin in model.data.cell_lineages.items():
        for node in lin.nodes():
            lin.nodes[node]["lineage_id_pycellin"] = lin_id


def _remove_division_events(model: Model) -> None:
    """
    Remove division events by deleting edges involved in divisions.

    The model is then updated, so that each cell cycle becomes a separate lineage.
    A model without divisions is left unchanged.

    Parameters
    ----------
    model : Model
        The Pycellin model to modify.
    """
    removed_link = False
    for lin in model.get_cell_lineages():
        divs = lin.get_divisions()
        div_edges = [edge for div in divs for edge in lin.out_edges(div)]
        for edge in div_edges:
            model.remove_link(*edge, lineage_id=lin.graph["lineage_id"])
            removed_link = True
    if removed_link:
        model.update()


def _renumber_negative_lineage_ids(model: Model) -> None:
    """
    Ensure lineage IDs are positive.

    Trackpy might not support negative lineage IDs so it is safer to
    renumber them to positive ones.

    Parameters
    ----------
    model : Model
        The Pycellin model to modify.
    """
    negative_lin_ids = [
        lin.graph["lineage_id"]
        for lin in model.get_cell_lineages()
        if lin.graph["lineage_id"] < 0
    ]
    for lin_id in negative_lin_ids:
        lin = model.get_cell_lineage(lin_id)
        assert lin is not None
        new_lin_id = model.get_next_available_lineage_id()
        # Update the lineage ID in the graph.
        lin.graph["lineage_id"] = new_lin_id
        # Update the lineage ID in the dictionary of cell lineages.
        model.data.cell_lineages.pop(lin_id)
        model.data.cell_lineages[new_lin_id] = lin


def _rename_columns_if_exist(df: pd.DataFrame, columns_map: dict) -> pd.DataFrame:
    """
    Rename columns if they exist in the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame whose columns to rename. It is not modified.
    columns_map : dict
        A dictionary mapping old column names to new column names.

    Returns
    -------
    pd.DataFrame
        A copy of the DataFrame, with its existing columns renamed, or `df` itself
        if no column is renamed.
    """
    for old_name, new_name in columns_map.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
    return df


def _drop_columns_if_exist(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Drop columns if they exist in the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame whose columns to drop. It is not modified.
    columns : list
        The names of the columns to drop.

    Returns
    -------
    pd.DataFrame
        A copy of the DataFrame, without the columns that existed among `columns`,
        or `df` itself if no column is dropped.
    """
    for column in columns:
        if column in df.columns:
            df = df.drop(columns=[column])
    return df


def _format_dataframe(df: pd.DataFrame, frame_prop: str) -> pd.DataFrame:
    """
    Format the DataFrame to be compatible with trackpy.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to format.
    frame_prop : str
        The property to use as the frame identifier. A ``frame`` column that holds
        another property is replaced.

    Returns
    -------
    pd.DataFrame
        The formatted DataFrame.
    """
    # Drop unnecessary columns.
    df = _drop_columns_if_exist(df, ["cell_contour", "particle"])
    # If we already have the "particle" column, it means the data is coming from
    # trackpy, but it might not be up to date. Safer to remove it then recreate
    # it from "lineage_id".
    # Likewise, a "frame" column that isn't frame_prop, e.g. because some cells have
    # no frame, would end up next to the renamed frame_prop.
    if frame_prop != "frame":
        df = _drop_columns_if_exist(df, ["frame"])

    # Rename columns to match trackpy format.
    df = _rename_columns_if_exist(
        df,
        {
            "cell_x": "x",
            "cell_y": "y",
            "cell_z": "z",
            "lineage_id": "particle",
            frame_prop: "frame",
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
    df = df.sort_values(by=["particle", "frame"])

    return df


def to_trackpy(model: Model) -> pd.DataFrame:
    """
    Export a Pycellin model to a trackpy DataFrame.

    Trackpy does not support division events. They will be removed for
    the export so each cell cycle will be represented by a single
    trackpy track in the dataframe.

    Parameters
    ----------
    model : Model
        The Pycellin model to export.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing trackpy formatted data. Its ``particle`` column
        identifies the cell cycles, and its ``lineage_id_pycellin`` column the
        lineages of the model.

    Raises
    ------
    UpdateRequiredError
        If the model requires an update.
    ValueError
        If the model has no cells, or no ``cell_x`` or ``cell_y`` values.
        If only some cells have a frame and their frames can't be deduced, see Notes.

    Notes
    -----
    The ``frame`` column comes from the frame property of the model, a node property
    called ``frame`` in any case, e.g. trackpy's ``frame`` or TrackMate's ``FRAME``.
    Cells without frame, e.g. added with `Model.add_cell`, get their timepoint plus the
    difference between frame and timepoint of the other cells, which must be the same
    for all of them. Without frame property, the frames are the timepoints, which
    start at 0 at the earliest cell.
    """
    _check_up_to_date(model)
    # Prepare the model for export.
    model_copy = copy.deepcopy(model)  # Don't want to modify the original model.
    _safekeep_original_lineage_ids(model_copy)
    _remove_division_events(model_copy)  # Trackpy does not support division events.
    _renumber_negative_lineage_ids(model_copy)

    # Creation of the trackpy DataFrame, once the missing frames are completed.
    frame_prop = _identify_frame_prop(model_copy)
    df = model_copy.to_cell_dataframe()
    missing = [prop for prop in ("cell_x", "cell_y") if prop not in df.columns]
    if missing:
        raise ValueError(
            "trackpy needs the positions of the cells, but the model has no "
            f"{' or '.join(repr(prop) for prop in missing)} values."
        )
    df = _format_dataframe(df, frame_prop)

    return df


if __name__ == "__main__":
    """
    Quick demo with sample data.
    """
    from pathlib import Path

    from pycellin.io.trackmate.reader import read_trackmate_xml

    xml = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Ecoli_growth_on_agar_pad.xml"
    )
    model = read_trackmate_xml(
        xml,
        lone_spots="all",
        tracks="all",
    )

    df = to_trackpy(model)
    print(df.head())
    print(df.shape)
