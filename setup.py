#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name="pycellin",
    version="0.3.1",
    licence="BSD-3-Clause",
    description=(
        "Graph-based framework to manipulate and analyze cell lineages "
        "from cell tracking data"
    ),
    author="Laura Xénard",
    author_email="laura.xenard@pasteur.fr",
    packages=["pycellin", "pycellin.io", "pycellin.graph", "pycellin.graph.features"],
)
