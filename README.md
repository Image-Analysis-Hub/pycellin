# pycellin

`pycellin` is a python library to help analyze tracking data obtained by the Fiji plugin [TrackMate](https://imagej.net/plugins/trackmate/).


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
