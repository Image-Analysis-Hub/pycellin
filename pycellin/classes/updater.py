#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class ModelUpdater():
        
    def __init__(self):

        self._update_required = False
        
        # TODO: is a set a good idea? Maybe better to pool the nodes per lineage...
        # In this case I need to be able to modify the content of the collection
        self._added_cells = set()  # set of Cell()
        self._removed_cells = set()
        self._added_links = set()
        self._removed_links = set()

    # def _update_nodes(self):
    #     pass

    # def _update_edges(self):
    #     pass
    