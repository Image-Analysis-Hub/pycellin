#!/usr/bin/env python3

"""Unit test for TrackMate XML file loader."""

import io
from copy import deepcopy
from typing import Any

import networkx as nx
import pytest
from lxml import etree as ET

import pycellin.io.trackmate.loader as tml
from pycellin.classes import CellLineage, Property, PropsMetadata
from pycellin.utils import is_equal


# Fixtures #####################################################################


@pytest.fixture(scope="module")
def units():
    return {"timeunits": "s", "spatialunits": "um"}


@pytest.fixture(scope="module")
def prop_QUALITY():
    return Property(
        identifier="QUALITY",
        name="Quality",
        description="Quality",
        provenance="TrackMate",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
    )


@pytest.fixture(scope="module")
def prop_FRAME():
    return Property(
        identifier="FRAME",
        name="Frame",
        description="Frame",
        provenance="TrackMate",
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
    )


@pytest.fixture(scope="module")
def prop_spot_name():
    return Property(
        identifier="cell_name",
        name="cell name",
        description="Name of the spot",
        provenance="TrackMate",
        prop_type="node",
        lin_type="CellLineage",
        dtype="string",
    )


@pytest.fixture(scope="module")
def spot_props(prop_QUALITY: Property, prop_FRAME: Property, prop_spot_name: Property):
    return {
        "QUALITY": prop_QUALITY,
        "FRAME": prop_FRAME,
        "cell_name": prop_spot_name,
    }


@pytest.fixture(scope="module")
def prop_SPOT_SOURCE_ID():
    return Property(
        identifier="SPOT_SOURCE_ID",
        name="Source spot ID",
        description="Source spot ID",
        provenance="TrackMate",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="int",
    )


@pytest.fixture(scope="module")
def prop_SPOT_TARGET_ID():
    return Property(
        identifier="SPOT_TARGET_ID",
        name="Target spot ID",
        description="Target spot ID",
        provenance="TrackMate",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="int",
    )


@pytest.fixture(scope="module")
def edge_props(prop_SPOT_SOURCE_ID: Property, prop_SPOT_TARGET_ID: Property):
    return {
        "SPOT_SOURCE_ID": prop_SPOT_SOURCE_ID,
        "SPOT_TARGET_ID": prop_SPOT_TARGET_ID,
    }


@pytest.fixture(scope="module")
def prop_TRACK_INDEX():
    return Property(
        identifier="TRACK_INDEX",
        name="Track index",
        description="Track index",
        provenance="TrackMate",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="int",
    )


@pytest.fixture(scope="module")
def prop_NUMBER_SPOTS():
    return Property(
        identifier="NUMBER_SPOTS",
        name="Number of spots",
        description="Number of spots",
        provenance="TrackMate",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="int",
    )


@pytest.fixture(scope="module")
def prop_track_name():
    return Property(
        identifier="lineage_name",
        name="lineage name",
        description="Name of the track",
        provenance="TrackMate",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="string",
    )


