#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name="pycellin",
    version="0.3",
    licence="BSD-3-Clause",
    description="Graph-based framework to analyze cell lineages",
    author="Laura Xénard",
    author_email="laura.xenard@pasteur.fr",
    packages=["pycellin", "pycellin.tmio", "pycellin.graph", "pycellin.graph.features"],
)
