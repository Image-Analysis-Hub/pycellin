#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class Data:
    """
    Do I really need this one?
      => do I have something that is applicable for both core and branch data?
    Or maybe I need only the Data class and no subclasses.
    """

    def __init__(self, data):
        self.data = data


class CoreData(Data):
    """
    dict of cell lineage: {lineage_id: CellLineage}
    """

    pass


class BranchData(Data):
    """
    dict of cycle lineage: {lineage_id: CycleLineage}
    """

    pass
