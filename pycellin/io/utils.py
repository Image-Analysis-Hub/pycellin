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
        assignment, or if no lineage properties match the lineage ID.
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

        if len(tmp) != 1:
            raise ValueError("Impossible state: several IDs for one lineage.")

        current_lineage_id = list(tmp)[0]
        current_lineage_attr = next(
            (
                d_attr
                for d_attr in lin_props
                if d_attr.get(lineage_ID_key) == current_lineage_id
            ),
            None,
        )
        if current_lineage_attr is None:
            raise ValueError(
                f"No lineage properties found for lineage ID {current_lineage_id!r}."
            )

        # Adding the properties to the lineage.
        for k, v in current_lineage_attr.items():
            lin.graph[k] = v


def _get_props_from_data(model: Model) -> tuple[set[str], set[str], set[str]]:
    """
    Collect all property keys present in the model's data.

    Parameters
    ----------
    model : Model
        The pycellin model to scan.

    Returns
    -------
    tuple[set[str], set[str], set[str]]
        Sets of node, edge, and lineage property keys found in the data.
    """
    node_props_data = set()
    edge_props_data = set()
    lineage_props_data = set()

    for lineage in model.data.cell_data.values():
        for node in lineage.nodes:
            node_props_data.update(lineage.nodes[node].keys())
        for edge in lineage.edges:
            edge_props_data.update(lineage.edges[edge].keys())
        lineage_props_data.update(lineage.graph.keys())

    return node_props_data, edge_props_data, lineage_props_data


# def _infer_prop_dtype(model, prop_id) -> str:
#     """
#     Infer the data type of a property based on its values.

#     This function checks the first non-None value of the property in the model data
#     and infers its data type.

#     Parameters
#     ----------
#     model : Model
#         The pycellin model containing the data to check.
#     prop_id : str
#         The identifier of the property to check.

#     Returns
#     -------
#     str
#         The inferred data type of the property ("int", "float", "string", "bool").

#     Warnings
#     --------
#     This function is NOT robust and is just a quick and dirty way to infer the
#     data type of a property in case of missing metadata. For example, it doesn't
#     handle mixed data types since it only checks the first non-None value (but
#     mixed types should not happen, right...?).
#     """
#     for lineage in model.data.cell_data.values():
#         for node, prop_value in lineage.nodes(data=prop_id):
#             if prop_value is not None:
#                 if isinstance(prop_value, bool):
#                     return "bool"
#                 elif isinstance(prop_value, int):
#                     return "int"
#                 elif isinstance(prop_value, float):
#                     return "float"
#                 elif isinstance(prop_value, str):
#                     return "string"
#                 else:
#                     return "string"
#     # Default to string if no values are found.
#     return "string"


# def _add_missing_props_to_metadata(
#     model: Model,
#     missing_props: set[str],
#     prop_type: PropertyType,
# ) -> None:
#     """
#     Add properties that are in data but missing from metadata.

#     Parameters
#     ----------
#     model : Model
#         The pycellin model to update.
#     missing_props : set[str]
#         Set of property identifiers to add.
#     prop_type : PropertyType
#         Type of properties ("node", "edge", or "lineage").
#     """
#     if not missing_props:
#         return

#     warnings.warn(
#         f"{prop_type.capitalize()} properties without metadata: {missing_props}. "
#         "They will be added to the model metadata with default values.",
#         stacklevel=3,
#     )

#     prov = "Auto-generated with default values to ensure data-metadata consistency."
#     for prop in missing_props:
#         model.props_metadata._add_prop(
#             Property(
#                 identifier=prop,
#                 name=prop,
#                 description="",
#                 provenance=prov,
#                 prop_type=prop_type,
#                 lin_type="Lineage",
#                 dtype=_infer_prop_dtype(model, prop),
#             )
#         )


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


def _remove_orphaned_metadata(model: Model) -> None:
    """
    Remove properties from metadata that are not present in any lineage.

    Parameters
    ----------
    model : Model
        The pycellin model to update.
    """
    node_props_md = model.props_metadata._get_prop_dict_from_prop_type("node").keys()
    edge_props_md = model.props_metadata._get_prop_dict_from_prop_type("edge").keys()
    lineage_props_md = model.props_metadata._get_prop_dict_from_prop_type(
        "lineage"
    ).keys()
    node_props_data, edge_props_data, lineage_props_data = _get_props_from_data(model)

    orphaned_node_props = list(node_props_md - node_props_data)
    orphaned_edge_props = list(edge_props_md - edge_props_data)
    orphaned_lineage_props = list(lineage_props_md - lineage_props_data)

    mapping = {
        "node": orphaned_node_props,
        "edge": orphaned_edge_props,
        "lineage": orphaned_lineage_props,
    }
    for prop_type, orphaned_props in mapping.items():
        if orphaned_props:
            warnings.warn(
                f"{prop_type.capitalize()} metadata with no corresponding data: "
                f"{orphaned_props}. They will be removed from the model metadata.",
                stacklevel=2,
            )
            model.props_metadata._remove_props(orphaned_props)


