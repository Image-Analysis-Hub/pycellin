#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from itertools import pairwise

import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.feature import FeaturesDeclaration, Feature
from pycellin.classes.data import CoreData
from pycellin.classes.lineage import CellLineage

# TODO: add FeaturesDeclaration and create proper model
# TODO: refactor
# TODO: decide on the name of the standard Pycellin features
# I think lower case is easier to read and allows for occasional use
# of upper case for abreviations.
# Snake case would be consistent with Python naming conventions.

ctc_file = "C:/Users/haiba/Documents/01_RES/res_track.txt"

model = Model()
graph = nx.DiGraph()
node_id = 0
lin_id = 0  # lineage ID

with open(ctc_file) as f:
    for line in f:
        track_id, start_frame, end_frame, parent_track = [
            int(element) for element in line.split()
        ]

        # Creating the nodes of the current track, with their respective attributes.
        nodes = []
        for frame in range(start_frame, end_frame + 1):
            nodes.append(
                (
                    node_id,
                    {
                        "ID": node_id,
                        "FRAME": frame,
                        "TRACK": track_id,
                    },
                )
            )
            node_id += 1

        # Adding nodes and edges of the current track to the graph.
        graph.add_nodes_from(nodes)
        for n1, n2 in pairwise(nodes):
            graph.add_edge(n1[0], n2[0])

        # Linking the current track and the parent track.
        if parent_track != 0:
            # Finding the last node of the parent track.
            parent_nodes = [
                (node, data["FRAME"])
                for node, data in graph.nodes(data=True)
                if data["TRACK"] == parent_track
            ]
            parent_node = sorted(parent_nodes, key=lambda x: x[1])[-1]
            graph.add_edge(parent_node[0], nodes[0][0])

# graph.plot_with_plotly()

# We want one lineage per connected component of the graph.
lineages = [
    CellLineage(graph.subgraph(c).copy()) for c in nx.weakly_connected_components(graph)
]

# Adding a TRACK_ID to each lineage and their nodes.
for lin in lineages:
    lin.graph["TRACK_ID"] = lin_id
    for node, data in lin.nodes(data=True):
        data["TRACK_ID"] = lin_id
        if "TRACK" in data:
            del data["TRACK"]
    lin_id += 1

for lin in lineages:
    print(lin)
    print(lin.graph["TRACK_ID"])
