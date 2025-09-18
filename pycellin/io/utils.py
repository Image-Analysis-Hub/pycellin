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
            "especially for tracking related properties. Crashes and incorrect "
            "results can occur. See documentation for more details."
        )
        warnings.warn(fusion_warning)


def _add_lineage_props(
    lineages: list[CellLineage],
    lin_props: list[dict[str, Any]],
    lineage_ID_key: str | None = "lineage_ID",
) -> None:
    """
    Update each CellLineage in the list with corresponding lineage properties.

    This function iterates over a list of CellLineage objects,
    attempting to match each lineage with its corresponding lineage
    properties based on the 'lineage_ID_key' property present in the
    lineage nodes. It then updates the lineage graph with these
    attributes.

    Parameters
    ----------
    lineages : list[CellLineage]
        A list of the lineages to update.
    lin_props : list[dict[str, Any]]
        A list of dictionaries, where each dictionary contains properties
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
        # Finding the dict of properties matching the lineage.
        tmp = set(t_id for _, t_id in lin.nodes(data=lineage_ID_key))

        if not tmp:
            # 'tmp' is empty because there's no nodes in the current graph.
            # Even if it can't be updated, we still want to return this graph.
            continue
        elif tmp == {None}:
            # Happens when all the nodes do not have a 'lineage_ID_key' property.
            continue
        elif None in tmp:
            # Happens when at least one node does not have a 'lineage_ID_key'
            # property, so we clean 'tmp' and carry on.
            tmp.remove(None)
        elif len(tmp) != 1:
            raise ValueError("Impossible state: several IDs for one lineage.")

        current_lineage_id = list(tmp)[0]
        current_lineage_attr = [
            d_attr for d_attr in lin_props if d_attr[lineage_ID_key] == current_lineage_id
        ][0]

        # Adding the properties to the lineage.
        for k, v in current_lineage_attr.items():
            lin.graph[k] = v


def _split_graph_into_lineages(
    graph: nx.Graph | nx.DiGraph,
    lin_props: list[dict[str, Any]] | None = None,
    lineage_ID_key: str | None = "lineage_ID",
) -> list[CellLineage]:
    """
    Split a graph into several subgraphs, each representing a lineage.

    Parameters
    ----------
    lineage : nx.DiGraph
        The graph to split.
    lin_props : list[dict[str, Any]] | None
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
        CellLineage(graph.subgraph(c).copy()) for c in nx.weakly_connected_components(graph)
    ]
    del graph  # Redondant with the subgraphs.
    if not lin_props:
        # We need to create and add a lineage_ID key to each lineage.
        for i, lin in enumerate(lineages):
            lin.graph["lineage_ID"] = i
    else:
        # Adding lineage properties to each lineage.
        try:
            _add_lineage_props(lineages, lin_props, lineage_ID_key)
        except ValueError as err:
            print(err)
            # The program is in an impossible state so we need to stop.
            raise

    return lineages


def _update_node_prop_key(
    lineage: CellLineage,
    old_key: str,
    new_key: str,
    enforce_old_key_existence: bool = False,
    set_default_if_missing: bool = False,
    default_value: Any | None = None,
) -> None:
    """
    Update the key of a property in all the nodes of a lineage.

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    old_key : str
        The old key of the property.
    new_key : str
        The new key of the property.
    enforce_old_key_existence : bool, optional
        If True, raises an error when the old key does not exist in a node.
        If False, the function will skip nodes that do not have the old key.
        Defaults to False.
    set_default_if_missing : bool, optional
        If True, set the new key to `default_value` when the old key does not exist.
        If False, the new key will not be set when the old key does not exist.
        Defaults to False.
    default_value : Any | None, optional
        The default value to set if the old key does not exist
        and set_default_if_missing is True. Defaults to None.

    Raises
    ------
    ValueError
        If enforce_old_key_existence is True and the old key does not exist
        in a node.
    """
    for node in lineage.nodes:
        if old_key in lineage.nodes[node]:
            lineage.nodes[node][new_key] = lineage.nodes[node].pop(old_key)
        else:
            if enforce_old_key_existence:
                raise ValueError(f"Node {node} does not have the required key '{old_key}'.")
            if set_default_if_missing:
                lineage.nodes[node][new_key] = default_value


def _update_lineage_prop_key(
    lineage: CellLineage,
    old_key: str,
    new_key: str,
) -> None:
    """
    Update the key of a property in the graph of a lineage.

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    old_key : str
        The old key of the property.
    new_key : str
        The new key of the property.
    """
    if old_key in lineage.graph:
        lineage.graph[new_key] = lineage.graph.pop(old_key)


def _update_lineages_IDs_key(
    lineages: list[CellLineage],
    lineage_ID_key: str | None,
) -> None:
    """
    Update the lineage ID key of lineage graphs to match pycellin convention.

    In the case of a one-node lineage, it is possible that the lineage does not have
    a key to identify it. So we define the lineage_ID as minus the node ID.
    That way, it is easy to discriminate between one-node lineages
    (negative IDs) and multi-nodes lineages (positive IDs).
    If the lineage_ID_key is not present in the lineage graph, a "lineage_ID" key
    is created and set to the next available lineage ID.

    Parameters
    ----------
    lineages : list[CellLineage]
        The lineages to update.
    lineage_ID_key : str | None
        The key that is the lineage identifier in lineage graphs.
    """
    ids = [lin.graph[lineage_ID_key] for lin in lineages if lineage_ID_key in lin.graph]
    next_id = max(ids) + 1 if ids else 0

    for lin in lineages:
        try:
            lin.graph["lineage_ID"] = lin.graph.pop(lineage_ID_key)
        except KeyError:
            if len(lin) == 1:
                node = list(lin.nodes)[0]
                lin.graph["lineage_ID"] = -node
            else:
                lin.graph["lineage_ID"] = next_id
                next_id += 1
