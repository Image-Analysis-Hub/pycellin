#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
exporter.py

References:
- geff GitHub: https://github.com/live-image-tracking-tools/geff
- geff Documentation: https://live-image-tracking-tools.github.io/geff/latest/
"""

import geff


if __name__ == "__main__":
    # xml_in = "sample_data/Ecoli_growth_on_agar_pad.xml"
    # xml_in = "sample_data/FakeTracks.xml"
    ctc_in = "sample_data/FakeTracks_TMtoCTC.txt"
    # ctc_in = "sample_data/Ecoli_growth_on_agar_pad_TMtoCTC.txt"
    geff_out = "C:/Users/lxenard/Documents/Janelia_Cell_Trackathon/test_pycellin_geff/test.zarr"

    from pycellin.io.trackmate.loader import load_TrackMate_XML
    from pycellin.io.cell_tracking_challenge.loader import load_CTC_file

    # model = load_TrackMate_XML(xml_in)
    # model.remove_feature("ROI_coords")
    model = load_CTC_file(ctc_in)
    print(model)
    print(model.get_cell_lineage_features().keys())
    print(model.data.cell_data.keys())
    lin1 = model.data.cell_data[1]
    print(lin1)
    print(lin1.nodes[77])
    # lin4 = model.data.cell_data[4]
    # print(lin4)

    geff.write_nx(
        model.data.cell_data[1],
        # model.data.cell_data[4],
        geff_out,
        # axis_names=["cell_x", "cell_y", "cell_z", "frame"],
        # axis_units=["um", "um", "um", "s"],
        # zarr_format=2,
    )
