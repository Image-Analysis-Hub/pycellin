#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Create a TrackMate compatible XML file from networkX directed graphs.
"""


import argparse
from pathlib import Path
import time

from xml_utils import read_settings, write_TrackMate_XML
from pycellin.graph.io import load_graph

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
        help=("filename for the xml output"),
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
        graphs = [load_graph(input)]

    # if args.header:
    #     header = XML_reader.read_header(args.header)
    # if args.settings:
    #     settings = XML_reader.read_settings(args.settings)

    # The settings we get below are needed. Without them, TM crashes when
    # opening the xml.
    # The other settings (like display settings) as well as the header
    # are not mandatory. So for the time being I'm just ignoring them.
    settings = read_settings(args.input_xml)
    write_TrackMate_XML(graphs, settings, args.output)

    p_time = time.process_time() - start
    print(f"...done in {(p_time // 60):.0f} min {(p_time % 60):.2f} s.")
    print(
        f'{len(graphs)} graph{"s have" if len(graphs) > 1 else " has"}'
        f" been exported in a TrackMate xml file."
    )
