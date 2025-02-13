#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A collection of diverse morphology features that can be added to 
lineage graphs.
"""

from itertools import product, combinations
from operator import itemgetter

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely.geometry import Point, LineString
from skimage.morphology import skeletonize

from pycellin.classes.lineage import CellLineage
from pycellin.classes.feature_calculator import NodeLocalFeatureCalculator

# TODO:
# - remove debug code
# - always return a value even if weird skeleton shape (but put a warning in that case)
# - separate width and length. Width only requires skeleton length and the distance
# transform so I should compute the skeleton in a separate function.
# - recode every thing and avoid drawing
# - move area_increment to a notebook as an example of custom feature


def from_roi_to_array(roi, width, height):
    # Actual drawing of the object and conversion to a numpy array.
    img = Image.new("L", (width, height), "black")
    img_draw = ImageDraw.Draw(img)
    img_draw.polygon(roi, fill="white")
    img = np.asarray(img, dtype=np.uint8)
    # We need a binary array to correctly compute the length.
    if not img.flags["WRITEABLE"]:
        img = img.copy()
    img[img > 0] = 1
    return img


def adjacent_pixels(img, pixel):
    i, j = pixel
    adj_px = []
    for k, l in product(range(i - 1, i + 2), range(j - 1, j + 2)):
        if k == i and l == j:
            continue
        # if k >= img.shape[1] or l >= img.shape[0]:

        try:
            if img[k, l] != 0:
                adj_px.append((k, l))
        except IndexError:
            # If current pixel is on the border of the image, there can't be
            # adjacency on the border side.
            continue
    return adj_px


def prune_skel(adjacency_dict):
    # We only want to keep the main skeleton which is the longest path
    # of the graph. To find it, we are looking for the longest shortest
    # path between 2 extremities of the graph. For this, we switch to
    # a graph representation of the skeleton to ease the path research.
    skel_graph = nx.from_dict_of_lists(adjacency_dict)
    longest_path = []
    tip_px = [px for px, list_px in adjacency_dict.items() if len(list_px) == 1]
    for n1, n2 in combinations(tip_px, 2):
        tmp_path = nx.shortest_path(skel_graph, n1, n2)
        if len(tmp_path) > len(longest_path):
            longest_path = tmp_path
    # Returning the adjacency_dict: now it contains only main skeleton pix.
    return nx.to_dict_of_lists(skel_graph, nodelist=longest_path)


def from_skel_to_path(adjacency_dict, first_px):
    # Ordering the skeleton pixels by following along the skeleton,
    # from one tip to another.
    path = [first_px]
    current_px = adjacency_dict[first_px][0]
    path.append(current_px)
    # print(current_px)
    while current_px in adjacency_dict:
        candidates = adjacency_dict[current_px]
        candidates.remove(path[-2])  # The pixel we're coming from.
        # print(candidates)
        if not candidates:  # There is no more pixel: we've reached a tip.
            break
        assert len(candidates) == 1
        current_px = candidates[0]
        path.append(current_px)
    return path


def from_path_to_line(path, tol):
    # Creation of a geometrical line out of the skeleton path.
    line = LineString([Point((x, y)) for (y, x) in path])
    # To get a better approximation of the object lenght, we simplify
    # the skeleton line.
    simplified_line = line.simplify(tol, preserve_topology=True)
    return simplified_line


def get_width_and_length(
    noi: int,
    lineage: CellLineage,
    pixel_size: float,
    skel_algo: str = "zhang",
    tolerance: float = 0.5,
    method_width: str = "mean",
    width_ignore_tips: bool = False,
    debug: bool = False,
    debug_folder: str | None = None,
) -> tuple[int, int]:
    """
    Compute the width and length of the ROI associated with a node.

    Parameters
    ----------
    noi : int
        Node ID (cell_ID) of the cell of interest.
    lineage : CellLineage
        Lineage graph containing the node of interest.
    pixel_size : float
        Pixel size in micrometer.
    skel_algo : str, optional
        'zhang' or 'lee', by default 'zhang'.
    tolerance : float, optional
        Tolerance distance for shape simplification (0-1).
        The higher the tolerance, the more simplified the line will be.
        By default 0.5.
    method_width : str, optional
        Method to compute width along skeleton: min, max, mean or median.
        By default mean.
    width_ignore_tips : bool, optional
        True to ignore the skeleton tips while computing width, by default False.
    debug : bool, optional
        True to activate debug behavior, by default False.
    debug_folder : Optional[str], optional
        Folder in which to save the debug graphs, by default None.

    Returns
    -------
    tuple[int, int]
        Width and length of the ROI.
    """
    if debug:
        print("NODE", noi)
        if skel_algo == "zhang":
            not_skel_algo = "lee"
        elif skel_algo == "lee":
            not_skel_algo = "zhang"

    # First we need to reconstruct the image of the object we are working on.
    # This is done by drawing and filling a polygon defined by the points
    # in the ROI list.
    roi = lineage.nodes[noi]["ROI_coords"]
    # The coordinates extracted from the graph are in microns, not in pixels.
    # roi = [(int(x * x_resolution), int(y * x_resolution)) for (x, y) in roi]
    roi = [(int(x * 1 / pixel_size), int(y * 1 / pixel_size)) for (x, y) in roi]

    # Here, ROIs coordinates are given in relation to each ROI center,
    # not to the top left corner of the image.
    # But we don't care about the position of the pixels in the image,
    # we only care about their relative position to each other.
    # So we create an image just small enough to hold the object.
    x_min = min(roi, key=itemgetter(0))[0]
    x_max = max(roi, key=itemgetter(0))[0]
    y_min = min(roi, key=itemgetter(1))[1]
    y_max = max(roi, key=itemgetter(1))[1]
    # We add 4 pixels so that the object does not touch the border of
    # the image (otherwise it might create skeleton artefacts).
    img_width = x_max - x_min + 1 + 4
    img_height = y_max - y_min + 1 + 4
    # Placing the object in the center of the image.
    roi = [(x - x_min + 2, y - y_min + 2) for (x, y) in roi]
    img = from_roi_to_array(roi, img_width, img_height)

    if debug:
        fig, ax = plt.subplots(nrows=2, ncols=3, sharex=True, sharey=True, dpi=400)
        ax[0, 0].imshow(img, cmap="gray")
        ax[0, 0].set_aspect("equal")
        ax[0, 0].axis("off")
        ax[0, 0].set_title(f"ROI node {noi}", fontsize=6)

    # Now that we have a numpy array modelling our object, we can compute
    # its distance transform and its skeleton.
    distance = ndi.distance_transform_edt(img)
    skel = skeletonize(img, method=skel_algo)
    # Distance transform but only for the pixels of the skeleton.
    dist_on_skel = distance * skel
    if debug:
        ax[0, 1].imshow(dist_on_skel, cmap="magma")
        ax[0, 1].contour(img, [0.5], colors="w")
        ax[0, 1].axis("off")
        ax[0, 1].set_title(f"Skeleton {skel_algo.capitalize()}", fontsize=6)

        skel2 = skeletonize(img, method=not_skel_algo)
        dist_on_skel2 = distance * skel2
        ax[1, 1].imshow(dist_on_skel2, cmap="magma")
        ax[1, 1].contour(img, [0.5], colors="w")
        ax[1, 1].axis("off")
        ax[1, 1].set_title(f"Skeleton {not_skel_algo.capitalize()}", fontsize=6)

    # The next step is to create a simple path out of the skeleton, then to
    # simplify the associated curve to compute an approximation of the
    # width and length of the object.
    # Building a pixel adjacency dictionary in which keys are the coordinates
    # of non zero pixels, and values are the coordinates of pixels adjacent
    # to the key pixel (using an 8-connectivity).
    adjacency_dict = {}
    pixels_i, pixels_j = np.nonzero(skel)
    pruning = False
    for i, j in zip(pixels_i, pixels_j):
        adj_px = adjacent_pixels(skel, (i, j))
        connectivity = len(adj_px)
        if connectivity > 2:
            # There is a side branching so we will need to prune it later
            # so as to only keep the main skeleton.
            pruning = True
        adjacency_dict[(i, j)] = adj_px

    if pruning:
        # We only want to keep the main skeleton which is the longest path
        # of the graph so we need to prune the side branches.
        if debug:
            print("PRUNING")
            print(adjacency_dict)
            # print(len(adjacency_dict))
        adjacency_dict = prune_skel(adjacency_dict)
        if debug:
            print(adjacency_dict)
            # print(len(adjacency_dict))

    # Tips of the skeleton = pixels connected to only 1 pixel.
    tip_px = [px for px, list_px in adjacency_dict.items() if len(list_px) == 1]
    if len(adjacency_dict) == 1:
        # There is only one pixel in the skeleton. The object being processed
        # is probably roundish. The method for mesuring length is not
        # adapted to this kind of morphology.
        try:
            track_ID = lineage.nodes[noi]["TRACK_ID"]
        except KeyError:
            print(
                f"WARNING: One pixel skeleton on node {noi}! "
                f"The object is probably roundish and the radius "
                f"is a better metric in that case. Setting the length and "
                f"width to NaN."
            )
        else:
            print(
                f"WARNING: One pixel skeleton on node {noi} of track "
                f"{track_ID}! The object is probably roundish and the radius"
                f" is a better metric in that case. Setting the length and "
                f"width to NaN."
            )
        length = np.NaN
        width = np.NaN
    elif len(adjacency_dict) == 0 or len(tip_px) == 0:
        # The skeleton is a loop!! The object being processed is
        # probably roundish. The method for mesuring length is not adapted to
        # this kind of morphology.
        try:
            track_ID = lineage.nodes[noi]["TRACK_ID"]
        except KeyError:
            print(
                f"WARNING: One pixel skeleton on node {noi}! "
                f"The object is probably roundish and the radius "
                f"is a better metric in that case. Setting the length and "
                f"width to NaN."
            )
        else:
            print(
                f"WARNING: Circular skeleton on node {noi} of track "
                f"{track_ID}! The object is probably roundish and the radius "
                f"is a better metric in that case. Setting the length and "
                f"width to NaN."
            )
        length = np.NaN
        width = np.NaN
    else:
        # Ordering the skeleton pixels by following along the skeleton,
        # from one tip to another.
        # The skeleton has been pruned so there should be only 2 tips.
        assert len(tip_px) == 2
        path = from_skel_to_path(adjacency_dict, tip_px[0])
        if debug:
            points = [Point((x, y)) for (y, x) in path]
            xs = [point.x for point in points]
            ys = [point.y for point in points]
            ax[0, 2].scatter(xs, ys, color="red", s=20)
            ax[0, 2].invert_yaxis()
            ax[0, 2].set_aspect("equal")
            ax[0, 2].axis("off")

        # Simplification of the path.
        line = from_path_to_line(path, tolerance)
        if debug:
            ax[0, 2].scatter(*line.xy, color="purple", marker="x", s=10)
            ax[0, 2].plot(*line.xy, color="purple")
            ax[0, 2].contour(img, [0.5], colors="b")
            ax[0, 2].set_title(
                f"Pruned skeleton {skel_algo.capitalize()}" f"\n+ simplified line",
                fontsize=6,
            )

        length = line.length
        for px in tip_px:
            # We need to add the distance from each tip of the skeleton to the
            # object border, as given by the distance map.
            # print(dist_on_skel[px])
            length += dist_on_skel[px]

        if debug:
            # Doing the same steps as above but for the other skeleton algo.
            adjacency_dict2 = {}
            pixels_i2, pixels_j2 = np.nonzero(skel2)
            pruning2 = False
            for i, j in zip(pixels_i2, pixels_j2):
                adj_px2 = adjacent_pixels(skel2, (i, j))
                connectivity2 = len(adj_px2)
                if connectivity2 > 2:
                    pruning2 = True
                adjacency_dict2[(i, j)] = adj_px2
            if pruning2:
                adjacency_dict2 = prune_skel(adjacency_dict2)
            tip_px2 = [
                px for px, list_px in adjacency_dict2.items() if len(list_px) == 1
            ]
            path2 = from_skel_to_path(adjacency_dict2, tip_px2[0])
            points2 = [Point((x, y)) for (y, x) in path2]
            xs = [point.x for point in points2]
            ys = [point.y for point in points2]
            ax[1, 2].scatter(xs, ys, color="red", s=20)
            ax[1, 2].invert_yaxis()
            ax[1, 2].set_aspect("equal")
            ax[1, 2].axis("off")
            line2 = from_path_to_line(path2, tolerance)
            ax[1, 2].scatter(*line2.xy, color="purple", marker="x", s=10)
            ax[1, 2].plot(*line2.xy, color="purple")
            ax[1, 2].contour(img, [0.5], colors="b")
            ax[1, 2].set_title(
                f"Pruned skeleton {not_skel_algo.capitalize()}" f"\n+ simplified line",
                fontsize=6,
            )
            length2 = line2.length
            for px in tip_px2:
                length2 += dist_on_skel2[px]

        if width_ignore_tips:
            if len(dist_on_skel[dist_on_skel > 0]) >= 3:
                # We remove the tips of the skeleton only when there are
                # at least 3 pixels in the skeleton.
                for px in tip_px:
                    dist_on_skel[px] = 0
        # We are only interested in the distance map of the skeleton
        # so we discard the rest.
        dist_on_skel = dist_on_skel[dist_on_skel > 0]

        if method_width == "mean":
            # Width: averaging the distance transform along skeleton.
            width = (np.sum(dist_on_skel) / len(dist_on_skel)) * 2 - 1
        elif method_width == "median":
            # Width: median distance transform along skeleton.
            width = np.median(dist_on_skel) * 2 - 1
        elif method_width == "max":
            # Width: max distance transform along skeleton.
            # TODO: see how to deal with this case, maybe put it in the ignore_tips?
            if len(dist_on_skel) == 0:
                width = np.NaN
            else:
                width = np.max(dist_on_skel) * 2 - 1
        elif method_width == "min":
            # Width: min distance transform along skeleton.
            if len(dist_on_skel) == 0:
                width = np.NaN
            else:
                width = np.min(dist_on_skel) * 2 - 1
        else:
            print("Wrong width method. Should be one of: min, max, mean, median.")
            # TODO: raise an error when method is not supported

        if debug:
            print(f"Width: {width:.2f} px i.e. {width*pixel_size:.2f} μm.")
            print(f"Length: {length:.2f} px i.e. {length*pixel_size:.2f} μm.\n")

            txt = (
                f'Length: {length*pixel_size:.2f} μm\n{" "*10}i.e. {length:.2f} px'
                f'\nWidth: {width*pixel_size:.2f} μm\n{" "*10}i.e. {width:.2f} px'
            )
            ax[0, 2].annotate(
                txt,
                xy=(0, 0),
                xycoords="figure fraction",
                xytext=(1, 0.5),
                textcoords="axes fraction",
                size=4,
                horizontalalignment="left",
                verticalalignment="top",
            )

            width2 = (np.sum(dist_on_skel2) / len(pixels_i2)) * 2 - 1
            txt2 = (
                f'Length: {length2*pixel_size:.2f} μm\n{" "*10}i.e. {length2:.2f} px'
                f'\nWidth: {width2*pixel_size:.2f} μm\n{" "*10}i.e. {width2:.2f} px'
            )
            ax[1, 2].annotate(
                txt2,
                xy=(0, 0),
                xycoords="figure fraction",
                xytext=(1, 0.4),
                textcoords="axes fraction",
                size=4,
                horizontalalignment="left",
                verticalalignment="top",
            )

            ax[1, 0].remove()
            plt.show()
            lin_id = lineage.nodes[noi]["lineage_ID"]
            file = f"{debug_folder}/Lineage{lin_id}_Node{noi}_{skel_algo}"
            plt.savefig(file)
            plt.close()

    length *= pixel_size
    width *= pixel_size

    return width, length


class CellWidth(NodeLocalFeatureCalculator):
    def __init__(
        self,
        feature,
        pixel_size: float,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
        debug: bool = False,
        debug_folder: str | None = None,
    ):
        super().__init__(feature)
        self.pixel_size = pixel_size
        self.skel_algo = skel_algo
        self.tolerance = tolerance
        self.method_width = method_width
        self.width_ignore_tips = width_ignore_tips
        self.debug = debug
        self.debug_folder = debug_folder

    def compute(self, lineage: CellLineage, noi: int) -> float:
        return get_width_and_length(
            noi,
            lineage,
            self.pixel_size,
            self.skel_algo,
            self.tolerance,
            self.method_width,
            self.width_ignore_tips,
            self.debug,
            self.debug_folder,
        )[0]


class CellLength(NodeLocalFeatureCalculator):
    def __init__(
        self,
        feature,
        pixel_size: float,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
        debug: bool = False,
        debug_folder: str | None = None,
    ):
        super().__init__(feature)
        self.pixel_size = pixel_size
        self.skel_algo = skel_algo
        self.tolerance = tolerance
        self.method_width = method_width
        self.width_ignore_tips = width_ignore_tips
        self.debug = debug
        self.debug_folder = debug_folder

    def compute(self, lineage: CellLineage, noi: int) -> float:
        return get_width_and_length(
            noi,
            lineage,
            self.pixel_size,
            self.skel_algo,
            self.tolerance,
            self.method_width,
            self.width_ignore_tips,
            self.debug,
            self.debug_folder,
        )[1]


# TODO: this is a feature that should not be in Pycellin, too many ways to define
# the area increment. Since it is user dependent, I should put it in a notebook
# as an example of custom feature.

# def get_area_increment(noi: int, lineage: CellLineage) -> float:
#     """
#     Compute the area increment of a node.

