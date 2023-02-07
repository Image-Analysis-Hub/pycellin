#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

from lxml import etree as ET
import networkx as nx

import XML_reader


def write_FeatureDeclarations(xf: ET.xmlfile,
                              graphs: list[nx.DiGraph]) -> None:
    """Write the feature declarations into an XML file.

    The feature declarations are divided in three parts: spot features,
    edge features, and track features.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write('\n\t\t')
    with xf.element('FeatureDeclarations'):
        features_type = ['SpotFeatures', 'EdgeFeatures', 'TrackFeatures']
        for f_type in features_type:
            # We need to check that all graphs have the same features
            # definition.
            dict_feats = {k: graphs[0].graph['Model'].get(k, None)
                          for k in [f_type]}
            for graph in graphs[1:]:
                tmp_dict = {k: graph.graph['Model'].get(k, None)
                            for k in [f_type]}
                assert dict_feats == tmp_dict

            # Actual writing.
            xf.write('\n\t\t\t')
            with xf.element(f_type):
                xf.write('\n\t\t\t\t')
                # For each type of features, data is stored as a dict of dict.
                # E.g. for SpotFeatures:
                # {'QUALITY': {'feature': 'QUALITY', 'name': 'Quality'...},
                #  'POSITION_X': {'feature': 'POSITION_X', 'name': 'X'...},
                #  ...}
                for v_feats in dict_feats.values():
                    dict_length = len(v_feats)
                    for i, v in enumerate(v_feats.values()):
                        el_feat = ET.Element('Feature', v)
                        xf.write(el_feat)
                        if i != dict_length - 1:
                            xf.write('\n\t\t\t\t')
                xf.write('\n\t\t\t')
        xf.write('\n\t\t')
    # xf.write('\n\t')


def create_Spot(graph: nx.DiGraph, node: dict) -> ET._Element:
    """Create an XML Spot Element representing a graph node. 

    Args:
        graph (nx.DiGraph): Graph containing the node to write.
        node (dict): Attributes of the spot.

    Returns:
        ET._Element: The newly created Spot Element.
    """
    # Building Spot attributes.
    exluded_keys = ['TRACK_ID', 'ROI_N_POINTS']
    n_attr = {k: str(v) for k, v in graph.nodes[node].items()
              if k not in exluded_keys}
    n_attr['ROI_N_POINTS'] = str(len(graph.nodes[node]['ROI_N_POINTS']))

    # Building Spot text: coordinates of ROI points.
    coords = [item for pt in graph.nodes[node]['ROI_N_POINTS'] for item in pt]

    el_node = ET.Element('Spot', n_attr)
    el_node.text = ' '.join(map(str, coords))
    return el_node


def write_AllSpots(xf: ET.xmlfile, graphs: list[nx.DiGraph]) -> None:
    """Write the nodes/spots data into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write('\n\t\t')
    nb_nodes = sum([len(graph) for graph in graphs])
    with xf.element('AllSpots', {'nspots': str(nb_nodes)}):
        # For each frame, nodes can be spread over several graphs so we first
        # need to identify all of the existing frames.
        frames = set()
        for graph in graphs:
            frames.update(nx.get_node_attributes(graph, 'FRAME').values())

        # Then at each frame, we can find the nodes and write its data.
        for frame in frames:
            xf.write('\n\t\t\t')
            with xf.element('SpotsInFrame', {'frame': str(frame)}):
                for graph in graphs:
                    nodes = [n for n in graph.nodes()
                             if graph.nodes[n]['FRAME'] == frame]
                    for node in nodes:
                        xf.write('\n\t\t\t\t')
                        xf.write(create_Spot(graph, node))
                xf.write('\n\t\t\t')
        xf.write('\n\t\t')


def write_AllTracks(xf: ET.xmlfile, graphs: list[nx.DiGraph]) -> None:
    """Write the tracks data into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write('\n\t\t')
    with xf.element('AllTracks'):
        pass


def write_FilteredTracks(xf: ET.xmlfile, graphs: list[nx.DiGraph]) -> None:
    """Write the filtered tracks data into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write('\n\t\t')
    with xf.element('FilteredTracks'):
        pass
    xf.write('\n\t')


def write_Model(xf: ET.xmlfile, graphs: list[nx.DiGraph]) -> None:
    """Write all the model data into an XML file.

    This includes Features declarations, spots, tracks and filtered tracks.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """

    # Checking that each and every graph have the same features.
    # It should be the case but better safe than sorry.
    dict_units = {k: graphs[0].graph['Model'].get(k, None)
                  for k in ('spatialunits', 'timeunits')}
    if len(graphs) > 1:
        for graph in graphs[1:]:
            tmp_dict = {k: graph.graph['Model'].get(k, None)
                        for k in ('spatialunits', 'timeunits')}
            assert dict_units == tmp_dict

    with xf.element('Model', dict_units):
        write_FeatureDeclarations(xf, graphs)
        write_AllSpots(xf, graphs)
        write_AllTracks(xf, graphs)
        write_FilteredTracks(xf, graphs)
        # xf.write('\n\t')


