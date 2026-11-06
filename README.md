[![PyPI](https://img.shields.io/pypi/v/pycellin.svg)](https://pypi.org/project/pycellin)
[![Development Status](https://img.shields.io/pypi/status/pycellin.svg)](https://en.wikipedia.org/wiki/Software_release_life_cycle#Beta)
[![Python Version](https://img.shields.io/pypi/pyversions/pycellin.svg)](https://python.org)
[![License](https://img.shields.io/pypi/l/pycellin.svg)](https://github.com/Image-Analysis-Hub/pycellin/blob/main/LICENSE)
[![Actions Status](https://github.com/Image-Analysis-Hub/pycellin/workflows/Test/badge.svg)](https://github.com/Image-Analysis-Hub/pycellin/actions)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

</br>
<p align="center">
    <img src="https://raw.githubusercontent.com/Image-Analysis-Hub/pycellin/main/pycellin_logo.png" height="150"/>
</p>


# Pycellin

Pycellin is a graph-based Python framework to easily manipulate and extract information from cell tracking data, at the single-cell level. In Pycellin, cell lineages are modeled intuitively by directed rooted trees. Graph nodes represent cells at a specific point in time and space, and graph edges represent the time and space displacement of the cells.

Each cell lineage can also be viewed as a cell cycle lineage, or cycle lineage for short, where a node represents a whole cell cycle, from the cell just after a division to the next division, instead of a cell at a specific point in time. You can then measure things at both levels, e.g. the speed of a cell between two timepoints or the duration of a cell cycle.

With Pycellin, you can:

- **Enrich your lineages** with predefined properties related to cell morphology, motion, timing, lineage topology and intensity. `pc.get_pycellin_cell_lineage_properties()` and `pc.get_pycellin_cycle_lineage_properties()` list them all. More predefined properties will be implemented in the future.
- **Create your own properties**, to accommodate the wide variety of experiments and biological questions.
- **Explore** your lineages, by plotting a property along their branches, or the mean of a property over time.
- **Edit your lineages** and **merge datasets** that share the same time and space calibration.
- **Get your data as pandas DataFrames**, with one row per cell, link between cells, cell cycle or lineage, or **write your data** to common tracking file formats.

Pycellin can read from and write to:
- [Cell Tracking Challenge](https://celltrackingchallenge.net/) text files,
- [GEFF](https://liveimagetrackingtools.org/geff/latest/) (Graph Exchange File Format),
- [trackpy](https://github.com/soft-matter/trackpy) DataFrames,
- [TrackMate](https://imagej.net/plugins/trackmate/) XMLs.


Although Pycellin was designed with bacteria / cell lineages in mind, it can be used with more diverse tracking data. The main requirement is that the data can be modeled by directed rooted trees. So while Pycellin is built to support cell divisions, **it does not fully support cell fusions**, also called merging events: a cell at a specific timepoint cannot have more than one parent. Please correct them in your tracking software before using Pycellin. Data with fusions can still be read, with a warning: `get_fusions()` then lists them and you can correct them with `remove_link()`, but until you do, crashes and incorrect results can occur.


## Installation

Pycellin supports Python 3.10 and above. It is tested with Python 3.10 and 3.14 on the latest versions of Ubuntu, Windows and macOS. Please [let me know](https://github.com/Image-Analysis-Hub/pycellin/issues) if you encounter any compatibility issue with a different combination.

It is recommended to install Pycellin in a conda or mamba environment. 

1. Check that conda/mamba is already installed by typing either `conda` or `mamba` in a terminal. If not, follow the installation instructions on [Miniforge](https://conda-forge.org/download/).

2. Create a Python environment dedicated to Pycellin:
    ```
    conda create -n my_env_pycellin python=3.14
    ```

3. Activate the environment:
    ```
    conda activate my_env_pycellin
    ```

4. Install Pycellin via [PyPI](https://pypi.org/):
    ```
    pip install pycellin
    ```
    or if you want to run the example notebooks, use instead:
    ```
    pip install "pycellin[notebooks]"
    ```
    This also installs JupyterLab, which you start with `jupyter lab`.
    To run the tests from a clone of the repository, install the test dependencies with pip >= 25.1:
    ```
    pip install -e . --group test
    ```

5. You're good to go!

> **Upgrading from 0.5.1?** Version 0.6.0 renames many functions, methods and arguments, without aliases: for example, `load_TrackMate_XML()` is now `read_trackmate_xml()`. Pickle files written with 0.5.1 can't be read anymore either. The [changelog](https://github.com/Image-Analysis-Hub/pycellin/blob/main/CHANGELOG.md) lists all the changes.


## Code Example

```python
import pycellin as pc

# Read data from an external tool, here TrackMate.
xml_path = "sample_data/Ecoli_growth_on_agar_pad.xml"
model = pc.read_trackmate_xml(xml_path)

# Plot the cell lineages.
for lin in model.get_cell_lineages():
    lin.plot()

# Compute and plot the cell cycle lineages.
model.add_cycle_lineages()
for clin in model.get_cycle_lineages():
    clin.plot()

# Enrich your lineages with additional predefined properties.
model.add_pycellin_properties(
    [
        "rod_length",
        "rod_width",
        "cell_displacement",
        "cell_speed",
        "cycle_mean_speed",
        "relative_age",
        "interdivision_time",
        "is_complete_cycle",
    ]
)
model.update()

# Get the enriched data as dataframes...
cell_df = model.to_cell_dataframe()
link_df = model.to_link_dataframe()
cycle_df = model.to_cycle_dataframe()
lineage_df = model.to_lineage_dataframe()

# ... or write it back to TrackMate for visualization...
pc.write_trackmate_xml(
    model,
    "sample_data/Ecoli_growth_on_agar_pad_enriched.xml",
    propagate_cycle_props=True,
)

# ... or to another file format.
pc.write_geff(
    model,
    "sample_data/Ecoli_growth_on_agar_pad_enriched.geff",
    propagate_cycle_props=True,
)
```


## Usage

Please note that the following notebooks serve as temporary documentation. A full user's documentation and API documentation will be added soon.

| Notebook                                                                                                              | Description                                                         | Level    |
|-----------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------|----------|
| [Getting started](https://github.com/Image-Analysis-Hub/pycellin/blob/main/notebooks/Getting%20started.ipynb)         | The basics of Pycellin, through examples                            | Beginner |
| [Managing properties](https://github.com/Image-Analysis-Hub/pycellin/blob/main/notebooks/Managing%20properties.ipynb) | How to add, compute and remove properties                           | Beginner |
| [Custom properties](https://github.com/Image-Analysis-Hub/pycellin/blob/main/notebooks/Custom%20properties.ipynb)     | How to create user-defined properties and add them to your lineages | Advanced |


## Credits and references

- Laure Le Blanc for _Escherichia coli_ growth on agar pad data (in sample_data directory)
- Jean-Yves Tinevez for _Caenorhabditis elegans_ embryo development data, from the [TrackMate manual track editing tutorial](https://imagej.net/plugins/trackmate/tutorials/manual-track-editing) (in sample_data directory)
- The [TrackMate getting started tutorial](https://imagej.net/plugins/trackmate/tutorials/getting-started) for the FakeTracks test data (in sample_data directory)
- [NetworkX](https://networkx.org/) for lineages modeling ([Hagberg, Schult and Swart, 2008](http://conference.scipy.org.s3-website-us-east-1.amazonaws.com/proceedings/scipy2008/paper_2/))
- [TrackMate](https://imagej.net/plugins/trackmate/) for the TrackMate data reader and writer ([Tinevez et al., 2017](https://doi.org/10.1016/j.ymeth.2016.09.016), [Ershov et al., 2022](https://doi.org/10.1038/s41592-022-01507-1))
- The [Cell Tracking Challenge](https://celltrackingchallenge.net/) for the CTC data reader and writer ([Maška et al., 2023](https://doi.org/10.1038/s41592-023-01879-y))
- [GEFF](https://liveimagetrackingtools.org/geff/latest/) for the GEFF data reader and writer ([Schwartz et al., 2026](https://doi.org/10.21105/joss.10143))
- [trackpy](https://github.com/soft-matter/trackpy) for the trackpy data reader and writer ([Allan et al., 2024](https://doi.org/10.5281/zenodo.12708864))