@pytest.fixture(scope="module")
def track_props(prop_TRACK_INDEX: Property, prop_NUMBER_SPOTS: Property, prop_track_name: Property):
    return {
        "TRACK_INDEX": prop_TRACK_INDEX,
        "NUMBER_SPOTS": prop_NUMBER_SPOTS,
        "lineage_name": prop_track_name,
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


# _get_props_dict ##########################################################


def test_get_props_dict():
    xml_data = (
        "<SpotFeatures>"
        '   <Feature feature="QUALITY" isint="false" />'
        '   <Feature feature="FRAME" isint="true" />'
        "</SpotFeatures>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    props = tml._get_props_dict(it, element)
    spot_features = [
        {"feature": "QUALITY", "isint": "false"},
        {"feature": "FRAME", "isint": "true"},
    ]
    assert props == spot_features


def test_get_props_dict_no_feature_tag():
    xml_data = "<SpotFeatures></SpotFeatures>"
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    props = tml._get_props_dict(it, element)
    assert props == []


def test_get_props_dict_other_tag():
    xml_data = (
        "<SpotFeatures>"
        '   <Feature feature="QUALITY" isint="false" />'
        '   <Other feature="FRAME" isint="true" />'
        "</SpotFeatures>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    props = tml._get_props_dict(it, element)
    spot_features = [{"feature": "QUALITY", "isint": "false"}]
    assert props == spot_features


# _convert_and_add_prop ####################################################


def test_convert_and_add_prop_spot_feature(units: dict[str, str], prop_QUALITY: Property):
    trackmate_feature = {
        "feature": "QUALITY",
        "name": "Quality",
        "isint": "false",
        "dimension": "NONE",
    }
    feature_type = "SpotFeatures"
    obtained = PropsMetadata()
    tml._convert_and_add_prop(trackmate_feature, feature_type, obtained, units)

    expected = PropsMetadata({"QUALITY": prop_QUALITY})

    assert obtained == expected


def test_convert_and_add_prop_edge_feature(units: dict[str, str], prop_SPOT_SOURCE_ID: Property):
    trackmate_feature = {
        "feature": "SPOT_SOURCE_ID",
        "name": "Source spot ID",
        "isint": "true",
        "dimension": "NONE",
    }
    feature_type = "EdgeFeatures"
    obtained = PropsMetadata()
    tml._convert_and_add_prop(trackmate_feature, feature_type, obtained, units)

    expected = PropsMetadata({"SPOT_SOURCE_ID": prop_SPOT_SOURCE_ID})

    assert obtained == expected


def test_convert_and_add_prop_track_feature(units: dict[str, str], prop_TRACK_INDEX: Property):
    trackmate_feature = {
        "feature": "TRACK_INDEX",
        "name": "Track index",
        "isint": "true",
        "dimension": "NONE",
    }
    feature_type = "TrackFeatures"
    obtained = PropsMetadata()
    tml._convert_and_add_prop(trackmate_feature, feature_type, obtained, units)

    expected = PropsMetadata({"TRACK_INDEX": prop_TRACK_INDEX})

    assert obtained == expected


def test_convert_and_add_prop_invalid_feature_type(units: dict[str, str]):
    trackmate_feature = {
        "feature": "QUALITY",
        "name": "Quality",
        "isint": "false",
        "dimension": "NONE",
    }
    feature_type = "InvalidFeatureType"
    props_md = PropsMetadata()

    with pytest.raises(ValueError, match="Invalid property type: InvalidFeatureType"):
        tml._convert_and_add_prop(trackmate_feature, feature_type, props_md, units)


# _add_all_props ###########################################################


def test_add_all_props(
    spot_props: dict[str, Any], edge_props: dict[str, Any], track_props: dict[str, Any]
):
    xml_data = (
        "<FeatureDeclarations>"
        "   <SpotFeatures>"
        '       <Feature feature="QUALITY" name="Quality" isint="false" dimension="NONE"/>'
        '       <Feature feature="FRAME" name="Frame" isint="true" dimension="NONE"/>'
        "   </SpotFeatures>"
        "   <EdgeFeatures>"
        '       <Feature feature="SPOT_SOURCE_ID" name="Source spot ID" isint="true" '
        '                dimension="NONE"/>'
        '       <Feature feature="SPOT_TARGET_ID" name="Target spot ID" isint="true" '
        '                dimension="NONE"/>'
        "   </EdgeFeatures>"
        "   <TrackFeatures>"
        '       <Feature feature="TRACK_INDEX" name="Track index" isint="true" dimension="NONE"/>'
        '       <Feature feature="NUMBER_SPOTS" name="Number of spots" isint="true" '
        '                dimension="NONE"/>'
        "   </TrackFeatures>"
        "</FeatureDeclarations>"
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = PropsMetadata()
    tml._add_all_props(it, element, obtained, {})

    expected = PropsMetadata({**spot_props, **edge_props, **track_props})

    assert obtained == expected


def test_add_all_props_empty():
    xml_data = "<FeatureDeclarations></FeatureDeclarations>"
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = PropsMetadata()
    tml._add_all_props(it, element, obtained, {})

    assert obtained == PropsMetadata()


def test_add_all_props_tag_with_no_feature_tag(
    spot_props: dict[str, Any], track_props: dict[str, Any]
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

    obtained = PropsMetadata()
    tml._add_all_props(it, element, obtained, {})

    expected = PropsMetadata({**spot_props, **track_props})

    assert obtained == expected


# _convert_attributes #########################################################


def test_convert_attributes():
    props = {
        "prop_float": Property(
            identifier="prop_float",
            name="",
            description="",
            provenance="",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
        ),
        "prop_int": Property(
            identifier="prop_int",
            name="",
            description="",
            provenance="",
            prop_type="node",
            lin_type="CellLineage",
            dtype="int",
        ),
        "prop_neg": Property(
            identifier="prop_neg",
            name="",
            description="",
            provenance="",
            prop_type="node",
            lin_type="CellLineage",
            dtype="int",
        ),
        "prop_string": Property(
            identifier="prop_string",
            name="",
            description="",
            provenance="",
            prop_type="node",
            lin_type="CellLineage",
            dtype="string",
        ),
    }

    obtained_attr = {
        "prop_float": "30",
        "prop_int": "20",
        "prop_neg": "-10",
        "prop_string": "nope",
    }
    tml._convert_attributes(obtained_attr, props, "node")

    expected_attr = {
        "prop_float": 30.0,
        "prop_int": 20,
        "prop_neg": -10.0,
        "prop_string": "nope",
    }

    assert obtained_attr == expected_attr


def test_convert_attributes_specific_keys():
    props = {}

    obtained_attr = {"ID": "42", "name": "ID42", "ROI_N_POINTS": "something here"}
    tml._convert_attributes(obtained_attr, props, "node")

    expected_attr = {"ID": 42, "name": "ID42", "ROI_N_POINTS": "something here"}

    assert obtained_attr == expected_attr


def test_convert_attributes_ValueError():
    props = {
        "prop_int": Property(
            identifier="prop_int",
            name="",
            description="",
            provenance="",
            prop_type="node",
            lin_type="CellLineage",
            dtype="integer",
        )
    }
    attributes = {"prop_int": "20"}

    with pytest.raises(ValueError):
        tml._convert_attributes(attributes, props, "node")


def test_convert_attributes_missing_prop():
    props = {
        "prop_float": Property(
            identifier="prop_float",
            name="",
            description="",
            provenance="",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
        ),
    }
    attributes = {"prop_float": "30", "prop_int": "20"}

    with pytest.warns(UserWarning):
        tml._convert_attributes(attributes, props, "node")
    assert props["prop_int"].identifier == "prop_int"
    assert props["prop_int"].name == "prop_int"
    assert props["prop_int"].description == "unknown"
    assert props["prop_int"].provenance == "unknown"
    assert props["prop_int"].prop_type == "node"
    assert props["prop_int"].lin_type == "CellLineage"
    assert props["prop_int"].dtype == "unknown"
    assert props["prop_int"].unit == "unknown"


# _convert_ROI_coordinates ####################################################


def test_convert_ROI_coordinates_2D():
    el_obtained = ET.Element("Spot")
    el_obtained.attrib["ROI_N_POINTS"] = "3"
    el_obtained.text = "1 2.0 -3 -4.0 5.5 6"
    att_obtained = deepcopy(el_obtained.attrib)
    tml._convert_ROI_coordinates(el_obtained, att_obtained)

    att_expected = {"ROI_coords": [(1.0, 2.0), (-3.0, -4.0), (5.5, 6.0)]}

    assert att_obtained == att_expected


def test_convert_ROI_coordinates_3D():
    el_obtained = ET.Element("Spot")
    el_obtained.attrib["ROI_N_POINTS"] = "2"
    el_obtained.text = "1 2.0 -3 -4.0 5.5 6"
    att_obtained = deepcopy(el_obtained.attrib)
    tml._convert_ROI_coordinates(el_obtained, att_obtained)

    att_expected = {"ROI_coords": [(1.0, 2.0, -3.0), (-4.0, 5.5, 6.0)]}

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

    att_expected = {"ROI_coords": None}

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

    spot_props = {
        "x": Property(
            identifier="x",
            name="",
            description="",
            provenance="",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
        ),
        "y": Property(
            identifier="y",
            name="",
            description="",
            provenance="",
            prop_type="node",
            lin_type="CellLineage",
            dtype="int",
        ),
    }
    props_md = PropsMetadata(spot_props)
    obtained = nx.DiGraph()
    tml._add_all_nodes(it, element, props_md, obtained)

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
        '<data>   <frame>       <Spot ID="1000" />       <Spot ID="1001" />   </frame></data>'
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = nx.DiGraph()
    tml._add_all_nodes(it, element, PropsMetadata(), obtained)

    expected = nx.DiGraph()
    expected.add_nodes_from([(1001, {"ID": 1001}), (1000, {"ID": 1000})])

    assert is_equal(obtained, expected)


def test_add_all_nodes_no_node_attributes():
    xml_data = '<data>   <frame>       <Spot />       <Spot ID="1001" />   </frame></data>'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = nx.DiGraph()
    tml._add_all_nodes(it, element, PropsMetadata(), obtained)

    expected = nx.DiGraph()
    expected.add_nodes_from([(1001, {"ID": 1001})])

    assert is_equal(obtained, expected)


def test_add_all_nodes_no_nodes():
    xml_data = "<data>   <frame /></data>"
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)

    obtained = nx.DiGraph()
    tml._add_all_nodes(it, element, PropsMetadata(), obtained)

    assert is_equal(obtained, nx.DiGraph())


# _add_edge ###################################################################


def test_add_edge():
    xml_data = '<data SPOT_SOURCE_ID="1" SPOT_TARGET_ID="2" x="20" y="25" />'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    track_id = 0

    edge_props = {
        "x": Property(
            identifier="x",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="float",
        ),
        "y": Property(
            identifier="y",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
        "SPOT_SOURCE_ID": Property(
            identifier="SPOT_SOURCE_ID",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
        "SPOT_TARGET_ID": Property(
            identifier="SPOT_TARGET_ID",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
    }
    obtained = nx.DiGraph()
    props_md = PropsMetadata(edge_props)
    tml._add_edge(element, props_md, obtained, track_id)

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

    edge_props = {
        "x": Property(
            identifier="x",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="float",
        ),
        "y": Property(
            identifier="y",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
        "SPOT_SOURCE_ID": Property(
            identifier="SPOT_SOURCE_ID",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
    }
    obtained = nx.DiGraph()
    props_md = PropsMetadata(edge_props)
    tml._add_edge(element, props_md, obtained, track_id)

    expected = nx.DiGraph()

    assert is_equal(obtained, expected)


def test_add_edge_no_edge_attributes():
    xml_data = '<data SPOT_SOURCE_ID="1" SPOT_TARGET_ID="2" />'
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    track_id = 0

    edge_props = {
        "SPOT_SOURCE_ID": Property(
            identifier="SPOT_SOURCE_ID",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
        "SPOT_TARGET_ID": Property(
            identifier="SPOT_TARGET_ID",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
    }
    obtained = nx.DiGraph()
    props_md = PropsMetadata(edge_props)
    tml._add_edge(element, props_md, obtained, track_id)

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
    edge_props = {
        "x": Property(
            identifier="x",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="float",
        ),
        "y": Property(
            identifier="y",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
        "SPOT_SOURCE_ID": Property(
            identifier="SPOT_SOURCE_ID",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
        "SPOT_TARGET_ID": Property(
            identifier="SPOT_TARGET_ID",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
    }
    track_props = {
        "TRACK_ID": Property(
            identifier="TRACK_ID",
            name="",
            description="",
            provenance="",
            prop_type="lineage",
            lin_type="CellLineage",
            dtype="int",
        )
    }

    obtained = nx.DiGraph()
    props_md = PropsMetadata({**edge_props, **track_props})
    obtained_tracks_attrib = tml._build_tracks(it, element, props_md, obtained)
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
    edge_props = {
        "x": Property(
            identifier="x",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="float",
        ),
        "y": Property(
            identifier="y",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
    }
    track_props = {
        "TRACK_ID": Property(
            identifier="TRACK_ID",
            name="",
            description="",
            provenance="",
            prop_type="lineage",
            lin_type="CellLineage",
            dtype="int",
        )
    }

    obtained = nx.DiGraph()
    props_md = PropsMetadata({**edge_props, **track_props})
    obtained_tracks_attrib = tml._build_tracks(it, element, props_md, obtained)
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
        '<data>   <Track TRACK_ID="1" name="blob" />   <Track TRACK_ID="2" name="blub" /></data>'
    )
    it = ET.iterparse(io.BytesIO(xml_data.encode("utf-8")), events=["start", "end"])
    _, element = next(it)
    track_props = {
        "TRACK_ID": Property(
            identifier="TRACK_ID",
            name="",
            description="",
            provenance="",
            prop_type="lineage",
            lin_type="CellLineage",
            dtype="int",
        )
    }

    obtained = nx.DiGraph()
    props_md = PropsMetadata(track_props)
    obtained_tracks_attrib = tml._build_tracks(it, element, props_md, obtained)
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
    edge_props = {
        "x": Property(
            identifier="x",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="float",
        ),
        "y": Property(
            identifier="y",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
        "SPOT_SOURCE_ID": Property(
            identifier="SPOT_SOURCE_ID",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
        "SPOT_TARGET_ID": Property(
            identifier="SPOT_TARGET_ID",
            name="",
            description="",
            provenance="",
            prop_type="edge",
            lin_type="CellLineage",
            dtype="int",
        ),
    }

    obtained = nx.DiGraph()
    props_md = PropsMetadata(edge_props)

    with pytest.raises(KeyError):
        tml._build_tracks(it, element, props_md, obtained)


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


# _update_location_related_props ###########################################


def test_update_location_related_props():
    lineage = CellLineage()
    lineage.add_node(1, POSITION_X=1, POSITION_Y=2, POSITION_Z=3)
    lineage.add_node(2, POSITION_X=4, POSITION_Y=5, POSITION_Z=6)
    lineage.add_edge(1, 2, EDGE_X_LOCATION=7, EDGE_Y_LOCATION=8, EDGE_Z_LOCATION=9)
    lineage.graph["TRACK_X_LOCATION"] = 10
    lineage.graph["TRACK_Y_LOCATION"] = 11
    lineage.graph["TRACK_Z_LOCATION"] = 12

    tml._update_location_related_props(lineage)

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


def test_update_location_related_props_one_node():
    lineage = CellLineage()
    lineage.add_node(1, POSITION_X=1, POSITION_Y=2, POSITION_Z=3)

    tml._update_location_related_props(lineage)

    assert lineage.nodes[1]["cell_x"] == 1
    assert lineage.nodes[1]["cell_y"] == 2
    assert lineage.nodes[1]["cell_z"] == 3


# _get_specific_tags ##########################################################


def test_get_specific_tags():
    xml_path = "sample_data/FakeTracks.xml"
    tag_names = ["GUIState", "FeaturePenalties", "FilteredTracks"]
    obtained = tml._get_specific_tags(xml_path, tag_names)

    nested_element = ET.Element("FilteredTracks")
    nested_element.append(ET.Element("TrackID", attrib={"TRACK_ID": "0"}))
    nested_element.append(ET.Element("TrackID", attrib={"TRACK_ID": "4"}))
    expected = {
        "GUIState": ET.Element("GUIState", attrib={"state": "ConfigureViews"}),
        "FeaturePenalties": ET.Element("FeaturePenalties"),  # empty tag
        "FilteredTracks": nested_element,
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

    expected = {"pixel_width": 1.5, "pixel_height": 2.0, "pixel_depth": 0.5}

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

    with pytest.raises(ValueError, match="The voxeldepth attribute cannot be converted to float."):
        tml._get_pixel_size(settings)


def test_get_pixel_size_missing_image_data():
    settings = ET.Element("Settings")

    with pytest.raises(KeyError, match="The 'ImageData' element is not found in the settings."):
        tml._get_pixel_size(settings)
