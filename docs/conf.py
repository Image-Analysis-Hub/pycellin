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
    "sphinx_design",
]
myst_enable_extensions = ["colon_fence"]
exclude_patterns = ["_build"]


# -- HTML output ---------------------------------------------------------------
# Theme-specific settings stay in this block: switching themes means rewriting it.
# PyData options: https://pydata-sphinx-theme.readthedocs.io/en/stable/

html_theme = "pydata_sphinx_theme"
html_theme_options = {
    # Font Awesome icons ship with the theme: no download when a page loads.
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/Image-Analysis-Hub/pycellin",
            "icon": "fa-brands fa-github",
        },
    ],
}
html_logo = "../pycellin_logo.png"
html_static_path = ["_static"]
html_css_files = ["pydata-overrides.css"]
