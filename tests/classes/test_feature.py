#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for Feature and FeaturesDeclaration classes from feature.py module.
"""

import pytest

from pycellin.classes import Feature, FeaturesDeclaration


# Class Feature ###############################################################


@pytest.fixture(scope="module")
def feat1():
    return Feature("name1", "desc1", "prov1", "node", "CellLineage", "type1", "unit1")


@pytest.fixture(scope="module")
def feat1_bis():
    return Feature("name1", "desc1", "prov1", "node", "CellLineage", "type1", "unit1")


@pytest.fixture(scope="module")
def feat2():
    return Feature("name2", "desc2", "prov2", "node", "CellLineage", "type2", "unit2")


@pytest.fixture(scope="module")
def feat3():
    return Feature("name1", "desc1", "prov1", "node", "CellLineage", "type1")


def test_feature_equality(feat1, feat1_bis):
    assert feat1 == feat1_bis


def test_feature_unequality(feat1, feat2, feat3):
    assert feat1 != feat2
    assert feat1 != feat3
    assert feat1 != "not a feature"


def test_feature_invalid_Literal():
    with pytest.raises(ValueError):
        Feature("name1", "desc1", "prov1", "node", "not a valid Literal", "type1")


# Class FeaturesDeclaration ###################################################


@pytest.fixture(scope="module")
def fd1():
    return FeaturesDeclaration(1)


@pytest.fixture(scope="module")
def fd1_bis():
    return FeaturesDeclaration(1)


@pytest.fixture(scope="module")
def fd2():
    return FeaturesDeclaration({})


@pytest.fixture(scope="module")
def fd2_bis():
    return FeaturesDeclaration({})


@pytest.fixture(scope="module")
def fd3():
    return FeaturesDeclaration(2)


@pytest.fixture(scope="module")
def fd4():
    return FeaturesDeclaration({"a": "a"})


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
