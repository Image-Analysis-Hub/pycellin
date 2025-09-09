#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import get_args
import warnings

from pycellin.custom_types import PropertyType, LineageType
from pycellin.utils import check_literal_type


class Property:
    """ """

    def __init__(
        self,
        identifier: str,
        name: str,
        description: str,
        provenance: str,
        prop_type: PropertyType,
        lin_type: LineageType,
        dtype: str,
        unit: str | None = None,
    ) -> None:
        """
        Constructs all the necessary attributes for the Property object.

        Parameters
        ----------
        identifier : str
            A unique identifier for the property.
        name : str
            A human-readable name for the property.
        description : str
            A description of the property.
        provenance : str
            The provenance of the property (TrackMate, CTC, pycellin, custom...).
        prop_type : PropertyType
            The type of the property: `node`, `edge` or `lineage.
        lin_type : LineageType
            The type of lineage the property is associated with: `CellLineage`,
            `CycleLineage`, or `Lineage` for both.
        dtype : str
            The data type of the property (int, float, string).
        unit : str, optional
            The unit of the property (e.g. µm, min, cell).

        Raises
        ------
        ValueError
            If the property type or the lineage type is not a valid value.
        """
        self.identifier = identifier
        self.name = name
        self.description = description
        self.provenance = provenance
        if not check_literal_type(prop_type, PropertyType):
            raise ValueError(f"Property type must be one of {', '.join(get_args(PropertyType))}.")
        self.prop_type = prop_type
        if not check_literal_type(lin_type, LineageType):
            raise ValueError(f"Lineage type must be one of {', '.join(get_args(LineageType))}.")
        self.lin_type = lin_type
        self.dtype = dtype
        self.unit = unit

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Property):
            return NotImplemented
        return (
            self.identifier == other.identifier
            and self.name == other.name
            and self.description == other.description
            and self.provenance == other.provenance
            and self.prop_type == other.prop_type
            and self.lin_type == other.lin_type
            and self.dtype == other.dtype
            and self.unit == other.unit
        )

    def __repr__(self) -> str:
        """
        Compute a string representation of the Property object.

        Returns
        -------
        str
            A string representation of the Property object.
        """
        return (
            f"Property(identifier={self.identifier!r}, name={self.name!r}, "
            f"description={self.description!r}, provenance={self.provenance!r}, "
            f"prop_type={self.prop_type!r}, lin_type={self.lin_type!r}, "
            f"dtype={self.dtype!r}, unit={self.unit!r})"
        )

    def __str__(self) -> str:
        """
        Compute a human-readable string representation of the Property object.

        Returns
        -------
        str
            A human-readable string representation of the Property object.
        """
        string = (
            f"Property '{self.identifier}'\n"
            f"  Name: {self.name}\n"
            f"  Description: {self.description}\n"
            f"  Provenance: {self.provenance}\n"
            f"  Type: {self.prop_type}\n"
            f"  Lineage type: {self.lin_type}\n"
            f"  Data type: {self.dtype}\n"
            f"  Unit: {self.unit}"
        )
        return string

    def _change_identifier(self, new_identifier: str) -> None:
        """
        Change the identifier of the property.

        Parameters
        ----------
        new_identifier : str
            The new identifier of the property.

        Raises
        ------
        ValueError
            If the new identifier is not a string.
        """
        if not isinstance(new_identifier, str):
            raise ValueError("Property identifier must be a string.")
        self.identifier = new_identifier

    def _change_name(self, new_name: str) -> None:
        """
        Change the name of the property.

        Parameters
        ----------
        new_name : str
            The new name of the property.

        Raises
        ------
        ValueError
            If the new name is not a string.
        """
        if not isinstance(new_name, str):
            raise ValueError("Property name must be a string.")
        self.name = new_name

    def _change_description(self, new_description: str) -> None:
        """
        Change the description of the property.

        Parameters
        ----------
        new_description : str
            The new description of the property.

        Raises
        ------
        ValueError
            If the new description is not a string.
        """
        if not isinstance(new_description, str):
            raise ValueError("Property description must be a string.")
        self.description = new_description

    def _change_provenance(self, new_provenance: str) -> None:
        """
        Change the provenance of the property.

        Parameters
        ----------
        new_provenance : str
            The new provenance of the property.

        Raises
        ------
        ValueError
            If the new provenance is not a string.
        """
        if not isinstance(new_provenance, str):
            raise ValueError("Property provenance must be a string.")
        self.provenance = new_provenance

    # Is this really needed?
    def is_equal(self, other: Property, ignore_prop_type: bool = False) -> bool:
        """
        Check if the property is equal to another property.

        Parameters
        ----------
        other : Property
            The other property to compare with.
        ignore_prop_type : bool, optional
            Whether to ignore the property type when comparing the properties.

        Returns
        -------
        bool
            True if the properties are equal, False otherwise.
        """
        if not isinstance(other, Property):
            return NotImplemented
        if ignore_prop_type:
            return (
                self.identifier == other.identifier
                and self.description == other.description
                and self.provenance == other.provenance
                and self.lin_type == other.lin_type
                and self.dtype == other.dtype
                and self.unit == other.unit
            )
        else:
            return self == other


