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

