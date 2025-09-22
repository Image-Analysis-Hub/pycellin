#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.metadata
from typing import get_args, get_origin, Literal


def check_literal_type(value, literal_type) -> bool:
    if get_origin(literal_type) is Literal:
        return value in get_args(literal_type)
    raise TypeError(f"{literal_type} is not a Literal type")


def get_pycellin_version() -> str:
    """Get pycellin version from package metadata"""
    try:
        return importlib.metadata.version("pycellin")
    except importlib.metadata.PackageNotFoundError:
        return "development"
