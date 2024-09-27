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
    """

    pass


class TimeFlowError(LineageStructureError):
    """
    Raised when a time flow error is detected in the lineage structure.

    In a lineage graph, time flows from the root of the graph to the leaves.
    As a result, a node should always have a time value greater than its parent.
    """

    pass
