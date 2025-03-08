#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from itertools import pairwise
import types
from typing import Any, Generator, Literal, Tuple

from igraph import Graph
import networkx as nx
from networkx.classes.digraph import DiGraph
import plotly.graph_objects as go

from pycellin.classes.exceptions import FusionError, TimeFlowError


class Lineage(nx.DiGraph, metaclass=ABCMeta):
    """
    Abstract class for a lineage graph.
    """

    def __init__(
        self, nx_digraph: nx.DiGraph | None = None, lineage_ID: int | None = None
    ) -> None:
        """
        Initialize a lineage graph.

        Parameters
        ----------
        nx_digraph : nx.DiGraph, optional
            A NetworkX directed graph to initialize the lineage with,
            by default None.
        lineage_ID : int, optional
            The ID of the lineage, by default None.
        """
        super().__init__(incoming_graph_data=nx_digraph)
        if lineage_ID is not None:
            assert isinstance(lineage_ID, int), "The lineage ID must be an integer."
            self.graph["lineage_ID"] = lineage_ID

    def get_root(self) -> int | list[int]:
        """
        Return the root of the lineage.

        The root is defined as the first node of the lineage temporally speaking,
        i.e. the node with no incoming edges and at least one outgoing edge.
        A lineage normally has one and exactly one root node. However, when in the
        process of modifying the lineage topology, a lineage can temporarily have
        more than one root node.
        In the case where the lineage has only one node, that node is considered
        the root.

        Returns
        -------
        int or list[int]
            The root node of the lineage. If the lineage has more than one root,
            a list of root nodes is returned
        """
        if len(self) == 1:
            roots = [n for n in self.nodes()]
        else:
            roots = [
                n
                for n in self.nodes()
                if self.in_degree(n) == 0 and self.out_degree(n) != 0
            ]
        if len(roots) == 1:
            return roots[0]
        else:
            return roots

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

    def get_ancestors(self, node: int) -> list[int]:
        """
        Return all the ancestors of a given node, in chronological order.

        Chronological order means from the root node to the target node.
        In terms of graph theory, it is the shortest path from the root node
        to the target node.

        Parameters
        ----------
        node : int
            A node of the lineage.

        Returns
        -------
        list[int]
            A list of all the ancestor nodes, from root node to target node.
        """
        root = self.get_root()
        ancestors = nx.shortest_path(self, source=root, target=node)[:-1]
        return ancestors

    def get_descendants(self, node: int) -> list[int]:
        """
        Return all the descendants of a given node.

        Parameters
        ----------
        node : int
            A node of the lineage.

        Returns
        -------
        list[int]
            A list of all the descendant nodes, from target node to leaf nodes.
        """
        descendants = nx.descendants(self, node)
        return list(descendants)

    def is_root(self, node: int) -> bool:
        """
        Check if a given node is a root node.

        The root is defined as the first node of the lineage temporally speaking,
        i.e. the node with no incoming edges.

        Parameters
        ----------
        node : int
            The node to check.

        Returns
        -------
        bool
            True if the node is a root node, False otherwise.
        """
        if self.in_degree(node) == 0:
            return True
        else:
            return False

    def is_leaf(self, node: int) -> bool:
        """
        Check if a given node is a leaf node.

        A leaf node is defined as a node with no outgoing edges.

        Parameters
        ----------
        node : int
            The node to check.

        Returns
        -------
        bool
            True if the node is a leaf node, False otherwise.
        """
        if self.out_degree(node) == 0:
            return True
        else:
            return False

    def get_fusions(self) -> list[int]:
        """
        Return fusion nodes, i.e. nodes with more than one parent.

        Returns
        -------
        list[int]
            The list of fusion nodes in the lineage.
        """
        return [node for node in self.nodes() if self.in_degree(node) > 1]

    @abstractmethod
    def plot(
        self,
        ID_feature: str,
        y_feature: str,
        y_legend: str,
        title: str | None = None,
        node_text: str | None = None,
        node_text_font: dict[str, Any] | None = None,
        node_marker_style: dict[str, Any] | None = None,
        node_colormap_feature: str | None = None,
        node_color_scale: str | None = None,
        node_hover_features: list[str] | None = None,
        edge_line_style: dict[str, Any] | None = None,
        edge_hover_features: list[str] | None = None,
        plot_bgcolor: str | None = None,
        show_horizontal_grid: bool = True,
        showlegend: bool = True,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """
        Plot the lineage as a tree using Plotly.

        Heavily based on the code from https://plotly.com/python/tree-plots/

        Parameters
        ----------
        ID_feature : str
            The feature of the nodes to use as identifier.
        y_feature : str
            The feature of the nodes to use for the y-axis.
        y_legend : str
            The label of the y-axis.
        title : str, optional
            The title of the plot. If None, no title is displayed.
        node_text : str, optional
            The feature of the nodes to display as text inside the nodes
            of the plot. If None, no text is displayed. None by default.
        node_text_font : dict, optional
            The font style of the text inside the nodes (size, color, etc).
            If None, defaults to current Plotly template.
        node_marker_style : dict, optional
            The style of the markers representing the nodes in the plot
            (symbol, size, color, line, etc). If None, defaults to
            current Plotly template.
        node_colormap_feature : str, optional
            The feature of the nodes to use for coloring the nodes.
            If None, no color mapping is applied.
        node_color_scale : str, optional
            The color scale to use for coloring the nodes. If None,
            defaults to current Plotly template.
        node_hover_features : list[str], optional
            The hover template for the nodes. If None, defaults to
            displaying `cell_ID` and the value of the y_feature.
        edge_line_style : dict, optional
            The style of the lines representing the edges in the plot
            (color, width, etc). If None, defaults to current Plotly template.
        edge_hover_features : list[str], optional
            The hover template for the edges. If None, defaults to
            displaying the source and target nodes.
        plot_bgcolor : str, optional
            The background color of the plot. If None, defaults to current
            Plotly template.
        show_horizontal_grid : bool, optional
            True to display the horizontal grid, False otherwise. True by default.
        showlegend : bool, optional
            True to display the legend, False otherwise. True by default.
        width : int, optional
            The width of the plot. If None, defaults to current Plotly template.
        height : int, optional
            The height of the plot. If None, defaults to current Plotly template.

        Warnings
        --------
        In case of cell divisions, the hover text of the edges between the parent
        and child cells will be displayed only for one child cell.
        This cannot easily be corrected.

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

        def get_nodes_position():
            x_nodes = [x for (x, _) in positions.values()]
            y_nodes = [y for (_, y) in positions.values()]
            return x_nodes, y_nodes

        def get_edges_position():
            edges = [edge.tuple for edge in G.es]
            x_edges = []
            y_edges = []
            for edge in edges:
                x_edges += [positions[edge[0]][0], positions[edge[1]][0], None]
                y_edges += [positions[edge[0]][1], positions[edge[1]][1], None]
            return x_edges, y_edges

        def node_text_annotations():
            node_labels = G.vs[node_text]
            if len(node_labels) != nodes_count:
                raise ValueError("The lists pos and text must have the same length.")
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
            return annotations

        def node_feature_color_mapping():
            # TODO: add colorbar units, but the info is stored in the model
            # FIXME: the colorbar is partially hiding the traces names
            node_marker_style["color"] = G.vs[node_colormap_feature]
            node_marker_style["colorscale"] = node_color_scale
            node_marker_style["colorbar"] = dict(title=node_colormap_feature)

        def node_hovertemplate():
            # TODO: when feature is float, display only 2 decimals
            # or give control to the user.
            if node_hover_features:
                node_hover_text = []
                for node in G.vs:
                    text = ""
                    for feat in node_hover_features:
                        if feat not in node.attributes():
                            raise KeyError(
                                f"Feature {feat} is not present in the node attributes."
                            )
                        hover_text = f"{feat}: {node[feat]}<br>"
                        text += hover_text
                    node_hover_text.append(text)
            else:
                node_hover_text = [
                    (
                        f"{ID_feature}: {node[ID_feature]}<br>"
                        f"{y_feature}: {node[y_feature]}"
                    )
                    for node in G.vs
                ]
            if "lineage_ID" in G.attributes():
                graph_name = f"lineage_ID: {G['lineage_ID']}"
            else:
                graph_name = ""
            return node_hover_text, graph_name

        def edge_hover_template():
            edge_hover_text = []
            for edge in G.es:
                source_id = index_to_nx_id[edge.source]
                target_id = index_to_nx_id[edge.target]
                text = f"Source cell_ID: {source_id}<br>Target cell_ID: {target_id}<br>"
                if edge_hover_features:
                    for feat in edge_hover_features:
                        if feat not in edge.attributes():
                            raise KeyError(
                                f"Feature {feat} is not present in the edge attributes."
                            )
                        hover_text = f"{feat}: {edge[feat]}<br>"
                        text += hover_text
                    edge_hover_text += [text, text, text]
            return edge_hover_text

        # Conversion of the networkx lineage graph to igraph.
        G = Graph.from_networkx(self)
        # Create a mapping from networkx node names to igraph vertex indices
        index_to_nx_id = {idx: nx_id for idx, nx_id in enumerate(G.vs["_nx_name"])}
        nodes_count = G.vcount()
        layout = G.layout("rt")  # Basic tree layout.
        # Updating the layout so the y position of the nodes is given
        # by the value of y_feature.
        layout = [(layout[k][0], G.vs[y_feature][k]) for k in range(nodes_count)]

        # Computing the exact positions of nodes and edges.
        positions = {k: layout[k] for k in range(nodes_count)}
        x_nodes, y_nodes = get_nodes_position()
        x_edges, y_edges = get_edges_position()

        # Color mapping the nodes to a node feature.
        if node_colormap_feature:
            if not node_marker_style:
                node_marker_style = dict()
            node_feature_color_mapping()

        # Text in the nodes.
        node_annotations = node_text_annotations() if node_text else None
        # TODO: see if it's better to use a background behind the text
        # https://plotly.com/python/text-and-annotations/#styling-and-coloring-annotations
        # Text when hovering on a node.
        node_hover_text, graph_name = node_hovertemplate()

        # Plot edges.
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x_edges,
                y=y_edges,
                mode="lines",
                line=edge_line_style,
                # hovertemplate="%{text}",
                text=edge_hover_template(),
                name="Edges",
            )
        )
        # Plot nodes.
        fig.add_trace(
            go.Scatter(
                x=x_nodes,
                y=y_nodes,
                mode="markers",
                marker=node_marker_style,
                hoverinfo="text",
                hovertemplate="%{text}",
                text=node_hover_text,  # Used in hoverinfo not for the nodes text.
                name=graph_name,
            )
        )

        fig.update_layout(
            title=title,
            annotations=node_annotations,
            showlegend=showlegend,
            plot_bgcolor=plot_bgcolor,
            hovermode="closest",  # Not ideal but the other modes are far worse.
            width=width,
            height=height,
        )
        fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=False)
        fig.update_yaxes(
            autorange="reversed",
            showgrid=show_horizontal_grid,
            zeroline=show_horizontal_grid,
            title=y_legend,
        )
        fig.show()

    @staticmethod
    def unfreeze(lin: Lineage) -> None:
        """
        Modify graph to allow changes by adding or removing nodes or edges.

        Parameters
        ----------
        lin : Lineage
            The lineage to unfreeze.
        """
        if nx.is_frozen(lin):
            lin.add_node = types.MethodType(DiGraph.add_node, lin)
            lin.add_nodes_from = types.MethodType(DiGraph.add_nodes_from, lin)
            lin.remove_node = types.MethodType(DiGraph.remove_node, lin)
            lin.remove_nodes_from = types.MethodType(DiGraph.remove_nodes_from, lin)
            lin.add_edge = types.MethodType(DiGraph.add_edge, lin)
            lin.add_edges_from = types.MethodType(DiGraph.add_edges_from, lin)
            lin.add_weighted_edges_from = types.MethodType(
                DiGraph.add_weighted_edges_from, lin
            )
            lin.remove_edge = types.MethodType(DiGraph.remove_edge, lin)
            lin.remove_edges_from = types.MethodType(DiGraph.remove_edges_from, lin)
            lin.clear = types.MethodType(DiGraph.clear, lin)
            lin.clear_edges = types.MethodType(DiGraph.clear_edges, lin)
            del lin.frozen


class CellLineage(Lineage):

    def __str__(self) -> str:
        name_txt = f" named {self.graph['name']}" if "name" in self.graph else ""
        txt = (
            f"CellLineage of ID {self.graph['lineage_ID']}{name_txt}"
            f" with {len(self.nodes())} cells and {len(self.edges())} links."
        )
        return txt

    def _get_next_available_node_ID(self) -> int:
        """
        Return the next available node ID in the lineage.

        Returns
        -------
        int
            The next available node ID.
        """
        if len(self.nodes()) == 0:
            return 0
        else:
            return max(self.nodes()) + 1

    def _add_cell(
        self, noi: int | None = None, frame: int | None = 0, **cell_attrs
    ) -> int:
        """
        Add a cell to the lineage graph.

        Parameters
        ----------
        noi : int, optional
            The node ID to assign to the new cell. If None, the next
            available node ID is used.
        frame : int, optional
            The frame of the cell. If None, the frame is set to 0.
        **cell_attrs
            Feature values to set for the node.

        Returns
        -------
        int
            The ID of the newly added cell.

        Raises
        ------
        KeyError
            If the lineage does not have a lineage ID.
        ValueError
            If the cell already exists in the lineage.
        """
        if noi is None:
            noi = self._get_next_available_node_ID()
        elif noi in self.nodes():
            raise ValueError(
                f"Cell {noi} already exists in the lineage "
                f"with ID {self.graph['lineage_ID']}."
            )
        self.add_node(noi, **cell_attrs)
        self.nodes[noi]["cell_ID"] = noi
        self.nodes[noi]["frame"] = frame
        return noi

    def _remove_cell(self, noi: int) -> dict[str, Any]:
        """
        Remove a cell from the lineage graph.

        It also removes all adjacent edges.

        Parameters
        ----------
        noi : int
            The node ID of the cell to remove.

        Returns
        -------
        dict[str, Any]
            The feature values of the removed node.

        Raises
        ------
        KeyError
            If the cell does not exist in the lineage.
        """
        try:
            cell_attrs = self.nodes[noi]
        except KeyError as err:
            _, txt = CellLineage._get_lineage_ID_and_err_msg(self)
            msg = f"Cell {noi} does not exist{txt}."
            raise KeyError(msg) from err
        self.remove_node(noi)
        return cell_attrs

    def _add_link(
        self,
        source_noi: int,
        target_noi: int,
        target_lineage: CellLineage | None = None,
        **link_attrs,
    ) -> None:
        """
        Create a link beween 2 cells.

        The 2 cells can be in the same lineage or in different lineages.
        However, the linking cannot be done if it leads to a fusion event,
        i. e. a cell with more than one parent.

        Parameters
        ----------
        source_noi : int
            The node ID of the source cell.
        target_noi : int
            The node ID of the target cell.
        target_lineage : CellLineage, optional
            The lineage of the target cell. If None, the target cell is
            assumed to be in the same lineage as the source cell.
        **link_attrs
            Feature values to set for the edge.

        Raises
        ------
        ValueError
            If the source or target cell does not exist in the lineage.
            If the edge already exists in the lineage.
        FusionError
            If the target cell already has a parent cell.
        TimeFlowError
            If the target cell happens before the source cell.
        """
        source_lineage_ID, txt_src = CellLineage._get_lineage_ID_and_err_msg(self)

        if target_lineage is not None:
            target_lineage_ID, txt_tgt = CellLineage._get_lineage_ID_and_err_msg(
                target_lineage
            )
        else:
            target_lineage = self
            target_lineage_ID = source_lineage_ID
            txt_tgt = txt_src
            # If the link already exists, NetworX does not raise an error but updates
            # the already existing link, potentially overwriting edge attributes.
            # To avoid any unwanted modifications to the lineage, we raise an error.
            if self.has_edge(source_noi, target_noi):
                raise ValueError(
                    f"Link 'Cell {source_noi} -> Cell {target_noi}' "
                    f"already exists{txt_tgt}."
                )

        # NetworkX does not raise an error if the cells don't exist,
        # it creates them along the link. To avoid any unwanted modifications
        # to the lineage, we raise an error if the cells don't exist.
        if source_noi not in self.nodes():
            raise ValueError(f"Source cell (ID {source_noi}) does not exist{txt_src}.")
        if target_noi not in target_lineage.nodes():
            raise ValueError(f"Target cell (ID {target_noi}) does not exist{txt_tgt}.")

        # Check that the link will not create a fusion event.
        if target_lineage.in_degree(target_noi) != 0:
            try:
                raise FusionError(target_noi, source_lineage_ID)
            except Exception as err:
                note = (
                    f"Remove any incoming edge to node {target_noi} "
                    f"before adding a new incoming edge."
                )
                err.add_note(note)
                raise err

        # Check that the link respects the flow of time.
        if self.nodes[source_noi]["frame"] >= target_lineage.nodes[target_noi]["frame"]:
            raise TimeFlowError(
                source_noi,
                target_noi,
                source_lineage_ID,
                target_lineage_ID,
            )

        if target_lineage != self:
            # Identify cell ID conflict between lineages.
            target_descendants = nx.descendants(target_lineage, target_noi)
            conflicting_ids = set(self.nodes()) & set(target_descendants)
            if conflicting_ids:
                next_id = self._get_next_available_node_ID()
                ids_mapping = {}
                for id in conflicting_ids:
                    ids_mapping[id] = next_id
                    next_id += 1

            # Create a new lineage from the target cell and its descendants,
            # including links.
            tmp_lineage = target_lineage._split_from_cell(target_noi)
            if conflicting_ids:
                nx.relabel_nodes(tmp_lineage, ids_mapping, copy=False)
                if target_noi in ids_mapping:
                    target_noi = ids_mapping[target_noi]
                assert tmp_lineage.get_root() == target_noi

            # Merge all the elements of the target lineage into the source lineage.
            self.update(
                edges=tmp_lineage.edges(data=True), nodes=tmp_lineage.nodes(data=True)
            )
            del tmp_lineage

        self.add_edge(source_noi, target_noi, **link_attrs)

    def _remove_link(self, source_noi: int, target_noi: int) -> dict[str, Any]:
        """
        Remove a link between two cells.

        This doesn't create a new lineage but divides the lineage graph into
        two weakly connected components: one for all the cells upstream
        of the removed edge, and one for all the cells downstream.
        To divide a lineage into two separate lineages,
        use the `_split_from_cell` or `_split_from_link` methods.

        Parameters
        ----------
        source_noi : int
            The node ID of the source cell.
        target_noi : int
            The node ID of the target cell.

        Returns
        -------
        dict[str, Any]
            The feature values of the removed edge.

        Raises
        ------
        ValueError
            If the source or target cell does not exist in the lineage.
        KeyError
            If the link does not exist in the lineage.
        """
        _, txt = CellLineage._get_lineage_ID_and_err_msg(self)
        if source_noi not in self.nodes():
            raise ValueError(f"Source cell (ID {source_noi}) does not exist{txt}.")
        if target_noi not in self.nodes():
            raise ValueError(f"Target cell (ID {target_noi}) does not exist{txt}.")

        try:
            link_attrs = self[source_noi][target_noi]
        except KeyError as err:
            raise KeyError(
                f"Link 'Cell {source_noi} -> Cell {target_noi}' does not exist{txt}."
            ) from err
        self.remove_edge(source_noi, target_noi)
        return link_attrs

    def _split_from_cell(
        self,
        noi: int,
        split: Literal["upstream", "downstream"] = "upstream",
    ) -> CellLineage:
        """
        From a given cell, split a part of the lineage into a new lineage.

        Parameters
        ----------
        noi : int
            The node ID of the cell from which to split the lineage.
        split : {"upstream", "downstream"}, optional
            Where to split the lineage relative to the given cell.
            If upstream, the given cell is included in the second lineage.
            If downstream, the given cell is included in the first lineage.
            "upstream" by default.

        Returns
        -------
        CellLineage
            The new lineage created from the split.

        Raises
        ------
        ValueError
            If the cell does not exist in the lineage.
            If the split parameter is not "upstream" or "downstream"
        """
        _, txt = CellLineage._get_lineage_ID_and_err_msg(self)
        if noi not in self.nodes():
            raise ValueError(f"Source cell (ID {noi}) does not exist{txt}.")

        if split == "upstream":
            nodes = nx.descendants(self, noi) | {noi}
        elif split == "downstream":
            nodes = nx.descendants(self, noi)
        else:
            raise ValueError("The split parameter must be 'upstream' or 'downstream'.")
        new_lineage = self.subgraph(nodes).copy()
        self.remove_nodes_from(nodes)
        return new_lineage

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
        Give all the nodes in the cell cycle of a given node, in chronological order.

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

        Raises
        ------
        FusionError
            If the given node has more than one predecessor.
        """
        # TODO: factorize
        lineage_ID, _ = CellLineage._get_lineage_ID_and_err_msg(self)
        cell_cycle = [node]
        start = False
        end = False

        if self.is_root(node):
            start = True
        if self.is_division(node) or self.is_leaf(node):
            end = True

        if not start:
            predecessors = list(self.predecessors(node))
            if len(predecessors) != 1:
                try:
                    raise FusionError(node, lineage_ID)
                except Exception as err:
                    note = f"This node has {len(predecessors)} predecessors."
                    err.add_note(note)
                    raise err
            while not self.is_division(*predecessors) and not self.is_root(
                *predecessors
            ):
                # While not the generation birth.
                cell_cycle.append(*predecessors)
                predecessors = list(self.predecessors(*predecessors))
                if len(predecessors) != 1:
                    try:
                        raise FusionError(node, lineage_ID)
                    except Exception as err:
                        note = f"This node has {len(predecessors)} predecessors."
                        err.add_note(note)
                        raise err
            if self.is_root(*predecessors) and not self.is_division(*predecessors):
                cell_cycle.append(*predecessors)
            cell_cycle.reverse()  # We built it from the end.

        if not end:
            successors = list(self.successors(node))
            err = (
                f"Something went wrong: division detected in the cell cycle "
                f"of node {node}. This node has {len(successors)} successors."
            )
            assert len(successors) == 1, err
            while not self.is_division(*successors) and not self.is_leaf(*successors):
                cell_cycle.append(*successors)
                successors = list(self.successors(*successors))
                err = (
                    f"Something went wrong: division detected in the cell cycle "
                    f"of node {node}. This node has {len(successors)} successors."
                )
                assert len(successors) == 1, err
            cell_cycle.append(*successors)

        return cell_cycle

    def get_cell_cycles(
        self, keep_incomplete_cell_cycles: bool = False, debug: bool = False
    ) -> list[list[int]]:
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

    def get_sister_cells(self, noi: int) -> list[int]:
        """
        Return the sister cells of a given cell.

        Sister cells are cells that are on the same frame
        and share the same parent cell.

        Parameters
        ----------
        noi : int
            Node ID of the cell of interest, for which
            to find the sister cells.

        Returns
        -------
        list[int]
            The list of node IDs of the sister cells of the given node.

        Raises
        ------
        FusionError
            If the given cell has more than one parent cell.
        """
        sister_cells = []
        current_frame = self.nodes[noi]["frame"]
        if not self.is_root(noi):
            current_cell_cycle = self.get_cell_cycle(noi)
            parents = list(self.predecessors(current_cell_cycle[0]))
            if len(parents) == 1:
                children = list(self.successors(parents[0]))
                children.remove(current_cell_cycle[0])
                for child in children:
                    sister_cell_cycle = self.get_cell_cycle(child)
                    sister_cells.extend(
                        [
                            n
                            for n in sister_cell_cycle
                            if self.nodes[n]["frame"] == current_frame
                        ]
                    )
            elif len(parents) > 1:
                lineage_ID, _ = CellLineage._get_lineage_ID_and_err_msg(self)
                raise FusionError(noi, lineage_ID)
        return sister_cells

    def is_division(self, node: int) -> bool:
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

    # def get_cousin_cells(
    #     self, node: int, max_ancestry_level: int = 0
    # ) -> dict[int, list[int]]:
    #     """
    #     Return the cousin cells of a given cell.

    #     Cousin cells are cells that are on the same frame
    #     and share a common ancestor.

    #     Parameters
    #     ----------
    #     node : int
    #         The cell for which to identify the cousin cells.
    #     max_ancestry_level : int, optional
    #         The maximum level of ancestry to consider. If 0, all ancestry levels
    #         are considered. 0 by default.
    #     """
    #     if self.is_root(node):
    #         return []

    #     candidate_nodes = [
    #         n
    #         for n in self.nodes()
    #         if self.nodes[n]["frame"] == self.nodes[node]["frame"]
    #     ]
    #     # How to define
    #     # ancestors = self.get_ancestors(self.get_root(), node)
    #     # ancestor_divs = [a for a in ancestors if self.is_division(a)]
    #     # for div in ancestor_divs:
    #     #     pass

    def plot(
        self,
        title: str | None = None,
        node_text: str | None = None,
        node_text_font: dict[str, Any] | None = None,
        node_marker_style: dict[str, Any] | None = None,
        node_colormap_feature: str | None = None,
        node_color_scale: str | None = None,
        node_hover_features: list[str] | None = None,
        edge_line_style: dict[str, Any] | None = None,
        edge_hover_features: list[str] | None = None,
        plot_bgcolor: str | None = None,
        show_horizontal_grid: bool = True,
        showlegend: bool = True,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """
        Plot the cell lineage as a tree using Plotly.

        Parameters
        ----------
        title : str, optional
            The title of the plot. If None, no title is displayed.
        node_text : str, optional
            The feature of the nodes to display as text inside the nodes
            of the plot. If None, no text is displayed. None by default.
        node_text_font : dict, optional
            The font style of the text inside the nodes (size, color, etc).
            If None, defaults to current Plotly template.
        node_marker_style : dict, optional
            The style of the markers representing the nodes in the plot
            (symbol, size, color, line, etc). If None, defaults to
            current Plotly template.
        node_colormap_feature : str, optional
            The feature of the nodes to use for coloring the nodes.
            If None, no color mapping is applied.
        node_color_scale : str, optional
            The color scale to use for coloring the nodes. If None,
            defaults to current Plotly template.
        node_hover_features : list[str], optional
            The hover template for the nodes. If None, defaults to
            displaying `cell_ID` and the value of the y_feature.
        edge_line_style : dict, optional
            The style of the lines representing the edges in the plot
            (color, width, etc). If None, defaults to current Plotly template.
        edge_hover_features : list[str], optional
            The hover template for the edges. If None, defaults to
            displaying the source and target nodes.
        plot_bgcolor : str, optional
            The background color of the plot. If None, defaults to current
            Plotly template.
        show_horizontal_grid : bool, optional
            True to display the horizontal grid, False otherwise. True by default.
        showlegend : bool, optional
            True to display the legend, False otherwise. True by default.
        width : int, optional
            The width of the plot. If None, defaults to current Plotly template.
        height : int, optional
            The height of the plot. If None, defaults to current Plotly template.

        Warnings
        --------
        In case of cell divisions, the hover text of the edges between the parent
        and child cells will be displayed only for one child cell.
        This cannot easily be corrected.

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
        # TODO: and if we want to plot in time units instead of frames?
        super().plot(
            ID_feature="cell_ID",
            y_feature="frame",
            y_legend="Time (frames)",
            title=title,
            node_text=node_text,
            node_text_font=node_text_font,
            node_marker_style=node_marker_style,
            node_colormap_feature=node_colormap_feature,
            node_color_scale=node_color_scale,
            node_hover_features=node_hover_features,
            edge_line_style=edge_line_style,
            edge_hover_features=edge_hover_features,
            plot_bgcolor=plot_bgcolor,
            show_horizontal_grid=show_horizontal_grid,
            showlegend=showlegend,
            width=width,
            height=height,
        )

    @staticmethod
    # TODO: I don't think this function is good design, even if it factorises code.
    def _get_lineage_ID_and_err_msg(lineage):
        """
        Return the lineage ID and a text to display in error messages.

        Parameters
        ----------
        lineage : CellLineage
            The lineage from which to extract the lineage ID.

        Returns
        -------
        int | None
            The lineage ID.
        str
            The text to display in error messages.
        """
        try:
            lineage_ID = lineage.graph["lineage_ID"]
            txt = f" in lineage {lineage_ID}"
        except KeyError:
            lineage_ID = None
            txt = ""
        return lineage_ID, txt


class CycleLineage(Lineage):

    def __init__(self, cell_lineage: CellLineage | None = None) -> None:
        super().__init__()

        if cell_lineage:
            # Creating nodes.
            divs = cell_lineage.get_divisions()
            leaves = cell_lineage.get_leaves()
            self.add_nodes_from(divs + leaves)

            # Adding corresponding edges.
            for n in divs:
                for successor in cell_lineage.successors(n):
                    self.add_edge(n, cell_lineage.get_cell_cycle(successor)[-1])

            # Freezing the structure since it's mapped on the cell lineage one.
            nx.freeze(self)

            # Adding node and graph features.
            self.graph["lineage_ID"] = cell_lineage.graph["lineage_ID"]
            for n in divs + leaves:
                self.nodes[n]["lineage_ID"] = cell_lineage.graph["lineage_ID"]
                self.nodes[n]["cycle_ID"] = n
                self.nodes[n]["cells"] = cell_lineage.get_cell_cycle(n)
                self.nodes[n]["cycle_length"] = len(self.nodes[n]["cells"])
                self.nodes[n]["level"] = nx.shortest_path_length(
                    self, self.get_root(), n
                )
            # cell_cycle completeness?
            # div_time?
            # Or I add it later with add_custom_feature()?

    def __str__(self) -> str:
        name_txt = f" named {self.graph['name']}" if "name" in self.graph else ""
        txt = (
            f"CycleLineage of ID {self.graph['lineage_ID']}{name_txt}"
            f" with {len(self.nodes())} cell cycles and {len(self.edges())} links."
        )
        return txt

    # Methods to freeze / unfreeze?

    def get_edges_within_cycle(self, noi: int) -> list[tuple[int, int]]:
        """
        Return the edges within a cell cycle.

        Parameters
        ----------
        noi : int
            The node ID of the cell cycle.

        Returns
        -------
        list[tuple(int, int)]
            A list of edges within the cell cycle.
        """
        return list(pairwise(self.nodes[noi]["cells"]))

    def yield_edges_within_cycle(
        self, noi: int
    ) -> Generator[Tuple[int, int], None, None]:
        """
        Yield the edges within a cell cycle.

        Parameters
        ----------
        noi : int
            The node ID of the cell cycle.

        Yields
        ------
        tuple(int, int)
            The edges within the cell cycle.
        """
        for edge in pairwise(self.nodes[noi]["cells"]):
            yield edge

    def plot(
        self,
        title: str | None = None,
        node_text: str | None = None,
        node_text_font: dict[str, Any] | None = None,
        node_marker_style: dict[str, Any] | None = None,
        node_colormap_feature: str | None = None,
        node_color_scale: str | None = None,
        node_hover_features: list[str] | None = None,
        edge_line_style: dict[str, Any] | None = None,
        edge_hover_features: list[str] | None = None,
        plot_bgcolor: str | None = None,
        show_horizontal_grid: bool = True,
        showlegend: bool = True,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """
        Plot the cell cycle lineage as a tree using Plotly.

        Parameters
        ----------
        title : str, optional
            The title of the plot. If None, no title is displayed.
        node_text : str, optional
            The feature of the nodes to display as text inside the nodes
            of the plot. If None, no text is displayed. None by default.
        node_text_font : dict, optional
            The font style of the text inside the nodes (size, color, etc).
            If None, defaults to current Plotly template.
        node_marker_style : dict, optional
            The style of the markers representing the nodes in the plot
            (symbol, size, color, line, etc). If None, defaults to
            current Plotly template.
        node_colormap_feature : str, optional
            The feature of the nodes to use for coloring the nodes.
            If None, no color mapping is applied.
        node_color_scale : str, optional
            The color scale to use for coloring the nodes. If None,
            defaults to current Plotly template.
        node_hover_features : list[str], optional
            The hover template for the nodes. If None, defaults to
            displaying `cell_ID` and the value of the y_feature.
        edge_line_style : dict, optional
            The style of the lines representing the edges in the plot
            (color, width, etc). If None, defaults to current Plotly template.
        edge_hover_features : list[str], optional
            The hover template for the edges. If None, defaults to
            displaying the source and target nodes.
        plot_bgcolor : str, optional
            The background color of the plot. If None, defaults to current
            Plotly template.
        show_horizontal_grid : bool, optional
            True to display the horizontal grid, False otherwise. True by default.
        showlegend : bool, optional
            True to display the legend, False otherwise. True by default.
        width : int, optional
            The width of the plot. If None, defaults to current Plotly template.
        height : int, optional
            The height of the plot. If None, defaults to current Plotly template.

        Warnings
        --------
        In case of cell divisions, the hover text of the edges between the parent
        and child cells will be displayed only for one child cell.
        This cannot easily be corrected.

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
        super().plot(
            ID_feature="cycle_ID",
            y_feature="level",
            y_legend="Cell cycle level",
            title=title,
            node_text=node_text,
            node_text_font=node_text_font,
            node_marker_style=node_marker_style,
            node_colormap_feature=node_colormap_feature,
            node_color_scale=node_color_scale,
            node_hover_features=node_hover_features,
            edge_line_style=edge_line_style,
            edge_hover_features=edge_hover_features,
            plot_bgcolor=plot_bgcolor,
            show_horizontal_grid=show_horizontal_grid,
            showlegend=showlegend,
            width=width,
            height=height,
        )
