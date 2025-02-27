#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Any

from pycellin.classes.data import Data
from pycellin.classes.feature import Feature
from pycellin.classes.lineage import Lineage


def _get_lin_data_from_lin_type(data: Data, lineage_type: str) -> dict[int, Lineage]:
    """
    Get the lineages from the data object based on the lineage type.

    Parameters
    ----------
    data : Data
        Data object containing the lineages.
    lineage_type : str
        Type of lineage to extract from the data object.
        Can be "CellLineage" or "CycleLineage".

    Returns
    -------
    dict[int, Lineage]
        Dictionary of lineages extracted from the data object.
        Keys are the lineage IDs.
    """
    if lineage_type == "CellLineage":
        return data.cell_data
    elif lineage_type == "CycleLineage":
        return data.cycle_data
    else:
        raise ValueError("Invalid lineage type.")


class FeatureCalculator(ABC):
    """
    Abstract class to compute and enrich data from a model with the values of a feature.
    """

    _LOCAL_FEATURE = None
    _FEATURE_TYPE = None

    def __init__(self, feature: Feature):
        self.feature = feature

    @classmethod
    def is_for_local_feature(self) -> bool | None:
        """
        Accessor to the _LOCAL_FEATURE attribute.

        Return True if the calculator is for a local feature,
        False if it is for a global feature.
        """
        return self._LOCAL_FEATURE

    @classmethod
    def get_feature_type(self) -> str | None:
        """
        Accessor to the _FEATURE_TYPE attribute.

        Return the type of object to which the feature applies
        (node, edge, lineage).
        """
        return self._FEATURE_TYPE

    @abstractmethod
    def compute(self, *args, **kwargs) -> Any:
        """
        Compute the value of a feature for a single object.
        Need to be implemented in subclasses.

        Returns
        -------
        Any
            The value of the feature for the object.
        """
        pass

    @abstractmethod
    def enrich(self, data: Data, *args, **kwargs) -> None:
        """
        Enrich the data with the value of a feature.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        """
        pass


class LocalFeatureCalculator(FeatureCalculator):
    """
    Abstract class to compute local feature values and add them to lineages.

    Local features are features that only need data from the current object
    to be computed.
    Examples:
    - cell area (node feature) only need data from the cell itself
      (coordinates of boundary points);
    - cell speed (edge feature) only need data from the edge itself
      (time and space location of the two nodes);
    - lineage duration (lineage feature) only need data from the lineage itself
      (number of timepoints).
    """

    _LOCAL_FEATURE = True

    @abstractmethod
    def compute(self, lineage: Lineage, *args, **kwargs) -> Any:
        """
        Compute the value of a local feature for a single object.
        Need to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object containing the object of interest.

        Returns
        -------
        Any
            The value of the local feature for the object.
        """
        pass

    @abstractmethod
    def enrich(self, data: Data, *args, **kwargs) -> None:
        """
        Enrich the data with the value of a local feature.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        """
        pass


class NodeLocalFeatureCalculator(LocalFeatureCalculator):

    _FEATURE_TYPE = "node"

    @abstractmethod
    def compute(self, lineage: Lineage, noi: int) -> Any:
        """
        Compute the value of a local feature for a single node.
        Need to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object containing the node of interest.
        noi : int
            Node ID of the node of interest.

        Returns
        -------
        Any
            The value of the local feature for the node.
        """
        pass

    def enrich(
        self, data: Data, nodes_to_enrich: list[tuple[int, int]], **kwargs
    ) -> None:
        """
        Enrich the data with the value of a local feature for a list of nodes.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        nodes_to_enrich : list of tuple[int, int]
            List of tuples containing the node ID and the lineage ID of the nodes
            to enrich with the feature value.
        """
        lineages = _get_lin_data_from_lin_type(data, self.feature.lin_type)
        for noi, lin_ID in nodes_to_enrich:
            lin = lineages[lin_ID]
            lin.nodes[noi][self.feature.name] = self.compute(lin, noi)


class EdgeLocalFeatureCalculator(LocalFeatureCalculator):

    _FEATURE_TYPE = "edge"

    @abstractmethod
    def compute(self, lineage: Lineage, edge: tuple[int, int]) -> Any:
        """
        Compute the value of a local feature for a single edge.
        Need to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object containing the edge of interest.
        edge : tuple[int, int]
            Directed edge of interest, as a tuple of two node IDs.

        Returns
        -------
        Any
            The value of the local feature for the edge.
        """
        pass

    def enrich(
        self, data: Data, edges_to_enrich: list[tuple[int, int, int]], **kwargs
    ) -> None:
        """
        Enrich the data with the value of a local feature for a list of edges.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        edges_to_enrich : list of tuple[int, int, int]
            List of tuples containing the source node ID, the target node ID and
            the lineage ID of the edges to enrich with the feature value.
        """
        lineages = _get_lin_data_from_lin_type(data, self.feature.lin_type)
        for source, target, lin_ID in edges_to_enrich:
            link = (source, target)
            lin = lineages[lin_ID]
            lin.edges[link][self.feature.name] = self.compute(lin, link)


