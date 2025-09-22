#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pycellin.utils import get_pycellin_version


@dataclass
class ModelMetadata:
    """Metadata for a pycellin Model"""

    # Semi-required fields, used to define the model's spatial and temporal context
    space_unit: str | None
    pixel_size: dict[str, float] | None  # to split into x, y, z
    time_unit: str | None  # if None, will be set depending on time_property and props_metadata
    time_step: float | None  # if None, will be set depending on time_property and props_metadata
    time_property: str | None = "frame"

    # Standard optional fields, for traceability
    pycellin_version: str = field(default_factory=get_pycellin_version)
    creation_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    name: str | None = None
    provenance: str | None = None
    file_location: str | None = None

    # User-defined fields
    user_fields: dict[str, Any] = field(default_factory=dict)
