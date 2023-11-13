#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name="pycellin",
    version="0.2",
    licence="BSD-3-Clause",
    description="Conversion and analysis of TrackMate tracks as networkX directed graphs",
    author="Laura Xénard",
    author_email="laura.xenard@pasteur.fr",
    packages=["pycellin", "pycellin.tmio", "pycellin.graph", "pycellin.graph.features"],
)