def _split_graph_into_lineages(
    graph: nx.DiGraph,
    lineage_ID_key: str | None = None,
    lin_props: list[dict[str, Any]] | None = None,
) -> list[CellLineage]:
    """
    Split a graph into subgraphs representing lineages, and ensure consistent lineage ID assignment.

    This function takes a directed graph and splits it into subgraphs,
    where each subgraph corresponds to a connected component. It also ensures
    that each lineage and its nodes have a consistent lineage ID,
    either by using an existing 'lineage_ID_key' property or by creating one
    if it is not provided. If 'lin_props' is provided, it also adds the
    corresponding properties to each lineage.

    Parameters
    ----------
    lineage : nx.DiGraph
        The graph to split.
    lineage_ID_key : str | None, optional
        The key used to identify the lineage in the properties. If None,
        a "lineage_ID" key will be created and set to the next available lineage ID.
    lin_props : list[dict[str, Any]] | None, optional
        A list of dictionaries, where each dictionary contains properties
        for a specific lineage, identified by a 'lineage_ID_key' key.
        If None, no properties will be added to the lineages.

    Returns
    -------
    list[CellLineage]
        A list of subgraphs, each representing a lineage.

    Raises
    ------
    ValueError
        If a lineage is found to contain nodes with multiple distinct
        'lineage_ID_key' values, indicating an inconsistency in lineage ID
        assignment, or if no lineage properties match a lineage ID when
        'lin_props' is provided.
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

    # Ensuring that nodes and lineages have a lineage_ID property,
    # and that it is consistent between them.
    if lineage_ID_key is None:
        # We need to create and add a lineage_ID key to each lineage and
        # to each node of the lineage.
        lin_id = 0
        for lin in lineages:
            if len(lin) == 1:
                node = list(lin.nodes)[0]
                lin.graph["lineage_ID"] = -node
                lin.nodes[node]["lineage_ID"] = -node
            else:
                lin.graph["lineage_ID"] = lin_id
                for node in lin.nodes:
                    lin.nodes[node]["lineage_ID"] = lin_id
                lin_id += 1
    else:
        used_lin_ids = {
            lin.graph[lineage_ID_key]
            for lin in lineages
            if lineage_ID_key in lin.graph and isinstance(lin.graph[lineage_ID_key], int)
        }
        next_lin_id = max(used_lin_ids) + 1 if used_lin_ids else 0

        # Do lineages and nodes have the lineage_ID_key property?
        for lin in lineages:
            lin_has_lin_id = (
                lineage_ID_key in lin.graph and lin.graph[lineage_ID_key] is not None
            )
            node_lin_ids = [lin.nodes[node].get(lineage_ID_key) for node in lin.nodes]
            non_null_node_lin_ids = {
                lin_id for lin_id in node_lin_ids if lin_id is not None
            }
            nodes_have_lin_id = _graph_has_node_prop(lin, lineage_ID_key) and all(
                lin_id is not None for lin_id in node_lin_ids
            )

            if not lin_has_lin_id and not nodes_have_lin_id:
                # No lineage_ID_key property is present, we need to create it
                # then add it to both nodes and lineages.
                if len(non_null_node_lin_ids) > 1:
                    raise ValueError(
                        "Impossible state: inconsistent lineage ID values between "
                        "the nodes of a same lineage."
                    )

                if len(non_null_node_lin_ids) == 1:
                    # Specific case when some nodes have a lineage ID but not all,
                    # and agree on a non-null value.
                    generated_lin_id = list(non_null_node_lin_ids)[0]
                else:
                    generated_lin_id = next_lin_id
                    next_lin_id += 1

                lin.graph[lineage_ID_key] = generated_lin_id
                for node in lin.nodes:
                    lin.nodes[node][lineage_ID_key] = generated_lin_id

            elif not lin_has_lin_id and nodes_have_lin_id:
                # We need to create and add a lineage_ID key to each lineage,
                # using the node property.
                tmp_lin_id = set(lin.nodes[node][lineage_ID_key] for node in lin.nodes)
                if len(tmp_lin_id) > 1:
                    raise ValueError(
                        "Impossible state: inconsistent lineage ID values between "
                        "the nodes of a same lineage."
                    )
                elif len(tmp_lin_id) == 0:
                    lin.graph[lineage_ID_key] = 0
                else:
                    lin.graph[lineage_ID_key] = list(tmp_lin_id)[0]

            elif lin_has_lin_id and not nodes_have_lin_id:
                # We need to add the lineage_ID_key property to each node of
                # the lineage, using the lineage property.
                if non_null_node_lin_ids and non_null_node_lin_ids != {
                    lin.graph[lineage_ID_key]
                }:
                    raise ValueError(
                        "Impossible state: inconsistent lineage ID values between "
                        "the lineage and its nodes."
                    )

                for node in lin.nodes:
                    lin.nodes[node][lineage_ID_key] = lin.graph[lineage_ID_key]

            else:
                if len(non_null_node_lin_ids) != 1:
                    raise ValueError(
                        "Impossible state: inconsistent lineage ID values between "
                        "the nodes of a same lineage."
                    )
                if lin.graph[lineage_ID_key] != list(non_null_node_lin_ids)[0]:
                    raise ValueError(
                        f"Impossible state: inconsistent lineage ID values between "
                        f"nodes and lineage of lineage {lin.graph[lineage_ID_key]}."
                    )

    # Adding lineage properties to lineages.
    if lin_props is not None:
        lin_id_key = lineage_ID_key if lineage_ID_key is not None else "lineage_ID"
        _add_lineage_props(lineages, lin_props, lin_id_key)

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
