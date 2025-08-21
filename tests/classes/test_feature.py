#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for Feature and FeaturesDeclaration classes from feature.py module."""

import pytest

from pycellin.classes import Feature, FeaturesDeclaration


# Class Feature ###############################################################


@pytest.fixture()
def feat1():
    return Feature(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        feat_type="node",
        lin_type="CellLineage",
        dtype="type1",
        unit="unit1",
    )


@pytest.fixture()
def feat1_bis():
    return Feature(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        feat_type="node",
        lin_type="CellLineage",
        dtype="type1",
        unit="unit1",
    )


@pytest.fixture()
def feat2():
    return Feature(
        identifier="name2",
        name="name2",
        description="desc2",
        provenance="prov2",
        feat_type="node",
        lin_type="CellLineage",
        dtype="type2",
        unit="unit2",
    )


@pytest.fixture()
def feat3():
    return Feature(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        feat_type="node",
        lin_type="CellLineage",
        dtype="type1",
    )


@pytest.fixture()
def feat4():
    return Feature(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        feat_type="edge",
        lin_type="CellLineage",
        dtype="type1",
        unit="unit1",
    )


# __eq__() ####################################################################


def test_feature_equality(feat1, feat1_bis):
    assert feat1 == feat1_bis


def test_feature_unequality(feat1, feat2, feat3):
    assert feat1 != feat2
    assert feat1 != feat3
    assert feat1 != "not a feature"


def test_feature_invalid_Literal():
    with pytest.raises(ValueError):
        Feature(
            identifier="name1",
            name="name1",
            description="desc1",
            provenance="prov1",
            feat_type="node",
            lin_type="not a valid Literal",
            dtype="type1",
        )


# _change_name() ##############################################################


def test_change_name(feat1):
    feat1._change_name("new_name")
    assert feat1.name == "new_name"


def test_change_name_ValueError(feat1):
    feat1 = Feature(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        feat_type="node",
        lin_type="CellLineage",
        dtype="type1",
        unit="unit1",
    )
    with pytest.raises(ValueError):
        feat1._change_name(42)


# _change_description() #######################################################


def test_change_description(feat1):
    feat1._change_description("new_desc")
    assert feat1.description == "new_desc"


def test_change_description_ValueError(feat1):
    with pytest.raises(ValueError):
        feat1._change_description(42)


# _change_provenance() ########################################################


def test_change_provenance(feat1):
    feat1._change_provenance("new_prov")
    assert feat1.provenance == "new_prov"


def test_change_provenance_ValueError(feat1):
    with pytest.raises(ValueError):
        feat1._change_provenance(42)


# is_equal() ##################################################################


def test_feature_is_equal(feat1, feat1_bis, feat2, feat3):
    assert feat1.is_equal(feat1_bis)
    assert not feat1.is_equal(feat2)
    assert not feat1.is_equal(feat3)
    assert feat1.is_equal("not a feature") == NotImplemented


def test_feature_is_equal_ignore_feat_type(feat1, feat3, feat4):
    assert feat1.is_equal(feat4, ignore_feat_type=True)
    assert not feat1.is_equal(feat4, ignore_feat_type=False)
    assert not feat1.is_equal(feat3, ignore_feat_type=True)
    assert feat1.is_equal("not a feature", ignore_feat_type=True) == NotImplemented


# Class FeaturesDeclaration ###################################################


@pytest.fixture()
def fd1():
    return FeaturesDeclaration(1)


@pytest.fixture()
def fd1_bis():
    return FeaturesDeclaration(1)


@pytest.fixture()
def fd2():
    return FeaturesDeclaration({})


@pytest.fixture()
def fd2_bis():
    return FeaturesDeclaration({})


@pytest.fixture()
def fd3():
    return FeaturesDeclaration(2)


@pytest.fixture()
def fd4():
    return FeaturesDeclaration({"a": "a"})


# __eq__() ####################################################################


def test_features_declaration_equality(feat1, feat1_bis, fd1, fd1_bis, fd2, fd2_bis):
    fd = FeaturesDeclaration({"feat1": feat1})
    fd_bis = FeaturesDeclaration({"feat1": feat1_bis})
    assert fd == fd_bis
    assert fd1 == fd1_bis
    assert fd2 == fd2_bis


def test_features_declaration_inequality(fd1, fd2, fd3, fd4):
    assert fd1 != fd2
    assert fd1 != fd3
    assert fd1 != fd4
    assert fd1 != "not a FeaturesDeclaration"
