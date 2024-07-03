#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod

import networkx as nx


class Lineage(nx.DiGraph, metaclass=ABCMeta):
    """
    Do I really need this one?
      => do I have something that is applicable for both cell and cycle lineage?
    - id

    Maybe it would make more sense to have CycleLineage inherit from CellLineage...?
    I need to think about all the methods I need to decide.
    """
    pass


    # For all the following methods, we might need to recompute features.
    #   => put it in the abstract method and then use super() in the subclasses after modifying the graph
    # Abstract method because for CellLineages, we first need to unfreeze the graph. 


    @abstractmethod
    def add_node(self):
        pass

    @abstractmethod
    def remove_node(self):
        pass

    @abstractmethod
    def add_edge(self):
        pass

    @abstractmethod
    def remove_edge(self):
        pass

    # If I use _add_element(), maybe I don't need the other methods to be abstract since they all call
    # _add_element() under the hood.    
    @abstractmethod
    def _add_element(self, element_type: str, element: dict):
        pass
    


class CellLineage(Lineage):
    pass


class CycleLineage(Lineage):
    # This one needs to be frozen: nx.freeze
    pass