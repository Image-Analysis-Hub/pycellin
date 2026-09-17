#!/usr/bin/env python3

"""Core property functions to create standard Property instances."""

import math

from pycellin.classes.data import Data
from pycellin.classes.exceptions import UpdateRequiredError
from pycellin.classes.property import Property
from pycellin.classes.property_calculator import NodeLocalPropCalculator


def create_frame_property(provenance: str = "pycellin") -> Property:
    """
    Create the declaration of the `frame` core property.

    `frame` is the frame number of the cell in the source image sequence.
    It is a node property of cell lineages.

    Parameters
    ----------
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `frame` property.
    """
    return Property(
        identifier="frame",
        name="Frame",
        description="Frame number of the cell",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
        unit="frame",
    )


def create_time_property(
    unit: str | None,
    provenance: str = "pycellin",
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    """
    Create the declaration of the `time` core property.

    `time` is the time of the detection of the cell, expressed in `unit`.
    It is a node property of cell lineages.

    Parameters
    ----------
    unit : str or None
        Unit of the time values, e.g. "min".
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.
    custom_identifier : str, optional
        New identifier for the property. If None, the identifier will be "time".
    custom_name : str, optional
        New name for the property. If None, the name will be "Time".
    custom_description : str, optional
        New description for the property. If None, the description will be
        "Time of the detection".

    Returns
    -------
    Property
        Declaration of the `time` property.
    """
    return Property(
        identifier=custom_identifier or "time",
        name=custom_name or "Time",
        description=custom_description or "Time of the detection",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


class Time(NodeLocalPropCalculator):
    """
    Calculator for the time property.

    Attributes
    ----------
    property : Property
        Property instance containing the time property metadata.
    base_time_prop : str
        Name of the base time property to use for time calculation.
    factor : float
        Factor to multiply the base time property by to get the new time property.
    force_recompute : bool
        If True, forces the recomputation of the time property even if it already
        exists in the lineage graph. Defaults to False.

    Warnings
    --------
    As a general rule, do not use 'timepoint' as the base time property if the
    calculator is associated with the reference time property of the model. To convert
    the reference time property into another unit, use `Model.rescale_time()` instead.
    This is due to 'timepoint' being derived from the reference time property,
    meaning that at each model update the 'timepoint' property will be recomputed
    from the reference time property. This will create a circular dependency that will
    lead to incorrect time values.
    """

    def __init__(
        self,
        property: Property,
        base_time_prop: str,
        factor: float,
        force_recompute: bool = False,
    ):
        super().__init__(property)

        if factor == 0:
            raise ValueError(
                "'factor' cannot be None nor zero for time property calculation."
            )
        self.base_time_prop = base_time_prop
        self.factor = factor
        self.force_recompute = force_recompute

    def compute(self, lineage, nid: int) -> float:
        """
        Compute the time of a given node.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cell_ID) of the cell of interest.

        Returns
        -------
        float
            The computed time value for the given node.
        """
        if not self.force_recompute and self.prop.identifier in lineage.nodes[nid]:
            return lineage.nodes[nid][self.prop.identifier]

        if self.base_time_prop not in lineage.nodes[nid]:
            raise KeyError(
                f"Base time property '{self.base_time_prop}' not found "
                f"in node {nid} of lineage {lineage.graph['lineage_ID']}."
            )
        return lineage.nodes[nid][self.base_time_prop] * self.factor


def create_timepoint_property(provenance: str = "pycellin") -> Property:
    """
    Create the declaration of the `timepoint` core property.

    `timepoint` is the index of the detection along the time axis, computed by
    pycellin from the reference time property of the model and its time step.
    It is a node property of cell lineages.

    Parameters
    ----------
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `timepoint` property.
    """
    return Property(
        identifier="timepoint",
        name="Timepoint",
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
                "'time_step' cannot be None nor zero for timepoint property calculation."
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
                f"Reference time property '{self.ref_time_prop}' not found "
                f"in node {nid} of lineage {lineage.graph['lineage_ID']}."
            )

        time = lineage.nodes[nid][self.ref_time_prop]
        timepoint = (time - self.min_time) / self.time_step

        rounded_timepoint = round(timepoint)
        if not math.isclose(timepoint, rounded_timepoint, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(
                f"Computed timepoint {timepoint} for node {nid} "
                f"of lineage {lineage.graph['lineage_ID']} is not close to an integer. "
                f"Check time step and reference time values."
            )

        return rounded_timepoint


def create_cell_id_property(provenance: str = "pycellin") -> Property:
    """
    Create the declaration of the `cell_ID` core property.

    `cell_ID` is the unique identifier of the cell within its lineage. It is a
    node property of cell lineages, and is used as the node ID of `CellLineage`
    graphs.

    Parameters
    ----------
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `cell_ID` property.
    """
    return Property(
        identifier="cell_ID",
        name="Cell ID",
        description="Unique identifier of the cell",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
    )


def create_lineage_id_property(provenance: str = "pycellin") -> Property:
    """
    Create the declaration of the `lineage_ID` core property.

    `lineage_ID` is the unique identifier of the lineage. It is both a node and
    a lineage property, and is defined on cell and cycle lineages alike.

    Parameters
    ----------
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `lineage_ID` property.
    """
    return Property(
        identifier="lineage_ID",
        name="Lineage ID",
        description="Unique identifier of the lineage",
        provenance=provenance,
        prop_type=["node", "lineage"],
        lin_type="Lineage",
        dtype="int",
    )


def create_cell_coord_property(
    unit: str | None, axis: str, provenance: str = "pycellin"
) -> Property:
    """
    Create the declaration of a `cell_<axis>` core property.

    `cell_<axis>` is the coordinate of the cell along the given axis, e.g.
    `cell_x`. It is a node property of cell lineages.

    Parameters
    ----------
    unit : str or None
        Unit of the coordinates, e.g. "µm".
    axis : str
        Axis of the coordinate, e.g. "x", "y" or "z". It defines the identifier
        and the name of the property.
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `cell_<axis>` property.
    """
    return Property(
        identifier=f"cell_{axis}",
        name=f"Cell {axis}",
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
        name="Cell {axis}",
        description="{axis} coordinate of the cell",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit="space unit",
    )


def create_link_coord_property(
    unit: str, axis: str, provenance: str = "pycellin"
) -> Property:
    """
    Create the declaration of a `link_<axis>` core property.

    `link_<axis>` is the coordinate of the link along the given axis, i.e. the
    mean coordinate of the two cells it connects. It is an edge property of
    cell lineages.

    Parameters
    ----------
    unit : str
        Unit of the coordinates, e.g. "µm".
    axis : str
        Axis of the coordinate, e.g. "x", "y" or "z". It defines the identifier
        and the name of the property.
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `link_<axis>` property.
    """
    return Property(
        identifier=f"link_{axis}",
        name=f"Link {axis}",
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
        name="Link {axis}",
        description="{axis} coordinate of the link, i.e. mean coordinate of its two cells",
        provenance="pycellin",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="float",
        unit="space unit",
    )


def create_lineage_coord_property(
    unit: str, axis: str, provenance: str = "pycellin"
) -> Property:
    """
    Create the declaration of a `lineage_<axis>` core property.

    `lineage_<axis>` is the coordinate of the lineage along the given axis, i.e.
    the mean coordinate of its cells. It is a lineage property of cell lineages.

    Parameters
    ----------
    unit : str
        Unit of the coordinates, e.g. "µm".
    axis : str
        Axis of the coordinate, e.g. "x", "y" or "z". It defines the identifier
        and the name of the property.
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `lineage_<axis>` property.
    """
    return Property(
        identifier=f"lineage_{axis}",
        name=f"Lineage {axis}",
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
        name="Lineage {axis}",
        description="{axis} coordinate of the lineage, i.e. mean coordinate of its cells",
        provenance="pycellin",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="float",
        unit="space unit",
    )


def create_cycle_id_property(provenance: str = "pycellin") -> Property:
    """
    Create the declaration of the `cycle_ID` core property.

    `cycle_ID` is the unique identifier of the cell cycle, i.e. the cell_ID of
    its last cell. It is a node property of cycle lineages, and is used as the
    node ID of `CycleLineage` graphs.

    Parameters
    ----------
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `cycle_ID` property.
    """
    return Property(
        identifier="cycle_ID",
        name="Cycle ID",
        description=(
            "Unique identifier of the cell cycle, i.e. cell_ID of the last cell in the cell cycle"
        ),
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )


def create_cells_property(provenance: str = "pycellin") -> Property:
    """
    Create the declaration of the `cells` core property.

    `cells` holds the cell_IDs of the cells of the cell cycle, in chronological
    order. It is a node property of cycle lineages.

    Parameters
    ----------
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `cells` property.
    """
    return Property(
        identifier="cells",
        name="Cells",
        description="cell_IDs of the cells in the cell cycle, in chronological order",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="list[int]",
    )


def create_cycle_length_property(provenance: str = "pycellin") -> Property:
    """
    Create the declaration of the `cycle_length` core property.

    `cycle_length` is the number of cells in the cell cycle, minding gaps. It is
    a node property of cycle lineages.

    Parameters
    ----------
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `cycle_length` property.
    """
    return Property(
        identifier="cycle_length",
        name="Cycle length",
        description="Number of cells in the cell cycle, minding gaps",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )


def create_cycle_duration_property(
    time_unit: str | None, provenance: str = "pycellin"
) -> Property:
    """
    Create the declaration of the `cycle_duration` core property.

    `cycle_duration` is the duration of the cell cycle, regardless of gaps,
    expressed in `time_unit`. It is a node property of cycle lineages.

    Parameters
    ----------
    time_unit : str or None
        Unit of the duration, e.g. "min".
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `cycle_duration` property.
    """
    return Property(
        identifier="cycle_duration",
        name="Cycle duration",
        description="Duration of the cell cycle, regardless of gaps",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=time_unit,
    )


def create_level_property(provenance: str = "pycellin") -> Property:
    """
    Create the declaration of the `level` core property.

    `level` is the level of the cell cycle in the lineage, i.e. the number of
    cell cycles upstream of the current one. It is a node property of cycle
    lineages.

    Parameters
    ----------
    provenance : str, optional
        Origin of the property, e.g. the name of the format it was loaded from.
        "pycellin" by default.

    Returns
    -------
    Property
        Declaration of the `level` property.
    """
    return Property(
        identifier="level",
        name="Level",
        description=(
            "Level of the cell cycle in the lineage, "
            "i.e. number of cell cycles upstream of the current one"
        ),
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )
