#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod

from pycellin.classes.data import Data
from pycellin.classes.feature import Feature
from pycellin.classes.lineage import Lineage


# Make an interface that specializes depending on:
# - the different types of objects: cells, links, lineages... (cell cycles?)
# - if the feature is local or global
# Local means that the feature only needs data from the current object
# to be computed.
# Global means that the feature needs data from other objects to be computed.
# For now feature type (node, edge, lineage) is not stored in the feature object.
# It probably should be. Same with local / global?
# In FeaturesDeclaration, maybe all the features should be stored in the same
# dictionary, with getters to access the features of a specific type?

# Common interface to compute a feature value:
# takes an object and returns a value
# In case of global features, I will need the whole model or at least the current
# lineage to compute the feature value. Will this not create a circular dependency?

# Maybe first separate into node, edge, lineage, then do the local / global separation.
# Because then the apply_on_all function can be defined in the middle level classes.


class FeatureCalculator(ABC):
    """
    Abstract class to compute feature values.
    """

    @abstractmethod
    def compute(
        self,
        data: Data,
    ) -> None:
        """
        Compute the value of a feature.

        Parameters
        ----------

        """
        pass


class NodeFeatureCalculator(FeatureCalculator):
    """
    Class to compute node feature values.
    """

    @abstractmethod
    def compute_for_one_node(
        self,
        node: int,
        lineage: Lineage,
    ) -> None:
        """
        Compute the value of a feature for a single node.

        Parameters
        ----------
        node : str
            The name of the node.
        lineage : Lineage
            The lineage the node belongs to.
        time_step : int
            The time step the node is at.
        """
        pass

    def compute_and_add(
        self,
        feature: Feature,
        data: Data,
    ) -> None:
        """
        Compute the value of a node feature.

        Parameters
        ----------

        """
        for lin in data.cell_data.values():
            for node in lin.nodes:
                lin.nodes[node]["feature.name"] = self.compute_for_one_node(node, lin)


class FeatureCalculatorFactory:
    """
    Factory class to create feature calculators.
    """

    def __init__(self) -> None:
        self._calculators = {}

    def register_calculator(
        self, feature: Feature, calculator: FeatureCalculator
    ) -> None:
        """
        Register a feature calculator.

        Parameters
        ----------
        feature : Feature
            The feature to register the calculator for.
        calculator : FeatureCalculator
            The calculator to register.
        """
        self._calculators[feature] = calculator

    def get_calculator(self, feature: Feature) -> FeatureCalculator:
        """
        Get the calculator for a feature.

        Parameters
        ----------
        feature : Feature
            The feature to get the calculator for.

        Returns
        -------
        FeatureCalculator
            The calculator for the feature.
        """
        calculator = self._calculators.get(feature)
        if calculator is None:
            raise ValueError(f"No calculator registered for feature {feature}.")
        return calculator
    

# class Calculator:
#     def __init__(self, factory: FeatureCalculatorFactory):
#         self.factory = factory

#     def calculate(self, operation_name: str, a: float, b: float) -> float:
#         operation = self.factory.create_operation(operation_name)
#         return operation.compute(a, b)
