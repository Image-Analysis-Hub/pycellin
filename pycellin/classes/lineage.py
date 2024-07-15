#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from typing import Optional

import matplotlib.pyplot as plt
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

    def get_root(self) -> int:
        """
        Return the root of the lineage.

        The root is defined as the first node of the lineage temporally speaking,
        i.e. the node with no incoming edges and at least one outgoing edge.
        A lineage has one and exactly one root node.
        In the case where the lineage has only one node,
        that node is considered the root.

        Returns:
            int: The root node of the lineage.

        Raises:
            AssertionError: If there is more or less than one root node.
        """
        if len(self) == 1:
            root = [n for n in self.nodes()]
            assert len(root) == 1
        else:
            root = [
                n
                for n in self.nodes()
                if self.in_degree(n) == 0 and self.out_degree(n) != 0
            ]
            assert len(root) == 1
        return root[0]

    def get_leaves(self) -> list[int]:
        """
        Return the leaves of the lineage.

        The leaves are defined as the nodes with at least one incoming edge
        and no outgoing edges.

        Returns:
            list[int]: The list of leaf nodes in the lineage.
        """
        leaves = [
            n
            for n in self.nodes()
            if self.in_degree(n) != 0 and self.out_degree(n) == 0
        ]
        return leaves

    def is_root(self, node: int):
        """
        Check if a given node is a root node.

        The root is defined as the first node of the lineage temporally speaking,
        i.e. the node with no incoming edges and at least one outgoing edge.

        Parameters:
            node (int): The node to check.

        Returns:
            bool: True if the node is a root node, False otherwise.
        """
        if self.in_degree(node) == 0 and self.out_degree(node) != 0:
            return True
        else:
            return False

    def is_leaf(self, node: int):
        """
        Check if a given node is a leaf node.

        A leaf node is defined as a node with at least one incoming edge
        and no outgoing edges.

        Parameters:
            node (int): The node to check.

        Returns:
            bool: True if the node is a leaf node, False otherwise.
        """
        if self.in_degree(node) != 0 and self.out_degree(node) == 0:
            return True
        else:
            return False

    def plot(self, figsize: tuple[float, float] = None):
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
        if figsize is not None:
            plt.figure(figsize=figsize)
        nx.draw(self, pos, with_labels=True, arrows=True, font_weight="bold")
        plt.show()


class CellLineage(Lineage):

    def get_divisions(self, nodes: Optional[list[int]] = None) -> list[int]:
        """
        Return the division nodes of the lineage.

        Division nodes are defined as nodes with more than one outgoing edge.

        Parameters:
            nodes (Optional[list[int]]): A list of nodes to check for divisions.
                If None, all nodes in the lineage will be checked.

        Returns:
            list[int]: The list of division nodes in the lineage.
        """
        if nodes is None:
            nodes = self.nodes()
        return [n for n in nodes if self.out_degree(n) > 1]

    def is_division(self, node: int):
        """
        Check if a given node is a division node.

        A division node is defined as a node with more than one outgoing edge
        and at most one incoming edge.

        Parameters:
            node (int): The node to check.

        Returns:
            bool: True if the node is a division node, False otherwise.
        """
        if self.in_degree(node) <= 1 and self.out_degree(node) > 1:
            return True
        else:
            return False


class CycleLineage(Lineage):
    # This one needs to be frozen: nx.freeze
    pass
