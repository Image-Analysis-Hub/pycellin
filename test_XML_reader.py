#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for pyTMn XML_reader.
"""

import io
# import xml.etree.ElementTree as ET
from lxml import etree as ET

import networkx as nx
import networkx.algorithms.isomorphism as iso
import pytest

import XML_reader as xmlr


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
    xml_data = ('<data attrib1="text" attrib2="10" />')
    it = ET.iterparse(io.StringIO(xml_data))
    _, element = next(it)
    obtained = xmlr.add_graph_attrib_from_element(nx.DiGraph(), element)
    model = {'attrib1': 'text', 'attrib2': '10'}
    expected = nx.DiGraph(Model=model)
    assert is_equal(obtained, expected)


def test_add_graph_attrib_from_element_no_graph_attributes():
    xml_data = ('<data>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data))
    _, element = next(it)
    obtained = xmlr.add_graph_attrib_from_element(nx.DiGraph(), element)
    expected = nx.DiGraph(Model={})
    assert is_equal(obtained, expected)


### add_features ###

def test_get_features_dict():
    xml_data = ('<SpotFeatures>'
                '   <Feature feature="QUALITY" isint="false" />'
                '   <Feature feature="FRAME" isint="true" />'
                '</SpotFeatures>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    features = xmlr.get_features_dict(it, element)
    spot_features = {'QUALITY': {'feature': 'QUALITY', 'isint': 'false'},
                     'FRAME': {'feature': 'FRAME', 'isint': 'true'}}
    assert features == spot_features


def test_get_features_dict_no_feature_tag():
    xml_data = ('<SpotFeatures>'
                '</SpotFeatures>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    features = xmlr.get_features_dict(it, element)
    assert features == {}


def test_get_features_dict_other_tag():
    xml_data = ('<SpotFeatures>'
                '   <Feature feature="QUALITY" isint="false" />'
                '   <Other feature="FRAME" isint="true" />'
                '</SpotFeatures>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    features = xmlr.get_features_dict(it, element)
    spot_features = {'QUALITY': {'feature': 'QUALITY', 'isint': 'false'}}
    assert features == spot_features


### add_all_features ###

def test_add_all_features():
    xml_data = ('<FeatureDeclarations>'
                '   <SpotFeatures>'
                '       <Feature feature="QUALITY" isint="false" />'
                '       <Feature feature="FRAME" isint="true" />'
                '   </SpotFeatures>'
                '   <EdgeFeatures>'
                '       <Feature feature="SPOT_SOURCE_ID" isint="true" />'
                '       <Feature feature="SPOT_TARGET_ID" isint="true" />'
                '   </EdgeFeatures>'
                '   <TrackFeatures>'
                '       <Feature feature="TRACK_INDEX" isint="true" />'
                '       <Feature feature="NUMBER_SPOTS" isint="true" />'
                '   </TrackFeatures>'
                '</FeatureDeclarations>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.DiGraph(Model={})
    xmlr.add_all_features(obtained, it, element)

    spot_features = {'QUALITY': {'feature': 'QUALITY', 'isint': 'false'},
                     'FRAME': {'feature': 'FRAME', 'isint': 'true'}}
    edge_features = {'SPOT_SOURCE_ID': {'feature': 'SPOT_SOURCE_ID',
                                        'isint': 'true'},
                     'SPOT_TARGET_ID': {'feature': 'SPOT_TARGET_ID',
                                        'isint': 'true'}}
    track_features = {'TRACK_INDEX': {'feature': 'TRACK_INDEX',
                                      'isint':'true'},
                      'NUMBER_SPOTS': {'feature': 'NUMBER_SPOTS',
                                       'isint': 'true'}}
    expected = nx.DiGraph(Model={'SpotFeatures': spot_features,
                                 'EdgeFeatures': edge_features,
                                 'TrackFeatures': track_features})
    
    assert is_equal(obtained, expected)


def test_add_all_features_empty():
    xml_data = ('<FeatureDeclarations>'
                '</FeatureDeclarations>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.DiGraph()
    xmlr.add_all_features(obtained, it, element)

    assert is_equal(obtained, nx.DiGraph())


def test_add_all_features_tag_with_no_feature_tag():
    xml_data = ('<FeatureDeclarations>'
                '   <SpotFeatures>'
                '       <Feature feature="QUALITY" isint="false" />'
                '       <Feature feature="FRAME" isint="true" />'
                '   </SpotFeatures>'
                '   <EdgeFeatures>'
                '   </EdgeFeatures>'
                '   <TrackFeatures>'
                '       <Feature feature="TRACK_INDEX" isint="true" />'
                '       <Feature feature="NUMBER_SPOTS" isint="true" />'
                '   </TrackFeatures>'
                '</FeatureDeclarations>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.DiGraph(Model={})
    xmlr.add_all_features(obtained, it, element)

    spot_features = {'QUALITY': {'feature': 'QUALITY', 'isint': 'false'},
                     'FRAME': {'feature': 'FRAME', 'isint': 'true'}}
    track_features = {'TRACK_INDEX': {'feature': 'TRACK_INDEX',
                                      'isint':'true'},
                      'NUMBER_SPOTS': {'feature': 'NUMBER_SPOTS',
                                       'isint': 'true'}}
    expected = nx.DiGraph(Model={'SpotFeatures': spot_features,
                                 'EdgeFeatures': {},
                                 'TrackFeatures': track_features})

    assert is_equal(obtained, expected)


def test_add_all_features_no_feature_attribute():
    xml_data = ('<FeatureDeclarations>'
                '   <SpotFeatures>'
                '       <Feature feature="QUALITY" isint="false" />'
                '       <Feature feature="FRAME" isint="true" />'
                '   </SpotFeatures>'
                '   <EdgeFeatures>'
                '       <Feature feature="SPOT_SOURCE_ID" isint="true" />'
                '       <Feature isint="true" />'
                '   </EdgeFeatures>'
                '   <TrackFeatures>'
                '       <Feature feature="TRACK_INDEX" isint="true" />'
                '       <Feature feature="NUMBER_SPOTS" isint="true" />'
                '   </TrackFeatures>'
                '</FeatureDeclarations>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.DiGraph(Model={})
    xmlr.add_all_features(obtained, it, element)

    spot_features = {'QUALITY': {'feature': 'QUALITY', 'isint': 'false'},
                     'FRAME': {'feature': 'FRAME', 'isint': 'true'}}
    edge_features = {'SPOT_SOURCE_ID': {'feature': 'SPOT_SOURCE_ID',
                                        'isint': 'true'}}
    track_features = {'TRACK_INDEX': {'feature': 'TRACK_INDEX',
                                      'isint':'true'},
                      'NUMBER_SPOTS': {'feature': 'NUMBER_SPOTS',
                                       'isint': 'true'}}
    expected = nx.DiGraph(Model={'SpotFeatures': spot_features,
                                 'EdgeFeatures': edge_features,
                                 'TrackFeatures': track_features})

    assert is_equal(obtained, expected)


### convert_attributes ###

def test_convert_attributes():
    features = {'float': {'isint': 'false'}, 'int': {'isint': 'true'},
                'neg': {'isint': 'false'}, 'str': {'isint': 'false'}}
    
    obtained_attr = {'float': '30', 'int': '20', 'neg': '-10', 'str': 'meep'}
    xmlr.convert_attributes(obtained_attr, features)
    
    expected_attr = {'float': 30.0, 'int': 20, 'neg': -10.0, 'str': 'meep'}

    assert obtained_attr == expected_attr


def test_convert_attributes_mixed_case():
    features = {'float': {'isint': 'FaLsE'}, 'int': {'isint': 'tRuE'}}
    
    obtained_attr = {'float': '30', 'int': '20'}
    xmlr.convert_attributes(obtained_attr, features)
    
    expected_attr = {'float': 30.0, 'int': 20}

    assert obtained_attr == expected_attr
    

def test_convert_attributes_KeyError():
    features = {'float': {'not_isint': 'false'}, 'int': {'not_isint': 'true'}}
    attributes = {'float': '30', 'int': '20'}

    with pytest.raises(KeyError):
        xmlr.convert_attributes(attributes, features)


def test_convert_attributes_ValueError():
    features = {'float': {'isint': 'not false'}, 'int': {'isint': 'true'}}
    attributes = {'float': '30', 'int': '20'}

    with pytest.raises(ValueError):
        xmlr.convert_attributes(attributes, features)


### add_ROI_coordinates ###

def test_add_ROI_coordinates_2D():
    el_obtained = ET.Element('Spot')
    el_obtained.attrib['ROI_N_POINTS'] = '3'
    el_obtained.text = '1 2.0 -3 -4.0 5.5 6'
    xmlr.add_ROI_coordinates(el_obtained)

    el_expected = ET.Element('Spot')
    el_expected.attrib['ROI_N_POINTS'] = [(1.0, 2.0), (-3.0, -4.0), (5.5, 6.0)]
    
    assert el_obtained.attrib == el_expected.attrib


def test_add_ROI_coordinates_3D():
    el_obtained = ET.Element('Spot')
    el_obtained.attrib['ROI_N_POINTS'] = '2'
    el_obtained.text = '1 2.0 -3 -4.0 5.5 6'
    xmlr.add_ROI_coordinates(el_obtained)

    el_expected = ET.Element('Spot')
    el_expected.attrib['ROI_N_POINTS'] = [(1.0, 2.0, -3.0), (-4.0, 5.5, 6.0)]
    
    assert el_obtained.attrib == el_expected.attrib


def test_add_ROI_coordinates_no_ROI():
    el_obtained = ET.Element('Spot')
    el_obtained.text = '1 2.0 -3 -4.0 5.5 6'
    xmlr.add_ROI_coordinates(el_obtained)

    assert el_obtained.attrib == ET.Element('Spot').attrib


### add_all_nodes ###

def test_add_all_nodes_several_attributes():
    xml_data = ('<data>'
                '   <frame>'
                '       <Spot ID="1000" x="10" y="20" />'
                '       <Spot ID="1001" x="30.5" y="30" />'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    spot_features = {'x': {'isint': 'false'}, 'y': {'isint': 'true'}}
    obtained = nx.DiGraph(Model={'SpotFeatures': spot_features})
    xmlr.add_all_nodes(obtained, it, element)

    expected = nx.DiGraph(Model={'SpotFeatures': spot_features})
    expected.add_nodes_from([(1001, {'y': 30, 'ID': 1001, 'x': 30.5}),
                             (1000, {'ID': 1000, 'x': 10.0, 'y': 20})])

    assert is_equal(obtained, expected)


def test_add_all_nodes_only_ID_attribute():
    xml_data = ('<data>'
                '   <frame>'
                '       <Spot ID="1000" />'
                '       <Spot ID="1001" />'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.DiGraph(Model={'SpotFeatures': {}})
    xmlr.add_all_nodes(obtained, it, element)

    expected = nx.DiGraph(Model={'SpotFeatures': {}})
    expected.add_nodes_from([(1001, {'ID': 1001}),
                             (1000, {'ID': 1000})])

    assert is_equal(obtained, expected)


def test_add_all_nodes_no_node_attributes():
    xml_data = ('<data>'
                '   <frame>'
                '       <Spot />'
                '       <Spot ID="1001" />'
                '   </frame>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained = nx.DiGraph(Model={'SpotFeatures': {}})
    xmlr.add_all_nodes(obtained, it, element)

    expected = nx.DiGraph(Model={'SpotFeatures': {}})
    expected.add_nodes_from([(1001, {'ID': 1001})])

    assert is_equal(obtained, expected)


def test_add_all_nodes_no_nodes():
    xml_data = ('<data>'
                '   <frame />'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    
    obtained = nx.DiGraph(Model={'SpotFeatures': {}})
    xmlr.add_all_nodes(obtained, it, element)
    
    assert is_equal(obtained, nx.DiGraph(Model={'SpotFeatures': {}}))


### add_edge_from_element ###

def test_add_edge_from_element():
    xml_data = ('<data SPOT_SOURCE_ID="1" SPOT_TARGET_ID="2" x="20" y="25" />')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    track_id = 0

    edge_features = {'x': {'isint': 'false'}, 'y': {'isint': 'true'},
                     'SPOT_SOURCE_ID': {'isint': 'true'},
                     'SPOT_TARGET_ID': {'isint': 'true'}}
    obtained = nx.DiGraph(Model={'EdgeFeatures': edge_features})
    xmlr.add_edge_from_element(obtained, element, track_id)

    expected = nx.DiGraph(Model={'EdgeFeatures': edge_features})
    expected.add_edge(1, 2, x=20.0, y=25, SPOT_SOURCE_ID=1, SPOT_TARGET_ID=2)
    expected.nodes[1]['TRACK_ID'] = track_id
    expected.nodes[2]['TRACK_ID'] = track_id

    assert is_equal(obtained, expected)


def test_add_edge_from_element_no_node_ID():
    xml_data = ('<data SPOT_SOURCE_ID="1" x="20" y="25" />')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    track_id = 0
    
    edge_features = {'x': {'isint': 'false'}, 'y': {'isint': 'true'},
                     'SPOT_SOURCE_ID': {'isint': 'true'}}
    obtained = nx.DiGraph(Model={'EdgeFeatures': edge_features})
    xmlr.add_edge_from_element(obtained, element, track_id)
    
    expected = nx.DiGraph(Model={'EdgeFeatures': edge_features})
    
    assert is_equal(obtained, expected)


def test_add_edge_from_element_no_edge_attributes():
    xml_data = ('<data SPOT_SOURCE_ID="1" SPOT_TARGET_ID="2" />')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    track_id = 0

    edge_features = {'SPOT_SOURCE_ID': {'isint': 'true'},
                     'SPOT_TARGET_ID': {'isint': 'true'}}
    obtained = nx.DiGraph(Model={'EdgeFeatures': edge_features})
    xmlr.add_edge_from_element(obtained, element, track_id)

    expected = nx.DiGraph(Model={'EdgeFeatures': edge_features})
    expected.add_edge(1, 2, SPOT_SOURCE_ID=1, SPOT_TARGET_ID=2)
    expected.nodes[1]['TRACK_ID'] = track_id
    expected.nodes[2]['TRACK_ID'] = track_id

    assert is_equal(obtained, expected)


### add_all_edges ###

def test_add_all_edges_several_attributes():
    xml_data = ('<data>'
                '   <Track TRACK_ID="1" name="blob">'
                '       <Edge SPOT_SOURCE_ID="11" SPOT_TARGET_ID="12"'
                '           x="10" y="20" />'
                '       <Edge SPOT_SOURCE_ID="12" SPOT_TARGET_ID="13"'
                '           x="30" y="30" />'
                '   </Track>'
                '   <Track TRACK_ID="2" name="blub">'
                '       <Edge SPOT_SOURCE_ID="21" SPOT_TARGET_ID="22"'
                '           x="15" y="25" />'
                '   </Track>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    edge_features = {'x': {'isint': 'false'}, 'y': {'isint': 'true'},
                     'SPOT_SOURCE_ID': {'isint': 'true'},
                     'SPOT_TARGET_ID': {'isint': 'true'}}
    track_features = {'TRACK_ID': {'isint': 'true'}}

    obtained = nx.DiGraph(Model={'EdgeFeatures': edge_features,
                                 'TrackFeatures': track_features})
    obtained_tracks_attrib = xmlr.add_all_edges(obtained, it, element)
    obtained_tracks_attrib = sorted(obtained_tracks_attrib, 
                                    key=lambda d: d['TRACK_ID'])

    expected = nx.DiGraph(Model={'EdgeFeatures': edge_features,
                                 'TrackFeatures': track_features})
    expected.add_edge(11, 12,
                      SPOT_SOURCE_ID=11, SPOT_TARGET_ID=12, x=10.0, y=20)
    expected.add_edge(12, 13,
                      SPOT_SOURCE_ID=12, SPOT_TARGET_ID=13, x=30.0, y=30)
    expected.add_edge(21, 22,
                      SPOT_SOURCE_ID=21, SPOT_TARGET_ID=22, x=15.0, y=25)
    expected.add_nodes_from([(11, {'TRACK_ID': 1}),
                             (12, {'TRACK_ID': 1}),
                             (13, {'TRACK_ID': 1}),
                             (21, {'TRACK_ID': 2}),
                             (22, {'TRACK_ID': 2})])
    expected_tracks_attrib = [{'TRACK_ID': 2, 'name': 'blub'},
                              {'TRACK_ID': 1, 'name': 'blob'}]
    expected_tracks_attrib = sorted(expected_tracks_attrib, 
                                    key=lambda d: d['TRACK_ID'])

    assert is_equal(obtained, expected)
    assert obtained_tracks_attrib == expected_tracks_attrib


def test_add_all_edges_no_nodes_ID():
    xml_data = ('<data>'
                '   <Track TRACK_ID="1" name="blob">'
                '       <Edge x="10" y="20" />'
                '       <Edge x="30" y="30" />'
                '   </Track>'
                '   <Track TRACK_ID="2" name="blub">'
                '       <Edge x="15" y="25" />'
                '   </Track>'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    edge_features = {'x': {'isint': 'false'}, 'y': {'isint': 'true'}}
    track_features = {'TRACK_ID': {'isint': 'true'}}

    obtained = nx.DiGraph(Model={'EdgeFeatures': edge_features,
                                 'TrackFeatures': track_features})
    obtained_tracks_attrib = xmlr.add_all_edges(obtained, it, element)
    obtained_tracks_attrib = sorted(obtained_tracks_attrib, 
                                    key=lambda d: d['TRACK_ID'])

    expected = nx.DiGraph(Model={'EdgeFeatures': edge_features,
                                 'TrackFeatures': track_features})
    expected_tracks_attrib = [{'TRACK_ID': 2, 'name': 'blub'},
                              {'TRACK_ID': 1, 'name': 'blob'}]
    expected_tracks_attrib = sorted(expected_tracks_attrib, 
                                    key=lambda d: d['TRACK_ID'])

    assert is_equal(obtained, expected)
    assert obtained_tracks_attrib == expected_tracks_attrib


def test_add_all_edges_no_edges():
    xml_data = ('<data>'
                '   <Track TRACK_ID="1" name="blob" />'
                '   <Track TRACK_ID="2" name="blub" />'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    track_features = {'TRACK_ID': {'isint': 'true'}}

    obtained = nx.DiGraph(Model={'TrackFeatures': track_features})
    obtained_tracks_attrib = xmlr.add_all_edges(obtained, it, element)
    obtained_tracks_attrib = sorted(obtained_tracks_attrib, 
                                    key=lambda d: d['TRACK_ID'])

    expected = nx.DiGraph(Model={'TrackFeatures': track_features})
    expected_tracks_attrib = [{'TRACK_ID': 2, 'name': 'blub'},
                              {'TRACK_ID': 1, 'name': 'blob'}]
    expected_tracks_attrib = sorted(expected_tracks_attrib, 
                                    key=lambda d: d['TRACK_ID'])

    assert is_equal(obtained, expected)
    assert obtained_tracks_attrib == expected_tracks_attrib


def test_add_all_edges_no_track_id():
    xml_data = ('<data>'
            '   <Track name="blob">'
            '       <Edge SPOT_SOURCE_ID="11" SPOT_TARGET_ID="12"'
            '           x="10" y="20" />'
            '       <Edge SPOT_SOURCE_ID="12" SPOT_TARGET_ID="13"'
            '           x="30" y="30" />'
            '   </Track>'
            '   <Track name="blub">'
            '       <Edge SPOT_SOURCE_ID="21" SPOT_TARGET_ID="22"'
            '           x="15" y="25" />'
            '   </Track>'
            '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    edge_features = {'x': {'isint': 'false'}, 'y': {'isint': 'true'},
                     'SPOT_SOURCE_ID': {'isint': 'true'},
                     'SPOT_TARGET_ID': {'isint': 'true'}}

    obtained = nx.DiGraph(Model={'EdgeFeatures': edge_features,
                                 'TrackFeatures': {}})
    obtained_tracks_attrib = xmlr.add_all_edges(obtained, it, element)
    
    expected = nx.DiGraph(Model={'EdgeFeatures': edge_features,
                                 'TrackFeatures': {}})
    expected.add_edge(11, 12, SPOT_SOURCE_ID=11, SPOT_TARGET_ID=12, 
                      x=10.0, y=20)
    expected.add_edge(12, 13, SPOT_SOURCE_ID=12, SPOT_TARGET_ID=13,
                      x=30.0, y=30)
    expected.add_edge(21, 22, SPOT_SOURCE_ID=21, SPOT_TARGET_ID=22,
                      x=15.0, y=25)
    expected.add_nodes_from([(11, {'TRACK_ID': None}),
                             (12, {'TRACK_ID': None}),
                             (13, {'TRACK_ID': None}),
                             (21, {'TRACK_ID': None}),
                             (22, {'TRACK_ID': None})])
    expected_tracks_attrib = [{'name': 'blub'}, {'name': 'blob'}]
    expected_tracks_attrib = sorted(expected_tracks_attrib, 
                                    key=lambda d: d['name'])
    
    assert is_equal(obtained, expected)
    assert obtained_tracks_attrib == expected_tracks_attrib


def test_add_all_edges_no_track_attributes():
    xml_data = ('<data>'
            '   <Track>'
            '       <Edge SPOT_SOURCE_ID="11" SPOT_TARGET_ID="12"'
            '           x="10" y="20" />'
            '       <Edge SPOT_SOURCE_ID="12" SPOT_TARGET_ID="13"'
            '           x="30" y="30" />'
            '   </Track>'
            '   <Track>'
            '       <Edge SPOT_SOURCE_ID="21" SPOT_TARGET_ID="22"'
            '           x="15" y="25" />'
            '   </Track>'
            '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    edge_features = {'x': {'isint': 'false'}, 'y': {'isint': 'true'},
                     'SPOT_SOURCE_ID': {'isint': 'true'},
                     'SPOT_TARGET_ID': {'isint': 'true'}}

    obtained = nx.DiGraph(Model={'EdgeFeatures': edge_features,
                                 'TrackFeatures': {}})
    obtained_tracks_attrib = xmlr.add_all_edges(obtained, it, element)
    
    expected = nx.DiGraph(Model={'EdgeFeatures': edge_features,
                                 'TrackFeatures': {}})
    expected.add_edge(11, 12, SPOT_SOURCE_ID=11, SPOT_TARGET_ID=12,
                      x=10.0, y=20)
    expected.add_edge(12, 13, SPOT_SOURCE_ID=12, SPOT_TARGET_ID=13, 
                      x=30.0, y=30)
    expected.add_edge(21, 22, SPOT_SOURCE_ID=21, SPOT_TARGET_ID=22,
                      x=15.0, y=25)
    expected.add_nodes_from([(11, {'TRACK_ID': None}),
                             (12, {'TRACK_ID': None}),
                             (13, {'TRACK_ID': None}),
                             (21, {'TRACK_ID': None}),
                             (22, {'TRACK_ID': None})])
    expected_tracks_attrib = [{}, {}]
    
    assert is_equal(obtained, expected)
    assert obtained_tracks_attrib == expected_tracks_attrib


### get_filtered_tracks_ID ###

def test_get_filtered_tracks_ID():
    xml_data = ('<data>'
                '   <TrackID TRACK_ID="0" />'
                '   <TrackID TRACK_ID="1" />'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)

    obtained_ID = xmlr.get_filtered_tracks_ID(it, element)
    expected_ID = [0, 1]
    assert obtained_ID.sort() == expected_ID.sort()
    

def test_get_filtered_tracks_ID_no_ID():
    xml_data = ('<data>'
                '   <TrackID />'
                '   <TrackID />'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    obtained_ID = xmlr.get_filtered_tracks_ID(it, element)
    assert not obtained_ID


def test_get_filtered_tracks_ID_no_tracks():
    xml_data = ('<data>'
                '   <tag />'
                '   <tag />'
                '</data>')
    it = ET.iterparse(io.StringIO(xml_data), events=['start', 'end'])
    _, element = next(it)
    obtained_ID = xmlr.get_filtered_tracks_ID(it, element)
    assert not obtained_ID
    

### add_tracks_info ###

def test_add_tracks_info():
    g1_attr = {'name': 'blob', 'TRACK_ID': 0}
    g2_attr = {'name': 'blub', 'TRACK_ID': 1}

    g1_obt = nx.DiGraph()
    g1_obt.add_node(1, TRACK_ID=0)
    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, TRACK_ID=1)
    obtained_graphs = xmlr.add_tracks_info([g1_obt, g2_obt],
                                            [g1_attr, g2_attr])

    g1_exp = nx.DiGraph()
    g1_exp.graph['name'] = 'blob'
    g1_exp.graph['TRACK_ID'] = 0
    g1_exp.add_node(1, TRACK_ID=0)
    g2_exp = nx.DiGraph()
    g2_exp.graph['name'] = 'blub'
    g2_exp.graph['TRACK_ID'] = 1
    g2_exp.add_node(2, TRACK_ID=1)
    expected_graphs = [g1_exp, g2_exp]

    assert is_equal(obtained_graphs[0], expected_graphs[0])
    assert is_equal(obtained_graphs[1], expected_graphs[1])


def test_add_tracks_info_no_track_ID_on_all_nodes():
    g1_attr = {'name': 'blob', 'TRACK_ID': 0}
    g2_attr = {'name': 'blub', 'TRACK_ID': 1}

    g1_obt = nx.DiGraph()
    g1_obt.add_node(1)
    g1_obt.add_node(3)
    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, TRACK_ID=1)
    obtained_graphs = xmlr.add_tracks_info([g1_obt, g2_obt],
                                            [g1_attr, g2_attr])

    g1_exp = nx.DiGraph()
    g1_exp.add_node(1)
    g1_exp.add_node(3)
    g2_exp = nx.DiGraph()
    g2_exp.graph['name'] = 'blub'
    g2_exp.graph['TRACK_ID'] = 1
    g2_exp.add_node(2, TRACK_ID=1)
    expected_graphs = [g1_exp, g2_exp]

    assert is_equal(obtained_graphs[0], expected_graphs[0])
    assert is_equal(obtained_graphs[1], expected_graphs[1])
    

def test_add_tracks_info_no_track_ID_on_one_node():
    g1_attr = {'name': 'blob', 'TRACK_ID': 0}
    g2_attr = {'name': 'blub', 'TRACK_ID': 1}

    g1_obt = nx.DiGraph()
    g1_obt.add_node(1)
    g1_obt.add_node(3)
    g1_obt.add_node(4, TRACK_ID=0)
    
    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, TRACK_ID=1)
    obtained_graphs = xmlr.add_tracks_info([g1_obt, g2_obt],
                                            [g1_attr, g2_attr])

    g1_exp = nx.DiGraph()
    g1_exp.graph['name'] = 'blob'
    g1_exp.graph['TRACK_ID'] = 0
    g1_exp.add_node(1)
    g1_exp.add_node(3)
    g1_exp.add_node(4, TRACK_ID=0)
    g2_exp = nx.DiGraph()
    g2_exp.graph['name'] = 'blub'
    g2_exp.graph['TRACK_ID'] = 1
    g2_exp.add_node(2, TRACK_ID=1)
    expected_graphs = [g1_exp, g2_exp]

    assert is_equal(obtained_graphs[0], expected_graphs[0])
    assert is_equal(obtained_graphs[1], expected_graphs[1])


def test_add_tracks_info_different_ID_for_one_track():
    g1_attr = {'name': 'blob', 'TRACK_ID': 0}
    g2_attr = {'name': 'blub', 'TRACK_ID': 1}
    
    g1_obt = nx.DiGraph()
    g1_obt.add_node(1, TRACK_ID=0)
    g1_obt.add_node(3, TRACK_ID=2)
    g1_obt.add_node(4, TRACK_ID=0)
    
    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, TRACK_ID=1)
    with pytest.raises(ValueError):
        obtained_graphs = xmlr.add_tracks_info([g1_obt, g2_obt],
                                                [g1_attr, g2_attr])


def test_add_tracks_info_no_nodes():
    g1_attr = {'name': 'blob', 'TRACK_ID': 0}
    g2_attr = {'name': 'blub', 'TRACK_ID': 1}

    g1_obt = nx.DiGraph()
    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, TRACK_ID=1)
    obtained_graphs = xmlr.add_tracks_info([g1_obt, g2_obt],
                                            [g1_attr, g2_attr])

    g1_exp = nx.DiGraph()
    g2_exp = nx.DiGraph()
    g2_exp.graph['name'] = 'blub'
    g2_exp.graph['TRACK_ID'] = 1
    g2_exp.add_node(2, TRACK_ID=1)
    expected_graphs = [g1_exp, g2_exp]

    assert is_equal(obtained_graphs[0], expected_graphs[0])
    assert is_equal(obtained_graphs[1], expected_graphs[1])





