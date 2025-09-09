#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Any

from pycellin.classes.data import Data
from pycellin.classes.property import Property
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


class PropertyCalculator(ABC):
    """
    Abstract class to compute and enrich data from a model with the values of a property.
    """

    _LOCAL_PROPERTY = None  # type: bool | None
    _PROPERTY_TYPE = None  # type: str | None

    def __init__(self, property: Property):
        self.prop = property

    @classmethod
    def is_for_local_property(cls) -> bool | None:
        """
        Accessor to the _LOCAL_PROPERTY attribute.

        Return True if the calculator is for a local property,
        False if it is for a global property.
        """
        return cls._LOCAL_PROPERTY

    @classmethod
    def get_property_type(cls) -> str | None:
        """
        Accessor to the _PROPERTY_TYPE attribute.

        Return the type of object to which the property applies
        (node, edge, lineage).
        """
        return cls._PROPERTY_TYPE

    @abstractmethod
    def compute(self, *args, **kwargs) -> Any:
        """
        Compute the value of a property for a single object.
        Need to be implemented in subclasses.

        Returns
        -------
        Any
            The value of the property for the object.
        """
        pass

    @abstractmethod
    def enrich(self, data: Data, *args, **kwargs) -> None:
        """
        Enrich the data with the value of a property.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        """
        pass


class LocalPropCalculator(PropertyCalculator):
    """
    Abstract class to compute local property values and add them to lineages.

    Local properties are properties that only need data from the current object
    to be computed.
    Examples:
    - cell area (node property) only need data from the cell itself
      (coordinates of boundary points);
    - cell speed (edge property) only need data from the edge itself
      (time and space location of the two nodes);
    - lineage duration (lineage property) only need data from the lineage itself
      (number of timepoints).
    """

    _LOCAL_PROPERTY = True

    @abstractmethod
    def compute(self, lineage: Lineage, *args, **kwargs) -> Any:
        """
        Compute the value of a local property for a single object.
        Need to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object containing the object of interest.

        Returns
        -------
        Any
            The value of the local property for the object.
        """
        pass

    @abstractmethod
    def enrich(self, data: Data, *args, **kwargs) -> None:
        """
        Enrich the data with the value of a local property.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        """
        pass


class NodeLocalPropCalculator(LocalPropCalculator):
    _PROPERTY_TYPE = "node"

    @abstractmethod
    def compute(self, lineage: Lineage, nid: int) -> Any:
        """
        Compute the value of a local property for a single node.
        Need to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object containing the node of interest.
        nid : int
            Node ID of the node of interest.

        Returns
        -------
        Any
            The value of the local property for the node.
        """
        pass

    def enrich(self, data: Data, nodes_to_enrich: list[tuple[int, int]], **kwargs) -> None:
        """
        Enrich the data with the value of a local property for a list of nodes.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        nodes_to_enrich : list of tuple[int, int]
            List of tuples containing the node ID and the lineage ID of the nodes
            to enrich with the property value.
        """
        lineages = _get_lin_data_from_lin_type(data, self.prop.lin_type)
        for nid, lin_ID in nodes_to_enrich:
            lin = lineages[lin_ID]
            lin.nodes[nid][self.prop.identifier] = self.compute(lin, nid)


class EdgeLocalPropCalculator(LocalPropCalculator):
    _PROPERTY_TYPE = "edge"

    @abstractmethod
    def compute(self, lineage: Lineage, edge: tuple[int, int]) -> Any:
        """
        Compute the value of a local property for a single edge.
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
            The value of the local property for the edge.
        """
        pass

    def enrich(self, data: Data, edges_to_enrich: list[tuple[int, int, int]], **kwargs) -> None:
        """
        Enrich the data with the value of a local property for a list of edges.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        edges_to_enrich : list of tuple[int, int, int]
            List of tuples containing the source node ID, the target node ID and
            the lineage ID of the edges to enrich with the property value.
        """
        lineages = _get_lin_data_from_lin_type(data, self.prop.lin_type)
        for source, target, lin_ID in edges_to_enrich:
            link = (source, target)
            lin = lineages[lin_ID]
            lin.edges[link][self.prop.identifier] = self.compute(lin, link)


