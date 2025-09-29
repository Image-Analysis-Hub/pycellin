#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from abc import ABCMeta, abstractmethod
from itertools import pairwise
from typing import Any, Generator, Literal, Tuple
import warnings

from igraph import Graph
import networkx as nx
import plotly.graph_objects as go

from pycellin.classes.exceptions import (
    FusionError,
    TimeFlowError,
    LineageStructureError,
)


class Lineage(nx.DiGraph, metaclass=ABCMeta):
    """
    Abstract class for a lineage graph.
    """

    def __init__(self, nx_digraph: nx.DiGraph | None = None, lid: int | None = None) -> None:
        """
        Initialize a lineage graph.

        Parameters
        ----------
        nx_digraph : nx.DiGraph, optional
            A NetworkX directed graph to initialize the lineage with,
            by default None.
        lid : int, optional
            The ID of the lineage, by default None.
        """
        super().__init__(incoming_graph_data=nx_digraph)
        if lid is not None:
            assert isinstance(lid, int), "The lineage ID must be an integer."
            self.graph["lineage_ID"] = lid

    def _remove_prop(self, prop_name: str, prop_type: str) -> None:
        """
        Remove a property from the lineage graph based on the property type.

        Parameters
        ----------
        prop_name : str
            The name of the property to remove.
        prop_type : str
            The type of property to remove. Must be one of `node`, `edge`, or `lineage`.

        Raises
        ------
        ValueError
            If the prop_type is not one of `node`, `edge`, or `lineage`.
        """
        match prop_type:
            case "node":
                for _, data in self.nodes(data=True):
                    data.pop(prop_name, None)
            case "edge":
                for _, _, data in self.edges(data=True):
                    data.pop(prop_name, None)
            case "lineage":
                self.graph.pop(prop_name, None)
            case _:
                raise ValueError("Invalid prop_type. Must be one of 'node', 'edge', or 'lineage'.")

    def get_root(self, ignore_lone_nodes: bool = False) -> int | list[int]:
        """
        Return the root of the lineage.

        The root is defined as the node with no incoming edges and usually at
        least one outgoing edge.
        A lineage normally has one and exactly one root node. However, when in the
        process of modifying the lineage topology, a lineage can temporarily have
        more than one.

        Parameters
        ----------
        ignore_lone_nodes : bool, optional
            True to ignore nodes with no incoming and outgoing edges, False otherwise.
            False by default.

        Returns
        -------
        int or list[int]
            The root node of the lineage. If the lineage has more than one root,
            a list of root nodes is returned
        """
        if ignore_lone_nodes:
            roots = [
                n
                for n in self.nodes()
                if self.in_degree(n) == 0 and self.out_degree(n) > 0  # type: ignore
            ]
        else:
            roots = [n for n in self.nodes() if self.in_degree(n) == 0]
        if len(roots) == 1:
            return roots[0]
        else:
            return roots

    def get_leaves(self, ignore_lone_nodes: bool = False) -> list[int]:
        """
        Return the leaves of the lineage.

        A leaf is a node with no outgoing edges and one or less incoming edge.

        Parameters
        ----------
        ignore_lone_nodes : bool, optional
            True to ignore nodes with no incoming and outgoing edges, False otherwise.
            False by default.

        Returns
        -------
        list[int]
            The list of leaf nodes in the lineage.
        """
        if ignore_lone_nodes:
            leaves = [n for n in self.nodes() if self.in_degree(n) != 0 and self.out_degree(n) == 0]
        else:
            leaves = [n for n in self.nodes() if self.out_degree(n) == 0]
        return leaves

    def get_ancestors(self, nid: int) -> list[int]:
        """
        Return all the ancestors of a given node.

        Chronological order means from the root node to the target node.
        In terms of graph theory, it is the shortest path from the root node
        to the target node.

        Parameters
        ----------
        nid : int
            ID of the node for which to find ancestors.

        Returns
        -------
        list[int]
            A list of all the ancestor nodes.
        """
        ancestors = list(nx.ancestors(self, nid))
        return ancestors

    def get_descendants(self, nid: int) -> list[int]:
        """
        Return all the descendants of a given node.

        Parameters
        ----------
        nid : int
            ID of the node for which to find descendants.

        Returns
        -------
        list[int]
            A list of all the descendant nodes, from target node to leaf nodes.
        """
        descendants = nx.descendants(self, nid)
        return list(descendants)

    def is_root(self, nid: int) -> bool:
        """
        Check if a given node is a root node.

        The root is defined as the first node of the lineage temporally speaking,
        i.e. the node with no incoming edges.

        Parameters
        ----------
        nid : int
            ID of the node to check.

        Returns
        -------
        bool
            True if the node is a root node, False otherwise.
        """
        if self.in_degree(nid) == 0:
            return True
        else:
            return False

    def is_leaf(self, nid: int) -> bool:
        """
        Check if a given node is a leaf node.

        A leaf node is defined as a node with no outgoing edges.

        Parameters
        ----------
        nid : int
            ID of the node to check.

        Returns
        -------
        bool
            True if the node is a leaf node, False otherwise.
        """
        if self.out_degree(nid) == 0:
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
        return [n for n in self.nodes() if self.in_degree(n) > 1]  # type: ignore

    @abstractmethod
    def plot(
        self,
        ID_prop: str,
        y_prop: str,
        y_legend: str,
        title: str | None = None,
        node_text: str | None = None,
        node_text_font: dict[str, Any] | None = None,
        node_marker_style: dict[str, Any] | None = None,
        node_colormap_prop: str | None = None,
        node_color_scale: str | None = None,
        node_hover_props: list[str] | None = None,
        edge_line_style: dict[str, Any] | None = None,
        edge_hover_props: list[str] | None = None,
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
        ID_prop : str
            The property of the nodes to use as identifier.
        y_prop : str
            The property of the nodes to use for the y-axis.
        y_legend : str
            The label of the y-axis.
        title : str, optional
            The title of the plot. If None, no title is displayed.
        node_text : str, optional
            The property of the nodes to display as text inside the nodes
            of the plot. If None, no text is displayed. None by default.
        node_text_font : dict, optional
            The font style of the text inside the nodes (size, color, etc).
            If None, defaults to current Plotly template.
        node_marker_style : dict, optional
            The style of the markers representing the nodes in the plot
            (symbol, size, color, line, etc). If None, defaults to
            current Plotly template.
        node_colormap_prop : str, optional
            The property of the nodes to use for coloring the nodes.
            If None, no color mapping is applied.
        node_color_scale : str, optional
            The color scale to use for coloring the nodes. If None,
            defaults to current Plotly template.
        node_hover_props : list[str], optional
            The hover template for the nodes. If None, defaults to
            displaying `cell_ID` and the value of the y_prop.
        edge_line_style : dict, optional
            The style of the lines representing the edges in the plot
            (color, width, etc). If None, defaults to current Plotly template.
        edge_hover_props : list[str], optional
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

        def node_prop_color_mapping():
            # TODO: add colorbar units, but the info is stored in the model
            # FIXME: the colorbar is partially hiding the traces names
            assert node_marker_style is not None
            node_marker_style["color"] = G.vs[node_colormap_prop]
            node_marker_style["colorscale"] = node_color_scale
            node_marker_style["colorbar"] = dict(title=node_colormap_prop)

        def node_hovertemplate():
            # TODO: when property is float, display only 2 decimals
            # or give control to the user.
            if node_hover_props:
                node_hover_text = []
                for node in G.vs:
                    text = ""
                    for prop in node_hover_props:
                        if prop not in node.attributes():
                            raise KeyError(
                                f"Property {prop} is not present in the node attributes."
                            )
                        hover_text = f"{prop}: {node[prop]}<br>"
                        text += hover_text
                    node_hover_text.append(text)
            else:
                node_hover_text = [
                    (f"{ID_prop}: {node[ID_prop]}<br>{y_prop}: {node[y_prop]}") for node in G.vs
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
                if edge_hover_props:
                    for prop in edge_hover_props:
                        if prop not in edge.attributes():
                            raise KeyError(
                                f"Property {prop} is not present in the edge attributes."
                            )
                        hover_text = f"{prop}: {edge[prop]}<br>"
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
        # by the value of y_prop.
        layout = [(layout[k][0], G.vs[y_prop][k]) for k in range(nodes_count)]

        # Computing the exact positions of nodes and edges.
        positions = {k: layout[k] for k in range(nodes_count)}
        x_nodes, y_nodes = get_nodes_position()
        x_edges, y_edges = get_edges_position()

        # Color mapping the nodes to a node property.
        if node_colormap_prop:
            if not node_marker_style:
                node_marker_style = dict()
            node_prop_color_mapping()

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

    # @staticmethod
    # def unfreeze(lin: Lineage) -> None:
    #     """
    #     Modify graph to allow changes by adding or removing nodes or edges.

    #     Parameters
    #     ----------
    #     lin : Lineage
    #         The lineage to unfreeze.
    #     """
    #     if nx.is_frozen(lin):
    #         lin.add_node = types.MethodType(DiGraph.add_node, lin)
    #         lin.add_nodes_from = types.MethodType(DiGraph.add_nodes_from, lin)
    #         lin.remove_node = types.MethodType(DiGraph.remove_node, lin)
    #         lin.remove_nodes_from = types.MethodType(DiGraph.remove_nodes_from, lin)
    #         lin.add_edge = types.MethodType(DiGraph.add_edge, lin)
    #         lin.add_edges_from = types.MethodType(DiGraph.add_edges_from, lin)
    #         lin.add_weighted_edges_from = types.MethodType(
    #             DiGraph.add_weighted_edges_from, lin
    #         )
    #         lin.remove_edge = types.MethodType(DiGraph.remove_edge, lin)
    #         lin.remove_edges_from = types.MethodType(DiGraph.remove_edges_from, lin)
    #         lin.clear = types.MethodType(DiGraph.clear, lin)
    #         lin.clear_edges = types.MethodType(DiGraph.clear_edges, lin)
    #         del lin.frozen


class CellLineage(Lineage):
    def __str__(self) -> str:
        name_txt = f" named {self.graph['name']}" if "name" in self.graph else ""
        txt = (
            f"CellLineage of ID {self.graph['lineage_ID']}{name_txt}"
            f" with {len(self)} cells and {len(self.edges())} links."
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
        if len(self) == 0:
            return 0
        else:
            return max(self.nodes()) + 1

    def _add_cell(
        self,
        nid: int | None = None,
        time_point: int | float = 0,
        time_prop: str = "frame",
        **cell_props,
    ) -> int:
        """
        Add a cell to the lineage graph.

        Parameters
        ----------
        nid : int, optional
            The node ID to assign to the new cell. If None, the next
            available node ID is used.
        time_point : int | float, optional
            The time point of the cell. If None, the time point is set to 0.
        time_prop : str, optional
            The property name to use for the time point. Default is "frame".
        **cell_props
            Property values to set for the node.

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
        if nid is None:
            nid = self._get_next_available_node_ID()
        elif nid in self.nodes():
            _, txt = CellLineage._get_lineage_ID_and_err_msg(self)
            msg = f"Cell {nid} already exists{txt}."
            raise ValueError(msg)
        self.add_node(nid, **cell_props)
        self.nodes[nid]["cell_ID"] = nid
        self.nodes[nid][time_prop] = time_point
        return nid

    def _remove_cell(self, nid: int) -> dict[str, Any]:
        """
        Remove a cell from the lineage graph.

        It also removes all adjacent edges.

        Parameters
        ----------
        nid : int
            The node ID of the cell to remove.

        Returns
        -------
        dict[str, Any]
            The property values of the removed node.

        Raises
        ------
        KeyError
            If the cell does not exist in the lineage.
        """
        try:
            cell_props = self.nodes[nid]
        except KeyError as err:
            _, txt = CellLineage._get_lineage_ID_and_err_msg(self)
            msg = f"Cell {nid} does not exist{txt}."
            raise KeyError(msg) from err
        self.remove_node(nid)
        return cell_props

    def _add_link(
        self,
        source_nid: int,
        target_nid: int,
        target_lineage: CellLineage | None = None,
        **link_props,
    ) -> dict[int, int] | None:
        """
        Create a link beween 2 cells.

        The 2 cells can be in the same lineage or in different lineages.
        However, the linking cannot be done if it leads to a fusion event,
        i. e. a cell with more than one parent.

        Parameters
        ----------
        source_nid : int
            The node ID of the source cell.
        target_nid : int
            The node ID of the target cell.
        target_lineage : CellLineage, optional
            The lineage of the target cell. If None, the target cell is
            assumed to be in the same lineage as the source cell.
        **link_props
            Property values to set for the edge.

        Returns
        -------
        dict[int, int] or None
            A dictionary of renamed cells {old_ID : new_ID} from
            the target lineage when it had conflicting cell IDs with the
            source lineage. None otherwise.

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
        source_lid, txt_src = CellLineage._get_lineage_ID_and_err_msg(self)

        if target_lineage is not None:
            target_lid, txt_tgt = CellLineage._get_lineage_ID_and_err_msg(target_lineage)
        else:
            target_lineage = self
            target_lid = source_lid
            txt_tgt = txt_src
            # If the link already exists, NetworX does not raise an error but updates
            # the already existing link, potentially overwriting edge attributes.
            # To avoid any unwanted modifications to the lineage, we raise an error.
            if self.has_edge(source_nid, target_nid):
                raise ValueError(
                    f"Link 'Cell {source_nid} -> Cell {target_nid}' already exists{txt_tgt}."
                )

        # NetworkX does not raise an error if the cells don't exist,
        # it creates them along the link. To avoid any unwanted modifications
        # to the lineage, we raise an error if the cells don't exist.
        if source_nid not in self.nodes():
            raise ValueError(f"Source cell (ID {source_nid}) does not exist{txt_src}.")
        if target_nid not in target_lineage.nodes():
            raise ValueError(f"Target cell (ID {target_nid}) does not exist{txt_tgt}.")

        # Check that the link will not create a fusion event.
        if target_lineage.in_degree(target_nid) != 0:
            raise FusionError(target_nid, source_lid)

        # Check that the link respects the flow of time.
        if self.nodes[source_nid]["frame"] >= target_lineage.nodes[target_nid]["frame"]:
            raise TimeFlowError(
                source_nid,
                target_nid,
                source_lid,
                target_lid,
            )

        conflicting_ids = None
        if target_lineage != self:
            # Identify cell ID conflict between lineages.
            target_descendants = nx.descendants(target_lineage, target_nid) | {target_nid}
            conflicting_ids = set(self.nodes()) & set(target_descendants)
            if conflicting_ids:
                next_id = self._get_next_available_node_ID()
                ids_mapping = {}  # a dict of {old_ID : new_ID}
                for id in conflicting_ids:
                    ids_mapping[id] = next_id
                    next_id += 1

            # Create a new lineage from the target cell and its descendants,
            # including links.
            tmp_lineage = target_lineage._split_from_cell(target_nid)
            if conflicting_ids:
                nx.relabel_nodes(tmp_lineage, ids_mapping, copy=False)
                for id, new_id in ids_mapping.items():
                    tmp_lineage.nodes[new_id]["cell_ID"] = new_id
                if target_nid in ids_mapping:
                    target_nid = ids_mapping[target_nid]
                assert tmp_lineage.get_root() == target_nid

            # Merge all the elements of the target lineage into the source lineage.
            self.update(
                edges=tmp_lineage.edges(data=True),
                nodes=tmp_lineage.nodes(data=True),
            )
            del tmp_lineage

        self.add_edge(source_nid, target_nid, **link_props)
        return ids_mapping if conflicting_ids else None

    def _remove_link(self, source_nid: int, target_nid: int) -> dict[str, Any]:
        """
        Remove a link between two cells.

        This doesn't create a new lineage but divides the lineage graph into
        two weakly connected components: one for all the cells upstream
        of the removed edge, and one for all the cells downstream.
        To divide a lineage into two separate lineages,
        use the `_split_from_cell` or `_split_from_link` methods.

        Parameters
        ----------
        source_nid : int
            The node ID of the source cell.
        target_nid : int
            The node ID of the target cell.

        Returns
        -------
        dict[str, Any]
            The property values of the removed edge.

        Raises
        ------
        ValueError
            If the source or target cell does not exist in the lineage.
        KeyError
            If the link does not exist in the lineage.
        """
        _, txt = CellLineage._get_lineage_ID_and_err_msg(self)
        if source_nid not in self.nodes():
            raise ValueError(f"Source cell (ID {source_nid}) does not exist{txt}.")
        if target_nid not in self.nodes():
            raise ValueError(f"Target cell (ID {target_nid}) does not exist{txt}.")

        try:
            link_props = self[source_nid][target_nid]
        except KeyError as err:
            raise KeyError(
                f"Link 'Cell {source_nid} -> Cell {target_nid}' does not exist{txt}."
            ) from err
        self.remove_edge(source_nid, target_nid)
        return link_props

    def _split_from_cell(
        self,
        nid: int,
        split: Literal["upstream", "downstream"] = "upstream",
    ) -> CellLineage:
        """
        From a given cell, split a part of the lineage into a new lineage.

        Parameters
        ----------
        nid : int
            The node ID of the cell from which to split the lineage.
        split : {"upstream", "downstream"}, optional
            Where to split the lineage relative to the given cell.
            If upstream, the given cell becomes the root of the newly
            created lineage. If downstream, the given cell stays in the initial
            lineage but its descendants all go in the newly created lineage.
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
        if nid not in self.nodes():
            raise ValueError(f"Source cell (ID {nid}) does not exist{txt}.")

        if split == "upstream":
            nodes = nx.descendants(self, nid) | {nid}
        elif split == "downstream":
            nodes = nx.descendants(self, nid)
        else:
            raise ValueError("The split parameter must be 'upstream' or 'downstream'.")
        new_lineage = self.subgraph(nodes).copy()  # new_lineage has same type as self
        self.remove_nodes_from(nodes)
        return new_lineage  # type: ignore

    def get_ancestors(self, cid: int, sorted=True) -> list[int]:
        """
        Return all the ancestors of a given cell.

        Chronological order means from the root cell to the target cell.
        In terms of graph theory, it is the shortest path from the root cell
        to the target cell.

        Parameters
        ----------
        cid : int
            ID of the cell for which to retrieve ancestor cells.
        sorted : bool, optional
            True to return the ancestors in chronological order, False otherwise.
            True by default.

        Returns
        -------
        list[int]
            A list of all the ancestor cells.

        Raises
        ------
        KeyError
            If the cell does not exist in the lineage.

        Warns
        -----
        UserWarning
            If the cells have no 'frame' property to order them.
        """
        try:
            ancestors = super().get_ancestors(cid)
        except nx.NetworkXError as err:
            raise KeyError(f"Cell {cid} is not in the lineage.") from err
        if sorted:
            try:
                ancestors.sort(key=lambda n: self.nodes[n]["frame"])
            except KeyError:
                warnings.warn("No 'frame' property to order the cells.")
        return ancestors

    def get_divisions(self, cids: list[int] | None = None) -> list[int]:
        """
        Return the cells that are dividing in the lineage.

        Division cells are defined as cells (nodes) with more than one outgoing edge.

        Parameters
        ----------
        cids : list[int], optional
            A list of cell IDs to check for divisions. If None, all cells
            in the lineage will be checked.

        Returns
        -------
        list[int]
            The list of dividing cells in the lineage.
        """
        if cids is None:
            cids = list(self.nodes())
        return [n for n in cids if self.out_degree(n) > 1]  # type: ignore

    def get_cell_cycle(self, cid: int) -> list[int]:
        """
        Return all the cells in the cell cycle of the given cell, in chronological order.

        A cell cycle is a lineage segment that starts at the root or at a
        division cell, ends at a division cell or at a leaf, and doesn't
        include any other division.

        Parameters
        ----------
        cid : int
            ID of the cell for which to identify the cells in the cell cycle.

        Returns
        -------
        list[int]
            A chronologically ordered list of cells representing
            the cell cycle for the given cell.

        Raises
        ------
        FusionError
            If the given cell has more than one predecessor.
        """
        # TODO: factorize
        lid, _ = CellLineage._get_lineage_ID_and_err_msg(self)
        cell_cycle = [cid]
        start = False
        end = False

        if self.is_root(cid):
            start = True
        if self.is_division(cid) or self.is_leaf(cid):
            end = True

        if not start:
            predecessors = list(self.predecessors(cid))
            if len(predecessors) != 1:
                raise FusionError(cid, lid)
            while not self.is_division(*predecessors) and not self.is_root(*predecessors):
                # While not the generation birth.
                cell_cycle.append(*predecessors)
                predecessors = list(self.predecessors(*predecessors))
                if len(predecessors) != 1:
                    raise FusionError(cid, lid)
            if self.is_root(*predecessors) and not self.is_division(*predecessors):
                cell_cycle.append(*predecessors)
            cell_cycle.reverse()  # We built it from the end.

        if not end:
            successors = list(self.successors(cid))
            err = (
                f"Something went wrong: division detected in the cell cycle "
                f"of cell {cid}. This cell has {len(successors)} successors."
            )
            assert len(successors) == 1, err
            while not self.is_division(*successors) and not self.is_leaf(*successors):
                cell_cycle.append(*successors)
                successors = list(self.successors(*successors))
                err = (
                    f"Something went wrong: division detected in the cell cycle "
                    f"of cell {cid}. This cell has {len(successors)} successors."
                )
                assert len(successors) == 1, err
            cell_cycle.append(*successors)

        return cell_cycle

    def get_cell_cycles(self, ignore_incomplete_cycles: bool = False) -> list[list[int]]:
        """
        Return all the cells of each cell cycle in a lineage.

        A cell cycle is a lineage segment that starts at the root or at a
        division cell, ends at a division cell or at a leaf, and doesn't
        include any other division.

        Parameters
        ----------
        ignore_incomplete_cycles : bool, optional
            True to ignore incomplete cell cycles, False otherwise. False by default.

        Returns
        -------
        list(list(int))
            List of cell IDs for each cell cycle, in chronological order.
        """
        if ignore_incomplete_cycles:
            end_nodes = self.get_divisions()  # Includes the root if it's a div.
        else:
            end_nodes = self.get_divisions() + self.get_leaves()

        cell_cycles = []
        for node in end_nodes:
            cc_nodes = self.get_cell_cycle(node)
            if ignore_incomplete_cycles and self.is_root(cc_nodes[0]):
                continue
            cell_cycles.append(cc_nodes)

        return cell_cycles

    def get_sister_cells(self, cid: int) -> list[int]:
        """
        Return the sister cells of a given cell.

        Sister cells are cells that are on the same frame
        and share the same parent cell.

        Parameters
        ----------
        cid : int
            ID of the cell for which to find the sister cells.

        Returns
        -------
        list[int]
            The list of cell IDs of the sister cells of the given cell.

        Raises
        ------
        FusionError
            If the given cell has more than one parent cell.
        """
        sister_cells = []
        current_frame = self.nodes[cid]["frame"]
        if not self.is_root(cid):
            current_cell_cycle = self.get_cell_cycle(cid)
            parents = list(self.predecessors(current_cell_cycle[0]))
            if len(parents) == 1:
                children = list(self.successors(parents[0]))
                children.remove(current_cell_cycle[0])
                for child in children:
                    sister_cell_cycle = self.get_cell_cycle(child)
                    sister_cells.extend(
                        [n for n in sister_cell_cycle if self.nodes[n]["frame"] == current_frame]
                    )
            elif len(parents) > 1:
                lid, _ = CellLineage._get_lineage_ID_and_err_msg(self)
                raise FusionError(cid, lid)
        return sister_cells

    def is_division(self, cid: int) -> bool:
        """
        Check if a given cell is dividing.

        A division cell is defined as a cell with more than one outgoing edge
        and at most one incoming edge.

        Parameters
        ----------
        cid : int
            ID of the cell to check.

        Returns
        -------
        bool
            True if the cell is a division cell, False otherwise.
        """
        if self.in_degree(cid) <= 1 and self.out_degree(cid) > 1:  # type: ignore
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
        ID_prop: str = "cell_ID",
        y_prop: str = "frame",
        y_legend: str = "Time (frames)",
        title: str | None = None,
        node_text: str | None = None,
        node_text_font: dict[str, Any] | None = None,
        node_marker_style: dict[str, Any] | None = None,
        node_colormap_prop: str | None = None,
        node_color_scale: str | None = None,
        node_hover_props: list[str] | None = None,
        edge_line_style: dict[str, Any] | None = None,
        edge_hover_props: list[str] | None = None,
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
        ID_prop : str, optional
            The property of the nodes to use as the node ID. "cell_ID" by default.
        y_prop : str, optional
            The property of the nodes to use as the y-axis. "frame" by default.
        y_legend : str, optional
            The label of the y-axis. "Time (frames)" by default.
        title : str, optional
            The title of the plot. If None, no title is displayed.
        node_text : str, optional
            The property of the nodes to display as text inside the nodes
            of the plot. If None, no text is displayed. None by default.
        node_text_font : dict, optional
            The font style of the text inside the nodes (size, color, etc).
            If None, defaults to current Plotly template.
        node_marker_style : dict, optional
            The style of the markers representing the nodes in the plot
            (symbol, size, color, line, etc). If None, defaults to
            current Plotly template.
        node_colormap_prop : str, optional
            The property of the nodes to use for coloring the nodes.
            If None, no color mapping is applied.
        node_color_scale : str, optional
            The color scale to use for coloring the nodes. If None,
            defaults to current Plotly template.
        node_hover_props : list[str], optional
            The hover template for the nodes. If None, defaults to
            displaying `cell_ID` and the value of the y_prop.
        edge_line_style : dict, optional
            The style of the lines representing the edges in the plot
            (color, width, etc). If None, defaults to current Plotly template.
        edge_hover_props : list[str], optional
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
            ID_prop=ID_prop,
            y_prop=y_prop,
            y_legend=y_legend,
            title=title,
            node_text=node_text,
            node_text_font=node_text_font,
            node_marker_style=node_marker_style,
            node_colormap_prop=node_colormap_prop,
            node_color_scale=node_color_scale,
            node_hover_props=node_hover_props,
            edge_line_style=edge_line_style,
            edge_hover_props=edge_hover_props,
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
            lid = lineage.graph["lineage_ID"]
            txt = f" in lineage {lid}"
        except KeyError:
            lid = None
            txt = ""
        return lid, txt


class CycleLineage(Lineage):
    def __init__(self, cell_lineage: CellLineage | None = None) -> None:
        super().__init__()

        if cell_lineage is not None:
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

            # Adding node and graph props.
            self.graph["lineage_ID"] = cell_lineage.graph["lineage_ID"]
            for n in divs + leaves:
                cells_in_cycle = cell_lineage.get_cell_cycle(n)
                first = cells_in_cycle[0]
                last = cells_in_cycle[-1]
                self.nodes[n]["cycle_ID"] = n
                self.nodes[n]["cells"] = cells_in_cycle
                # How many cells in the cycle?
                self.nodes[n]["cycle_length"] = len(cells_in_cycle)
                # How many frames in the cycle?
                self.nodes[n]["cycle_duration"] = (
                    cell_lineage.nodes[last]["frame"] - cell_lineage.nodes[first]["frame"]
                ) + 1
                root = self.get_root()
                if isinstance(root, list):
                    raise LineageStructureError("A cycle lineage cannot have multiple roots.")
                self.nodes[n]["level"] = nx.shortest_path_length(self, root, n)

    def __str__(self) -> str:
        name_txt = f" named {self.graph['name']}" if "name" in self.graph else ""
        txt = (
            f"CycleLineage of ID {self.graph['lineage_ID']}{name_txt}"
            f" with {len(self)} cell cycles and {len(self.edges())} links."
        )
        return txt

    # Methods to freeze / unfreeze?

    def get_ancestors(self, ccid: int, sorted=True) -> list[int]:
        """
        Return all the ancestor cell cycles of a given cell cycle.

        Chronological order means from the root cell cycle to the target cell cycle.
        In terms of graph theory, it is the shortest path from the root cell cycle
        to the target cell cycle.

        Parameters
        ----------
        ccid : int
            ID of the cell cycle for which to retrieve ancestor cell cycle.
        sorted : bool, optional
            True to return the ancestors in chronological order, False otherwise.
            True by default.

        Returns
        -------
        list[int]
            A list of all the ancestor cell cycles.

        Raises
        ------
        KeyError
            If the cell cycle does not exist in the lineage.

        Warns
        -----
        UserWarning
            If there is no 'level' property to order the cell cycles.
        """
        try:
            ancestors = super().get_ancestors(ccid)
        except nx.NetworkXError as err:
            raise KeyError(f"Cell cycle {ccid} is not in the lineage.") from err
        if sorted:
            try:
                ancestors.sort(key=lambda n: self.nodes[n]["level"])
            except KeyError:
                warnings.warn("No 'level' property to order the cell cycles.")
        return ancestors

    def get_links_within_cycle(self, ccid: int) -> list[tuple[int, int]]:
        """
        Return all the links between the cells of a cell cycle.

        This doesn't include the link from the previous cell cycle to the current one.

        Parameters
        ----------
        ccid : int
            The ID of the cell cycle for which to retrieve links.

        Returns
        -------
        list[tuple(int, int)]
            A list of links between the cells of a cell cycle.
        """
        return list(pairwise(self.nodes[ccid]["cells"]))

    def yield_links_within_cycle(self, ccid: int) -> Generator[Tuple[int, int], None, None]:
        """
        Yield all the links between the cells of a cell cycle.

        This doesn't include the link from the previous cell cycle to the current one.

        Parameters
        ----------
        ccid : int
            The ID of the cell cycle for which to retrieve links.

        Yields
        ------
        tuple(int, int)
            The links between the cells of a cell cycle.
        """
        for edge in pairwise(self.nodes[ccid]["cells"]):
            yield edge

    def plot(
        self,
        ID_prop: str = "cycle_ID",
        y_prop: str = "level",
        y_legend: str = "Cell cycle level",
        title: str | None = None,
        node_text: str | None = None,
        node_text_font: dict[str, Any] | None = None,
        node_marker_style: dict[str, Any] | None = None,
        node_colormap_prop: str | None = None,
        node_color_scale: str | None = None,
        node_hover_props: list[str] | None = None,
        edge_line_style: dict[str, Any] | None = None,
        edge_hover_props: list[str] | None = None,
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
        ID_prop : str, optional
            The property of the nodes to use as the node ID. "cycle_ID" by default.
        y_prop : str, optional
            The property of the nodes to use as the y-axis. "level" by default.
        y_legend : str, optional
            The label of the y-axis. "Cell cycle level" by default.
        title : str, optional
            The title of the plot. If None, no title is displayed.
        node_text : str, optional
            The property of the nodes to display as text inside the nodes
            of the plot. If None, no text is displayed. None by default.
        node_text_font : dict, optional
            The font style of the text inside the nodes (size, color, etc).
            If None, defaults to current Plotly template.
        node_marker_style : dict, optional
            The style of the markers representing the nodes in the plot
            (symbol, size, color, line, etc). If None, defaults to
            current Plotly template.
        node_colormap_prop : str, optional
            The property of the nodes to use for coloring the nodes.
            If None, no color mapping is applied.
        node_color_scale : str, optional
            The color scale to use for coloring the nodes. If None,
            defaults to current Plotly template.
        node_hover_props : list[str], optional
            The hover template for the nodes. If None, defaults to
            displaying `cell_ID` and the value of the y_prop.
        edge_line_style : dict, optional
            The style of the lines representing the edges in the plot
            (color, width, etc). If None, defaults to current Plotly template.
        edge_hover_props : list[str], optional
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
            ID_prop=ID_prop,
            y_prop=y_prop,
            y_legend=y_legend,
            title=title,
            node_text=node_text,
            node_text_font=node_text_font,
            node_marker_style=node_marker_style,
            node_colormap_prop=node_colormap_prop,
            node_color_scale=node_color_scale,
            node_hover_props=node_hover_props,
            edge_line_style=edge_line_style,
            edge_hover_props=edge_hover_props,
            plot_bgcolor=plot_bgcolor,
            show_horizontal_grid=show_horizontal_grid,
            showlegend=showlegend,
            width=width,
            height=height,
        )
