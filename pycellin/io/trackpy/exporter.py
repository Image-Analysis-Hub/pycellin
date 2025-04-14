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
    # We don't want to modify the original model.
    model_copy = copy.deepcopy(model)
    # Removal of division events.
    # We simply remove the edges involved in the divisions.
    print("model before", model_copy)
    for lin in model_copy.get_cell_lineages():
        print("before", lin)
        divs = lin.get_divisions()
        div_edges = [lin.out_edges(div) for div in divs]
        for edge in div_edges:
            print("removing edge", edge)
            model_copy.remove_link(*edge, lin.graph["lineage_ID"])
        print("after", lin)
    model_copy.update()
    print("model after", model_copy)

    df = pd.DataFrame()

    return df


if __name__ == "__main__":
    folder = "/mnt/data/Code/trackpy-examples-master/sample_data/"
    tracks = "FakeTracks_trackpy.pkl"

    df = pd.read_pickle(folder + tracks)

    from pycellin import load_trackpy_dataframe

    model = load_trackpy_dataframe(df)
    for lin in model.get_cell_lineages():
        print(lin)
    #     lin.plot()
    # model.add_link(source_cell_ID=8, source_lineage_ID=0, target_cell_ID=9)

    # model.add_link(
    #     source_cell_ID=8, source_lineage_ID=0, target_cell_ID=10, target_lineage_ID=1
    # )

    # model.get_cell_lineage_from_ID(0)._add_link(
    #     source_noi=8, target_noi=10, target_lineage=model.get_cell_lineage_from_ID(1)
    # )

    # model.get_cell_lineage_from_ID(1)._remove_link(10, 11)
    # model.get_cell_lineage_from_ID(0)._add_link(
    #     source_noi=9, target_noi=11, target_lineage=model.get_cell_lineage_from_ID(1)
    # )

    model.remove_link(10, 11, 1)
    model.add_link(
        source_cell_ID=9, source_lineage_ID=0, target_cell_ID=11, target_lineage_ID=1
    )
    model.update()
    # export_trackpy_dataframe(model)
    for lin in model.get_cell_lineages():
        print(lin)
        lin.plot()
