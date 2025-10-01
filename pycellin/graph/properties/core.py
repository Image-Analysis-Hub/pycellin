#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Core property functions to create standard Property instances."""

import math
from decimal import Decimal
from pycellin.classes.data import Data
from pycellin.classes.exceptions import UpdateRequiredError
from pycellin.classes.property import Property
from pycellin.classes.property_calculator import NodeLocalPropCalculator


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


class Timepoint(NodeLocalPropCalculator):
    """Calculator for the timepoint property."""

    def __init__(
        self,
        property: Property,
        data: Data,
        time_step: int | float | None,
        reference_time_property: str,
    ):
        # TODO: move time_step computation to Model level
        # Maybe add a parameter for irregular time_steps. That way we can rely on the
        # previous implementation (min time difference) by default but upgrade to the gcd
        # when irregular time_step
        # Should time_step be recomputed when doing an update?
        # TODO: switch all methods relying on "frame" to "timepoint" (cf table in obsidian)
        # TODO: add missing wrappers (cf obsidian)
        super().__init__(property)
        self.time_step: int | float
        self.ref_time_prop = reference_time_property

        min_time = None
        time_differences = set()

        for lin in data.cell_data.values():
            # Find minimum time
            root = lin.get_root()
            if isinstance(root, list):
                raise UpdateRequiredError(
                    "The lineage root is a list. "
                    "Timepoint calculation requires a single root node. "
                    "Please update your data."
                )
            time = lin.nodes[root][self.ref_time_prop]
            if min_time is None or time < min_time:
                min_time = time

            if time_step is None:
                # Collect all time differences
                for source_node, target_node in lin.edges():
                    source_time = lin.nodes[source_node][self.ref_time_prop]
                    target_time = lin.nodes[target_node][self.ref_time_prop]
                    time_diff = abs(target_time - source_time)
                    if time_diff > 0:
                        time_differences.add(time_diff)

        if time_step is None:
            if not time_differences:
                raise ValueError(
                    "No valid time differences found in the dataset to determine time step."
                )

            # Calculate GCD of all time differences
            # Check if all values are effectively integers (within floating point precision)
            # TODO: extract EPSILON to Model level
            EPSILON = 1e-12
            if all(abs(td - round(td)) < EPSILON for td in time_differences):
                # Treat as integers for more efficient GCD calculation
                self.time_step = math.gcd(*map(int, map(round, time_differences)))
            else:
                self.time_step = self._gcd_floats(time_differences)
        else:
            self.time_step = time_step

        self.min_time = min_time

    def _gcd_floats(self, values: set[float]) -> float:
        """Calculate GCD for floating point numbers using exact decimal precision."""
        if not values:
            raise ValueError("Cannot calculate GCD of empty list")

        # Convert to Decimal for exact precision handling
        decimal_values = [Decimal(str(v)) for v in values if v > 0]
        if not decimal_values:
            raise ValueError("All values are zero or negative")

        # Find the maximum number of decimal places among all values
        max_decimal_places = 0
        for d in decimal_values:
            exponent = d.as_tuple().exponent
            if isinstance(exponent, int) and exponent < 0:
                max_decimal_places = max(max_decimal_places, abs(exponent))

        # Scale all values to integers
        scale_factor = 10**max_decimal_places
        int_values = [int(d * scale_factor) for d in decimal_values]
        result_scaled = math.gcd(*int_values)

        return float(result_scaled / scale_factor)

    def compute(self, lineage, nid: int) -> float:
        time = lineage.nodes[nid][self.ref_time_prop]
        return (time - self.min_time) / self.time_step


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
