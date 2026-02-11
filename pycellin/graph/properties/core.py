#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Core property functions to create standard Property instances."""

from pycellin.classes.data import Data
from pycellin.classes.exceptions import UpdateRequiredError
from pycellin.classes.property import Property
from pycellin.classes.property_calculator import NodeLocalPropCalculator

# TODO: capitalize property names in the code


def create_frame_property(provenance: str = "pycellin") -> Property:
    return Property(
        identifier="frame",
        name="frame",
        description="Frame number of the cell",
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
        unit=None,
    )


class Timepoint(NodeLocalPropCalculator):
    """Calculator for the timepoint property."""

    def __init__(
        self,
        property: Property,
        data: Data,
        time_step: int | float | None,
        reference_time_property: str,
    ):
        super().__init__(property)

        if time_step is None or time_step == 0:
            raise ValueError(
                "`time_step` cannot be None nor zero for timepoint property calculation."
            )

        self.time_step = time_step
        self.ref_time_prop = reference_time_property

        min_time = None
        for lin in data.cell_data.values():
            root = lin.get_root()
            if isinstance(root, list):
                raise UpdateRequiredError(
                    f"Lineage {lin.graph['lineage_ID']} has several root nodes. "
                    f"Timepoint calculation requires a single root node."
                )
            if self.ref_time_prop not in lin.nodes[root]:
                raise ValueError(
                    f"Reference time property '{self.ref_time_prop}' not found in root node {root} "
                    f"of lineage {lin.graph.get('lineage_ID', 'of unknown ID')}."
                )
            time = lin.nodes[root][self.ref_time_prop]
            if min_time is None or time < min_time:
                min_time = time

        if min_time is None:
            raise ValueError("No valid time values found in lineage data.")

        self.min_time = min_time

    def compute(self, lineage, nid: int) -> int:
        """
        Compute the timepoint of a given node.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cell_ID) of the cell of interest.

        Returns
        -------
        int
            The computed timepoint value for the given node.

        Raises
        ------
        KeyError
            If the reference time property is not found in the node.
        """
        if self.ref_time_prop not in lineage.nodes[nid]:
            raise KeyError(
                f"Reference time property '{self.ref_time_prop}' not found in node {nid}."
            )

        time = lineage.nodes[nid][self.ref_time_prop]
        timepoint = (time - self.min_time) / self.time_step

        if not timepoint.is_integer():
            raise ValueError(
                f"Computed timepoint {timepoint} for node {nid} is not an integer. "
                f"Check time_step and reference time values."
            )

        return int(timepoint)


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


def _create_generic_cell_coord_property() -> Property:
    """Fake property for AST discovery of cell coordinates properties."""
    return Property(
        identifier="cell_{axis}",
        name="cell {axis}",
        description="{axis} coordinate of the cell",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit="space unit",
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


def _create_generic_link_coord_property() -> Property:
    """Fake property for AST discovery of link coordinates properties."""
    return Property(
        identifier="link_{axis}",
        name="link {axis}",
        description="{axis} coordinate of the link, i.e. mean coordinate of its two cells",
        provenance="pycellin",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="float",
        unit="space unit",
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


def _create_generic_lineage_coord_property() -> Property:
    """Fake property for AST discovery of lineage coordinates properties."""
    return Property(
        identifier="lineage_{axis}",
        name="lineage {axis}",
        description="{axis} coordinate of the lineage, i.e. mean coordinate of its cells",
        provenance="pycellin",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="float",
        unit="space unit",
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


def create_cycle_duration_property(time_unit: str | None, provenance: str = "pycellin") -> Property:
    return Property(
        identifier="cycle_duration",
        name="cycle duration",
        description="Duration of the cell cycle, regardless of gaps",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=time_unit,
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
