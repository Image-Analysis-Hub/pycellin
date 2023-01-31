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
    features_type = ['SpotFeatures', 'EdgeFeatures', 'TrackFeatures']
    for type in features_type:
        dict_feats = {k: graphs[0].graph['Model'].get(k, None) 
                    for k in [type]}
        for graph in graphs[1:]:
            tmp_dict = {k: graph.graph['Model'].get(k, None) 
                        for k in [type]}
            assert dict_feats == tmp_dict

        xf.write('\n\t\t')
        with xf.element(type):
            xf.write('\n\t\t\t')
            for v_feats in dict_feats.values():
                for v in v_feats.values():
                    el_feat = ET.Element('Feature', v)
                    xf.write(el_feat)
                    xf.write('\n\t\t\t')
            xf.write('\n\t\t')
    
    xf.write('\n\t')

def create_Spot(node: dict) -> ET._Element:
    """Create an XML Spot Element representing a graph node. 

    Args:
        node (dict): Attributes of the spot.

    Returns:
        ET._Element: The newly created Spot Element.
    """

    # print(graphs[0].nodes())
    # print(len(graphs[0].nodes[2004].keys()))  # 30 ici alors que 29 dans XML
    # TODO: dans les graphes, il y a les TRACK_ID en plus, bien penser à 
    # enlever ça avant d'écrire en XML
    pass


def write_AllSpots(xf: ET.xmlfile, graphs: list[nx.DiGraph]) -> None:
    """Write the nodes/spots data into an XML file.
    
    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    
    # Remove TRACK_ID from node attributes
    # Sort nodes by frame
    # For each frame, write the corresponding nodes, with ROI as text
    pass


def write_AllTracks(xf: ET.xmlfile, graphs: list[nx.DiGraph]) -> None:
    """Write the tracks data into an XML file.
    
    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    
    pass


def write_FilteredTracks(xf: ET.xmlfile, graphs: list[nx.DiGraph]) -> None:
    """Write the filtered tracks data into an XML file.
    
    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """

    pass


def write_Model(xf: ET.xmlfile, graphs: list[nx.DiGraph]) -> None:
    """Write all the model data into an XML file.

    This includes Features declarations, spots, tracks and filtered tracks.
    
    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    
    dict_units = {k: graphs[0].graph['Model'].get(k, None) 
                  for k in ('spatialunits', 'timeunits')}
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
    # xml_out = '/mnt/data/xml_test/somefile.xml'
    # graph_folder = "/mnt/data/Code/pytmn/samples/"

    xml_in = 'G:/RAID/IAH/Code/pytmn/samples/FakeTracks.xml'
    xml_out = 'G:/RAID/IAH/Code/pytmn/samples/FakeTracks_written.xml'
    graph_folder = "G:/RAID/IAH/Code/pytmn/samples/"

    # For now, not taking into account lone nodes.
    def load_graphs(folder):
        graphs = []
        for file in Path(folder).glob('*_Track_*.gz'):
            graph = nx.read_gpickle(file)
            graphs.append(graph)
        return graphs

    graphs = load_graphs(graph_folder)
    print(len(graphs))

    settings = XML_reader.read_settings(xml_in)
    write_TrackMate_XML(graphs, settings, xml_out)

    # print(graphs[0].graph['Model'].keys())
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
    