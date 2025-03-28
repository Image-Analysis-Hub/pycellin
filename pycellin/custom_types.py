#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import namedtuple
from typing import Literal


LineageType = Literal["CellLineage", "CycleLineage", "Lineage"]
FeatureType = Literal["node", "edge", "lineage"]

# TODO: should I force the user to use the Cell and Link named tuples?
# Would impact the signature of a lot of methods, but would make these
# signatures more structured and consistent (looking at you, add_cell()).
Cell = namedtuple("Cell", ["cell_ID", "lineage_ID"])
Link = namedtuple(
    "Link",
    ["source_cell_ID", "target_cell_ID", "lineage_ID"],
)