class LineageLocalFeatureCalculator(LocalFeatureCalculator):

    _FEATURE_TYPE = "lineage"

    @abstractmethod
    def compute(self, lineage: Lineage) -> Any:
        """
        Compute the value of a local feature for a single lineage.
        Need to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object of interest.

        Returns
        -------
        Any
            The value of the local feature for the lineage.
        """
        pass

    def enrich(self, data: Data, lineages_to_enrich: list[int], **kwargs) -> None:
        """
        Enrich the data with the value of a local feature for all lineages.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        """
        lineages = _get_lin_data_from_lin_type(data, self.feature.lin_type)
        for lin_ID in lineages_to_enrich:
            lin = lineages[lin_ID]
            lin.graph[self.feature.name] = self.compute(lin)


class GlobalFeatureCalculator(FeatureCalculator):
    """
    Abstract class to compute global feature values and add them to lineages.

    Global features are features that need data from other objects to be computed.
    Examples:
    - cell age (node feature) needs data from all its ancestor cells in the lineage;
    - TODO: edge feature, find relevant example?
    - TODO: lineage feature, find relevant example?
    """

    _LOCAL_FEATURE = False

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, *args, **kwargs) -> Any:
        """
        Compute the value of a global feature for a single object.
        Need to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.

        Returns
        -------
        Any
            The value of the global feature for the object.
        """
        pass

    @abstractmethod
    def enrich(self, data: Data, **kwargs) -> None:
        """
        Enrich the data with the value of a global feature for all objects in all lineages.

        Parameters
        ----------
        data : Data
            Data object containing the lineages to enrich.
        """
        pass


class NodeGlobalFeatureCalculator(GlobalFeatureCalculator):

    _FEATURE_TYPE = "node"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, noi: int) -> Any:
        """
        Compute the value of a global feature for a single node.
        Need to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        lineage : Lineage
            Lineage containing the node of interest.
        noi : int
            Node ID of the node of interest.

        Returns
        -------
        Any
            The value of the global feature for the node.
        """
        pass

    def enrich(self, data: Data, **kwargs) -> None:
        """
        Enrich the data with the value of a global feature for all nodes in all lineages.

        Parameters
        ----------
        data : Data
            Data object containing the lineages to enrich.
        """
        lineages = _get_lin_data_from_lin_type(data, self.feature.lin_type)
        for lin in lineages.values():
            for noi in lin.nodes:
                lin.nodes[noi][self.feature.name] = self.compute(data, lin, noi)


class EdgeGlobalFeatureCalculator(GlobalFeatureCalculator):

    _FEATURE_TYPE = "edge"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, edge: tuple[int, int]) -> Any:
        """
        Compute the value of a global feature for a single edge.
        Need to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        lineage : Lineage
            Lineage containing the edge of interest.
        edge : tuple[int, int]
            Directed edge of interest, as a tuple of two node IDs.

        Returns
        -------
        Any
            The value of the global feature for the edge.
        """
        pass

    def enrich(self, data: Data, **kwargs) -> None:
        """
        Enrich the data with the value of a global feature for all edges in all lineages.

        Parameters
        ----------
        data : Data
            Data object containing the lineages to enrich.
        """
        lineages = _get_lin_data_from_lin_type(data, self.feature.lin_type)
        for lin in lineages.values():
            for edge in lin.edges:
                lin.edges[edge][self.feature.name] = self.compute(data, lin, edge)


class LineageGlobalFeatureCalculator(GlobalFeatureCalculator):

    _FEATURE_TYPE = "lineage"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage) -> Any:
        """
        Compute the value of a global feature for a single lineage.
        Need to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        lineage : Lineage
            Lineage of interest.

        Returns
        -------
        Any
            The value of the global feature for the lineage.
        """
        pass

    def enrich(self, data: Data, **kwargs) -> None:
        """
        Enrich the data with the value of a global feature for all lineages.

        Parameters
        ----------

        data : Data
            Data object containing the lineages to enrich.
        """
        lineages = _get_lin_data_from_lin_type(data, self.feature.lin_type)
        for lin in lineages.values():
            lin.graph[self.feature.name] = self.compute(data, lin)
