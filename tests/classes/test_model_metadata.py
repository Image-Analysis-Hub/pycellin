#!/usr/bin/env python3

"""Unit tests for the ModelMetadata class from model_metadata.py module."""

import pytest

from pycellin.classes import ModelMetadata


class TestModelMetadataFromDict:
    """Test cases for ModelMetadata.from_dict() method."""

    def test_missing_reference_time_prop_raises(self):
        """Test that a dictionary without the required field raises ValueError."""
        with pytest.raises(ValueError, match="Missing required fields"):
            ModelMetadata.from_dict({"time_step": 1})
