import logging
import numbers
from collections import Counter
from collections.abc import Iterable
from typing import Any

import networkx as nx

from pycellin.classes import CellLineage, Model
from pycellin.custom_types import PropertyType, _property_type_from_string
from pycellin.exceptions import UpdateRequiredError

logger = logging.getLogger(__name__)


def _check_fusions(model: Model) -> None:
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
        num = len(all_fusions)
        fusion_warning = (
            f"Unsupported data, {num} cell fusion{'s' if num > 1 else ''} detected. "
            "It is advised to deal with fusions before any other processing, "
            "especially for tracking related properties. Crashes and incorrect "
            "results can occur. Use model.get_fusions() to list them and "
            "model.remove_link() to correct them."
        )
        logger.warning(fusion_warning)


def _check_up_to_date(model: Model) -> None:
    """
    Check that a model to export doesn't require an update.

    Otherwise, the exported data would miss the changes not yet processed by
    `update()`, e.g. the split of a lineage after `remove_link()`, or the values of
    a property just added.

    Parameters
    ----------
    model : Model
        The model to export.

    Raises
    ------
    UpdateRequiredError
        If the model requires an update.
    """
    if model.is_update_required():
        raise UpdateRequiredError(
            "The model has changes that update() has not processed yet. "
            "Update it with model.update() before exporting it."
        )


def _add_lineage_props(
    lineages: list[CellLineage],
    lin_props: list[dict[str, Any]],
    lineage_id_key: str = "lineage_id",
) -> None:
    """
    Update each CellLineage in the list with corresponding lineage properties.

    This function iterates over a list of CellLineage objects,
    attempting to match each lineage with its corresponding lineage
    properties based on the 'lineage_id_key' property present in the
    lineage nodes. It then updates the lineage graph with these
    attributes.

    Parameters
    ----------
    lineages : list[CellLineage]
        A list of the lineages to update.
    lin_props : list[dict[str, Any]]
        A list of dictionaries, where each dictionary contains properties
        for a specific lineage, identified by a the given 'lineage_id_key' key.
    lineage_id_key : str, optional
        The key used to identify the lineage in the attributes.
        Defaults to "lineage_id".

    Raises
    ------
    ValueError
        If a lineage is found to contain nodes with multiple distinct
        'lineage_id_key' values, indicating an inconsistency in lineage ID
        assignment.

    Warns
    -----
    UserWarning
        If no lineage properties match a lineage ID, the lineage is skipped
        and a warning is issued. This commonly occurs for single-node tracks
        in TrackMate XML files, which don't have Track elements.
    """
    missing_lineage_ids = []

    for lin in lineages:
        # Finding the dict of properties matching the lineage.
        tmp = {t_id for _, t_id in lin.nodes(data=lineage_id_key)}

        if not tmp:
            # 'tmp' is empty because there's no nodes in the current graph.
            # Even if it can't be updated, we still want to return this graph.
            continue
        elif tmp == {None}:
            # Happens when all the nodes do not have a 'lineage_id_key' property.
            continue
        elif None in tmp:
            # Happens when at least one node does not have a 'lineage_id_key'
            # property, so we clean 'tmp' and carry on.
            tmp.remove(None)

        if len(tmp) != 1:
            raise ValueError("Impossible state: several IDs for one lineage.")

        current_lineage_id = next(iter(tmp))
        current_lineage_attr = next(
            (
                d_attr
                for d_attr in lin_props
                if d_attr.get(lineage_id_key) == current_lineage_id
            ),
            None,
        )
        if current_lineage_attr is None:
            missing_lineage_ids.append((current_lineage_id, len(lin)))
            continue

        # Adding the properties to the lineage.
        for k, v in current_lineage_attr.items():
            lin.graph[k] = v

    if missing_lineage_ids:
        details = "; ".join(
            f"lineage ID {lin_id!r} ({num_nodes} node{'' if num_nodes == 1 else 's'})"
            for lin_id, num_nodes in missing_lineage_ids
        )
        logger.info(
            f"No lineage properties found for: {details}. "
            f"These lineages will be skipped from lineage property assignment."
        )


