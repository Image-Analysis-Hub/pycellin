#!/usr/bin/env python3

"""Unit test for TrackMate XML file loader."""

import io
from copy import deepcopy
from typing import Any

import networkx as nx
import pytest
from lxml import etree as ET

import pycellin.io.trackmate.loader as tml
from pycellin.classes import CellLineage, Feature, FeaturesDeclaration
from pycellin.utils import is_equal

# Fixtures #####################################################################


@pytest.fixture(scope="module")
def units():
    return {"timeunits": "s", "spatialunits": "um"}


@pytest.fixture(scope="module")
def feat_QUALITY():
    return Feature(
        name="QUALITY",
        description="Quality",
        provenance="TrackMate",
        feat_type="node",
        lin_type="CellLineage",
        data_type="float",
    )


@pytest.fixture(scope="module")
def feat_FRAME():
    return Feature(
        name="FRAME",
        description="Frame",
        provenance="TrackMate",
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
    )


@pytest.fixture(scope="module")
def feat_spot_name():
    return Feature(
        name="cell_name",
        description="Name of the spot",
        provenance="TrackMate",
        feat_type="node",
        lin_type="CellLineage",
        data_type="string",
    )


@pytest.fixture(scope="module")
def spot_feats(feat_QUALITY: Feature, feat_FRAME: Feature, feat_spot_name: Feature):
    return {
        "QUALITY": feat_QUALITY,
        "FRAME": feat_FRAME,
        "cell_name": feat_spot_name,
    }


@pytest.fixture(scope="module")
def feat_SPOT_SOURCE_ID():
    return Feature(
        name="SPOT_SOURCE_ID",
        description="Source spot ID",
        provenance="TrackMate",
        feat_type="edge",
        lin_type="CellLineage",
        data_type="int",
    )


@pytest.fixture(scope="module")
def feat_SPOT_TARGET_ID():
    return Feature(
        name="SPOT_TARGET_ID",
        description="Target spot ID",
        provenance="TrackMate",
        feat_type="edge",
        lin_type="CellLineage",
        data_type="int",
    )


@pytest.fixture(scope="module")
def edge_feats(feat_SPOT_SOURCE_ID: Feature, feat_SPOT_TARGET_ID: Feature):
    return {
        "SPOT_SOURCE_ID": feat_SPOT_SOURCE_ID,
        "SPOT_TARGET_ID": feat_SPOT_TARGET_ID,
    }


@pytest.fixture(scope="module")
def feat_TRACK_INDEX():
    return Feature(
        name="TRACK_INDEX",
        description="Track index",
        provenance="TrackMate",
        feat_type="lineage",
        lin_type="CellLineage",
        data_type="int",
    )


@pytest.fixture(scope="module")
def feat_NUMBER_SPOTS():
    return Feature(
        name="NUMBER_SPOTS",
        description="Number of spots",
        provenance="TrackMate",
        feat_type="lineage",
        lin_type="CellLineage",
        data_type="int",
    )


@pytest.fixture(scope="module")
def feat_track_name():
    return Feature(
        name="lineage_name",
        description="Name of the track",
        provenance="TrackMate",
        feat_type="lineage",
        lin_type="CellLineage",
        data_type="string",
    )


@pytest.fixture(scope="module")
def track_feats(
    feat_TRACK_INDEX: Feature, feat_NUMBER_SPOTS: Feature, feat_track_name: Feature
):
    return {
        "TRACK_INDEX": feat_TRACK_INDEX,
        "NUMBER_SPOTS": feat_NUMBER_SPOTS,
        "lineage_name": feat_track_name,
    }


# _get_units ##################################################################


def test_get_units():
    xml_data = '<Model spatialunits="µm" timeunits="min"></Model>'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    obtained = tml._get_units(element)

    expected = {"spatialunits": "µm", "timeunits": "min"}

    assert obtained == expected


def test_get_units_missing_spaceunits():
    xml_data = '<Model timeunits="min"></Model>'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    obtained = tml._get_units(element)

    expected = {"spatialunits": "pixel", "timeunits": "min"}

    assert obtained == expected


def test_get_units_missing_timeunits():
    xml_data = '<Model spatialunits="µm"></Model>'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    obtained = tml._get_units(element)

    expected = {"spatialunits": "µm", "timeunits": "frame"}

    assert obtained == expected


