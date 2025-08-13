#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO: add a Warning when a feature is not present across all cells,
# links, or lineages?

# TODO: create an exception when unknown cell, cell cycle, link, lineage...

# TODO: maybe add a FeatureTypeValueError and a LineageTypeValueError


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
        message: str | None = None,
    ):
        self.node_ID = node_ID
        self.lineage_ID = lineage_ID
        if message is None:
            if lineage_ID is None:
                message = f"Node {node_ID} has more than one parent node."
            else:
                message = f"Node {node_ID} in lineage {lineage_ID} has more than one parent node."
        super().__init__(message)


class TimeFlowError(LineageStructureError):
    """
    Raised when a time flow error is detected in the lineage structure.

    In a lineage graph, time flows from the root of the graph to the leaves.
    As a result, a node should always have a time value greater than its parent.

    Parameters
    ----------
    source_nid : int
        The ID of the source node.
    target_nid : int
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
        source_nid: int,
        target_nid: int,
        source_lineage_ID: int | None = None,
        target_lineage_ID: int | None = None,
        message: str | None = None,
    ):
        self.source_nid = source_nid
        self.source_lineage_ID = source_lineage_ID
        self.target_nid = target_nid
        self.target_lineage_ID = target_lineage_ID
        if message is None:
            txt_source_lin = "" if source_lineage_ID is None else f" in lineage {source_lineage_ID}"
            txt_target_lin = "" if target_lineage_ID is None else f" in lineage {target_lineage_ID}"
            message = (
                f"Node {target_nid}{txt_target_lin} "
                f"has a time value lower than its parent node, "
                f"node {source_nid}{txt_source_lin}."
            )
        super().__init__(message)


class UpdateRequiredError(Exception):
    """
    Raised when an update is required before performing an operation.

    Parameters
    ----------
    message : str, optional
        The error message to display.
        If not provided, a default message is displayed.
    """

    def __init__(
        self,
        message: str | None = None,
    ):
        if message is None:
            message = "An update is required before performing this operation."
        super().__init__(message)


class ProtectedFeatureError(Exception):
    """
    Raised when trying to modify or delete a protected feature.

    Parameters
    ----------
    feature_name : str
        The name of the feature that is protected.
    message : str, optional
        The error message to display.
        If not provided, a default message is displayed.
    """

    def __init__(self, feat_name: str, message: str | None = None):
        self.feature_name = feat_name
        if message is None:
            message = f"The feature '{feat_name}' is protected and cannot be modified nor removed."
        super().__init__(message)