def _identify_frame_prop(model: Model) -> str:
    """
    Identify a frame-like property in the model.

    This function checks if there is a frame-like property in the model's metadata.
    If not, it falls back to the 'timepoint' property.

    Parameters
    ----------
    model : Model
        The pycellin model to check for a frame-like property.

    Raises
    ------
    KeyError
        If neither a frame-like property nor 'timepoint' is present on all nodes.
    """
    # First, collect all frame-like properties from the metadata.
    candidates = []
    for prop in model.props_metadata._get_prop_dict_from_prop_type(
        PropertyType.NODE
    ).values():
        if prop.identifier.lower() == "frame":
            candidates.append(prop.identifier)

    # Check each candidate to see if it exists on all nodes in all lineages.
    frame_prop = None
    for candidate in candidates:
        has_prop = True
        for lin in model.data.cell_lineages.values():
            has_prop = _graph_has_node_prop(lin, candidate) and has_prop

        if has_prop:
            frame_prop = candidate
            break
        else:
            logger.info(
                f"Property '{candidate}' found in metadata but not present on all "
                "nodes. Trying next candidate or falling back to 'timepoint'."
            )

    # If no valid frame property found, fallback to "timepoint".
    if frame_prop is None:
        frame_prop = "timepoint"
        has_prop = True
        for lin in model.data.cell_lineages.values():
            has_prop = _graph_has_node_prop(lin, frame_prop) and has_prop

        if has_prop:
            logger.info(
                f"No valid frame-like property found. Falling back to '{frame_prop}'."
            )
        else:
            raise KeyError(
                "No valid frame-like property found. Tried candidates: "
                f"{candidates} and fallback 'timepoint'. "
            )

    return frame_prop


def _get_props_from_data(
    lineages: Iterable[nx.DiGraph],
) -> tuple[set[str], set[str], set[str]]:
    """
    Collect all property keys present in lineages.

    Parameters
    ----------
    lineages : Iterable[nx.DiGraph]
        The cell or cycle lineages to scan.

    Returns
    -------
    tuple[set[str], set[str], set[str]]
        Sets of node, edge, and lineage property keys found in the lineages.
    """
    node_props_data = set()
    edge_props_data = set()
    lineage_props_data = set()

    for lineage in lineages:
        for node in lineage.nodes:
            node_props_data.update(lineage.nodes[node].keys())
        for edge in lineage.edges:
            edge_props_data.update(lineage.edges[edge].keys())
        lineage_props_data.update(lineage.graph.keys())

    return node_props_data, edge_props_data, lineage_props_data


def _graph_has_node_prop(graph: nx.Graph, key: str) -> bool:
    """
    Check if all nodes in the graph have a specific property.

    Parameters
    ----------
    graph : nx.Graph
        The graph to check.
    key : str
        The name of the property to look for.

    Returns
    -------
    bool
        True if all nodes have the property, False otherwise.
    """
    return all(key in graph.nodes[node] for node in graph.nodes)


def _relabel_nodes_in_place(graph: nx.Graph, mapping: dict[int, int]) -> None:
    """
    Relabel the nodes of a graph in place, whatever their old and new IDs.

    NetworkX refuses to do it when old and new IDs form a loop, e.g. {0: 1, 1: 0}.
    Only then do the nodes go through temporary IDs. Doing it every time would make
    relabeling slower, and would change the order of the nodes when old and new IDs
    overlap without a loop, hence the autogenerated lineage IDs of a GEFF file.

    Parameters
    ----------
    graph : nx.Graph
        The graph to relabel.
    mapping : dict[int, int]
        The new ID of each node, as {old_id: new_id}.
    """
    try:
        nx.relabel_nodes(graph, mapping, copy=False)
    except nx.NetworkXUnfeasible:
        # NetworkX raises before changing anything in the graph.
        tmp_mapping = {old_id: ("__tmp__", i) for i, old_id in enumerate(mapping)}
        final_mapping = {
            ("__tmp__", i): new_id for i, new_id in enumerate(mapping.values())
        }
        nx.relabel_nodes(graph, tmp_mapping, copy=False)
        nx.relabel_nodes(graph, final_mapping, copy=False)


