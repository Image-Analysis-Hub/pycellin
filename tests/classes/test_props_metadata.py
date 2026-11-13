#!/usr/bin/env python3

"""Unit tests for the PropsMetadata class from props_metadata.py module."""

import pytest

from pycellin.classes import Property, PropsMetadata


@pytest.fixture()
def declared_prop():
    return Property(
        identifier="declared",
        name="declared",
        description="A declared property",
        provenance="test",
        prop_type="node",
        lineage_type="cell",
        dtype="int",
    )


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
