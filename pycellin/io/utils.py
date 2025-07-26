import warnings
from typing import Any

import networkx as nx

from pycellin.classes import CellLineage, Model


def check_fusions(model: Model) -> None:
    """
    Check if the model contains fusions and issue a warning if so.

    Parameters
    ----------
    model : Model
        The pycellin model to check for fusions.

    Returns
    -------
    None
    """
    all_fusions = model.get_fusions()
    if all_fusions:
        # TODO: link toward correct documentation when it is written.
        fusion_warning = (
            f"Unsupported data, {len(all_fusions)} cell fusions detected. "
            "It is advised to deal with them before any other processing, "
            "especially for tracking related features. Crashes and incorrect "
            "results can occur. See documentation for more details."
        )
        warnings.warn(fusion_warning)


def _add_lineages_features(
    lineages: list[CellLineage],
    lin_features: list[dict[str, Any]],
    lineage_ID_key: str | None = "lineage_ID",
) -> None:
    """
    Update each CellLineage in the list with corresponding lineage features.

    This function iterates over a list of CellLineage objects,
    attempting to match each lineage with its corresponding lineage
    features based on the 'lineage_ID_key' feature present in the
    lineage nodes. It then updates the lineage graph with these
    attributes.

    Parameters
    ----------
    lineages : list[CellLineage]
        A list of the lineages to update.
    lin_features : list[dict[str, Any]]
        A list of dictionaries, where each dictionary contains features
        for a specific lineage, identified by a the given 'lineage_ID_key' key.
    lineage_ID_key : str | None, optional
        The key used to identify the lineage in the attributes.

    Raises
    ------
    ValueError
        If a lineage is found to contain nodes with multiple distinct
        'lineage_ID_key' values, indicating an inconsistency in lineage ID
        assignment.
    """
    for lin in lineages:
        # Finding the dict of features matching the lineage.
        tmp = set(t_id for _, t_id in lin.nodes(data=lineage_ID_key))

        if not tmp:
            # 'tmp' is empty because there's no nodes in the current graph.
            # Even if it can't be updated, we still want to return this graph.
            continue
        elif tmp == {None}:
            # Happens when all the nodes do not have a 'lineage_ID_key' feature.
            continue
        elif None in tmp:
            # Happens when at least one node does not have a 'lineage_ID_key'
            # feature, so we clean 'tmp' and carry on.
            tmp.remove(None)
        elif len(tmp) != 1:
            raise ValueError("Impossible state: several IDs for one lineage.")

        current_lineage_id = list(tmp)[0]
        current_lineage_attr = [
            d_attr
            for d_attr in lin_features
            if d_attr[lineage_ID_key] == current_lineage_id
        ][0]

        # Adding the features to the lineage.
        for k, v in current_lineage_attr.items():
            lin.graph[k] = v


def _split_graph_into_lineages(
    graph: nx.DiGraph,
    lin_features: list[dict[str, Any]] | None = None,
    lineage_ID_key: str | None = "lineage_ID",
) -> list[CellLineage]:
    """
    Split a graph into several subgraphs, each representing a lineage.

    Parameters
    ----------
    lineage : nx.DiGraph
        The graph to split.
    lin_features : list[dict[str, Any]] | None
        A list of dictionaries, where each dictionary contains TrackMate
        attributes for a specific track, identified by a 'TRACK_ID' key.
        If None, no attributes will be added to the lineages.

    Returns
    -------
    list[CellLineage]
        A list of subgraphs, each representing a lineage.
    """
    # One subgraph is created per lineage, so each subgraph is
    # a connected component of `graph`.
    lineages = [
        CellLineage(graph.subgraph(c).copy())
        for c in nx.weakly_connected_components(graph)
    ]
    del graph  # Redondant with the subgraphs.
    if not lin_features:
        # We need to create and add a lineage_ID key to each lineage.
        for i, lin in enumerate(lineages):
            lin.graph["lineage_ID"] = i
    else:
        # Adding lineage features to each lineage.
        try:
            _add_lineages_features(lineages, lin_features, lineage_ID_key)
        except ValueError as err:
            print(err)
            # The program is in an impossible state so we need to stop.
            raise

    return lineages


def _update_node_feature_key(
    lineage: CellLineage,
    old_key: str,
    new_key: str,
) -> None:
    """
    Update the key of a feature in all the nodes of a lineage.

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    old_key : str
        The old key of the feature.
    new_key : str
        The new key of the feature.
    """
    for node in lineage.nodes:
        if old_key in lineage.nodes[node]:
            lineage.nodes[node][new_key] = lineage.nodes[node].pop(old_key)


def _update_lineage_feature_key(
    lineage: CellLineage,
    old_key: str,
    new_key: str,
) -> None:
    """
    Update the key of a feature in the graph of a lineage.

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    old_key : str
        The old key of the feature.
    new_key : str
        The new key of the feature.
    """
    if old_key in lineage.graph:
        lineage.graph[new_key] = lineage.graph.pop(old_key)


def _update_lineage_ID_key(
    lineage: CellLineage,
    lineage_ID_key: str,
    available_ID: int | None = None,
) -> int | None:
    """
    Update the lineage ID key in the lineage graph to match pycellin convention.

    In the case of a one-node lineage, it is possible that the lineage does not have
    a key to identify it. So we define the lineage_ID as minus the node ID.
    That way, it is easy to discriminate between one-node lineages
    (negative IDs) and multi-nodes lineages (positive IDs).

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    lineage_ID_key : str
        The key that is the lineage identifier in the lineage graph.
    available_ID : int | None, optional
        The next available lineage ID to use if the lineage does not have one.

    Returns
    -------
    int | None
        The lineage ID if it was created, or None if it was already present.

    Raises
    ------
    TypeError
        If the lineage is a multi-node lineage and no available_ID is provided.
    """
    try:
        # If the lineage has a lineage_ID_key, we rename it to "lineage_ID".
        # This is the key used by pycellin to identify lineages.
        lineage.graph["lineage_ID"] = lineage.graph.pop(lineage_ID_key)
        return None
    except KeyError:
        if len(lineage) == 1:
            # If the lineage has only one node, we set the lineage ID to minus the node ID.
            # This is a convention used by pycellin to identify one-node lineages.
            node = list(lineage.nodes)[0]
            lineage.graph["lineage_ID"] = -node
            return -node
        else:
            # If the lineage does not have a lineage_ID_key, we create it.
            # We set the ID of a multi-node lineage to the next available lineage ID.
            if available_ID is None:
                raise TypeError(
                    "Missing available_ID argument for multi-node lineage "
                    f"with no {lineage_ID_key} key."
                )
            lineage.graph["lineage_ID"] = available_ID
            return available_ID