def _get_cycle_props_message(props: list[str]) -> str:
    """
    Return the warning about the cycle properties left out of an export.

    Parameters
    ----------
    props : list[str]
        The identifiers of the cycle properties left out, at least one.

    Returns
    -------
    str
        The warning, which also says how to export these properties.
    """
    plural = len(props) > 1
    return (
        f"Cycle propert{'ies are' if plural else 'y is'} not exported: "
        f"{', '.join(props)}. Use propagate_cycle_props=True to write "
        f"{'them' if plural else 'it'} on the cells."
    )


def _remove_orphaned_metadata(model: Model) -> None:
    """
    Remove properties from metadata that are not present in any cell lineage.

    If a multitype property has some of its types with no corresponding data,
    only the types with no data will be removed from the property. If all types
    of a property have no corresponding data, the property will be removed entirely
    from the metadata.

    Protected properties are unprotected to be removed, then protected again if some
    of their types remain. This function is meant to be used on a copy of a model,
    e.g. before exporting it.

    Parameters
    ----------
    model : Model
        The pycellin model to update.

    Warns
    -----
    If some of the cell and link properties removed have values on the cycle
    lineages, since an export leaves these values out. Properties without any value
    only get an info message, as nothing is lost, and lineage properties no message,
    as they are not exported anyway.
    """
    node_props_md = model.props_metadata._get_prop_dict_from_prop_type(
        PropertyType.NODE
    ).keys()
    edge_props_md = model.props_metadata._get_prop_dict_from_prop_type(
        PropertyType.EDGE
    ).keys()
    lineage_props_md = model.props_metadata._get_prop_dict_from_prop_type(
        PropertyType.LINEAGE
    ).keys()
    node_props_data, edge_props_data, lineage_props_data = _get_props_from_data(
        model.data.cell_lineages.values()
    )
    cycle_node_props, cycle_edge_props, _ = _get_props_from_data(
        (model.data.cycle_lineages or {}).values()
    )

    orphaned_node_props = sorted(node_props_md - node_props_data)
    orphaned_edge_props = sorted(edge_props_md - edge_props_data)
    orphaned_lineage_props = sorted(lineage_props_md - lineage_props_data)

    not_exported = sorted(
        (cycle_node_props & set(orphaned_node_props))
        | (cycle_edge_props & set(orphaned_edge_props))
    )
    if not_exported:
        logger.warning(_get_cycle_props_message(not_exported), stacklevel=2)
    for location, orphaned_props, cycle_props in (
        ("cells", orphaned_node_props, cycle_node_props),
        ("links", orphaned_edge_props, cycle_edge_props),
    ):
        without_value = [prop for prop in orphaned_props if prop not in cycle_props]
        if without_value:
            logger.info(
                f"Ignoring propert{'ies' if len(without_value) > 1 else 'y'} without "
                f"any value on {location}: {', '.join(without_value)}.",
                stacklevel=2,
            )

    mapping = {
        "node": orphaned_node_props,
        "edge": orphaned_edge_props,
        "lineage": orphaned_lineage_props,
    }
    for prop_type_str, orphaned_props in mapping.items():
        if orphaned_props:
            prop_type = _property_type_from_string(prop_type_str)
            protected = [
                prop_id
                for prop_id in orphaned_props
                if prop_id in model.props_metadata._protected_props
            ]
            for prop_id in protected:
                model.props_metadata._unprotect_prop(prop_id)
            model.props_metadata._remove_props(orphaned_props, prop_type=prop_type)
            for prop_id in protected:
                if model.props_metadata._has_prop(prop_id):
                    model.props_metadata._protect_prop(prop_id)


