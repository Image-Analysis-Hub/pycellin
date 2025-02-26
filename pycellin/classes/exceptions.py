#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO: add a Warning when a feature is not present across all cells,
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
    lineage_ID : int, optional
        The ID of the lineage where the fusion event was detected.
        None by default.
    message : str, optional
        The error message to display.
        If not provided, a default message is displayed.
    """

    def __init__(
        self,
        node_ID: int,
        lineage_ID: int | None = None,
        message: str = None,
    ):
        self.node_ID = node_ID
        self.lineage_ID = lineage_ID
        if message is None:
            if lineage_ID is None:
                message = f"Node {node_ID} already has a parent node."
            else:
                message = (
                    f"Node {node_ID} in lineage {lineage_ID} already has "
                    f"a parent node."
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
    target_noi : int
        The ID of the target node.
    source_lineage_ID : int, optional
        The ID of the lineage of the source node.
        None by default.
    target_lineage_ID : int, optional
        The ID of the lineage of the target node.
        None by default.
    message : str, optional
        The error message to display.
        If not provided, a default message is displayed.
    """

    def __init__(
        self,
        source_noi: int,
        target_noi: int,
        source_lineage_ID: int | None = None,
        target_lineage_ID: int | None = None,
        message: str = None,
    ):
        self.source_noi = source_noi
        self.source_lineage_ID = source_lineage_ID
        self.target_noi = target_noi
        self.target_lineage_ID = target_lineage_ID
        if message is None:
            txt_source_lin = (
                "" if source_lineage_ID is None else f" in lineage {source_lineage_ID}"
            )
            txt_target_lin = (
                "" if target_lineage_ID is None else f" in lineage {target_lineage_ID}"
            )
            message = (
                f"Node {target_noi}{txt_target_lin} "
                f"has a time value lower than its parent node, "
                f"node {source_noi}{txt_source_lin}."
            )
        super().__init__(message)


# TODO: maybe add a FeatureTypeValueError and a LineageTypeValueError
