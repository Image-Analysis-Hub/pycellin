#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for Property class from property.py module."""

import pytest

from pycellin.classes import Property
from pycellin.custom_types import PropertyType


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


class TestPropertyConstructor:
    """Test cases for Property constructor."""

    def test_empty_property_type_raises_error(self):
        """Test that PropertyType with no flags cannot be used to create a Property."""
        empty_flag = PropertyType(0)
        with pytest.raises(
            ValueError, match="Property type must be a valid PropertyType Flag"
        ):
            Property(
                identifier="test",
                name="test",
                description="test",
                provenance="test",
                prop_type=empty_flag,
                lin_type="CellLineage",
                dtype="int",
            )


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
    def test_invalid_description_raises_error(self, prop1):
        """Test that invalid description raises ValueError."""
        with pytest.raises(ValueError):
            prop1._change_description(42)


class TestPropertyChangeIdentifier:
    """Test cases for Property._change_identifier() method."""

    def test_normal(self, prop1):
        """Test normal behavior."""
        prop1._change_identifier("new_id")
        assert prop1.identifier == "new_id"

    def test_invalid_identifier_raises_error(self, prop1):
        """Test that invalid identifier raises ValueError."""
        with pytest.raises(ValueError):
            prop1._change_identifier(42)


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
        """Test that invalid provenance raises ValueError."""
        with pytest.raises(ValueError):
            prop1._change_provenance(42)


class TestPropertyConstructorConversion:
    """Test cases for Property constructor with string/list conversion."""

    def test_constructor_with_string_prop_type(self):
        """Test constructor accepts string prop_type and converts it."""
        prop = Property(
            identifier="test",
            name="test",
            description="test",
            provenance="test",
            prop_type="node",
            lin_type="CellLineage",
            dtype="int",
        )
        assert prop.prop_type == PropertyType.NODE

    def test_constructor_with_list_prop_type_single(self):
        """Test constructor converts single-item list to PropertyType."""
        prop = Property(
            identifier="test",
            name="test",
            description="test",
            provenance="test",
            prop_type=["edge"],
            lin_type="CellLineage",
            dtype="int",
        )
        assert prop.prop_type == PropertyType.EDGE

    def test_constructor_with_list_prop_type_multi(self):
        """Test constructor converts multi-item list to combined PropertyType."""
        prop = Property(
            identifier="test",
            name="test",
            description="test",
            provenance="test",
            prop_type=["node", "edge"],
            lin_type="CellLineage",
            dtype="int",
        )
        assert prop.prop_type == (PropertyType.NODE | PropertyType.EDGE)

    def test_constructor_with_property_type_flag(self):
        """Test constructor accepts PropertyType Flag directly."""
        prop = Property(
            identifier="test",
            name="test",
            description="test",
            provenance="test",
            prop_type=PropertyType.LINEAGE,
            lin_type="CellLineage",
            dtype="int",
        )
        assert prop.prop_type == PropertyType.LINEAGE


class TestPropertyConstructorAttributes:
    """Test cases for Property constructor attribute assignment."""

    def test_all_attributes_assigned(self, prop1):
        """Test that all attributes are correctly assigned in constructor."""
        assert prop1.identifier == "name1"
        assert prop1.name == "name1"
        assert prop1.description == "desc1"
        assert prop1.provenance == "prov1"
        assert prop1.prop_type == PropertyType.NODE
        assert prop1.lin_type == "CellLineage"
        assert prop1.dtype == "type1"
        assert prop1.unit == "unit1"

    def test_unit_optional(self, prop3):
        """Test that unit parameter is optional and can be None."""
        assert prop3.unit is None

    def test_invalid_lineage_type(self):
        """Test that invalid lin_type raises ValueError."""
        with pytest.raises(ValueError, match="Lineage type must be one of"):
            Property(
                identifier="test",
                name="test",
                description="test",
                provenance="test",
                prop_type="node",
                lin_type="InvalidType",
                dtype="int",
            )

    def test_different_lineage_types(self):
        """Test constructor with different valid lineage types."""
        for lin_type in ["CellLineage", "CycleLineage", "Lineage"]:
            prop = Property(
                identifier="test",
                name="test",
                description="test",
                provenance="test",
                prop_type="node",
                lin_type=lin_type,
                dtype="int",
            )
            assert prop.lin_type == lin_type


class TestPropertyRepr:
    """Test cases for Property.__repr__() method."""

    def test_repr_format(self, prop1):
        """Test that __repr__() returns a valid representation."""
        repr_str = repr(prop1)
        assert "Property(" in repr_str
        assert "identifier='name1'" in repr_str
        assert "name='name1'" in repr_str
        assert "dtype='type1'" in repr_str

    def test_repr_contains_all_fields(self, prop1):
        """Test that __repr__() includes all attribute fields."""
        repr_str = repr(prop1)
        assert "identifier=" in repr_str
        assert "name=" in repr_str
        assert "description=" in repr_str
        assert "provenance=" in repr_str
        assert "prop_type=" in repr_str
        assert "lin_type=" in repr_str
        assert "dtype=" in repr_str
        assert "unit=" in repr_str


class TestPropertyStr:
    """Test cases for Property.__str__() method."""

    def test_str_format(self, prop1):
        """Test that __str__() returns a human-readable string."""
        str_repr = str(prop1)
        assert "Property 'name1'" in str_repr
        assert "Name: name1" in str_repr
        assert "Description: desc1" in str_repr

    def test_str_contains_all_fields(self, prop1):
        """Test that __str__() includes all attribute fields."""
        str_repr = str(prop1)
        assert "Name:" in str_repr
        assert "Description:" in str_repr
        assert "Provenance:" in str_repr
        assert "Type:" in str_repr
        assert "Lineage type:" in str_repr
        assert "Data type:" in str_repr
        assert "Unit:" in str_repr

    def test_str_with_no_unit(self, prop3):
        """Test __str__() when unit is None."""
        str_repr = str(prop3)
        assert "Unit: None" in str_repr
