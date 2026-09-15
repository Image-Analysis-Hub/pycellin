#!/usr/bin/env python3

"""Unit test for exception classes from classes.exceptions."""

from pycellin.classes.exceptions import MissingPropertyError

# MissingPropertyError ########################################################


class TestMissingPropertyError:
    def test_default_message_with_node_and_lineage(self):
        err = MissingPropertyError("cell_area", nid=3, lineage_ID=1)
        assert err.nid == 3
        assert err.message == (
            "Required property 'cell_area' is missing for node 3 in lineage 1."
        )

    def test_default_message_without_node(self):
        err = MissingPropertyError("cell_area")
        assert err.nid is None
        assert err.message == "Required property 'cell_area' is missing."

    def test_custom_message(self):
        err = MissingPropertyError("cell_area", message="Add 'cell_area' first.")
        assert err.prop_name == "cell_area"
        assert err.message == "Add 'cell_area' first."
