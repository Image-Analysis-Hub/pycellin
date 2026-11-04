#!/usr/bin/env python3

"""
writer.py

This module is part of the pycellin package.

This module provides a function to write a pycellin model to a pickle file.
"""

import pickle
from pathlib import Path

from pycellin.classes.model import Model


def write_pickle(
    model: Model, path: str | Path, *, protocol: int = pickle.HIGHEST_PROTOCOL
) -> None:
    """
    Write a pycellin model to a pickle file.

    The whole model is saved, so that work on it can be resumed later, e.g. in
    another Python session, with `read_pickle()`.

    Parameters
    ----------
    model : Model
        The model to write.
    path : str | Path
        Path of the pickle file to write.
    protocol : int, optional
        Pickle protocol to use (default is pickle.HIGHEST_PROTOCOL).
    """
    with open(path, "wb") as file:
        pickle.dump(model, file, protocol=protocol)
