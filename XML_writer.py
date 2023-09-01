#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from pathlib import Path
import pickle
import sys
from typing import Union

from lxml import etree as ET
import networkx as nx

# TODO: delete lines below when main will be cleaned up.
import XML_reader
# sys.path.append('/mnt/data/Code/lleblanc/src/')
# sys.path.append('G:/RAID/IAH/Code/lleblanc/src/')
sys.path.append('/mnt/bee/Pasteur/Code/lleblanc/src/')
import lineage as lin


def write_FeatureDeclarations(
        xf: ET.xmlfile,
        graphs: list[nx.DiGraph],
        ) -> None:
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


def value_to_str(
        value: Union[int, float, str],
        ) -> str:
    """Convert a value to its associated string.

    Indeed, ET.write() method only accepts to write strings.
    However, TrackMate is only able to read Spot, Edge and Track
    features that can be parsed as numeric by Java.

    Args:
        value (Union[int, float, str]): Value to convert to string.

    Returns:
        str: The string equivalent of `value`.
    """
    # TODO: Should this function take care of converting non-numeric added
    # features to numeric ones (like GEN_ID)? Or should it be done in 
    # pycellin?
    if isinstance(value, str):
        return value
    elif math.isnan(value):
        return "NaN"
    elif math.isinf(value):
        if value > 0:
            return "Infinity"
        else:
            return "-Infinity"
    else:
        return str(value)


def create_Spot(
        graph: nx.DiGraph,
        node: int,
        ) -> ET._Element:
    """Create an XML Spot Element representing a graph node. 

    Args:
        graph (nx.DiGraph): Graph containing the node to create.
        node (int): ID of the node in the graph.

    Returns:
        ET._Element: The newly created Spot Element.
    """
    # Building Spot attributes.
    exluded_keys = ['TRACK_ID', 'ROI_N_POINTS']
    n_attr = {k: value_to_str(v) for k, v in graph.nodes[node].items()
              if k not in exluded_keys}
    n_attr['ROI_N_POINTS'] = str(len(graph.nodes[node]['ROI_N_POINTS']))

    # Building Spot text: coordinates of ROI points.
    coords = [item for pt in graph.nodes[node]['ROI_N_POINTS'] for item in pt]

    el_node = ET.Element('Spot', n_attr)
    el_node.text = ' '.join(map(str, coords))
    return el_node


def write_AllSpots(
        xf: ET.xmlfile, 
        graphs: list[nx.DiGraph],
        ) -> None:
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


def write_AllTracks(
        xf: ET.xmlfile,
        graphs: list[nx.DiGraph],
        ) -> None:
    """Write the tracks data into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write('\n\t\t')
    with xf.element('AllTracks'):
        for graph in graphs:
            # We have track tags to add only if there was a tracking done
            # in the first place. A graph with no TRACK_ID attribute has
            # no tracking associated.
            if 'TRACK_ID' not in graph.graph:
                continue

            # Track tags.
            xf.write('\n\t\t\t')
            exluded_keys = ['Model', 'FilteredTrack']
            t_attr = {k: value_to_str(v) for k, v in graph.graph.items()
                      if k not in exluded_keys}
            with xf.element('Track', t_attr):
                # Edge tags.
                for edge in graph.edges.data():
                    xf.write('\n\t\t\t\t')
                    e_attr = {k: value_to_str(v) for k, v in edge[2].items()}
                    xf.write(ET.Element('Edge', e_attr))
                xf.write('\n\t\t\t')
        xf.write('\n\t\t')


def write_FilteredTracks(
        xf: ET.xmlfile,
        graphs: list[nx.DiGraph],
        ) -> None:
    """Write the filtered tracks data into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write. 
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write('\n\t\t')
    with xf.element('FilteredTracks'):
        for graph in graphs:
            if 'TRACK_ID' in graph.graph and graph.graph['FilteredTrack']:
                xf.write('\n\t\t\t')
                t_attr = {'TRACK_ID': str(graph.graph['TRACK_ID'])}
                xf.write(ET.Element('TrackID', t_attr))
        xf.write('\n\t\t')
    xf.write('\n\t')