class LineageLocalPropCalculator(LocalPropCalculator):
    _PROPERTY_TYPE = "lineage"

    @abstractmethod
    def compute(self, lineage: Lineage) -> Any:
        """
        Compute the value of a local property for a single lineage.
        Need to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object of interest.

        Returns
        -------
        Any
            The value of the local property for the lineage.
        """
        pass

    def enrich(self, data: Data, lineages_to_enrich: list[int], **kwargs) -> None:
        """
        Enrich the data with the value of a local property for all lineages.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        """
        lineages = _get_lin_data_from_lin_type(data, self.prop.lin_type)
        for lin_ID in lineages_to_enrich:
            lin = lineages[lin_ID]
            lin.graph[self.prop.identifier] = self.compute(lin)


class GlobalPropCalculator(PropertyCalculator):
    """
    Abstract class to compute global property values and add them to lineages.

    Global properties are properties that need data from other objects to be computed.
    Examples:
    - cell age (node property) needs data from all its ancestor cells in the lineage;
    - TODO: edge property, find relevant example?
    - TODO: lineage property, find relevant example?
    """

    _LOCAL_PROPERTY = False

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, *args, **kwargs) -> Any:
        """
        Compute the value of a global property for a single object.
        Need to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.

        Returns
        -------
        Any
            The value of the global property for the object.
        """
        pass

    @abstractmethod
    def enrich(self, data: Data, **kwargs) -> None:
        """
        Enrich the data with the value of a global property for all objects in all lineages.

        Parameters
        ----------
        data : Data
            Data object containing the lineages to enrich.
        """
        pass


class NodeGlobalPropCalculator(GlobalPropCalculator):
    _PROPERTY_TYPE = "node"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, nid: int) -> Any:
        """
        Compute the value of a global property for a single node.
        Need to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            Data object containing the lineages.
        lineage : Lineage
            Lineage containing the node of interest.
        nid : int
            Node ID of the node of interest.

        Returns
        -------
        Any
            The value of the global property for the node.
        """
        pass

    def enrich(self, data: Data, **kwargs) -> None:
        """
        Enrich the data with the value of a global property for all nodes in all lineages.

        Parameters
        ----------
        data : Data
            Data object containing the lineages to enrich.
        """
        lineages = _get_lin_data_from_lin_type(data, self.prop.lin_type)
        for lin in lineages.values():
            for nid in lin.nodes:
                lin.nodes[nid][self.prop.identifier] = self.compute(data, lin, nid)


class EdgeGlobalPropCalculator(GlobalPropCalculator):
    _PROPERTY_TYPE = "edge"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, edge: tuple[int, int]) -> Any:
        """
        Compute the value of a global property for a single edge.
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
            The value of the global property for the edge.
        """
        pass

    def enrich(self, data: Data, **kwargs) -> None:
        """
        Enrich the data with the value of a global property for all edges in all lineages.

        Parameters
        ----------
        data : Data
            Data object containing the lineages to enrich.
        """
        lineages = _get_lin_data_from_lin_type(data, self.prop.lin_type)
        for lin in lineages.values():
            for edge in lin.edges:
                lin.edges[edge][self.prop.identifier] = self.compute(data, lin, edge)


class LineageGlobalPropCalculator(GlobalPropCalculator):
    _PROPERTY_TYPE = "lineage"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage) -> Any:
        """
        Compute the value of a global property for a single lineage.
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
            The value of the global property for the lineage.
        """
        pass

    def enrich(self, data: Data, **kwargs) -> None:
        """
        Enrich the data with the value of a global property for all lineages.

        Parameters
        ----------

        data : Data
            Data object containing the lineages to enrich.
        """
        lineages = _get_lin_data_from_lin_type(data, self.prop.lin_type)
        for lin in lineages.values():
            lin.graph[self.prop.identifier] = self.compute(data, lin)
