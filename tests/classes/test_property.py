#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for Property and PropsMetadata classes from property.py module."""

import pytest

from pycellin.classes import Property, PropsMetadata


# Class Property ###############################################################


@pytest.fixture()
def prop1():
    return Property(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        prop_type="node",
        lin_type="CellLineage",
        dtype="type1",
        unit="unit1",
    )


@pytest.fixture()
def prop1_bis():
    return Property(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        prop_type="node",
        lin_type="CellLineage",
        dtype="type1",
        unit="unit1",
    )


@pytest.fixture()
def prop2():
    return Property(
        identifier="name2",
        name="name2",
        description="desc2",
        provenance="prov2",
        prop_type="node",
        lin_type="CellLineage",
        dtype="type2",
        unit="unit2",
    )


@pytest.fixture()
def prop3():
    return Property(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        prop_type="node",
        lin_type="CellLineage",
        dtype="type1",
    )


@pytest.fixture()
def prop4():
    return Property(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="type1",
        unit="unit1",
    )


# __eq__() ####################################################################


def test_prop_equality(prop1, prop1_bis):
    assert prop1 == prop1_bis


def test_prop_unequality(prop1, prop2, prop3):
    assert prop1 != prop2
    assert prop1 != prop3
    assert prop1 != "not a property"


def test_prop_invalid_Literal():
    with pytest.raises(ValueError):
        Property(
            identifier="name1",
            name="name1",
            description="desc1",
            provenance="prov1",
            prop_type="node",
            lin_type="not a valid Literal",
            dtype="type1",
        )


# _change_name() ##############################################################


def test_change_name(prop1):
    prop1._change_name("new_name")
    assert prop1.name == "new_name"


def test_change_name_ValueError(prop1):
    prop1 = Property(
        identifier="name1",
        name="name1",
        description="desc1",
        provenance="prov1",
        prop_type="node",
        lin_type="CellLineage",
        dtype="type1",
        unit="unit1",
    )
    with pytest.raises(ValueError):
        prop1._change_name(42)


# _change_description() #######################################################


def test_change_description(prop1):
    prop1._change_description("new_desc")
    assert prop1.description == "new_desc"


def test_change_description_ValueError(prop1):
    with pytest.raises(ValueError):
        prop1._change_description(42)


# _change_provenance() ########################################################


def test_change_provenance(prop1):
    prop1._change_provenance("new_prov")
    assert prop1.provenance == "new_prov"


def test_change_provenance_ValueError(prop1):
    with pytest.raises(ValueError):
        prop1._change_provenance(42)


# is_equal() ##################################################################


def test_prop_is_equal(prop1, prop1_bis, prop2, prop3):
    assert prop1.is_equal(prop1_bis)
    assert not prop1.is_equal(prop2)
    assert not prop1.is_equal(prop3)
    assert prop1.is_equal("not a property") == NotImplemented


def test_prop_is_equal_ignore_prop_type(prop1, prop3, prop4):
    assert prop1.is_equal(prop4, ignore_prop_type=True)
    assert not prop1.is_equal(prop4, ignore_prop_type=False)
    assert not prop1.is_equal(prop3, ignore_prop_type=True)
    assert prop1.is_equal("not a property", ignore_prop_type=True) == NotImplemented


# Class PropsMetadata ###################################################


@pytest.fixture()
def pmd1():
    return PropsMetadata(1)


@pytest.fixture()
def pmd1_bis():
    return PropsMetadata(1)


@pytest.fixture()
def pmd2():
    return PropsMetadata({})


@pytest.fixture()
def pmd2_bis():
    return PropsMetadata({})


@pytest.fixture()
def pmd3():
    return PropsMetadata(2)


@pytest.fixture()
def pmd4():
    return PropsMetadata({"a": "a"})


# __eq__() ####################################################################


def test_props_md_equality(prop1, prop1_bis, pmd1, pmd1_bis, pmd2, pmd2_bis):
    pmd = PropsMetadata({"prop1": prop1})
    pmd_bis = PropsMetadata({"prop1": prop1_bis})
    assert pmd == pmd_bis
    assert pmd1 == pmd1_bis
    assert pmd2 == pmd2_bis


def test_props_md_inequality(pmd1, pmd2, pmd3, pmd4):
    assert pmd1 != pmd2
    assert pmd1 != pmd3
    assert pmd1 != pmd4
    assert pmd1 != "not a PropsMetadata"
