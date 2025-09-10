#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import get_args
import warnings

from pycellin.custom_types import PropertyType, LineageType
from pycellin.utils import check_literal_type
from .property import Property


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
        # Import property functions - no circular dependency since PropsMetadata is now separate
        from pycellin.graph.properties.core import (
            create_cycle_id_property,
            create_cells_property,
            create_cycle_length_property,
            create_cycle_duration_property,
            create_level_property,
        )

        prop_ID = create_cycle_id_property()
        prop_cells = create_cells_property()
        prop_length = create_cycle_length_property()
        prop_duration = create_cycle_duration_property()
        prop_level = create_level_property()
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

    def _get_units_per_props(self) -> dict[str | None, list[str]]:
        """
        Return a dict of units and the properties associated with each unit.

        The method iterates over the node, edge, and lineage properties
        of the properties declaration object, grouping them by unit.

        Returns
        -------
        dict[str | None, list[str]]
            A dictionary where the keys are units (or None for unitless properties)
            and the values are lists of property identifiers. For example:
            {'unit1': ['property1', 'property2'], 'unit2': ['property3'], None: ['property4']}.
        """
        units = {}  # type: dict[str | None, list[str]]
        for prop in self.props.values():
            if prop.unit in units:
                units[prop.unit].append(prop.identifier)
            else:
                units[prop.unit] = [prop.identifier]
        return units
