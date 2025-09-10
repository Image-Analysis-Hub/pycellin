#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# from __future__ import annotations

from typing import get_args

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
    def is_equal(self, other: "Property", ignore_prop_type: bool = False) -> bool:
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
