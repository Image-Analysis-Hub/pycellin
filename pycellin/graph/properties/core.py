#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Core property functions to create standard Property instances."""

from pycellin.classes.property import Property


def create_frame_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="frame",
        name="frame",
        description="Frame number of the cell ",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
        unit="frame",
    )


def create_timepoint_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="timepoint",
        name="timepoint",
        description="Timepoint of the detection",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
        unit="frame",
    )


def create_cell_id_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="cell_ID",
        name="cell ID",
        description="Unique identifier of the cell",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
    )


def create_lineage_id_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="lineage_ID",
        name="lineage ID",
        description="Unique identifier of the lineage",
        provenance=provenance,
        prop_type="lineage",
        lin_type="Lineage",
        dtype="int",
    )


def create_cell_coord_property(unit: str, axis: str, provenance: str = "pycellin") -> Property:
    return Property(
        identifier=f"cell_{axis}",
        name=f"cell {axis}",
        description=f"{axis.upper()} coordinate of the cell",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


def create_link_coord_property(unit: str, axis: str, provenance: str = "pycellin") -> Property:
    return Property(
        identifier=f"link_{axis}",
        name=f"link {axis}",
        description=(
            f"{axis.upper()} coordinate of the link, i.e. mean coordinate of its two cells"
        ),
        provenance=provenance,
        prop_type="edge",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


def create_lineage_coord_property(unit: str, axis: str, provenance: str = "pycellin") -> Property:
    return Property(
        identifier=f"lineage_{axis}",
        name=f"lineage {axis}",
        description=(
            f"{axis.upper()} coordinate of the lineage, i.e. mean coordinate of its cells"
        ),
        provenance=provenance,
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


def create_cycle_id_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="cycle_ID",
        name="cycle ID",
        description=(
            "Unique identifier of the cell cycle, i.e. cell_ID of the last cell in the cell cycle"
        ),
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )


def create_cells_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="cells",
        name="cells",
        description="cell_IDs of the cells in the cell cycle, in chronological order",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="list[int]",
    )


def create_cycle_length_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="cycle_length",
        name="cycle length",
        description="Number of cells in the cell cycle, minding gaps",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )


def create_cycle_duration_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="cycle_duration",
        name="cycle duration",
        description="Number of frames in the cell cycle, regardless of gaps",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
        unit="frame",
    )


def create_level_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="level",
        name="level",
        description=(
            "Level of the cell cycle in the lineage, "
            "i.e. number of cell cycles upstream of the current one"
        ),
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )
