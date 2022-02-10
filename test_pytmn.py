#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for pyTMn.
"""

import io
import xml.etree.ElementTree as ET

import networkx as nx
import networkx.algorithms.isomorphism as iso
import pytest

import pytmn


def is_equal(obt, exp):
    """Check if two graphs are perfectly identical.

    It checks that the graphs are isomorphic, and that their graph,
    nodes and edges attributes are all identical.

    Args:
        obt (nx.DiGraph): The obtained graph, built from pytmn.py.
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
        for data1, data2 in zip(sorted(obt.nodes.data()), 
                                sorted(exp.nodes.data())):
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
        for data1, data2 in zip(sorted(obt.edges.data()), 
                                sorted(exp.edges.data())):
            n11, n12, attr1 = data1
            n21, n22, attr2 = data2
            if (sorted(attr1) == sorted(attr2)
                and sorted((n11, n12)) == sorted((n21, n22))):
                same_edges = True
            else:
                same_edges = False

    if (nx.is_isomorphic(obt, exp, edge_match=em, node_match=nm) 
        and obt.graph == exp.graph
        and same_nodes
        and same_edges):
        return True
    else:
        return False
    

### add_graph_attrib_from_element ###

def test_add_graph_attrib_from_element():
    xml_data = ('<data attrib1="text" attrib2="10">'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data))
    _, element = next(it)
    obtained = pytmn.add_graph_attrib_from_element(nx.DiGraph(), element)
    expected = nx.DiGraph(attrib1="text", attrib2="10")

    print(obtained.edges.data())
    print(expected.edges.data())
    print(obtained.edges.data() == expected.edges.data())
    
    assert is_equal(obtained, expected)


def test_add_graph_attrib_from_element_no_graph_attributes():
    xml_data = ('<data>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data))
    _, element = next(it)
    obtained = pytmn.add_graph_attrib_from_element(nx.DiGraph(), element)
    expected = nx.DiGraph()
    assert is_equal(obtained, expected)


### add_all_nodes ###

def test_add_all_nodes_several_attributes():
    xml_data = ('<data>'
                '   <frame>'
                '       <Spot ID="blob" x="10" y="20"></Spot>'
                '       <Spot ID="blub" x="30" y="30"></Spot>'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    event, element = next(it)

    obtained = nx.DiGraph()
    pytmn.add_all_nodes(obtained, it, element)

    expected = nx.DiGraph()
    expected.add_nodes_from([("blub", {"y": "30", "x": "30"}),
                             ("blob", {"x": "10", "y": "20"})])

    assert is_equal(obtained, expected)


def test_add_all_nodes_only_ID_attribute():
    xml_data = ('<data>'
                '   <frame>'
                '       <Spot ID="blob"></Spot>'
                '       <Spot ID="blub"></Spot>'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.DiGraph()
    pytmn.add_all_nodes(obtained, it, element)

    expected = nx.DiGraph()
    expected.add_nodes_from(["blob", "blub"])

    assert is_equal(obtained, expected)


def test_add_all_nodes_no_node_attributes():
    xml_data = ('<data>'
                '   <frame>'
                '       <Spot></Spot>'
                '       <Spot ID="blub"></Spot>'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.DiGraph()
    pytmn.add_all_nodes(obtained, it, element)

    expected = nx.DiGraph()
    expected.add_nodes_from(["blub"])

    assert is_equal(obtained, expected)


def test_add_all_nodes_no_nodes():
    xml_data = ('<data>'
                '   <frame>'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    
    obtained = nx.DiGraph()
    pytmn.add_all_nodes(obtained, it, element)
    
    assert is_equal(obtained, nx.DiGraph())


### add_edge_from_element ###

def test_add_edge_from_element():
    xml_data = ('<data SPOT_SOURCE_ID="1" SPOT_TARGET_ID="2" x="20" y="25">'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    track_id = '0'

    obtained = nx.DiGraph()
    pytmn.add_edge_from_element(obtained, element, track_id)

    expected = nx.DiGraph()
    expected.add_edge('1', '2', x='20', y='25')
    expected.nodes['1']['TRACK_ID'] = track_id
    expected.nodes['2']['TRACK_ID'] = track_id

    assert is_equal(obtained, expected)


def test_add_edge_from_element_no_node_ID():
    xml_data = ('<data SPOT_SOURCE_ID="1" x="20" y="25">'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    track_id = '0'
    
    obtained = nx.DiGraph()
    pytmn.add_edge_from_element(obtained, element, track_id)
    
    assert is_equal(obtained, nx.DiGraph())


def test_add_edge_from_element_no_edge_attributes():
    xml_data = ('<data SPOT_SOURCE_ID="1" SPOT_TARGET_ID="2">'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    track_id = '0'

    obtained = nx.DiGraph()
    pytmn.add_edge_from_element(obtained, element, track_id)

    expected = nx.DiGraph()
    expected.add_edge('1', '2')
    expected.nodes['1']['TRACK_ID'] = track_id
    expected.nodes['2']['TRACK_ID'] = track_id

    assert is_equal(obtained, expected)


### add_all_edges ###

def test_add_all_edges():
    pass
