#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for pyTMn.
"""

import io
import xml.etree.ElementTree as ET

import networkx as nx
import pytest

import pytmn


def test_add_model_info():
    xml_data = ('<data attrib1="text" attrib2="10">'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data))
    _, element = next(it)
    obtained = pytmn.add_model_info(nx.Graph(), element).graph
    expected = nx.Graph(attrib1="text", attrib2="10").graph
    assert obtained == expected


def test_add_model_info_no_graph_attributes():
    xml_data = ('<data>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data))
    _, element = next(it)
    obtained = pytmn.add_model_info(nx.Graph(), element).graph
    expected = nx.Graph().graph
    assert obtained == expected


def test_add_all_nodes_several_attributes():
    xml_data = ('<data>'
                '   <frame>'
                '       <Spot ID="blob" x="10" y="20"></Spot>'
                '       <Spot ID="blub" x="30" y="30"></Spot>'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    event, element = next(it)

    obtained = nx.Graph()
    pytmn.add_all_nodes(obtained, it, element)

    expected = nx.Graph()
    expected.add_nodes_from([("blob", {"x": "10", "y": "20"}),
                             ("blub", {"x": "30", "y": "30"})])

    nm = nx.algorithms.isomorphism.categorical_node_match("x", "y")
    assert nx.is_isomorphic(obtained, expected, node_match=nm)


def test_add_all_nodes_only_ID_attribute():
    xml_data = ('<data>'
                '   <frame>'
                '       <Spot ID="blob"></Spot>'
                '       <Spot ID="blub"></Spot>'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.Graph()
    pytmn.add_all_nodes(obtained, it, element)

    expected = nx.Graph()
    expected.add_nodes_from(["blob", "blub"])

    assert nx.is_isomorphic(obtained, expected)


def test_add_all_nodes_no_node_attributes():
    xml_data = ('<data>'
                '   <frame>'
                '       <Spot></Spot>'
                '       <Spot ID="blub"></Spot>'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.Graph()
    pytmn.add_all_nodes(obtained, it, element)

    expected = nx.Graph()
    expected.add_nodes_from(["blub"])

    assert nx.is_isomorphic(obtained, expected)


def test_add_all_nodes_no_nodes():
    xml_data = ('<data>'
                '   <frame>'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    obtained = nx.Graph()
    pytmn.add_all_nodes(obtained, it, element)
    assert nx.is_isomorphic(obtained, nx.Graph())


