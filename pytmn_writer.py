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


def load_graph(path: Path) -> nx.DiGraph:
    # Small change of API between version 2 and 3 of networkx.
    # Cf https://networkx.org/documentation/stable/release/migration_guide_from_2.x_to_3.0.html
    nx_version = version("networkx")
    if nx_version.startswith("2."):
        graph = nx.read_gpickle(path)
    elif nx_version.startswith("3."):
        with open(path, "rb") as file:
            graph = pickle.load(file)
    else:
        err = (
            f"Unsupported networkx version ({nx_version}). "
            "Version 2.x or 3.x is required."
        )
        raise RuntimeError(err)
    return graph


if __name__ == "__main__":
    start = time.process_time()
    print("Starting conversion...")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input_graph",
        help=("gpickle (.gz) file to process, or folder holding the .gz"),
    )
    parser.add_argument(
        "input_xml",
        help=("original xml file to get its settings"),
    )
    parser.add_argument(
        "output",
        help=(""),
    )
    # parser.add_argument(
    #     "--header",
    #     dest="header",
    #     action="store",
    #     help=("original xml file to get its header"),
    # )
    # parser.add_argument(
    #     "--settings",
    #     dest="settings",
    #     action="store",
    #     help=("original xml file to get its settings"),
    # )

    args = parser.parse_args()

    input = Path(args.input_graph)
    if input.is_dir():
        # Loading all the gz files in the directory.
        graphs = []
        for file in input.glob("*.gz"):
            graphs.append(load_graph(file))
    else:
        # Only one .gz to load.
        try:
            graph = load_graph(input)
        except RuntimeError as err:
            print(err)
        graphs = [graph]
    print(len(graphs))

    # if args.header:
    #     header = XML_reader.read_header(args.header)
    # if args.settings:
    #     settings = XML_reader.read_settings(args.settings)

    # The settings we get below are needed. Without them, TM crashes when
    # opening the xml.
    # The other settings (like display settings) as well as the header
    # are not mandatory.
    settings = XML_reader.read_settings(args.input_xml)
    XML_writer.write_TrackMate_XML(graphs, settings, args.output)

    p_time = time.process_time() - start
    print(f"...done in {(p_time // 60):.0f} min {(p_time % 60):.2f} s.")
    print(
        f'{len(graphs)} graph{"s have" if len(graphs) > 1 else " has"}'
        f" been exported in a TrackMate xml file."
    )