def write_Settings(xf: ET.xmlfile, settings: ET._Element) -> None:
    """Write the given TrackMate settings into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write.
        settings (ET._Element): Element holding all the settings to write.
    """

    xf.write(settings, pretty_print=True)


def write_TrackMate_XML(graphs: list[nx.DiGraph], settings: ET._Element,
                        xml_path: str) -> None:
    """Write an XML file readable by TrackMate from networkX graphs data.

    Args:
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
        settings (ET._Element): Element holding all the settings to write.
        xml_path (str): Path of the XML file to write.
    """

    with ET.xmlfile(xml_path, encoding='utf-8', close=True) as xf:
        xf.write_declaration()
        with xf.element('TrackMate'):
            xf.write('\n\t')
            write_Model(xf, graphs)
            xf.write('\n\t')
            write_Settings(xf, settings)


if __name__ == "__main__":

    # xml_in = "/mnt/data/Code/pytmn/samples/FakeTracks.xml"
    # xml_out = '/mnt/data/Code/pytmn/samples/FakeTracks_written.xml'
    # graph_folder = "/mnt/data/Code/pytmn/samples/"

    xml_in = 'G:/RAID/IAH/Code/pytmn/samples/FakeTracks.xml'
    xml_out = 'G:/RAID/IAH/Code/pytmn/samples/FakeTracks_written.xml'
    graph_folder = "G:/RAID/IAH/Code/pytmn/samples/"

    def load_graphs(folder):
        # only tracks
        graphs = []
        for file in Path(folder).glob('*_Track_*.gz'):
            print(file)
            graph = nx.read_gpickle(file)
            print(len(graph))
            graphs.append(graph)
        return graphs

    def load_graphs_rost(folder):
        # one graph
        graphs = []
        for file in Path(folder).glob('FakeTracks.gz'):
            print(file)
            graph = nx.read_gpickle(file)
            print(len(graph))
            graphs.append(graph)
        return graphs

    def load_graphs_rst(folder):
        # tracks + lone nodes
        graphs = []
        for file in Path(folder).glob('FakeTracks_*.gz'):
            print(file)
            graph = nx.read_gpickle(file)
            print(len(graph))
            graphs.append(graph)
        return graphs

    graphs = load_graphs_rost(graph_folder)
    print(len(graphs))

    settings = XML_reader.read_settings(xml_in)
    write_TrackMate_XML(graphs, settings, xml_out)

    # derp = {k for k,v in graphs[0].nodes[2004].items()}
    # print(derp)

    # FeatureDeclarations
    # AllSpots
    # AllTracks
    # FilteredTracks

    # print(graphs[0].graph['Model'])
    # print({k: graphs[0].graph['Model'].get(k, None) for k in ('spatialunits', 'timeunits')})

    # def generate_some_elements():
    #     a = ET.Element('a')
    #     for i in range(10):
    #         rec = ET.SubElement(a, "record", id=str(i))
    #         rec.text = "record text data"

    #     return a

    # with ET.xmlfile(xml_out, encoding='utf-8') as xf:
    #     xf.write_declaration(standalone=True)
    #     xf.write_doctype('<!DOCTYPE root SYSTEM "some.dtd">')

    #     # generate an element (the root element)
    #     with xf.element('root'):
    #          # write a complete Element into the open root element
    #          xf.write(ET.Element('test'), pretty_print=True)

    #         #  # generate and write more Elements, e.g. through iterparse
    #          for element in generate_some_elements():
    #              # serialise generated elements into the XML file
    #              xf.write(element, pretty_print=True)

    #          # or write multiple Elements or strings at once
    #          xf.write(ET.Element('start'), "text", ET.Element('end'),
    #                   pretty_print=True)

    # def derp(tag):
    #     with xf.element(tag):
    #             for value in '123':
    #                 # construct a really complex XML tree
    #                 el = ET.Element('xyz', attr=value)
    #                 xf.write(el, pretty_print=True)
    #                 # no longer needed, discard it right away!
    #                 el = None

    # with ET.xmlfile(xml_out, encoding='utf-8') as xf:
    #     with xf.element('abc'):
    #         derp('model')

    # a = ET.Element('a')
    #         for i in range(4):
    #             rec = ET.SubElement(a, "record", id=str(i))
    #             rec.text = "record text data"
    #             rec2 = ET.SubElement(rec, "info", code=str(i+10))
    #             rec3 = ET.SubElement(rec, "info", code=str(i+20))
    #         xf.write(a, pretty_print=True)
