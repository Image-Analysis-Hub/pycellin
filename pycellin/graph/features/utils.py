#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pycellin.classes import Feature


# TODO: see if there is way to get the same info without hard coding
# the list of available features.
# TODO: should these functions be here or in a utils.py at a higher level,
# like at the root of Pycellin?


def get_pycellin_cell_lineage_features() -> dict[str, str]:
    """
    Return the Pycellin features that can be computed on cell lineages.

    Returns
    -------
    dict[str, str]
        Dictionary of features of the cell lineages,
        with features name as keys and features description as values.
    """
    cell_lineage_feats = {
        "absolute_age": "Age of the cell since the beginning of the lineage",
        "angle": "Angle of the cell trajectory between two consecutive detections",
        "cell_displacement": (
            "Displacement of the cell between two consecutive detections"
        ),
        "cell_speed": "Speed of the cell between two consecutive detections",
        "relative_age": "Age of the cell since the beginning of the current cell cycle",
    }
    return cell_lineage_feats


def get_pycellin_cycle_lineage_features() -> dict[str, str]:
    """
    Return the Pycellin features that can be computed on cycle lineages.

    Returns
    -------
    dict[str, str]
        Dictionary of features of the cycle lineages,
        with features name as keys and features description as values.
    """
    cycle_lineage_feats = {
        "branch_total_displacement": "Displacement of the cell during the cell cycle",
        "branch_mean_displacement": (
            "Mean displacement of the cell during the cell cycle"
        ),
        "branch_mean_speed": "Mean speed of the cell during the cell cycle",
        "cell_cycle_completeness": (
            "Completeness of the cell cycle, i.e. does it start and end with a division"
        ),
        "division_time": "Time elapsed between the birth of a cell and its division",
        "division_rate": "Number of divisions per time unit",
        "straightness": "Straightness of the cell trajectory",
    }
    return cycle_lineage_feats


def define_frame_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="frame",
        description="Frame number of the cell ",
        lineage_type="CellLineage",
        provenance=provenance,
        data_type="int",
        unit="frame",
    )
    return feat


def define_cell_ID_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="cell_ID",
        description="Unique identifier of the cell",
        lineage_type="CellLineage",
        provenance=provenance,
        data_type="int",
        unit="none",
    )
    return feat


def define_lineage_ID_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="lineage_ID",
        description="Unique identifier of the lineage",
        lineage_type="CellLineage",
        provenance=provenance,
        data_type="int",
        unit="none",
    )
    return feat


def define_cell_location_Feature(unit: str, provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="location",
        description="Location of the cell",
        lineage_type="CellLineage",
        provenance=provenance,
        data_type="float",
        unit=unit,
    )
    return feat
