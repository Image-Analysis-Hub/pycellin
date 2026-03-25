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
    spatial and temporal context, as well as custom fields.

    Parameters
    ----------
    reference_time_property : str
        Name of the property used as the reference for time measurements.
        Common choices are "frame" for frame number or "time" for actual time.
        By default, all time-related operations will use this property so it must
        be present across all cells.
    time_step : int | float | None
        Time interval between consecutive time points in time_unit.
        If None, will be set depending on reference_time_property and props_metadata.
    time_unit : str | None
        Unit of time measurements (e.g., 's', 'min', 'h', 'frames').
        If None, will be set depending on reference_time_property and props_metadata.
    pixel_width : float | None
        Physical size of a pixel in the x-dimension, in space_unit.
    pixel_height : float | None
        Physical size of a pixel in the y-dimension, in space_unit.
    pixel_depth : float | None
        Physical size of a pixel in the z-dimension, in space_unit.
    space_unit : str | None
        Unit of spatial measurements (e.g., 'μm', 'nm', 'pixels').
    pycellin_version : str
        Version of pycellin used to create the model (automatically set).
    creation_timestamp : str
        ISO format timestamp of when the model was created (automatically set).
    name : str | None, default None
        Human-readable name for the model.
    provenance : str | None, default None
        Information about the origin or processing history of the data.
    file_location : str | None, default None
        Path or location where the associated data files are stored.

    Examples
    --------
    Create basic metadata:

    >>> metadata = ModelMetadata(
    ...     reference_time_property="time",
    ...     time_unit="seconds",
    ...     time_step=30.0,
    ...     space_unit="μm",
    ...     pixel_width=0.1,
    ...     pixel_height=0.1,
    ...     name="Cell Growth Analysis"
    ... )

    Add custom fields dynamically:

    >>> metadata.experiment_date = "2025-09-29"
    >>> metadata.temperature = 37.0
    >>> metadata.conditions = {"pH": 7.3, "CO2": "5%"}

    Serialize and deserialize:

    >>> data_dict = metadata.to_dict()
    >>> restored_metadata = ModelMetadata.from_dict(data_dict)
    """

    # Mandatory field.
    reference_time_property: str

    # Semi-required fields, used to define the model's spatial and temporal context.
    time_step: int | float | None = None
    time_unit: str | None = None
    pixel_width: float | None = None
    pixel_height: float | None = None
    pixel_depth: float | None = None
    space_unit: str | None = None

    # Standard optional fields, for traceability.
    pycellin_version: str = field(default_factory=get_pycellin_version)
    creation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    name: str | None = None
    provenance: str | None = None
    file_location: str | None = None

    def __post_init__(self) -> None:
        """
        Post-initialization processing for ModelMetadata.

        Handles any additional metadata validation.
        """
        # reference_time_property validation.
        if not isinstance(self.reference_time_property, str):
            raise TypeError(
                f"reference_time_property must be a string, got "
                f"{type(self.reference_time_property).__name__}"
            )
        if not self.reference_time_property:
            raise ValueError("reference_time_property cannot be an empty string.")

        # Validate that pixel dimensions are positive, if provided.
        if self.pixel_width is not None and self.pixel_width <= 0:
            raise ValueError("`pixel_width` must be positive.")
        if self.pixel_height is not None and self.pixel_height <= 0:
            raise ValueError("`pixel_height` must be positive.")
        if self.pixel_depth is not None and self.pixel_depth <= 0:
            raise ValueError("`pixel_depth` must be positive.")

    def __delattr__(self, name: str) -> None:
        """
        Prevent deletion of dataclass fields, allow deletion of dynamically added fields.

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
        object.__delattr__(self, name)

    def get_custom_metadata(self) -> dict[str, Any]:
        """
        Return a dictionary of the custom metadata (dynamically added fields).

        Returns
        -------
        dict[str, Any]
            Dictionary containing only the dynamically added fields.
        """
        dataclass_fields = set(self.__dataclass_fields__.keys())
        return {k: v for k, v in self.__dict__.items() if k not in dataclass_fields}

    def get_standard_metadata(self) -> dict[str, Any]:
        """
        Return a dictionary of the standard metadata (predefined dataclass fields).

        Returns
        -------
        dict[str, Any]
            Dictionary containing only the predefined dataclass fields.
        """
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    def get_all_metadata(self) -> dict[str, Any]:
        """
        Return a dictionary of all metadata (both predefined and dynamically added fields).

        Returns
        -------
        dict[str, Any]
            Dictionary containing all metadatafields.
        """
        return dict(self.__dict__)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for serialization (alias for get_all_metadata).

        Returns all fields (both predefined and dynamically added) in a single
        dictionary suitable for JSON serialization, database storage, etc.

        Returns
        -------
        dict[str, Any]
            Dictionary containing all metadata fields.
        """
        return self.get_all_metadata()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelMetadata":
        """
        Create ModelMetadata instance from dictionary.

        Handles both predefined fields and dynamically added fields properly.
        Unknown fields are added as dynamic attributes.

        Parameters
        ----------
        data : dict[str, Any]
            Dictionary containing metadata fields. Can include both predefined
            dataclass fields and arbitrary fields.

        Returns
        -------
        ModelMetadata
            New instance with all fields restored from the dictionary.

        Raises
        ------
        TypeError
            If data is not a dictionary.
        ValueError
            If required fields are missing from the dictionary.
        """
        # Validate input type.
        if not isinstance(data, dict):
            raise TypeError(f"data must be a dictionary, got {type(data).__name__}")

        dataclass_fields = set(cls.__dataclass_fields__.keys())
        required_fields = {
            name
            for name, field_obj in cls.__dataclass_fields__.items()
            if field_obj.default is field_obj.default_factory is None  # no default value
        }

        # Check for missing required fields.
        missing_fields = required_fields - set(data.keys())
        if missing_fields:
            raise ValueError(
                f"Missing required fields: {', '.join(sorted(missing_fields))}"
            )

        # Create instance with dataclass fields.
        init_kwargs = {k: v for k, v in data.items() if k in dataclass_fields}
        instance = cls(**init_kwargs)

        # Add custom fields as dynamic attributes.
        custom_fields = {k: v for k, v in data.items() if k not in dataclass_fields}
        for key, value in custom_fields.items():
            setattr(instance, key, value)

        return instance