def _split_graph_into_lineages(
    graph: nx.DiGraph,
    lineage_id_key: str | None = None,
    lin_props: list[dict[str, Any]] | None = None,
) -> list[CellLineage]:
    """
    Split a graph into subgraphs representing lineages, and ensure consistent lineage ID
    assignment.

    This function takes a directed graph and splits it into subgraphs,
    where each subgraph corresponds to a connected component. It also ensures
    that each lineage and its nodes have a consistent lineage ID,
    either by using an existing 'lineage_id_key' property or by creating one
    if it is not provided. If 'lin_props' is provided, it also adds the
    corresponding properties to each lineage.

    Lineages without an ID get the next IDs that no other lineage uses, in the
    order of the lineages: from 0, or after the largest ID given by the data.

    Parameters
    ----------
    lineage : nx.DiGraph
        The graph to split.
    lineage_id_key : str | None, optional
        The key used to identify the lineage in the properties. If None,
        a "lineage_id" key will be created and set to the next available lineage ID.
    lin_props : list[dict[str, Any]] | None, optional
        A list of dictionaries, where each dictionary contains properties
        for a specific lineage, identified by a 'lineage_id_key' key.
        If None, no properties will be added to the lineages.

    Returns
    -------
    list[CellLineage]
        A list of subgraphs, each representing a lineage.

    Raises
    ------
    ValueError
        If a lineage is found to contain nodes with multiple distinct
        'lineage_id_key' values, indicating an inconsistency in lineage ID
        assignment, if several lineages have the same ID, or if no lineage
        properties match a lineage ID when 'lin_props' is provided.
    """
    # One subgraph is created per lineage, so each subgraph is
    # a connected component of `graph`.
    lineages = [
        CellLineage(graph.subgraph(c).copy())
        for c in nx.weakly_connected_components(graph)
    ]
    if len(lineages) == 0:
        empty_lin = CellLineage(nx.DiGraph())
        for k, v in graph.graph.items():
            empty_lin.graph[k] = v  # copying graph properties to the empty lineage
        lineages = [empty_lin]
    del graph  # don't need it anymore

    # Ensuring that nodes and lineages have a lineage_id property,
    # and that it is consistent between them.
    if lineage_id_key is None:
        # We need to create and add a lineage_id key to each lineage and
        # to each node of the lineage.
        for lin_id, lin in enumerate(lineages):
            lin.graph["lineage_id"] = lin_id
            for node in lin.nodes:
                lin.nodes[node]["lineage_id"] = lin_id
    else:
        # IDs given by the data, on the lineages or on their nodes.
        used_lin_ids = set()
        for lin in lineages:
            if lin.graph.get(lineage_id_key) is not None:
                used_lin_ids.add(lin.graph[lineage_id_key])
            used_lin_ids.update(
                lin_id
                for _, lin_id in lin.nodes(data=lineage_id_key)
                if lin_id is not None
            )
        # Lineages without an ID get the next IDs after those given by the data.
        next_lin_id = max(max(_get_int_ids(used_lin_ids), default=-1) + 1, 0)

        # Do lineages and nodes have the lineage_id_key property?
        for lin in lineages:
            lin_has_lin_id = (
                lineage_id_key in lin.graph and lin.graph[lineage_id_key] is not None
            )
            node_lin_ids = [lin.nodes[node].get(lineage_id_key) for node in lin.nodes]
            non_null_node_lin_ids = {
                lin_id for lin_id in node_lin_ids if lin_id is not None
            }
            nodes_have_lin_id = _graph_has_node_prop(lin, lineage_id_key) and all(
                lin_id is not None for lin_id in node_lin_ids
            )

            if not lin_has_lin_id and not nodes_have_lin_id:
                # No lineage_id_key property is present, we need to create it
                # then add it to both nodes and lineages.
                if len(non_null_node_lin_ids) > 1:
                    raise ValueError(
                        "Impossible state: inconsistent lineage ID values between "
                        "the nodes of a same lineage."
                    )

                if len(non_null_node_lin_ids) == 1:
                    # Specific case when some nodes have a lineage ID but not all,
                    # and agree on a non-null value.
                    generated_lin_id = next(iter(non_null_node_lin_ids))
                else:
                    generated_lin_id = next_lin_id
                    next_lin_id += 1

                lin.graph[lineage_id_key] = generated_lin_id
                for node in lin.nodes:
                    lin.nodes[node][lineage_id_key] = generated_lin_id

            elif not lin_has_lin_id and nodes_have_lin_id:
                # We need to create and add a lineage_id key to each lineage,
                # using the node property.
                tmp_lin_id = {lin.nodes[node][lineage_id_key] for node in lin.nodes}
                if len(tmp_lin_id) > 1:
                    raise ValueError(
                        "Impossible state: inconsistent lineage ID values between "
                        "the nodes of a same lineage."
                    )
                elif len(tmp_lin_id) == 0:
                    lin.graph[lineage_id_key] = 0
                else:
                    lin.graph[lineage_id_key] = next(iter(tmp_lin_id))

            elif lin_has_lin_id and not nodes_have_lin_id:
                # We need to add the lineage_id_key property to each node of
                # the lineage, using the lineage property.
                if non_null_node_lin_ids and non_null_node_lin_ids != {
                    lin.graph[lineage_id_key]
                }:
                    raise ValueError(
                        "Impossible state: inconsistent lineage ID values between "
                        "the lineage and its nodes."
                    )

                for node in lin.nodes:
                    lin.nodes[node][lineage_id_key] = lin.graph[lineage_id_key]

            else:
                if len(non_null_node_lin_ids) != 1:
                    raise ValueError(
                        "Impossible state: inconsistent lineage ID values between "
                        "the nodes of a same lineage."
                    )
                if lin.graph[lineage_id_key] != next(iter(non_null_node_lin_ids)):
                    raise ValueError(
                        f"Impossible state: inconsistent lineage ID values between "
                        f"nodes and lineage of lineage {lin.graph[lineage_id_key]}."
                    )

    # Lineages are stored by ID, so a duplicate ID would silently drop lineages.
    lin_id_key = lineage_id_key if lineage_id_key is not None else "lineage_id"
    lin_id_counts = Counter(lin.graph[lin_id_key] for lin in lineages)
    duplicates = [lin_id for lin_id, count in lin_id_counts.items() if count > 1]
    if duplicates:
        raise ValueError(
            "Lineage IDs must be unique, but several disconnected parts of the graph "
            f"have the same '{lin_id_key}' value: {', '.join(map(str, duplicates))}."
        )

    # Adding lineage properties to lineages.
    if lin_props is not None:
        _add_lineage_props(lineages, lin_props, lin_id_key)

    return lineages