def write_Model(
        xf: ET.xmlfile, 
        graphs: list[nx.DiGraph],
        ) -> None:
    """Write all the model data into an XML file.

    This includes Features declarations, spots, tracks and filtered 
    tracks.

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


def write_Settings(
        xf: ET.xmlfile, 
        settings: ET._Element,
        ) -> None:
    """Write the given TrackMate settings into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write.
        settings (ET._Element): Element holding all the settings to write.
    """
    xf.write(settings, pretty_print=True)


def write_TrackMate_XML(
        graphs: list[nx.DiGraph], 
        settings: ET._Element,
        xml_path: str,
        ) -> None:
    """Write an XML file readable by TrackMate from networkX graphs data.

    Args:
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
        settings (ET._Element): Element holding all the settings to write.
        xml_path (str): Path of the XML file to write.
    """
    with ET.xmlfile(xml_path, encoding='utf-8', close=True) as xf:
        xf.write_declaration()
        # TODO: deal with the problem of unknown version.
        with xf.element('TrackMate', {'version': "unknown"}):
            xf.write('\n\t')
            write_Model(xf, graphs)
            xf.write('\n\t')
            write_Settings(xf, settings)


if __name__ == "__main__":

    # xml_in = "220516_Loading_Chamber_PDMS15for1_Ecoli-TB28-ZipA-mCherry_100X+SR3D_timestep5min_pressure1000mbar_Stage5_StackReg_crop_merged+track_FINAL.xml"
    # xml_out = '220516_Loading_Chamber_PDMS15for1_Ecoli-TB28-ZipA-mCherry_100X+SR3D_timestep5min_pressure1000mbar_Stage5_StackReg_crop_merged+track_FINAL_updated.xml'
    # folder = "/mnt/data/Films/Chip_Ec/220516/220516_AutomaticSelection/Stage5/"

    nb = '7' 

    folder = f"/mnt/bee/Pasteur/Films/For_Laura/Segmentation_ONLY/230828_Ec-BW-Rcs-FtsZ/Stage8/"
    file_graph = f'230828_Ec-BW-Rcs-FtsZ_Stage8_timestep30min_crop_merge_FINAL_updated.gz'
    xml_in = f'230828_Ec-BW-Rcs-FtsZ_Stage8_timestep30min_crop_merge_FINAL.xml'
    xml_out = f'230828_Ec-BW-Rcs-FtsZ_Stage8_timestep30min_crop_merge_FINAL_updated.xml'

    # folder = f"/mnt/data/Films/Chip_Ec/220907+230323_IbpA/Induction_threshold/Stage{nb}/"
    # file_graph = f'230323_IbpA_Stage{nb}_Composite_Crop_FinalMerge_updated.gz'
    # xml_in = f"230323_IbpA_Stage{nb}_Composite_Crop_FinalMerge.xml"
    # xml_out = f'230323_IbpA_Stage{nb}_Composite_Crop_FinalMerge_updated.xml'
    
    # folder = f"/mnt/data/Films/Chip_Ec/230109_RcsA/Induction_threshold/Stage{nb}/"
    # file_graph = f'230109_Ec-MG1655-ZipA-pRcsA_Stage{nb}_491_focus_crop_Merge_updated.gz'
    # xml_in = folder + f"230109_Ec-MG1655-ZipA-pRcsA_Stage{nb}_491_focus_crop_Merge.xml"
    # xml_out = folder + f'230109_Ec-MG1655-ZipA-pRcsA_Stage{nb}_491_focus_crop_Merge_updated.xml'

    # folder = f"/mnt/data/Films/Chip_Ec/220908/Induction_threshold/Stage{nb}/"
    # file_graph = f'220908_YiaG_Stage{nb}_timestep30min_focus_crop_Merge_FINAL_no-tracking_updated.gz'
    # xml_in = folder + f"220908_YiaG_Stage{nb}_timestep30min_focus_crop_Merge_FINAL_no-tracking.xml"
    # xml_out = folder + f"220908_YiaG_Stage{nb}_timestep30min_focus_crop_Merge_FINAL_no-tracking_updated.xml"
    
    # folder = f"/mnt/data/Films/Chip_Ec/220907/Induction_threshold/Stage{nb}/"
    # file_graph = f'220907_Ec-MG1655-ZipA-IbpA_timestep30min_Stage{nb}_crop_Merge_updated.gz'
    # xml_in = folder + f"220907_Ec-MG1655-ZipA-IbpA_timestep30min_Stage{nb}_crop_Merge.xml"
    # xml_out = folder + f"220907_Ec-MG1655-ZipA-IbpA_timestep30min_Stage{nb}_crop_Merge_updated.xml"
    
    # folder = f"/mnt/data/Films/Chip_Ec/221128/Induction_threshold/Stage{nb}/"
    # file_graph = f'221128_Ec-MG1655-ZipA-Cpx_timestep30min_Stage{nb}_crop_Merge_updated.gz'
    # xml_in = folder + f"221128_Ec-MG1655-ZipA-Cpx_timestep30min_Stage{nb}_crop_Merge.xml"
    # xml_out = folder + f"221128_Ec-MG1655-ZipA-Cpx_timestep30min_Stage{nb}_crop_Merge_updated.xml"

    # folder = f"/mnt/data/Films/Chip_Ec/221004/Induction_threshold/Stage{nb}/"
    # file_graph = f'221004_Ec-MG1655-ZipA-RecA_Stage{nb}_491nm_focus_crop_Merge_updated.gz'
    # xml_in = folder + f"221004_Ec-MG1655-ZipA-RecA_Stage{nb}_491nm_focus_crop_Merge.xml"
    # xml_out = folder + f"221004_Ec-MG1655-ZipA-RecA_Stage{nb}_491nm_focus_crop_Merge_updated.xml"

    # xml_in = "/mnt/data/Code/data_test_pytmn_writer/220516_Loading_Chamber_PDMS15for1_Ecoli-TB28-ZipA-mCherry_100X+SR3D_timestep5min_pressure1000mbar_Stage5_StackReg_crop_merged+track_FINAL.xml"
    # xml_out = '/mnt/data/Code/data_test_pytmn_writer/220516_Loading_Chamber_PDMS15for1_Ecoli-TB28-ZipA-mCherry_100X+SR3D_timestep5min_pressure1000mbar_Stage5_StackReg_crop_merged+track_FINAL_written.xml'
    # graph_folder = "/mnt/data/Code/data_test_pytmn_writer/"

    # xml_in = 'G:/RAID/IAH/Code/pytmn/samples/FakeTracks.xml'
    # xml_out = 'G:/RAID/IAH/Code/pytmn/samples/FakeTracks_written.xml'
    # graph_folder = "G:/RAID/IAH/Code/pytmn/samples/"

    # xml_in = 'G:/RAID/IAH/Film/XML_TEST/220516_Loading_Chamber_PDMS15for1_Ecoli-TB28-ZipA-mCherry_100X+SR3D_timestep5min_pressure1000mbar_Stage3_StackReg_crop_merged+track_FINAL.xml'
    # xml_out = 'G:/RAID/IAH/Film/XML_TEST/220516_Loading_Chamber_PDMS15for1_Ecoli-TB28-ZipA-mCherry_100X+SR3D_timestep5min_pressure1000mbar_Stage3_StackReg_crop_merged+track_FINAL_WRITTEN.xml'
    # graph_folder = "G:/RAID/IAH/Film/XML_TEST/"

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
        for file in Path(folder).glob('*_updated.gz'):
            print(file)
            with open(file, 'rb') as f:
                # graph = nx.read_gpickle(file)
                graph = pickle.load(f)
            print(len(graph))
            graphs.append(graph)
        return graphs

    def load_graphs_rst(folder):
        # tracks + lone nodes
        graphs = []
        for file in Path(folder).glob('*_updated.gz'):
            # print(file)
            graph = nx.read_gpickle(file)
            # print(len(graph))
            graphs.append(graph)
        return graphs
    


    graphs = load_graphs_rost(folder)
    print(len(graphs))
    # for graph in graphs:
    #     lin.add_node_attributes(graph, tracking=False)

    # graph = nx.read_gpickle(folder + file_graph)
    # print(len(graph))
    settings = XML_reader.read_settings(folder + xml_in)
    write_TrackMate_XML(graphs, settings, folder + xml_out)
    # settings = XML_reader.read_settings(xml_in)
    # write_TrackMate_XML(graphs, settings, xml_out)
