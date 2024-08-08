#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class LineageStructureError(Exception):
    """
    Exception raised for errors in the lineage structure.

    For now, the only use-case I have for this exception
    is when one of the node has several parents,
    i.e. there are merges in the lineage.
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
