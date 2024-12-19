#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import get_args, get_origin, Literal


def check_literal_type(value, literal_type) -> bool:
    if get_origin(literal_type) is Literal:
        return value in get_args(literal_type)
    raise TypeError(f"{literal_type} is not a Literal type")
