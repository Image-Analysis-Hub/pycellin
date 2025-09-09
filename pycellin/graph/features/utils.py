#!/usr/bin/env python3
# -*- coding: utf-8 -*-


def get_pycellin_cell_lineage_properties() -> dict[str, str]:
    """
    Return the pycellin properties that can be computed on cell lineages.

    Returns
    -------
    dict[str, str]
        Dictionary of properties of the cell lineages,
        with properties name as keys and properties description as values.
    """
    cell_lineage_props = {
        "absolute_age": "Age of the cell since the beginning of the lineage",
        "angle": "Angle of the cell trajectory between two consecutive detections",
        "cell_displacement": ("Displacement of the cell between two consecutive detections"),
        "cell_speed": "Speed of the cell between two consecutive detections",
        "rod_length": "Length of the cell, for rod-shaped cells only",
        "rod_width": "Width of the cell, for rod-shaped cells only",
        "relative_age": "Age of the cell since the beginning of the current cell cycle",
    }
    return cell_lineage_props


def get_pycellin_cycle_lineage_properties() -> dict[str, str]:
    """
    Return the pycellin properties that can be computed on cycle lineages.

    Returns
    -------
    dict[str, str]
        Dictionary of properties of the cycle lineages,
        with properties name as keys and properties description as values.
    """
    cycle_lineage_props = {
        "branch_total_displacement": "Displacement of the cell during the cell cycle",
        "branch_mean_displacement": ("Mean displacement of the cell during the cell cycle"),
        "branch_mean_speed": "Mean speed of the cell during the cell cycle",
        "cycle_completeness": (
            "Completeness of the cell cycle, i.e. does it start and end with a division"
        ),
        "division_time": "Time elapsed between the birth of a cell and its division",
        "division_rate": "Number of divisions per time unit",
        "straightness": "Straightness of the cell trajectory",
    }
    return cycle_lineage_props
