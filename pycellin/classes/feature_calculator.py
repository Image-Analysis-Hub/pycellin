#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Any

from pycellin.classes.data import Data
from pycellin.classes.feature import Feature
from pycellin.classes.lineage import Lineage

# In FeaturesDeclaration, maybe all the features should be stored in the same
# dictionary, with getters to access the features of a specific type?


def _get_lin_data_from_lin_type(data: Data, lineage_type: str) -> list[Lineage]:
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
    list of Lineage
        List of lineages of the specified type.
    """
    if lineage_type == "CellLineage":
        return list(data.cell_data.values())
    elif lineage_type == "CycleLineage":
        return list(data.cycle_data.values())
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

    # @abstractmethod
    # def add_to_one(self, lineage: Lineage, *args, **kwargs) -> None:
    #     """
    #     Compute and add the value of a local feature to a single object.
    #     """
    #     pass


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
        lineages = _get_lin_data_from_lin_type(data, self.feature.lineage_type)
        for noi, lin_ID in nodes_to_enrich:
            lin = lineages[lin_ID]
            lin.nodes[noi][self.feature.name] = self.compute(lin, noi)

    # def add_to_one(self, lineage: Lineage, noi: int) -> None:
    #     """
    #     Compute and add the value of a local feature to a single node.

    #     Parameters
    #     ----------
    #     lineage : Lineage
    #         Lineage object containing the node of interest.
    #     noi : int
    #         Node ID of the node of interest.
    #     """
    #     lineage.nodes[noi][self.feature.name] = self.compute(lineage, noi)


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
        lineages = _get_lin_data_from_lin_type(data, self.feature.lineage_type)
        for source, target, lin_ID in edges_to_enrich:
            link = (source, target)
            lin = lineages[lin_ID]
            lin.edges[link][self.feature.name] = self.compute(lin, link)

    # def add_to_one(self, lineage: Lineage, edge: tuple[int, int]) -> None:
    #     """
    #     Compute and add the value of a local feature to a single edge.

    #     Parameters
    #     ----------
    #     lineage : Lineage
    #         Lineage object containing the edge of interest.
    #     edge : tuple[int, int]
    #         Directed edge of interest, as a tuple of two node IDs.
    #     """
    #     lineage.edges[edge][self.feature.name] = self.compute(lineage, edge)


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
        lineages = _get_lin_data_from_lin_type(data, self.feature.lineage_type)
        for lin_ID in lineages_to_enrich:
            lin = lineages[lin_ID]
            lin.graph[self.feature.name] = self.compute(lin)

    # def add_to_one(self, lineage: Lineage) -> None:
    #     """
    #     Compute and add the value of a local feature to a single lineage.

    #     Parameters
    #     ----------
    #     lineage : Lineage
    #         Lineage object containing the node of interest.
    #     """
    #     lineage.graph[self.feature.name] = self.compute(lineage)


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

    # @abstractmethod
    # def _add_to_lineage(self, data: Data, lineage: Lineage) -> None:
    #     """
    #     Compute and add the value of a global feature to all objects in a lineage.
    #     Need to be implemented in subclasses.
    #     """
    #     pass

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

    # def add_to_all(self, data: Data) -> None:
    #     """
    #     Compute and add the value of a global feature to all objects in all lineages
    #     of the data.

    #     Parameters
    #     ----------
    #     data : Data
    #         Data object containing the lineages.
    #     """
    #     if self.feature.lineage_type == "CellLineage":
    #         lineages = data.cell_data.values()
    #     else:
    #         lineages = data.cycle_data.values()

    #     for lin in lineages:
    #         self._add_to_lineage(data, lin)


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
        lineages = _get_lin_data_from_lin_type(data, self.feature.lineage_type)
        for lin in lineages:
            for noi in lin.nodes:
                lin.nodes[noi][self.feature.name] = self.compute(data, lin, noi)

    # def _add_to_lineage(self, data: Data, lineage: Lineage) -> None:
    #     """
    #     Compute and add the value of a global feature to all nodes in a lineage.

    #     Parameters
    #     ----------
    #     data : Data
    #         Data object containing all the lineages.
    #     lineage : Lineage
    #         Lineage containing the nodes of interest.
    #     """
    #     for noi in lineage.nodes:
    #         lineage.nodes[noi][self.feature.name] = self.compute(data, lineage, noi)


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
        lineages = _get_lin_data_from_lin_type(data, self.feature.lineage_type)
        for lin in lineages:
            for edge in lin.edges:
                lin.edges[edge][self.feature.name] = self.compute(data, lin, edge)

    # def _add_to_lineage(self, data: Data, lineage: Lineage) -> None:
    #     """
    #     Compute and add the value of a global feature to all edges in a lineage.

    #     Parameters
    #     ----------
    #     data : Data
    #         Data object containing all the lineages.
    #     lineage : Lineage
    #         Lineage containing the edges of interest.
    #     """
    #     for edge in lineage.edges:
    #         lineage.edges[edge][self.feature.name] = self.compute(data, lineage, edge)


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
        lineages = _get_lin_data_from_lin_type(data, self.feature.lineage_type)
        for lin in lineages:
            lin.graph[self.feature.name] = self.compute(data, lin)

    # def _add_to_lineage(self, data: Data, lineage: Lineage) -> None:
    #     """
    #     Compute and add the value of a global feature to a lineage.

    #     Parameters
    #     ----------
    #     data : Data
    #         Data object containing all the lineages.
    #     lineage : Lineage
    #         Lineage of interest.
    #     """
    #     lineage.graph[self.feature.name] = self.compute(data, lineage)