#     Parameters
#     ----------
#     noi : int
#         Node ID (cell_ID) of the cell of interest.
#     lineage : CellLineage
#         Lineage graph containing the node of interest.

#     Returns
#     -------
#     float
#         Area increment of the node.
#     """
#     # TODO: rework: name/definition is not intuitive.
#     # Why specifically between t and t-1? And not t and t+1?
#     # Should give 2 nodes as input and compute the area increment between them.
#     # Or add a parameter to specify if t-1 or t+1.
#     # Area of node at t minus area at t-1.
#     predecessors = list(lineage.predecessors(noi))
#     if len(predecessors) == 0:
#         return np.NaN
#     else:
#         err_mes = (
#             f'Node {noi} in track {lineage.graph["name"]} has multiple predecessors.'
#         )
#         assert len(predecessors) == 1, err_mes
#         # print(predecessors)
#         return lineage.nodes[noi]["AREA"] - lineage.nodes[predecessors[0]]["AREA"]


# def _add_area_increment(lineages: list[CellLineage]) -> None:
#     """
#     Add the area increment feature to the nodes of the lineages.

#     Parameters
#     ----------
#     lineages : list[CellLineage]
#         Cell lineages to update with the area increment feature.
#     """
#     for lin in lineages:
#         for node in lin.nodes:
#             lin.nodes[node]["AREA_INCREMENT"] = get_area_increment(node, lin)


if __name__ == "__main__":

    import itertools
    import math
    from shapely.geometry import Polygon
    from pycellin.io.trackmate import load_TrackMate_XML

    xml = "sample_data/FakeTracks.xml"

    model = load_TrackMate_XML(xml, keep_all_spots=True, keep_all_tracks=True)
    lineage = model.data.cell_data[0]
    # print(lineage.nodes[2004]["ROI_coords"])
    node = 2035
    print(lineage.nodes[node]["area"])

    # Shapely
    roi = Polygon(lineage.nodes[node]["ROI_coords"])
    print(roi.area)

    # Shoelace formula
    vertices = lineage.nodes[node]["ROI_coords"]
    border = vertices + [vertices[0]]
    area = sum(
        [p1[0] * p2[1] - p1[1] * p2[0] for (p1, p2) in itertools.pairwise(border)]
    )
    print(abs(area) / 2)

    # Perimeter shapely vs by hand
    print(roi.length)
    print(sum([math.dist(p1, p2) for (p1, p2) in itertools.pairwise(border)]))

    # print(lineage.nodes[node]["location"])
    # print(roi.centroid)
