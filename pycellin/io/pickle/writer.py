#!/usr/bin/env python3

"""Writer for pickle files of Pycellin models."""

import pickle
from pathlib import Path

from pycellin.classes.model import Model


def write_pickle(
    model: Model, path: str | Path, *, protocol: int = pickle.HIGHEST_PROTOCOL
) -> None:
    """
    Write a Pycellin model to a pickle file.

    The whole model is saved, so that work on it can be resumed later, e.g. in
    another Python session, with `read_pickle()`.

    Parameters
    ----------
    model : Model
        The model to write.
    path : str | Path
        Path of the pickle file to write.
    protocol : int, default=pickle.HIGHEST_PROTOCOL
        Pickle protocol to use.
    """
    with open(path, "wb") as file:
        pickle.dump(model, file, protocol=protocol)
