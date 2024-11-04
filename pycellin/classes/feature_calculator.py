#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Any

from pycellin.classes.data import Data
from pycellin.classes.feature import Feature
from pycellin.classes.lineage import Lineage

# In FeaturesDeclaration, maybe all the features should be stored in the same
# dictionary, with getters to access the features of a specific type?


class FeatureCalculator(ABC):
    """
    Abstract class to compute feature values.
    """

    _LOCAL_FEATURE = None
    _FEATURE_TYPE = None

    @classmethod
    def is_for_local_feature(self) -> bool | None:
        """
        Accessor to the _LOCAL_FEATURE attribute.

        Return True if the calculator is for local features,
        False if it is for global features.
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
        """
        pass

    @abstractmethod
    def add_to_one(self, feat_name: str, lineage: Lineage, *args, **kwargs) -> None:
        """
        Compute and add the value of a local feature to a single object.
        """
        pass


class NodeLocalFeatureCalculator(LocalFeatureCalculator):

    _FEATURE_TYPE = "node"

    @abstractmethod
    def compute(self, lineage: Lineage, noi: int) -> Any:
        """
        Compute the value of a local feature for a single node.
        Need to be implemented in subclasses.
        """
        pass

    def add_to_one(self, feat_name: str, lineage: Lineage, noi: int) -> None:
        """
        Compute and add the value of a local feature to a single node.

        Parameters
        ----------
        feat_name : str
            Name of the local feature to compute.
        lineage : Lineage
            Lineage object containing the node of interest.
        noi : int
            Node ID of the node of interest.
        """
        lineage.nodes[noi][feat_name] = self.compute(lineage, noi)


class EdgeLocalFeatureCalculator(LocalFeatureCalculator):

    _FEATURE_TYPE = "edge"

    @abstractmethod
    def compute(self, lineage: Lineage, edge: tuple[int, int]) -> Any:
        """
        Compute the value of a local feature for a single edge.
        Need to be implemented in subclasses.
        """
        pass

    def add_to_one(
        self, feat_name: str, lineage: Lineage, edge: tuple[int, int]
    ) -> None:
        """
        Compute and add the value of a local feature to a single edge.

        Parameters
        ----------
        feat_name : str
            Name of the local feature to compute.
        lineage : Lineage
            Lineage object containing the edge of interest.
        edge : tuple[int, int]
            Directed edge of interest, as a tuple of two node IDs.
        """
        lineage.edges[edge][feat_name] = self.compute(lineage, edge)


class LineageLocalFeatureCalculator(LocalFeatureCalculator):

    _FEATURE_TYPE = "lineage"

    @abstractmethod
    def compute(self, lineage: Lineage) -> Any:
        """
        Compute the value of a local feature for a single lineage.
        Need to be implemented in subclasses.
        """
        pass

    def add_to_one(self, feat_name: str, lineage: Lineage) -> None:
        """
        Compute and add the value of a local feature to a single lineage.

        Parameters
        ----------
        feat_name : str
            Name of the local feature to compute.
        lineage : Lineage
            Lineage object containing the node of interest.
        """
        lineage.graph[feat_name] = self.compute(lineage)


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
        """
        pass

    @abstractmethod
    def _add_to_lineage(self, feat_name: str, data: Data, lineage: Lineage) -> None:
        """
        Compute and add the value of a global feature to all objects in a lineage.
        Need to be implemented in subclasses.
        """
        pass

    def add_to_all(self, feature: Feature, data: Data) -> None:
        """
        Compute and add the value of a global feature to all objects in all lineages
        of the data.

        Parameters
        ----------
        feature : Feature
            Feature associated with the calculator.
        data : Data
            Data object containing the lineages.
        """
        feat_name = feature.name
        lin_type = feature.lineage_type
        if lin_type == "CellLineage":
            lineages = data.cell_data.values()
        else:
            lineages = data.cycle_data.values()

        for lin in lineages:
            self._add_to_lineage(feat_name, data, lin)


class NodeGlobalFeatureCalculator(GlobalFeatureCalculator):

    _FEATURE_TYPE = "node"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, noi: int) -> Any:
        """
        Compute the value of a global feature for a single node.
        Need to be implemented in subclasses.
        """
        pass

    def _add_to_lineage(self, feat_name: str, data: Data, lineage: Lineage) -> None:
        """
        Compute and add the value of a global feature to all nodes in a lineage.

        Parameters
        ----------
        feat_name : str
            Name of the global feature to compute.
        data : Data
            Data object containing all the lineages.
        lineage : Lineage
            Lineage containing the nodes of interest.
        """
        for noi in lineage.nodes:
            lineage.nodes[noi][feat_name] = self.compute(data, lineage, noi)


class EdgeGlobalFeatureCalculator(GlobalFeatureCalculator):

    _FEATURE_TYPE = "edge"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, edge: tuple[int, int]) -> Any:
        """
        Compute the value of a global feature for a single edge.
        Need to be implemented in subclasses.
        """
        pass

    def _add_to_lineage(self, feat_name: str, data: Data, lineage: Lineage) -> None:
        """
        Compute and add the value of a global feature to all edges in a lineage.

        Parameters
        ----------
        feat_name : str
            Name of the global feature to compute.
        data : Data
            Data object containing all the lineages.
        lineage : Lineage
            Lineage containing the edges of interest.
        """
        for edge in lineage.edges:
            lineage.edges[edge][feat_name] = self.compute(data, lineage, edge)


class LineageGlobalFeatureCalculator(GlobalFeatureCalculator):

    _FEATURE_TYPE = "lineage"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage) -> Any:
        """
        Compute the value of a global feature for a single lineage.
        Need to be implemented in subclasses.
        """
        pass

    def _add_to_lineage(self, feat_name: str, data: Data, lineage: Lineage) -> None:
        """
        Compute and add the value of a global feature to a lineage.

        Parameters
        ----------
        feat_name : str
            Name of the global feature to compute.
        data : Data
            Data object containing all the lineages.
        lineage : Lineage
            Lineage of interest.
        """
        lineage.graph[feat_name] = self.compute(data, lineage)
