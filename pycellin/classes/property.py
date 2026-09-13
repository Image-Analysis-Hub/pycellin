#!/usr/bin/env python3

from typing import Any, get_args

from pycellin.custom_types import (
    LineageType,
    PropertyType,
    property_type_from_string,
    property_type_to_strings,
)
from pycellin.utils import _normalize_dtype, check_literal_type

# Unit and data type of properties whose declaration is unknown (e.g. TrackMate stubs).
_UNKNOWN = "unknown"


class Property:
    """ """

    def __init__(
        self,
        identifier: str,
        name: str,
        description: str,
        provenance: str,
        prop_type: PropertyType | str | list[str],
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
        prop_type : PropertyType or str or list[str]
            The type of the property. Can be:
            - PropertyType Flag: PropertyType.NODE, PropertyType.EDGE, PropertyType.LINEAGE,
            or combinations like PropertyType.NODE | PropertyType.EDGE.
            - String: "node", "edge", or "lineage"
            - List of strings: ["node", "lineage"] for multi-type properties
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

        # Convert string/list to PropertyType Flag if needed.
        if isinstance(prop_type, (str, list)):
            prop_type = property_type_from_string(prop_type)

        # Validate PropertyType.
        if not isinstance(prop_type, PropertyType) or prop_type == PropertyType(0):
            raise ValueError(
                "Property type must be a valid PropertyType Flag with at least one flag set. "
                "Valid types: PropertyType.NODE, PropertyType.EDGE, PropertyType.LINEAGE, "
                "or combinations like PropertyType.NODE | PropertyType.EDGE, and "
                "strings/lists: 'node', 'edge', 'lineage', ['node', 'lineage']."
            )
        self.prop_type = prop_type

        if not check_literal_type(lin_type, LineageType):
            raise ValueError(
                f"Lineage type must be one of {', '.join(get_args(LineageType))}."
            )
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

    def get_incompatibilities(self, other: "Property") -> dict[str, tuple[Any, Any]]:
        """
        Return the declaration fields that are incompatible with another property.

        Two properties are compatible when they have the same property type, lineage
        type, unit and data type. Data types are compared after normalizing their
        spelling (e.g. "float" and "float64", "str" and "string"). An "unknown" unit or
        data type is compatible with any value. Name, description and provenance are
        not compared.

        Parameters
        ----------
        other : Property
            The property to compare with.

        Returns
        -------
        dict[str, tuple[Any, Any]]
            The incompatible fields, with (value in this property, value in the other
            property) tuples as values. Empty if the properties are compatible.
        """
        incompatibilities = {
            field: (getattr(self, field), getattr(other, field))
            for field in ("prop_type", "lin_type")
            if getattr(self, field) != getattr(other, field)
        }
        if _UNKNOWN not in (self.unit, other.unit) and self.unit != other.unit:
            incompatibilities["unit"] = (self.unit, other.unit)
        dtypes = (_normalize_dtype(self.dtype), _normalize_dtype(other.dtype))
        if _UNKNOWN not in (self.dtype, other.dtype) and dtypes[0] != dtypes[1]:
            incompatibilities["dtype"] = (self.dtype, other.dtype)
        return incompatibilities

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
            f"  Type: {property_type_to_strings(self.prop_type)}\n"
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
