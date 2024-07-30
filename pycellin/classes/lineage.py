#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod
from typing import Any

from igraph import Graph, EdgeSeq
import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objects as go


class Lineage(nx.DiGraph, metaclass=ABCMeta):
    """
    Abstract class for a lineage graph.
    """

    def __init__(self, nx_digraph: nx.DiGraph | None = None):
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

    def plot_with_plotly(
        self,
        title: str | None = None,
        node_text: str | None = None,
        node_text_font: dict[str, Any] | None = None,
        node_marker_style: dict[str, Any] | None = None,
        node_colormap_feature: str | None = None,
        node_color_scale: str | None = None,
        node_hover_features: list[str] | None = None,
        edge_line_style: dict[str, Any] | None = None,
    ):
        """
        Plot the lineage as a tree using Plotly.

        Heavily based on the code from https://plotly.com/python/tree-plots/

        Parameters
        ----------
        title : str, optional
            The title of the plot. If None, no title is displayed.
        node_text : str, optional
            The feature of the nodes to display as text inside
            the nodes of the plot. If None, no text is displayed.
            ID of the node ("cell_ID") by default.
        node_text_font : dict, optional
            The font style of the text inside the nodes (size, color, etc).
            If None, a default style is used.
        node_marker_style : dict, optional
            The style of the markers representing the nodes in the plot
            (symbol, size, color, line, etc). If None, a default style is used.
        node_colormap_feature : str, optional
            The feature of the nodes to use for coloring the nodes.
            If None, no color mapping is applied.
        node_color_scale : str, optional
            The color scale to use for coloring the nodes. If None,
            default to current Plotly template.
        node_hover_features : list[str], optional
            The hover template for the nodes. If None, a default template
            is used.
        edge_line_style : dict, optional
            The style of the lines representing the edges in the plot
            (color, width, etc). If None, default to current Plotly template.

        Examples
        --------
        For styling the graph:

        node_text_font = dict(
            color="black",
            size=10,
        )

        node_marker_style = dict(
            symbol="circle",
            size=20,
            color="white",
            line=dict(color="black", width=1),
        )
        """
        # https://plotly.com/python/hover-text-and-formatting/#customizing-hover-label-appearance
        # https://plotly.com/python/hover-text-and-formatting/#customizing-hover-text-with-a-hovertemplate

        # TODO: extract parameters to make the function more versatile:
        # - node style                  OK
        # - edge style                  OK
        # - node text                   OK
        # - edge text?
        # - node hoverinfo style
        # - edge hoverinfo style
        # - node hoverinfo text         OK
        # - edge hoverinfo text
        # - axes
        # - color mapping node/edge attributes?     OK nodes
        # - option to hide nodes? or just put nodes and edges in the legend
        #   so we can hide manually one or the other

        # Conversion of the networkx lineage graph to igraph.
        G = Graph.from_networkx(self)
        nodes_count = G.vcount()

        # Basic tree layout.
        layout = G.layout("rt")

        # Adjusting the y position of the nodes to be the frame number.
        frame_values = G.vs["frame"]
        layout = [(layout[k][0], frame_values[k]) for k in range(nodes_count)]

        # Computing the exact positions of nodes and edges.
        positions = {k: layout[k] for k in range(nodes_count)}
        edges = [edge.tuple for edge in G.es]
        x_nodes = [x for (x, _) in positions.values()]
        y_nodes = [y for (_, y) in positions.values()]
        x_edges = []
        y_edges = []
        for edge in edges:
            x_edges += [positions[edge[0]][0], positions[edge[1]][0], None]
            y_edges += [positions[edge[0]][1], positions[edge[1]][1], None]

        # Add color mapping if node_colormap_feature is specified.
        if node_colormap_feature:
            if not node_marker_style:
                node_marker_style = dict()
            node_colors = G.vs[node_colormap_feature]
            node_marker_style["color"] = node_colors
            node_marker_style["colorscale"] = node_color_scale
            node_marker_style["colorbar"] = dict(title=node_colormap_feature)
            # TODO: add colorbar units, but the info is stored in the model
            # FIXME: the colorbar is not displayed above the traces names

        # Text in the nodes.
        if node_text:
            node_labels = G.vs[node_text]
            if len(node_labels) != nodes_count:
                raise ValueError("The lists pos and text must have the same len")
            annotations = []
            for k in range(nodes_count):
                annotations.append(
                    dict(
                        text=node_labels[k],
                        x=positions[k][0],
                        y=positions[k][1],
                        xref="x1",
                        yref="y1",
                        font=node_text_font,
                        showarrow=False,
                    )
                )
        else:
            annotations = None

        # Plot edges.
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x_edges,
                y=y_edges,
                mode="lines",
                line=edge_line_style,
                name="Edges",
                # hoverinfo="none",
            )
        )

        # Define hovertemplate.
        # TODO: when feature is float, display only 2 decimals
        # or give control to the user.
        if node_hover_features:
            node_hover_text = []
            for node in G.vs:
                text = ""
                for feat in node_hover_features:
                    hover_text = f"{feat}: {node[feat]}<br>"
                    text += hover_text
                node_hover_text.append(text)
        else:
            node_hover_text = [
                f"cell_ID: {node['cell_ID']}<br>frame: {node['frame']}" for node in G.vs
            ]
        if "lineage_ID" in G.attributes():
            graph_name = f"lineage_ID: {G['lineage_ID']}"
        else:
            graph_name = ""

        # Plot nodes.
        fig.add_trace(
            go.Scatter(
                x=x_nodes,
                y=y_nodes,
                hovertemplate="%{text}",
                mode="markers",
                marker=node_marker_style,
                text=node_hover_text,  # Used in hoverinfo not for the text in the nodes
                hoverinfo="text",
                name=graph_name,
            )
        )

        fig.update_layout(
            title=title,
            annotations=annotations,
            showlegend=True,
            hovermode="closest",
        )
        fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
        fig.update_yaxes(autorange="reversed", title="Time (frames)")
        fig.show()


class CellLineage(Lineage):

    def get_divisions(self, nodes: list[int] | None = None) -> list[int]:
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
                    f"Node {node} in lineage of ID {self.graph['lineage_ID']} "
                    f"has {len(predecessors)} predecessors."
                )
                assert len(predecessors) == 1, err
            if self.is_root(*predecessors) and not self.is_division(*predecessors):
                cell_cycle.append(*predecessors)
            cell_cycle.reverse()  # We built it from the end.

        if not end:
            successors = list(self.successors(node))
            err = (
                f"Node {node} in lineage of ID {self.graph['lineage_ID']} "
                f"has {len(successors)} successors."
            )
            assert len(successors) == 1, err
            while not self.is_division(*successors) and not self.is_leaf(*successors):
                cell_cycle.append(*successors)
                successors = list(self.successors(*successors))
                err = (
                    f"Node {node} in lineage of ID {self.graph['lineage_ID']} "
                    f"has {len(successors)} successors."
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
            cc_nodes = self.get_cell_cycle(node)
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
