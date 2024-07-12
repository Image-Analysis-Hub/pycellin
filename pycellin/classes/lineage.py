#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from typing import Optional

import networkx as nx


class Lineage(nx.DiGraph, metaclass=ABCMeta):
    """
    Do I really need this one?
      => do I have something that is applicable for both cell and cycle lineage?
    - id

    Maybe it would make more sense to have CycleLineage inherit from CellLineage...?
    I need to think about all the methods before I decide.
    """

    def __init__(self, nx_digraph: Optional[nx.DiGraph] = None):
        super().__init__(incoming_graph_data=nx_digraph)

    # TODO: A method to check that there is no merge (i. e. in_degree > 1)
    # I wrote one for Laure at some point but I cannot find it anymore...?!
    # def check_no_merge(graph: nx.DiGraph):
    #     no_merge = True
    #     for node in graph.nodes():
    #         if graph.in_degree(node) > 1:
    #             no_merge = False
    #             print(f"Node {node} has an in_degree > 1.")

    #     if no_merge:
    #         print("All good, there is no merge in the graph.")

    # For all the following methods, we might need to recompute features.
    #   => put it in the abstract method and then use super() in the subclasses after modifying the graph
    # Abstract method because for CellLineages, we first need to unfreeze the graph.
    # Can I reuse already implemented methods from networkx?

    # @abstractmethod
    # def add_node(self):
    #     pass

    # @abstractmethod
    # def remove_node(self):
    #     pass

    # @abstractmethod
    # def add_edge(self):
    #     pass

    # @abstractmethod
    # def remove_edge(self):
    #     pass

    # # If I use _add_element(), maybe I don't need the other methods to be abstract
    # # since they all call _add_element() under the hood.
    # @abstractmethod
    # def _add_element(self, element_type: str, element: dict):
    #     # element_type: node or edge, but maybe it could also be 0 for node and 1 for edge
    #     pass

    pass

    def plot(self):
        # TODO: investigate the use of plotly to draw an interactive lineage
        # instead of networkx-pygraphviz. Pygraphviz installation in Windows
        # is not straightforward and need the preliminary installation of
        # Graphviz executable.
        # https://plotly.com/python/tree-plots/
        # It will rely on igraph but there is a networkx to igraph converter,
        # and igraph can be installed via conda and is actively supported.
        # https://python.igraph.org/en/stable/
        # https://python.igraph.org/en/stable/generation.html#from-external-libraries
        # Or maybe I can let the user choose between pygraphviz and plotly?
        pos = nx.drawing.nx_agraph.graphviz_layout(self, prog="dot")
        # The computed positions do not temporally align the nodes, so we force
        # the y position to be the frame number.
        pos = {node: (x, -self.nodes[node]["FRAME"]) for node, (x, _) in pos.items()}
        nx.draw(self, pos, with_labels=True, arrows=True, font_weight="bold")


class CellLineage(Lineage):

    pass


class CycleLineage(Lineage):
    # This one needs to be frozen: nx.freeze
    pass