def test_get_units_no_units():
    xml_data = "<Model></Model>"
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    obtained = tml._get_units(element)

    expected = {"spatialunits": "pixel", "timeunits": "frame"}

    assert obtained == expected


# _get_features_dict ##########################################################


def test_get_features_dict():
    xml_data = (
        "<SpotFeatures>"
        '   <Feature feature="QUALITY" isint="false" />'
        '   <Feature feature="FRAME" isint="true" />'
        "</SpotFeatures>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    features = tml._get_features_dict(it, element)
    spot_features = [
        {"feature": "QUALITY", "isint": "false"},
        {"feature": "FRAME", "isint": "true"},
    ]
    assert features == spot_features


def test_get_features_dict_no_feature_tag():
    xml_data = "<SpotFeatures></SpotFeatures>"
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    features = tml._get_features_dict(it, element)
    assert features == []


def test_get_features_dict_other_tag():
    xml_data = (
        "<SpotFeatures>"
        '   <Feature feature="QUALITY" isint="false" />'
        '   <Other feature="FRAME" isint="true" />'
        "</SpotFeatures>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    features = tml._get_features_dict(it, element)
    spot_features = [{"feature": "QUALITY", "isint": "false"}]
    assert features == spot_features


# _convert_and_add_feature ####################################################


def test_convert_and_add_feature_spot_feature(
    units: dict[str, str], feat_QUALITY: Feature
):
    trackmate_feature = {
        "feature": "QUALITY",
        "name": "Quality",
        "isint": "false",
        "dimension": "NONE",
    }
    feature_type = "SpotFeatures"
    obtained = FeaturesDeclaration()
    tml._convert_and_add_feature(trackmate_feature, feature_type, obtained, units)

    expected = FeaturesDeclaration({"QUALITY": feat_QUALITY})

    assert obtained == expected


def test_convert_and_add_feature_edge_feature(
    units: dict[str, str], feat_SPOT_SOURCE_ID: Feature
):
    trackmate_feature = {
        "feature": "SPOT_SOURCE_ID",
        "name": "Source spot ID",
        "isint": "true",
        "dimension": "NONE",
    }
    feature_type = "EdgeFeatures"
    obtained = FeaturesDeclaration()
    tml._convert_and_add_feature(trackmate_feature, feature_type, obtained, units)

    expected = FeaturesDeclaration({"SPOT_SOURCE_ID": feat_SPOT_SOURCE_ID})

    assert obtained == expected


def test_convert_and_add_feature_track_feature(
    units: dict[str, str], feat_TRACK_INDEX: Feature
):
    trackmate_feature = {
        "feature": "TRACK_INDEX",
        "name": "Track index",
        "isint": "true",
        "dimension": "NONE",
    }
    feature_type = "TrackFeatures"
    obtained = FeaturesDeclaration()
    tml._convert_and_add_feature(trackmate_feature, feature_type, obtained, units)

    expected = FeaturesDeclaration({"TRACK_INDEX": feat_TRACK_INDEX})

    assert obtained == expected


def test_convert_and_add_feature_invalid_feature_type(units: dict[str, str]):
    trackmate_feature = {
        "feature": "QUALITY",
        "name": "Quality",
        "isint": "false",
        "dimension": "NONE",
    }
    feature_type = "InvalidFeatureType"
    feat_declaration = FeaturesDeclaration()

    with pytest.raises(ValueError, match="Invalid feature type: InvalidFeatureType"):
        tml._convert_and_add_feature(
            trackmate_feature, feature_type, feat_declaration, units
        )


# _add_all_features ###########################################################


def test_add_all_features(
    spot_feats: dict[str, Any], edge_feats: dict[str, Any], track_feats: dict[str, Any]
):
    xml_data = (
        "<FeatureDeclarations>"
        "   <SpotFeatures>"
        '       <Feature feature="QUALITY" name="Quality" isint="false" '
        '                dimension="NONE"/>'
        '       <Feature feature="FRAME" name="Frame" isint="true" dimension="NONE"/>'
        "   </SpotFeatures>"
        "   <EdgeFeatures>"
        '       <Feature feature="SPOT_SOURCE_ID" name="Source spot ID" isint="true" '
        '                dimension="NONE"/>'
        '       <Feature feature="SPOT_TARGET_ID" name="Target spot ID" isint="true" '
        '                dimension="NONE"/>'
        "   </EdgeFeatures>"
        "   <TrackFeatures>"
        '       <Feature feature="TRACK_INDEX" name="Track index" isint="true" '
        '                dimension="NONE"/>'
        '       <Feature feature="NUMBER_SPOTS" name="Number of spots" isint="true" '
        '                dimension="NONE"/>'
        "   </TrackFeatures>"
        "</FeatureDeclarations>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = FeaturesDeclaration()
    tml._add_all_features(it, element, obtained, {})

    expected = FeaturesDeclaration({**spot_feats, **edge_feats, **track_feats})

    assert obtained == expected


def test_add_all_features_empty():
    xml_data = "<FeatureDeclarations></FeatureDeclarations>"
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = FeaturesDeclaration()
    tml._add_all_features(it, element, obtained, {})

    assert obtained == FeaturesDeclaration()


def test_add_all_features_tag_with_no_feature_tag(
    spot_feats: dict[str, Any], track_feats: dict[str, Any]
):
    xml_data = (
        "<FeatureDeclarations>"
        "   <SpotFeatures>"
        '       <Feature feature="QUALITY" name="Quality" isint="false" '
        '                dimension="NONE"/>'
        '       <Feature feature="FRAME" name="Frame" isint="true" dimension="NONE"/>'
        "   </SpotFeatures>"
        "   <EdgeFeatures>"
        "   </EdgeFeatures>"
        "   <TrackFeatures>"
        '       <Feature feature="TRACK_INDEX" name="Track index" isint="true" '
        '                dimension="NONE"/>'
        '       <Feature feature="NUMBER_SPOTS" name="Number of spots" isint="true" '
        '                dimension="NONE"/>'
        "   </TrackFeatures>"
        "</FeatureDeclarations>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = FeaturesDeclaration()
    tml._add_all_features(it, element, obtained, {})

    expected = FeaturesDeclaration({**spot_feats, **track_feats})

    assert obtained == expected


# _convert_attributes #########################################################


def test_convert_attributes():
    features = {
        "feat_float": Feature("", "", "", "node", "CellLineage", data_type="float"),
        "feat_int": Feature("", "", "", "node", "CellLineage", data_type="int"),
        "feat_neg": Feature("", "", "", "node", "CellLineage", data_type="int"),
        "feat_string": Feature("", "", "", "node", "CellLineage", data_type="string"),
    }

    obtained_attr = {
        "feat_float": "30",
        "feat_int": "20",
        "feat_neg": "-10",
        "feat_string": "nope",
    }
    tml._convert_attributes(obtained_attr, features, "node")

    expected_attr = {
        "feat_float": 30.0,
        "feat_int": 20,
        "feat_neg": -10.0,
        "feat_string": "nope",
    }

    assert obtained_attr == expected_attr


def test_convert_attributes_specific_keys():
    features = {}

    obtained_attr = {"ID": "42", "name": "ID42", "ROI_N_POINTS": "something here"}
    tml._convert_attributes(obtained_attr, features, "node")

    expected_attr = {"ID": 42, "name": "ID42", "ROI_N_POINTS": "something here"}

    assert obtained_attr == expected_attr


def test_convert_attributes_ValueError():
    features = {
        "feat_int": Feature("", "", "", "node", "CellLineage", data_type="integer")
    }
    attributes = {"feat_int": "20"}

    with pytest.raises(ValueError):
        tml._convert_attributes(attributes, features, "node")


def test_convert_attributes_missing_feat():
    features = {
        "feat_float": Feature("", "", "", "node", "CellLineage", data_type="float"),
    }
    attributes = {"feat_float": "30", "feat_int": "20"}

    with pytest.warns(UserWarning):
        tml._convert_attributes(attributes, features, "node")
    assert features["feat_int"].name == "feat_int"
    assert features["feat_int"].description == "unknown"
    assert features["feat_int"].provenance == "unknown"
    assert features["feat_int"].feat_type == "node"
    assert features["feat_int"].lin_type == "CellLineage"
    assert features["feat_int"].data_type == "unknown"
    assert features["feat_int"].unit == "unknown"


# _convert_ROI_coordinates ####################################################


def test_convert_ROI_coordinates_2D():
    el_obtained = ET.Element("Spot")
    el_obtained.attrib["ROI_N_POINTS"] = "3"
    el_obtained.text = "1 2.0 -3 -4.0 5.5 6"
    att_obtained = deepcopy(el_obtained.attrib)
    tml._convert_ROI_coordinates(el_obtained, att_obtained)

    att_expected = {
        "ROI_N_POINTS": "3",
        "ROI_coords": [(1.0, 2.0), (-3.0, -4.0), (5.5, 6.0)],
    }

    assert att_obtained == att_expected


def test_convert_ROI_coordinates_3D():
    el_obtained = ET.Element("Spot")
    el_obtained.attrib["ROI_N_POINTS"] = "2"
    el_obtained.text = "1 2.0 -3 -4.0 5.5 6"
    att_obtained = deepcopy(el_obtained.attrib)
    tml._convert_ROI_coordinates(el_obtained, att_obtained)

    att_expected = {
        "ROI_N_POINTS": "2",
        "ROI_coords": [(1.0, 2.0, -3.0), (-4.0, 5.5, 6.0)],
    }

    assert att_obtained == att_expected


def test_convert_ROI_coordinates_KeyError():
    el_obtained = ET.Element("Spot")
    el_obtained.text = "1 2.0 -3 -4.0 5.5 6"
    att_obtained = deepcopy(el_obtained.attrib)

    with pytest.raises(KeyError):
        tml._convert_ROI_coordinates(el_obtained, att_obtained)


def test_convert_ROI_coordinates_no_ROI_txt():
    el_obtained = ET.Element("Spot")
    el_obtained.attrib["ROI_N_POINTS"] = "2"
    att_obtained = deepcopy(el_obtained.attrib)
    tml._convert_ROI_coordinates(el_obtained, att_obtained)

    att_expected = {"ROI_N_POINTS": "2", "ROI_coords": None}

    assert att_obtained == att_expected


# _add_all_nodes ##############################################################


def test_add_all_nodes_several_attributes():
    xml_data = (
        "<data>"
        "   <frame>"
        '       <Spot name="ID1000" ID="1000" x="10" y="20" />'
        '       <Spot name="ID1001" ID="1001" x="30.5" y="30" />'
        "   </frame>"
        "</data>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    spot_features = {
        "x": Feature("", "", "", "node", "CellLineage", data_type="float"),
        "y": Feature("", "", "", "node", "CellLineage", data_type="int"),
    }
    feat_decl = FeaturesDeclaration(spot_features)
    obtained = nx.DiGraph()
    tml._add_all_nodes(it, element, feat_decl, obtained)

    expected = nx.DiGraph()
    expected.add_nodes_from(
        [
            (1001, {"name": "ID1001", "y": 30, "ID": 1001, "x": 30.5}),
            (1000, {"name": "ID1000", "ID": 1000, "x": 10.0, "y": 20}),
        ]
    )

    assert is_equal(obtained, expected)


def test_add_all_nodes_only_ID_attribute():
    xml_data = (
        "<data>"
        "   <frame>"
        '       <Spot ID="1000" />'
        '       <Spot ID="1001" />'
        "   </frame>"
        "</data>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = nx.DiGraph()
    tml._add_all_nodes(it, element, FeaturesDeclaration(), obtained)

    expected = nx.DiGraph()
    expected.add_nodes_from([(1001, {"ID": 1001}), (1000, {"ID": 1000})])

    assert is_equal(obtained, expected)


def test_add_all_nodes_no_node_attributes():
    xml_data = (
        '<data>   <frame>       <Spot />       <Spot ID="1001" />   </frame></data>'
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = nx.DiGraph()
    tml._add_all_nodes(it, element, FeaturesDeclaration(), obtained)

    expected = nx.DiGraph()
    expected.add_nodes_from([(1001, {"ID": 1001})])

    assert is_equal(obtained, expected)


def test_add_all_nodes_no_nodes():
    xml_data = "<data>   <frame /></data>"
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = nx.DiGraph()
    tml._add_all_nodes(it, element, FeaturesDeclaration(), obtained)

    assert is_equal(obtained, nx.DiGraph())


# _add_edge ###################################################################


def test_add_edge():
    xml_data = '<data SPOT_SOURCE_ID="1" SPOT_TARGET_ID="2" x="20" y="25" />'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    track_id = 0

    edge_feats = {
        "x": Feature("", "", "", "edge", "CellLineage", data_type="float"),
        "y": Feature("", "", "", "edge", "CellLineage", data_type="int"),
        "SPOT_SOURCE_ID": Feature("", "", "", "edge", "CellLineage", data_type="int"),
        "SPOT_TARGET_ID": Feature("", "", "", "edge", "CellLineage", data_type="int"),
    }
    obtained = nx.DiGraph()
    feat_decl = FeaturesDeclaration(edge_feats)
    tml._add_edge(element, feat_decl, obtained, track_id)

    expected = nx.DiGraph()
    expected.add_edge(1, 2, x=20.0, y=25, SPOT_SOURCE_ID=1, SPOT_TARGET_ID=2)
    expected.nodes[1]["TRACK_ID"] = track_id
    expected.nodes[2]["TRACK_ID"] = track_id

    assert is_equal(obtained, expected)


def test_add_edge_no_node_ID():
    xml_data = '<data SPOT_SOURCE_ID="1" x="20" y="25" />'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    track_id = 0

    edge_feats = {
        "x": Feature("", "", "", "edge", "CellLineage", data_type="float"),
        "y": Feature("", "", "", "edge", "CellLineage", data_type="int"),
        "SPOT_SOURCE_ID": Feature("", "", "", "edge", "CellLineage", data_type="int"),
    }
    obtained = nx.DiGraph()
    feat_decl = FeaturesDeclaration(edge_feats)
    tml._add_edge(element, feat_decl, obtained, track_id)

    expected = nx.DiGraph()

    assert is_equal(obtained, expected)


def test_add_edge_no_edge_attributes():
    xml_data = '<data SPOT_SOURCE_ID="1" SPOT_TARGET_ID="2" />'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    track_id = 0

    edge_feats = {
        "SPOT_SOURCE_ID": Feature("", "", "", "edge", "CellLineage", data_type="int"),
        "SPOT_TARGET_ID": Feature("", "", "", "edge", "CellLineage", data_type="int"),
    }
    obtained = nx.DiGraph()
    feat_decl = FeaturesDeclaration(edge_feats)
    tml._add_edge(element, feat_decl, obtained, track_id)

    expected = nx.DiGraph()
    expected.add_edge(1, 2, SPOT_SOURCE_ID=1, SPOT_TARGET_ID=2)
    expected.nodes[1]["TRACK_ID"] = track_id
    expected.nodes[2]["TRACK_ID"] = track_id

    assert is_equal(obtained, expected)


# _build_tracks ###############################################################


def test_build_tracks_several_attributes():
    xml_data = (
        "<data>"
        '   <Track TRACK_ID="1" name="blob">'
        '       <Edge SPOT_SOURCE_ID="11" SPOT_TARGET_ID="12"'
        '           x="10" y="20" />'
        '       <Edge SPOT_SOURCE_ID="12" SPOT_TARGET_ID="13"'
        '           x="30" y="30" />'
        "   </Track>"
        '   <Track TRACK_ID="2" name="blub">'
        '       <Edge SPOT_SOURCE_ID="21" SPOT_TARGET_ID="22"'
        '           x="15" y="25" />'
        "   </Track>"
        "</data>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    edge_feats = {
        "x": Feature("", "", "", "edge", "CellLineage", data_type="float"),
        "y": Feature("", "", "", "edge", "CellLineage", data_type="int"),
        "SPOT_SOURCE_ID": Feature("", "", "", "edge", "CellLineage", data_type="int"),
        "SPOT_TARGET_ID": Feature("", "", "", "edge", "CellLineage", data_type="int"),
    }
    track_feats = {
        "TRACK_ID": Feature("", "", "", "lineage", "CellLineage", data_type="int")
    }

    obtained = nx.DiGraph()
    feat_decl = FeaturesDeclaration({**edge_feats, **track_feats})
    obtained_tracks_attrib = tml._build_tracks(it, element, feat_decl, obtained)
    obtained_tracks_attrib = sorted(obtained_tracks_attrib, key=lambda d: d["TRACK_ID"])

    expected = nx.DiGraph()
    expected.add_edge(11, 12, SPOT_SOURCE_ID=11, SPOT_TARGET_ID=12, x=10.0, y=20)
    expected.add_edge(12, 13, SPOT_SOURCE_ID=12, SPOT_TARGET_ID=13, x=30.0, y=30)
    expected.add_edge(21, 22, SPOT_SOURCE_ID=21, SPOT_TARGET_ID=22, x=15.0, y=25)
    expected.add_nodes_from(
        [
            (11, {"TRACK_ID": 1}),
            (12, {"TRACK_ID": 1}),
            (13, {"TRACK_ID": 1}),
            (21, {"TRACK_ID": 2}),
            (22, {"TRACK_ID": 2}),
        ]
    )
    expected_tracks_attrib = [
        {"TRACK_ID": 2, "name": "blub"},
        {"TRACK_ID": 1, "name": "blob"},
    ]
    expected_tracks_attrib = sorted(expected_tracks_attrib, key=lambda d: d["TRACK_ID"])

    assert is_equal(obtained, expected)
    assert obtained_tracks_attrib == expected_tracks_attrib


def test_build_tracks_no_nodes_ID():
    xml_data = (
        "<data>"
        '   <Track TRACK_ID="1" name="blob">'
        '       <Edge x="10" y="20" />'
        '       <Edge x="30" y="30" />'
        "   </Track>"
        '   <Track TRACK_ID="2" name="blub">'
        '       <Edge x="15" y="25" />'
        "   </Track>"
        "</data>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    edge_feats = {
        "x": Feature("", "", "", "edge", "CellLineage", data_type="float"),
        "y": Feature("", "", "", "edge", "CellLineage", data_type="int"),
    }
    track_feats = {
        "TRACK_ID": Feature("", "", "", "lineage", "CellLineage", data_type="int")
    }

    obtained = nx.DiGraph()
    feat_decl = FeaturesDeclaration({**edge_feats, **track_feats})
    obtained_tracks_attrib = tml._build_tracks(it, element, feat_decl, obtained)
    obtained_tracks_attrib = sorted(obtained_tracks_attrib, key=lambda d: d["TRACK_ID"])

    expected = nx.DiGraph()
    expected_tracks_attrib = [
        {"TRACK_ID": 2, "name": "blub"},
        {"TRACK_ID": 1, "name": "blob"},
    ]
    expected_tracks_attrib = sorted(expected_tracks_attrib, key=lambda d: d["TRACK_ID"])

    assert is_equal(obtained, expected)
    assert obtained_tracks_attrib == expected_tracks_attrib


def test_build_tracks_no_edges():
    xml_data = (
        "<data>"
        '   <Track TRACK_ID="1" name="blob" />'
        '   <Track TRACK_ID="2" name="blub" />'
        "</data>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    track_feats = {
        "TRACK_ID": Feature("", "", "", "lineage", "CellLineage", data_type="int")
    }

    obtained = nx.DiGraph()
    feat_decl = FeaturesDeclaration(track_feats)
    obtained_tracks_attrib = tml._build_tracks(it, element, feat_decl, obtained)
    obtained_tracks_attrib = sorted(obtained_tracks_attrib, key=lambda d: d["TRACK_ID"])

    expected = nx.DiGraph()
    expected_tracks_attrib = [
        {"TRACK_ID": 2, "name": "blub"},
        {"TRACK_ID": 1, "name": "blob"},
    ]
    expected_tracks_attrib = sorted(expected_tracks_attrib, key=lambda d: d["TRACK_ID"])

    assert is_equal(obtained, expected)
    assert obtained_tracks_attrib == expected_tracks_attrib


def test_build_tracks_no_track_ID():
    xml_data = (
        "<data>"
        '   <Track name="blob">'
        '       <Edge SPOT_SOURCE_ID="11" SPOT_TARGET_ID="12"'
        '           x="10" y="20" />'
        '       <Edge SPOT_SOURCE_ID="12" SPOT_TARGET_ID="13"'
        '           x="30" y="30" />'
        "   </Track>"
        '   <Track name="blub">'
        '       <Edge SPOT_SOURCE_ID="21" SPOT_TARGET_ID="22"'
        '           x="15" y="25" />'
        "   </Track>"
        "</data>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    edge_feats = {
        "x": Feature("", "", "", "edge", "CellLineage", data_type="float"),
        "y": Feature("", "", "", "edge", "CellLineage", data_type="int"),
        "SPOT_SOURCE_ID": Feature("", "", "", "edge", "CellLineage", data_type="int"),
        "SPOT_TARGET_ID": Feature("", "", "", "edge", "CellLineage", data_type="int"),
    }

    obtained = nx.DiGraph()
    feat_decl = FeaturesDeclaration(edge_feats)

    with pytest.raises(KeyError):
        tml._build_tracks(it, element, feat_decl, obtained)


# _get_filtered_tracks_ID #####################################################


def test_get_filtered_tracks_ID():
    xml_data = '<data>   <TrackID TRACK_ID="0" />   <TrackID TRACK_ID="1" /></data>'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained_ID = tml._get_filtered_tracks_ID(it, element)
    expected_ID = [0, 1]
    assert obtained_ID.sort() == expected_ID.sort()


def test_get_filtered_tracks_ID_no_ID():
    xml_data = "<data>   <TrackID />   <TrackID /></data>"
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    obtained_ID = tml._get_filtered_tracks_ID(it, element)
    assert not obtained_ID


def test_get_filtered_tracks_ID_no_tracks():
    xml_data = "<data>   <tag />   <tag /></data>"
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    obtained_ID = tml._get_filtered_tracks_ID(it, element)
    assert not obtained_ID


# _update_node_feature_key ####################################################


def test_update_node_feature_key():
    lineage = CellLineage()
    old_key_values = ["value1", "value2", "value3"]
    lineage.add_node(1, old_key=old_key_values[0])
    lineage.add_node(2, old_key=old_key_values[1])
    lineage.add_node(3, old_key=old_key_values[2])

    tml._update_node_feature_key(lineage, "old_key", "new_key")

    for i, node in enumerate(lineage.nodes):
        assert "new_key" in lineage.nodes[node]
        assert "old_key" not in lineage.nodes[node]
        assert lineage.nodes[node]["new_key"] == old_key_values[i]


# _update_TRACK_ID ############################################################


def test_update_TRACK_ID():
    lineage = CellLineage()
    lineage.add_node(1)
    lineage.graph["TRACK_ID"] = 10
    tml._update_TRACK_ID(lineage)
    assert "lineage_ID" in lineage.graph
    assert lineage.graph["lineage_ID"] == 10
    assert "lineage_ID" not in lineage.nodes[1]


def test_update_TRACK_ID_no_TRACK_ID():
    lineage = CellLineage()
    lineage.add_node(1)
    tml._update_TRACK_ID(lineage)
    assert "lineage_ID" in lineage.graph
    assert lineage.graph["lineage_ID"] == -1


def test_update_TRACK_ID_several_subgraphs():
    lineage = CellLineage()
    lineage.add_node(1)
    lineage.add_node(2)

    with pytest.raises(AssertionError):
        tml._update_TRACK_ID(lineage)


# _update_location_related_features ###########################################


def test_update_location_related_features():
    lineage = CellLineage()
    lineage.add_node(1, POSITION_X=1, POSITION_Y=2, POSITION_Z=3)
    lineage.add_node(2, POSITION_X=4, POSITION_Y=5, POSITION_Z=6)
    lineage.add_edge(1, 2, EDGE_X_LOCATION=7, EDGE_Y_LOCATION=8, EDGE_Z_LOCATION=9)
    lineage.graph["TRACK_X_LOCATION"] = 10
    lineage.graph["TRACK_Y_LOCATION"] = 11
    lineage.graph["TRACK_Z_LOCATION"] = 12

    tml._update_location_related_features(lineage)

    assert lineage.nodes[1]["cell_x"] == 1
    assert lineage.nodes[1]["cell_y"] == 2
    assert lineage.nodes[1]["cell_z"] == 3
    assert lineage.nodes[2]["cell_x"] == 4
    assert lineage.nodes[2]["cell_y"] == 5
    assert lineage.nodes[2]["cell_z"] == 6
    assert lineage.edges[(1, 2)]["link_x"] == 7
    assert lineage.edges[(1, 2)]["link_y"] == 8
    assert lineage.edges[(1, 2)]["link_z"] == 9
    assert lineage.graph["lineage_x"] == 10
    assert lineage.graph["lineage_y"] == 11
    assert lineage.graph["lineage_z"] == 12


def test_update_location_related_features_one_node():
    lineage = CellLineage()
    lineage.add_node(1, POSITION_X=1, POSITION_Y=2, POSITION_Z=3)

    tml._update_location_related_features(lineage)

    assert lineage.nodes[1]["cell_x"] == 1
    assert lineage.nodes[1]["cell_y"] == 2
    assert lineage.nodes[1]["cell_z"] == 3


# _get_specific_tags ##########################################################


def test_get_specific_tags():
    xml_path = "sample_data/FakeTracks.xml"
    tag_names = ["GUIState", "FeaturePenalties"]
    obtained = tml._get_specific_tags(xml_path, tag_names)

    expected = {
        "GUIState": ET.Element("GUIState", attrib={"state": "ConfigureViews"}),
        "FeaturePenalties": ET.Element("FeaturePenalties"),  # empty tag
    }

    assert obtained.keys() == expected.keys()
    for k in obtained:
        assert k in expected
        assert obtained[k].tag == expected[k].tag
        assert obtained[k].attrib == expected[k].attrib


# _get_trackmate_version ######################################################


def test_get_trackmate_version():
    xml_path = "sample_data/FakeTracks.xml"
    obtained = tml._get_trackmate_version(xml_path)

    assert obtained == "8.0.0-SNAPSHOT-f411154ed1a4b9de350bbfe91c230cf3ae7639a3"


# _get_time_step ##############################################################


def test_get_time_step():
    settings = ET.Element("Settings")
    ET.SubElement(settings, "ImageData", timeinterval="0.5")
    obtained = tml._get_time_step(settings)
    expected = 0.5
    assert obtained == expected


def test_get_time_step_missing_timeinterval():
    settings = ET.Element("Settings")
    ET.SubElement(settings, "ImageData")
    with pytest.raises(KeyError, match="The 'timeinterval' attribute is missing"):
        tml._get_time_step(settings)


def test_get_time_step_invalid_timeinterval():
    settings = ET.Element("Settings")
    ET.SubElement(settings, "ImageData", timeinterval="invalid")
    with pytest.raises(
        ValueError, match="The 'timeinterval' attribute cannot be converted to float"
    ):
        tml._get_time_step(settings)


def test_get_time_step_missing_image_data():
    settings = ET.Element("Settings")
    with pytest.raises(KeyError, match="The 'ImageData' element is not found"):
        tml._get_time_step(settings)


# _get_pixel_size #############################################################


def test_get_pixel_size():
    settings = ET.Element("Settings")
    image_data = ET.SubElement(settings, "ImageData")
    image_data.attrib["pixelwidth"] = "1.5"
    image_data.attrib["pixelheight"] = "2.0"
    image_data.attrib["voxeldepth"] = "0.5"

    obtained = tml._get_pixel_size(settings)

    expected = {"width": 1.5, "height": 2.0, "depth": 0.5}

    assert obtained == expected


def test_get_pixel_size_missing_attribute():
    settings = ET.Element("Settings")
    image_data = ET.SubElement(settings, "ImageData")
    image_data.attrib["pixelwidth"] = "1.5"
    image_data.attrib["pixelheight"] = "2.0"

    with pytest.raises(KeyError, match="The voxeldepth attribute is missing"):
        tml._get_pixel_size(settings)


def test_get_pixel_size_invalid_attribute():
    settings = ET.Element("Settings")
    image_data = ET.SubElement(settings, "ImageData")
    image_data.attrib["pixelwidth"] = "1.5"
    image_data.attrib["pixelheight"] = "2.0"
    image_data.attrib["voxeldepth"] = "invalid"

    with pytest.raises(
        ValueError, match="The voxeldepth attribute cannot be converted to float."
    ):
        tml._get_pixel_size(settings)


def test_get_pixel_size_missing_image_data():
    settings = ET.Element("Settings")

    with pytest.raises(
        KeyError, match="The 'ImageData' element is not found in the settings."
    ):
        tml._get_pixel_size(settings)
