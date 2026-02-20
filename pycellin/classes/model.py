#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pickle
import warnings
from decimal import Decimal
from itertools import pairwise
from math import gcd
from typing import Any, Callable, Literal, TypeVar

import networkx as nx
import pandas as pd

import pycellin.graph.properties.morphology as morpho
import pycellin.graph.properties.motion as motion
import pycellin.graph.properties.tracking as tracking
import pycellin.graph.properties.utils as futils
from pycellin.classes.data import Data
from pycellin.classes.exceptions import FusionError, ProtectedPropertyError
from pycellin.classes.lineage import CellLineage, CycleLineage, Lineage
from pycellin.classes.model_metadata import ModelMetadata
from pycellin.classes.property import Property
from pycellin.classes.property_calculator import PropertyCalculator
from pycellin.classes.props_metadata import PropsMetadata
from pycellin.classes.updater import ModelUpdater
from pycellin.custom_types import Cell, Link
from pycellin.graph.properties.core import Timepoint, create_timepoint_property

L = TypeVar("L", bound="Lineage")


class Model:
    """ """

    def __init__(
        self,
        model_metadata: ModelMetadata | dict[str, Any] | None = None,
        props_metadata: PropsMetadata | None = None,
        data: Data | None = None,
        reference_time_property: str | None = None,
        variable_time_step: bool = False,
    ) -> None:
        """
        Constructs all the necessary attributes for the Model object.

        Parameters
        ----------
        model_metadata : ModelMetadata | dict[str, Any] | None, optional
            Metadata of the model (default is None).
        props_metadata : PropsMetadata, optional
            The declaration of the properties present in the model (default is None).
        data : Data, optional
            The lineages data of the model (default is None).
        reference_time_property : str, optional
            The name of the property to use as the reference for time measurements.
            Needs to be provided if model_metadata is None or does not contain it.
        variable_time_step : bool, optional
            If True and time_step is not provided in model_metadata, the time step
            will be computed using the greatest common divisor (GCD) of time
            differences, which is suitable for irregularly sampled timepoints.
            If False, the minimum time difference is used instead (default is False).
            This parameter is only used when time_step needs to be automatically
            computed from the data.

        Raises
        ------
        ValueError
            If `reference_time_property` is not provided and cannot be inferred from
            `model_metadata`.
        TypeError
            If `model_metadata` is not None, ModelMetadata, or dict.

        Warns
        -----
        UserWarning
            If `time_step` is not provided in `model_metadata` and cannot be inferred
            from the data.
        """
        # Check that we have a reference_time_property.
        if reference_time_property is None:
            if model_metadata is None:
                raise ValueError("`reference_time_property` must be provided.")

            # Extract from metadata regardless of type.
            if isinstance(model_metadata, dict):
                reference_time_property = model_metadata.get("reference_time_property")
            else:
                reference_time_property = getattr(
                    model_metadata, "reference_time_property", None
                )

            if not reference_time_property:
                raise ValueError(
                    "`reference_time_property` must be provided in model_metadata "
                    "or as an explicit argument."
                )
        self.reference_time_property = reference_time_property

        # Initialize data early since _compute_time_step() needs it.
        self.data = data.copy() if data is not None else Data(dict())

        # Do we already have a time_step?
        if model_metadata is not None:
            if isinstance(model_metadata, dict):
                time_step = model_metadata.get("time_step")
            else:
                time_step = getattr(model_metadata, "time_step", None)
        else:
            time_step = None

        # Determine time_step if not provided in metadata.
        if time_step is None:
            if self.data.cell_data:
                # Create temporary metadata for _compute_time_step().
                temp_metadata = ModelMetadata(
                    reference_time_property=reference_time_property
                )
                self.model_metadata = temp_metadata
                time_step = self._compute_time_step(variable_time_step)
            else:
                msg = (
                    "`time_step` is not defined in model metadata and there is no data "
                    "in the model to infer it. Set the time_step manually with "
                    "`model.set_time_step(your_timestep)`. Alternatively, you can set it "
                    "automatically with `model.set_time_step()` once you have added data "
                    "to the model."
                )
                warnings.warn(msg, UserWarning, stacklevel=2)

        # Create final model metadata with all required values.
        # TODO: add unit extracted from props_metadata, if any
        if model_metadata is None:
            self.model_metadata = ModelMetadata(
                reference_time_property=reference_time_property, time_step=time_step
            )
        elif isinstance(model_metadata, ModelMetadata):
            metadata_dict = model_metadata.to_dict()  # to avoid mutating the original
            metadata_dict["reference_time_property"] = reference_time_property
            metadata_dict["time_step"] = time_step
            self.model_metadata = ModelMetadata.from_dict(metadata_dict)
        elif isinstance(model_metadata, dict):
            metadata_dict = model_metadata.copy()  # to avoid mutating the original
            metadata_dict["reference_time_property"] = reference_time_property
            metadata_dict["time_step"] = time_step
            self.model_metadata = ModelMetadata.from_dict(metadata_dict)
        else:
            raise TypeError(
                f"`model_metadata` must be None, ModelMetadata, or dict, "
                f"got `{type(model_metadata).__name__}`."
            )

        # Set the rest of the attributes.
        self.props_metadata = (
            props_metadata.copy() if props_metadata is not None else PropsMetadata()
        )
        self._updater = ModelUpdater()

        # Update to actually compute the "timepoint" property.
        if self.data.cell_data and "timepoint" not in self.get_node_properties():
            self.add_custom_property(
                Timepoint(
                    property=create_timepoint_property(),
                    data=self.data,
                    time_step=self.model_metadata.time_step,
                    reference_time_property=self.model_metadata.reference_time_property,
                )
            )
            self.props_metadata._protect_prop("timepoint")
            self.update(["timepoint"])

        # Add an optional argument to ask to compute the CycleLineage?
        # Should name be optional or set to None? If optional and not provided, an
        # error will be raised when trying to access the attribute.
        # Same for provenance, description, etc.

    def __repr__(self) -> str:
        return (
            f"Model(model_metadata={self.model_metadata!r}, "
            f"props_metadata={self.props_metadata!r}, "
            f"data={self.data!r})"
        )

    def __str__(self) -> str:
        if self.model_metadata and self.data:
            nb_lin = self.data.number_of_lineages()
            if (
                hasattr(self.model_metadata, "name")
                and self.model_metadata.name
                and hasattr(self.model_metadata, "provenance")
                and self.model_metadata.provenance
            ):
                txt = (
                    f"Model named '{self.model_metadata.name}' "
                    f"with {nb_lin} lineage{'s' if nb_lin > 1 else ''}, "
                    f"built from {self.model_metadata.provenance}."
                )
            elif hasattr(self.model_metadata, "name") and self.model_metadata.name:
                txt = (
                    f"Model named '{self.model_metadata.name}' "
                    f"with {nb_lin} lineage{'s' if nb_lin > 1 else ''}."
                )
            elif (
                hasattr(self.model_metadata, "provenance")
                and self.model_metadata.provenance
            ):
                txt = (
                    f"Model with {nb_lin} lineage{'s' if nb_lin > 1 else ''}, "
                    f"built from {self.model_metadata.provenance}."
                )
            else:
                txt = f"Model with {nb_lin} lineage{'s' if nb_lin > 1 else ''}."
        elif self.data:
            nb_lin = self.data.number_of_lineages()
            txt = f"Model with {nb_lin} lineage{'s' if nb_lin > 1 else ''}."
        elif self.model_metadata:
            if (
                hasattr(self.model_metadata, "name")
                and self.model_metadata.name
                and hasattr(self.model_metadata, "provenance")
                and self.model_metadata.provenance
            ):
                txt = (
                    f"Model named '{self.model_metadata.name}' "
                    f"built from {self.model_metadata.provenance}."
                )
            elif hasattr(self.model_metadata, "name") and self.model_metadata.name:
                txt = f"Model named '{self.model_metadata.name}'."
            elif (
                hasattr(self.model_metadata, "provenance")
                and self.model_metadata.provenance
            ):
                txt = f"Model built from {self.model_metadata.provenance}."
            else:
                txt = "Empty model."
        else:
            txt = "Empty model."
        return txt

    def __getstate__(self) -> dict[str, Any]:
        """
        Custom pickle state preparation.

        Converts ModelMetadata to dictionary format for serialization.
        This ensures that ModelMetadata with dynamic fields is properly serialized.

        Returns
        -------
        dict[str, Any]
            State dictionary for pickling.
        """
        state = self.__dict__.copy()
        # Convert ModelMetadata to dict for pickling
        if hasattr(self, "model_metadata") and self.model_metadata is not None:
            state["model_metadata"] = self.model_metadata.to_dict()
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """
        Custom pickle state restoration.

        Converts dictionary back to ModelMetadata instance during deserialization.
        This ensures that ModelMetadata with dynamic fields is properly restored.

        Parameters
        ----------
        state : dict[str, Any]
            State dictionary from pickling.
        """
        # Restore ModelMetadata from dict
        if "model_metadata" in state and isinstance(state["model_metadata"], dict):
            state["model_metadata"] = ModelMetadata.from_dict(state["model_metadata"])
        self.__dict__.update(state)

    def _compute_time_step(self, variable_time_step: bool = False) -> int | float:
        """
        Compute the time step of the model based on the reference time property.

        By default, the time step is calculated as the minimum difference between
        consecutive timepoints across all lineages.
        If the timepoints are irregularly sampled, i.e. not evenly spaced regardless of gaps,
        `variable_time_step` should be set to True. In this case, the greatest common divisor (GCD)
        of the differences is used instead. However, this method is more computationally intensive
        and should be used only when necessary.

        Parameters
        ----------
        variable_time_step : bool, optional
            If True, the time step is computed using the GCD of time differences.
            If False, the minimum time difference is used (default is False).

        Returns
        -------
        int | float
            The computed time step of the model.

        Raises
        ------
        ValueError
            If no lineages are found in the model data.
            If no valid time intervals are found (e.g., all nodes have the same timepoint).
            If reference_time_property is not found in lineage nodes.

        Examples
        --------
        Regular time sampling (variable_time_step=False):
        >>> # Time differences: [1, 1, 1, 1] → time_step = 1 (minimum)
        >>> model._compute_time_step(variable_time_step=False)
        1

        Regular time sampling with consistent base interval but gaps (variable_time_step=False):
        >>> # Time differences: [1, 2, 1, 3] → time_step = 1 (minimum)
        >>> model._compute_time_step(variable_time_step=False)
        1

        Regular time sampling with consistent float interval but gaps (variable_time_step=False):
        >>> # Time differences: [1.5, 3.0, 1.5] → time_step = 1.5 (minimum)
        >>> model._compute_time_step(variable_time_step=False)
        1.5

        Irregular time sampling (variable_time_step=True):
        >>> # Time differences: [1.5, 3.0, 1.1, 0.3] → time_step = 0.1 (GCD)
        >>> model._compute_time_step(variable_time_step=True)
        0.1
        >>> # Default minimum time difference yields incorrect result:
        >>> model._compute_time_step(variable_time_step=False)
        0.3

        Negative timepoints are supported in all cases:
        >>> # Timepoints like [-5, -3, -1, 0, 2] (regular intervals with negatives)
        >>> # Time differences: [2, 2, 1, 2] → time_step = 1 (minimum)
        >>> model._compute_time_step(variable_time_step=False)
        1
        >>> # Timepoints like [-5, -2, 0, 1.5] (irregular intervals with negatives)
        >>> # Time differences: [3, 2, 1.5] → time_step = 0.5 (GCD)
        >>> model._compute_time_step(variable_time_step=True)
        0.5

        When to use variable_time_step=False:
        - Regular timepoints like [0, 1, 2, 3, 4] (classic case)
        - Timepoints like [0, 1, 3, 4, 5, 7] (some gaps but consistent unit steps)
        - Timepoints like [0, 1.5, 3.0, 4.5] (non-integer but regular intervals)
        - Timepoints like [0, 1, 1.5, 2.5, 4] (non-integer and gaps but regular intervals)

        When to use variable_time_step=True:
        - Timepoints like [0, 1, 2.5, 3.5] (non-integer and gaps but no regular intervals)
          => cannot reach all timepoints by adding a fixed step of 1 from the minimum,
             we need a smaller step to reach all timepoints (0.5 in this case)
        - Timepoints like [0, 1.1, 2.5, 2.8] (non-integer and irregular intervals)
        - Timepoints like [0, 1.1, 3.42, 4.0, 7.61] (completely random intervals)
        """
        # TODO: Should time_step be recomputed when doing an update?
        lineages = self.data.cell_data.values()
        if not lineages:
            raise ValueError("Cannot compute time step: no lineages found.")

        time_diffs = set()
        time_prop = self.model_metadata.reference_time_property
        for lin in lineages:
            for source_node, target_node in lin.edges():
                if time_prop not in lin.nodes[source_node]:
                    raise ValueError(
                        f"Reference time property '{time_prop}' not found in node {source_node} "
                        f"of lineage {lin.graph.get('lineage_ID', 'of unknown ID')}."
                    )
                source_time = lin.nodes[source_node][time_prop]
                if time_prop not in lin.nodes[target_node]:
                    raise ValueError(
                        f"Reference time property '{time_prop}' not found in node {target_node} "
                        f"of lineage {lin.graph.get('lineage_ID', 'of unknown ID')}."
                    )
                target_time = lin.nodes[target_node][time_prop]
                time_diff = abs(target_time - source_time)
                if time_diff > 0:
                    time_diffs.add(time_diff)

        if not time_diffs:
            raise ValueError("Cannot compute time step: no valid time intervals found.")

        time_step: int | float
        if variable_time_step:  # use GCD of all time differences
            # TODO: extract EPSILON as a constant
            EPSILON = 1e-12
            if all(abs(td - round(td)) < EPSILON for td in time_diffs):
                # Treat numbers like 2.0000001 as integers for more efficient GCD calculation
                time_step = gcd(*map(int, map(round, time_diffs)))
            else:
                time_step = self._gcd_floats(time_diffs)
        else:  # use minimum time difference
            time_step = min(time_diffs)

        return time_step

    def set_time_step(
        self,
        time_step: int | float | None = None,
        variable_time_step: bool = False,
    ) -> None:
        """
        Set the time step of the model.

        Parameters
        ----------
        time_step : int | float | None
            The time step to set for the model. If None, the time step will be
            computed automatically based on the data in the model (default is None).
        variable_time_step : bool, optional
            If True and time_step is None, the time step will be computed using
            the GCD of time differences. If False, the minimum time difference
            will be used (default is False).

        # TODO: should I copy the docstring examples from _compute_time_step() here?
        """
        if time_step is None:
            time_step = self._compute_time_step(variable_time_step)
        self.model_metadata.time_step = time_step

    @staticmethod
    def _gcd_floats(values: set[float]) -> float:
        """
        Calculate GCD for floating point numbers using exact decimal precision.

        This method converts floats to Decimals to avoid precision issues,
        scales them to integers, computes the GCD, and then rescales back to float.

        Parameters
        ----------
        values : set[float]
            Set of floating point numbers to compute the GCD for.

        Returns
        -------
        float
            The GCD of the input floating point numbers.
        """
        # Convert to Decimal for exact precision handling.
        # The str() conversion is to avoid precision issues with floats.
        decimal_values = list(map(Decimal, map(str, values)))

        # Find the maximum number of decimal places among all values
        max_decimal_places = 0
        for d in decimal_values:
            exponent = d.as_tuple().exponent
            if isinstance(exponent, int) and exponent < 0:
                max_decimal_places = max(max_decimal_places, abs(exponent))

        # Scale all values to integers
        scale_factor = 10**max_decimal_places
        int_values = [int(d * scale_factor) for d in decimal_values]
        result_scaled = gcd(*int_values)

        return float(result_scaled / scale_factor)

    def get_space_unit(self) -> str | None:
        """
        Return the spatial unit of the model.

        Returns
        -------
        str
            The spatial unit of the model.
        """
        return self.model_metadata.space_unit

    def get_pixel_width(self) -> float | None:
        """
        Return the pixel width of the model.

        Returns
        -------
        float
            The pixel width of the model.
        """
        return self.model_metadata.pixel_width

    def get_pixel_height(self) -> float | None:
        """
        Return the pixel height of the model.

        Returns
        -------
        float
            The pixel height of the model.
        """
        return self.model_metadata.pixel_height

    def get_pixel_depth(self) -> float | None:
        """
        Return the pixel depth of the model.

        Returns
        -------
        float
            The pixel depth of the model.
        """
        return self.model_metadata.pixel_depth

    def get_pixel_size(self) -> dict[str, float] | None:
        """
        Return the pixel size of the model.

        Returns
        -------
        dict[str, float]
            The pixel size of the model as a dictionary with 'width', 'height', and 'depth' keys.
            Returns None if no pixel sizes are defined.
        """
        pixel_size = {}
        if self.model_metadata.pixel_width is not None:
            pixel_size["width"] = self.model_metadata.pixel_width
        if self.model_metadata.pixel_height is not None:
            pixel_size["height"] = self.model_metadata.pixel_height
        if self.model_metadata.pixel_depth is not None:
            pixel_size["depth"] = self.model_metadata.pixel_depth

        return pixel_size if pixel_size else None

    def get_time_unit(self) -> str | None:
        """
        Return the temporal unit of the model.

        Returns
        -------
        str
            The temporal unit of the model.
        """
        return self.model_metadata.time_unit

    def get_time_step(self) -> float | None:
        """
        Return the time step of the model.

        Returns
        -------
        float
            The time step of the model.
        """
        return self.model_metadata.time_step

    def get_units_per_properties(self) -> dict[str, list[str]]:
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
        return self.props_metadata._get_units_per_props()

    def get_properties(self) -> dict[str, Property]:
        """
        Return the properties present in the model.

        Returns
        -------
        dict[str, Property]
            Dictionary of the properties present in the model.
        """
        return self.props_metadata.props

    def get_cell_lineage_properties(
        self,
        include_Lineage_props: bool = True,
    ) -> dict[str, Property]:
        """
        Return the cell lineages properties present in the model.

        Parameters
        ----------
        include_Lineage_props : bool, optional
            True to return Lineage properties along with CellLineage ones,
            False to only return CellLineage properties (default is True).

        Returns
        -------
        dict[str, Property]
            Dictionary of the cell lineages properties present in the model.
        """
        props = self.props_metadata._get_prop_dict_from_lin_type("CellLineage")
        if include_Lineage_props:
            props.update(self.props_metadata._get_prop_dict_from_lin_type("Lineage"))
        return props

    def get_cycle_lineage_properties(
        self,
        include_Lineage_props: bool = True,
    ) -> dict[str, Property]:
        """
        Return the cycle lineages properties present in the model.

        Parameters
        ----------
        include_Lineage_props : bool, optional
            True to return Lineage properties along with CycleLineage ones,
            False to only return CycleLineage properties (default is True).

        Returns
        -------
        dict[str, Property]
            Dictionary of the cycle lineages properties present in the model.
        """
        props = self.props_metadata._get_prop_dict_from_lin_type("CycleLineage")
        if include_Lineage_props:
            props.update(self.props_metadata._get_prop_dict_from_lin_type("Lineage"))
        return props

    def get_node_properties(self) -> dict[str, Property]:
        """
        Return the node properties present in the model.

        Returns
        -------
        dict[str, Property]
            Dictionary of the node properties present in the model.
        """
        return self.props_metadata._get_prop_dict_from_prop_type("node")

    def get_edge_properties(self) -> dict[str, Property]:
        """
        Return the edge properties present in the model.

        Returns
        -------
        dict[str, Property]
            Dictionary of the edge properties present in the model.
        """
        return self.props_metadata._get_prop_dict_from_prop_type("edge")

    def get_lineage_properties(self) -> dict[str, Property]:
        """
        Return the lineage properties present in the model.

        Returns
        -------
        dict[str, Property]
            Dictionary of the lineage properties present in the model.
        """
        return self.props_metadata._get_prop_dict_from_prop_type("lineage")

    def get_cell_lineages(self) -> list[CellLineage]:
        """
        Return the cell lineages present in the model.

        Returns
        -------
        list[CellLineage]
            List of the cell lineages present in the model.
        """
        return list(self.data.cell_data.values())

    def get_cycle_lineages(self) -> list[CycleLineage]:
        """
        Return the cycle lineages present in the model.

        Returns
        -------
        list[CellLineage]
            List of the cycle lineages present in the model.
        """
        if self.data.cycle_data is None:
            return []
        else:
            return list(self.data.cycle_data.values())

    def get_cell_lineage_from_ID(self, lid: int) -> CellLineage | None:
        """
        Return the cell lineage with the specified ID.

        Parameters
        ----------
        lid : int
            ID of the lineage to return.

        Returns
        -------
        CellLineage
            The cell lineage with the specified ID.
        """
        if lid in self.data.cell_data:
            return self.data.cell_data[lid]
        else:
            return None

    def get_cycle_lineage_from_ID(self, lid: int) -> CycleLineage | None:
        """
        Return the cycle lineage with the specified ID.

        Parameters
        ----------
        lid : int
            ID of the lineage to return.

        Returns
        -------
        CycleLineage
            The cycle lineage with the specified ID.
        """
        if self.data.cycle_data and lid in self.data.cycle_data:
            return self.data.cycle_data[lid]
        else:
            return None

    @staticmethod
    def _get_lineages_from_lin_prop(
        lineages: list[L],
        lin_prop: str,
        lin_prop_value: Any,
    ) -> list[L]:
        """
        Return the lineages with the specified property value.

        Parameters
        ----------
        lineages : list[T]
            The lineages.
        lin_prop : str
            The identifier of the property to check.
        lin_prop_value : Any
            The value of the property to check.

        Returns
        -------
        list[T]
            The lineages with the specified property value.
        """
        return [lin for lin in lineages if lin.graph[lin_prop] == lin_prop_value]

    def get_cell_lineages_from_lin_prop(
        self,
        lin_prop: str,
        lin_prop_value: Any,
    ) -> list[CellLineage]:
        """
        Return the cell lineages with the specified property value.

        Parameters
        ----------
        lin_prop : str
            The identifier of the property to check.
        lin_prop_value : Any
            The value of the property to check.

        Returns
        -------
        list[CellLineage]
            The cell lineage(s) with the specified property value.
        """
        return self._get_lineages_from_lin_prop(
            list(self.data.cell_data.values()), lin_prop, lin_prop_value
        )

    def get_cycle_lineages_from_lin_prop(
        self,
        lin_prop: str,
        lin_prop_value: Any,
    ) -> list[CycleLineage]:
        """
        Return the cycle lineages with the specified property value.

        Parameters
        ----------
        lin_prop : str
            The identifier of the property to check.
        lin_prop_value : Any
            The value of the property to check.

        Returns
        -------
        list[CycleLineage]
            The cycle lineages with the specified property value.
        """
        if self.data.cycle_data is None:
            return []
        return self._get_lineages_from_lin_prop(
            list(self.data.cycle_data.values()), lin_prop, lin_prop_value
        )

    def get_next_available_lineage_ID(self, positive: bool = True) -> int:
        """
        Return the next available lineage ID, positive by default.

        Parameters
        ----------
        positive : bool, optional
            True to return a positive lineage ID,
            False to return a negative lineage ID (default is True).

        Returns
        -------
        int
            The next available lineage ID.

        Notes
        -----
        Next available lineage IDs are determined by finding the maximum
        (for positive IDs) or minimum (for negative IDs) existing lineage ID
        in the model and incrementing or decrementing it by one, respectively.
        This way, lineage IDs of previously deleted lineages are not reused.
        This avoids potential confusion or errors in lineage handling.

        The returned lineage ID cannot be 0 in case the user wants to reserve
        it for special purposes.

        Positive lineage IDs should be used for lineages with more than one cell.
        Negative lineage IDs should be used for lineages with a single cell,
        and are equal to the negative of the cell ID.
        """
        return self.data._get_next_available_lineage_ID(positive)

    def has_property(
        self,
        prop_identifier: str,
    ) -> bool:
        """
        Check if the model contains the specified property.

        Parameters
        ----------
        prop_identifier : str
            The identifier of the property to check.

        Returns
        -------
        bool
            True if the property is in the model, False otherwise.
        """
        return self.props_metadata._has_prop(prop_identifier)

    def prepare_full_data_update(self) -> None:
        """
        Prepare the updater for a full data update.

        All cells, links and lineages in the model data will see
        their property values recomputed during the next update.
        """
        if self._updater._full_data_update:
            return
        self._updater._full_data_update = True
        self._updater._update_required = True
        for lin_ID, lin in self.data.cell_data.items():
            for nid in lin.nodes:
                self._updater._added_cells.add(Cell(nid, lin_ID))
            for edge in lin.edges:
                self._updater._added_links.add(Link(edge[0], edge[1], lin_ID))
        self._updater._added_lineages = set(self.data.cell_data.keys())

    def is_update_required(self) -> bool:
        """
        Check if the model requires an update.

        The model requires an update if new properties have been added to the model,
        or if cells, links or lineages have been added or removed.
        In that case, some properties need to be recomputed to account for the changes.

        Returns
        -------
        bool
            True if the model requires an update, False otherwise.
        """
        return self._updater._update_required

    def update(self, props_to_update: list[str] | None = None) -> None:
        """
        Bring the model up to date by recomputing properties.

        This method will recompute the properties of the model
        based on the current data and the properties declaration.

        Parameters
        ----------
        props_to_update : list[str], optional
            List of properties to update. If None, all properties are updated.

        Warns
        -----
        If the model is already up to date, a warning is raised and no update
        is performed. If the user wants to force an update, they can call
        `prepare_full_data_update()` before calling this method.
        If a property in the `props_to_update` list has not been declared,
        a warning is raised and that property is ignored during the update.
        If no properties are left to update after filtering, a warning is raised
        and the model is not updated.
        """
        if not self._updater._update_required:
            warnings.warn("Model is already up to date.")
            return

        if props_to_update is not None:
            missing_props = [
                prop
                for prop in props_to_update
                if not self.props_metadata._has_prop(prop)
            ]
            if missing_props:
                warnings.warn(
                    f"The following properties have not been declared "
                    f"and will be ignored: {', '.join(missing_props)}."
                )
                props_to_update = [
                    prop for prop in props_to_update if prop not in missing_props
                ]
                if not props_to_update:
                    warnings.warn(
                        "No properties to update. The model will not be updated."
                    )
                    return

        # self.data._freeze_lineage_data()

        # TODO: need to handle all the errors that can be raised
        # by the updater methods to avoid incoherent states.
        # => saving a copy of the model before the update so we can roll back?

        time_step = self.model_metadata.time_step
        if time_step is None:
            # TODO: add "see documentation" to the error message or explain
            # directly how to set it?
            raise ValueError(
                "The time step of the model is currently not defined "
                "but is required for cycle lineage computation."
            )
        self._updater._update(
            self.data,
            time_prop=self.model_metadata.reference_time_property,
            time_step=time_step,
            props_to_update=props_to_update,
        )

        # self.data._unfreeze_lineage_data()

    def add_lineage(
        self,
        lineage: CellLineage | None = None,
        lid: int | None = None,
        with_CycleLineage: bool = False,
    ) -> int:
        """
        Add a lineage to the model.

        Parameters
        ----------
        lineage : CellLineage, optional
            Lineage to add (default is None). If None, a new lineage
            will be created.
        lid : int, optional
            ID of the lineage to add (default is None). If None, a new ID
            will be generated.
        with_CycleLineage : bool, optional
            True to compute the cycle lineage, False otherwise (default is False).

        Returns
        -------
        int
            The ID of the added lineage.

        Warns
        -----
        UserWarning
            If `with_CycleLineage` is True but the cycle data has not been added yet.
            In this case, the cycle lineage cannot be computed.
        """
        if lineage is None:
            if lid is None:
                lid = self.get_next_available_lineage_ID()
            lineage = CellLineage(lid=lid)
        else:
            lid = lineage.graph["lineage_ID"]
        assert lid is not None
        self.data.cell_data[lid] = lineage

        if with_CycleLineage:
            if self.data.cycle_data is None:
                msg = f"Cannot add cycle lineage {lid} when cycle data has not been added yet."
                warnings.warn(msg)
            else:
                cycle_lineage = self.data._compute_cycle_lineage(lid)
                self.data.cycle_data[lid] = cycle_lineage

        # Notify that an update of the property values may be required.
        self._updater._update_required = True
        self._updater._added_lineages.add(lid)

        return lid

    def remove_lineage(self, lid: int) -> CellLineage:
        """
        Remove the specified lineage from the model.

        Parameters
        ----------
        lid : int
            ID of the lineage to remove.

        Returns
        -------
        CellLineage
            The removed lineage.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not
            exist in the model.
        """
        try:
            lineage = self.data.cell_data.pop(lid)
        except KeyError:
            raise KeyError(f"Lineage with ID {lid} does not exist.")
        if self.data.cycle_data and lid in self.data.cycle_data:
            self.data.cycle_data.pop(lid)

        # Notify that an update of the property values may be required.
        self._updater._update_required = True
        self._updater._removed_lineages.add(lid)

        return lineage

    def split_lineage_from_cell(
        self,
        cid: int,
        lid: int,
        new_lid: int | None = None,
        split: Literal["upstream", "downstream"] = "upstream",
    ) -> CellLineage:
        """
        From a given cell, split a part of the given lineage into a new lineage.

        By default, the given cell will be the root of the new lineage.

        Parameters
        ----------
        cid : int
            ID of the cell at which to split the lineage.
        lid : int
            ID of the lineage to split.
        new_lid : int, optional
            ID of the new lineage (default is None). If None, a new ID
            will be generated.
        split : {"upstream", "downstream"}, optional
            Where to split the lineage relative to the given cell.
            If upstream, the given cell is included in the second lineage.
            If downstream, the given cell is included in the first lineage.
            "upstream" by default.

        Returns
        -------
        CellLineage
            The new lineage.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        """
        # TODO: unclear method... and the case where the cell is a division
        # and split is downstream is not handled correctly (we end up with
        # a lineage with several disconnected components.
        try:
            lineage = self.data.cell_data[lid]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {lid} does not exist.") from err

        # Create the new lineage.
        new_lineage = lineage._split_from_cell(cid, split)
        if new_lid is None:
            new_lid = self.get_next_available_lineage_ID()
        new_lineage.graph["lineage_ID"] = new_lid

        # Update the model data.
        self.data.cell_data[new_lid] = new_lineage
        # The update of the cycle lineages (if needed) will be
        # done by the updater.

        # Notify that an update of the property values may be required.
        self._updater._update_required = True
        self._updater._added_lineages.add(new_lid)
        self._updater._modified_lineages.add(lid)

        return new_lineage

    def add_cell(
        self,
        lid: int,
        cid: int | None = None,
        time_value: int | float = 0,
        prop_values: dict[str, Any] | None = None,
    ) -> int:
        """
        Add a cell to the lineage.

        Parameters
        ----------
        lid : int
            The ID of the lineage to which the cell belongs.
        cid : int, optional
            The ID of the cell to add (default is None).
        time_value : int | float, optional
            The value of the reference time property for the cell to add (default is 0).
        prop_values : dict, optional
            A dictionary containing the properties values of the cell to add.

        Returns
        -------
        int
            The ID of the added cell.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        KeyError
            If a property in the prop_values is not declared.
        """
        try:
            lineage = self.data.cell_data[lid]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {lid} does not exist.") from err

        if not isinstance(time_value, (int, float)):
            raise ValueError("Time value must be an integer or a float.")

        if prop_values is not None:
            for prop in prop_values:
                if not self.props_metadata._has_prop(prop):
                    raise KeyError(f"The property {prop} has not been declared.")
        else:
            prop_values = dict()

        time_step = self.model_metadata.time_step
        timepoint = None
        if time_step is not None:
            # Is the time value consistent with the time step of the model?
            if time_value % time_step != 0:
                warnings.warn(
                    f"The time value {time_value} is not consistent with the time step "
                    f"of the model ({time_step}). Use model.set_time_step() to set or "
                    f"compute a new time step compatible with all time values."
                )
            # Timepoint value computation.
            timepoint = time_value // time_step

        cid = lineage._add_cell(
            cid,
            time_prop_name=self.model_metadata.reference_time_property,
            time_prop_value=time_value,
            timepoint=timepoint,
            **prop_values,
        )

        # Notify that an update of the property values may be required.
        self._updater._update_required = True
        self._updater._added_cells.add(Cell(cid, lid))
        self._updater._modified_lineages.add(lid)

        return cid

    def remove_cell(self, cid: int, lid: int) -> dict[str, Any]:
        """
        Remove a cell from a lineage.

        Parameters
        ----------
        cid : int
            The ID of the cell to remove.
        lid : int
            The ID of the lineage to which the cell belongs.

        Returns
        -------
        dict
            Property values of the removed cell.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        """
        try:
            lineage = self.data.cell_data[lid]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {lid} does not exist.") from err

        cell_attrs = lineage._remove_cell(cid)

        # Notify that an update of the property values may be required.
        self._updater._update_required = True
        self._updater._removed_cells.add(Cell(cid, lid))
        self._updater._modified_lineages.add(lid)

        return cell_attrs

    def add_link(
        self,
        source_cid: int,
        source_lid: int,
        target_cid: int,
        target_lid: int | None = None,
        prop_values: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a link between two cells.

        Parameters
        ----------
        source_cid : int
            The ID of the source cell.
        source_lid : int
            The ID of the source lineage.
        target_cid : int
            The ID of the target cell.
        target_lid : int, optional
            The ID of the target lineage (default is None).
        prop_values : dict, optional
            A dictionary containing the properties value of
            the link between the two cells.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        KeyError
            If a property in the link_attributes is not declared.
        """
        try:
            source_lineage = self.data.cell_data[source_lid]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {source_lid} does not exist.") from err
        if target_lid is not None:
            try:
                target_lineage = self.data.cell_data[target_lid]
            except KeyError as err:
                raise KeyError(f"Lineage with ID {target_lid} does not exist.") from err
        else:
            target_lid = source_lid
            target_lineage = self.data.cell_data[source_lid]

        if prop_values is not None:
            for prop in prop_values:
                if not self.props_metadata._has_prop(prop):
                    raise KeyError(f"The property '{prop}' has not been declared.")
        else:
            prop_values = dict()

        source_lineage._add_link(
            source_cid,
            target_cid,
            target_lineage,
            time_prop_name=self.model_metadata.reference_time_property,
            **prop_values,
        )

        # Notify that an update of the property values may be required.
        self._updater._update_required = True
        self._updater._added_links.add(Link(source_cid, target_cid, source_lid))
        self._updater._modified_lineages.add(source_lid)
        if target_lid != source_lid:
            self._updater._modified_lineages.add(target_lid)

    def remove_link(self, source_cid: int, target_cid: int, lid: int) -> dict[str, Any]:
        """
        Remove a link between two cells.

        Parameters
        ----------
        source_cid : int
            The ID of the source cell.
        target_cid : int
            The ID of the target cell.
        lid : int
            The ID of the lineage to which the cells belong.

        Returns
        -------
        dict
            Property values of the removed link.

        Raises
        ------
        KeyError
            If the link between the two cells does not exist.
        """
        try:
            lineage = self.data.cell_data[lid]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {lid} does not exist.") from err
        link_attrs = lineage._remove_link(source_cid, target_cid)

        # Notify that an update of the property values may be required.
        self._updater._update_required = True
        self._updater._removed_links.add(Link(source_cid, target_cid, lid))
        self._updater._modified_lineages.add(lid)

        return link_attrs

    def get_fusions(self, lids: list[int] | None = None) -> list[Cell]:
        """
        Return fusion cells, i.e. cells with more than one parent.

        Parameters
        ----------
        lids : list[int], optional
            List of lineage IDs to check for fusions.
            If not specified, all lineages will be checked (default is None).

        Returns
        -------
        list[Cell]
            List of the fusion cells. Each cell is a named tuple:
            (cell_ID, lineage_ID).

        Raises
        ------
        KeyError
            If a lineage with the specified ID does not exist in the model.
        """
        fusions = []
        if lids is None:
            lids = list(self.data.cell_data.keys())
        for lin_ID in lids:
            try:
                lineage = self.data.cell_data[lin_ID]
            except KeyError as err:
                msg = f"Lineage with ID {lin_ID} does not exist."
                raise KeyError(msg) from err
            tmp = lineage.get_fusions()
            if tmp:
                fusions.extend([Cell(cell_ID, lin_ID) for cell_ID in tmp])
        return fusions

    def add_custom_property(
        self,
        calculator: PropertyCalculator,
    ) -> None:
        """
        Add a custom property to the model.

        This method adds the property to the PropsMetadata,
        register the way to compute the property,
        and notify the updater that all data needs to be updated.
        To actually update the data, the user needs to call the update() method.

        Parameters
        ----------
        calculator : PropertyCalculator
            Calculator to compute the property.

        Raises
        ------
        ValueError
            If the property is a cycle lineage property and cycle lineages
            have not been computed yet.
        """
        if calculator.prop.lin_type == "CycleLineage" and not self.data.cycle_data:
            raise ValueError(
                "Cycle lineages have not been computed yet. "
                "Please compute the cycle lineages first with `model.add_cycle_data()`."
            )
        self.props_metadata._add_prop(calculator.prop)
        self._updater.register_calculator(calculator)
        self.prepare_full_data_update()

    # TODO: in case of data coming from a loader, there is no calculator associated
    # with the declared properties.

    def add_absolute_age(
        self,
        custom_time_property: str | None = None,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the cell absolute age property to the model.

        The absolute age of a cell is defined as the time elapsed since
        the beginning of the lineage. Absolute age of the root is 0.
        By default, absolute age is given in the time unit of the model,
        but a custom time property can be specified.

        Parameters
        ----------
        custom_time_property : str, optional
            Identifier of the time property to use for the computation.
            If None, the reference time property of the model will be used.
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "absolute_age".
        custom_name : str, optional
            New name for the property. If None, the name will be "Absolute age".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Age of the cell since the start of the lineage".
        """
        if custom_time_property is None:
            time_prop = self.props_metadata.props.get(
                self.model_metadata.reference_time_property
            )
        else:
            time_prop = self.props_metadata.props.get(custom_time_property)
        if time_prop is None:
            time_prop = (
                custom_time_property or self.model_metadata.reference_time_property
            )
            raise KeyError(f"The time property '{time_prop}' has not been declared.")

        prop = tracking.create_absolute_age_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            dtype=time_prop.dtype,
            unit=time_prop.unit,
        )
        self.add_custom_property(tracking.AbsoluteAge(prop, time_prop.identifier))

    def add_angle(
        self,
        unit: Literal["radian", "degree"] = "radian",
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the angle property to the model.

        The angle is defined as the angle between the vectors representing
        the displacement of the cell at two consecutive detections.

        Parameters
        ----------
        unit : Literal["radian", "degree"], optional
            Unit of the angle (default is "radian").
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "angle".
        custom_name : str, optional
            New name for the property. If None, the name will be "Angle".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Angle of the cell trajectory between two consecutive detections".
        """
        prop = motion.create_angle_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            unit=unit,
        )
        self.add_custom_property(motion.Angle(prop, unit))

    def add_branch_mean_displacement(
        self,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the branch mean displacement property to the model.

        The branch mean displacement is defined as the mean displacement of the cell
        during the cell cycle.

        Parameters
        ----------
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "branch_mean_displacement".
        custom_name : str, optional
            New name for the property. If None, the name will be
            "Branch mean displacement".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Mean displacement of the cell during the cell cycle".
        """
        prop = motion.create_branch_mean_displacement_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            unit=self.model_metadata.space_unit or "pixel",
        )
        self.add_custom_property(motion.BranchMeanDisplacement(prop))

    def add_branch_mean_speed(
        self,
        include_incoming_edge: bool = False,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the branch mean speed property to the model.

        The branch mean speed is defined as the mean speed of the cell
        during the cell cycle.

        Parameters
        ----------
        include_incoming_edge : bool, optional
            Whether to include the distance between the first cell of the cycle
            and its predecessor. Default is False.
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "branch_mean_speed".
        custom_name : str, optional
            New name for the property. If None, the name will be
            "Branch mean speed".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Mean speed of the cell during the cell cycle".
        """
        space_unit = self.model_metadata.space_unit or "pixel"
        time_unit = self.model_metadata.time_unit or "frame"
        prop = motion.create_branch_mean_speed_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            unit=f"{space_unit} / {time_unit}",
        )
        self.add_custom_property(motion.BranchMeanSpeed(prop, include_incoming_edge))

    def add_branch_total_displacement(
        self,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the branch total displacement property to the model.

        The branch total displacement is defined as the displacement of the cell
        during the cell cycle.

        Parameters
        ----------
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "branch_total_displacement".
        custom_name : str, optional
            New name for the property. If None, the name will be
            "Branch total displacement".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Displacement of the cell during the cell cycle".
        """
        prop = motion.create_branch_total_displacement_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            unit=self.model_metadata.space_unit or "pixel",
        )
        self.add_custom_property(motion.BranchTotalDisplacement(prop))

    def add_cycle_completeness(
        self,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the cell cycle completeness property to the model.

        A cell cycle is defined as complete when it starts by a division
        AND ends by a division. Cell cycles that start at the root
        or end with a leaf are thus incomplete.
        This can be useful when analyzing properties like division time. It avoids
        the introduction of a bias since we have no information on what happened
        before the root or after the leaves.

        Parameters
        ----------
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "cycle_completeness".
        custom_name : str, optional
            New name for the property. If None, the name will be
            "Cycle completeness".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Completeness of the cell cycle".
        """
        prop = tracking.create_cycle_completeness_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
        )
        self.add_custom_property(tracking.CycleCompleteness(prop))

    def add_cell_displacement(
        self,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the cell displacement property to the model.

        The cell displacement is defined as the Euclidean distance between the positions
        of the cell at two consecutive detections.

        Parameters
        ----------
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "cell_displacement".
        custom_name : str, optional
            New name for the property. If None, the name will be "Cell displacement".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Displacement of the cell between two consecutive detections".
        """
        prop = motion.create_cell_displacement_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            unit=self.model_metadata.space_unit or "pixel",
        )
        self.add_custom_property(motion.CellDisplacement(prop))

    def add_rod_length(
        self,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        prop = morpho.create_rod_length_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            unit=self.model_metadata.space_unit or "pixel",
        )
        pixel_size = self.get_pixel_size()
        size_x = pixel_size["width"] if pixel_size else 1.0
        size_y = pixel_size["height"] if pixel_size else 1.0
        assert size_x == size_y, "Pixels must be isotropic in x and y."
        calc = morpho.RodLength(
            prop,
            size_x,
            skel_algo=skel_algo,
            tolerance=tolerance,
            method_width=method_width,
            width_ignore_tips=width_ignore_tips,
        )
        self.add_custom_property(calc)

    def add_cell_speed(
        self,
        custom_time_property: str | None = None,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the cell speed property to the model.

        The cell speed is defined as the displacement of the cell between two
        consecutive detections divided by the time elapsed between these two detections.
        By default, it is computed using the reference time property
        of the model, but a custom time property can be specified.

        Parameters
        ----------
        custom_time_property : str, optional
            Identifier of the time property to use for the computation.
            If None, the reference time property of the model will be used.
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "cell_speed".
        custom_name : str, optional
            New name for the property. If None, the name will be "Cell speed".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Speed of the cell between two consecutive detections".
        """
        if custom_time_property is None:
            time_prop = self.props_metadata.props.get(
                self.model_metadata.reference_time_property
            )
        else:
            time_prop = self.props_metadata.props.get(custom_time_property)
        if time_prop is None:
            time_prop = (
                custom_time_property or self.model_metadata.reference_time_property
            )
            raise KeyError(f"The time property '{time_prop}' has not been declared.")

        prop = motion.create_cell_speed_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            unit=time_prop.unit,
        )
        self.add_custom_property(motion.CellSpeed(prop, time_prop.identifier))

    def add_rod_width(
        self,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        prop = morpho.create_rod_width_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            unit=self.model_metadata.space_unit or "pixel",
        )
        pixel_size = self.get_pixel_size()
        size_x = pixel_size["width"] if pixel_size else 1.0
        size_y = pixel_size["height"] if pixel_size else 1.0
        assert size_x == size_y, "Pixels must be isotropic in x and y."
        calc = morpho.RodWidth(
            prop,
            size_x,
            skel_algo=skel_algo,
            tolerance=tolerance,
            method_width=method_width,
            width_ignore_tips=width_ignore_tips,
        )
        self.add_custom_property(calc)

    def add_division_rate(
        self,
        custom_time_property: str | None = None,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the division rate property to the model.

        Division rate is defined as the number of divisions per time unit.
        It is the inverse of the division time. By default, division rate
        is given in the time unit of the model, but a custom time property can be
        specified.

        Parameters
        ----------
        custom_time_property : str, optional
            Identifier of the time property to use for the computation.
            If None, the reference time property of the model will be used.
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "division_rate".
        custom_name : str, optional
            New name for the property. If None, the name will be "Division rate".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Number of divisions per time unit".
        """
        if custom_time_property is None:
            time_prop = self.props_metadata.props.get(
                self.model_metadata.reference_time_property
            )
        else:
            time_prop = self.props_metadata.props.get(custom_time_property)
        if time_prop is None:
            time_prop = (
                custom_time_property or self.model_metadata.reference_time_property
            )
            raise KeyError(f"The time property '{time_prop}' has not been declared.")

        prop = tracking.create_division_rate_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            unit=time_prop.unit,
        )
        self.add_custom_property(tracking.DivisionRate(prop, time_prop.identifier))

    def add_division_time(
        self,
        custom_time_property: str | None = None,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the division time property to the model.

        Division time is defined as the time elapsed between two successive divisions.
        By default, division time is given in the time unit of the model,
        but a custom time property can be specified.

        Parameters
        ----------
        custom_time_property : str, optional
            Identifier of the time property to use for the computation.
            If None, the reference time property of the model will be used.
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "division_time".
        custom_name : str, optional
            New name for the property. If None, the name will be "Division time".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Time elapsed between two successive divisions".
        """
        if custom_time_property is None:
            time_prop = self.props_metadata.props.get(
                self.model_metadata.reference_time_property
            )
        else:
            time_prop = self.props_metadata.props.get(custom_time_property)
        if time_prop is None:
            time_prop = (
                custom_time_property or self.model_metadata.reference_time_property
            )
            raise KeyError(f"The time property '{time_prop}' has not been declared.")

        prop = tracking.create_division_time_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            dtype=time_prop.dtype,
            unit=time_prop.unit,
        )

        self.add_custom_property(tracking.DivisionTime(prop, time_prop.identifier))

    def add_relative_age(
        self,
        custom_time_property: str | None = None,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the cell relative age property to the model.

        The relative age of a cell is defined as the time elapsed since the start
        of the cell cycle (i.e. previous division, or beginning of the lineage).
        Relative age of the first cell of a cell cycle is 0. By default, relative age
        is given in the time unit of the model, but a custom time property can be
        specified.

        Parameters
        ----------
        custom_time_property : str, optional
            Identifier of the time property to use for the computation.
            If None, the reference time property of the model will be used.
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "relative_age".
        custom_name : str, optional
            New name for the property. If None, the name will be "Relative age".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Age of the cell since the start of the current cell cycle".
        """
        if custom_time_property is None:
            time_prop = self.props_metadata.props.get(
                self.model_metadata.reference_time_property
            )
        else:
            time_prop = self.props_metadata.props.get(custom_time_property)
        if time_prop is None:
            time_prop = (
                custom_time_property or self.model_metadata.reference_time_property
            )
            raise KeyError(f"The time property '{time_prop}' has not been declared.")

        prop = tracking.create_relative_age_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
            dtype=time_prop.dtype,
            unit=time_prop.unit,
        )
        self.add_custom_property(tracking.RelativeAge(prop, time_prop.identifier))

    def add_straightness(
        self,
        include_incoming_edge: bool = False,
        custom_identifier: str | None = None,
        custom_name: str | None = None,
        custom_description: str | None = None,
    ) -> None:
        """
        Add the straightness property to the model.

        The straightness is defined as the ratio of the Euclidean distance between
        the start and end cells of the cell cycle to the total distance traveled.
        Straightness is a value between 0 and 1. A straight line has a straightness
        of 1, while a trajectory with many turns has a straightness close to 0.

        Parameters
        ----------
        include_incoming_edge : bool, optional
            Whether to include the distance between the first cell and its predecessor
            (default is False).
        custom_identifier : str, optional
            New identifier for the property. If None, the identifier will be
            "straightness".
        custom_name : str, optional
            New name for the property. If None, the name will be "Straightness".
        custom_description : str, optional
            New description for the property. If None, the description will be
            "Straightness of the cell trajectory during the cell cycle".
        """
        prop = motion.create_straightness_property(
            custom_identifier=custom_identifier,
            custom_name=custom_name,
            custom_description=custom_description,
        )
        self.add_custom_property(motion.Straightness(prop, include_incoming_edge))

    def _get_prop_method(self, prop_identifier: str) -> Callable:
        """
        Return the method to compute the property from its identifier.

        Parameters
        ----------
        prop_identifier : str
            Identifier of the property.

        Returns
        -------
        callable
            Method to compute the property.

        Raises
        ------
        AttributeError
            If the method to compute the property is not found in the Model class.

        Notes
        -----
        The method name must follow the pattern "add_{property_name}", otherwise
        it won't be recognized.
        """
        method_name = f"add_{prop_identifier}"
        method = getattr(self, method_name, None)
        if method:
            return method
        else:
            raise AttributeError(f"Method {method_name} not found in Model class.")

    def add_pycellin_property(self, prop_identifier: str, **kwargs: bool) -> None:
        """
        Add a single predefined pycellin property to the model.

        Parameters
        ----------
        prop_identifier : str
            Identifier of the property to add. Needs to be an available property.
        kwargs : bool
            Additional keyword arguments to pass to the function
            computing the property. For example, for absolute_age,
            in_time_unit=True can be used to yield the age
            in the time unit of the model instead of in frames.

        Raises
        ------
        KeyError
            If the property is not a predefined property of pycellin.
        ValueError
            If the property is a property of cycle lineages and the cycle lineages
            have not been computed yet.
        """
        cell_lin_props = list(futils.get_pycellin_cell_lineage_properties().keys())
        cycle_lin_props = list(futils.get_pycellin_cycle_lineage_properties().keys())
        if prop_identifier not in cell_lin_props + cycle_lin_props:
            raise KeyError(
                f"Property {prop_identifier} is not a predefined property of pycellin."
            )
        elif prop_identifier in cycle_lin_props and not self.data.cycle_data:
            raise ValueError(
                f"Property {prop_identifier} is a property of cycle lineages, "
                "but the cycle lineages have not been computed yet. "
                "Please compute the cycle lineages first with `model.add_cycle_data()`."
            )
        self._get_prop_method(prop_identifier)(**kwargs)

    def add_pycellin_properties(self, props_info: list[str | dict[str, Any]]) -> None:
        """
        Add the specified predefined pycellin properties to the model.

        Parameters
        ----------
        props_info : list[str | dict[str, Any]]
            List of the properties to add. Each property can be a string
            (the identifier of the property) or a dictionary with the identifier
            of the property as the key and additional keyword arguments as values.

        Examples
        --------
        With no additional arguments:
        >>> model.add_pycellin_properties(["absolute_age", "relative_age"])
        With additional arguments:
        >>> model.add_pycellin_properties(
        ...     [
        ...         {"absolute_age": {"in_time_unit": True}},
        ...         {"relative_age": {"in_time_unit": True}},
        ...     ]
        )
        It is possible to mix properties with and without additional arguments:
        >>> model.add_pycellin_properties(
        ...     [
        ...         {"absolute_age": {"in_time_unit": True}},
        ...         "cell_cycle_completeness",
        ...         {"relative_age": {"in_time_unit": True}},
        ...     ]
        )
        """
        for prop_info in props_info:
            if isinstance(prop_info, str):
                self.add_pycellin_property(prop_info)
            elif isinstance(prop_info, dict):
                for prop_id, kwargs in prop_info.items():
                    self.add_pycellin_property(prop_id, **kwargs)

    def recompute_property(self, prop_identifier: str) -> None:
        """
        Recompute the values of the specified property for all lineages.

        Parameters
        ----------
        prop_identifier : str
            Identifier of the property to recompute.

        Raises
        ------
        ValueError
            If the property does not exist.
        """
        # First need to check if the property exists.
        if not self.props_metadata._has_prop(prop_identifier):
            raise ValueError(f"Property '{prop_identifier}' does not exist.")

        # Then need to update the data.
        # TODO: implement
        pass

    def remove_property(
        self,
        prop_identifier: str,
    ) -> None:
        """
        Remove the specified property from the model.

        This updates the PropsMetadata, remove the property values
        for all lineages, and notify the updater to unregister the calculator.

        Parameters
        ----------
        prop_identifier : str
            Identifier of the property to remove.

        Raises
        ------
        ValueError
            If the property does not exist.
        ProtectedPropertyError
            If the property is a protected property.
        """
        # Preliminary checks.
        if not self.props_metadata._has_prop(prop_identifier):
            raise ValueError(
                f"There is no property {prop_identifier} in the declared properties."
            )
        if prop_identifier in self.props_metadata._get_protected_props():
            raise ProtectedPropertyError(prop_identifier)

        # First we update the PropsMetadata...
        prop_type = self.props_metadata.props[prop_identifier].prop_type
        lin_type = self.props_metadata.props[prop_identifier].lin_type
        self.props_metadata.props.pop(prop_identifier)

        # ... we remove the property values...
        match lin_type:
            case "CellLineage":
                for lin in self.data.cell_data.values():
                    lin._remove_prop(prop_identifier, prop_type)
            case "CycleLineage" if self.data.cycle_data:
                for clin in self.data.cycle_data.values():
                    clin._remove_prop(prop_identifier, prop_type)
            case "Lineage":
                for lin in self.data.cell_data.values():
                    lin._remove_prop(prop_identifier, prop_type)
                if self.data.cycle_data:
                    for clin in self.data.cycle_data.values():
                        clin._remove_prop(prop_identifier, prop_type)
            case _:
                raise ValueError(
                    "Lineage type not recognized. Must be 'CellLineage', 'CycleLineage'"
                    "or 'Lineage'."
                )

        # ... and finally we update the updater.
        try:
            self._updater.delete_calculator(prop_identifier)
        except KeyError:
            # No calculator doesn't mean there is something wrong,
            # maybe it's just an imported property.
            pass

    # TODO: add a method to remove several properties at the same time?
    # When no argument is provided, remove all properties?
    # def remove_properties(self, props_info: list[str | dict[str, Any]]) -> None:
    #     pass

    def add_cycle_data(self) -> None:
        """
        Compute and add the cycle lineages of the model.

        This method computes the cycle lineages from the cell lineages
        and add them to the model. It also adds the default properties
        associated with cycle lineages to the PropsMetadata.

        Raises
        ------
        ValueError
            If the time step of the model is not defined.
        """
        # if self._updater._update_required:
        #     txt = (
        #         "The structure of the cell lineages has been modified. "
        #         "Please update the model before attempting to add "
        #         "the cycle lineages."
        #     )
        #     raise UpdateRequiredError(txt)
        # TODO: I have nothing to check if the structure was modified since
        # _update_required becomes true when properties are added...
        time_prop = self.model_metadata.reference_time_property
        time_step = self.model_metadata.time_step
        if time_step is None:
            # TODO: add "see documentation" to the error message or explain
            # directly how to set it?
            raise ValueError(
                "The time step of the model is currently not defined "
                "but is required for cycle lineage computation."
            )
        time_unit = self.model_metadata.time_unit
        self.data._add_cycle_lineages(time_prop, time_step)
        self.props_metadata._add_cycle_lineage_props(time_unit)

    def has_cycle_data(self) -> bool:
        """
        Check if the model has cycle lineages.

        Returns
        -------
        bool
            True if the model has cycle lineages, False otherwise.
        """
        return bool(self.data.cycle_data)

    def _categorize_props(
        self, props: list[str] | None
    ) -> tuple[list[str], list[str], list[str]]:
        """
        Categorize properties by type (node, edge, lineage).

        Parameters
        ----------
        props : list[str] | None
            List of properties to categorize. If None, all cycle properties are used.

        Returns
        -------
        tuple[list[str], list[str], list[str]]
            Tuple containing a list of node properties, a list of edge properties,
            and a list of lineage properties.

        Raises
        ------
        ValueError
            If a property is not a cycle lineage property or not declared in the model.
        """
        props = self.get_cycle_lineage_properties()
        if props is None:
            node_props = [
                prop_id for prop_id, prop in props.items() if prop.prop_type == "node"
            ]
            edge_props = [
                prop_id for prop_id, prop in props.items() if prop.prop_type == "edge"
            ]
            lin_props = [
                prop_id for prop_id, prop in props.items() if prop.prop_type == "lineage"
            ]
        else:
            missing_props = [prop for prop in props if prop not in props]
            if missing_props:
                missing_str = ", ".join(repr(f) for f in missing_props)
                plural = len(missing_props) > 1
                raise ValueError(
                    f"Propert{'ies' if plural else 'y'} {missing_str} "
                    f"{'are' if plural else 'is'} either not{' ' if plural else 'a'}"
                    f"cycle lineage propert{'ies' if plural else 'y'} or not declared "
                    f"in the model."
                )
            node_props = [f for f in props if f in self.get_node_properties()]
            edge_props = [f for f in props if f in self.get_edge_properties()]
            lin_props = [f for f in props if f in self.get_lineage_properties()]

        return (node_props, edge_props, lin_props)

    @staticmethod
    def _propagate_node_props(
        node_props: list[str],
        clin: CycleLineage,
        lin: CellLineage,
    ) -> None:
        """
        Propagate node properties from cycle lineage to cell lineage.

        Parameters
        ----------
        node_props : list[str]
            List of node properties to propagate.
        clin : CycleLineage
            Source cycle lineage.
        lin : CellLineage
            Target cell lineage.
        """
        for cycle, cells in clin.nodes(data="cells"):
            for cell in cells:
                for prop in node_props:
                    try:
                        lin.nodes[cell][prop] = clin.nodes[cycle][prop]
                    except KeyError:
                        # If the property is not present, we skip it.
                        continue

    @staticmethod
    def _propagate_edge_props(
        edge_props: list[str],
        clin: CycleLineage,
        lin: CellLineage,
    ) -> None:
        """
        Propagate edge properties from cycle lineage to cell lineage.

        Parameters
        ----------
        edge_props : list[str]
            List of edge properties to propagate.
        clin : CycleLineage
            Source cycle lineage.
        lin : CellLineage
            Target cell lineage.

        Raises
        ------
        FusionError
            If a cell has more than one incoming edge, indicating fusion.
        """
        for edge in clin.edges:
            cycle = clin.nodes[edge[1]]["cycle_ID"]
            cells = clin.nodes[cycle]["cells"]

            # Intracycle edges.
            for link in pairwise(cells):
                for prop in edge_props:
                    try:
                        lin.edges[link][prop] = clin.edges[edge][prop]
                    except KeyError:
                        # If the property is not present, we skip it.
                        continue

            # Intercycle edge.
            incoming_edges = list(lin.in_edges(cells[0]))
            # TODO: check this, prop just below is unbound
            if len(incoming_edges) > 1:
                raise FusionError(cells[0], lin.graph["lineage_ID"])
            try:
                lin.edges[incoming_edges[0]][prop] = clin.edges[edge][prop]
            except (IndexError, KeyError):
                # Either the cell is a root or the property is not present.
                # In both cases, we skip it.
                continue

    @staticmethod
    def _propagate_lineage_props(
        lin_props: list[str],
        clin: CycleLineage,
        lin: CellLineage,
    ) -> None:
        """
        Propagate lineage properties from cycle lineage to cell lineage.

        Parameters
        ----------
        lin_props : list[str]
            List of lineage properties to propagate.
        clin : CycleLineage
            Source cycle lineage.
        lin : CellLineage
            Target cell lineage.
        """
        for prop in lin_props:
            try:
                lin.graph[prop] = clin.graph[prop]
            except KeyError:
                continue

    def propagate_cycle_properties(
        self, props: list[str] | None = None, update: bool = True
    ) -> None:
        """
        Propagate the cycle properties to the cell lineages.

        Parameters
        ----------
        props : list[str], optional
            List of the properties to propagate. If None, all cycle properties are
            propagated. Default is None.
        update : bool, optional
            Whether to update the model before propagating the properties.
            Default is True. For a correct propagation, the model must be updated
            beforehand. If you are not sure about the state of the model, leave
            this parameter to True. If you are sure that the model is up to date,
            you can set it to False for better performances.

        Raises
        ------
        ValueError
            If the cycle lineages have not been computed yet.
            If a property in the list is not a cycle lineage property or not declared
            in the model.
        FusionError
            If a cell has more than one incoming edge in the cycle lineage,
            which indicates a fusion event.

        Warnings
        --------
        Quantitative analysis of cell cycle properties should not be done on cell
        lineages after propagation of cycle properties, UNLESS you account for cell
        cycle length. Otherwise you will introduce a bias in your quantification.
        Indeed, after propagation, cycle properties (like division time) become
        over-represented in long cell cycles since these properties are propagated on each
        node of the cell cycle in cell lineages, whereas they are stored only once
        per cell cycle on the cycle node in cycle lineages.
        """
        if not self.data.cycle_data:
            raise ValueError(
                "Cycle lineages have not been computed yet. "
                "Please compute the cycle lineages first with `model.add_cycle_data()`."
            )
        if self._updater._update_required and update:
            self.update()
        node_props, edge_props, lin_props = self._categorize_props(props)

        # Update the properties declaration: now the property type is `Lineage`
        # instead of just `CycleLineage` since the properties are now present on cycle
        # AND cell lineages.
        for prop in node_props + edge_props + lin_props:
            self.props_metadata.props[prop].lin_type = "Lineage"

        # Actual propagation.
        for lin_ID in self.data.cell_data:
            lin = self.data.cell_data[lin_ID]
            clin = self.data.cycle_data[lin_ID]
            if node_props:
                Model._propagate_node_props(node_props, clin, lin)
            if edge_props:
                Model._propagate_edge_props(edge_props, clin, lin)
            if lin_props:
                Model._propagate_lineage_props(lin_props, clin, lin)

    def to_cell_dataframe(self, lids: list[int] | None = None) -> pd.DataFrame:
        """
        Return the cell data of the model as a pandas DataFrame.

        Parameters
        ----------
        lids : list[int], optional
            List of IDs of the lineages to export (default is None).
            If None, all lineages are exported.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the cell data.

        Raises
        ------
        ValueError
            If the `lineage_ID`, `frame` or `cell_ID` property is not found in the model.
        """
        list_df = []
        nb_nodes = 0
        for lin_ID, lineage in self.data.cell_data.items():
            if lids and lin_ID not in lids:
                continue
            nb_nodes += len(lineage)
            tmp_df = pd.DataFrame(dict(lineage.nodes(data=True)).values())
            tmp_df["lineage_ID"] = lin_ID
            list_df.append(tmp_df)
        df = pd.concat(list_df, ignore_index=True)
        assert nb_nodes == len(df)

        # Reoder the columns to have pycellin mandatory properties first.
        time_prop = self.model_metadata.reference_time_property
        columns = df.columns.tolist()
        try:
            columns.remove("lineage_ID")
            columns.remove(time_prop)
            columns.remove("cell_ID")
        except ValueError as err:
            raise err
        columns = ["lineage_ID", time_prop, "cell_ID"] + columns
        df = df[columns]
        df.sort_values(
            ["lineage_ID", time_prop, "cell_ID"], ignore_index=True, inplace=True
        )

        return df

    def to_link_dataframe(self, lids: list[int] | None = None) -> pd.DataFrame:
        """
        Return the link data of the model as a pandas DataFrame.

        Parameters
        ----------
        lids : list[int], optional
            List of IDs of the lineages to export (default is None).
            If None, all lineages are exported.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the link data.
        """
        list_df = []
        nb_edges = 0
        for lin_ID, lineage in self.data.cell_data.items():
            if lids and lin_ID not in lids:
                continue
            nb_edges += len(lineage.edges)
            tmp_df = nx.to_pandas_edgelist(
                lineage, source="source_cell_ID", target="target_cell_ID"
            )
            tmp_df["source_cell_ID"] = tmp_df["source_cell_ID"].astype(int)
            tmp_df["target_cell_ID"] = tmp_df["target_cell_ID"].astype(int)
            tmp_df["lineage_ID"] = lin_ID
            list_df.append(tmp_df)
        df = pd.concat(list_df, ignore_index=True)
        assert nb_edges == len(df)

        # Reoder the columns to have pycellin mandatory properties first.
        columns = df.columns.tolist()
        try:
            columns.remove("lineage_ID")
        except ValueError as err:
            raise err
        columns = ["lineage_ID"] + columns
        df = df[columns]
        df.sort_values("lineage_ID", ignore_index=True, inplace=True)

        return df

    def to_lineage_dataframe(self, lids: list[int] | None = None) -> pd.DataFrame:
        """
        Return the lineage data of the model as a pandas DataFrame.

        Parameters
        ----------
        lids : list[int], optional
            List of IDs of the lineages to export (default is None).
            If None, all lineages are exported.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the lineage data.

        Raises
        ------
        ValueError
            If the `lineage_ID` is not found in the model.
        """
        list_df = []
        for lin_ID, lineage in self.data.cell_data.items():
            if lids and lin_ID not in lids:
                continue
            tmp_df = pd.DataFrame([lineage.graph])
            list_df.append(tmp_df)
        df = pd.concat(list_df, ignore_index=True)

        # Reoder the columns to have pycellin mandatory properties first.
        columns = df.columns.tolist()
        try:
            columns.remove("lineage_ID")
        except ValueError as err:
            raise err
        columns = ["lineage_ID"] + columns
        df = df[columns]
        df.sort_values("lineage_ID", ignore_index=True, inplace=True)

        return df

    def to_cycle_dataframe(self, lids: list[int] | None = None) -> pd.DataFrame:
        """
        Return the cell cycle data of the model as a pandas DataFrame.

        Parameters
        ----------
        lids : list[int], optional
            List of IDs of the lineages to export (default is None).
            If None, all lineages are exported.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the cell cycle data.

        Raises
        ------
        ValueError
            If the cycle lineages have not been computed yet.
            If the `lineage_ID`, `level` or `cycle_ID` property is not found
            in the model.
        """
        list_df = []  # type: list[pd.DataFrame]
        nb_nodes = 0
        if not self.data.cycle_data:
            raise ValueError(
                "Cycle lineages have not been computed yet. "
                "Please compute the cycle lineages first with `model.add_cycle_data()`."
            )
        for lin_ID, lineage in self.data.cycle_data.items():
            if lids and lin_ID not in lids:
                continue
            nb_nodes += len(lineage)
            tmp_df = pd.DataFrame(dict(lineage.nodes(data=True)).values())
            tmp_df["lineage_ID"] = lin_ID
            list_df.append(tmp_df)
        df = pd.concat(list_df, ignore_index=True)
        assert nb_nodes == len(df)

        # Reoder the columns to have pycellin mandatory properties first.
        columns = df.columns.tolist()
        try:
            columns.remove("lineage_ID")
            columns.remove("level")
            columns.remove("cycle_ID")
        except ValueError as err:
            raise err
        columns = ["lineage_ID", "level", "cycle_ID"] + columns
        df = df[columns]
        df.sort_values(
            ["lineage_ID", "level", "cycle_ID"], ignore_index=True, inplace=True
        )

        return df

    def save_to_pickle(self, path: str, protocol: int = pickle.HIGHEST_PROTOCOL) -> None:
        """
        Save the model to a file by pickling it.

        Uses custom __getstate__ and __setstate__ methods to ensure ModelMetadata
        with dynamic fields is properly serialized and deserialized.

        Parameters
        ----------
        path : str
            Path to save the model.
        protocol : int, optional
            Pickle protocol to use (default is pickle.HIGHEST_PROTOCOL).
        """
        with open(path, "wb") as file:
            pickle.dump(self, file, protocol=protocol)

    @staticmethod
    def load_from_pickle(path: str) -> "Model":
        """
        Load a model from a pickled pycellin file.

        Uses custom __getstate__ and __setstate__ methods to ensure ModelMetadata
        with dynamic fields is properly serialized and deserialized.

        Parameters
        ----------
        path : str
            Path to read the model.

        Returns
        -------
        Model
            The loaded model.
        """
        with open(path, "rb") as file:
            return pickle.load(file)

    def export(self, path: str, format: str) -> None:
        """
        Export the model to a file in a specific format (e.g. TrackMate).

        Parameters
        ----------
        path : str
            Path to export the model.
        format : str
            Format of the exported file.
        """
        # TODO: implement
        pass
