#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from lxml import etree as ET
import networkx as nx

import XML_reader


def write_FeatureDeclarations(graphs: list[nx.DiGraph], xml_path: str) -> None:
    pass


def write_AllSpots(graphs: list[nx.DiGraph], xml_path: str) -> None:
    pass


def write_AllTracks(graphs: list[nx.DiGraph], xml_path: str) -> None:
    pass


def write_FilteredTracks(graphs: list[nx.DiGraph], xml_path: str) -> None:
    pass


def write_Model(graphs: list[nx.DiGraph], xml_path: str) -> None:

    write_FeatureDeclarations(graphs, xml_path)
    write_AllSpots(graphs, xml_path)
    write_AllTracks(graphs, xml_path)
    write_FilteredTracks(graphs, xml_path)

def write_Settings(settings: ET._Element, xml_path: str) -> None:

    with ET.xmlfile(xml_path, encoding='utf-8') as xf:
        xf.write(settings, pretty_print=True)
        

def write_TrackMate_XML(graphs: list[nx.DiGraph], settings: ET._Element,
                        xml_path: str) -> None:

    write_Model(graphs, xml_path)
    write_Settings(settings, xml_path)


if __name__ == "__main__":

    xml_in = "/mnt/data/Code/pytmn/samples/FakeTracks.xml"
    xml_out = '/mnt/data/xml_test/somefile.xml'

    settings = XML_reader.read_settings(xml_in)
    graphs = [nx.DiGraph(), nx.DiGraph(), nx.DiGraph()]
    write_TrackMate_XML(graphs, settings, xml_out)

    # def generate_some_elements():
    #     a = ET.Element('a')
    #     for i in range(10):
    #         rec = ET.SubElement(a, "record", id=str(i))
    #         rec.text = "record text data"

    #     return a

    # # with ET.xmlfile(file_path, encoding='utf-8') as xf:
    # #     xf.write_declaration(standalone=True)
    # #     xf.write_doctype('<!DOCTYPE root SYSTEM "some.dtd">')

    # #     # generate an element (the root element)
    # #     with xf.element('root'):
    # #          # write a complete Element into the open root element
    # #          xf.write(ET.Element('test'), pretty_print=True)

    # #         #  # generate and write more Elements, e.g. through iterparse
    # #         #  for element in generate_some_elements():
    # #         #      # serialise generated elements into the XML file
    # #         #      xf.write(element, pretty_print=True)

    # #          # or write multiple Elements or strings at once
    # #         #  xf.write(ET.Element('start'), "text", ET.Element('end'), 
    # #         #           pretty_print=True)

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

    #         a = ET.Element('a')
    #         for i in range(4):
    #             rec = ET.SubElement(a, "record", id=str(i))
    #             rec.text = "record text data"
    #             rec2 = ET.SubElement(rec, "info", code=str(i+10))
    #             rec3 = ET.SubElement(rec, "info", code=str(i+20))
    #         xf.write(a, pretty_print=True)
    