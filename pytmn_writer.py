#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Importation of ImageJ TrackMate results (XML file) as a Python network
for tracks analysis.
"""

__author__ = "Laura Xénard"
__contact__ = "laura.xenard@pasteur.fr"
__copyright__ = "GNU GPLv3"
__date__ = "2022-02-07"
__version__ = "0.2"

import argparse

from importlib.metadata import version
from pathlib import Path
import pickle
import time

import networkx as nx

import XML_reader
import XML_writer


if __name__ == "__main__":
    start = time.process_time()
    print("Starting conversion...")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input",
        help=("gpickle (.gz) file to process, or folder holding the .gz"),
    )
    parser.add_argument(
        "output",
        help=(""),
    )
    parser.add_argument(
        "--header",
        dest="header",
        action="store",
        help=("original xml file to get its header"),
    )
    parser.add_argument(
        "--settings",
        dest="settings",
        action="store",
        help=("original xml file to get its settings"),
    )

    args = parser.parse_args()

    input = Path(args.input)
    if input.is_dir():
        pass
    else:
        try:
            # opening the file as a gpickle
            pass
        except ValueError:
            # find the correct error when file do not have the correct format
            pass

    print(args.header)

    # Small change of API between version 2 and 3 of networkx.
    # Cf https://networkx.org/documentation/stable/release/migration_guide_from_2.x_to_3.0.html
    nx_version = version("networkx")
    if nx_version.startswith("2."):
        pass
        # nx.read_gpickle(graph, output, protocol=5)
    elif nx_version.startswith("3."):
        pass
        # with open(output, "wb") as f:
        #     pickle.load(graph, f, pickle.HIGHEST_PROTOCOL)
    else:
        err = (
            f"Unsupported networkx version ({nx_version}). "
            "Version 2.x or 3.x is required."
        )
        raise RuntimeError(err)

    p_time = time.process_time() - start
    print(f"...done in {(p_time // 60):.0f} min {(p_time % 60):.2f} s.")
    # print(
    #     f'{len(graphs)} track{"s have" if len(graphs) > 1 else " has"}'
    #     f" been exported."
    # )

    # XML_reader.write_TrackMate_XML(graphs, xml_out)
