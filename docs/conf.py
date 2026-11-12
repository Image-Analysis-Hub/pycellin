"""Sphinx configuration for the pycellin documentation.

Settings reference: https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import inspect
from pathlib import Path

import networkx as nx
from sphinx.util.inspect import stringify_signature

import pycellin

# -- Project information -------------------------------------------------------

project = "Pycellin"
author = "Laura Xénard"
copyright = "2023-%Y, Institut Pasteur Paris, Laura Xénard"
release = pycellin.__version__


# -- General configuration -----------------------------------------------------

extensions = [
    "myst_parser",
    "numpydoc",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_design",
]
myst_enable_extensions = ["colon_fence"]
exclude_patterns = ["_build", "_generated"]
templates_path = ["_templates"]
intersphinx_mapping = {
    "networkx": ("https://networkx.org/documentation/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "python": ("https://docs.python.org/3/", None),
}


# -- API reference -------------------------------------------------------------

autoclass_content = "both"
numpydoc_show_class_members = False
toc_object_entries_show_parents = "hide"
numpydoc_xref_param_type = True
numpydoc_xref_ignore = "all"
numpydoc_xref_aliases = {
    # Other projects, by the short names pycellin's docstrings use.
    "nx.DiGraph": "networkx.DiGraph",
    "pd.DataFrame": "pandas.DataFrame",
    "Path": "pathlib.Path",
    # pycellin's classes and exceptions, by their short names.
    "CellLineage": "pycellin.CellLineage",
    "CycleLineage": "pycellin.CycleLineage",
    "Data": "pycellin.Data",
    "Model": "pycellin.Model",
    "ModelMetadata": "pycellin.ModelMetadata",
    "Property": "pycellin.Property",
    "PropsMetadata": "pycellin.PropsMetadata",
    "FusionError": "pycellin.exceptions.FusionError",
    "LineageStructureError": "pycellin.exceptions.LineageStructureError",
    "MissingPropertyError": "pycellin.exceptions.MissingPropertyError",
    "ProtectedPropertyError": "pycellin.exceptions.ProtectedPropertyError",
    "TimeFlowError": "pycellin.exceptions.TimeFlowError",
    "UpdateRequiredError": "pycellin.exceptions.UpdateRequiredError",
}
default_role = "py:obj"
# Parameter names go in single backticks too (numpydoc's guide) and can't link: don't
# report bare lowercase names that don't resolve.
nitpick_ignore_regex = [("py:obj", r"[a-z_][a-z0-9_]*")]


def _lineage_signature(app, what, name, obj, options, signature, return_annotation):
    """Show the __init__ signature of the lineage classes, not NetworkX's __new__.

    Sphinx calls this for every object autodoc documents. Returning None keeps the
    signature autodoc found.
    """
    if what == "class" and isinstance(obj, type) and issubclass(obj, nx.DiGraph):
        sig = inspect.signature(obj.__init__, eval_str=True)
        # Drop self.
        sig = sig.replace(parameters=list(sig.parameters.values())[1:])
        text = stringify_signature(
            sig, show_return_annotation=False, unqualified_typehints=True
        )
        return text, None
    return None


def _write_predefined_properties(app):
    """Write the tables included by api/predefined_properties.md.

    The file is only rewritten when its content changes, so that Sphinx doesn't reread
    the page at every build.
    """
    lines = []
    for title, get_properties in [
        ("Cell lineages", pycellin.get_pycellin_cell_lineage_properties),
        ("Cycle lineages", pycellin.get_pycellin_cycle_lineage_properties),
    ]:
        lines += [f"## {title}", "", "| Property | Description | Added with |"]
        lines += ["| --- | --- | --- |"]
        for identifier, description in get_properties().items():
            method = f"add_{identifier}"
            if hasattr(pycellin.Model, method):
                added_with = f"{{meth}}`~pycellin.Model.{method}`"
            else:
                added_with = "Automatic"
            description = description.replace("|", r"\|")
            lines.append(f"| `{identifier}` | {description} | {added_with} |")
        lines.append("")
    text = "\n".join(lines)
    path = Path(app.srcdir, "_generated", "predefined_properties.md")
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")


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


# -- Event handlers ------------------------------------------------------------


def setup(app):
    app.connect("autodoc-process-signature", _lineage_signature)
    app.connect("builder-inited", _write_predefined_properties)
