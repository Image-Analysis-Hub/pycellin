#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from typing import Optional

from igraph import Graph, EdgeSeq
import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go


class Lineage(nx.DiGraph, metaclass=ABCMeta):
    """
    Abstract class for a lineage graph.
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

        Returns
        -------
        int
            The root node of the lineage.

        Raises
        ------
        AssertionError
            If there is more or less than one root node.
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

        Returns
        -------
        list[int]
            The list of leaf nodes in the lineage.
        """
        leaves = [
            n
            for n in self.nodes()
            if self.in_degree(n) != 0 and self.out_degree(n) == 0
        ]
        return leaves

    def get_ancestors(self, root: int, target_node: int) -> list[int]:
        """
        Return all the ancestors of a given node, in chronological order.

        Chronological order means from the root node to the target node.
        In terms of graph theory, it is the shortest path from the root node
        to the target node.

        Parameters
        ----------
        root : int
            The root node of the lineage.
        target_node : int
            A node of the lineage.

        Returns
        -------
        list[int]
            A list of all the ancestor nodes, from root node to target node.
        """
        return nx.shortest_path(self, source=root, target=target_node)

    def is_root(self, node: int):
        """
        Check if a given node is a root node.

        The root is defined as the first node of the lineage temporally speaking,
        i.e. the node with no incoming edges and at least one outgoing edge.

        Parameters
        ----------
        node : int
            The node to check.

        Returns
        -------
        bool
            True if the node is a root node, False otherwise.
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

        Parameters
        ----------
        node : int
            The node to check.

        Returns
        -------
        bool
            True if the node is a leaf node, False otherwise.
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

    def plot_with_plotly(self):
        """
        Plot the lineage as a tree using Plotly.
        """

        def make_annotations(pos, labels, font_size=10, font_color="rgb(250,250,250)"):
            L = len(pos)
            if len(labels) != L:
                raise ValueError("The lists pos and text must have the same len")
            annotations = []
            for k in range(L):
                annotations.append(
                    dict(
                        text=labels[
                            k
                        ],  # or replace labels with a different list for the text within the circle
                        x=pos[k][0],
                        y=2 * M - position[k][1],
                        xref="x1",
                        yref="y1",
                        font=dict(color=font_color, size=font_size),
                        showarrow=False,
                    )
                )
            return annotations

        # Conversion of the lineage/graph from networkx to igraph.
        G = Graph.from_networkx(self)
        # print(g)

        nr_vertices = G.vcount()
        v_label = G.vs["ID"]
        lay = G.layout("rt")  # plot tree

        position = {k: lay[k] for k in range(nr_vertices)}
        Y = [lay[k][1] for k in range(nr_vertices)]
        # Y = [G.vs["ID"]]
        M = max(Y)

        es = EdgeSeq(G)  # sequence of edges
        E = [e.tuple for e in G.es]  # list of edges

        L = len(position)
        Xn = [position[k][0] for k in range(L)]
        Yn = [2 * M - position[k][1] for k in range(L)]
        Xe = []
        Ye = []
        for edge in E:
            Xe += [position[edge[0]][0], position[edge[1]][0], None]
            Ye += [2 * M - position[edge[0]][1], 2 * M - position[edge[1]][1], None]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=Xe,
                y=Ye,
                mode="lines",
                line=dict(color="rgb(210,210,210)", width=1),
                hoverinfo="none",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=Xn,
                y=Yn,
                mode="markers",
                name="bla",
                marker=dict(
                    symbol="circle",
                    size=18,
                    color="#6175c1",  #'#DB4551',
                    line=dict(color="rgb(50,50,50)", width=1),
                ),
                text=v_label,
                hoverinfo="text",
                opacity=0.8,
            )
        )

        axis = dict(
            showline=False,  # hide axis line, grid, ticklabels and  title
            zeroline=False,
            showgrid=False,
            showticklabels=False,
        )

        fig.update_layout(
            title="Title",
            annotations=make_annotations(position, v_label),
            font_size=5,
            showlegend=False,
            xaxis=axis,
            yaxis=axis,
            margin=dict(l=40, r=40, b=85, t=100),
            hovermode="closest",
            plot_bgcolor="rgb(248,248,248)",
        )
        fig.show()


class CellLineage(Lineage):

    def get_divisions(self, nodes: Optional[list[int]] = None) -> list[int]:
        """
        Return the division nodes of the lineage.

        Division nodes are defined as nodes with more than one outgoing edge.

        Parameters
        ----------
        nodes : list[int], optional
            A list of nodes to check for divisions. If None, all nodes
            in the lineage will be checked.

        Returns
        -------
        list[int]
            The list of division nodes in the lineage.
        """
        if nodes is None:
            nodes = self.nodes()
        return [n for n in nodes if self.out_degree(n) > 1]

    def get_cell_cycle(self, node: int) -> list[int]:
        """
        Identify all the nodes in the cell cycle of a given node, in chronological order.

        The cell cycle starts from the root or a division node,
        and ends at a division or leaf node.

        Parameters
        ----------
        node : int
            The node for which to identify the nodes in the cell cycle.

        Returns
        -------
        list[int]
            A chronologically ordered list of nodes representing
            the cell cycle for the given node.
        """
        cell_cycle = [node]
        start = False
        end = False

        if self.is_root(node):
            start = True
        if self.is_division(node) or self.is_leaf(node):
            end = True

        if not start:
            predecessors = list(self.predecessors(node))
            assert len(predecessors) == 1
            while not self.is_division(*predecessors) and not self.is_root(
                *predecessors
            ):
                # While not the generation birth.
                cell_cycle.append(*predecessors)
                predecessors = list(self.predecessors(*predecessors))
                err = (
                    f"Node {node} in {self.graph['name']} has "
                    f"{len(predecessors)} predecessors."
                )
                assert len(predecessors) == 1, err
            if self.is_root(*predecessors) and not self.is_division(*predecessors):
                cell_cycle.append(*predecessors)
            cell_cycle.reverse()  # We built it from the end.

        if not end:
            successors = list(self.successors(node))
            err = (
                f"Node {node} in {self.graph['name']} has "
                f"{len(successors)} successors."
            )
            assert len(successors) == 1, err
            while not self.is_division(*successors) and not self.is_leaf(*successors):
                cell_cycle.append(*successors)
                successors = list(self.successors(*successors))
                err = (
                    f"Node {node} in {self.graph['name']} has "
                    f"{len(successors)} successors."
                )
                assert len(successors) == 1, err
            cell_cycle.append(*successors)

        return cell_cycle

    def get_cell_cycles(
        self, keep_incomplete_cell_cycles: bool = False, debug: bool = False
    ):
        """
        Identify all the nodes of each cell cycle in a lineage.

        A cell cycle is a tree segment that starts at the root or at a
        division node, ends at a division node or at a leaf, and doesn't
        include any other division.

        Parameters
        ----------
        keep_incomplete_cell_cycles : bool, optional
            True to keep the first and last cell cycles, False otherwise.
            False by default.
        debug : bool, optional
            True to display debug messages, False otherwise. False by default.

        Returns
        -------
        list(list(int))
            List of nodes ID for each cell cycle, in chronological order.
        """
        if keep_incomplete_cell_cycles:
            end_nodes = self.get_divisions() + self.get_leaves()
        else:
            end_nodes = self.get_divisions()  # Includes the root if it's a div.
        if debug:
            print("End nodes:", end_nodes)

        cell_cycles = []
        for node in end_nodes:
            cc_nodes = self.get_generation(node)
            if not keep_incomplete_cell_cycles and self.get_root() in cc_nodes:
                continue
            cell_cycles.append(cc_nodes)
            if debug:
                print("Cell cycle nodes:", cc_nodes)

        return cell_cycles

    def is_division(self, node: int):
        """
        Check if a given node is a division node.

        A division node is defined as a node with more than one outgoing edge
        and at most one incoming edge.

        Parameters
        ----------
        node : int
            The node to check.

        Returns
        -------
        bool
            True if the node is a division node, False otherwise.
        """
        if self.in_degree(node) <= 1 and self.out_degree(node) > 1:
            return True
        else:
            return False


class CycleLineage(Lineage):
    # This one needs to be frozen: nx.freeze
    pass
