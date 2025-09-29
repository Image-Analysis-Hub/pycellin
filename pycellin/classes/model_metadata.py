#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pycellin.utils import get_pycellin_version


@dataclass
class ModelMetadata:
    """
    Metadata for a pycellin Model.

    This class holds metadata information for a pycellin model, including
    spatial and temporal context, as well as user-defined fields.

    Parameters
    ----------
    space_unit : str | None
        Unit of spatial measurements (e.g., 'μm', 'nm', 'pixels').
    pixel_width : float | None
        Physical size of a pixel in the x-dimension, in space_unit.
    pixel_height : float | None
        Physical size of a pixel in the y-dimension, in space_unit.
    pixel_depth : float | None
        Physical size of a pixel in the z-dimension, in space_unit.
    time_unit : str | None
        Unit of time measurements (e.g., 's', 'min', 'h', 'frames').
        If None, will be set depending on time_property and props_metadata.
    time_step : float | None
        Time interval between consecutive time points in time_unit.
        If None, will be set depending on time_property and props_metadata.
    time_property : str | None, default "frame"
        Name of the property representing time in the model.
    pycellin_version : str
        Version of pycellin used to create this metadata (automatically set).
    creation_timestamp : str
        ISO format timestamp of when this metadata was created (automatically set).
    name : str | None, default None
        Human-readable name for this model or experiment.
    provenance : str | None, default None
        Information about the origin or processing history of the data.
    file_location : str | None, default None
        Path or location where the associated data files are stored.

    Notes
    -----
    Dynamic Field Support:
        This class allows dynamic addition of custom fields while maintaining
        attribute-style access (instance.field_name). Dynamic fields are stored
        directly in the instance's __dict__ for maximum simplicity and performance.

        Dynamic fields can be added after instantiation using normal attribute assignment:

        >>> metadata = ModelMetadata(space_unit="μm", time_unit="s")
        >>> metadata.experiment_id = "EXP-001"
        >>> metadata.researcher = "Dr. Smith"

    Examples
    --------
    Create basic metadata:

    >>> metadata = ModelMetadata(
    ...     space_unit="μm",
    ...     pixel_width=0.1,
    ...     pixel_height=0.1,
    ...     time_unit="s",
    ...     time_step=30.0,
    ...     name="Cell Growth Analysis"
    ... )

    Add custom fields dynamically:

    >>> metadata.experiment_date = "2025-09-29"
    >>> metadata.temperature = 37.0
    >>> metadata.conditions = {"pH": 7.4, "CO2": "5%"}

    Serialize and deserialize:

    >>> data_dict = metadata.to_dict()
    >>> restored_metadata = ModelMetadata.from_dict(data_dict)
    """

    # Semi-required fields, used to define the model's spatial and temporal context
    time_unit: str | None = None

    time_step: float | None = None
    time_property: str = "frame"
    space_unit: str | None = None
    pixel_width: float | None = None
    pixel_height: float | None = None
    pixel_depth: float | None = None

    # Standard optional fields, for traceability
    pycellin_version: str = field(default_factory=get_pycellin_version)
    creation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    name: str | None = None
    provenance: str | None = None
    file_location: str | None = None

    def __delattr__(self, name: str) -> None:
        """
        Prevent deletion of dataclass fields, allow deletion of user-defined fields.

        Parameters
        ----------
        name : str
            Name of the attribute to delete.

        Raises
        ------
        AttributeError
            If attempting to delete a dataclass field.
        """
        if name in self.__dataclass_fields__:
            raise AttributeError(f"Cannot delete dataclass field '{name}'")
        super().__delattr__(name)

    def get_user_defined_metadata(self) -> dict[str, Any]:
        """
        Return a dictionary of all user-defined metadata (non-dataclass fields).

        Returns
        -------
        dict[str, Any]
            Dictionary containing only the dynamically added fields.
            Private attributes (starting with '_') are excluded.
        """
        dataclass_fields = set(self.__dataclass_fields__.keys())
        return {
            k: v
            for k, v in self.__dict__.items()
            if k not in dataclass_fields and not k.startswith("_")
        }

    def get_dataclass_metadata(self) -> dict[str, Any]:
        """
        Return a dictionary of all dataclass metadata with their current values.

        Returns
        -------
        dict[str, Any]
            Dictionary containing only the predefined dataclass fields and their values.
        """
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    def get_all_metadata(self) -> dict[str, Any]:
        """
        Return a dictionary of all metadata (both dataclass and user-defined fields).

        Returns
        -------
        dict[str, Any]
            Dictionary containing all fields except private attributes.
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns all fields (both dataclass and user-defined) in a single dictionary
        suitable for JSON serialization, database storage, etc.

        Returns
        -------
        dict[str, Any]
            Dictionary containing all metadata fields.

        Examples
        --------
        >>> metadata = ModelMetadata(space_unit="μm", time_unit="s")
        >>> metadata.experiment_id = "EXP-001"
        >>> data = metadata.to_dict()
        >>> json_string = json.dumps(data)
        """
        return self.get_all_metadata()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelMetadata":
        """
        Create ModelMetadata instance from dictionary.

        Handles both dataclass fields and user-defined fields properly.
        Unknown fields are added as dynamic attributes.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary containing metadata fields. Can include both predefined
            dataclass fields and arbitrary user-defined fields.

        Returns
        -------
        ModelMetadata
            New instance with all fields restored from the dictionary.

        Examples
        --------
        >>> data = {
        ...     'space_unit': 'μm',
        ...     'time_unit': 's',
        ...     'experiment_id': 'EXP-001',
        ...     'researcher': 'John Doe'
        ... }
        >>> metadata = ModelMetadata.from_dict(data)
        >>> print(metadata.experiment_id)  # 'EXP-001'
        """
        dataclass_fields = set(cls.__dataclass_fields__.keys())

        # Create instance with dataclass fields
        init_kwargs = {k: v for k, v in data.items() if k in dataclass_fields}
        instance = cls(**init_kwargs)

        # Add user-defined fields as dynamic attributes
        user_fields = {k: v for k, v in data.items() if k not in dataclass_fields}
        for key, value in user_fields.items():
            setattr(instance, key, value)

        return instance
