"""Sphinx configuration for the pycellin documentation.

Settings reference: https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import pycellin

# -- Project information -------------------------------------------------------

project = "Pycellin"
author = "Laura Xénard"
copyright = "2023-%Y, Institut Pasteur Paris, Laura Xénard"
release = pycellin.__version__

# -- General configuration -----------------------------------------------------

extensions = [
    "myst_parser",
]
exclude_patterns = ["_build"]
