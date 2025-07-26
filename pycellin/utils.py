#!/usr/bin/env python3

from typing import Literal, get_args, get_origin

import networkx as nx
import networkx.algorithms.isomorphism as iso


def check_literal_type(value, literal_type) -> bool:
    if get_origin(literal_type) is Literal:
        return value in get_args(literal_type)
    raise TypeError(f"{literal_type} is not a Literal type")


# TODO: this function should move into a tests/utils.py file
def is_equal(obt, exp):
    """Check if two graphs are perfectly identical.

    It checks that the graphs are isomorphic, and that their graph,
    nodes and edges attributes are all identical.

    Args:
        obt (nx.DiGraph): The obtained graph, built from XML_reader.py.
        exp (nx.DiGraph): The expected graph, built from here.

    Returns:
        bool: True if the graphs are identical, False otherwise.
    """
    edges_attr = list(set([k for (n1, n2, d) in exp.edges.data() for k in d]))
    edges_default = len(edges_attr) * [0]
    em = iso.categorical_edge_match(edges_attr, edges_default)
    nodes_attr = list(set([k for (n, d) in exp.nodes.data() for k in d]))
    nodes_default = len(nodes_attr) * [0]
    nm = iso.categorical_node_match(nodes_attr, nodes_default)

    if not obt.nodes.data() and not exp.nodes.data():
        same_nodes = True
    elif len(obt.nodes.data()) != len(exp.nodes.data()):
        same_nodes = False
    else:
        for data1, data2 in zip(sorted(obt.nodes.data()), sorted(exp.nodes.data())):
            n1, attr1 = data1
            n2, attr2 = data2
            if sorted(attr1) == sorted(attr2) and n1 == n2:
                same_nodes = True
            else:
                same_nodes = False

    if not obt.edges.data() and not exp.edges.data():
        same_edges = True
    elif len(obt.edges.data()) != len(exp.edges.data()):
        same_edges = False
    else:
        for data1, data2 in zip(sorted(obt.edges.data()), sorted(exp.edges.data())):
            n11, n12, attr1 = data1
            n21, n22, attr2 = data2
            if sorted(attr1) == sorted(attr2) and sorted((n11, n12)) == sorted(
                (n21, n22)
            ):
                same_edges = True
            else:
                same_edges = False

    if (
        nx.is_isomorphic(obt, exp, edge_match=em, node_match=nm)
        and obt.graph == exp.graph
        and same_nodes
        and same_edges
    ):
        return True
    else:
        return False
