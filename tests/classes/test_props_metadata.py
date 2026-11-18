#!/usr/bin/env python3

"""Unit tests for the PropsMetadata class from props_metadata.py module."""

import pytest

from pycellin.classes import Property, PropsMetadata


def _create_prop(identifier):
    return Property(
        identifier=identifier,
        name=identifier,
        description=f"A {identifier} property",
        provenance="test",
        prop_type="node",
        lineage_type="cell",
        dtype="int",
    )


@pytest.fixture()
def declared_prop():
    return _create_prop("declared")


class TestPropsMetadataConstructor:
    """Test cases for PropsMetadata constructor."""

    def test_undeclared_protected_props_are_all_dropped(self, declared_prop):
        """Test that each undeclared protected property is dropped with a warning."""
        # Two undeclared properties in a row: the second one was kept before.
        protected = ["missing_a", "missing_b", "declared", "missing_c"]
        with pytest.warns(UserWarning, match="does not exist") as record:
            props_md = PropsMetadata(
                properties={"declared": declared_prop}, protected_props=protected
            )
        assert props_md._protected_props == ["declared"]
        assert len(record) == 3

    def test_given_lists_are_not_modified(self, declared_prop):
        """Test that the lists given stay unchanged and aren't shared."""
        protected = ["missing", "declared"]
        propagated = ["declared"]
        with pytest.warns(UserWarning):
            props_md = PropsMetadata(
                properties={"declared": declared_prop},
                protected_props=protected,
                propagated_props=propagated,
            )
        assert protected == ["missing", "declared"]
        assert props_md._protected_props is not protected
        assert props_md._propagated_props is not propagated


class TestChangePropIdentifier:
    """Test cases for PropsMetadata._change_prop_identifier()."""

    def test_identifier_already_declared_raises(self, declared_prop):
        """Test that another declaration isn't replaced."""
        other_prop = _create_prop("other")
        props_md = PropsMetadata(
            properties={"declared": declared_prop, "other": other_prop}
        )
        with pytest.raises(ValueError, match="already declared"):
            props_md._change_prop_identifier("declared", "other")
        assert props_md.properties["declared"] is declared_prop
        assert props_md.properties["other"] is other_prop

    def test_non_string_identifier_changes_nothing(self, declared_prop):
        """Test that the declaration stays under its identifier."""
        props_md = PropsMetadata(properties={"declared": declared_prop})
        with pytest.raises(TypeError):
            props_md._change_prop_identifier("declared", 3)
        assert list(props_md.properties) == ["declared"]


class TestProtectProp:
    """Test cases for PropsMetadata._protect_prop()."""

    def test_undeclared_prop_is_not_protected(self, declared_prop):
        """Test that a property that isn't declared isn't protected."""
        props_md = PropsMetadata(properties={"declared": declared_prop})
        with pytest.warns(UserWarning, match="cannot be protected"):
            props_md._protect_prop("missing")
        assert "missing" not in props_md._protected_props
