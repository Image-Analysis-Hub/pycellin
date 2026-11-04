#!/usr/bin/env python3

"""
reader.py

This module is part of the pycellin package.

This module provides a function to read a pycellin model from a pickle file.
"""

import pickle
from pathlib import Path

from pycellin.classes.model import Model


def read_pickle(path: str | Path) -> Model:
    """
    Read a pycellin model from a pickle file.

    Only read pickle files from sources you trust: unpickling a file can run
    arbitrary code. A model pickled with another version of pycellin may not be
    readable.

    Parameters
    ----------
    path : str | Path
        Path of the pickle file to read.

    Returns
    -------
    Model
        The model read from the file.
    """
    with open(path, "rb") as file:
        return pickle.load(file)
