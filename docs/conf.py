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


# -- HTML output ---------------------------------------------------------------
# Theme-specific settings stay in this block: switching themes means rewriting it.
# Shibuya options: https://shibuya.lepture.com/

html_theme = "shibuya"
html_theme_options = {
    "accent_color": "purple",
    "github_url": "https://github.com/Image-Analysis-Hub/pycellin",
}
html_logo = "../pycellin_logo.png"
html_static_path = ["_static"]
html_css_files = ["shibuya-overrides.css"]

