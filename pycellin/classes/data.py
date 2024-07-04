#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class Data:
    """
    Do I really need this one?
      => do I have something that is applicable for both core and branch data?
    """

    def __init__(self, data):
        self.data = data


class CoreData(Data):
    pass


class BranchData(Data):
    pass