def frame_Property(provenance: str = "pycellin") -> Property:
    prop = Property(
        identifier="frame",
        name="frame",
        description="Frame number of the cell ",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
        unit="frame",
    )
    return prop


def cell_ID_Property(provenance: str = "pycellin") -> Property:
    prop = Property(
        identifier="cell_ID",
        name="cell ID",
        description="Unique identifier of the cell",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
    )
    return prop


def lineage_ID_Property(provenance: str = "pycellin") -> Property:
    prop = Property(
        identifier="lineage_ID",
        name="lineage ID",
        description="Unique identifier of the lineage",
        provenance=provenance,
        prop_type="lineage",
        lin_type="Lineage",
        dtype="int",
    )
    return prop


def cell_coord_Property(unit: str, axis: str, provenance: str = "pycellin") -> Property:
    prop = Property(
        identifier=f"cell_{axis}",
        name=f"cell {axis}",
        description=f"{axis.upper()} coordinate of the cell",
        provenance=provenance,
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )
    return prop


def link_coord_Property(unit: str, axis: str, provenance: str = "pycellin") -> Property:
    prop = Property(
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
    return prop


def lineage_coord_Property(unit: str, axis: str, provenance: str = "pycellin") -> Property:
    prop = Property(
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
    return prop


def cycle_ID_Property(provenance: str = "pycellin") -> Property:
    prop = Property(
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
    return prop


def cells_Property(provenance: str = "pycellin") -> Property:
    prop = Property(
        identifier="cells",
        name="cells",
        description="cell_IDs of the cells in the cell cycle, in chronological order",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="list[int]",
    )
    return prop


def cycle_length_Property(provenance: str = "pycellin") -> Property:
    prop = Property(
        identifier="cycle_length",
        name="cycle length",
        description="Number of cells in the cell cycle, minding gaps",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )
    return prop


def cycle_duration_Property(provenance: str = "pycellin") -> Property:
    prop = Property(
        identifier="cycle_duration",
        name="cycle duration",
        description="Number of frames in the cell cycle, regardless of gaps",
        provenance=provenance,
        prop_type="node",
        lin_type="CycleLineage",
        dtype="int",
        unit="frame",
    )
    return prop


def level_Property(provenance: str = "pycellin") -> Property:
    prop = Property(
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
    return prop


class PropsMetadata:
    """
    The PropsMetadata class is used to store the properties that are
    associated with the nodes, edges, and lineages of cell lineage graphs.

    Attributes
    ----------
    props : dict[str, Property]
        A dictionary of properties where the keys are the property identifiers and
        the values are the Property objects.
    protected_props : list[str]
        A list of property identifiers that are protected from being modified or removed.

    Notes
    -----
    Spatial and temporal units are not part of the PropsMetadata but of the
    properties themselves to allow different units for a same dimension (e.g. time
    in seconds or minutes).
    """

    def __init__(
        self,
        props: dict[str, Property] | None = None,
        protected_props: list[str] | None = None,
    ) -> None:
        self.props = props if props is not None else {}
        self._protected_props = protected_props if protected_props is not None else []
        for prop in self._protected_props:
            if prop not in self.props:
                msg = (
                    f"Protected property '{prop}' does not exist in the declared "
                    "properties. Removing it from the list of protected properties."
                )
                warnings.warn(msg)
                self._protected_props.remove(prop)

    def __eq__(self, other):
        if not isinstance(other, PropsMetadata):
            return False
        return self.props == other.props

    def __repr__(self) -> str:
        """
        Compute a string representation of the PropsMetadata object.

        Returns
        -------
        str
            A string representation of the PropsMetadata object.
        """
        return f"PropsMetadata(props={self.props!r})"

    def __str__(self) -> str:
        """
        Compute a human-readable str representation of the PropsMetadata object.

        Returns
        -------
        str
            A human-readable string representation of the PropsMetadata object.
        """
        node_props = ", ".join(self._get_prop_dict_from_prop_type("node").keys())
        edge_props = ", ".join(self._get_prop_dict_from_prop_type("edge").keys())
        lin_props = ", ".join(self._get_prop_dict_from_prop_type("lineage").keys())
        return (
            f"Node properties: {node_props}\n"
            f"Edge properties: {edge_props}\n"
            f"Lineage properties: {lin_props}"
        )

    def _has_prop(
        self,
        prop_id: str,
    ) -> bool:
        """
        Check if the PropsMetadata contains the specified property.

        Parameters
        ----------
        prop_id : str
            The identifier of the property to check.

        Returns
        -------
        bool
            True if the property has been declared, False otherwise.
        """
        if prop_id in self.props:
            return True
        else:
            return False

    def _get_prop_dict_from_prop_type(self, prop_type: PropertyType) -> dict:
        """
        Return the dictionary of properties corresponding to the specified type.

        Parameters
        ----------
        prop_type : PropertyType
            The type of the properties to return (node, edge, or lineage).

        Returns
        -------
        dict
            The dictionary of properties corresponding to the specified type.

        Raises
        ------
        ValueError
            If the property type is invalid.
        """
        if not check_literal_type(prop_type, PropertyType):
            raise ValueError(f"Property type must be one of {', '.join(get_args(PropertyType))}.")
        props = {k: v for k, v in self.props.items() if prop_type == v.prop_type}
        return props

    def _get_prop_dict_from_lin_type(self, lin_type: LineageType) -> dict:
        """
        Return the dictionary of properties corresponding to the specified lineage type.

        Parameters
        ----------
        lin_type : LineageType
            The type of the lineage properties to return (CellLineage,
            CycleLineage or Lineage).

        Returns
        -------
        dict
            The dictionary of properties corresponding to the specified lineage type.

        Raises
        ------
        ValueError
            If the lineage type is invalid.
        """
        if not check_literal_type(lin_type, LineageType):
            raise ValueError(f"Lineage type must be one of {', '.join(get_args(LineageType))}.")
        props = {k: v for k, v in self.props.items() if lin_type == v.lin_type}
        return props

    def _get_protected_props(self) -> list[str]:
        """
        Return the list of protected properties.

        Returns
        -------
        list[str]
            The list of protected properties.
        """
        return self._protected_props

    def _add_prop(self, property: Property, overwrite: bool = False) -> None:
        """
        Add the specified property to the PropsMetadata.

        Parameters
        ----------
        property : Property
            The property to add.
        overwrite : bool, optional
            Whether to overwrite an existing property with the same identifier.
            If False (default), existing properties will not be overwritten but a
            warning will be issued. If True, existing properties will be overwritten.

        Warns
        -----
        UserWarning
            If a property with the same identifier already exists and overwrite=True.
            The existing property will be overwritten.
        UserWarning
            If a property with the same identifier already exists and overwrite=False.
            The existing property will NOT be overwritten.
        """
        if property.identifier in self.props:
            old_prop = self.props[property.identifier]
            if property.prop_type == old_prop.prop_type:
                txt = "with the same type"
            else:
                txt = "with a different type"

            if overwrite:
                msg = f"A Property '{property.identifier}' already exists {txt}. Overwriting the old Property."
                warnings.warn(msg, stacklevel=2)
                self.props[property.identifier] = property
            else:
                msg = f"A Property '{property.identifier}' already exists {txt}. Not overwriting the old Property."
                warnings.warn(msg, stacklevel=2)
        else:
            self.props[property.identifier] = property

    def _add_props(
        self,
        properties: list[Property],
        overwrite: bool = False,
    ) -> None:
        """
        Add the specified properties to the PropsMetadata.

        Parameters
        ----------
        properties : list[Property]
            The properties to add.
        overwrite : bool, optional
            Whether to overwrite existing properties with the same identifier.
            If False (default), existing properties will not be overwritten but a
            warning will be issued. If True, existing properties will be overwritten.
        """
        for property in properties:
            self._add_prop(property, overwrite=overwrite)

    def _add_cycle_lineage_props(self) -> None:
        """
        Add the basic properties of cell cycle lineages.
        """
        prop_ID = cycle_ID_Property()
        prop_cells = cells_Property()
        prop_length = cycle_length_Property()
        prop_duration = cycle_duration_Property()
        prop_level = level_Property()
        for prop in [prop_ID, prop_cells, prop_length, prop_duration, prop_level]:
            if prop.identifier not in self.props:
                self._add_prop(prop)
                self._protect_prop(prop.identifier)

    def _remove_prop(
        self,
        prop_id: str,
    ) -> None:
        """
        Remove the specified property from the PropsMetadata.

        Parameters
        ----------
        prop_id : str
            The identifier of the property to remove.

        Raises
        ------
        ValueError
            If the property type is invalid.
        UserWarning
            If the property is protected and cannot be removed.
        """
        if prop_id not in self.props:
            raise KeyError(f"Property '{prop_id}' does not exist in the declared properties.")
        if prop_id in self._protected_props:
            msg = (
                f"Property '{prop_id}' is protected and cannot be removed. "
                "Unprotect the property before modifying it."
            )
            warnings.warn(msg)
        else:
            del self.props[prop_id]

    def _remove_props(
        self,
        prop_ids: list[str],
    ) -> None:
        """
        Remove the specified properties from the PropsMetadata.

        Parameters
        ----------
        prop_ids : list[str]
            The identifiers of the properties to remove.
        """
        for prop_id in prop_ids:
            self._remove_prop(prop_id)

    def _change_prop_identifier(
        self,
        prop_id: str,
        new_id: str,
    ) -> None:
        """
        Change the identifier of a specified property.

        Parameters
        ----------
        prop_id : str
            The current identifier of the property.
        new_id : str
            The new identifier for the property.

        Raises
        ------
        KeyError
            If the property does not exist in the declared properties.
        UserWarning
            If the property is protected and cannot be modified.
        """
        if prop_id not in self.props:
            raise KeyError(f"Property '{prop_id}' does not exist in the declared properties.")
        if prop_id in self._protected_props:
            msg = (
                f"Property '{prop_id}' is protected and cannot be modified. "
                "Unprotect the property before modifying it."
            )
            warnings.warn(msg)
        else:
            self.props[new_id] = self.props.pop(prop_id)
            self.props[new_id]._change_identifier(new_id)

    def _change_prop_name(self, prop_id: str, new_name: str) -> None:
        """
        Change the name of a specified property.

        Parameters
        ----------
        prop_id : str
            The identifier of the property whose name is to be changed.
        new_name : str
            The new name for the property.
        """
        if prop_id not in self.props:
            raise KeyError(f"Property '{prop_id}' does not exist in the declared properties.")
        if prop_id in self._protected_props:
            msg = (
                f"Property '{prop_id}' is protected and cannot be modified. "
                "Unprotect the property before modifying it."
            )
            warnings.warn(msg)
        else:
            self.props[prop_id]._change_name(new_name)

    def _change_prop_description(
        self,
        prop_id: str,
        new_description: str,
    ) -> None:
        """
        Change the description of a specified property.

        Parameters
        ----------
        prop_id : str
            The identifier of the property whose description is to be changed.
        new_description : str
            The new description for the property.

        Raises
        ------
        KeyError
            If the property does not exist in the declared properties.
        UserWarning
            If the property is protected and cannot be modified
            (i.e. it is in the list of protected properties).
        """
        if prop_id not in self.props:
            raise KeyError(f"Property '{prop_id}' does not exist in the declared properties.")
        if prop_id in self._protected_props:
            msg = (
                f"Property '{prop_id}' is protected and cannot be modified. "
                "Unprotect the property before modifying it."
            )
            warnings.warn(msg)
        else:
            self.props[prop_id]._change_description(new_description)

    def _protect_prop(self, prop_id: str) -> None:
        """
        Protect the specified property from being modified or removed.

        Parameters
        ----------
        prop_id : str
            The identifier of the property to protect.

        Raises
        ------
        UserWarning
            If the property does not exist in the declared properties.
        """
        if prop_id not in self.props:
            msg = (
                f"Property '{prop_id}' does not exist in the declared properties "
                "and cannot be protected."
            )
            warnings.warn(msg)

        if prop_id not in self._protected_props:
            self._protected_props.append(prop_id)

    def _unprotect_prop(self, prop_id: str) -> None:
        """
        Unprotect the specified property.

        Parameters
        ----------
        prop_id : str
            The identifier of the property to unprotect.

        Raises
        ------
        UserWarning
            If the property does not exist in the declared properties.
        """
        if prop_id not in self.props:
            msg = (
                f"Property '{prop_id}' does not exist in the declared properties "
                "and cannot be unprotected."
            )
            warnings.warn(msg)

        if prop_id in self._protected_props:
            self._protected_props.remove(prop_id)

    def _get_units_per_props(self) -> dict[str, list[str]]:
        """
        Return a dict of units and the properties associated with each unit.

        The method iterates over the node, edge, and lineage properties
        of the properties declaration object, grouping them by unit.

        Returns
        -------
        dict[str, list[str]]
            A dictionary where the keys are units and the values are lists
            of property identifiers. For example:
            {'unit1': ['property1', 'property2'], 'unit2': ['property3']}.
        """
        units = {}  # type: dict[str, list[str]]
        for prop in self.props.values():
            if prop.unit in units:
                units[prop.unit].append(prop.identifier)
            else:
                units[prop.unit] = [prop.identifier]
        return units


if __name__ == "__main__":
    # Basic testing of the Property and PropsMetadata classes.
    # TODO: do this properly in test_property.py.

    # Add properties
    pmd = PropsMetadata()
    pmd._add_prop(cell_ID_Property())
    pmd._add_props(
        [
            frame_Property(),
            lineage_ID_Property(),
        ]
    )
    # for k, v in pmd.props.items():
    #     print(k, v)

    # Add identical property
    pmd._add_prop(cell_ID_Property())
    print()

    # Add different type property
    tmp_prop = cell_ID_Property()
    tmp_prop.prop_type = "edge"
    print(tmp_prop)
    pmd._add_prop(tmp_prop)
    print(pmd.props["cell_ID"])

    # Add different definition property
    tmp_prop = cell_ID_Property()
    tmp_prop.description = "new description"
    pmd._add_prop(tmp_prop)
    print(pmd.props["cell_ID"])

    # Get props dict
    # print(pmd.get_node_props().keys())
    # print(pmd.get_edge_props().keys())
    # print(pmd.get_lin_props().keys())

    # Remove prop
    pmd._remove_prop("frame")
    # print(pmd.props.keys())

    # Remove prop with type
    pmd._remove_prop("lineage_ID")
    # for k, v in pmd.props.items():
    #     print(k, v)

    # Remove prop with type, but last type so in fact remove prop
    pmd._remove_prop("lineage_ID")
    # print(pmd.props.keys())

    # Remove prop with multi type
    pmd._add_prop(lineage_ID_Property())
    pmd._remove_prop("lineage_ID")
    # print(pmd.props.keys())

    # Invalid prop name
    # pmd._remove_property("cel_ID")

    # Invalid prop type
    # pmd._remove_property("cell_ID", "nod")

    # Rename property
    pmd._change_prop_identifier("cell_ID", "cell_ID_new")
    # print(pmd.props.keys(), pmd.props["cell_ID_new"].name)

    # Modify description
    pmd._change_prop_description("cell_ID_new", "New description")
    # print(pmd.props["cell_ID_new"])

    print(cell_ID_Property().is_equal(cell_ID_Property()))
    print(cell_ID_Property().is_equal(lineage_ID_Property()))
