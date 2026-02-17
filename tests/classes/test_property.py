#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for Property and PropsMetadata classes from property.py module."""

import pytest

from pycellin.classes import Property, PropsMetadata


# Property fixtures ###############################################################


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


# PropsMetadata fixtures #######


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


# Test classes ###############################################################

# Property tests


class TestPropertyEq:
    """Test cases for Property.__eq()__ method."""

    def test_equality(self, prop1, prop1_bis):
        """Test for Property equality."""
        assert prop1 == prop1_bis

    def test_unequality(self, prop1, prop2, prop3):
        """Test for Property inequality."""
        assert prop1 != prop2
        assert prop1 != prop3
        assert prop1 != "not a property"

    def test_invalid_Literal(self):
        """Test Property equality in the case of an invalid Literal for lin_type."""
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


class TestPropertyIsEqual:
    """Test cases for Property.is_equal() method."""

    def test_normal(self, prop1, prop1_bis, prop2, prop3):
        """Test normal behavior."""
        assert prop1.is_equal(prop1_bis)
        assert not prop1.is_equal(prop2)
        assert not prop1.is_equal(prop3)
        assert prop1.is_equal("not a property") == NotImplemented

    def test_ignore_prop_type(self, prop1, prop3, prop4):
        """Test with argument ignore_prop_type."""
        assert prop1.is_equal(prop4, ignore_prop_type=True)
        assert not prop1.is_equal(prop4, ignore_prop_type=False)
        assert not prop1.is_equal(prop3, ignore_prop_type=True)
        assert prop1.is_equal("not a property", ignore_prop_type=True) == NotImplemented


class TestPropertyChangeDescription:
    """Test cases for Property._change_description() method."""

    def test_normal(self, prop1):
        """Test normal behavior."""
        prop1._change_description("new_desc")
        assert prop1.description == "new_desc"

    # TODO: maybe it should be a TypeError instead?
    # Same for _change_name() above and _change_provenance() below
    def test_invalid__description_raises_error(self, prop1):
        """Test that invalid name raises ValueError."""
        with pytest.raises(ValueError):
            prop1._change_description(42)


class TestPropertyChangeName:
    """Test cases for Property._change_name() method."""

    def test_normal(self, prop1):
        """Test normal behavior."""
        prop1._change_name("new_name")
        assert prop1.name == "new_name"

    def test_invalid_name_raises_error(self, prop1):
        """Test that invalid name raises ValueError."""
        with pytest.raises(ValueError):
            prop1._change_name(42)


class TestPropertyChangeProvenance:
    """Test cases for Property._change_provenance() method."""

    def test_normal(self, prop1):
        """Test normal behavior."""
        prop1._change_provenance("new_prov")
        assert prop1.provenance == "new_prov"

    def test_invalid_provenance_raises_error(self, prop1):
        """Test that invalid name raises ValueError."""
        with pytest.raises(ValueError):
            prop1._change_provenance(42)


# PropsMetadata tests


class TestPropsMetadataEq:
    """Test cases for Property.is_equal() method."""

    def test_equality(self, prop1, prop1_bis, pmd1, pmd1_bis, pmd2, pmd2_bis):
        """Test PropsMetadata equality."""
        pmd = PropsMetadata({"prop1": prop1})
        pmd_bis = PropsMetadata({"prop1": prop1_bis})
        assert pmd == pmd_bis
        assert pmd1 == pmd1_bis
        assert pmd2 == pmd2_bis

    def test_inequality(self, pmd1, pmd2, pmd3, pmd4):
        """Test PropsMetadata equality."""
        assert pmd1 != pmd2
        assert pmd1 != pmd3
        assert pmd1 != pmd4
        assert pmd1 != "not a PropsMetadata"
