[![PyPI](https://img.shields.io/pypi/v/pycellin.svg)](https://pypi.org/project/pycellin)
[![Development Status](https://img.shields.io/pypi/status/pycellin.svg)](https://en.wikipedia.org/wiki/Software_release_life_cycle#Beta)
[![Python Version](https://img.shields.io/pypi/pyversions/pycellin.svg)](https://python.org)
[![License](https://img.shields.io/pypi/l/pycellin.svg)](https://github.com/Image-Analysis-Hub/pycellin/blob/main/LICENSE)
[![Actions Status](https://github.com/Image-Analysis-Hub/pycellin/workflows/Test/badge.svg)](https://github.com/Image-Analysis-Hub/pycellin/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

</br>
<p align="center">
    <img src="https://github.com/Image-Analysis-Hub/pycellin/blob/main/pycellin_logo.png" height="150"/>
</p>


# Pycellin

Pycellin is a graph-based Python framework to easily manipulate and extract information from cell tracking data, at the single-cell level. In pycellin, cell lineages are modeled intuitively by directed rooted trees. Graph nodes represent cells at a specific point in time and space, and graph edges represent the time and space displacement of the cells. Please note that while pycellin is built to support cell division events, **it does not authorize cell merging events**: a cell at a specific timepoint cannot have more than one parent.

Pycellin provides predefined features related to cell morphology, cell motion and tracking that can be automatically added to enrich lineages. More predefined features will be implemented in the future. The framework also facilitates the creation of new features defined by the user to accommodate the wide variety of experiments and biological questions.

Pycellin can read from and write to:
- [TrackMate](https://imagej.net/plugins/trackmate/) XMLs,
- [Cell Tracking Challenge](https://celltrackingchallenge.net/) text files,
- [trackpy](https://github.com/soft-matter/trackpy) DataFrames.

More tracking formats will progressively be supported.

While pycellin has been designed with bacteria / cell lineages in mind, it could be used with more diverse tracking data provided the few conditions below are enforced:
- the tracking data can be modeled by directed rooted trees, meaning no merging event
- gaps between detection are allowed but the time step must consistent.


## Installation

Pycellin supports Python 3.10 and above. It is tested with Python 3.10 and 3.13 on the latest versions of Ubuntu, Windows and MacOS. Please let me know if you encounter any compatibility issue with a different combination.

It is recommended to install pycellin in a conda or mamba environment. 

1. Check that conda/mamba is already installed by typing either `conda` or `mamba` in a terminal. If not, follow the installation instructions on [Miniforge](https://conda-forge.org/download/).

2. Create a Python environment dedicated to pycellin:
    ```
    conda create -n my_env_pycellin
    ```

3. Activate the environment:
    ```
    conda activate my_env_pycellin
    ```

4. Install pycellin via [PyPI](https://pypi.org/):
    ```
    pip install pycellin
    ```
    or if you want to install the optional test related dependencies use instead:
    ```
    pip install pycellin[test]
    ```

5. You're good to go!


## Code Example

```python
import pycellin

# Import data from an external tool, here TrackMate.
xml_path = "sample_data/Ecoli_growth_on_agar_pad.xml"
model = pycellin.load_TrackMate_XML(xml_path)

# Plot the cell lineages.
for lin in model.get_cell_lineages():
    plot(lin)

# Compute and plot the cell cycle lineages.
model.add_cycle_data()
for clin in model.get_cycle_lineages():
    plot(clin)

# Enrich your lineages with additional predefined features.
model.add_pycellin_features([
    "cell_length", 
    "cell_width",
    "cell_displacement", 
    "cell_speed", 
    "branch_mean_speed",
    "relative_age",
    "division_time", 
    "cell_cycle_completeness",
    ])
model.update()

# Export the enriched data as dataframes.
cell_df = model.to_cell_dataframe()
link_df = model.to_link_dataframe()
cycle_df = model.to_cycle_dataframe()
lineage_df = model.to_lineage_dataframe()
```


## Usage

Please note that the following notebooks are still a work in progress. There may be some mistakes in the code and some sections might move from one notebook to another.

| Notebook                                                                                 | Description                                                       | Level    | State |
|------------------------------------------------------------------------------------------|-------------------------------------------------------------------|----------|-------|
| [Getting started](./notebooks/Getting%20started.ipynb)                                   | The basics of pycellin, through examples                          | Beginner | WIP   |
| [Managing features](./notebooks/Managing%20features.ipynb)                               | How to add, compute and remove features from a model              | Beginner | WIP   |
| [Working with TrackMate data](./notebooks/Working%20with%20TrackMate%20data.ipynb)       | How pycellin can work with TrackMate, through an example          | Beginner | WIP   |
| [Creating a model from scratch](./notebooks/Creating%20a%20model%20from%20scratch.ipynb) | How to manually create a pycellin model, including its lineages   | Advanced | Stub  |
| [Custom features](./notebooks/Custom%20features.ipynb)                                   | How to create user-defined features and augment a model with them | Advanced | WIP   |


## Credits and references

- Laure Le Blanc for _Escherichia coli_ growth on agar pad data (in sample_data directory)
- [NetworkX](https://networkx.org/) for lineages modeling ([Hagberg, Schult and Swart, 2008](http://conference.scipy.org.s3-website-us-east-1.amazonaws.com/proceedings/scipy2008/paper_2/))
- [TrackMate](https://imagej.net/plugins/trackmate/) for the TrackMate data loader and exporter ([Tinevez et al., 2017](https://doi.org/10.1016/j.ymeth.2016.09.016), [Ershov et al., 2022](https://doi:10.1038/s41592-022-01507-1))
- The [Cell Tracking Challenge](https://celltrackingchallenge.net/) for the CTC data loader and exporter ([Maška et al., 2023](https://doi.org/10.1038/s41592-023-01879-y))
- [trackpy](https://github.com/soft-matter/trackpy) for the trackpy data loader and exporter ([Allan et al., 2024](https://doi.org/10.5281/zenodo.12708864))
