from typing import Final

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio


# Pycellin colors.
PYCELLIN_PURPLE: Final = "#7F08A4"
PYCELLIN_PINK: Final = "#BE3985"
PYCELLIN_ORANGE: Final = "#E36A5E"

# Pycellin templates.
# Shared style config.
_COMMON_AXIS = dict(
    showgrid=False,
    ticks="outside",
    ticklen=5,
    tickwidth=1,
    showline=True,
    linewidth=1,
    rangemode="tozero",
)
_COMMON_LAYOUT = dict(
    hovermode="x unified",
    font=dict(family="Arial", size=13),
    colorway=list(px.colors.qualitative.Safe),
)


def _make_axis(color: str) -> dict:
    """Return the shared axis style with the given tick/line color."""
    return {**_COMMON_AXIS, "tickcolor": color, "linecolor": color}


def _make_template(base: str, axis_color: str) -> go.layout.Template:
    """
    Build a Pycellin template on top of a built-in Plotly template.

    Parameters
    ----------
    base : str
        Name of the built-in Plotly template to extend (e.g. "plotly_white").
    axis_color : str
        Color of the axis ticks and lines (e.g. "black" or "white").

    Returns
    -------
    go.layout.Template
        A new template extending `base` with Pycellin styling.
    """
    custom = go.layout.Template(
        layout=dict(
            xaxis=_make_axis(axis_color),
            yaxis=_make_axis(axis_color),
            **_COMMON_LAYOUT,
        )
    )
    return go.layout.Template(pio.templates[base]).update(custom)


pio.templates["pycellin_white"] = _make_template("plotly_white", axis_color="black")
pio.templates["pycellin_dark"] = _make_template("plotly_dark", axis_color="white")
