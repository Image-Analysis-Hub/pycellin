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

    @abstractmethod
    def compute(self, *args, **kwargs) -> Any:
        """
        Compute the value of a feature.

        Parameters
        ----------

        """
        pass

    @abstractmethod
    def add_to_lineages(self, feature: Feature, data: Data) -> None:
        pass

    @abstractmethod
    def _add_feature_to_lineage(self, feat_name: str, lineage: Lineage) -> None:
        pass


class LocalFeatureCalculator(FeatureCalculator):
    """
    Abstract class to compute local feature values and add them to lineages.

    Local features are features that only need data from the current object
    to be computed.
    Examples:
    - cell area (node feature) only need data from the cell itself
      (coordinates of boundary points) ;
    - cell speed (edge feature) only need data from the edge itself
      (time and space location of the two nodes) ;
    - lineage duration (lineage feature) only need data from the lineage itself
      (number of timepoints).
    """

    @abstractmethod
    def compute(self, lineage: Lineage, *args, **kwargs) -> Any:
        pass

    def add_to_lineages(self, feature: Feature, data: Data) -> None:
        feat_name = feature.name
        lin_type = feature.lineage_type
        if lin_type == "CellLineage":
            lineages = data.cell_data.values()
        else:
            lineages = data.cycle_data.values()

        for lin in lineages:
            self._add_feature_to_lineage(lin, feat_name)

    @abstractmethod
    def _add_feature_to_lineage(self, feat_name: str, lineage: Lineage) -> None:
        pass


class NodeLocalFeatureCalculator(LocalFeatureCalculator):

    @abstractmethod
    def compute(self, lineage: Lineage, noi: int) -> Any:
        pass

    def _add_feature_to_lineage(self, feat_name: str, lineage: Lineage) -> None:
        for noi in lineage.nodes:
            lineage.nodes[noi][feat_name] = self.compute(lineage, noi)


class EdgeLocalFeatureCalculator(LocalFeatureCalculator):

    @abstractmethod
    def compute(self, lineage: Lineage, edge: tuple[int, int]) -> Any:
        pass

    def _add_feature_to_lineage(self, feat_name: str, lineage: Lineage) -> None:
        for edge in lineage.edges:
            lineage.edges[edge][feat_name] = self.compute(lineage, edge)


class LineageLocalFeatureCalculator(LocalFeatureCalculator):

    @abstractmethod
    def compute(self, lineage: Lineage) -> Any:
        pass

    def _add_feature_to_lineage(self, feat_name: str, lineage: Lineage) -> None:
        lineage.graph[feat_name] = self.compute(lineage)


class GlobalFeatureCalculator(FeatureCalculator):
    """
    Abstract class to compute global feature values and add them to lineages.

    Global features are features that need data from other objects to be computed.
    Examples:
    - cell age (node feature) needs data from all its ancestor cells in the lineage ;
    - TODO: edge feature, find relevant example?
    - TODO: lineage feature, find relevant example?
    """

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, *args, **kwargs) -> Any:
        pass

    def add_to_lineages(self, feature: Feature, data: Data) -> None:
        feat_name = feature.name
        lin_type = feature.lineage_type
        if lin_type == "CellLineage":
            lineages = data.cell_data.values()
        else:
            lineages = data.cycle_data.values()

        for lin in lineages:
            self._add_feature_to_lineage(feat_name, lin, data)

    @abstractmethod
    def _add_feature_to_lineage(self, feat_name: str, lineage: Lineage) -> None:
        pass


class NodeGlobalFeatureCalculator(GlobalFeatureCalculator):

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, noi: int) -> Any:
        pass

    def _add_feature_to_lineage(
        self, feat_name: str, lineage: Lineage, data: Data
    ) -> None:
        for noi in lineage.nodes:
            lineage.nodes[noi][feat_name] = self.compute(noi, lineage, data)


class EdgeGlobalFeatureCalculator(GlobalFeatureCalculator):

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, edge: tuple[int, int]) -> Any:
        pass

    def _add_feature_to_lineage(
        self, feat_name: str, lineage: Lineage, data: Data
    ) -> None:
        for edge in lineage.edges:
            lineage.edges[edge][feat_name] = self.compute(edge, lineage, data)


class LineageGlobalFeatureCalculator(GlobalFeatureCalculator):

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage) -> Any:
        pass

    def _add_feature_to_lineage(
        self, feat_name: str, lineage: Lineage, data: Data
    ) -> None:
        lineage.graph[feat_name] = self.compute(lineage, data)


# class FeatureCalculatorFactory:
#     """
#     Factory class to create feature calculators.
#     """

#     def __init__(self) -> None:
#         self._calculators = {}

#     def register_calculator(
#         self, feature: Feature, calculator: FeatureCalculator
#     ) -> None:
#         """
#         Register a feature calculator.

#         Parameters
#         ----------
#         feature : Feature
#             The feature to register the calculator for.
#         calculator : FeatureCalculator
#             The calculator to register.
#         """
#         self._calculators[feature] = calculator

#     def get_calculator(self, feature: Feature) -> FeatureCalculator:
#         """
#         Get the calculator for a feature.

#         Parameters
#         ----------
#         feature : Feature
#             The feature to get the calculator for.

#         Returns
#         -------
#         FeatureCalculator
#             The calculator for the feature.
#         """
#         calculator = self._calculators.get(feature)
#         if calculator is None:
#             raise ValueError(f"No calculator registered for feature {feature}.")
#         return calculator
