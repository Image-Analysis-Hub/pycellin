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
        provenance=provenance,
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
        unit="frame",
    )
    return feat


def define_cell_ID_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="cell_ID",
        description="Unique identifier of the cell",
        provenance=provenance,
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
        unit="none",
    )
    return feat


def define_lineage_ID_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="lineage_ID",
        description="Unique identifier of the lineage",
        provenance=provenance,
        feat_type="lineage",
        lin_type="Lineage",
        data_type="int",
        unit="none",
    )
    return feat


def define_cell_coord_Feature(
    unit: str, dimension: str, provenance: str = "Pycellin"
) -> Feature:
    feat = Feature(
        name=f"cell_{dimension}",
        description=f"{dimension.upper()} coordinate of the cell",
        provenance=provenance,
        feat_type="node",
        lin_type="CellLineage",
        data_type="float",
        unit=unit,
    )
    return feat


def define_link_coord_Feature(
    unit: str, dimension: str, provenance: str = "Pycellin"
) -> Feature:
    feat = Feature(
        name=f"link_{dimension}",
        description=(
            f"{dimension.upper()} coordinate of the link, "
            f"i.e. mean coordinate of its two cells"
        ),
        provenance=provenance,
        feat_type="edge",
        lin_type="CellLineage",
        data_type="float",
        unit=unit,
    )
    return feat


def define_lineage_coord_Feature(
    unit: str, dimension: str, provenance: str = "Pycellin"
) -> Feature:
    feat = Feature(
        name=f"lineage_{dimension}",
        description=(
            f"{dimension.upper()} coordinate of the lineage, "
            f"i.e. mean coordinate of its cells"
        ),
        provenance=provenance,
        feat_type="lineage",
        lin_type="CellLineage",
        data_type="float",
        unit=unit,
    )
    return feat
