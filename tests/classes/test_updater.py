#!/usr/bin/env python3

"""Unit tests for ModelUpdater class from updater.py module."""

from typing import ClassVar

from pycellin.classes import Property
from pycellin.classes.property_calculator import NodeLocalPropCalculator
from pycellin.classes.updater import ModelUpdater


def _create_calculator(identifier: str, input_prop: str | None = None):
    """Create a calculator for a node property, reading `input_prop` if given."""
    prop = Property(
        identifier=identifier,
        name=identifier,
        description=identifier,
        provenance="test",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
    )
    if input_prop is None:
        return Constant(prop)
    return Copy(prop, input_prop)


class Constant(NodeLocalPropCalculator):
    """User-defined property with the same value on every cell."""

    def compute(self, lineage, nid):
        return 1.0


class Copy(NodeLocalPropCalculator):
    """User-defined property copying another node property."""

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "input_prop": ("node", "CellLineage")
    }

    def __init__(self, property, input_prop):
        super().__init__(property)
        self.input_prop = input_prop

    def compute(self, lineage, nid):
        return lineage.nodes[nid][self.input_prop]


class TestOrderCalculators:
    """Test cases for ModelUpdater._order_calculators() method."""

    def test_registration_order_kept_without_dependencies(self):
        """Test that calculators that read no property keep their order."""
        updater = ModelUpdater()
        for identifier in ["b", "c", "a"]:
            updater.register_calculator(_create_calculator(identifier))
        assert list(updater._calculators) == ["b", "c", "a"]

    def test_input_moved_before_its_reader(self):
        """Test that a calculator registered after a reader of its property runs
        before it."""
        updater = ModelUpdater()
        updater.register_calculator(_create_calculator("other"))
        updater.register_calculator(_create_calculator("copy", input_prop="x"))
        updater.register_calculator(_create_calculator("x"))
        assert list(updater._calculators) == ["other", "x", "copy"]

    def test_calculators_in_between_stay_after_the_reader(self):
        """Test that the input is moved before its reader rather than the reader after
        the input, so that the calculators registered in between still run after the
        reader."""
        updater = ModelUpdater()
        updater.register_calculator(_create_calculator("copy", input_prop="x"))
        updater.register_calculator(_create_calculator("other"))
        updater.register_calculator(_create_calculator("x"))
        assert list(updater._calculators) == ["x", "copy", "other"]

    def test_chain_of_readers(self):
        """Test that each calculator runs after the ones it reads, through a chain."""
        updater = ModelUpdater()
        updater.register_calculator(_create_calculator("c", input_prop="b"))
        updater.register_calculator(_create_calculator("b", input_prop="a"))
        updater.register_calculator(_create_calculator("a"))
        assert list(updater._calculators) == ["a", "b", "c"]

    def test_replaced_calculator_stays_before_its_reader(self):
        """Test that registering a calculator again keeps it before its readers."""
        updater = ModelUpdater()
        updater.register_calculator(_create_calculator("x"))
        updater.register_calculator(_create_calculator("copy", input_prop="x"))
        new_calc = _create_calculator("x")
        updater.register_calculator(new_calc)
        assert list(updater._calculators) == ["x", "copy"]
        assert updater._calculators["x"] is new_calc

    def test_timepoint_stays_first(self):
        """Test that the timepoint calculator stays first."""
        updater = ModelUpdater()
        updater.register_calculator(_create_calculator("copy", input_prop="x"))
        updater.register_calculator(_create_calculator("x"))
        updater.register_calculator(_create_calculator("timepoint"))
        assert list(updater._calculators) == ["timepoint", "x", "copy"]

    def test_circular_dependencies_keep_all_calculators(self):
        """Test that calculators reading each other are all kept."""
        updater = ModelUpdater()
        updater.register_calculator(_create_calculator("a", input_prop="b"))
        updater.register_calculator(_create_calculator("b", input_prop="a"))
        assert sorted(updater._calculators) == ["a", "b"]
