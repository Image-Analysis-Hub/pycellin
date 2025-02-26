#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pycellin.classes import Feature


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
        "cell_length": "Length of the cell",
        "cell_speed": "Speed of the cell between two consecutive detections",
        "cell_width": "Width of the cell",
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
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
        provenance=provenance,
        unit="frame",
    )
    return feat


def define_cell_ID_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="cell_ID",
        description="Unique identifier of the cell",
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
        provenance=provenance,
        unit="none",
    )
    return feat


def define_lineage_ID_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="lineage_ID",
        description="Unique identifier of the lineage",
        feat_type="lineage",
        lin_type="CellLineage",  # TODO: should be Lineage? or CellLineage+CycleLineage
        data_type="int",
        provenance=provenance,
        unit="none",
    )
    return feat


# FIXME:  location should be splitted into x, y and z, with a different name depending
# on the feature type (node, edge, lineage), something like cell_x, edge_y...
def define_cell_location_Feature(unit: str, provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="cell_location",
        description="Location of the cell",
        feat_type="node",
        lin_type="CellLineage",
        data_type="float",
        provenance=provenance,
        unit=unit,
    )
    return feat