def _get_int_ids(ids: Iterable[Any]) -> list[int]:
    """
    Return the integer IDs among some IDs, NumPy integers included.

    Parameters
    ----------
    ids : Iterable[Any]
        The IDs, which can be of any type.

    Returns
    -------
    list[int]
        The IDs that are integers.
    """
    return [
        lin_id
        for lin_id in ids
        if isinstance(lin_id, numbers.Integral) and not isinstance(lin_id, bool)
    ]


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
                raise ValueError(
                    f"Node {node} does not have the required key '{old_key}'."
                )
            if set_default_if_missing:
                lineage.nodes[node][new_key] = default_value


def _update_edge_prop_key(
    lineage: CellLineage,
    old_key: str,
    new_key: str,
) -> None:
    """
    Update the key of a property in all the edges of a lineage.

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    old_key : str
        The old key of the property.
    new_key : str
        The new key of the property.
    """
    for u, v in lineage.edges:
        if old_key in lineage.edges[u, v]:
            lineage.edges[u, v][new_key] = lineage.edges[u, v].pop(old_key)


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


def _update_lineages_ids_key(
    lineages: list[CellLineage],
    lineage_id_key: str | None,
) -> None:
    """
    Update the lineage ID key of lineage graphs to match pycellin convention.

    If the lineage_id_key is not present in the lineage graph, a "lineage_id" key
    is created and set to the next available lineage ID.

    Parameters
    ----------
    lineages : list[CellLineage]
        The lineages to update.
    lineage_id_key : str | None
        The key that is the lineage identifier in lineage graphs.
    """
    ids = [lin.graph[lineage_id_key] for lin in lineages if lineage_id_key in lin.graph]
    next_id = max(ids) + 1 if ids else 0

    for lin in lineages:
        try:
            lin.graph["lineage_id"] = lin.graph.pop(lineage_id_key)
        except KeyError:
            lin.graph["lineage_id"] = next_id
            next_id += 1
