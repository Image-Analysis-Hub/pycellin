"""Sphinx configuration for the pycellin documentation.

Settings reference: https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import enum
import inspect
import logging
import os
from pathlib import Path

import networkx as nx
from sphinx.ext import intersphinx
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
    "sphinx.ext.extlinks",
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
    "plotly": ("https://plotly.com/python-api-reference/", None),
    "python": ("https://docs.python.org/3/", None),
}
# Links to the files of the repository, in the version these docs are built from: the
# commit Read the Docs checked out, or dev for local builds. For example
# {repo}`Getting started <notebooks/Getting%20started.ipynb>`.
_git_ref = os.environ.get("READTHEDOCS_GIT_COMMIT_HASH", "dev")
extlinks = {
    "repo": (
        f"https://github.com/Image-Analysis-Hub/pycellin/blob/{_git_ref}/%s",
        "%s",
    ),
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
    # Written in full in the docstrings: an alias to the same name stays plain text
    # (numpydoc_xref_ignore = "all"), but a role links.
    "plotly.graph_objects.Figure": ":class:`plotly.graph_objects.Figure`",
    # pycellin's classes and exceptions, by their short names.
    "Cell": "pycellin.custom_types.Cell",
    "CellLineage": "pycellin.CellLineage",
    "CycleLineage": "pycellin.CycleLineage",
    "Data": "pycellin.Data",
    "Model": "pycellin.Model",
    "ModelMetadata": "pycellin.ModelMetadata",
    "Property": "pycellin.Property",
    "PropertyType": "pycellin.custom_types.PropertyType",
    "PropsMetadata": "pycellin.PropsMetadata",
    "FusionError": "pycellin.exceptions.FusionError",
    "LineageStructureError": "pycellin.exceptions.LineageStructureError",
    "MissingPropertyError": "pycellin.exceptions.MissingPropertyError",
    "ProtectedPropertyError": "pycellin.exceptions.ProtectedPropertyError",
    "TimeFlowError": "pycellin.exceptions.TimeFlowError",
    "UpdateRequiredError": "pycellin.exceptions.UpdateRequiredError",
}
# Check docstrings against numpydoc's guide. Left out: the checks asking for more
# content (extended summary, Examples, See Also), and GL02 (closing quotes on their own
# line), which the #: comments documenting attributes can't follow.
numpydoc_validation_checks = {"all", "ES01", "EX01", "SA01", "GL02"}
# Not checked: numpydoc reads the (*values) signature Python gives enum classes.
numpydoc_validation_exclude = {r"^pycellin\.custom_types\.PropertyType$"}
default_role = "py:obj"
# Report every reference that doesn't resolve, like the -n option.
nitpicky = True
# Parameter names go in single backticks too (numpydoc's guide) and can't link: don't
# report bare lowercase names that don't resolve.
nitpick_ignore_regex = [("py:obj", r"[a-z_][a-z0-9_]*")]
# Types in signatures with no page to link to.
nitpick_ignore = [
    # pycellin's private base classes.
    ("py:class", "pycellin.classes.lineage.Lineage"),
    ("py:class", "pycellin.classes.property_calculator.PropertyCalculator"),
    # No working entry in plotly's inventory.
    ("py:class", "plotly.graph_objs.layout._template.Template"),
]


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


def _enum_signature(app, what, name, obj, options, signature, return_annotation):
    """Hide the (*values) signature Python gives enum classes.

    Users write PropertyType.NODE, never PropertyType(...).
    """
    if what == "class" and isinstance(obj, type) and issubclass(obj, enum.Enum):
        return "", None
    return None


# numpydoc messages already shown, see _show_once.
_shown = set()


def _show_once(record):
    """Drop a numpydoc message already shown.

    autosummary reads the docstring of each object it lists, for the table row, then the
    object's page reads it again: numpydoc checks it, and warns, twice.
    """
    message = record.getMessage()
    if message in _shown:
        return False
    _shown.add(message)
    return True


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


# plotly classes in pycellin's type hints, by the public name plotly's docs list
# (plotly's inventory still lists plotly.graph_objs names, but their pages are gone).
_PLOTLY_PUBLIC_NAMES = {
    "plotly.graph_objs._figure.Figure": "plotly.graph_objects.Figure",
}


def _plotly_public_name(app, env, node, contnode):
    """Link plotly classes under their public name.

    Type hints give plotly's private module (plotly.graph_objs._figure.Figure), which
    plotly's docs don't list.
    """
    public = _PLOTLY_PUBLIC_NAMES.get(node.get("reftarget"))
    if public is None:
        return None
    node["reftarget"] = public
    return intersphinx.missing_reference(app, env, node, contnode)


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
    # "Edit on GitHub" button, in the right sidebar. See _edit_button_off_on_api_pages.
    "use_edit_page_button": True,
}
# Where that button points: docs/ on the dev branch.
html_context = {
    "github_user": "Image-Analysis-Hub",
    "github_repo": "pycellin",
    "github_version": "dev",
    "doc_path": "docs",
}
# No "Show Source" link: the edit button replaces it.
html_show_sourcelink = False
html_logo = "_static/logo/pycellin_logo.svg"
html_static_path = ["_static"]
html_css_files = ["pydata-overrides.css"]
# On Read the Docs, tell search engines which URL is the main copy of each page.
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")


def _edit_button_off_on_api_pages(app, pagename, templatename, context, doctree):
    """Hide the "Edit on GitHub" button on the pages autosummary generates.

    They have no file in the repository: their content comes from the docstrings.
    """
    if pagename.startswith("api/generated/"):
        context["theme_use_edit_page_button"] = False


# -- Event handlers ------------------------------------------------------------


def setup(app):
    app.connect("autodoc-process-signature", _lineage_signature)
    app.connect("autodoc-process-signature", _enum_signature)
    app.connect("builder-inited", _write_predefined_properties)
    app.connect("missing-reference", _plotly_public_name)
    app.connect("html-page-context", _edit_button_off_on_api_pages)
    logging.getLogger("sphinx.numpydoc.numpydoc").addFilter(_show_once)
