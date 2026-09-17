#!/usr/bin/env python3

"""
Declarations of the properties pycellin can attach to lineages.

The factories exported here build the `Property` declarations of pycellin core
properties: the ones loaders create, and the ones you need to declare yourself
when building a `Model` from scratch or writing a loader for a new format.

Every other pycellin property (morphology, motion, topology, tracking) is added
through its dedicated `Model.add_<identifier>()` method, which builds the
declaration and registers the matching calculator in one step. Use
`get_pycellin_cell_lineage_properties()` and
`get_pycellin_cycle_lineage_properties()` to list them.
"""

from .core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_cells_property,
    create_cycle_duration_property,
    create_cycle_id_property,
    create_cycle_length_property,
    create_frame_property,
    create_level_property,
    create_lineage_coord_property,
    create_lineage_id_property,
    create_link_coord_property,
    create_time_property,
    create_timepoint_property,
)
from .utils import (
    get_pycellin_cell_lineage_properties,
    get_pycellin_cycle_lineage_properties,
)

__all__ = [
    "create_cell_coord_property",
    "create_cell_id_property",
    "create_cells_property",
    "create_cycle_duration_property",
    "create_cycle_id_property",
    "create_cycle_length_property",
    "create_frame_property",
    "create_level_property",
    "create_lineage_coord_property",
    "create_lineage_id_property",
    "create_link_coord_property",
    "create_time_property",
    "create_timepoint_property",
    "get_pycellin_cell_lineage_properties",
    "get_pycellin_cycle_lineage_properties",
]
