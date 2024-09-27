#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO: add a WWarning when a feature is not present across all cells,
# links, or lineages?


class LineageStructureError(Exception):
    """
    Raised when an incorrect lineage structure is detected.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class FusionError(LineageStructureError):
    """
    Raised when a fusion event is detected in the lineage structure.

    A fusion event happens when a node has more than one parent,
    i. e. an in_degree greater than 1.

    Parameters
    ----------
    node_ID : int
        The ID of the node where the fusion event was detected.
    lineage_ID : int
        The ID of the lineage where the fusion event was detected.
    message : str, optional
        The error message to display.
        If not provided, a default message is displayed.
    """

    def __init__(self, node_ID: int, lineage_ID: int, message: str = None):
        self.node_ID = node_ID
        self.lineage_ID = lineage_ID
        if message is None:
            message = (
                f"Node {node_ID} already has a parent node in lineage {lineage_ID}.\n"
                f"Remove any incoming edge to node {node_ID} "
                f"before adding a new incoming edge."
            )
        super().__init__(message)


class TimeFlowError(LineageStructureError):
    """
    Raised when a time flow error is detected in the lineage structure.

    In a lineage graph, time flows from the root of the graph to the leaves.
    As a result, a node should always have a time value greater than its parent.

    Parameters
    ----------
    source_noi : int
        The ID of the source node.
    source_lineage_ID : int
        The ID of the lineage of the source node.
    target_noi : int
        The ID of the target node.
    target_lineage_ID : int
        The ID of the lineage of the target node.
    message : str, optional
        The error message to display.
        If not provided, a default message is displayed.
    """

    def __init__(
        self,
        source_noi: int,
        source_lineage_ID: int,
        target_noi: int,
        target_lineage_ID: int,
        message: str = None,
    ):
        self.source_noi = source_noi
        self.source_lineage_ID = source_lineage_ID
        self.target_noi = target_noi
        self.target_lineage_ID = target_lineage_ID
        if message is None:
            message = (
                f"Node {target_noi} from lineage {target_lineage_ID} "
                f"has a time value lower than its parent node, "
                f"node {source_noi} from lineage {source_lineage_ID}."
            )
        super().__init__(message)
