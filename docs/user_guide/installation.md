# Installation

Pycellin supports Python 3.10 and above. It is tested with Python 3.10 and 3.14 on the latest versions of Ubuntu, Windows and macOS. Please [let me know](https://github.com/Image-Analysis-Hub/pycellin/issues) if you encounter any compatibility issue with a different combination.

It is recommended to install Pycellin in a conda or mamba environment. 

1. Check that conda/mamba is already installed by typing either `conda` or `mamba` in a terminal. If not, follow the installation instructions on [Miniforge](https://conda-forge.org/download/).

2. Create a Python environment dedicated to Pycellin:
    ```shell
    conda create -n my_env_pycellin python=3.14
    ```

3. Activate the environment:
    ```shell
    conda activate my_env_pycellin
    ```

4. Install Pycellin via [PyPI](https://pypi.org/), choosing one of:

    ::::{tab-set}
    :::{tab-item} Standard
    ```shell
    pip install pycellin
    ```
    :::
    :::{tab-item} With the example notebooks
    ```shell
    pip install "pycellin[notebooks]"
    ```
    This also installs JupyterLab, which you start with `jupyter lab`.
    :::
    :::{tab-item} For development
    From a clone of the repository, with pip >= 25.1:
    ```shell
    pip install -e . --group test
    ```
    :::
    :::: 

5. You're good to go!


:::{admonition} Upgrading from 0.5.1?
:class: warning
:name: upgrading-from-0-5-1

Version 0.6.0 renames many functions, methods and arguments, without aliases: for example, `load_TrackMate_XML()` is now `read_trackmate_xml()`. Pickle files written with 0.5.1 can't be read anymore either. The [changelog](https://github.com/Image-Analysis-Hub/pycellin/blob/main/CHANGELOG.md) lists all the changes.
:::

