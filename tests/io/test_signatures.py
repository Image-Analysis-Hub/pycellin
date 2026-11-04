#!/usr/bin/env python3

"""Unit tests for the signatures shared by the reading and writing functions."""

import inspect

import pytest

import pycellin as pc

# The arguments each function takes by position: its input, and the model for writers.
POSITIONAL_ARGS = {
    "read_ctc": ["path"],
    "read_geff": ["path"],
    "read_pickle": ["path"],
    "read_trackmate_xml": ["path"],
    "from_trackpy": ["df"],
    "write_ctc": ["model", "path"],
    "write_geff": ["model", "path"],
    "write_pickle": ["model", "path"],
    "write_trackmate_xml": ["model", "path"],
    "to_trackpy": ["model"],
}


class TestSignatures:
    """Test cases for the signatures of the reading and writing functions."""

    def test_every_function_listed(self):
        """Test that every reading and writing function of pycellin is listed."""
        prefixes = ("read_", "write_", "from_", "to_")
        names = {name for name in pc.__all__ if name.startswith(prefixes)}
        assert names == set(POSITIONAL_ARGS)

    @pytest.mark.parametrize("name", POSITIONAL_ARGS)
    def test_options_keyword_only(self, name):
        """Test that only the input, and the model for writers, are positional."""
        params = inspect.signature(getattr(pc, name)).parameters.values()
        positional = [p.name for p in params if p.kind is not p.KEYWORD_ONLY]
        assert positional == POSITIONAL_ARGS[name]
