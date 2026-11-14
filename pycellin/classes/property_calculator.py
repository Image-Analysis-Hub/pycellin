#!/usr/bin/env python3

"""The base classes of the calculators, which compute the values of properties."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any, ClassVar

from pycellin.classes.data import Data
from pycellin.classes.lineage import Lineage
from pycellin.classes.property import Property


def _get_lin_data_from_lin_type(data: Data, lineage_type: str) -> dict[int, Lineage]:
    """
    Get the lineages from the data object based on the lineage type.

    Parameters
    ----------
    data : Data
        `Data` object containing the lineages.
    lineage_type : str
        Type of lineage to extract from the data object.
        Can be ``"cell"``, ``"cycle"``, or ``"both"``.

    Returns
    -------
    dict[int, Lineage]
        Dictionary of lineages extracted from the data object.
        Keys are the lineage IDs. For ``"both"``, the cell lineages, each replaced by
        its cycle lineage when it has one, since they share their lineage ID.

    Raises
    ------
    ValueError
        If `lineage_type` is not ``"cell"``, ``"cycle"`` or ``"both"``.
    """
    if lineage_type == "cell":
        return data.cell_lineages
    elif lineage_type == "cycle":
        return data.cycle_lineages
    elif lineage_type == "both":
        return {**data.cell_lineages, **data.cycle_lineages}
    else:
        raise ValueError("Invalid lineage type.")


class PropertyCalculator(ABC):
    """
    Abstract class to compute and enrich data from a model with property values.

    A calculator computes the values of one property for the nodes, edges or lineages
    of a model. `Model.add_custom_property` adds it to a model, then at each update,
    the model calls its `enrich()` method, which calls `compute()` for each object to
    enrich and stores the value under the identifier of the property. Calculators
    derive from one of the six public subclasses, such as `NodeLocalPropCalculator`,
    depending on the objects the property applies to (nodes, edges or lineages) and
    on the data it needs (local or global), which set ``_PROPERTY_TYPE`` and
    ``_LOCAL_PROPERTY``.

    `INPUT_PROPS` lists the properties read by the calculator whose identifier is
    chosen by the user: it maps the name of the calculator attribute holding the
    identifier of such a property to the property type and lineage type the property
    must have, e.g. ``{"area_prop": ("node", "cell")}``. `Model.add_custom_property`
    checks that these properties are declared with these types. Calculators holding
    data that belong to the model they were created for and are not stored in it,
    e.g. a label image, set ``_USES_EXTERNAL_DATA`` to True.

    Parameters
    ----------
    property : Property
        The property computed by the calculator.
    """

    _LOCAL_PROPERTY = None  # type: bool | None
    _PROPERTY_TYPE = None  # type: str | None
    # True for calculators holding data that belong to the model they were created
    # for and are not stored in it (e.g. a label image). Such calculators are not
    # kept by Model.merge(), since they cannot compute the lineages of another model.
    _USES_EXTERNAL_DATA = False
    # Subclasses repeat the ClassVar annotation, without which Ruff warns about
    # a mutable class attribute (RUF012).
    #: Properties read by the calculator whose identifier is chosen by the user.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {}

    def __init__(self, property: Property):
        self.property = property

    @classmethod
    def is_for_local_property(cls) -> bool | None:
        """
        Return whether the calculator is for a local property.

        Accessor to the ``_LOCAL_PROPERTY`` class attribute.

        Returns
        -------
        bool | None
            True if the calculator is for a local property, False if it is for a
            global property, None for the abstract base class of all calculators.
        """
        return cls._LOCAL_PROPERTY

    @classmethod
    def get_property_type(cls) -> str | None:
        """
        Return the type of object to which the property applies.

        Accessor to the ``_PROPERTY_TYPE`` class attribute.

        Returns
        -------
        str | None
            ``"node"``, ``"edge"`` or ``"lineage"``, or None for the abstract base
            classes that don't define it.
        """
        return cls._PROPERTY_TYPE

    @classmethod
    def uses_external_data(cls) -> bool:
        """
        Return whether the calculator uses data that are not stored in the model.

        Accessor to the ``_USES_EXTERNAL_DATA`` class attribute. Such data belong to
        the model the calculator was created for, e.g. a label image: `Model.merge`
        drops these calculators, and keeps their property values, since they cannot
        compute the lineages of another model.

        Returns
        -------
        bool
            True if the calculator uses data that belong to a specific model and are
            not stored in it (e.g. a label image), False otherwise.
        """
        return cls._USES_EXTERNAL_DATA

    def get_input_props(self) -> dict[str, tuple[str, str, str]]:
        """
        Return the properties read by the calculator whose identifier the user chooses.

        They are listed in `INPUT_PROPS`.

        Returns
        -------
        dict[str, tuple[str, str, str]]
            Keys are the names of the calculator attributes holding the identifiers
            of the input properties (e.g. ``"area_prop"``). Values are tuples
            (identifier, property type, lineage type), where property type and
            lineage type are the ones the input property must have.
        """
        return {
            attr: (getattr(self, attr), prop_type, lineage_type)
            for attr, (prop_type, lineage_type) in self.INPUT_PROPS.items()
        }

    @abstractmethod
    def compute(self, *args: Any, **kwargs: Any) -> Any:
        """
        Compute the value of a property for a single object.

        Needs to be implemented in subclasses.

        Parameters
        ----------
        *args : Any
            The arguments identifying the object, which depend on the subclass.
        **kwargs : Any
            Keyword arguments of the subclass, if any.

        Returns
        -------
        Any
            The value of the property for the object.
        """

    @abstractmethod
    def enrich(self, data: Data, *args: Any, **kwargs: Any) -> None:
        """
        Enrich the data with the value of a property.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages.
        *args : Any
            Positional arguments of the subclass, if any.
        **kwargs : Any
            The objects to enrich, given by the model as ``nodes_to_enrich``,
            ``edges_to_enrich`` and ``lineage_ids_to_enrich``.
        """


class LocalPropCalculator(PropertyCalculator):
    """
    Abstract class to compute local property values and add them to lineages.

    Local properties only need data from the lineage holding the object they
    describe: the object itself, but also any other node, edge or graph attribute
    of that lineage. At each update, they are only recomputed for the objects of
    the lineages added or modified since the previous update. For example:

    - cell area (node property) only needs data from the cell itself
      (coordinates of boundary points);
    - absolute age (node property) needs the time of the cell and of the root
      of its lineage;
    - cell speed (edge property) needs the time and space location of the two
      nodes of the edge;
    - lineage duration (lineage property) needs the time of all the cells
      of the lineage.

    Parameters
    ----------
    property : Property
        The property computed by the calculator.
    """

    _LOCAL_PROPERTY = True

    @abstractmethod
    def compute(self, lineage: Lineage, *args: Any, **kwargs: Any) -> Any:
        """
        Compute the value of a local property for a single object.

        Needs to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object containing the object of interest.
        *args : Any
            The other arguments identifying the object, which depend on the subclass,
            e.g. a node ID.
        **kwargs : Any
            Keyword arguments of the subclass, if any.

        Returns
        -------
        Any
            The value of the local property for the object.
        """

    @abstractmethod
    def enrich(self, data: Data, *args: Any, **kwargs: Any) -> None:
        """
        Enrich the data with the value of a local property.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages.
        *args : Any
            Positional arguments of the subclass, if any.
        **kwargs : Any
            The objects to enrich, given by the model as ``nodes_to_enrich``,
            ``edges_to_enrich`` and ``lineage_ids_to_enrich``.
        """


class NodeLocalPropCalculator(LocalPropCalculator):
    """
    Abstract class to compute local node property values and add them to lineages.

    A local node property is computed for each node, i.e. each cell of a cell lineage
    or each cell cycle of a cycle lineage, from data of the lineage of the node only:
    the node itself, but also any other node, edge or graph attribute of that
    lineage. At each update of the model, it is only recomputed for the nodes of the
    lineages added or modified since the previous update. Cycle lineage properties
    are recomputed for all the cycle lineages at each update. For a property that
    needs data from other lineages, use `NodeGlobalPropCalculator` instead.

    To write a calculator, subclass this class and implement `compute()`, which takes
    a lineage and the ID of one of its nodes, and returns the value of the property
    for this node. Then add an instance to a model with `Model.add_custom_property`,
    and call `Model.update` to compute the values.

    Parameters
    ----------
    property : Property
        The node property computed by the calculator. Its lineage type sets the
        lineages it is computed on: cell lineages for ``"cell"``, cycle lineages for
        ``"cycle"``.

    Notes
    -----
    If `compute()` reads properties whose identifiers are chosen by the user, store
    each identifier in an attribute of the calculator, and list these attributes in
    `INPUT_PROPS` with the property type and lineage type each property must have,
    e.g. ``{"area_prop": ("node", "cell")}``: `Model.add_custom_property` then checks
    that these properties are declared with these types. To give such identifiers,
    or other arguments, to the calculator, override ``__init__()`` and call
    ``super().__init__(property)`` in it.

    See the "Custom properties" notebook, listed in :doc:`/user_guide/tutorials`, for
    examples.
    """

    _PROPERTY_TYPE = "node"

    @abstractmethod
    def compute(self, lineage: Lineage, node_id: int) -> Any:
        """
        Compute the value of a local property for a single node.

        Needs to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object containing the node of interest: a `CellLineage` or a
            `CycleLineage`, depending on the lineage type of the property.
        node_id : int
            Node ID of the node of interest.

        Returns
        -------
        Any
            The value of the local property for the node.
        """

    def enrich(
        self, data: Data, nodes_to_enrich: list[tuple[int, int]], **kwargs: Any
    ) -> None:
        """
        Enrich the data with the value of a local property for a list of nodes.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages.
        nodes_to_enrich : list[tuple[int, int]]
            List of tuples containing the node ID and the lineage ID of the nodes
            to enrich with the property value.
        **kwargs : Any
            Not used: the edges and lineages to enrich, which the model gives to all
            the calculators.
        """
        lineages = _get_lin_data_from_lin_type(data, self.property.lineage_type)
        for nid, lin_id in nodes_to_enrich:
            lin = lineages[lin_id]
            lin.nodes[nid][self.property.identifier] = self.compute(lin, nid)


class EdgeLocalPropCalculator(LocalPropCalculator):
    """
    Abstract class to compute local edge property values and add them to lineages.

    A local edge property is computed for each edge, i.e. each link between two cells
    of a cell lineage or between two cell cycles of a cycle lineage, from data of the
    lineage of the edge only: the edge and its two nodes, but also any other node,
    edge or graph attribute of that lineage. At each update of the model, it is only
    recomputed for the edges of the lineages added or modified since the previous
    update. Cycle lineage properties are recomputed for all the cycle lineages at
    each update. For a property that needs data from other lineages, use
    `EdgeGlobalPropCalculator` instead.

    To write a calculator, subclass this class and implement `compute()`, which takes
    a lineage and one of its edges, as a (source node ID, target node ID) tuple, and
    returns the value of the property for this edge. Then add an instance to a model
    with `Model.add_custom_property`, and call `Model.update` to compute the values.

    Parameters
    ----------
    property : Property
        The edge property computed by the calculator. Its lineage type sets the
        lineages it is computed on: cell lineages for ``"cell"``, cycle lineages for
        ``"cycle"``.

    Notes
    -----
    If `compute()` reads properties whose identifiers are chosen by the user, store
    each identifier in an attribute of the calculator, and list these attributes in
    `INPUT_PROPS` with the property type and lineage type each property must have,
    e.g. ``{"area_prop": ("node", "cell")}``: `Model.add_custom_property` then checks
    that these properties are declared with these types. To give such identifiers,
    or other arguments, to the calculator, override ``__init__()`` and call
    ``super().__init__(property)`` in it.

    See the "Custom properties" notebook, listed in :doc:`/user_guide/tutorials`, for
    examples.
    """

    _PROPERTY_TYPE = "edge"

    @abstractmethod
    def compute(self, lineage: Lineage, edge: tuple[int, int]) -> Any:
        """
        Compute the value of a local property for a single edge.

        Needs to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object containing the edge of interest: a `CellLineage` or a
            `CycleLineage`, depending on the lineage type of the property.
        edge : tuple[int, int]
            Directed edge of interest, as a tuple of two node IDs.

        Returns
        -------
        Any
            The value of the local property for the edge.
        """

    def enrich(
        self, data: Data, edges_to_enrich: list[tuple[int, int, int]], **kwargs: Any
    ) -> None:
        """
        Enrich the data with the value of a local property for a list of edges.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages.
        edges_to_enrich : list[tuple[int, int, int]]
            List of tuples containing the source node ID, the target node ID and
            the lineage ID of the edges to enrich with the property value.
        **kwargs : Any
            Not used: the nodes and lineages to enrich, which the model gives to all
            the calculators.
        """
        lineages = _get_lin_data_from_lin_type(data, self.property.lineage_type)
        for source, target, lin_id in edges_to_enrich:
            link = (source, target)
            lin = lineages[lin_id]
            lin.edges[link][self.property.identifier] = self.compute(lin, link)


class LineageLocalPropCalculator(LocalPropCalculator):
    """
    Abstract class to compute local lineage property values and add them to lineages.

    A local lineage property is computed for each lineage, from data of that lineage
    only: any node, edge or graph attribute of the lineage. At each update of the
    model, it is only recomputed for the lineages added or modified since the
    previous update. Cycle lineage properties are recomputed for all the cycle
    lineages at each update. For a property that needs data from other lineages, use
    `LineageGlobalPropCalculator` instead.

    To write a calculator, subclass this class and implement `compute()`, which takes
    a lineage and returns the value of the property for this lineage. Then add an
    instance to a model with `Model.add_custom_property`, and call `Model.update` to
    compute the values.

    Parameters
    ----------
    property : Property
        The lineage property computed by the calculator. Its lineage type sets the
        lineages it is computed on: cell lineages for ``"cell"``, cycle lineages for
        ``"cycle"``.

    Notes
    -----
    If `compute()` reads properties whose identifiers are chosen by the user, store
    each identifier in an attribute of the calculator, and list these attributes in
    `INPUT_PROPS` with the property type and lineage type each property must have,
    e.g. ``{"area_prop": ("node", "cell")}``: `Model.add_custom_property` then checks
    that these properties are declared with these types. To give such identifiers,
    or other arguments, to the calculator, override ``__init__()`` and call
    ``super().__init__(property)`` in it.

    See the "Custom properties" notebook, listed in :doc:`/user_guide/tutorials`, for
    examples.
    """

    _PROPERTY_TYPE = "lineage"

    @abstractmethod
    def compute(self, lineage: Lineage) -> Any:
        """
        Compute the value of a local property for a single lineage.

        Needs to be implemented in subclasses.

        Parameters
        ----------
        lineage : Lineage
            Lineage object of interest: a `CellLineage` or a `CycleLineage`,
            depending on the lineage type of the property.

        Returns
        -------
        Any
            The value of the local property for the lineage.
        """

    def enrich(
        self, data: Data, lineage_ids_to_enrich: Iterable[int], **kwargs: Any
    ) -> None:
        """
        Enrich the data with the value of a local property for the given lineages.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages.
        lineage_ids_to_enrich : Iterable[int]
            IDs of the lineages to enrich.
        **kwargs : Any
            Not used: the nodes and edges to enrich, which the model gives to all
            the calculators.
        """
        lineages = _get_lin_data_from_lin_type(data, self.property.lineage_type)
        for lin_id in lineage_ids_to_enrich:
            lin = lineages[lin_id]
            lin.graph[self.property.identifier] = self.compute(lin)


class GlobalPropCalculator(PropertyCalculator):
    """
    Abstract class to compute global property values and add them to lineages.

    Global properties need data from lineages other than the one holding the object
    they describe, typically a cycle lineage property computed from the cells of
    the matching cell lineage. At each update, they are recomputed for all the
    objects of all the lineages, so use a local property when the lineage holding
    the object is enough. Cycle lineages are rebuilt at each update, so their
    properties are recomputed for all cell cycles in both cases. For example:

    - cycle mean area (cycle lineage node property) needs the area of the cells
      of the cell cycle, which are stored in the cell lineage;
    - the number of cells present at the same time in the whole model (cell
      lineage node property) needs the cells of all the lineages.

    Parameters
    ----------
    property : Property
        The property computed by the calculator.
    """

    _LOCAL_PROPERTY = False

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, *args: Any, **kwargs: Any) -> Any:
        """
        Compute the value of a global property for a single object.

        Needs to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages.
        lineage : Lineage
            Lineage object containing the object of interest.
        *args : Any
            The other arguments identifying the object, which depend on the subclass,
            e.g. a node ID.
        **kwargs : Any
            Keyword arguments of the subclass, if any.

        Returns
        -------
        Any
            The value of the global property for the object.
        """

    @abstractmethod
    def enrich(self, data: Data, **kwargs: Any) -> None:
        """
        Enrich the data with the value of a global property for all objects.

        All the objects of all the lineages are enriched.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages to enrich.
        **kwargs : Any
            Not used: the objects to enrich, which the model gives to all the
            calculators.
        """


class NodeGlobalPropCalculator(GlobalPropCalculator):
    """
    Abstract class to compute global node property values and add them to lineages.

    A global node property is computed for each node, i.e. each cell of a cell
    lineage or each cell cycle of a cycle lineage, from data that can come from any
    lineage of the model, typically a cycle lineage property computed from the cells
    of the matching cell lineage. At each update of the model, it is recomputed for
    all the nodes of all the lineages, so use `NodeLocalPropCalculator` when the
    lineage of the node is enough.

    To write a calculator, subclass this class and implement `compute()`, which takes
    the data of the model (a `Data` object), a lineage and the ID of one of its
    nodes, and returns the value of the property for this node. Then add an instance
    to a model with `Model.add_custom_property`, and call `Model.update` to compute
    the values.

    Parameters
    ----------
    property : Property
        The node property computed by the calculator. Its lineage type sets the
        lineages it is computed on: cell lineages for ``"cell"``, cycle lineages for
        ``"cycle"``.

    Notes
    -----
    If `compute()` reads properties whose identifiers are chosen by the user, store
    each identifier in an attribute of the calculator, and list these attributes in
    `INPUT_PROPS` with the property type and lineage type each property must have,
    e.g. ``{"area_prop": ("node", "cell")}``: `Model.add_custom_property` then checks
    that these properties are declared with these types. To give such identifiers,
    or other arguments, to the calculator, override ``__init__()`` and call
    ``super().__init__(property)`` in it.

    See the "Custom properties" notebook, listed in :doc:`/user_guide/tutorials`, for
    examples.
    """

    _PROPERTY_TYPE = "node"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, node_id: int) -> Any:
        """
        Compute the value of a global property for a single node.

        Needs to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages.
        lineage : Lineage
            Lineage containing the node of interest: a `CellLineage` or a
            `CycleLineage`, depending on the lineage type of the property.
        node_id : int
            Node ID of the node of interest.

        Returns
        -------
        Any
            The value of the global property for the node.
        """

    def enrich(self, data: Data, **kwargs: Any) -> None:
        """
        Enrich the data with the value of a global property for all nodes.

        All the nodes of all the lineages are enriched.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages to enrich.
        **kwargs : Any
            Not used: the objects to enrich, which the model gives to all the
            calculators.
        """
        lineages = _get_lin_data_from_lin_type(data, self.property.lineage_type)
        for lin in lineages.values():
            for nid in lin.nodes:
                lin.nodes[nid][self.property.identifier] = self.compute(data, lin, nid)


class EdgeGlobalPropCalculator(GlobalPropCalculator):
    """
    Abstract class to compute global edge property values and add them to lineages.

    A global edge property is computed for each edge, i.e. each link between two
    cells of a cell lineage or between two cell cycles of a cycle lineage, from data
    that can come from any lineage of the model. At each update of the model, it is
    recomputed for all the edges of all the lineages, so use `EdgeLocalPropCalculator`
    when the lineage of the edge is enough.

    To write a calculator, subclass this class and implement `compute()`, which takes
    the data of the model (a `Data` object), a lineage and one of its edges, as a
    (source node ID, target node ID) tuple, and returns the value of the property for
    this edge. Then add an instance to a model with `Model.add_custom_property`, and
    call `Model.update` to compute the values.

    Parameters
    ----------
    property : Property
        The edge property computed by the calculator. Its lineage type sets the
        lineages it is computed on: cell lineages for ``"cell"``, cycle lineages for
        ``"cycle"``.

    Notes
    -----
    If `compute()` reads properties whose identifiers are chosen by the user, store
    each identifier in an attribute of the calculator, and list these attributes in
    `INPUT_PROPS` with the property type and lineage type each property must have,
    e.g. ``{"area_prop": ("node", "cell")}``: `Model.add_custom_property` then checks
    that these properties are declared with these types. To give such identifiers,
    or other arguments, to the calculator, override ``__init__()`` and call
    ``super().__init__(property)`` in it.

    See the "Custom properties" notebook, listed in :doc:`/user_guide/tutorials`, for
    examples.
    """

    _PROPERTY_TYPE = "edge"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage, edge: tuple[int, int]) -> Any:
        """
        Compute the value of a global property for a single edge.

        Needs to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages.
        lineage : Lineage
            Lineage containing the edge of interest: a `CellLineage` or a
            `CycleLineage`, depending on the lineage type of the property.
        edge : tuple[int, int]
            Directed edge of interest, as a tuple of two node IDs.

        Returns
        -------
        Any
            The value of the global property for the edge.
        """

    def enrich(self, data: Data, **kwargs: Any) -> None:
        """
        Enrich the data with the value of a global property for all edges.

        All the edges of all the lineages are enriched.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages to enrich.
        **kwargs : Any
            Not used: the objects to enrich, which the model gives to all the
            calculators.
        """
        lineages = _get_lin_data_from_lin_type(data, self.property.lineage_type)
        for lin in lineages.values():
            for edge in lin.edges:
                lin.edges[edge][self.property.identifier] = self.compute(
                    data, lin, edge
                )


class LineageGlobalPropCalculator(GlobalPropCalculator):
    """
    Abstract class to compute global lineage property values and add them to lineages.

    A global lineage property is computed for each lineage, from data that can come
    from any lineage of the model, e.g. a cycle lineage property computed from the
    cells of the matching cell lineage. At each update of the model, it is recomputed
    for all the lineages, so use `LineageLocalPropCalculator` when the lineage itself
    is enough.

    To write a calculator, subclass this class and implement `compute()`, which takes
    the data of the model (a `Data` object) and a lineage, and returns the value of
    the property for this lineage. Then add an instance to a model with
    `Model.add_custom_property`, and call `Model.update` to compute the values.

    Parameters
    ----------
    property : Property
        The lineage property computed by the calculator. Its lineage type sets the
        lineages it is computed on: cell lineages for ``"cell"``, cycle lineages for
        ``"cycle"``.

    Notes
    -----
    If `compute()` reads properties whose identifiers are chosen by the user, store
    each identifier in an attribute of the calculator, and list these attributes in
    `INPUT_PROPS` with the property type and lineage type each property must have,
    e.g. ``{"area_prop": ("node", "cell")}``: `Model.add_custom_property` then checks
    that these properties are declared with these types. To give such identifiers,
    or other arguments, to the calculator, override ``__init__()`` and call
    ``super().__init__(property)`` in it.

    See the "Custom properties" notebook, listed in :doc:`/user_guide/tutorials`, for
    examples.
    """

    _PROPERTY_TYPE = "lineage"

    @abstractmethod
    def compute(self, data: Data, lineage: Lineage) -> Any:
        """
        Compute the value of a global property for a single lineage.

        Needs to be implemented in subclasses.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages.
        lineage : Lineage
            Lineage of interest: a `CellLineage` or a `CycleLineage`, depending on
            the lineage type of the property.

        Returns
        -------
        Any
            The value of the global property for the lineage.
        """

    def enrich(self, data: Data, **kwargs: Any) -> None:
        """
        Enrich the data with the value of a global property for all lineages.

        Parameters
        ----------
        data : Data
            `Data` object containing the lineages to enrich.
        **kwargs : Any
            Not used: the objects to enrich, which the model gives to all the
            calculators.
        """
        lineages = _get_lin_data_from_lin_type(data, self.property.lineage_type)
        for lin in lineages.values():
            lin.graph[self.property.identifier] = self.compute(data, lin)
