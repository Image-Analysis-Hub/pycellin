# pycellin

`pycellin` is a python library to help analyze tracking data obtained by the Fiji plugin [TrackMate](https://imagej.net/plugins/trackmate/). It focuses on bacteria or cell lineages analysis but might prove useful to other applications.

From TrackMate XML output, `pycellin` builds [NetworkX](https://networkx.org/) directed graphs, thus providing an intuitive way of representing cell lineages.
No tracking information is lost in the process. Each TrackMate track gives birth to a directed graph while TrackMate spots become graph nodes and TrackMate links become graph edges. TrackMate features are stored as either node, edge or graph attributes.

Since the tracks topology is kept intact, it is quite easy to compute new features like division rate, or to do an analysis on individual cells over time. To this end, `pycellin` provides a few tracking and morphological features that can be added automatically to a graph/lineage. It is also possible to add your own features on nodes, edges or graphs.

Finally,  `pycellin` can save these updated graphs into a TrackMate compatible XML. In most cases, the newly added features are carried along and can be used in TrackMate for visualization or filtering purposes.

## Installation

`pycellin` is compatible with at least Python 3.10 and 3.11, and has been tested on Windows and Linux.

Use pip to install the latest development version:

```
pip install git+https://github.com/Image-Analysis-Hub/pycellin.git
```

### Dependencies

`pycellin` itself requires the following dependencies:
- `lxml`
- `matplotlib`
- `networkx`
- `pygraphviz`
- `scikit-image`
- `scipy`
- `shapely`

On top of that, running the tests requires `pytest` and running the notebooks requires `tifffile`.

All these packages are available through conda default channel, except for `pygraphviz` which is available through the conda-forge channel.

See `requirements.txt` for more information.

## Usage

See the `Getting_started` notebook located in the `notebooks` folder.
